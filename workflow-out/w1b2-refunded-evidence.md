# W1-B2 T6 证据：keeper v2 实测 `claim_timeout` 退款成功（Funded → Refunded）

> 时间：2026-10-28（宿主 Git Bash + 宿主 python 3.14.5 / requests，NodeClient 通道）
> 实例：`Lyquid-xydh5ecomgg2rukd7qbw6gjv7cuf4uiktzbaa` @ `0xA4899D35897033b927acFCf422bc745916139776`
>      （Platform Version 0.8 / LDK 0.8.1；镜像 `sha256:45a96668ef47be1ac23a487bb1cb8d83c79eac2a49bb450a05b12590cc4c17e7`）
> 部署与探针佐证：`w1b2-claim-probe-evidence.txt`（实例、md5 自证、A~H 全阶段）
> 脚本：`scripts/keeper.py`（v2，写通道 = NodeClient `_send`，本轮持久保留）

## 1. claim 交易（tx hash + 回执）

keeper 输出（原文）：

```
[keeper 23:49:10] deal-1: {"state": "Refunded", "action": "claimed", "tx": "0x85e4e39b628a358ef7cd61bfc8c87e67a730c76617a823a6001a87ea86ae0838"}
```

`eth_getTransactionReceipt` 回执（宿主 curl，原文摘录）：

```
status      : 0x1
blockNumber : 104
from        : 0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266   （= anvil#0 = BROKER；claim_timeout 为 Access::Anyone，无需额外密钥）
to          : 0xa4899d35897033b927acfcf422bc745916139776
txHash      : 0x85e4e39b628a358ef7cd61bfc8c87e67a730c76617a823a6001a87ea86ae0838
gasUsed     : 35996
```

- tx 无 `gas` 字段（`eth_sendTransaction` 由节点自动注气；`eth_estimateGas` 对 lyquid
  合约不可用，w1b2-s4-rpc.md §B-③④b）。
- `status=0x1` 仅代表**已上序**（平台吞方法 Err，§A-1 教训）；成功判定以第 2、3 节读回为准。

## 2. `deal_info(deal-1)` 原始字面（含 `"state": "Refunded"`）

退款后（宿主 NodeClient，原文）：

```
{"id": "deal-1", "buyer": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266", "seller": "agent-bob", "amount": 1000, "state": "Refunded", "timeout_slots": 1, "deadline_slot": 102}
```

退款前（同一通道，T3 结束时）：

```
{"id": "deal-1", "buyer": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266", "seller": "agent-bob", "amount": 1000, "state": "Funded", "timeout_slots": 1, "deadline_slot": 102}
```

字面勾稽：`"state":"Funded"` → `"state":"Refunded"`；`deadline_slot=102`（funded_slot 101 + timeout_slots 1），
claim 发生于 block 104（104 ≥ 102，满足 `now >= deadline` 的边界语义，core.rs claim_timeout）。

## 3. `balance_of(#0)` 前后勾稽（+1000）

| 时点 | block | balance_of(0xf39F…92266) | 说明 |
|---|---|---|---|
| T3 结束后（退款前） | 103 | **999002** | faucet 1,000,000 − escrow 1000 + benign pokes 2 |
| T6 退款后 | 104 | **1000002** | = 999002 + 1000（full_refund，fee_bps 不参与退款） |

`1000002 − 999002 = 1000` 即 deal.amount（core::claim_timeout → `Payout::full_refund(1000)`；
apply_payout 的 `refund_to_buyer > 0` 分支入账）。与 T4 探针 F 阶段的
`F:payout=Ok(Payout{to_seller:0,fee_to_broker:0,refund_to_buyer:1000,slash_to_treasury:0})`
逐字段一致。

## 4. keeper 日志摘录（完整一轮）

```
$ python scripts/keeper.py --node http://127.0.0.1:10087 \
    --contract 0xA4899D35897033b927acFCf422bc745916139776 --deals deal-1 --interval 5 --once
[keeper] node=http://127.0.0.1:10087 contract=0xA4899D35897033b927acFCf422bc745916139776 sender=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
[keeper] watching ['deal-1'] every 5s (guard decides; submissions are free)
[keeper 23:49:10] deal-1: {"state": "Refunded", "action": "claimed", "tx": "0x85e4e39b628a358ef7cd61bfc8c87e67a730c76617a823a6001a87ea86ae0838"}
[keeper] --once: single round done
```

- `action=claimed` 只在**读回复核** `deal_info.state == "Refunded"` 时产生（status=1 ≠ 方法 Ok）；
  读回带 5×0.4s 终局延迟重试（T3 实测：fund 后首次读回仍为 Qualified）。
- keeper v2 传输层 = NodeClient：`_send`（eth_sendTransaction 无 gas + 回执轮询
  `status=="0x1"`）直取回执的 `transactionHash`，**未**走 rpc.py 的 `claim_timeout`
  公开封装（丢弃回执、恒返回 True，rpc.py:330-337）。rpc.py 本身未改。

## 5. 复现命令清单

```bash
# 0) 前提：multi 栈 Up；新实例已部署（Lyquid-xydh5… @ 0xA4899D…，见 w1b2-claim-probe-evidence.txt）
# 1) 造快过期 deal（faucet → create_deal(est_duration_ms=200 ⇒ timeout_slots=1) → fund；automine 需补 tx 造块）
python workflow-out/_w1b2_t3_replay.py 0xA4899D35897033b927acFCf422bc745916139776

# 2) 探针佐证（A~H，advisory now = 实读块高）
docker exec multi-tools cast call --rpc-url http://node1:10087/api \
  0xA4899D35897033b927acFCf422bc745916139776 \
  "probe_claim_sim(string,uint64) returns (string)" deal-1 <eth_blockNumber 实读值>

# 3) keeper 一轮退款（本轮实测命令）
python scripts/keeper.py --node http://127.0.0.1:10087 \
  --contract 0xA4899D35897033b927acFCf422bc745916139776 --deals deal-1 --interval 5 --once

# 4) 读回复核（宿主 python，NodeClient）
python -c "import sys; sys.path.insert(0, '.'); from agents.common.rpc import NodeClient, DEFAULT_SENDER; \
c=NodeClient('http://127.0.0.1:10087', contract='0xA4899D35897033b927acFCf422bc745916139776'); \
print(c.deal_info('deal-1')); print(c.balance_of(DEFAULT_SENDER))"
```

## 6. 幂等说明（重试安全）

Refunded 属终态：再次 `claim_timeout` 被 core 的 `require_states(Funded)` 拒绝
（core.rs:171），平台吞掉 Err、tx 仍上序但状态不变；keeper 的读回复核会记为
`not-due-or-reverted` 而不会误记 claimed。故重复轮询/重试无副作用。

## 7. 关联偏离（本轮登记）

- `assess_brief` 的 `export = eth` 已撤下（solc「Stack too deep」平台限制；与本退款链路无关，
  详见 `w1b2-claim-probe-evidence.txt` §2 与 `implementation.md` 偏离登记）。
- keeper 依赖面：`stdlib only` → 依赖 `agents/common`（requests），按 D2/§B-⑤ 决策门登记。
