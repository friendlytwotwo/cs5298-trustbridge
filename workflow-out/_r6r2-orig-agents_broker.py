#!/usr/bin/env python3
"""Agent B — the broker/middleman agent.

Runs the LLM assessment (pluggable; ScriptedLLM by default) and creates the
on-chain deal with an ESTIMATE-DERIVED timeout — the two-step pattern:
instance-side inference, network-side commit. In the full story agent B is
operated next to a Lyquor node that also sits in the endorsement committee.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys

sys.path.insert(0, ".")

from agents.common.llm import build_assessor_prompt, get_llm
from agents.common.protocol import (KIND_ASSESSMENT, KIND_REQUEST, Assessment, envelope, digest)
from agents.common.rpc import DEFAULT_NODE, FakeNode, NodeClient

AGENT_ID = "agent-broker"
FEE_BPS = 200  # 2% broker fee on settlement


def assess(brief: dict):
    llm = get_llm()
    raw = llm.complete_json(build_assessor_prompt(brief))
    rep = json.loads(raw)
    a = Assessment(**{k: rep[k] for k in ("qualification_score", "est_duration_ms", "est_confidence")})
    a.risks = rep.get("risks", [])
    print(f"[broker] assessment score={a.qualification_score} est_p90={a.est_duration_ms}ms conf={a.est_confidence}")
    return a


def create_deal(node, buyer: str, seller: str, amount: int, a: Assessment, terms: dict) -> str:
    terms_digest = hashlib.sha256(json.dumps(terms, sort_keys=True).encode()).hexdigest()
    acceptance = {"of": terms_digest, "check": "deliverable matches license terms; evidence trace complete"}
    acceptance_digest = hashlib.sha256(json.dumps(acceptance, sort_keys=True).encode()).hexdigest()
    deal_id = node.create_deal(buyer, seller, amount, FEE_BPS, terms_digest, acceptance_digest,
                               a.est_duration_ms, a.est_confidence)
    env = envelope(KIND_ASSESSMENT, {"score": a.qualification_score, "est_ms": a.est_duration_ms},
                   AGENT_ID, buyer, deal_id)
    print(f"[broker] deal created {deal_id} (timeout from est: {a.est_duration_ms}ms p90)")
    node.notarize(deal_id, AGENT_ID, buyer, digest(env))
    return deal_id


def request_seller(node, deal_id: str, terms_digest: str, amount: int, timeout_slots: int):
    env = envelope(KIND_REQUEST, {"amount": amount, "terms": terms_digest, "timeout_slots": timeout_slots},
                   AGENT_ID, "agent-bob", deal_id)
    node.notarize(deal_id, AGENT_ID, "agent-bob", digest(env))
    print(f"[broker] request sent to seller (notarized)")


def setup_committee(node, members=None, threshold=3):
    members = members or ["node-1", "node-2", "node-3", "node-4"]
    node.committee_config(members, threshold)
    print(f"[broker] committee configured: {len(members)} members, threshold {threshold}")


def main():
    p = argparse.ArgumentParser(description="Agent B (broker)")
    p.add_argument("--node", default=DEFAULT_NODE)
    p.add_argument("--sim", action="store_true")
    p.add_argument("--buyer", default="agent-alice")
    p.add_argument("--seller", default="agent-bob")
    p.add_argument("--amount", type=int, default=1_000)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("assess")
    sub.add_parser("committee")
    s = sub.add_parser("deal"); s.add_argument("--terms", default="license:song:online-video,12mo,EU")
    args = p.parse_args()

    node: NodeClient | FakeNode = FakeNode() if (args.sim or args.node == "sim") else NodeClient(args.node)

    if args.cmd == "assess":
        assess({"buyer": args.buyer, "seller": args.seller, "amount": args.amount})
    elif args.cmd == "committee":
        setup_committee(node)
    elif args.cmd == "deal":
        brief = {"buyer": args.buyer, "seller": args.seller, "amount": args.amount}
        a = assess(brief)
        terms = {"terms": args.terms, "amount": args.amount}
        deal_id = create_deal(node, args.buyer, args.seller, args.amount, a, terms)
        info = node.deal_info(deal_id)
        request_seller(node, deal_id, hashlib.sha256(json.dumps(terms, sort_keys=True).encode()).hexdigest(),
                       args.amount, info["timeout_slots"])


if __name__ == "__main__":
    main()
