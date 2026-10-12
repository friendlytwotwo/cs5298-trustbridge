#!/usr/bin/env python3
"""Agent C — Bob's selling agent (rights holder).

Accepts the broker's request (notarized proof-of-agreement), then delivers:
produces the license grant document, notarizes the delivery message, and
submits the deliverable digest on-chain before the deadline.
"""

from __future__ import annotations

import argparse
import hashlib
import sys

sys.path.insert(0, ".")

from agents.common.protocol import KIND_ACCEPTANCE, KIND_DELIVERABLE, envelope, digest
from agents.common.rpc import DEFAULT_NODE, FakeNode, NodeClient

AGENT_ID = "agent-bob"


def accept(node, deal_id: str, terms_digest: str):
    env = envelope(KIND_ACCEPTANCE, {"terms": terms_digest, "accepted": True}, AGENT_ID, "agent-broker", deal_id)
    node.notarize(deal_id, AGENT_ID, "agent-broker", digest(env))
    print(f"[bob] accepted {deal_id} (notarized PoA)")


def deliver(node, deal_id: str, license_doc: str) -> str:
    doc_digest = hashlib.sha256(license_doc.encode()).hexdigest()
    env = envelope(KIND_DELIVERABLE, {"license_doc_sha256": doc_digest}, AGENT_ID, "agent-alice", deal_id)
    node.notarize(deal_id, AGENT_ID, "agent-alice", digest(env))
    node.submit_deliverable(deal_id, doc_digest)
    print(f"[bob] delivered {deal_id} doc_digest={doc_digest[:16]}…")
    return doc_digest


def main():
    p = argparse.ArgumentParser(description="Agent C (seller)")
    p.add_argument("--node", default=DEFAULT_NODE)
    p.add_argument("--sim", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("accept"); s.add_argument("deal_id"); s.add_argument("terms_digest")
    s = sub.add_parser("deliver"); s.add_argument("deal_id"); s.add_argument("license_doc", nargs="?", default="LICENSE:grant")
    args = p.parse_args()

    node: NodeClient | FakeNode = FakeNode() if (args.sim or args.node == "sim") else NodeClient(args.node)

    if args.cmd == "accept":
        accept(node, args.deal_id, args.terms_digest)
    elif args.cmd == "deliver":
        deliver(node, args.deal_id, args.license_doc)


if __name__ == "__main__":
    main()
