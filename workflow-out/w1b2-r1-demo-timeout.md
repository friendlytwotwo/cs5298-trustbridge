# W1-B2 R1 · `demo.py --node` 门控演示 + 超时流证据（G5 门）

- 实例：`Lyquid-5h2kjsj3cbx2haipw6dzpd7cbe52z3seyfkaa` / `0x40918Ba7f132E0aCba2CE4de4c4baF9BD2D7D849`
- 日期：2026-10-29；原始日志：`_r1-demo-all-raw.txt`、`_r1-due-deals-raw.txt`、
  `_r1-keeper-raw.txt`、`_r1-keeper-nudge-raw.txt`、`_r1-final-state-raw.txt`
- 前置：同一实例上已先跑过一次 `--flow normal`（deal-1 Settled，见
  `w1b2-r1-demo-normal.md`），故本轮的 normal 流为 deal-2、超时流为 deal-3。

## §1 命令

```
$ python scripts/demo.py --node http://127.0.0.1:10087 \
    --contract 0x40918Ba7f132E0aCba2CE4de4c4baF9BD2D7D849 --flow all
```

## §2 运行原文（原样）

```
====================================================================
  adversarial: sim-only — apply_committee_verdict 不在 eth 导出面(plan R3)，对抗流请 --sim
====================================================================

====================================================================
  FLOW 1 — normal: assess -> escrow -> deliver -> settle
====================================================================
deal=deal-2 info={'id': 'deal-2', 'buyer': '0x70997970C51812dc3A010C7d01b50e0d17dc79C8', 'seller': '0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC', 'amount': 1000, 'state': 'Qualified', 'timeout_slots': 300, 'deadline_slot': None}
final state=Settled balances: alice=18000 bob=1960 broker=40

====================================================================
  FLOW 2 — timeout: seller stalls, watcher claims, buyer refunded
====================================================================
deal=deal-3 info={'id': 'deal-3', 'buyer': '0x70997970C51812dc3A010C7d01b50e0d17dc79C8', 'seller': '0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC', 'amount': 1000, 'state': 'Qualified', 'timeout_slots': 1, 'deadline_slot': None} (short-estimate create: est_ms=200)
deal=deal-3 deadline_slot=191 (timeout_slots=1)
nudge: block=190 deadline_slot=191 — nudging past it
  nudge -> block=191
  nudge -> block=192
watcher: discovered=['deal-1', 'deal-2', 'deal-3'] due=['deal-3']
final state=Refunded alice=19000 (made whole)

====================================================================
  DEMO COMPLETE
====================================================================
```

**门控三项**：

1. `--flow all` 下**只跑 normal + timeout 两流**（FLOW 3 未出现）。
2. 横幅字面：`adversarial: sim-only — apply_committee_verdict 不在 eth 导出面(plan R3)，对抗流请 --sim`。
3. 显式 `--flow adversarial`：

```
$ python scripts/demo.py --node http://127.0.0.1:10087 --flow adversarial
（同款横幅）
EXIT=2
```

## §3 超时流要素逐项

| 要素 | 实测值 | 说明 |
|---|---|---|
| 短估算建单 | `est_ms=200, est_conf=90` ⇒ `timeout_slots=1` | 方案登记的 demo 偏离：node 超时流不走 agent 侧 60s 评估（60000×2/400=300 slots 不可演示）；60s 路径由 normal 流覆盖（不受 deadline 约束） |
| fund 后 deadline | `deadline_slot=191`（紧接 fund 的打印为 `block=190`，即 funded_slot；191 = 190 + timeout_slots(1)） | 首读曾出现 `deadline_slot=None`（读滞后，见 §6）；已加 post-fund 读回重试 |
| nudge 轨迹 | `block=190 → 191 → 192`（两次零额 faucet 自送） | `NodeClient.nudge()`（设计输入⑤）：automine 下唯一可靠的时钟推进=落一笔交易 |
| 枚举 due | `discovered=['deal-1','deal-2','deal-3']`，`due=['deal-3']` | `NodeClient.discover_deals()` 从 deal-1 探测到首个缺口（设计输入① 枚举适配） |
| claim | `claim_timeout("deal-3")`（默认 sender #0，Anyone） | 守卫自行重算 now=192 ≥ 191 |
| 终态 | `state=="Refunded"` | §2 字面 + §4 eth_call 复核 |
| 余额勾稽 | alice `18000 → 19000`（**+1000**）；bob `1960`、broker `40` 不变 | 本流内：faucet +1000 − escrow 1000 + 退款 1000 ⇒ 净 **+1000** ✓ |

## §4 终态复核（eth_call 原文）

```
deal_info(deal-3) → {"id":"deal-3","buyer":"0x7099…79C8","seller":"0x3C44…93BC",
                     "amount":1000,"state":"Refunded","timeout_slots":1,"deadline_slot":191}
balance_of(#1 alice) = 19000
balance_of(#2 bob)   = 1960
balance_of(#0 broker)= 40
evidence_entries_json(deal-3) = []   （短估算直建未附 offer/request 公证，见 §5 偏离）
```

**G5 门满足：横幅字面 + `state=="Refunded"` 字面 + +1000 勾稽成立。**

## §5 偏离与登记

1. **短估算直建（demo 偏离）**：node 超时流不调用 `assess_brief`/`get_llm`，直接用
   `est_ms=200` 建单；因此 deal-3 的证据日志为空（没有 offer/request 公证）。正常流
   （deal-1/2）保留完整公证序列。
2. **nudge 而非真实时间流逝**：deadline 被"推块"追平，方向与真实运行一致（claim 守卫
   独立重算链上高度），不会伪造资格。
3. **#2 作为 sender 的结论（D6 结清）**：deal-3 的 buyer/seller 与所有写入均使用
   `#1/#0`；`#2` 的首次实证发生在正常流（`submit_deliverable` Seller 守卫 + 多条
   self-signed notarize，见 `w1b2-r1-demo-normal.md §4`）。**#2 作为 sender 可用**，无需
   R5 降级映射。

## §6 读通道滞后（本轮实测，登记）

- `fund` 返回后立即 `deal_info` 可能仍读 `Qualified`/`deadline_slot=None`（R0 已见，
  本轮首次 `--flow all` 于 block 163 复现并中断）；`complete` 后立即读也可能读到前态。
- 处置（方案 R7）：demo 增加 keeper 同款读回重试 —— `read_back()`（终态 5×0.4s）与
  `read_back_funded()`（等 Funded + deadline 可见）。§2 的终态与 deadline 均为重试后读数。

## §7 `due_deals` wire 面实测附录（D9 收口）

```
$ curl -s -X POST http://127.0.0.1:10087/api -H 'content-type: application/json' \
    --data '{"jsonrpc":"2.0","id":1,"method":"eth_blockNumber","params":[]}'
{"jsonrpc":"2.0","id":1,"result":"0xc1"}          # block 193

$ docker exec multi-tools cast call --rpc-url http://node1:10087/api 0x40918Ba7…D7D849 \
    "due_deals(uint64) returns (string[])" 195
[]

$ docker exec multi-tools cast call --rpc-url http://node1:10087/api 0x40918Ba7…D7D849 \
    "due_deals(uint64) returns (string[])" 191
[]

$ python -c "…NodeClient.due_deals()…"
due_deals()      : []
```

结论：**wire 面可路由**，返回合法 ABI `string[]`（全终态实例上为空）；D9 记录的
`FuncNotFound` 未复现。语义仍只列"Funded 且 now ≥ deadline"的 deal（advisory-only），
因此 demo/keeper 的枚举走 `discover_deals()`（deal-1 起探测首个缺口），`due_deals` 仅
作读通面备查。`agents/common/rpc.py` 的 `due_deals` docstring 已补该实测注记。

## §8 keeper 面冒烟（T2 改动验证，非门）

```
$ python scripts/keeper.py --node … --contract 0x4091…D849 --once
[keeper] discovered deals: ['deal-1', 'deal-2', 'deal-3'] (source=discovered)
… deal-1/2: {"state": "Settled", "action": "terminal"}; deal-3: {"state": "Refunded", "action": "terminal"}

$ python scripts/keeper.py --node … --contract 0x4091…D849 --deals deal-3 --once --no-nudge
[keeper] explicit deals: ['deal-3'] … {"state": "Refunded", "action": "terminal"}
```

nudge 分支单独实证（临时建 deal-4 `timeout_slots=300` → fund → keeper 单轮 → cancel 回收）：

```
[keeper] nudge: zero-value faucet sent (one automined block)
[keeper 21:59:43] deal-4: {"state": "Funded", "action": "not-due-or-reverted", "tx": "0x6def3da2…17e0"}
after cancel {'id': 'deal-4', …, 'state': 'Refunded', 'timeout_slots': 300, 'deadline_slot': 495}
```

⇒ 发现式枚举、`--deals` 显式路径、nudge 开关、未到期 claim 被守卫拒绝（平台吞 Err、
status 仍 0x1）四条行为与 rpc.py 文档口径一致。deal-4 已 cancel 回收，实例终态为
deal-1/2 Settled、deal-3/4 Refunded。
