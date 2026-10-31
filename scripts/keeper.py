#!/usr/bin/env python3
"""TrustBridge keeper — the production timeout path (S1 verdict: native
triggers never fire on multi v0.8.1, so a watcher MUST submit claims).

Doctrine (matches lib.rs guards): keeper only SUBMITS `claim_timeout`;
the chain-side guard re-derives eligibility (Funded-only, deadline passed),
so polling early/often/duplicately is harmless — rejections are free, and a
second claim on a Refunded deal is rejected by the state guard (core.rs:171
require_states).

Transport (W1-B2 D2 decision gate, w1b2-s4-rpc.md §B-⑤): NodeClient over the
node's ETH JSON-RPC API —
  reads  = eth_call;
  writes = eth_sendTransaction with NO gas field (eth_estimateGas is unusable
           on lyquid contracts, §B-③④b, and unnecessary: the node auto-gasses),
           then eth_getTransactionReceipt polling until `status == "0x1"`.
The keeper calls `NodeClient._send` directly instead of the public
`claim_timeout` wrapper: the wrapper drops the receipt and always returns True
(rpc.py:578-584), while keeper needs the receipt's `transactionHash` for the
refunded evidence file. `_send` (rpc.py:464-485) already asserts status=="0x1".

Measured caveat carried over from rpc.py: status=="0x1" means SEQUENCED, not
method-Ok (a lyquid Err is swallowed by the platform, §A-1 note 3). Hence the
read-back check below: only `deal_info(deal_id).state == "Refunded"` counts as
a claim.

Dependency note (registered deviation): this script imports `agents/common`
(requests) instead of being stdlib-only. Decision D2 / §B-⑤ outranks the old
"cast inside docker exec" doctrine; the cast fallback stays documented in the
plan (R6) but is not the primary channel.

Usage:
  python scripts/keeper.py --node http://127.0.0.1:10087 \
      --contract 0x... [--deals deal-1,deal-2] [--interval 20] [--once] [--no-nudge]

`--deals` is OPTIONAL (R1 S4): without it the keeper enumerates the escrow
(deal-1 upward until the first gap, NodeClient.discover_deals — the same
discovery loop create_deal uses) at startup and prints the discovered list
(设计输入①). An explicit `--deals` keeps the R0 evidence-run behaviour
verbatim.

`--nudge` (default ON, `--no-nudge` to disable; 设计输入⑤): once per poll
round, if any watched deal is Funded, the keeper first sends a zero-value
faucet to itself — one automined block — then attempts the claims. Reason:
R0 relied on the operator nudging the chain externally; baking it in makes
the keeper's timeout path self-contained (the claim guard re-derives the
deadline from the block height, so the nudge cannot fake eligibility).

Exit: runs forever until Ctrl-C (every action logged with a timestamp);
`--once` runs a single round and exits — the evidence-run mode.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.common.rpc import DEFAULT_NODE, NodeClient, NodeError, TxError  # noqa: E402

# Read-after-write retry budget: the read path can lag one block behind the
# receipt (measured on the W1-B2 instance — the first deal_info read back after
# `fund` still said Qualified; w1b2-claim-probe-evidence.txt §4). NodeClient's
# own _poll_deal uses the same "consensus finality retry" idea (rpc.py:549-559).
READ_BACK_ATTEMPTS = 5
READ_BACK_DELAY_S = 0.4


def _read_back(node: NodeClient, deal_id: str) -> dict:
    """deal_info with a short finality-window retry (terminal state preferred)."""
    info = node.deal_info(deal_id)
    for _ in range(READ_BACK_ATTEMPTS - 1):
        if info.get("state") in ("Refunded", "Settled"):
            break
        time.sleep(READ_BACK_DELAY_S)
        info = node.deal_info(deal_id)
    return info


def poll_once(node: NodeClient, deals: list[str], nudge: bool = False) -> dict:
    """One polling round over `deals`; returns the per-deal report dict.

    `nudge`: at most one zero-value self-faucet per round, sent before the
    first claim attempt when a Funded deal is seen (设计输入⑤; the claim
    guard still re-derives the deadline on-chain)."""
    report = {}
    nudged = False
    for deal_id in deals:
        try:
            info = node.deal_info(deal_id)
        except NodeError as e:
            report[deal_id] = {"error": str(e)}
            continue
        state = info.get("state", "?")
        if state in ("Settled", "Refunded"):
            report[deal_id] = {"state": state, "action": "terminal"}
            continue
        if state != "Funded":
            report[deal_id] = {"state": state, "action": "skip"}
            continue
        if nudge and not nudged:
            try:
                node.nudge()
                nudged = True
                print("[keeper] nudge: zero-value faucet sent (one automined block)", flush=True)
            except (NodeError, TxError) as e:
                print(f"[keeper] nudge failed (continuing): {e}", flush=True)
        # Funded: attempt the claim every poll. The guard rejects until the
        # deadline; one success flips the deal to Refunded and further sends
        # are rejected by the terminal-state guard.
        try:
            receipt = node._send("claim_timeout(string)", (deal_id,))
        except (NodeError, TxError) as e:
            # Guard rejection (not due / not Funded) or transport failure.
            # Old keeper semantics kept for the common case: guard rejects are
            # free, the next poll retries.
            report[deal_id] = {"state": state, "action": "not-due-or-reverted", "error": str(e)}
            continue
        tx = receipt.get("transactionHash") if isinstance(receipt, dict) else None
        after = _read_back(node, deal_id)
        if after.get("state") == "Refunded":
            report[deal_id] = {"state": "Refunded", "action": "claimed", "tx": tx}
        else:
            # Receipt landed (status 0x1) but the state did not flip: the
            # platform swallowed a method Err (not due yet, or already
            # terminal on a re-read). Kept as the documented old action name.
            report[deal_id] = {"state": after.get("state", "?"), "action": "not-due-or-reverted", "tx": tx}
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--node", default=DEFAULT_NODE, help="node ETH JSON-RPC base URL (host view)")
    p.add_argument("--contract", required=True, help="escrow Lyquid contract address (0x...)")
    p.add_argument("--deals", default=None,
                   help="comma-separated deal ids to watch; default = enumerate the escrow")
    p.add_argument("--nudge", dest="nudge", action="store_true", default=True,
                   help="send one zero-value faucet per round when a deal is Funded (default)")
    p.add_argument("--no-nudge", dest="nudge", action="store_false",
                   help="disable the block-nudge (R0 external-nudge behaviour)")
    p.add_argument("--interval", type=int, default=20, help="poll interval seconds")
    p.add_argument("--once", action="store_true", help="run a single round and exit (evidence runs)")
    args = p.parse_args()
    # R5 P1-4 fail-closed: interval <= 0 busy-loops (sleep(0)) or crashes
    # (sleep of a negative), and an --deals string that parses to nothing
    # would silently watch an empty set — reject both at the gate.
    if args.interval <= 0:
        p.error("--interval must be >= 1 (0/negative would busy-loop or crash)")

    node = NodeClient(args.node, contract=args.contract)
    if args.deals:
        deals = [d.strip() for d in args.deals.split(",") if d.strip()]
        if not deals:
            p.error("--deals parsed to an empty list; nothing to watch")
        print(f"[keeper] explicit deals: {deals}")
    else:
        deals = node.discover_deals()
        print(f"[keeper] discovered deals: {deals} (source=discovered)")
    print(f"[keeper] node={args.node} contract={args.contract} sender={node.sender} nudge={args.nudge}")
    print(f"[keeper] watching {deals} every {args.interval}s (guard decides; submissions are free)")
    try:
        while True:
            ts = time.strftime("%H:%M:%S")
            for deal_id, r in poll_once(node, deals, nudge=args.nudge).items():
                print(f"[keeper {ts}] {deal_id}: {json.dumps(r, ensure_ascii=False)}", flush=True)
            if args.once:
                print("[keeper] --once: single round done")
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("[keeper] stopped")


if __name__ == "__main__":
    main()
