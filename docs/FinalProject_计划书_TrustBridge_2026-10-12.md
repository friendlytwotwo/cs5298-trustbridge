# CS5298 Final Project 计划书：TrustBridge — 委员会背书的 A2A 履约信任层

> 版本：v1.0（2026-10-12）
> 依据：[方向总结](FinalProject_方向总结_A2A信任桥.md) + [可行性调研](FinalProject_可行性调研_现有方法_2026-10-11.md)（含同日评估 PDF 交叉核对）
> 代码框架：`./trustbridge/`（本次同步搭建）
> 硬节点：10/19 Canvas 注册；11/19 12:00 提交报告+demo；当天 8 分钟展示

---

## 进度快照（2026-10-19，四阶段协作完成后）

> 以下正文为 2026-10-12 定稿的计划书基线，予以保留；**冲突处以本节为准**。四阶段 GLM×DeepSeek 协作（纯核心加固→平台封装守卫→机械修复+真契约→Python 对齐）已完成并推送：13 个提交，HEAD `912a4ae`，仓库 github.com/friendlytwotwo/cs5298-trustbridge。

| 项 | 当前状态 |
|---|---|
| 里程碑 | 四阶段代码审查与加固完成；**W1 spike 未开始**（五项清单见仓库 README；Canvas 注册 10/19 截止请确认已办理） |
| 测试 | verify_core 壳 **39/39 全绿**（core 32 + escrow 5 + modelcheck 2，较初始 28 增 11）；模型检查 720+ 事件排序 0 违例；sim 三流程账目守恒 |
| 已修复真缺陷 | 未注资 cancel 铸币漏洞、裁决→终态误标、fee 溢出/下溢、Qualified-取消语义、E0433/E0061/E0277 编译错路径、未签名裁决证书可伪造（封装层）、fund 账务顺序 |
| 新增契约 | evidence_root = FNV-1a-64 证据序列折叠（空序列根 `cbf29ce484222325`，顺序敏感，向量钉死；demo 路径同源校验，独立性留 W4 oracle）；平台侧 ACCESS_MATRIX 权限矩阵与错误桥接 |
| 风险登记册更新 | R1（timer 语义）仍开放=W1 首项；R2（新颖性）已由措辞收敛+竞品对照缓解；R5（LLM 非确定性）已由 MockLLM 回放缓解；新增已知项：lib.rs 对真实 ldk 73 个编译错=W1 spike 范围（预期状态，纯核心壳不受影响） |
| 下一步 | W1 spike 五项 → W2 正常流上 devnet（按 §6 里程碑推进，其余里程碑不变） |

---

## 0. 摘要卡

| 项 | 内容 |
|---|---|
| 一句话 | 两个互不信任的自主 Agent 在 Lyquor 上完成一笔版权授权交易：资金托管、通信哈希存证、LLM 估时超时、委员会裁决赔付全部由链上强制执行 |
| 新颖性主张（严格收敛版） | ① 委员会背书的履约过程可信（vs ERC-8183 的"客户自选无抵押评估者"）② A2A 通信轨迹哈希公证作为中立证据（兼容 x402 #2833 提案格式）③ LLM 估时驱动强制超时（现有系统 deadline 均为人工常量）④ 单链集成：UPC 让中介=委员会=账本合一 |
| 场景 | 视频创作者 Agent（买方）经中介 Agent 向歌手 Agent（权利方）购买歌曲授权 |
| 技术栈 | Rust + LDK v0.7.3（锁定 tag）+ lyquid-llm + 4 节点 devnet/Anvil；Agent 端 Python |
| 差异化基线 | 同一托管守卫跑纯 EVM(Anvil/Solidity) 对照实现，演示"缺委员会背书/缺 LLM 估时"的差异（Why-Lyquor 实证） |

---

## 1. 定位与卖点

**不是**"给 A2A 做托管"（ERC-8183 已标准化该原语、Virtuals ACP 已在生产运行），**而是**"独立的、委员会背书的履约过程可信层"：

- 证据 = **密码学公证的通信轨迹**（每条关键消息的 sha256 摘要按序上链），不是评估者意见，也不是商户自证；
- 裁判 = **有门槛的多节点委员会**（oracle 认证调用 / UPC 聚合，阈值签名），不是客户自选、无抵押的单个评估者；
- 时限 = **LLM 估时 × 安全系数**（平台侧评估者角色，lyquid-llm 跑在 instance 函数，非共识路径），超时采用"watcher 提交 + 链上守卫复核"模式（native trigger 仅作优化）；
- 互操作 = 证据摘要格式对齐 x402 Foundation #2833（delivery-receipt attestation）与 ERC-8183 `attestationHash`——把"撞车"变成兼容卖点。

Why Web3（每环节已答）：托管与结算必须上链（去信任中介）；Why Lyquor（收敛后）：**托管账本 + 委员会背书 + 状态机在同一可编程单元内**——LLM 私有计算是能力加分项，不作为主论点（评估 PDF 同判）。

## 2. 场景与用户故事

```
Alice(视频创作者)──Agent A          Agent C──Bob(歌手/权利方)
        │      \\        Agent B(中介, Lyquor节点+委员会成员)      │
        │ ①报价brief ──→ B: ②LLM资格审查+估时 ──→ ③向C发起请求 ──→ │
        │                                                        │
        │ ④资金入托管(network state) ←── ⑤C接受(签名PoA, 存证) ──┘
        │ ⑥C交付授权书摘要+全程消息哈希存证(链上, 按序)
        │ ⑦委员会(≥3/4节点)核对证据 vs 验收标准 → 认证裁决
        │ ⑧放款:C收货款-中介费 / 超时:全额退款 / 争议:裁决赔付
```

三条演示流程：**正常流**（①–⑧ 走通）；**超时流**（C 未按期交付 → watcher 提交 → 链上守卫复核 → 全额退款）；**对抗流**（伪造交付/迟到证据 → 委员会否决 → 退款+不端记录）。

## 3. 架构设计

### 3.1 分层（框架已按此落地）

| 层 | 内容 | 位置 |
|---|---|---|
| 纯核心逻辑 | 交易状态机 + 守卫 + 守恒校验（**无平台依赖，普通 cargo test 可测**） | `trustbridge/lyquid/src/{types,core}.rs` |
| 链上信任层 | network 状态托管账本/证据日志/委员会配置；network 函数 = core 的薄封装 + 调用者守卫 | `src/lib.rs`（escrow/notary/committee 方法） |
| 平台侧智能 | instance 函数：LLM 资格审查 + 估时（lyquid-llm），结果经两步模式提交 network | `src/assessor.rs` |
| 超时执行 | "off-chain trigger; on-chain guard"：instance watcher 扫描到期交易 → 提交退款调用 → network 函数复核守卫（PDF 与我方验证一致的首选模式） | `src/timeout.rs` |
| 委员会背书 | UPC 三阶段/oracle `propose_and_certify` 阈值认证 → `apply_committee_verdict` | `src/committee.rs` |
| Agent 端 | 脚本化行为 + 可插拔 LLM（Mock 可回放，保 B1 可复现） | `trustbridge/agents/` |

### 3.2 交易状态机（core.rs 已实现，测试覆盖）

```
Qualified ─fund→ Funded ─submit(deliverable)→ Submitted ─complete(买方同意|委员会认证)→ Settled(终)
    │                │                                                            ↑
    │                ├─claim_timeout(now≥funded+timeout, 仅Funded可)→ Refunded(终)   │
    │                └─open_dispute→ Disputed ─apply_verdict(Fulfilled)─────────────┘
    │                                    └apply_verdict(NotFulfilled|Malicious)→ Refunded(终)+不端记录
```

关键规则（吸取评估 PDF 模型检查教训：朴素"取消即释放全款"规则在 10,080 种事件排序中 1,017 种违例）：
- **自动退款仅允许从 Funded 态**（未提交任何交付证据）——彻底消灭"退款后迟到证据"竞态类；
- Submitted 态的资金去向**只能**经 complete（买方同意）或 Disputed→委员会裁决；
- 终态后无任何出边；每次结算满足**资金守恒**：卖方收款+中介费+退款+罚没 ≡ 托管金额。

### 3.3 上链对象

| 对象 | 存储 | 写入者 |
|---|---|---|
| Deal 记录（条款摘要、估时、超时槽数、状态） | network `deals` | `create_deal`（broker） |
| 托管账本（Agent→余额） | network `balances` | fund/settle/refund |
| 证据日志（按交易有序的消息摘要序列） | network `evidence` | `notarize`（任何人，只追加） |
| 委员会配置（成员+阈值） | network | `committee_config`（demo: broker） |
| 委员会裁决证书（verdict+签名者集+证据根） | 随 Deal | `apply_committee_verdict`（验阈值） |
| LLM 评估报告（资格分/估时/置信度） | instance（缓存）→ 摘要随 Deal 上链 | assessor |

## 4. 差异化论证（报告 Related Work 骨架）

| 对比对象 | 它做到哪 | 我们的差异 |
|---|---|---|
| ERC-8183 | 托管状态机+超时退款标准化；**明确无仲裁** | 委员会背书裁决；证据=通信轨迹公证而非评估者意见 |
| Virtuals ACP v2 | 生产运行，交付物也托管；评估者=收费 Agent | 中立阈值委员会（无利益绑定）；证据密码学公证 |
| x402 #2833（提案） | 请求/响应哈希回执锚定（EAS/Base） | 我们做链上原生实现+守卫强制+委员会裁决；格式兼容其摘要定义 |
| Olas Mech | 优先窗口后他人可接管（超时接管先例） | 新颖性不在接管，在 LLM 估时+委员会裁决赔付——引用并让出该点 |
| ASP/ExecMesh/RAILS/A2A-SE/Burgos | 学术先行（托管+证据+超时三元组各有覆盖） | 见 §0 四点；逐篇引用对比（写报告前到 arXiv 复核编号） |
| SoK 2610.01756 | 把"验证↔结算缺口"正式化为开放问题 | Problem Statement 权威背书，直接引用 |

## 5. 技术方案：已验证 API 映射

| 需求 | LDK API（已验证 v0.7.3 存在） | 状态 |
|---|---|---|
| 托管账本 | `state!{ network balances: HashMap<K,V> = new_hashmap(); }`（erc20 示例模式） | ✅ 可抄 |
| 消息摘要存证 | network state `Vec`/map 追加 + seq | ✅ 同上 |
| LLM 资格/估时 | `lyquid-llm`: `call_model` + `OpenAiCompatBackend`/`GeminiBackend` + `OutputFormat::JsonSchema`；宿主 `http_request`（仅 instance） | ✅ shopping-assistant 先例 |
| 估时→超时 | instance 算 `timeout_slots = est_ms × safety / SLOT_MS` → 随 `create_deal` 上链；执行靠 watcher+守卫；`TriggerMode::Once(ms)` 仅优化项 | ✅ 模式已定，trigger 语义 W1 spike |
| 委员会 | oracle：`propose_and_certify`/`set_threshold`/`ctx.cert.signers`（price-feed 4 节点先例）+ UPC 三阶段聚合 | ⚠️ 自写聚合，W1 第二 spike |
| 链上结算（stretch） | `circle-nanopay-flow`（Base Sepolia USDC）/ `OracleServiceTarget::EVM` | demo 主线用内部记账 |

平台纪律：锁定 git tag `v0.7.3`（crates.io 的 lyquid-llm 是占位包，必须 git 依赖）；网络函数内禁 UPC/timer/http/随机数、HashMap 用 `new_hashmap()` 别名；`shaker deploy --update` 会重置状态——demo 脚本要幂等重建。

## 6. 里程碑与验收（3 人 × 6 周）

| 周 | 交付 | 验收标准 |
|---|---|---|
| **W1**（→10/19） | 四项 spike：①4 节点 devnet kill/重启测 `Once` 触发去重 ②`propose_and_certify` 一回合 ③instance LLM→network 两步提交 ④Agent↔节点 RPC 包格式；**10/19 Canvas 注册**；框架编译+hello 部署 | spike 报告（每项：结论/证据/备用方案）；`cargo test` 绿 |
| W2 | 设计冻结（本计划书 §3 状态机+消息 schema）；escrow 核心（fund/submit/complete/refund）在 devnet 走通；Agent CLI 连上节点 | 单元+集成测试绿；正常流干跑到 Funded |
| W3 | 正常流端到端（报价→LLM 评估→托管→存证→交付→结算+中介费）；内部账本+faucet | demo 脚本一次跑通正常流 |
| W4 | 对抗流：超时退款（watcher+守卫）、争议→委员会裁决→不端记录；LLM 响应缓存/回放（B1）；退款规则模型检查（事件排序枚举，移植评估 PDF 方法） | 两条对抗流可复现演示；模型检查 0 违例 |
| W5 | 4 节点委员会演示（E2）；**对照实验**：纯 EVM 版同守卫 vs Lyquor 版（E3 素材+Why-Lyquor 实证）；组外用户测试（B3）；自审计章节 | 实验数据表；用户测试记录 |
| W6 | 报告 PDF（≥6 页+AI 声明）、幻灯片、预录 3 分钟 demo | 11/19 12:00 前提交 |

分工建议：P1=Lyquid 核心（escrow/notary/账本）；P2=委员会+LLM+超时（oracle/UPC/assessor/timeout）；P3=Agent 端+demo 编排+实验与报告。全组每人都能讲核心流程（展示评分要求）。

## 7. 实验与评估设计

1. **正确性**：core.rs 状态机全转移单测 + `tests/modelcheck_refund.rs` 枚举事件排序（fund/submit/timeout/dispute/verdict/cancel 的排列）断言两条不变量：单一终态支出、资金守恒。
2. **对照实验（Why-Lyquor 实证）**：同一退款守卫用 Solidity 在 Anvil 实现一版；对比维度：能否表达委员会阈值认证、LLM 估时来源、证据日志与结算的一致性保障、代码量/复杂度。
3. **可用性**：B3 组外同学以 Agent 运营方角色跑正常流+超时流，任务完成率+问卷。
4. **性能（次要）**：存证→终局时延、争议裁决墙钟时间（4 节点 localnet）。

## 8. 风险登记册

| # | 风险 | 等级 | 缓解（已内建） |
|---|---|---|---|
| R1 | trigger 多节点语义不明 | 高 | W1 首个 spike；主方案=watcher+链上守卫（不依赖 trigger 正确性） |
| R2 | 新颖性被压缩（ERC-8183/ACP/Olas） | 高 | §0 四点收敛措辞；报告逐篇引用对比 |
| R3 | SDK 周级变动/封闭开发 | 中 | 锁 v0.7.3；问题靠镜像源码；框架纯核心层可离线开发测试 |
| R4 | 范围失控 | 中 | 只做版权授权闭环；对抗流仅超时+伪造两类 |
| R5 | LLM 非确定性 vs 可复现（B1） | 中 | MockLLM 回放；测试走 mock、demo 可选真实调用 |
| R6 | 委员会签名链上验证复杂 | 中 | demo 用成员集+阈值+签名者集合校验，生产路径注明走 certified calls |

## 9. 评分映射（更新版）

A1 场景新颖=自主 Agent 经济的履约保障；A2 方案新颖=§0 四点（对照 ERC-8183/ACP/#2833/ASP 系论证）；A3 实用价值=x402 生态把"无争议通道"列为公开议题+SoK 背书；B1=纯核心层测试+MockLLM 回放+幂等 demo 脚本；B2=双状态/UPC/oracle/lyquid-llm/trigger（broad use）；B3=W5 用户测试；C2/C3=竞品对照表+攻击场景+模型检查；D=正常流+两条对抗流预录；E1=自选方向（措辞按 §0）；E2=4 节点委员会多机部署；E3=结构化自审计（信任假设表：委员会合谋/评估者操纵/存证选择性提交/超时博弈）+修复记录。

## 10. 框架仓库导览（本次交付）

```
trustbridge/
├── README.md                 # 快速开始 + W1 spike 清单 + API 已验证状态表
├── lyquid/                   # Rust Lyquid（信任层本体）
│   ├── Cargo.toml            # git 锁 ldk v0.7.3
│   ├── src/types.rs          # 领域类型（Deal/证据/证书）
│   ├── src/core.rs           # 纯状态机+守卫+守恒（无平台依赖，先测这层）
│   ├── src/lib.rs            # state! + network/instance 方法薄封装
│   ├── src/committee.rs      # 阈值校验 + oracle/UPC 接线说明
│   ├── src/assessor.rs       # LLM 资格审查+估时（instance）
│   ├── src/timeout.rs        # watcher 扫描逻辑 + trigger 接线
│   └── tests/                # 生命周期测试 + 退款规则模型检查
├── agents/                   # Python Agent 端（A 买方/B 中介/C 权利方）
│   ├── common/               # 协议消息+规范哈希、节点RPC、可插拔LLM(Mock可回放)
│   ├── alice.py / broker.py / bob.py
├── scripts/                  # devnet-up / deploy / demo 编排（正常+超时+对抗）
└── .gitignore
```

约定：所有 `SPIKE(W1)` 注释 = 一周内必须实证的 API 假设；所有 `TODO` = 按里程碑补齐。
