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
                               FakeNode, NodeClient)

ALICE, BROKER, BOB = "agent-alice", "agent-broker", "agent-bob"
# Committee: the nodes adjacent to the broker double as endorsement members
# (broker.py narrative), so BROKER itself sits on the set. The verdict gate
# requires caller ∈ members ∧ caller ∈ signers, so the demo submits the
# verdict under BROKER's identity with signers = COMMITTEE[:THRESHOLD].
COMMITTEE = [BROKER, "node-1", "node-2", "node-3"]
THRESHOLD = 3

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


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--node", default=DEFAULT_NODE, help="node base url, or 'sim'")
    p.add_argument("--sim", action="store_true", help="shorthand for --node sim")
    p.add_argument("--contract", default=None,
                   help="escrow Lyquid address (node mode; fallback = TB_CONTRACT)")
    p.add_argument("--flow", choices=["normal", "timeout", "adversarial", "all"], default="all")
    p.add_argument("--selftest", action="store_true",
                   help="pin evidence_root/fnv1a64 to the core.rs vectors, then exit")
    args = p.parse_args()
    if args.sim:
        args.node = "sim"

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
    committee = ([BROKER_ADDR] + COMMITTEE[1:]) if node_mode(node) else COMMITTEE
    node.committee_config(committee, THRESHOLD)

    flows = {"normal": flow_normal, "timeout": flow_timeout, "adversarial": flow_adversarial}
    if args.flow == "all":
        # R2 门控拆除：对抗流已上链，node 与 sim 的 all 序列一致。
        seq = ["normal", "timeout", "adversarial"]
    else:
        seq = [args.flow]
    for name in seq:
        flows[name](node)

    banner("DEMO COMPLETE")


if __name__ == "__main__":
    main()
