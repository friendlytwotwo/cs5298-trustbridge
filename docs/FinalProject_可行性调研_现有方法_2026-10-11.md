# CS5298 Final Project 可行性调研：现有方法全景与 Lyquor 平台验证

> 调研日期：2026-10-11（基于 5 路并行深度检索，共复核 ~255 个来源）
> 配套文档：[FinalProject_方向总结_A2A信任桥.md](FinalProject_方向总结_A2A信任桥.md)
> 结论先行：**方向成立，但"空白"比方向文档写得更窄——主张需要重新收敛；Lyquor 四项能力全部有实锤代码与官方示例，6 周可行（有条件）。**
> 2026-10-11 补充：已交叉核对同日《Agent to Agent Task Platform》架构评估文档（22 页 PDF），其独有竞品覆盖并入 §2 各层表格与 §2.5，引用可核验性见 §6

---

## 1. 一页结论

| 问题 | 结论 | 置信度 |
|---|---|---|
| "Agent 交易缺履约保障"这个需求还成立吗？ | **成立，且刚被学术正式化**：2026-10-01 的 arXiv SoK（2610.01756）把"验证与结算之间的缺口"定义为该领域的公认未解问题 | 高（一手论文） |
| "托管 + 超时退款"还是我们的空白吗？ | **不是了**。ERC-8183（2026-02 草案）已把"任务托管+超时退款+评估者放款"做成标准原语；Virtuals ACP 已在生产环境跑同样的事（2000+ Agent） | 高（一手规范/白皮书） |
| 那还有什么空白？ | 三点组合仍然无人做：**① 委员会背书的履约过程存证**（现在所有方案都靠"客户自选、无抵押的评估者"或商户自证）；**② A2A 通信轨迹的哈希公证作为履约证据**（最接近的 x402 Foundation #2833 提案 2026-07 提出、未合并）；**③ LLM 估计任务时长驱动强制超时**（文献中所有 deadline 都是人工配置常量） | 高（多路独立检索收敛） |
| Lyquor 能撑起这个设计吗？ | **能（有条件）**。UPC/LLM/定时器/资产四项均有已发布代码+官方示例；最大未知 = 多节点下 timer 触发语义，W1 spike 第一优先 | 高（官方文档+源码级验证） |
| 6 周能做完吗？ | 单人 Demo 闭环可以；条件：SDK 锁定 `v0.7.3`、范围限定本地 devnet/Anvil、托管状态迁移全部走网络函数 | 中高 |
| 同日评估文档（A2A Task Platform PDF）是否推翻以上结论？ | **否**——超时设计、委员会用法、LLM 隔离三点与我们的验证独立互相印证；它补充了竞品覆盖（已并入 §2），并要求新颖性措辞按更严格标准收敛 | 高（交叉验证） |

**最重要的战略修正**：不要把项目定位成"给 A2A 交易做托管"（该座位已有人），而应定位成——**"独立的、委员会背书的履约过程可信层"**：证据是密码学公证的通信轨迹而非评估者意见，裁判是有抵押的多节点委员会而非客户自选评估者。这恰好仍是空档，且与 x402 #2833 提案、ERC-8183 `attestationHash`、ERC-8004 注册表天然可互操作（互操作 = 创新论证的加分项）。

---

## 2. 现有方法全景（2026-10 更新版）

方向文档 §5 的"三层栈"仍然成立，但过去一个月格局有明显变动，逐项更新如下。

### 2.1 支付轨道层

| 协议 | 2026-10 状态 | 对本项目意味着什么 |
|---|---|---|
| **x402** | v2 已上线；2026-07 移交 **x402 Foundation**（Linux 基金会治理，~40 成员：AWS、Cloudflare、Anthropic、Circle 等）；AWS 已 GA 支持 | 官方明确"pay-before-delivery、无争议通道"。争议/托管是其公开的设计议题（GitHub issue #1645 等）。**是我们"补哪层"论证的最佳靶子** |
| **L402** | 规范仍在，采用面远小于 x402 | 预付+macaroon 模型，与托管无关 |
| Cloudflare NET Dollar / Monetization Gateway | 2026 年铺开，走 x402 | 只计费计量，无履约保障 |
| **MPP**（Machine Payments Protocol，Stripe + Tempo） | 2026-04 起的开放标准（[mpp.dev](https://mpp.dev)、[tempo.xyz](https://tempo.xyz)）；**MPP Sessions** = 链上支付通道，一次授权消费上限，随用量推进**累计签名凭证**（凭证记总额而非增量，天然幂等），适配计量/流式计费 | 计量计费原语，与 x402（按请求付费）互补；仍无托管/仲裁——支付轨道变宽，履约轨道仍为零 |

注意：有中置信度来源称 x402 链上交易量 2025-12 ~$970K/日 → 2026-07 ~$16K/日（平均单笔 ~$0.32）——**引用前需用 DefiLlama 自己复核**，但"支付轨道很热、履约轨道为零"的定性结论不受影响。

### 2.2 授权与身份层

| 协议 | 2026-10 状态 | 对本项目意味着什么 |
|---|---|---|
| **AP2**（Google） | **2026-05 捐给 FIDO Alliance**（与 Mastercard 一起）；v0.2 把 Mandate 改名为 Checkout/Payment Mandate | 仍然只管"授权与不可否认审计"，明确不做托管/履约/争议流程 |
| **ERC-8004** Trustless Agents | **仍是 Draft**；参考实现 2026-01 上主网；2026 年中实证研究：注册文件质量差、**信誉被 Sybil 主导** | 身份/信誉/验证三注册表。Validation Registry（0-100 分+证据 URI）是"履约证据"最接近的现有插槽——但只有评分、无托管语义、无证据内容标准 |
| 卡组织 | Visa TAP / Mastercard Agentic Tokens 商用铺开 | 只做网络入口的 Agent 身份认证；争议仍走为人类设计的旧规则 |
| **MetaMask Delegation Framework** | 活跃；可编程约束账户授权 + 再委托机制 | 授权传播本身不构成新颖性——差异化必须落在"授权 → 任务负债与生命周期"的连接上（同日评估文档同此判断） |

### 2.3 通信层（我们复用，无变化）

A2A（Linux 基金会，**官方 AgentExtension 机制** = 我们的自然挂载点）+ MCP。两者都刻意只做传输；MCP 支付集成（Stripe/PayPal/x402 桥）全是 API 包装并附带"不做任何担保"免责声明。Google 官方 `a2a-x402` 扩展也是"先付款后交付"，反托管。

### 2.4 托管/结算层——**方向文档缺失的一行，必须补进竞品表**

| 协议 | 状态 | 机制 | 留下了什么空档 |
|---|---|---|---|
| **ERC-8183 "Agentic Commerce"**（2026-02 草案） | 草案+参考实现 | 任务托管状态机 Open→Funded→Submitted→Completed/Rejected/Expired；评估者放款；`expiredAt` 后任何人可 `claimRefund` | 规范原文明确写出：**"无争议解决或仲裁；reject/expire 即终局"**。评估者是客户自选、无抵押的——"谁来评评估者"无解 |
| **Virtuals ACP v2** | 生产运行，2000+ Agent，多链 | 托管物包含**付款与交付物**；请求→协商(签名 PoA)→交易→评估；指定评估 Agent 裁决（收 ~5% 费用）；超时自动退款 | 评估者是**收钱的 Agent**（自我选定的利益方）；证据=评估者意见，非密码学公证；生态封闭 |
| x402 Foundation **issue #2833**"delivery-receipt attestation" | **仅提案（2026-07，未合并）** | 收款方签名回执，绑定结算交易与**请求/响应的 sha256 指纹**，经 EAS(Merkle 批量) 上 Base 锚定；带 `erc8004_agent_id`；明确说"这就是 ERC-8183 evaluator 的 `attestationHash` 应该提交的东西" | **这是与我们"通信哈希存证"想法撞车的设计**——但只是 issue，无实现无标准。应对策略：兼容它的格式并做出 Lyquor 原生实现+委员会背书，而非假装它不存在 |
| Boson x402-escrow-schema / A2A-SE 讨论稿 | 提案阶段 | commit/release、卖家保证金、可罚没；争议路径"由实现定义" | 无落地标准 |
| **Olas**（Mech 市场 + 服务质押） | 生产运行 | 链上请求路径支持**优先窗口过后他人接管**（超时替换先例）；链下路径靠请求者重试；服务注册需 bond、违规罚没运维保证金 | "超时接管"已有先例 → 我们的超时新颖性必须落在"LLM 估时 + 委员会裁决赔付"，而非接管机制本身 |
| **Nevermined** | 活跃 | Agent 预算、访问控制、计量、多结算轨道 | 买侧基础设施重叠面大；并发/递归行为待评估 |
| **Agent Escrow 参考实现**（评估文档引用 [8]） | **未核实** | 据评估文档描述：含里程碑、争议、parent links、委托工具与测试网演示的开源参考实现 | 公开检索不到——向文档作者索取链接并打开验证前，不得写入课程报告 |
| Skyfire / Nekuda / Catena / Payman | Skyfire 转型"Agent 信任栈"；Nekuda 已**转出**支付赛道 | 均无托管/仲裁面 | 不构成竞争 |

### 2.5 对照实现栈与设计先例（评估文档补充——非直接竞品，是对照实验对象）

| 名称 | 提供什么 | 对本项目的作用 |
|---|---|---|
| Chainlink CRE / Gelato | 现成的触发器与外部协调自动化 | "另一套栈能否用更少运维实现同样保障规则"的对照对象——评估文档要求 Lyquor 必须与之对比（可改造成课程评估实验） |
| UMA Optimistic Oracle V3 | 可配置断言 + 争议机制 | 断言/仲裁模式的现成先例；集成它即引入其自身信任与可用性假设，非 Lyquor 白送 |
| Across（intent 生命周期） | 独占中继窗口 → 开放填充、fill deadline、重复填充保护 | 执行权与 deadline 设计先例（其结算目标比任意链下 agent 工作更受限） |
| CoW（solver 竞争） | 竞争性提案 + 结算 deadline | "并行候选 + 单一受控提交"的设计先例 |
| Lit Protocol / Nillion | 版本化签名与访问控制 / 隐私存储与计算 | 相邻能力；集成则引入额外信任假设 |
| Story / Golem / Bittensor | 许可版税 / 链下算力市场 / 任务供给激励 | 相邻领域已有玩家，即削弱"首个"类宽泛主张——Related Work 引用即可 |

评估文档另一可复用素材：其本地模型检查实验——对"取消时释放全部预订、但仍兑付迟到有效索赔"这一退款规则枚举 10,080 种事件排序，其中 1,017 种违例（保守保留未决预订则 0 违例）。可直接移植为 E3 自审计中退款规则的模型检查证据。

---

## 3. 必须引用并区分的学术先行工作（新颖性红队）

以下工作与本项目机制重叠度**高**，报告 Related Work 必须显式对比（引用前先到 arXiv 用标题复核确切 ID 与内容）：

| 工作 | 时间 | 机制重叠 | 我们的差异点 |
|---|---|---|---|
| **ASP**（Agentic Settlement Protocol） | 2026-09 | 链上授权-捕获托管 + **三重 deadline 超时模型** + 履约验证阶梯 + 部分退款（XDC 链） | ASP 的履约确认靠**商户自己的履约引擎**（信任阶梯≠中立证据）；无 LLM 估时、无委员会中介 |
| **ExecMesh** | 2025-11 | Agent 算力市场：`ProofOfWorkChannel.sol` 托管 + deadline + **zk 证明 + 输出哈希上链** + 1 小时争议窗口 + 声誉罚没 | 用 ZK 而非委员会仲裁；只覆盖可重放计算；无通信轨迹公证、无估时 |
| **RAILS** | 2026-06 | 提出"agentic clearing problem"；**哈希锚定的 Evidence Envelope** + 异构验证者**面板**（含人类仲裁）→ 清算决定 → 结算指令 | 概念规格，无实现无评估；非单链集成、无 UPC 式节点背书 |
| **A2A-SE**（A2A Settlement Extension 规范） | 2026-06 | 直接在 A2A 上定义"承诺/交付/验证/放款退款/争议/声誉/终局"规范层 | 纸面规范，无实现；无节点委员会信任模型 |
| **Burgos et al. ×2** | 2025-06 / 2026-03 | 智能合约托管 + 多重 deadline + ZKP+哈希承诺证据 + **3 仲裁人委员会投票**（域：ML 模型协作/采购） | 机制三元组同构，但域非 Agent 商务；论文自己注明"接口原则上可被自动化 Agent 使用"——**是最近的先验工作，必须正面对比** |
| SAKSHI (2023) / MODiCuM (2020) | — | 托管支付通道+SLA+挑战者池+链上争议 / 账本托管+可信中介+超时罚金 | 域为 AI 推理服务/外包计算；奠基性引用即可 |
| **SoK: Decentralized Agent Economic Infrastructure**（arXiv 2610.01756） | **2026-10-01** | 系统化 12 系统/17 属性族，实证指出"正确的托管可能在几乎无交付证据的授权下放款"——**把我们的空白正式化为公认开放问题** | 直接引用作为 Problem Statement 的权威支撑 |
| Fault Tolerant Budget Conservation in Distributed Multi Agent Delegation | 预印本（**未核实**，公开检索不到） | 委托图上的托管积分与容错预算守恒——评估文档预算守恒设计的相关先行工作 | 拿到链接前不引用；若属实，差异 = 域（委托图预算 vs 履约过程存证） |

文献共识（可直接写进报告）：支付发起层（x402/AP2/ACP）狂奔，而**结算后端——判定受托义务是否真的被履行、并据此触发结算——是公认缺失的原语**（RAILS 命名之为 clearing problem；USENIX Security 2026 的 x402 安全研究实测 15 个 facilitator 全部违反 8 条安全规则中的若干条，本身就是 E3 自审计素材）。Hu & Rong (2025-11)：**任何单一信任机制都不够**，领域在收敛于 Proof+Stake+Reputation 混合栈——我们的委员会背书正是这种混合。

**新颖性判定**：托管+证据+超时这个**三元组作为机制已不新**（ASP/ExecMesh/RAILS/A2A-SE/Burgos 都碰过）；仍然成立的新颖点 = ①**中立委员会背书**（对比客户自选评估者）②**A2A 通信轨迹本身作为公证证据**（对比输出/评估意见）③**LLM 估时驱动强制超时**（全文献 deadline 均为人工常量）④单链集成（UPC 把中介=委员会=账本合一，对比 RAILS 的多层堆栈）。报告的 A2/E1 论证请**严格按这四点收敛措辞**。

---

## 4. Lyquor 平台可行性（源码级验证结果）

平台状态：**活跃且快速迭代但封闭开发**。仓库 2025-04 创建；2026-08-04 → 09-29 周更发版（v0.4.2→v0.7.3）；公开 `ldk` 仓库是私有 upstream 的**单向 bot 镜像**（唯一"贡献者"是自动化机器人，无公开 issue 区，5 stars）。意味着：遇到文档外问题只能读镜像源码，无社区可问。

### 4.1 四项能力裁定

| 能力 | 裁定 | API 实证 | 官方示例 |
|---|---|---|---|
| UPC 多节点背书 | ✅ 存在 / ⚠️ 无内置仲裁 | `upc!` 宏；三阶段处理器 `#[method::instance(upc(prepare/request/response))]`；`ctx.cache` 聚合；`timeout_ms` | `price-feed`：4 报告者+委员会中位数+认证阈值（4 节点 localnet）——**委员会背书的完整先例** |
| Lyquid 内调 LLM | ✅ 存在 | `lyquid-llm` crate（仓库内真实代码；docs.rs 上只是占位名！）：`call_model<B: Backend>`、`OpenAiCompatBackend::openai`、`GeminiBackend::google_ai`、`OutputFormat::JsonSchema`；宿主 API `http_request`（**仅限 instance 函数**） | `shopping-assistant`（LLM Agent，OpenAI/Gemini 双后端）；`lyquid-flow` 有 refinement-loop 原语 |
| 定时/超时 | ✅ 存在 / ⚠️ 语义未文档化 | `TriggerMode::{Recurrent(ms), Once(ms), Commit, Stop}` + `trigger!` 宏；**网络函数内禁用**（非确定性） | `Once(delay_ms)` 正是托管超时原语；但多节点下谁触发、重启后是否重复触发、延迟保证均无文档 |
| 资产原语 | ⚠️ 无原生 token API / ✅ 模式已验证 | `erc20` 示例展示 network 状态记账模式（`state! { network balances: HashMap<...> }` + `transfer`/`approve`）；**`circle-nanopay-flow` 示例在 Base Sepolia 真实结算 USDC（x402/EIP-3009）** | 内部记账 + 链上结算两条路都有可抄的官方代码 |

其余确认：双状态模型 `state! { network x; instance y; }`（授权/托管=network，LLM 审查=instance，与方向文档 §6.2 的建模一致）；`#[lyquid_test::test]` WASM 测试；4 节点 devnet 端口 10087/11087/12087/13087；`shaker deploy`；`call!` 跨 Lyquid 调用；`OracleServiceTarget::EVM` 以太坊互操作。

### 4.2 Top 5 平台风险（按优先级）

1. **timer 触发语义未文档化**（多节点下谁触发/重启重复/延迟界）——W1 spike 第一优先，备用方案现成：外部 keeper 或任意节点 HTTP 导出函数提交退款调用。
2. **封闭开发+无社区**：bug 只能自己读镜像源码解决；`docs.rs/lyquid` 仅 63% 文档化。
3. **SDK 周级变动**：5 周内 0.4→0.7；`lyquid-flow`/`lyquid-llm` 在 crates.io 是占位包，真实代码只在 git path 依赖里；**`shaker deploy --update` 改代码摘要会重置全部状态**（状态保留迁移钩子"计划中"）——必须锁 tag 开发。
4. **UPC 无内置仲裁**：聚合逻辑全靠自己在 `upc(response)` 里写；阈值签名委员会要走 oracle 认证调用流（`propose_and_certify`/`set_threshold`，文档中最复杂子系统）——是我们自己的定制代码量所在。
5. **确定性纪律**：网络函数禁止 UPC/timer/http/随机数，`std::HashMap` 迭代顺序会静默破坏共识；LLM 检查必须 instance 函数跑完后经网络调用提交结果（两步异步模式有文档但示例少）。

### 4.3 总体裁定

**有条件 GO**。四项能力全部有已发布代码+文档+至少一个官方示例；3 人团队 6 周可交付。条件：锁 `v0.7.3`；Demo 限定 localnet/Anvil（Base Sepolia 结算仅作 stretch）；资金状态迁移全部走网络函数；W1 把两个最险未知提前引爆（见下）。

---

## 5. 对方向文档的具体修订建议

1. **§5 竞品表**：加一行 ERC-8183（托管原语已标准化、明确无仲裁）；更新 x402（v2+基金会治理）、AP2（已入 FIDO）；加"学术先行工作"一行指向 §3 表。
2. **§4.1/§1 定位措辞**：从"做 A2A 的担保交易"改为"**独立的、委员会背书的履约过程可信层**"——每个上链环节仍答 Why Web3，但新颖性主张严格收敛到 §3 末的四点。
3. **与 x402 #2833 的关系**：在报告中主动引用并声明格式兼容（它自己说 digest 应与 ERC-8183 `attestationHash` 对齐）——把撞车变成互操作卖点，也是 A2 创新分的差异化证据。
4. **§8 风险表更新**：加"竞品比预设的近（ERC-8183/ACP）"一条，缓解措施即第 2 点的措辞收敛；加"ldk 为封闭镜像仓库"一条。
5. **E3 素材新增**：USENIX Sec 2026 x402 facilitator 攻击研究（Free Shopping、资产盗窃等 4 攻击 × 15 facilitator）可直接映射到我们的对抗场景清单。
6. **W1 spike 清单更新**（按风险排序）：
   - 4 节点 devnet 上设 `TriggerMode::Once` 触发退款网络调用 → kill/重启节点，观察触发次数/延迟/重复（**最高优先**）；
   - `price-feed` 骨架上跑通一次 `propose_and_certify` 委员会回合；
   - instance 函数里 `lyquid-llm` 调用 → 网络调用提交结果的两步模式；
   - Canvas 分组注册（10/19 截止，不变）。
7. **LLM 定位与超时实现修正（源自同日评估文档）**：Why-Lyquor 不要押在"LLM 私有计算"上——评估文档明确建议推理留在 agent 运行时（其 idea 目录把链下推理/算力销售评为 D 级）。LLM 改述为"平台侧评估/估时"角色（lyquid-llm 能力已验证真实可用）；超时采用"watcher 提交 + 链上守卫复核"模式（与我方验证的 keeper fallback 完全一致），native trigger 仅作优化项。

---

## 6. 引用与置信度说明

- **高置信**（一手）：EIP-8004/8183 全文、x402 Foundation 公告与 issue、Virtuals ACP 白皮书、AP2 官方仓库与 FIDO 公告、docs.lyquor.dev、lyquor-labs/ldk 镜像源码、arXiv 2610.01756、USENIX Sec 2026 论文页。
- **中置信**（需引用前复核）：x402 交易量衰减数据（聚合器）、Instant Checkout 暂停传闻（媒体）、ASP/RAILS/ExecMesh/A2A-SE 的确切 arXiv 编号（检索返回的是代理链接，写报告前用标题在 arXiv 复核）、Skyfire/Nekuda 现状（部分来自搜索引擎摘要）。
- **低置信/已排除**：若干 SEO 内容农场条目（TFSF Ventures"escrow 对比"、无法核实的"Pinion"创业公司）未纳入。
- 检索方法：5 个并行研究线程（加密轨道 / 传统轨道与 Google-OpenAI 栈 / 学术文献 / Lyquor 源码级验证 / 对抗性竞品空白核查），Exa 深度检索 + 一手来源直接抓取，合计复核约 255 个来源；两条线程独立收敛到同一新颖性判定（委员会背书 + 通信轨迹公证 + LLM 估时），交叉验证通过。
- **2026-10-11 增补来源**：同日《Agent to Agent Task Platform — Technical Architecture and Venture Assessment》PDF（22 页，document-95a2cbf276fc3980494a2c6236fa3247.pdf）的竞品评估与设计先例章节，经独立检索核验后并入本报告。其中 MPP 已核实为 Stripe + Tempo 的 Machine Payments Protocol（[mpp.dev](https://mpp.dev)）；其引用 [8] "Agent Escrow 参考实现"与 [6] "Fault Tolerant Budget Conservation" 预印本**公开检索不到，标记未核实**——向文档作者索取链接前不得写入课程报告。
