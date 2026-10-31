# R4-D1 方案：期末报告 PDF（规划师，2026-10-30）

六阶段拆分④：**纯文档任务**——撰写 TrustBridge 期末报告并构建为 PDF（≥6 页）。
铁律第一条：**零 git 写操作**（不 commit/push/branch/tag/restore；仓库已定格于
`8d093b5` 并推送 origin/main，本任务只读引用）。前置状态：R0–R3 全部证据在档、
B3 三文档已交付、T7 端到端复验完成（`w1b2-r3-e2-committee.md` §T7）。

## 0. 受影响文件清单（6 项，供审查员核对）

| # | 文件 | 动作 | 说明 |
|---|---|---|---|
| 1 | `workflow-out/plan.md` | 覆盖写 | 本方案（任务指令指定写入位置）。旧 R3-T5+T6 方案已由规划期 `cp` 逐字节备份 |
| 2 | `workflow-out/_plan-prev-r4d1-backup.md` | 新建 | 备份件，md5 `a808bbfcc4384fd5148530b61db49ff7` 与覆盖前 plan.md 双侧一致（本轮实跑 `md5sum` 在案） |
| 3 | `workflow-out/report/` | 新建目录 | 报告专用目录（规划期已 `mkdir`） |
| 4 | `workflow-out/report/build_report.py` | 新建 | reportlab 构建脚本（报告唯一源文件；内容以 Python 数据结构内嵌） |
| 5 | `workflow-out/report/trustbridge-final-report.pdf` | 新建 | 构建产物，**≥6 页**（验收硬指标） |
| 6 | `workflow-out/report/README.md` | 新建 | 构建说明 + 证据索引 + 逐字复现命令 + 开工基线 `git status` 存证小节（仲裁修订 2；无论 PDF 是否构建成功都交付） |

**纪律边界**：除上表 6 项外零写入。`lyquid/`、`scripts/`、`agents/`、`experiments/`
零触碰；`docs/` 零触碰；不跑任何链上写（docker devnet 本任务不需要动——纯本地构建）。
上表 #1/#2 是任务指令要求的工作流文件（任务原文「把完整开发计划与变更方案写入
workflow-out/plan.md」），交付产物（#3–#6）只落 `report/`。

## 1. 目标与验收判据

| 项 | 判据 |
|---|---|
| 交付物 | `workflow-out/report/trustbridge-final-report.pdf`，A4，**≥6 页**，中文 |
| 内容 | 任务给定 5 节结构：①问题定义 ②架构 ③实验结果四阶段+R2/R3 详情与 EVM 对照 ④信任假设与局限（诚实清单）⑤AI 使用声明 |
| 诚实红线 | 报告中每一个数字/地址/tx hash/状态字面值都必须能在 §3 映射表所指的档内文件行号逐字找到；无数据处写「无数据（原因）」，不外推 |
| 构建 | 用宿主已验证的 reportlab 真出 PDF（见 §4）；构建与验证命令全部实跑并留档 README |
| 仓库 | 结束时 `git log --oneline -1` 仍为 `8d093b5`；`git status` 以 T1 开工实跑捕获的基线为准——基线 9 条（M _probe_gate_a0.md、M plan.md、?? _implementation-prev-r1/r2/w1a-backup.md、?? _plan-prev-r4d1-backup.md、?? _pre-task-snapshot-r1/r2/r3.patch）原样保留，新增未跟踪路径仅 workflow-out/report/（及其下 3 个交付文件）。规划期已实跑 `git status --short` 复核：当前输出与上述列举逐条比对（差异登记）。若 T1 开工实跑的 git status 输出与上文列举的基线条目有出入（评审/规划轮次可能被动更新 _probe_*.md 等工作流文件），以 T1 实跑输出为准逐字记入核对笔记并登记差异行，GT-d 比对即以该实跑存证为基准 |

## 2. 报告章节设计（5 节，对应任务要求）

报告标题：《TrustBridge：委员会背书的 A2A 履约信任层——期末报告》。
课程背景信息（CS5298、日期 2026-10-30、仓库状态 HEAD 8d093b5、devnet 环境）置于封面页。

### 第 1 节 问题定义（约 1 页）

素材：`../FinalProject_方向总结_A2A信任桥.md`（课程目录根）+ 计划书。

| 数据点 | 出处（编码员逐字核对） |
|---|---|
| 一句话定义（信任保障层；中介作为协议而非平台） | 方向总结 :9-:13 |
| 课程要求（报告 ≥6 页、AI 声明必须含、11-19 提交） | 方向总结 :17-:27 |
| 三层定位表（通信层复用 A2A/MCP、信任层=本项目、计算层=LLM） | 方向总结 :69-:77 |
| 示范场景（版权授权市场 Alice/Bob/中介） | 方向总结 :79-:90 |
| 问题定义的正确写法（无可信中央平台担保） | 方向总结 :99-:103 |
| 竞品三层栈（ERC-8004/x402/AP2/A2A-MCP）与本项目空档 | 方向总结 :106-:119 |
| 副标题与摘要 | `../FinalProject_计划书_TrustBridge_2026-10-12.md` :1（标题）、:25（摘要卡）、:102（差异化论证骨架） |

### 第 2 节 架构（约 1.5 页）

| 数据点 | 出处 |
|---|---|
| escrow 状态机：Qualified→Funded→Submitted→Disputed→Settled/Refunded（**按证据写全阶梯**，任务简写「Funded→…」不照抄） | `w1b2-r2-adversarial.md` :74（状态阶梯字面）；计划书 §3.2（:76 起） |
| oracle 两阶段委员会认证（propose→aggregate→certified call；cert 门控资金路径；validate_cert 四查） | `w1b2-r3-e2-committee.md` §T1（th2/th4 聚合结论表）+ console :19-:37 流程序列；`implementation.md` §2.2 表（7 方法 × 门禁） |
| cert_probe 先例（机制已证的探针来源） | `implementation.md` :56（「先例 cert_probe lib.rs:110」注记）；W1-B1 原始探针档 `w1b1-s2-oracle.md`（如在则直引，不在则引 implementation.md 注记并注明去向） |
| keeper 驱动（native triggers 不可用实证 → keeper 轮询模式） | `w1b1-s1-timer.md` :94（「exactly-once 不满足…native trigger 不可依赖」）、:99（「native trigger 判定：不可用…主方案转 keeper 模式」） |
| NodeClient ETH 通道（eth_sendTransaction 主通道 + eth_call 读通道；estimateGas 不可用、自动注气） | `w1b2-s4-rpc.md` :121（estimateGas 结论）、:143-:144（主/读通道决策表） |
| 组件图（文字框图即可）：demo/keeper/NodeClient/lyquid 合约/4 节点 devnet | 综合上述；环境事实引 `implementation.md` §0 表（:28-:31 七容器、工具链） |

### 第 3 节 实验结果四阶段（约 2.5-3 页，报告主体）

**R0 超时退款实测**（素材 `w1b2-refunded-evidence.md`）：

| 数据点 | 出处 |
|---|---|
| tx hash `0x85e4e39b628a358ef7cd61bfc8c87e67a730c76617a823a6001a87ea86ae0838` | :14（keeper 输出原文）、:24（回执 txHash） |
| 回执：status 0x1 / block 104 / from=anvil#0(BROKER) / gasUsed 35996 | :20-:25 |
| `deal_info` 字面 `"state": "Refunded"`（退款前 `"Funded"`） | :37（后）、:43（前） |
| 余额勾稽 999002→1000002（+1000=全额退款，fee_bps 不参与退款） | :51-:54 |
| deadline 102 / claim 于 block 104（边界语义 104≥102） | :46-:47 |
| status=0x1 ≠ 方法成功的判读纪律（平台吞 Err） | :28-:30 |

**R1 接线**（素材 `w1b2-r1-s3-assess.md`）：

| 数据点 | 出处 |
|---|---|
| `assess_brief` 7×string→4×string（Stack too deep 平台限制）+ `export=eth` 恢复 | :184（S3-1 偏离行）、:80-:90（cast call 探针与返回） |
| selector `0x3297eeb6` 冻结进 rpc.py `_ABI` | :78-:79、:87 |
| heuristic 定值 `75/["heuristic-mode"]/60000/40` 与 assessor.rs:89 逐字一致 | :83-:86 |
| role key 表 + nudge/discover/assess 封装（S4） | git 提交 `f36d24e`（R1 S4: role key table + wrappers）；通道细节引 `w1b2-s4-rpc.md` §B |
| 真实 LLM 通道如实登记：egress 拒私网（策略原文）+ 无 TB_LLM_* 凭据 | :148-:152（egress 原文）、:161-:163（G-init ④） |

**R2 对抗流三裁决**（素材 `w1b2-r2-adversarial.md`）：

| 数据点 | 出处 |
|---|---|
| 三裁决终态表：Malicious(deal-6)→Refunded+misconduct 1→2；Fulfilled(deal-7)→Settled，bob +980/broker +20；NotFulfilled(deal-8)→Refunded 计数不增 | :84-:90（终态表）、:102-:105（console 四行原文） |
| 分账公式 `fee = 1_000×200/10_000 = 20`；Fulfilled 结算勾稽 bob 0→980、broker 0→20（980+20=1000），alice 49000→48000（fund 后）→48000（verdict 后） | :77-:78、:93-:94 |
| （注·仲裁修订 1）任务原文字面「9000/980/20」三数同现的在档记录为 R1 正常流 `w1b2-r1-demo-normal.md` :29（`final state=Settled balances: alice=9000 bob=980 broker=20`）与 :79（守恒式 9000+980+20=10000），与 R2 对抗流分属不同运行；**R2 档内无此三元组，三数出处不得标注为 R2** | — |
| misconduct 无 getter、println 为既有观测缝（累计视图语义） | :106-:111 |
| 编码器缺陷暴露与修复（attempt1 留档；head_size 偏移 0x20 错位；cast calldata 逐字节 MATCH） | :113-:135 |
| 实例余额守恒 77000+3920+80=81000 | :146-:157 |
| `--flow all` node 集成连跑（DEMO_EXIT=0，门控拆除验证） | :159-:172 |

**R3 E2 四节点认证 L2**（素材 `w1b2-r3-e2-committee.md` §T3/§T7）：

| 数据点 | 出处 |
|---|---|
| 判级 L2：`agreed … from 4 input(s) (avg_num=4)` + `cert.signers RAW = [0, 1, 2, 3] (len=4)` + 四条互异 signer→NodeID 映射 | :71、:73（对应 console :24/:31/:32-:35） |
| 实例 `Lyquid-ybidj3krshf4gqcjk3m3px6mooi6tg74twwaa` @ `0x87006e75a5B6bE9D1bbF61AC8Cd84f05D9140589` | :42 |
| 退款守恒 alice 10000→9000（fund −1000）→10000（退款 +1000），bob/broker 恒 0；faucet 链上单笔实证（blocks 0–341 仅 1 笔） | :98（勾稽表 #4） |
| arm 单次/读回断言/run_round 单次纪律；「两段 agreed 无重复结算」如实注记 | :95-:97、:87-:89 |
| D-T3-1 断言缺陷（stale baseline）与 T7 修复复验（新实例 `Lyquid-dpp6…unqa` exit 0、`DEMO COMPLETE`） | :106-:121（D-T3-1）、§T7 :164-:179 |
| 判级口径 L2/L1/L0 三层定义与诚实红线 | `docs/b3-user-test/通过判据.md` §1（:23-:36） |

**EVM 对照**（素材 `r3-t4-contrast-report.md`）：

| 数据点 | 出处 |
|---|---|
| 创建 gas 三值：EVM 1,936,008 / Lyquid R3 3,843,041 / R2 3,707,457（同链同 signer 直比口径） | :180-:187（④-4 表） |
| 代码量双口径：Escrow.sol 407 行 vs Lyquid 六文件 2083（含测）/1323（去测）vs 含 lib.rs 2933/2173 | :60-:83（①三列表+口径声明） |
| 信任假设对照（EVM 地址表委员会 vs 平台 NodeID 认证；本轮 EVM 成员含买卖双方的事实） | :85-:97（②表+如实说明） |
| 负对照：deal-3 三签重放 deal-4 被拒（`non-member signer`，rc=1） | :104（③表）、§3 清单 :232 |
| 单笔操作 gas 混合结论（EVM 部分高、fund 反而低；不做总量结论） | :251（结论 #4） |
| 结论六条（如实） | :246-:253（§4） |

### 第 4 节 信任假设与局限：诚实清单（约 1 页）

| 条目 | 出处 |
|---|---|
| oracle 路线②多节点认证 vs R2 单点 broker 签署的历史对比（eth 直调路径只做地址门不验签名，`lib.rs:222` 自述 TODO(W4)；两条路径强度不同、并列不合并） | `r3-t4-contrast-report.md` :93、:97 |
| 真实 LLM 未接（egress 策略 + 无凭据；heuristic 回放模式为当前形态） | `w1b2-r1-s3-assess.md` §3.4、`implementation.md` §6-#9 |
| misconduct 无 getter（仅 println 观测缝，非共识状态） | `r3-t4-contrast-report.md` :107 |
| B3 用户测试待线下（反馈收集表为空白表单、无已收集反馈） | `docs/b3-user-test/反馈收集表.md`（四维空白表）+ `implementation.md` §9.1 #6 |
| 对抗流 node 复跑仍未执行（R3-T6 授权面遗留） | `implementation.md` §7.5-#2 |
| EVM 对照口径限制（不同实例不合并、时间域差异、Lyquid 跨单重放无数据仅有代码路径） | `r3-t4-contrast-report.md` §0 阅读须知、:212-:221（数据缺口表） |
| devnet 单机 7 容器（非真实分布式部署，E2 加分项不主张） | `implementation.md` :28 |

### 第 5 节 AI 使用声明（约 0.5-1 页，如实）

分工（任务给定，报告如实陈述）：

| 角色 | 模型 | 职责 |
|---|---|---|
| 规划师 | GLM-5.3 | 方案撰写与终裁 |
| 编码员 | deepseek-flash | 编码实现与逐轮自审 |
| 审查员 | deepseek-flash（原生子代理） | 方案与代码逐轮审查 |
| 仲裁人 | GLM-5.3-Flash | 审查意见逐条处置与总结 |
| 终裁官 | GLM-5.3（冷上下文） | 轮数耗尽时裁定 |
| **人工（作者）** | — | **阶段决策、提交确认、终裁记录复核** |

佐证材料：`workflow-out/_collab/` 目录（`planner_sys.txt`、`planner_user.txt`、
`llm_call.py`、`probe_bigmodel.txt` 等多模型协作痕迹）；`implementation.md` 各轮
「仲裁修订登记」段落（如 :347-:361、:663-:696）与「终裁条款」引用（:3-:4）。

人工决策节点（有档可查；编码员从 git log 与 implementation.md 核对补全）：

1. **阶段重排决策**：W1-B2 中止、改 R0–R4 重排（git `136dc23` 提交信息明载）。
2. **提交确认**：R1–R3 全部提交经人工确认落地（`implementation.md` §10-1「主控按用户指令落地」；git `acb7315`…`3af0460`+`d292012`+`8d093b5`，本轮实跑 `git log --oneline -25` 在案）。
3. **T7 授权**：D-T3-1 修复端到端复验经用户授权「继续 R3」（`w1b2-r3-e2-committee.md` §T7 头注、`implementation.md` §10-2）。
4. **每阶段任务拆分与开工确认**：六阶段拆分①–④均为人工发起（本方案即拆分④）。

### 附：报告尾部

证据索引表（本方案 §2 各映射表的浓缩，供评卷人溯源）+ 构建信息
（reportlab 5.0.1、构建命令、总页数、生成日期 2026-10-30）。

## 3. 证据映射总表（诚实红线执行面）

编码员写作时**逐条对照** §2 各节表格「出处」列打开源文件核对字面值；审查员复核
按同一映射表（建议全查）。总则：

1. 所有 tx hash、地址、gas、行数、状态字面值只允许从 §2 所指文件抄录，禁止凭记忆。
2. `git log --oneline -25`（规划期已实跑，HEAD=8d093b5）是第 5 节提交序列依据；引用 hash 逐字对照。
3. 引用行号用「档内文件:行」格式，与 `r3-t4-contrast-report.md` 体例一致。
4. 仓库外素材（方向总结/计划书）按课程目录相对路径书写并注明。

## 4. 构建链（规划期已实测验证）

| 项 | 实测结果（本轮规划期命令） |
|---|---|
| reportlab | `python -c "import reportlab; print(reportlab.Version)"` → **5.0.1** ✅ |
| 中文字体 | `python -c "…pdfmetrics.registerFont(TTFont('MSYH', r'C:\Windows\Fonts\msyh.ttc'))…"` → **cjk-font-ok** ✅ |
| pandoc / xelatex / pdflatex | `where` 查询均失败 ❌（不可用） |

**主路径**：reportlab Platypus（A4、SimpleDocTemplate、MSYH 正文 + 等宽小号段落用于
tx hash/代码字面值、页眉页码、表格样式）。`build_report.py` 内嵌全部文案（SECTIONS
数据结构分层），一键 `python workflow-out/report/build_report.py` 产出 PDF。

**页数验证**（两路，结果写入 README）：
- 主：脚本内 `onPage`/`canvasmaker` 回调计数，构建结束打印 `TOTAL_PAGES=N`（N≥6 为过）；
- 复核：`python -c "import pypdf…"` 若可用则独立读页数交叉验证；不可用则如实登记「仅脚本自报页数」。

**降级路径**（任务规定；仅当 reportlab 编码轮意外不可用——规划期已证可用，预计
不触发）：交付 `report/report.md`（Markdown 源）+ README 逐字构建说明，并**显式**
登记「PDF 未构建+原因」。不得静默降级。

## 5. 子任务拆分与执行顺序（严格串行）

| # | 子任务 | 内容 | 产出 |
|---|---|---|---|
| T1 | 素材核对 | **开工第一动作（仲裁修订 2-b）：实跑 `git status --short`，输出逐字记入核对笔记（开工基线）**；随后按 §2 映射表逐条打开源文件核对字面值（行号漂移按实际行号引用并登记差异） | 核对笔记（含开工基线，并入 README 附表） |
| T2 | 撰写文案 | 按 5 节结构撰写中文报告全文，数字全部来自映射表 | 文案（内嵌于 build_report.py 数据结构） |
| T3 | 构建脚本 | 写 `build_report.py`（reportlab + MSYH + 页眉页码 + 表格样式 + 页数计数） | `report/build_report.py` |
| T4 | 构建与验证 | 跑构建 → PDF；验证：存在、非零大小、TOTAL_PAGES≥6、pypdf 复核（如可用）、抽查文本（pypdf 提取或人工开档，如实登记用哪条） | `report/trustbridge-final-report.pdf` + 验证输出 |
| T5 | README | 构建说明（环境/命令/验证输出）、证据索引、复现步骤、（如发生）降级登记；**开工基线九行随核对笔记并入「开工基线」小节存证（仲裁修订 2-b；README 即 §0 第 6 项，不新增第 7 个文件）** | `report/README.md` |
| T6 | 收尾自检 | §6 门禁逐项过；`git log --oneline -1` 仍 `8d093b5`；相对开工基线无越界新增（比对结果附门禁表） | 门禁表（交付回报内） |

## 6. 门禁总表（GT，验收口径）

| 门 | 判据 | 验证方式 |
|---|---|---|
| GT-a | PDF 存在、≥6 页、A4 中文渲染正常（无缺字方块） | T4 验证输出 + 人工开档抽查 |
| GT-b | 任务陈述列出的全部数字（0x85e4e39b / 3,707,457 / 3,843,041 / 407 / 0x8700…0589 / 10000→9000→10000 / misconduct 1→2 / 980 / 20 等）逐条在映射表所指档内文件可寻得 | 审查员按 §2/§3 全查 |
| GT-c | 零 git 写操作 | `git log --oneline -1` = `8d093b5`；全程无 add/commit/push |
| GT-d | 零越界写入 | `git status --short` 与 README 存证基线逐行比对：基线条目不减不改，新增仅 report/；lyquid/ scripts/ agents/ experiments/ docs/ 零改动 |
| GT-e | README 含逐字构建说明与证据索引，一键复现 | 复跑 `python workflow-out/report/build_report.py` 成功 |
| GT-f | 若走降级：目录有 Markdown 源 + README 显式登记「PDF 未构建+原因」 | 检查 README 降级段（主路径为「未触发」） |

## 7. 风险与回退

| # | 风险 | 概率/影响 | 缓解/回退 |
|---|---|---|---|
| R1 | reportlab 编码轮环境漂移（规划期 5.0.1 可用） | 低/高 | 降级路径（§4）：Markdown 源 + README 登记；不臆造构建成功 |
| R2 | TTC 子字体索引问题致中文渲染异常 | 低/中（规划期注册实测成功） | 备选依次 `simhei.ttf`、`simsun.ttc`；README 登记实际用字 |
| R3 | 页数不足 6 页 | 低/高 | 内容量按 §2 预估 7–10 页；不足则如实展开已在档证据（EVM 逐笔 gas 选摘、console 判级行引用），**不注水不重复** |
| R4 | 数字转录错误（诚实红线） | 中/高 | T1 前置核对 + 审查员映射表全查；发现即改 |
| R5 | 覆盖 plan.md 丢失旧方案 | 已消除 | 规划期已备份 `_plan-prev-r4d1-backup.md`（md5 双侧一致在案） |
| R6 | 源文件行号与映射表漂移 | 低/中 | T1 以实际行号为准并登记差异；引用语义不变 |
| R7 | 构建脚本排版 bug（表格溢出/断行） | 中/低 | Platypus 自动分页；超宽字面值（tx hash）小号等宽或允许断行；迭代修复 |

## 8. 明确不做（边界）

- 不修改任何证据档文件（`w1b2-*`、`_r*` 日志、`implementation.md`、B3 三文档、备份件）。
- 不新跑任何链上实验、不启动/不触碰 docker devnet（纯本地构建）。
- 不美化不外推：EVM 对照维持「不做单一结论」口径；L2 判级维持「console 原文可直读」口径；真实 LLM 未接如实写。
- 不执行任何 git 写操作（铁律第一条）。
