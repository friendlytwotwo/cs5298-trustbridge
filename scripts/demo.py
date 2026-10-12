#!/usr/bin/env python3
"""TrustBridge demo orchestration: normal / timeout / adversarial flows.

Two modes:
  --sim (default) FakeNode in-process smoke of the ORCHESTRATION only.
                 Deal semantics truth = Rust core + tests; FakeNode mirrors.
  --node URL     drive the real devnet via NodeClient (after SPIKE W1-4).

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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.common.llm import build_assessor_prompt, get_llm
from agents.common.protocol import (KIND_ACCEPTANCE, KIND_DELIVERABLE, KIND_DISPUTE, KIND_OFFER,
                                    KIND_RECEIPT, KIND_REQUEST, envelope, digest)
from agents.common.rpc import DEFAULT_NODE, SLOT_MS, FakeNode, NodeClient

ALICE, BROKER, BOB = "agent-alice", "agent-broker", "agent-bob"
COMMITTEE = ["node-1", "node-2", "node-3", "node-4"]
THRESHOLD = 3


def banner(t: str):
    print("\n" + "=" * 68 + f"\n  {t}\n" + "=" * 68)


def notarize(node, deal_id, kind, payload, frm, to):
    env = envelope(kind, payload, frm, to, deal_id)
    d = digest(env)
    seq = node.notarize(deal_id, frm, to, d)
    return seq, d


def new_assessed_deal(node, amount=1_000):
    """broker: LLM assessment -> create_deal (two-step pattern)."""
    llm = get_llm()
    rep = json.loads(llm.complete_json(build_assessor_prompt(
        {"buyer": ALICE, "seller": BOB, "amount": amount})))
    terms = {"terms": "license:song:midnight-motors:online-video,12mo,EU", "amount": amount}
    terms_digest = hashlib.sha256(json.dumps(terms, sort_keys=True).encode()).hexdigest()
    acceptance = {"of": terms_digest, "check": "deliverable matches license terms"}
    acceptance_digest = hashlib.sha256(json.dumps(acceptance, sort_keys=True).encode()).hexdigest()
    deal_id = node.create_deal(ALICE, BOB, amount, 200, terms_digest, acceptance_digest,
                               rep["est_duration_ms"], rep["est_confidence"])
    notarize(node, deal_id, KIND_OFFER, {"budget": amount}, ALICE, BROKER)
    notarize(node, deal_id, KIND_REQUEST, {"amount": amount, "terms": terms_digest}, BROKER, BOB)
    return deal_id, terms_digest


def flow_normal(node):
    banner("FLOW 1 — normal: assess -> escrow -> deliver -> settle")
    node.faucet(ALICE, 10_000)
    deal_id, terms_digest = new_assessed_deal(node)
    print(f"deal={deal_id} info={node.deal_info(deal_id)}")

    node.fund(deal_id)
    notarize(node, deal_id, KIND_ACCEPTANCE, {"terms": terms_digest, "accepted": True}, BOB, BROKER)
    license_doc = "LICENSE-DOC: grant of song 'midnight-motors' to alice, online-video,12mo,EU"
    doc_digest = hashlib.sha256(license_doc.encode()).hexdigest()
    notarize(node, deal_id, KIND_DELIVERABLE, {"license_doc_sha256": doc_digest}, BOB, ALICE)
    node.submit_deliverable(deal_id, doc_digest)
    notarize(node, deal_id, KIND_RECEIPT, {"ok": True}, ALICE, BOB)
    node.complete(deal_id)

    print(f"final state={node.deal_info(deal_id)['state']} "
          f"balances: alice={node.balance_of(ALICE)} bob={node.balance_of(BOB)} broker={node.balance_of(BROKER)}")


def flow_timeout(node):
    banner("FLOW 2 — timeout: seller stalls, watcher claims, buyer refunded")
    node.faucet(ALICE, 1_000)
    deal_id, _ = new_assessed_deal(node, amount=1_000)
    node.fund(deal_id)
    info = node.deal_info(deal_id)
    print(f"deal={deal_id} deadline_slot={info['deadline_slot']} (timeout_slots={info['timeout_slots']})")

    # seller stalls; time passes; watcher (any node / keeper) polls and claims.
    # tick() only exists on FakeNode — against a real node, wall-clock time
    # advances by itself and the keeper (W2) submits the claims.
    if hasattr(node, "tick"):
        node.tick(info["timeout_slots"] + 1)
    due = node.due_deals()
    print(f"watcher: due_deals={due}")
    for d in due:
        node.claim_timeout(d)

    print(f"final state={node.deal_info(deal_id)['state']} alice={node.balance_of(ALICE)} (made whole)")


def flow_adversarial(node):
    banner("FLOW 3 — adversarial: forged deliverable -> dispute -> committee Malicious verdict")
    node.faucet(ALICE, 1_000)
    deal_id, _ = new_assessed_deal(node, amount=1_000)
    node.fund(deal_id)

    forged = "FORGED-LICENSE-DOC: copied template, wrong scope"
    forged_digest = hashlib.sha256(forged.encode()).hexdigest()
    node.submit_deliverable(deal_id, forged_digest)

    reason = {"reason": "deliverable does not match agreed terms"}
    reason_digest = hashlib.sha256(json.dumps(reason, sort_keys=True).encode()).hexdigest()
    notarize(node, deal_id, KIND_DISPUTE, reason, ALICE, BOB)
    node.open_dispute(deal_id, reason_digest)

    # committee: 3 of 4 members inspected the evidence log -> Malicious
    signers = COMMITTEE[:THRESHOLD]
    node.apply_committee_verdict(deal_id, 2, signers)

    print(f"final state={node.deal_info(deal_id)['state']} alice={node.balance_of(ALICE)} "
          f"misconduct={getattr(node, 'misconduct', {})}")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--node", default=DEFAULT_NODE, help="node base url, or 'sim'")
    p.add_argument("--sim", action="store_true", help="shorthand for --node sim")
    p.add_argument("--flow", choices=["normal", "timeout", "adversarial", "all"], default="all")
    args = p.parse_args()
    if args.sim:
        args.node = "sim"

    if args.node == "sim":
        node = FakeNode()
        print("[demo] SIM MODE (FakeNode) — orchestration smoke only; deal semantics truth = rust core tests")
    else:
        node = NodeClient(args.node)
        node.committee_config(COMMITTEE, THRESHOLD)

    flows = {"normal": flow_normal, "timeout": flow_timeout, "adversarial": flow_adversarial}
    seq = ["normal", "timeout", "adversarial"] if args.flow == "all" else [args.flow]
    for name in seq:
        flows[name](node)

    banner("DEMO COMPLETE")


if __name__ == "__main__":
    main()
