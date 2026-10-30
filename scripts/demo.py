#!/usr/bin/env python3
"""TrustBridge demo orchestration: normal / timeout / adversarial flows.

Two modes:
  --sim (default) FakeNode in-process smoke of the ORCHESTRATION only.
                 Deal semantics truth = Rust core + tests; FakeNode mirrors.
  --node URL     drive the real devnet via NodeClient (ETH JSON-RPC, S4).

Node-mode notes (R1):
  * identities: buyer/seller params and notarize `from` are anvil address
    strings (ALICE=#1, BOB=#2, BROKER=#0) — the chain guards compare
    `ctx.caller.to_string()` exactly (lib.rs require(), D5);
  * sender matrix: faucet/committee_config/create_deal -> BROKER default,
    fund/complete -> alice, submit_deliverable -> bob, notarize -> the entry's
    own `from` (self-signed guard, lib.rs:367-369), claim_timeout -> default;
  * flow gating: （R2 已拆除）— 对抗流自 R2 起上链：apply_committee_verdict 的
    wire 在 lib.rs 扁平化为 (string,uint8,string[]) 并 eth 导出（体内重建 wire
    结构体，校验链零改），故 node 的 --flow all 序列 = normal+timeout+adversarial
    （与 sim 对齐）。三个裁决场景（Malicious / NotFulfilled / Fulfilled）各建一单，
    每单 fund 前有余额读回断言（资金自足：分支头 faucet 10_000）；misconduct
    计数走 apply_verdict 的 println（`shaker console` 回放取证）；
  * 正常流评估（R2）：node 模式改走链上 assess_brief（instance 方法，export=eth，
    空 base_url/api_key => HeuristicModel 回放），报告 JSON 直接驱动 create_deal
    的 est_duration_ms/est_confidence；sim 模式仍走 get_llm 回放；
  * timeout flow deviation (registered, w1b2-r1-demo-timeout.md): the deal is
    created with a SHORT estimate (200ms -> 1 slot) instead of the 60s LLM
    estimate, then nudged past the deadline with zero-value faucet sends and
    discovered by enumeration — the 60s assessment path is covered by the
    normal flow (no deadline wait).

The three demo scenarios match PLAN §2:
  normal      offer -> assess -> deal -> fund -> accept -> deliver -> complete
  timeout     ... fund, seller stalls, watcher claims, buyer refunded
  adversarial ... deliver a FORGED doc, buyer disputes, committee verdict=Malicious

R3（路线② E2）`--flow committee`（**node-only**，不进 `--flow all` 序列）：
  env 断言（docker/cast + TARGET=`shaker to-hex <实例名>` 非零且 ≠ --contract）
  → GetNodeInfo ×4（NodeID 制成员，禁硬编码）→ committee_config(NodeID×4) +
  e2_configure(bytes32×4, 4)（**cast send 通道**）→ advance(cast call) →
  dest_epoch poll → finalize(cast call) → 争议单（无交付 = 证据派生
  NotFulfilled）→ e2_arm 一次 + e2_net_config 读回断言 armed_deal → node1 单次
  e2_run_verdict_round（**cast call**，严禁 cast send）→ Refunded 读回 + 余额
  勾稽 + console（取证源 node1）signers/aggregate/apply_verdict 行。
  `--instance Lyquid-…` 必填（shaker console/to-hex 用实例名，不是地址）。
  诚实红线：绝不以单签冒充四节点——L2/L1/L0 分级结论由 T3 实测登记（plan §3.4）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.common.llm import build_assessor_prompt, get_llm
from agents.common.protocol import (KIND_ACCEPTANCE, KIND_DELIVERABLE, KIND_DISPUTE, KIND_OFFER,
                                    KIND_RECEIPT, KIND_REQUEST, envelope, digest, evidence_root,
                                    fnv1a64)
from agents.common.rpc import (ALICE_ADDR, BOB_ADDR, BROKER_ADDR, DEFAULT_NODE, SLOT_MS,
                               FakeNode, NodeClient, docker_exec, get_node_ids,
                               shaker_console, shaker_to_hex)

ALICE, BROKER, BOB = "agent-alice", "agent-broker", "agent-bob"
# Committee: the nodes adjacent to the broker double as endorsement members
# (broker.py narrative), so BROKER itself sits on the set. The verdict gate
# requires caller ∈ members ∧ caller ∈ signers, so the demo submits the
# verdict under BROKER's identity with signers = COMMITTEE[:THRESHOLD].
COMMITTEE = [BROKER, "node-1", "node-2", "node-3"]
THRESHOLD = 3

# --- R3（路线② E2）委员会流常量 -------------------------------------------
# oracle 主题名（lib.rs `network oracle cert_verdict`；回调 group =
# oracle::certified::cert_verdict::two_phase）。
E2_TOPIC = "cert_verdict"
# 认证域与成员域**阈值同值**（plan §3.3）：4 节点全数签署。T1 若登记降级值，
# 改这里即可（阈值是调用参数，不需重新 deploy；avg_num 才是编码期常量）。
E2_THRESHOLD = 4
# `--instance` 缺省值：**T3 deploy 实录回填点**（plan §0-#4 / §3.6-7）。
# 形态先例 `_r1-deploy-raw.txt:423-424`：`created Lyquid-ffy2ydso… => 0xF8e3…`。
# shaker console / shaker to-hex 都必须用**实例名**（不是合约地址，
# implementation.md:204）；未回填时 committee 流以明确错误退出（fail-closed，
# 绝不猜测实例名）。
DEFAULT_INSTANCE = "Lyquid-ybidj3krshf4gqcjk3m3px6mooi6tg74twwaa"
INSTANCE = DEFAULT_INSTANCE       # main() 由 --instance 覆盖

# Read-after-write retry budget: on the devnet the eth_call read path can lag
# one block behind the receipt (R0 measured; keeper.py:56-58 uses the same
# 5 x 0.4s). Final-state prints must not report a stale pre-transition state.
READ_BACK_ATTEMPTS = 5
READ_BACK_DELAY_S = 0.4


def banner(t: str):
    print("\n" + "=" * 68 + f"\n  {t}\n" + "=" * 68)


def read_back(node, deal_id, terminal=("Settled", "Refunded")):
    """deal_info with the keeper's finality-window retry (sim: single read)."""
    info = node.deal_info(deal_id)
    if not node_mode(node):
        return info
    for _ in range(READ_BACK_ATTEMPTS - 1):
        if info.get("state") in terminal:
            break
        time.sleep(READ_BACK_DELAY_S)
        info = node.deal_info(deal_id)
    return info


def read_back_funded(node, deal_id):
    """Post-fund read: wait until the read path shows Funded AND a deadline
    (the first deal_info after fund can still say Qualified/deadline=None —
    R0 measured one-block lag; keeper.py:60-68 同款重试口径)."""
    info = node.deal_info(deal_id)
    if not node_mode(node):
        return info
    for _ in range(READ_BACK_ATTEMPTS - 1):
        if info.get("state") == "Funded" and info.get("deadline_slot") is not None:
            break
        time.sleep(READ_BACK_DELAY_S)
        info = node.deal_info(deal_id)
    return info


def wait_state(node, deal_id, expected):
    """Read back until `deal_info.state == expected` (budget = the keeper's).

    The devnet read path can lag one block behind the receipt (R1 measured),
    so a state print taken immediately after a write can show the
    pre-transition state. Returns the last info read either way — callers
    print/assert on it, so a stuck state is visible, never hidden."""
    info = node.deal_info(deal_id)
    if not node_mode(node):
        return info
    for _ in range(READ_BACK_ATTEMPTS - 1):
        if info.get("state") == expected:
            break
        time.sleep(READ_BACK_DELAY_S)
        info = node.deal_info(deal_id)
    return info


def wait_for(node, predicate, timeout_s=30.0, interval_s=1.0, *, what="condition"):
    """读回轮询（R5 口径）：**间隔递增**，预算内等到 predicate 完成。

    `predicate()` 返回 `(done, value)`；`done=True` 即返回该 value；**可以抛
    异常**表示硬失配（立即 abort，不等满预算）。超时抛 RuntimeError，消息带
    last value 并注明「still pending, not a mismatch」——使「pending 到超时」
    与「硬失配」两类失败语义可区分。仅 node 路径（flow_committee）使用，
    sim 路径零改动。

    为什么递增间隔：认证回调的内层 certified call 可能晚一块上链，且 4 节点
    validate 轮本身有耗时（w1b1-s2-oracle.md:82 实测块推进）；固定 0.4s×5 的
    读回预算（READ_BACK_ATTEMPTS）不够，同时不应高频抖动地 hammer 读路径。
    节奏 = 1s, 2s, 4s（cap 4s）。
    """
    deadline = time.time() + timeout_s
    attempt = 0
    delay = interval_s
    last = None
    while True:
        attempt += 1
        done, last = predicate()
        if done:
            return last
        if time.time() >= deadline:
            raise RuntimeError(
                f"[wait_for] {what}: timeout after {timeout_s}s "
                f"({attempt} attempt(s), last={last!r}) — still pending, not a mismatch")
        # 睡眠不越过预算（否则 4s 的递增间隔会把 1.5s 预算拖成 3s）
        time.sleep(max(0.0, min(delay, deadline - time.time())))
        delay = min(delay * 2, 4.0)


def require_funds(node, buyer, amount=1_000):
    """资金门（T6 总则，静默）：每笔 fund 前读回断言买方余额 >= 托管额。

    fund 的余额不足在链上是**静默 Err**（lib.rs 预检 Err 被平台吞掉，tx
    status 仍 0x1，rpc.py 模块 docstring），只能靠读回提前拦截。故意零打印：
    sim transcript 必须逐字不变（G3a/T4 逐字比对门）。"""
    bal = node.balance_of(buyer)
    if bal < amount:
        raise RuntimeError(
            f"funds gate: balance_of({buyer})={bal} < {amount} — stopping (record, do not continue)")


def selftest_evidence_root():
    """Pin the Python evidence_root to the vectors frozen in core.rs tests
    (evidence_root_fold_contract_pinned) + the two official FNV-1a-64 vectors
    quoted in core.rs. Any drift between the two implementations trips here."""
    e1 = {"seq": 1, "from": "alice", "to": "bob", "payload_digest": "deadbeef", "slot": 7}
    e2 = {"seq": 2, "from": "bob", "to": "alice", "payload_digest": "cafebabe", "slot": 9}
    cases = [
        ("empty log == offset basis          ", evidence_root([]) == "cbf29ce484222325"),
        ("single entry                       ", evidence_root([e1]) == "ce89e4ab1c1b684e"),
        ("two entries, slice order           ", evidence_root([e1, e2]) == "29657aade6273a2b"),
        ("permutation, order-sensitive       ", evidence_root([e2, e1]) == "1760599a7e9537c3"),
        ("deterministic and order-divergent  ",
         evidence_root([e1, e2]) == evidence_root([e1, e2]) != evidence_root([e2, e1])),
        ("official FNV vector fnv1a64(b\"a\")     ", fnv1a64(b"a") == "af63dc4c8601ec8c"),
        ("official FNV vector fnv1a64(b\"foobar\")", fnv1a64(b"foobar") == "85944171f73967e8"),
    ]
    for name, ok in cases:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        assert ok, f"selftest failed: {name.strip()}"
    print("SELFTEST OK")


def node_mode(node) -> bool:
    """True when the transport is the real devnet (NodeClient)."""
    return isinstance(node, NodeClient)


def role_ids(node):
    """On-chain identity vs sim identity (plan R1 §4 C/demo).

    node mode: chain identities ARE the anvil address strings — the guards
    compare `ctx.caller.to_string()` exactly (lib.rs require(), D5), and the
    deal's buyer/seller params must be the same strings.
    sim mode: agent names — behaviour unchanged.
    Returns (alice, broker, bob)."""
    if node_mode(node):
        return ALICE_ADDR, BROKER_ADDR, BOB_ADDR
    return ALICE, BROKER, BOB


def call(node, method, *args, sender=None):
    """Per-call sender selection exists only on NodeClient (the node's dev
    signer signs per `from`, rpc.py module docstring). FakeNode has no sender
    concept, so the sim path stays argument-identical to before."""
    fn = getattr(node, method)
    if node_mode(node) and sender is not None:
        return fn(*args, sender=sender)
    return fn(*args)


def notarize(node, deal_id, kind, payload, frm, to, sender=None):
    """Append a notarized envelope. Node mode signs with the entry's own `from`
    (self-signed guard: `from` must equal the caller); sim mode passes no
    sender and keeps the old call shape."""
    env = envelope(kind, payload, frm, to, deal_id)
    d = digest(env)
    if sender is None and node_mode(node):
        sender = frm
    seq = call(node, "notarize", deal_id, frm, to, d, sender=sender)
    return seq, d


def terms_digests(amount):
    """Canonical terms + acceptance digests shared by both modes/flows."""
    terms = {"terms": "license:song:midnight-motors:online-video,12mo,EU", "amount": amount}
    terms_digest = hashlib.sha256(json.dumps(terms, sort_keys=True).encode()).hexdigest()
    acceptance = {"of": terms_digest, "check": "deliverable matches license terms"}
    acceptance_digest = hashlib.sha256(json.dumps(acceptance, sort_keys=True).encode()).hexdigest()
    return terms_digest, acceptance_digest


def new_assessed_deal(node, alice, broker, bob, amount=1_000):
    """broker: assessment -> create_deal (two-step pattern).

    sim : get_llm() replay (R1 baseline, output unchanged);
    node: the assessment runs ON-CHAIN via assess_brief (instance method,
          export=eth; empty base_url/api_key => HeuristicModel replay) — the
          brief is the DealBrief four-field JSON (assessor.rs:45-50) and the
          returned report drives create_deal's estimate fields."""
    terms_digest, acceptance_digest = terms_digests(amount)
    if node_mode(node):
        brief = json.dumps({
            "buyer_profile_digest": hashlib.sha256(f"profile:{alice}".encode()).hexdigest(),
            "seller_profile_digest": hashlib.sha256(f"profile:{bob}".encode()).hexdigest(),
            "terms_digest": terms_digest,
            "license_scope": "online-video,12mo,EU",
        }, sort_keys=True)
        rep = node.assess_brief(brief)          # 回放模式：空 base_url/api_key
        print(f"assess_brief (on-chain, mode=replay): {rep}")   # node-only 证据行
    else:
        llm = get_llm()
        rep = json.loads(llm.complete_json(build_assessor_prompt(
            {"buyer": alice, "seller": bob, "amount": amount})))
    deal_id = call(node, "create_deal", alice, bob, amount, 200, terms_digest,
                   acceptance_digest, rep["est_duration_ms"], rep["est_confidence"])
    notarize(node, deal_id, KIND_OFFER, {"budget": amount}, alice, broker)
    notarize(node, deal_id, KIND_REQUEST, {"amount": amount, "terms": terms_digest}, broker, bob)
    return deal_id, terms_digest


def short_estimated_deal(node, alice, bob, amount=1_000):
    """Node-mode timeout deal: direct create_deal with a 200ms estimate
    (timeout_slots=1, types.rs:195-197) instead of the 60s LLM estimate, so the
    deadline is reachable by nudging. Registered deviation — see module doc."""
    terms_digest, acceptance_digest = terms_digests(amount)
    deal_id = call(node, "create_deal", alice, bob, amount, 200, terms_digest,
                   acceptance_digest, 200, 90)
    return deal_id, terms_digest


def flow_normal(node):
    banner("FLOW 1 — normal: assess -> escrow -> deliver -> settle")
    alice, broker, bob = role_ids(node)
    node.faucet(alice, 10_000)
    deal_id, terms_digest = new_assessed_deal(node, alice, broker, bob)
    print(f"deal={deal_id} info={node.deal_info(deal_id)}")

    require_funds(node, alice)   # 资金门（T6 总则）：fund 前余额读回，静默
    call(node, "fund", deal_id, sender=alice)
    notarize(node, deal_id, KIND_ACCEPTANCE, {"terms": terms_digest, "accepted": True}, bob, broker)
    license_doc = "LICENSE-DOC: grant of song 'midnight-motors' to alice, online-video,12mo,EU"
    doc_digest = hashlib.sha256(license_doc.encode()).hexdigest()
    notarize(node, deal_id, KIND_DELIVERABLE, {"license_doc_sha256": doc_digest}, bob, alice)
    call(node, "submit_deliverable", deal_id, doc_digest, sender=bob)
    notarize(node, deal_id, KIND_RECEIPT, {"ok": True}, alice, bob)
    call(node, "complete", deal_id, sender=alice)

    final = read_back(node, deal_id)
    print(f"final state={final['state']} "
          f"balances: alice={node.balance_of(alice)} bob={node.balance_of(bob)} "
          f"broker={node.balance_of(broker)}")


def flow_timeout(node):
    banner("FLOW 2 — timeout: seller stalls, watcher claims, buyer refunded")
    alice, broker, bob = role_ids(node)
    node.faucet(alice, 1_000)
    if node_mode(node):
        # Deviation (registered): short estimate -> 1 slot; the 60s LLM
        # assessment path is covered by the normal flow.
        deal_id, _ = short_estimated_deal(node, alice, bob, amount=1_000)
        print(f"deal={deal_id} info={node.deal_info(deal_id)} (short-estimate create: est_ms=200)")
    else:
        deal_id, _ = new_assessed_deal(node, alice, broker, bob, amount=1_000)
    call(node, "fund", deal_id, sender=alice)
    info = read_back_funded(node, deal_id)
    print(f"deal={deal_id} deadline_slot={info['deadline_slot']} (timeout_slots={info['timeout_slots']})")

    # seller stalls; time passes; watcher (any node / keeper) polls and claims.
    if node_mode(node):
        deadline = info["deadline_slot"]
        if deadline is None:
            raise RuntimeError(
                f"{deal_id}: deadline_slot not visible after retries (fund may have failed)")
        print(f"nudge: block={node.block_number()} deadline_slot={deadline} — nudging past it")
        while node.block_number() <= deadline:
            node.nudge()
            print(f"  nudge -> block={node.block_number()}", flush=True)
        block = node.block_number()
        known = node.discover_deals()
        due = [d for d in known
               if node.deal_info(d).get("state") == "Funded"
               and node.deal_info(d).get("deadline_slot") is not None
               and block >= node.deal_info(d)["deadline_slot"]]
        print(f"watcher: discovered={known} due={due}")
        for d in due:
            call(node, "claim_timeout", d)
        after = read_back(node, deal_id, terminal=("Refunded",))
        print(f"final state={after['state']} alice={node.balance_of(alice)} "
              f"(made whole)")
    else:
        # tick() only exists on FakeNode — against a real node the block clock
        # advances via nudge (above) and the keeper (W2) submits the claims.
        if hasattr(node, "tick"):
            node.tick(info["timeout_slots"] + 1)
        due = node.due_deals()
        print(f"watcher: due_deals={due}")
        for d in due:
            node.claim_timeout(d)
        after = read_back(node, deal_id)
        print(f"final state={after['state']} alice={node.balance_of(alice)} (made whole)")


def flow_adversarial(node):
    banner("FLOW 3 — adversarial: forged deliverable -> dispute -> committee Malicious verdict")
    if node_mode(node):
        flow_adversarial_node(node)
        return
    node.faucet(ALICE, 1_000)
    deal_id, _ = new_assessed_deal(node, ALICE, BROKER, BOB, amount=1_000)
    node.fund(deal_id)

    forged = "FORGED-LICENSE-DOC: copied template, wrong scope"
    forged_digest = hashlib.sha256(forged.encode()).hexdigest()
    node.submit_deliverable(deal_id, forged_digest)

    reason = {"reason": "deliverable does not match agreed terms"}
    reason_digest = hashlib.sha256(json.dumps(reason, sort_keys=True).encode()).hexdigest()
    notarize(node, deal_id, KIND_DISPUTE, reason, ALICE, BOB)
    node.open_dispute(deal_id, reason_digest)

    # committee: threshold signers inspected the evidence log -> Malicious.
    # The broker sits on the committee (nodes next to the broker double as
    # members) and submits under its own identity, mirroring the Rust gate
    # (caller must be a member AND among the signers). The cert root is
    # folded from the same evidence log the chain re-checks — same-source by
    # design (README trust table); the DISPUTE entry above is already in the
    # log and nothing appends between the fold and the verdict.
    signers = COMMITTEE[:THRESHOLD]                      # includes BROKER
    entries = node.evidence_entries(deal_id)             # mirror of members reading evidence_entries_json
    cert = (2, evidence_root(entries), signers)          # Malicious + root + signers
    node.apply_committee_verdict(deal_id, cert, BROKER)  # orchestration passes broker's identity

    print(f"final state={node.deal_info(deal_id)['state']} alice={node.balance_of(ALICE)} "
          f"misconduct={getattr(node, 'misconduct', {})}")


def flow_adversarial_node(node):
    """R2 goal B: adversarial flow on the REAL devnet — three verdict scenarios.

    Same wire for all three (apply_committee_verdict with the flat
    (string,uint8,string[]) params): only the verdict_code and the deliverable
    differ, so the transcript is the on-chain positive/negative control set of
    core.rs's verdict -> state/payout mapping (Fulfilled -> Settled,
    NotFulfilled/Malicious -> Refunded; misconduct bumps ONLY on Malicious,
    core.rs:203-210).

    Self-contained funding (T6 总则): faucet 10_000 up front, and every fund is
    guarded by a balance read-back (>= 1_000). Malicious/NotFulfilled refund
    1_000 each to alice, but Fulfilled pays via Payout::settle with
    refund_to_buyer = 0 (types.rs:170) — alice gets nothing back on that deal,
    so the third fund MUST be covered by this branch's own headroom
    (10_000 >= 3 x 1_000 + margin)."""
    alice, broker, bob = role_ids(node)
    node.faucet(alice, 10_000)
    # Address-based committee: on-chain members are just strings; node-1..3 are
    # never called, they only fill the threshold. signers = the first THRESHOLD
    # entries (broker address included) => caller ∈ members ∧ caller ∈ signers
    # ∧ len >= threshold all hold for the broker-sent verdict.
    committee = [BROKER_ADDR] + COMMITTEE[1:]
    signers = committee[:THRESHOLD]
    print(f"[adversarial] faucet(alice,10000) -> balance_of(alice)={node.balance_of(alice)} "
          f"(self-funded arm; T6 general rule)")

    forged = "FORGED-LICENSE-DOC: copied template, wrong scope"
    forged_digest = hashlib.sha256(forged.encode()).hexdigest()
    reason = {"reason": "deliverable does not match agreed terms"}
    reason_digest = hashlib.sha256(json.dumps(reason, sort_keys=True).encode()).hexdigest()

    def snapshot():
        return {"alice": node.balance_of(alice), "bob": node.balance_of(bob),
                "broker": node.balance_of(broker)}

    def open_scenario(tag, deliverable_digest):
        """create -> fund -> submit -> dispute.

        Returns (deal_id, pre-fund balances, post-fund balances). Both snapshots
        are needed: the refund verdict gives the escrow back (post-fund +1_000),
        a settlement keeps it (post-fund unchanged) — the pre-fund snapshot alone
        cannot distinguish those two."""
        before = snapshot()
        require_funds(node, alice, 1_000)
        deal_id, _ = new_assessed_deal(node, alice, broker, bob, amount=1_000)
        created = node.deal_info(deal_id)
        call(node, "fund", deal_id, sender=alice)
        funded = wait_state(node, deal_id, "Funded")
        after_fund = snapshot()
        call(node, "submit_deliverable", deal_id, deliverable_digest, sender=bob)
        submitted = wait_state(node, deal_id, "Submitted")
        notarize(node, deal_id, KIND_DISPUTE, reason, alice, bob)
        call(node, "open_dispute", deal_id, reason_digest, sender=alice)
        disputed = wait_state(node, deal_id, "Disputed")
        print(f"[{tag}] deal={deal_id} state ladder: {created['state']} -> {funded['state']} "
              f"-> {submitted['state']} -> {disputed['state']} "
              f"(timeout_slots={funded['timeout_slots']})")
        return deal_id, before, after_fund

    def apply_verdict(deal_id, verdict_code):
        # 证书根由链上证据日志折叠（与链上 into_domain 同源）；签名集 = signers；
        # 提交方 = broker 地址（caller ∈ members ∧ caller ∈ signers）。
        entries = node.evidence_entries(deal_id)
        cert = (verdict_code, evidence_root(entries), signers)
        call(node, "apply_committee_verdict", deal_id, cert, broker)

    def report(tag, deal_id, before, after_fund, final):
        after = snapshot()
        print(f"[{tag}] final state={final['state']}  "
              f"alice {before['alice']} -> {after_fund['alice']} (after fund) -> {after['alice']} (after verdict)  "
              f"bob {before['bob']}->{after['bob']}  broker {before['broker']}->{after['broker']}")
        return after

    # --- scenario 1: Malicious (2) => Refunded + misconduct[bob] += 1 ---
    deal_m, before_m, funded_m = open_scenario("malicious", forged_digest)
    apply_verdict(deal_m, 2)
    final_m = read_back(node, deal_m, terminal=("Refunded",))
    after_m = report("malicious", deal_m, before_m, funded_m, final_m)
    if final_m["state"] != "Refunded":
        raise RuntimeError(f"malicious verdict did not reach Refunded: {final_m}")
    if after_m["alice"] != funded_m["alice"] + 1_000:
        raise RuntimeError(f"malicious refund: alice {funded_m['alice']}->{after_m['alice']} != +1000")
    print("[malicious] misconduct counter has no getter (method list frozen) — evidence is the "
          "apply_verdict println cumulative view via `shaker console` "
          "(_r2-adversarial-console-raw.txt)")

    # --- scenario 2 (Fulfilled control): compliant deliverable -> cert 0 -> Settled ---
    license_doc = "LICENSE-DOC: grant of song 'midnight-motors' to alice, online-video,12mo,EU"
    doc_digest = hashlib.sha256(license_doc.encode()).hexdigest()
    deal_f, before_f, funded_f = open_scenario("fulfilled", doc_digest)
    fee = 1_000 * 200 // 10_000          # amount * fee_bps / 10_000 (200 bps)
    apply_verdict(deal_f, 0)
    final_f = read_back(node, deal_f, terminal=("Settled", "Refunded"))
    after_f = report("fulfilled", deal_f, before_f, funded_f, final_f)
    if final_f["state"] != "Settled":
        raise RuntimeError(f"fulfilled verdict did not reach Settled: {final_f}")
    if after_f["alice"] != funded_f["alice"]:
        raise RuntimeError("fulfilled: alice must not receive a refund (refund_to_buyer == 0)")
    if after_f["bob"] != before_f["bob"] + 1_000 - fee:
        raise RuntimeError(f"fulfilled split: bob {before_f['bob']}->{after_f['bob']} != +{1_000 - fee}")
    if after_f["broker"] != before_f["broker"] + fee:
        raise RuntimeError(f"fulfilled split: broker {before_f['broker']}->{after_f['broker']} != +{fee}")
    print(f"[fulfilled] split check OK: fee={fee}, bob +{1_000 - fee}, broker +{fee}")

    # --- scenario 3: NotFulfilled (1) => Refunded, misconduct NOT bumped ---
    deal_n, before_n, funded_n = open_scenario("not-fulfilled", forged_digest)
    apply_verdict(deal_n, 1)
    final_n = read_back(node, deal_n, terminal=("Refunded",))
    after_n = report("not-fulfilled", deal_n, before_n, funded_n, final_n)
    if final_n["state"] != "Refunded":
        raise RuntimeError(f"not-fulfilled verdict did not reach Refunded: {final_n}")
    if after_n["alice"] != funded_n["alice"] + 1_000:
        raise RuntimeError(f"not-fulfilled refund: alice {funded_n['alice']}->{after_n['alice']} != +1000")
    if after_n["bob"] != before_n["bob"] or after_n["broker"] != before_n["broker"]:
        raise RuntimeError("not-fulfilled: seller/broker balances must stay unchanged")
    print("[not-fulfilled] misconduct control point: its apply_verdict println shows the SAME "
          "counter value as after the Malicious verdict (no bump) — see console evidence")


# ---------------------------------------------------------------------------
# R3（路线② E2）：四节点委员会认证回合（node-only）
# ---------------------------------------------------------------------------


def _wait_dest_epoch(node, timeout_s=30.0, interval_s=1.0) -> int:
    """advance 之后轮询 dest epoch（P5：**dest 面**才是 finalize 的等待条件）。

    `get_epoch` 读源侧 current.epoch，finalize 前恒 0——绝不能用它做等待条件
    （probe_net_config 注记）。"""
    deadline = time.time() + timeout_s
    epoch = 0
    tries = 0
    while time.time() < deadline:
        tries += 1
        epoch = node.oracle_dest_epoch(E2_TOPIC)
        print(f"[committee]   dest_epoch poll #{tries} -> {epoch}", flush=True)
        if epoch >= 1:
            return epoch
        time.sleep(interval_s)
    raise RuntimeError(
        f"[committee] dest_epoch stayed {epoch} after {timeout_s}s (advance did not land)")


def flow_committee(node):
    """R3 目标 A：四节点委员会认证（路线②）的单命令演示（node-only）。

    步骤 = plan §3.6 的 1–7：env/TARGET 断言 → GetNodeInfo×4 → 双域同源配置
    （escrow NodeID 成员域 + oracle bytes32 认证域）→ advance/finalize →
    证据派生 NotFulfilled 的争议单 → arm（读回断言）+ node1 单次 run_round →
    Refunded 读回 + 余额勾稽 + console 取证。

    诚实边界：本函数只**驱动**回合；能否聚齐 4 提案 / 4 签（L2）由 T3 首跑
    console 判定，不达时按 plan §3.4 预登记 fallback（avg_num=1 + 重新 deploy）
    或 L0 三段式降级——**绝不以单签冒充四节点**。
    """
    banner("FLOW 4 — committee: 4-node oracle certification (route ②, E2)")
    if not node_mode(node):
        raise SystemExit(
            "[committee] node-only flow: FakeNode has no oracle certification round; "
            "rerun with --node <url> --contract <addr> --instance Lyquid-…")
    instance = (INSTANCE or "").strip()
    if not instance:
        raise SystemExit(
            "[committee] --instance <Lyquid-…> is required: shaker console / to-hex take the "
            "instance NAME, not the contract address (T3 deploy 实录回填 DEFAULT_INSTANCE)")

    # --- 1. env 断言（plan §3.6-1） -------------------------------------
    cp = docker_exec("cast", "--version", check=False)
    if cp.returncode != 0:
        raise RuntimeError(
            f"[committee] docker/cast unavailable (rc={cp.returncode}): {cp.stderr.strip()}")
    target = shaker_to_hex(instance)
    if int(target, 16) == 0 or target.lower() == node.contract.lower():
        raise RuntimeError(
            f"[committee] TARGET assertion failed: shaker to-hex {instance} -> {target}; "
            f"contract={node.contract} (TARGET must be non-zero and != --contract)")
    print(f"[committee] env: node={node.base_url} contract={node.contract} instance={instance}")
    print(f"[committee] TARGET={target} (shaker to-hex {instance}) != contract={node.contract} -> OK")

    nodes = get_node_ids()
    node_ids = [n["node_id"] for n in nodes]
    node_bytes32 = [n["bytes32"] for n in nodes]
    for n in nodes:
        print(f"[committee] {n['node']} port={n['port']} node_id={n['node_id']} bytes32={n['bytes32']}")

    # --- 2. 双域同源配置（plan §3.3：两域阈值同值、成员同源） -----------
    node.committee_config(node_ids, E2_THRESHOLD)
    print(f"[committee] committee_config(NodeID×4, threshold={E2_THRESHOLD}) sent by broker "
          f"(escrow 成员域)")
    send_out = node.e2_configure_cast(node_bytes32, E2_THRESHOLD)
    first_line = next((ln.strip() for ln in send_out.splitlines() if ln.strip()), "(no stdout)")
    print(f"[committee] e2_configure(bytes32[]×4, {E2_THRESHOLD}) cast send -> {first_line} "
          f"(console: staged committee of 4 nodes)")

    # --- 3. advance → dest_epoch poll → finalize（cast call 通道） --------
    adv = node.oracle_advance_epoch(E2_TOPIC, target)
    print(f"[committee] __lyquor_oracle_advance_epoch({E2_TOPIC}, {target}) -> {adv}")
    if not adv:
        raise RuntimeError("[committee] advance_epoch returned false (staging/target mismatch)")
    _wait_dest_epoch(node)
    fin = node.oracle_finalize_epoch(E2_TOPIC, target)
    print(f"[committee] __lyquor_oracle_finalize_epoch({E2_TOPIC}, {target}) -> {fin}")
    if not fin:
        raise RuntimeError("[committee] finalize_epoch returned false")
    print(f"[committee] e2_net_config after activate: {node.e2_net_config()}")

    # --- 4. 建争议单（主场景 = 证据派生 NotFulfilled：无交付） -----------
    alice, broker, bob = role_ids(node)

    def snapshot():
        return {"alice": node.balance_of(alice), "bob": node.balance_of(bob),
                "broker": node.balance_of(broker)}

    pre_tap = node.balance_of(alice)
    node.faucet(alice, 10_000)

    def faucet_landed():
        bal = node.balance_of(alice)
        if bal - pre_tap >= 10_000:
            return True, bal
        return False, bal  # 读路径滞后（pending），继续等

    tapped = wait_for(node, faucet_landed, timeout_s=15.0, interval_s=1.0,
                      what="faucet read-back")
    print(f"[committee] faucet read-back OK: alice {pre_tap} -> {tapped} (+{tapped - pre_tap})")
    before = snapshot()
    require_funds(node, alice, 1_000)
    deal_id, _ = new_assessed_deal(node, alice, broker, bob, amount=1_000)
    print(f"[committee] deal={deal_id} info={node.deal_info(deal_id)}")
    call(node, "fund", deal_id, sender=alice)
    funded = wait_state(node, deal_id, "Funded")
    after_fund = snapshot()
    print(f"[committee] deal={deal_id} state={funded['state']} "
          f"(deliverable_digest=None -> check_evidence_shape=false -> NotFulfilled)")
    reason = {"reason": "seller accepted escrow and never delivered"}
    reason_digest = hashlib.sha256(json.dumps(reason, sort_keys=True).encode()).hexdigest()
    notarize(node, deal_id, KIND_DISPUTE, reason, alice, bob)
    call(node, "open_dispute", deal_id, reason_digest, sender=alice)
    disputed = wait_state(node, deal_id, "Disputed")
    print(f"[committee] deal={deal_id} state={disputed['state']} "
          f"(evidence entries={len(node.evidence_entries(deal_id))})")

    # --- 5. arm（network 域单发全节点生效）+ 读回断言 + node1 单次回合 --
    # 读回纪律（仲裁修订 3）：e2_arm **只发一次**（plan §3.6-5「一次」），随后
    # 轮询 e2_net_config 至 armed_deal == deal_id（预算 ~15s）。armed_deal 为空
    # 或仍是 arm 前的旧值 = 读路径滞后（pending，继续等）；出现第三种值 = 硬失配，
    # 立即 abort——**绝不重复 e2_arm**。
    pre_arm = node.e2_net_config().get("armed_deal")
    node.e2_arm(deal_id)

    def arm_state():
        cfg_ = node.e2_net_config()
        armed = cfg_.get("armed_deal")
        if armed == deal_id:
            return True, cfg_
        if armed == pre_arm:
            return False, cfg_
        raise RuntimeError(
            f"[committee] arm mismatch (abort): e2_net_config.armed_deal={armed!r} "
            f"!= {deal_id!r} and != pre-arm {pre_arm!r} — refusing to re-arm "
            f"(plan §3.6-5: arm exactly once)")

    cfg = wait_for(node, arm_state, timeout_s=15.0, interval_s=1.0, what="arm read-back")
    print(f"[committee] e2_net_config after arm: {cfg}")
    print(f"[committee] arm read-back OK: armed_deal == {deal_id} (pre-arm={pre_arm!r})")
    round_ok = node.e2_run_verdict_round()
    print(f"[committee] e2_run_verdict_round() -> {round_ok} "
          f"(node1 single trigger; cast call channel — 禁多次触发)")
    if not round_ok:
        raise RuntimeError(
            "[committee] run_round returned false (oracle inactive or aggregate refused) — "
            "no certified call will land; inspect console before any retry")

    # --- 6. 终态读回 + 余额勾稽（NotFulfilled = 全额退款、misconduct 不增） --
    # 读回纪律（仲裁修订 3）：轮询至 Refunded，预算 ~30s（覆盖内层 certified call
    # 晚块上链 + 4 节点 validate 轮）。state 停在 Disputed = pending，继续等；
    # 出现其他终态（如 Settled）或超时才 abort——**绝不重触发 run_round**。
    def terminal_state():
        info = node.deal_info(deal_id)
        st = info.get("state")
        if st == "Refunded":
            return True, info
        if st == "Disputed":
            return False, info
        raise RuntimeError(
            f"[committee] unexpected state {st!r} (expected Refunded; Disputed=pending, "
            f"other state = abort; run_round is NOT retriggered)")

    final = wait_for(node, terminal_state, timeout_s=30.0, interval_s=1.0,
                     what="terminal Refunded")
    after = snapshot()
    print(f"[committee] final state={final['state']} balances after={after}")
    if final["state"] != "Refunded":
        raise RuntimeError(f"[committee] verdict did not reach Refunded: {final}")
    if not (after["alice"] == before["alice"] and after["bob"] == before["bob"]
            and after["broker"] == before["broker"]):
        raise RuntimeError(
            f"[committee] refund accounting mismatch: before={before} after_fund={after_fund} "
            f"after={after} (NotFulfilled must refund the buyer and leave seller/broker untouched)")
    print(f"[committee] refund check OK: alice {before['alice']} -> {after_fund['alice']} "
          f"(after fund) -> {after['alice']} (after verdict); bob/broker unchanged")

    # --- 7. console 取证段（取证源 = node1；实例名，不是地址） -----------
    console = shaker_console(instance)
    keys = ("e2_configure", "e2_net_config", "e2_arm", "e2_propose", "e2_aggregate",
            "e2_run_verdict_round", "committee_verdict_certified", "apply_verdict")
    lines = [ln.strip() for ln in console.stdout.splitlines() if any(k in ln for k in keys)]
    print(f"[committee] console evidence (source=node1, rc={console.returncode}, "
          f"{len(lines)} matching line(s)):")
    for ln in lines:
        print(f"  {ln}")
    if not lines:
        print("[committee] WARNING: no committee lines captured from console (replay window / relay); "
              "re-run manually:\n"
              f"  timeout 60 docker exec multi-tools shaker console {instance} "
              f"--endpoint ws://node1:10087/ws")

    banner("COMMITTEE FLOW SUMMARY")
    print(f"  instance  = {instance}")
    print(f"  contract  = {node.contract}")
    print(f"  target    = {target} (shaker to-hex; != contract)")
    print(f"  deal      = {deal_id} -> {final['state']}")
    print("  signers   = see committee_verdict_certified lines above "
          "(each must map to a real NodeID among committee_members)")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--node", default=DEFAULT_NODE, help="node base url, or 'sim'")
    p.add_argument("--sim", action="store_true", help="shorthand for --node sim")
    p.add_argument("--contract", default=None,
                   help="escrow Lyquid address (node mode; fallback = TB_CONTRACT)")
    p.add_argument("--instance", default=DEFAULT_INSTANCE,
                   help="Lyquid instance NAME (Lyquid-…); required for --flow committee "
                        "(shaker console/to-hex take the name, not the contract address)")
    p.add_argument("--flow", choices=["normal", "timeout", "adversarial", "committee", "all"],
                   default="all")
    p.add_argument("--selftest", action="store_true",
                   help="pin evidence_root/fnv1a64 to the core.rs vectors, then exit")
    args = p.parse_args()
    if args.sim:
        args.node = "sim"
    global INSTANCE
    INSTANCE = (args.instance or "").strip()

    if args.selftest:
        # Pure stdlib, before any node/LLM/network construction.
        selftest_evidence_root()
        sys.exit(0)

    if args.node == "sim":
        node = FakeNode()
        print("[demo] SIM MODE (FakeNode) — orchestration smoke only; deal semantics truth = rust core tests")
    else:
        node = NodeClient(args.node, contract=args.contract)
    # Both transports need the same committee config: the verdict gate checks
    # caller ∈ members ∧ caller ∈ signers, and FakeNode's default set does
    # not include the broker. Node mode configures the ADDRESS list: chain
    # identities are anvil addresses, and node-1..3 stay string placeholders
    # (members only — never called, they just fill the threshold).
    # R3（仲裁修订 1：fail-closed 门控）：--flow committee **跳过**本默认配置——
    # flow_committee 在 env/TARGET 断言之后才自行发 NodeID 制 committee_config
    # （plan §3.6「先断言后写」序）；已核它不依赖本地址制集（在建单前整表覆盖）。
    # FakeNode.committee_config 静默（rpc.py），故 sim 字面零变化（--flow all 仍走
    # 本分支；`--flow committee --sim` 仍由 flow_committee 的 node-only 检查退出）。
    # 修复前旧序会在 --instance 校验前先发一笔 committee_config tx（见 implementation.md §5-12）。
    if args.flow != "committee":
        committee = ([BROKER_ADDR] + COMMITTEE[1:]) if node_mode(node) else COMMITTEE
        node.committee_config(committee, THRESHOLD)

    flows = {"normal": flow_normal, "timeout": flow_timeout,
             "adversarial": flow_adversarial, "committee": flow_committee}
    if args.flow == "all":
        # R2 门控拆除：对抗流已上链，node 与 sim 的 all 序列一致。
        # R3：committee 流是 node-only 且带 oracle 配置/activation 副作用，
        # 不进 --flow all 序列（序列与全部 sim 代码路径零改动 = G2 逐字门前提）。
        seq = ["normal", "timeout", "adversarial"]
    else:
        seq = [args.flow]
    for name in seq:
        flows[name](node)

    banner("DEMO COMPLETE")


if __name__ == "__main__":
    main()
