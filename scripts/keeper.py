#!/usr/bin/env python3
"""TrustBridge keeper — the production timeout path (S1 verdict: native
triggers never fire on multi v0.8.1, so a watcher MUST submit claims).

Doctrine (matches lib.rs guards): keeper only SUBMITS `claim_timeout`;
the chain-side guard re-derives eligibility (Funded-only, deadline passed),
so polling early/often/duplicately is harmless — rejections are free.

Transport: `docker exec <tools-container> cast call/send --rpc-url <node-api>`
(the tools container has cast + intra-network reach to every node; this is the
channel proven in W1-A/W1-B1). Stdlib only.

Usage:
  python scripts/keeper.py --container multi-tools-1 \
      --rpc http://node1:10087/api --deals deal-1,deal-2 [--interval 20]

Exit: runs forever until Ctrl-C; every action is logged with timestamp.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time


def cast(container: str, rpc: str, mode: str, contract: str, sig: str, *args: str) -> str:
    """Run cast call/send inside the tools container; return raw stdout."""
    cmd = ["docker", "exec", container, "cast", mode, "--rpc-url", rpc, contract, sig, *args]
    if mode == "send":
        cmd += "--json"  # structured receipt; guard reverts return non-zero exit
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    out = (p.stdout or "") + (p.stderr or "")
    if p.returncode != 0 and mode == "call":
        raise RuntimeError(f"cast call failed ({p.returncode}): {out.strip()[:200]}")
    return out.strip()


def parse_cast_json(raw: str):
    """cast call output is plain text of the ABI-decoded value(s); deal_info is
    a single string return, so the value arrives as-is (no json wrapper)."""
    return raw


def deal_state(container: str, rpc: str, contract: str, deal_id: str):
    """deal_info(string) -> DealView JSON string (single string return)."""
    raw = cast(container, rpc, "call", contract, "deal_info(string)", deal_id)
    text = raw.strip()
    if text.startswith('"') and text.endswith('"'):
        text = json.loads(text)  # ABI string return: unquote
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}


def claim_timeout(container: str, rpc: str, contract: str, deal_id: str):
    """claim_timeout(string) — guard-side idempotent; revert = not eligible."""
    return cast(container, rpc, "send", contract, "claim_timeout(string)", deal_id)


def poll_once(container: str, rpc: str, contract: str, deals: list[str]) -> dict:
    report = {}
    for deal_id in deals:
        try:
            info = deal_state(container, rpc, contract, deal_id)
        except RuntimeError as e:
            report[deal_id] = {"error": str(e)}
            continue
        state = info.get("state", "?")
        if state in ("Settled", "Refunded"):
            report[deal_id] = {"state": state, "action": "terminal"}
            continue
        if state != "Funded":
            report[deal_id] = {"state": state, "action": "skip"}
            continue
        # Funded: attempt the claim every poll. The guard rejects until the
        # deadline; one success flips to Refunded and further sends revert.
        try:
            claim_timeout(container, rpc, contract, deal_id)
            after = deal_state(container, rpc, contract, deal_id)
            report[deal_id] = {"state": after.get("state", "?"), "action": "claimed"}
        except RuntimeError as e:
            report[deal_id] = {"state": state, "action": "not-due-or-reverted"}
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--container", default="multi-tools-1", help="tools container for docker exec")
    p.add_argument("--rpc", default="http://node1:10087/api", help="node API from the container's view")
    p.add_argument("--contract", required=True, help="escrow Lyquid contract address (0x...)")
    p.add_argument("--deals", required=True, help="comma-separated deal ids to watch")
    p.add_argument("--interval", type=int, default=20, help="poll interval seconds")
    args = p.parse_args()

    deals = [d.strip() for d in args.deals.split(",") if d.strip()]
    print(f"[keeper] container={args.container} rpc={args.rpc} contract={args.contract}")
    print(f"[keeper] watching {deals} every {args.interval}s (guard decides; submissions are free)")
    try:
        while True:
            ts = time.strftime("%H:%M:%S")
            for deal_id, r in poll_once(args.container, args.rpc, args.contract, deals).items():
                print(f"[keeper {ts}] {deal_id}: {json.dumps(r, ensure_ascii=False)}")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("[keeper] stopped")


if __name__ == "__main__":
    main()
