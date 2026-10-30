# R2 目标 C 证据：正常流一条龙（链上 assess 回放）+ cast call 直证

> 实例：`Lyquid-tldda6zqdhab2kdysepcqxx73uvm3sxz7wbaa` @
> `0xFD6F7A6a5c21A3f503EBaE7a473639974379c351`。
> 原始日志：`_r2-normal-assess-raw.txt`（流内 transcript）、
> `_r2-assess-castcall-raw.txt`（cast call 直证 + 同款 brief 原文）。
> 采集时间 2026-10-29 23:42。

---

## §1 命令与 transcript

```
$ python scripts/demo.py --node http://127.0.0.1:10087 --contract 0xFD6F7A6a…c351 --flow normal

====================================================================
  FLOW 1 — normal: assess -> escrow -> deliver -> settle
====================================================================
assess_brief (on-chain, mode=replay): {'qualification_score': 75, 'risks': ['heuristic-mode'],
                                       'est_duration_ms': 60000, 'est_confidence': 40}
deal=deal-9 info={'id': 'deal-9', 'buyer': '0x70997970C51812dc3A010C7d01b50e0d17dc79C8',
                  'seller': '0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC', 'amount': 1000,
                  'state': 'Qualified', 'timeout_slots': 300, 'deadline_slot': None}
final state=Settled balances: alice=58000 bob=1960 broker=40
DEMO_EXIT=0
```

**一条龙要素**（G6C）：

| 步 | 证据 |
|---|---|
| ① 链上 assess（回放） | `assess_brief (on-chain, mode=replay)` 行——node 模式 `new_assessed_deal` 走 `NodeClient.assess_brief`（instance 方法，export=eth，空 `base_url`/`api_key` ⇒ HeuristicModel 回放） |
| ② 评估驱动建单 | `timeout_slots=300`：来自链上报告的 `est_duration_ms=60000`（`timeout_slots = 60000×2/400 = 300`，types.rs:195-197） |
| ③ fund（资金门） | `require_funds(node, alice, 1_000)` 静默读回断言通过（零打印，sim transcript 不漂移） |
| ④ submit + complete | 流内 notarize（acceptance/deliverable/receipt）+ `submit_deliverable`(bob) + `complete`(alice) |
| ⑤ 终态 | `state=Settled` |
| ⑥ 余额勾稽 | alice −1_000（托管）、bob +980、broker +20（fee = 1_000×200/10_000 = 20）；本段基线：alice 59_000 → 58_000（含 faucet 10_000） |

## §2 cast call 直证（同款 brief，R1 通道纪律）

`brief` 与 demo 内 `new_assessed_deal` **完全同款**的 DealBrief 四字段 JSON（同一
alice/bob 地址、同一 terms digest、同一 `license_scope`）。brief 原文已入档
`_r2-assess-castcall-raw.txt`：

```
{"buyer_profile_digest": "a965f12a83ebedef449ce601a24e3fc2b844092fa29daef620dbe4af236e3b1b",
 "license_scope": "online-video,12mo,EU",
 "seller_profile_digest": "8fa0ea23b90cec6c76a4f243a4bc2497b0619588f38030a78396b3e0f914f076",
 "terms_digest": "ff580cc43c17c3f94e27d97eddc8304c1564fd0f811b89f31d8f3ec5604a0bdc"}
```

```
$ docker exec multi-tools cast call --rpc-url http://node1:10087/api 0xFD6F7A6a…c351 \
    "assess_brief(string,string,string,string) returns (string)" "<brief>" "" "" ""
"{\"qualification_score\":75,\"risks\":[\"heuristic-mode\"],\"est_duration_ms\":60000,\"est_confidence\":40}"
```

**同源对照**（逐字段）：`qualification_score=75` ✓ / `risks=["heuristic-mode"]` ✓ /
`est_duration_ms=60000` ✓ / `est_confidence=40` ✓ ——流内报告（eth_call 经 NodeClient）与
cast call 直证给出同一报告。两通道都是 eth_call（节点本地执行），差别仅在客户端；
`shaker console` 另有一行 `assess_brief: mode=heuristic report={…}` 可作第三对照
（见 `_r2-adversarial-console-raw.txt` 中 4 处 `assess_brief:` 行）。

## §3 偏离登记

1. **node 分支的评估从 `get_llm()` 改为链上 `assess_brief`**（方案 §6-3 第 3 项），sim 分支
   逐字不动。`terms_digests()` 前移到 assess 之前（brief 内嵌 terms_digest），digest 计算
   无副作用 ⇒ sim 输出不变（T4/T7 两次逐字比对门实证）。
2. **真实 LLM 通道仍未取证**（非目标，维持 R1 结论）：`env | grep -i TB_LLM` 为空，回放
   模式是唯一可执行路径；本轮未重跑 R1 的 egress 拒绝探针（结论不变，无新信息面）。
3. **`timeout_slots=300` 来自回放固定报告**（60000ms/40），非真实估值——这正是方案 §2-8
   钉死的时序安全前提（正常流不等 deadline）。
