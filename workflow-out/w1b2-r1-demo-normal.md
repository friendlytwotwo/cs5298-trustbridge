# W1-B2 R1 · `demo.py --node` 正常流证据（G4 门）

- 实例：`Lyquid-5h2kjsj3cbx2haipw6dzpd7cbe52z3seyfkaa` / `0x40918Ba7f132E0aCba2CE4de4c4baF9BD2D7D849`
- 日期：2026-10-29；原始日志：`_r1-demo-normal-raw.txt`（本文件 §2 为原文）、
  `_r1-console-fund-raw.txt`、`_r1-final-state-raw.txt`

## §1 命令与角色映射

```
$ python scripts/demo.py --node http://127.0.0.1:10087 \
    --contract 0x40918Ba7f132E0aCba2CE4de4c4baF9BD2D7D849 --flow normal
```

node 模式身份映射（plan §4 C/demo，`demo.py role_ids()`）：

| 角色 | 链上身份（anvil 确定性账户） | 发送方（`from`） |
|---|---|---|
| alice = buyer | `0x70997970C51812dc3A010C7d01b50e0d17dc79C8`（#1） | fund / complete / 她的 notarize = #1 |
| broker | `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266`（#0） | faucet / committee_config / create_deal / 其 notarize = #0 |
| bob = seller | `0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC`（#2） | submit_deliverable / 其 notarize = #2 |

## §2 运行原文（原样）

```
====================================================================
  FLOW 1 — normal: assess -> escrow -> deliver -> settle
====================================================================
deal=deal-1 info={'id': 'deal-1', 'buyer': '0x70997970C51812dc3A010C7d01b50e0d17dc79C8', 'seller': '0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC', 'amount': 1000, 'state': 'Qualified', 'timeout_slots': 300, 'deadline_slot': None}
final state=Settled balances: alice=9000 bob=980 broker=20

====================================================================
  DEMO COMPLETE
====================================================================
```

## §3 状态阶梯（每步证据来源）

| 步 | 状态 | 证据 |
|---|---|---|
| create_deal（评估 est=60000/conf=40 由 `get_llm()` 脚本回放给出） | `Qualified` | §2 中 `deal_info` 字面（`"state": "Qualified"`，deadline=None） |
| fund（sender=#1） | `Funded` | `shaker console` 的 `fund:deal_view` 行（D4 通道）：`{"id":"deal-1",…,"state":"Funded","timeout_slots":300,"deadline_slot":471}` |
| notarize ×2（offer #1→#0，request #0→#2） | — | 证据日志 seq 0/1（见 §4） |
| notarize acceptance（#2→#0） / deliverable（#2→#1） | — | 证据日志 seq 2/3 |
| submit_deliverable（sender=#2） | `Submitted` | **非直接打印**：complete 的 core 守卫 `require_states(Submitted)` 成功（终态 Settled）反证该状态曾成立 |
| notarize receipt（#1→#2） | — | 证据日志 seq 4 |
| complete（sender=#1） | `Settled` | §2 终态字面；§5 eth_call 复核 `"state":"Settled"` |

（demo 只在建单与终态打印 `deal_info`；中间态由上表所列通道补齐，未使用任何推测值。）

## §4 notarize 序列（`evidence_entries_json(deal-1)` 原文）

```
[{"seq":0,"from":"0x70997970C51812dc3A010C7d01b50e0d17dc79C8","to":"0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266","payload_digest":"bee6b97435be36bd708e025928597172f137dd610360017ef0a3c525adb008bd","slot":169},
 {"seq":1,"from":"0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266","to":"0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC","payload_digest":"992573964e174530ad8f1397e3bc0748c558bb16ab693a50981308dc0474d695","slot":170},
 {"seq":2,"from":"0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC","to":"0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266","payload_digest":"6e3b509ad6a4a0b943c5ac742edce3be3da3517d3d73a6506fee965655924272","slot":172},
 {"seq":3,"from":"0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC","to":"0x70997970C51812dc3A010C7d01b50e0d17dc79C8","payload_digest":"5b3df286daff72fb1a3f679bcc5f3b67e3687e95980abd67eddde7b6b9a29de3","slot":173},
 {"seq":4,"from":"0x70997970C51812dc3A010C7d01b50e0d17dc79C8","to":"0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC","payload_digest":"b0e9d8c82d0e1b323b6aaed1dbb3737fc336676218a1f621ecadf2878890345e","slot":175}]
```

每条 `from` 都等于其发送方地址串（自署名守卫 `from == caller`，lib.rs:367-369 通过），
且 EIP-55 大小写与 Rust 侧 `Address::to_string()` 完全一致（R6 风险未发生）。

## §5 终态与余额勾稽（G4 门）

```
deal_info(deal-1) → {"id":"deal-1","buyer":"0x7099…79C8","seller":"0x3C44…93BC",
                     "amount":1000,"state":"Settled","timeout_slots":300,"deadline_slot":471}
balance_of(#1 alice)  = 9000
balance_of(#2 bob)    = 980
balance_of(#0 broker) = 20
```

勾稽（amount=1000，fee_bps=200 ⇒ fee = 1000×200/10000 = 20）：

- alice：faucet +10000 − escrow 1000 = **9000** ✓（本实例账本从零起，唯一入账来源是
  faucet；守恒式 9000+980+20=10000 即证 faucet 前为 0）
- bob：**+980** = 1000 − 20 ✓
- broker：**+20** ✓
- 守恒：9000 + 980 + 20 = 10000 = faucet 总量 ✓

**G4 门满足：`state=="Settled"` 字面 + 三余额勾稽成立。**

## §6 本轮发现（登记）

- **读通道终局延迟**：complete 后立刻读 `deal_info` 可能仍返回前态（本轮首次实测即出现
  `Submitted` 的陈旧读）；已按方案 R7 在 demo 终态打印前加入 keeper 同款读回重试
  （`read_back`，5×0.4s），本节 §2/§5 均为重试后的稳定读数。
- `#2` 作为 sender 的首次验证（D6）在正常流内完成：`submit_deliverable`（Seller 守卫）
  与多条 self-signed `notarize` 由其签名落地（§4）。
