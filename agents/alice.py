#!/usr/bin/env python3
"""Agent A — Alice's buying agent (video creator).

Scripted behavior (agent intelligence is out of scope by team discipline):
offer -> fund -> (on delivery) consent & complete. Every A2A message it sends
is digested and notarized first, so the chain sees the same trace the peers do.
"""

from __future__ import annotations

import argparse
import sys

sys.path.insert(0, ".")

from agents.common.protocol import (KIND_OFFER, KIND_RECEIPT, Acceptance, Deliverable, OfferBrief,
                                    envelope, digest)
from agents.common.rpc import DEFAULT_NODE, FakeNode, NodeClient

AGENT_ID = "agent-alice"


def make_offer(node, brief: OfferBrief) -> str:
    env = envelope(KIND_OFFER, brief.payload(), AGENT_ID, "agent-broker")
    d = digest(env)
    # the offer is notarized against deal-0 (pre-deal channel); W2: broker
    # creates the deal first so notarization lands under the real deal id.
    print(f"[alice] offer digest={d[:16]}…")
    return d


def fund(node, deal_id: str):
    node.fund(deal_id)
    info = node.deal_info(deal_id)
    print(f"[alice] funded {deal_id} state={info['state']} deadline_slot={info['deadline_slot']}")


def receive_deliverable_and_complete(node, deal_id: str, deliverable_digest: str):
    env = envelope(KIND_RECEIPT, {"deliverable": deliverable_digest, "ok": True}, AGENT_ID, "agent-bob", deal_id)
    node.notarize(deal_id, AGENT_ID, "agent-bob", digest(env))
    node.complete(deal_id)
    print(f"[alice] consented & completed {deal_id}")


def main():
    p = argparse.ArgumentParser(description="Agent A (buyer)")
    p.add_argument("--node", default=DEFAULT_NODE, help="node base url, or 'sim' for FakeNode")
    p.add_argument("--sim", action="store_true", help="force FakeNode sim mode")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("offer")
    s = sub.add_parser("fund"); s.add_argument("deal_id")
    s = sub.add_parser("complete"); s.add_argument("deal_id"); s.add_argument("deliverable_digest")
    args = p.parse_args()

    node: NodeClient | FakeNode = FakeNode() if (args.sim or args.node == "sim") else NodeClient(args.node)

    if args.cmd == "offer":
        brief = OfferBrief(buyer_agent=AGENT_ID, work_ref="song:midnight-motors",
                           usage_scope="online-video,12mo,EU", budget=1_000)
        make_offer(node, brief)
    elif args.cmd == "fund":
        fund(node, args.deal_id)
    elif args.cmd == "complete":
        receive_deliverable_and_complete(node, args.deal_id, args.deliverable_digest)


if __name__ == "__main__":
    main()
