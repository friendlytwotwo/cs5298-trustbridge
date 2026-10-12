# TrustBridge

**Committee-attested fulfillment trust layer for AI-agent-to-AI-agent deals on Lyquor.**
**Lyquor 上面向 AI Agent 间交易的、委员会背书的履约信任层。**

CS5298 Final Project. Plan: [`docs/FinalProject_计划书_TrustBridge_2026-10-12.md`](docs/FinalProject_计划书_TrustBridge_2026-10-12.md); research: [`docs/FinalProject_可行性调研_现有方法_2026-10-11.md`](docs/FinalProject_可行性调研_现有方法_2026-10-11.md); direction memo: [`docs/FinalProject_方向总结_A2A信任桥.md`](docs/FinalProject_方向总结_A2A信任桥.md).

---

## What it is | 这是什么

**EN:** Two autonomous agents transact (a video creator's agent buying a song license from a rights holder's agent, brokered by a third agent). Escrow, hash-notarized communication traces, LLM-estimated enforceable timeouts, and committee-arbitrated payouts are enforced on-chain. The novelty claims are the four convergent points in the plan §0 — NOT "escrow for agents" (ERC-8183 / Virtuals ACP already own that seat).

**中文：** 两个互不信任的自主 Agent 完成一笔交易（视频创作者 Agent 经中介 Agent 向权利方 Agent 购买歌曲授权）。资金托管、通信轨迹哈希存证、LLM 估时的强制超时、委员会裁决赔付全部由链上强制执行。新颖性主张是计划书 §0 收敛后的四点——**不是**"给 Agent 做托管"（该座位已被 ERC-8183 / Virtuals ACP 占据）。

---

## Quickstart | 快速开始

**EN:**

```bash
# 1) Pure core tests — no platform needed, runs anywhere with cargo:
cd lyquid && cargo test

# 2) Orchestration smoke (in-process FakeNode; no devnet required):
cd .. && python scripts/demo.py --sim            # all three flows
python scripts/demo.py --sim --flow timeout      # single flow

# 3) Against the real devnet (after W1 spikes):
bash scripts/devnet-up.sh        # docker compose: nodes on :10087/:11087/:12087/:13087 + Anvil
bash scripts/deploy.sh           # shaker deploy (NOTE: --update resets state; demos are idempotent)
python scripts/demo.py --node http://127.0.0.1:10087
```

Python deps: `pip install -r agents/requirements.txt` (requests only).

**中文：**

```bash
# 1) 纯核心层测试 —— 不需要平台,任何有 cargo 的地方都能跑:
cd lyquid && cargo test

# 2) 编排冒烟测试(进程内 FakeNode,无需 devnet):
cd .. && python scripts/demo.py --sim            # 全部三条流程
python scripts/demo.py --sim --flow timeout      # 单条流程

# 3) 对接真实 devnet(W1 spike 之后):
bash scripts/devnet-up.sh        # docker compose:节点在 :10087/:11087/:12087/:13087 + Anvil
bash scripts/deploy.sh           # shaker deploy(注意:--update 会重置状态;demo 脚本设计为幂等)
python scripts/demo.py --node http://127.0.0.1:10087
```

Python 依赖：`pip install -r agents/requirements.txt`（仅 requests）。

---

## Layout | 目录结构

**EN:**

```
docs/                  planning documents (plan, research, direction memo, in Chinese)
lyquid/                 Rust Lyquid = the trust layer
  src/types.rs          domain types (Deal, evidence, committee cert, payout)
  src/core.rs           PURE state machine: guards/transitions/conservation + 8 unit tests
  src/lib.rs            state! + network/instance method wrappers (thin, caller guards)
  src/committee.rs      threshold validation + oracle/UPC wiring notes (price-feed path)
  src/assessor.rs       instance-side LLM: qualification + duration estimate (JsonSchema out)
  src/timeout.rs        "off-chain trigger; on-chain guard" watcher design
  tests/escrow_lifecycle.rs    book-conservation tests for the three demo flows
  tests/modelcheck_refund.rs   exhaustive event-ordering model check (E3 evidence)
agents/                 Python agent side (scripted behavior, pluggable LLM)
  common/protocol.py    A2A message envelopes + canonical JSON + sha256 (what gets notarized)
  common/rpc.py         NodeClient (devnet) + FakeNode (sim mirror; truth = rust core)
  common/llm.py         ScriptedLLM (deterministic replay) / OpenAICompatLLM (TB_LLM=openai)
  alice.py broker.py bob.py    per-agent CLIs
scripts/                devnet-up / deploy / demo orchestration
```

**中文：**

```
docs/                  规划文档(计划书、可行性调研、方向总结,中文)
lyquid/                 Rust Lyquid = 信任层本体
  src/types.rs          领域类型(Deal、证据、委员会证书、 payout)
  src/core.rs           纯状态机:守卫/转移/守恒 + 8 个单元测试(无平台依赖)
  src/lib.rs            state! + network/instance 方法薄封装(调用者守卫)
  src/committee.rs      阈值校验 + oracle/UPC 接线说明(price-feed 路径)
  src/assessor.rs       instance 侧 LLM:资格审查 + 时长估计(JsonSchema 输出)
  src/timeout.rs        "链下触发;链上守卫" watcher 设计
  tests/escrow_lifecycle.rs    三条 demo 流程的账本守恒测试
  tests/modelcheck_refund.rs   事件排序穷举模型检查(E3 证据)
agents/                 Python Agent 端(脚本化行为、可插拔 LLM)
  common/protocol.py    A2A 消息信封 + 规范化 JSON + sha256(被存证的内容)
  common/rpc.py         NodeClient(devnet)+ FakeNode(仿真镜像;真值 = rust core)
  common/llm.py         ScriptedLLM(确定性回放)/ OpenAICompatLLM(TB_LLM=openai)
  alice.py broker.py bob.py    各 Agent 的 CLI
scripts/                devnet-up / deploy / demo 编排
```

---

## W1 spike checklist | W1 spike 清单

**EN** (blockers, in priority order):

1. **Timer semantics (R1)** — on the 4-node devnet: a deal past deadline + a `TriggerMode::Once` watcher submitting `claim_timeout`; kill/restart nodes; assert exactly one refund, no double-fires, latency < 2x period. Fallback already built: keeper + on-chain guard.
2. **Committee round-trip** — port the `price-feed` oracle skeleton; one `propose_and_certify` / `set_threshold` round; read `ctx.cert.signers`.
3. **lyquid-llm two-step** — instance fn calls `call_model` (JsonSchema), result committed via a network call (pattern in `assessor.rs`); verify `http_request` egress constraints.
4. **RPC envelope** — exact JSON shape agents must POST to `/lyquor/api` (`rpc.py NodeClient.call` placeholder), incl. Vec/struct param encoding.
5. **Macro drift audit** — `state!` Vec field, caller-identity accessor (`ctx.from`? `eth_guard = creator`?), slot accessor, error constructor: every `SPIKE(W1)` marker in `lyquid/src/`.

**中文**（阻塞项,按优先级排序）：

1. **定时器语义（R1）**——4 节点 devnet 上：一笔回合超期的交易 + `TriggerMode::Once` watcher 提交 `claim_timeout`；kill/重启节点；断言恰好一次退款、无重复触发、延迟 < 2 倍周期。备用方案已内建：keeper + 链上守卫。
2. **委员会回合**——移植 `price-feed` oracle 骨架；跑通一次 `propose_and_certify` / `set_threshold` 回合；读取 `ctx.cert.signers`。
3. **lyquid-llm 两步提交**——instance 函数调 `call_model`（JsonSchema），结果经网络调用提交（模式见 `assessor.rs`）；确认 `http_request` 出口限制。
4. **RPC 包格式**——Agent 向 `/lyquor/api` POST 的确切 JSON 形状（`rpc.py NodeClient.call` 目前是占位），含 Vec/结构体参数编码。
5. **宏漂移审计**——`state!` 的 Vec 字段、调用者身份访问器（`ctx.from`？`eth_guard = creator`？）、slot 访问器、错误构造器：逐个核对 `lyquid/src/` 里所有 `SPIKE(W1)` 标记。

**Platform discipline | 平台纪律** — **EN:** git-pin `v0.7.3` and never float (repo moves weekly; crates.io `lyquid-llm` is a placeholder); no UPC/timers/http/randomness inside network fns; HashMaps only via `new_hashmap()`; `shaker deploy --update` resets state. **中文：** git 锁定 `v0.7.3` 绝不浮动（仓库每周在动；crates.io 的 `lyquid-llm` 是占位包）；网络函数内禁止 UPC/timer/http/随机数；HashMap 只用 `new_hashmap()` 别名；`shaker deploy --update` 会重置状态。

---

## Verified-API status | 已验证 API 状态

**EN** (from the feasibility report | 来自可行性调研报告):

| Need | API | Status |
|---|---|---|
| Escrow ledger | `state!{ network balances: HashMap<K,V> = new_hashmap(); }` | ✅ erc20 example |
| Evidence log | network `Vec` append + seq | ✅ same pattern |
| LLM in-Lyquid | `lyquid-llm::call_model` + OpenAI/Gemini backends, `OutputFormat::JsonSchema` | ✅ shopping-assistant example |
| Timeout | watcher + guard (primary); `TriggerMode::Once(ms)` (optimization) | ⚠️ spike #1 |
| Committee | oracle `propose_and_certify` / UPC 3-phase | ⚠️ spike #2, price-feed example |
| On-chain settle (stretch) | `circle-nanopay-flow` (Base Sepolia USDC) | ✅ example exists, not wired |

**中文：**

| 需求 | API | 状态 |
|---|---|---|
| 托管账本 | `state!{ network balances: HashMap<K,V> = new_hashmap(); }` | ✅ erc20 示例已验证 |
| 证据日志 | network `Vec` 追加 + 序号 | ✅ 同上模式 |
| Lyquid 内调 LLM | `lyquid-llm::call_model` + OpenAI/Gemini 后端, `OutputFormat::JsonSchema` | ✅ shopping-assistant 示例 |
| 超时 | watcher + 守卫（主方案）；`TriggerMode::Once(ms)`（优化项） | ⚠️ spike #1 |
| 委员会 | oracle `propose_and_certify` / UPC 三阶段 | ⚠️ spike #2, price-feed 示例 |
| 链上结算（stretch） | `circle-nanopay-flow`（Base Sepolia USDC） | ✅ 示例存在,尚未接线 |

---

## Demo trust assumptions | Demo 信任假设

**EN** (report E3 table, keep honest):

- Threshold agreement ≠ semantic truth: k signatures attest k members ran the check.
- Committee collusion bounded by member selection + misconduct log, not eliminated.
- `faucet` is demo-only. No seller stake yet (slash hook is a documented W4 stretch).
- Evidence digests are client-supplied; W4 adds the #2833-style request/response binding so receipts carry cryptographic linkage to the exchange.

**中文**（报告 E3 表,保持诚实）：

- 阈值达成 ≠ 语义真相：k 个签名只证明 k 个成员**跑过**检查，不证明结论正确。
- 委员会合谋由成员遴选 + 不端记录约束，但未消除。
- `faucet` 仅限 demo。尚无卖家保证金（罚没钩子是文档化的 W4 拓展项）。
- 证据摘要由客户端提交；W4 将加入 #2833 式请求/响应绑定，使回执与交易内容有密码学关联。
