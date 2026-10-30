# R2 目标 A 证据：keeper 循环驱动超时流 + `due_deals` 非空

> 实例：`Lyquid-tldda6zqdhab2kdysepcqxx73uvm3sxz7wbaa` @
> `0xFD6F7A6a5c21A3f503EBaE7a473639974379c351`（R2 新实例；R1 实例 `0x4091…D849`
> 全程只读不动，收尾复核仍为 broker=40）。
> 原始日志：`_r2-due-nonempty-raw.txt`（deal X + Y 建单/注资/取证）、
> `_r2-keeper-loop-raw.txt`（keeper transcript + 块扫描归因 + 收尾）。
> 采集时间 2026-10-29 23:38–23:40。`scripts/keeper.py` 本轮**零改动**。

---

## §1 命令原文

```
# 1) deal X（due_deals 取证专用）+ deal Y（keeper 驱动专用）由外层驱动脚本建立：
#    同一 python heredoc 驱动 agents/common/rpc.py NodeClient（R1 §2 T5-3 同款手法）
$ python - <<'EOF'
    node.faucet(ALICE_ADDR, 10_000)
    ... create_deal(est_ms=200) / 余额断言 / fund / 读回 deadline / nudge 过 deadline / due_deals ...
EOF
# 2) keeper 循环（不是 --once），显式只盯 deal-3，默认 nudge：
$ python scripts/keeper.py --node http://127.0.0.1:10087 \
      --contract 0xFD6F7A6a5c21A3f503EBaE7a473639974379c351 --deals deal-3 --interval 5
# 3) 读回 Refunded 后停 keeper，再对 (start_block, end_block] 逐块扫描归因
```

`--deals` 显式给出是**归因隔离的必要条件**：缺省会走 `keeper.py:154` 的
`discover_deals`，把 deal X 也枚举进去并在首轮先 claim X，其交易先产块会污染 Y 的
窗口（方案 §5 T6-A 步 3 / R6）。

## §2 六要素表（方案 §5 T6-A 步 6 / G6A）

| # | 要素 | 证据（原文摘录） | 出处 |
|---|---|---|---|
| 1 | 循环模式（非单发） | 同一 keeper 进程连续三轮：`[keeper 23:39:22]`、`[keeper 23:39:28]`、`[keeper 23:39:38]` | `_r2-keeper-loop-raw.txt` |
| 2 | 显式 deals | `[keeper] explicit deals: ['deal-3']` | 同上 |
| 3 | nudge 产块 | `[keeper] nudge: zero-value faucet sent (one automined block)` | 同上 |
| 4 | 自动 claim | `deal-3: {"state": "Refunded", "action": "claimed", "tx": "0x4095005c0e72c139fb99f630d8e20b7ef005596a88dfac8b1fec8717cd5ada02"}` | 同上 |
| 5 | Refunded + 余额复核 | `deal-3 info: … 'state': 'Refunded', 'timeout_slots': 1, 'deadline_slot': 213`；`alice 18000->19000`（全额回流） | 同上（final read-back 段） |
| 6 | 块号/deadline 归因段 | 见 §4 块扫描表 | 同上（block-scan 段） |
| 附 | `due_deals` 非空（deal X） | 见 §3 | `_r2-due-nonempty-raw.txt` |

## §3 `due_deals` 非空（deal X = deal-2，R1 §4 遗留项关闭）

```
block_number at start = 207
funds gate(X): balance_of(alice) = 20000 >= 1000  OK
deal X = deal-2 (est_ms=200 -> timeout_slots=1)
deal X after fund: state=Funded deadline_slot=210 timeout_slots=1
due_deals BEFORE crossing the deadline: block=209 deadline=210 -> []
  nudge -> block=210
due_deals AFTER crossing the deadline: block=210 deadline=210 -> ['deal-2']
RESULT: due_deals non-empty, contains deal X = deal-2  (now=210 >= deadline=210)
```

**产块后重读纪律**：过 deadline 前读回 `[]`、nudge 产块后重读得到 `['deal-2']`——
两次读都用同一 `now`（当前块高），差别只来自块高跨越 deadline。

**资金登记**：deal X 托管锁定 1_000；本臂预算 = faucet 10_000 ≥ X 1_000 + Y 1_000 +
余量。X 取证后**留置不 claim**，其收尾（`claim_timeout`，alice 发送）在 keeper 归因窗口
**关闭之后**执行：`deal-2 after claim_timeout: state=Refunded alice 19000->20000`。

**解码缺陷登记（本轮新发现并修复）**：`due_deals` 的**首个非空返回**暴露了
`rpc.py _decode_ret("string[]")` 的元素偏移口径错误（相对数组基址，正确应为相对长度字
之后的 tail = base+32）；R1 只见过空数组故未暴露。同一轮还发现 `_enc_value("string[]")`
有同源相反方向的错误（见 `w1b2-r2-adversarial.md` §5）。修复后 `due_deals` 非空返回
与标准 ABI 一致，实测原文已入档：

```
due_deals raw return: 0x…0020 | 0000…0001 | 0000…0020 | 0000…0006 | "deal-2"…
  word[0]=0x20 (array offset) word[1]=1 (len) word[2]=0x20 (element offset, rel. tail)
  word[3]=0x06 (string len)  word[4]=6465616c2d32… ("deal-2")
```

## §4 块号 / deadline 归因（块扫描，方案 §5 T6-A 步 5 a–d）

**探针（步 5a）**：`eth_getBlockByNumber("latest", true)` 返回**含 `input` 的完整 tx
对象**（`probe tx keys = ['accessList','blockHash',…,'from','gas','hash','input',…]`），
无需退化路线。

**窗口**：`start_block = 212`（含 fund(Y) 的块，窗口外）；`end_block = 214`
（Refunded 读回时的块高）。归因窗口 = `(212, 214]`。

| 块 | from | selector | 归属 | tx hash |
|---|---|---|---|---|
| 212（窗口外，fund Y） | `0x7099…79C8`（alice） | `0x73451f65` fund | 操作者 | `0xf7d14de7…ec3c` |
| 213 | `0xf39F…92266` | `0xb540def8` faucet(nudge) | **keeper** | `0x79615ea0…ccbc` |
| 214 | `0xf39F…92266` | `0x786cfc8f` claim_timeout | **keeper** | `0x4095005c…da02` |

**判据与结论**：窗口内每块恰一笔 tx，且两笔全属 keeper sender + 两个 keeper selector
（automine 一 tx 一块，P6）⇒ 自 keeper 启动至 Refunded 的产块**全部来自 keeper 自身
交易**，期间无操作者交易；跨过 deal-3 deadline（213）的那一块就是 keeper 的 nudge 交易
本身，「循环驱动过 deadline」归因成立。

**deadline 归因**：`deal Y after fund: state=Funded deadline_slot=213 timeout_slots=1`；
nudge 产块到 213（= deadline），同轮 claim 在 214 落块，guard 语义 `now >= deadline`
（`core.rs:173-174`）放行。

**窗口关闭顺序（步 5d）**：扫描在 deal X 的收尾动作之前完成（§3 的
`claim_timeout(deal-2)` 在扫描之后、block 273 之前执行），操作者交易未落入窗口。

## §5 偏离登记

1. **`_decode_ret("string[]")` 修正**（超出方案 §6-2 的名义改动面，但为 T6-A 取证所必需）：
   见 §3。改动仅解码逻辑，不涉 selector/编码/调用面。
2. **attempt 1 的 deal-1 作废**：首次取证时因上述解码缺陷读回 32 字节零串而断言失败，
   该 deal 已在 block 207 用 `claim_timeout` 回收（`state=Refunded`，1_000 全额回流），
   未进入 keeper 窗口；正式取证改用 deal-2（X）/deal-3（Y）。
3. **读通道终局滞后再次命中**：`claim_timeout` 后首次 `deal_info` 仍显示旧态，5×0.4s
   重试后为 `Refunded`（R1 已登记的既有机制，非新偏离）。
4. **keeper.py 零改动**：本轮所有证据用既有面（`--deals`/`--interval`/默认 nudge）；未
   出现需要微调的情形。
