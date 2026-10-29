"""W1-B2 T3: replay a fast-expiring deal on the new instance (host NodeClient).

Plan §5 T3: faucet -> create_deal(est_duration_ms=200 => timeout_slots=1) ->
fund -> wait until block height > deadline_slot (automine needs a benign tx).

Prints every read-back so the transcript can be archived as evidence.
"""
import json
import sys
import time

sys.path.insert(0, r"F:\canvus auto\downloads\202609CS5298\trustbridge")

from agents.common.rpc import DEFAULT_SENDER, NodeClient  # noqa: E402

CONTRACT = sys.argv[1] if len(sys.argv) > 1 else "0xA4899D35897033b927acFCf422bc745916139776"
c = NodeClient("http://127.0.0.1:10087", contract=CONTRACT)

print("== T3 start ==")
print("contract          :", CONTRACT)
print("sender/broker/buyer:", DEFAULT_SENDER)
print("[0] block_number  :", c.block_number())
print("[0] balance_of #0 :", c.balance_of(DEFAULT_SENDER))

c.faucet(DEFAULT_SENDER, 1_000_000)
print("[1] faucet(#0, 1000000) ok")
print("[1] balance_of #0 :", c.balance_of(DEFAULT_SENDER))

deal_id = c.create_deal(
    DEFAULT_SENDER, "agent-bob", 1000, 200,
    "terms-digest-w1b2-t3", "accept-digest-w1b2-t3", 200, 90,
)
info = c.deal_info(deal_id)
print("[2] create_deal ->", deal_id, json.dumps(info, ensure_ascii=False))
print("[2] balance_of #0 :", c.balance_of(DEFAULT_SENDER))

c.fund(deal_id)
info = c.deal_info(deal_id)
print("[3] fund ->", json.dumps(info, ensure_ascii=False))
print("[3] balance_of #0 :", c.balance_of(DEFAULT_SENDER), "(faucet 1000000 - escrow 1000)")
print("[3] block_number  :", c.block_number())

deadline = info.get("deadline_slot")
print("[3] deadline_slot :", deadline)

# automine: blocks only advance on txs. Poll a few times, then poke with a
# benign faucet (plan R3 mitigation) until block > deadline.
for i in range(6):
    bn = c.block_number()
    if deadline is not None and bn > deadline:
        break
    time.sleep(2)
    if i == 2:
        c.faucet(DEFAULT_SENDER, 1)
        print("[4] benign faucet(#0, 1) to advance the chain")

info = c.deal_info(deal_id)
bn = c.block_number()
print("[4] final block   :", bn)
print("[4] deal_info     :", json.dumps(info, ensure_ascii=False))
print("[4] G3 gate       :", "PASS" if info.get("state") == "Funded" and deadline is not None and bn > deadline else "FAIL")
print("== T3 end ==")
