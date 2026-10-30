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
  * flow gating: --flow all => normal+timeout only; the adversarial flow needs
    apply_committee_verdict, which is NOT on the eth export face (plan R3) —
    --flow adversarial prints the sim-only banner and exits 2;
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

ADVERSARIAL_BANNER = (
    "adversarial: sim-only — apply_committee_verdict 不在 eth 导出面(plan R3)，对抗流请 --sim")

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
    """broker: LLM assessment -> create_deal (two-step pattern)."""
    llm = get_llm()
    rep = json.loads(llm.complete_json(build_assessor_prompt(
        {"buyer": alice, "seller": bob, "amount": amount})))
    terms_digest, acceptance_digest = terms_digests(amount)
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
        if args.flow in ("all", "adversarial"):
            # flow 门控（设计输入④）：对抗流需要 apply_committee_verdict，而它不在
            # eth 导出面（R3 结构体参数）——node 模式只跑 normal+timeout。
            banner(ADVERSARIAL_BANNER)
        if args.flow == "adversarial":
            sys.exit(2)
        node = NodeClient(args.node, contract=args.contract)
    # Both transports need the same committee config: the verdict gate checks
    # caller ∈ members ∧ caller ∈ signers, and FakeNode's default set does
    # not include the broker.
    node.committee_config(COMMITTEE, THRESHOLD)

    flows = {"normal": flow_normal, "timeout": flow_timeout, "adversarial": flow_adversarial}
    if args.flow == "all":
        seq = ["normal", "timeout"] if node_mode(node) else ["normal", "timeout", "adversarial"]
    else:
        seq = [args.flow]
    for name in seq:
        flows[name](node)

    banner("DEMO COMPLETE")


if __name__ == "__main__":
    main()
