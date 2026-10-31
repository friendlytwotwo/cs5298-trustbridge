# R4-D2+D3 方案：幻灯片 + 预录 demo 脚本（规划师，2026-10-30）

六阶段拆分⑤：**纯文档任务**——D2 幻灯片（≥10 页 .pptx）+ D3 预录 demo 分镜脚本。
铁律第一条：**零 git 写操作**（不 commit/push/branch/tag/restore/stash；仓库已定格于
`8d093b5` 并推送 origin/main，本任务只读引用）。前置状态（规划期实跑核实）：
D1 报告三件已交付 `workflow-out/report/`（`README.md` 195 行 / `build_report.py` /
`trustbridge-final-report.pdf` 12 页，KEY_HITS 27/27）；R0–R3 证据、T4 对照报告、
T7 复验实录全部在档。

**工具链自验（规划期实跑，2026-10-30）**：
`python -c "import pptx; print(pptx.__version__)"` → **python-pptx 1.0.2 可用**；
`where pandoc` / `where marp` → 均未找到（信息: 用提供的模式无法找到文件）。
故 D2 主路径 = python-pptx 真出 `.pptx`（与 D1 reportlab 主路径同构），无降级预期。

## 0. 受影响文件清单（7 项，供审查员核对）

| # | 路径 | 动作 | 说明 |
|---|---|---|---|
| 1 | `workflow-out/plan.md` | 覆盖写 | 本方案；覆盖前旧 D1 方案已备份（#2） |
| 2 | `workflow-out/_plan-prev-r4d1-final-backup.md` | 新建（备份） | 规划期已执行：`cp` 复制旧 plan.md，md5 `771f2a109d13f687e77264304f9ef46a` 两侧一致（实跑输出在案） |
| 3 | `workflow-out/slides/build_slides.py` | 新建 | D2 幻灯片**唯一源文件**（python-pptx；全文 12 页以 Python 数据结构内嵌，仿 `report/build_report.py` 模式） |
| 4 | `workflow-out/slides/trustbridge-final-slides.pptx` | 新建（构建产物） | 16:9，12 页，每页含 speaker notes |
| 5 | `workflow-out/slides/README.md` | 新建 | 构建说明 / 验证命令与实跑输出 / KEY_HITS 一致性核对表 / 降级路径登记（仿 `report/README.md` 体例） |
| 6 | `workflow-out/demo-script.md` | 新建 | D3 预录 demo 分镜脚本（分镜表 + 录制技巧 + 风险预案） |
| 7 | `workflow-out/_r4d2d3-verify-raw.txt` | 新建 | 验证段实录（构建自检 + KEY_HITS 抽查 + git 收尾存证的原始输出） |

只读素材（不改，编码期引用）：`workflow-out/report/README.md`（KEY_HITS 唯一事实源）、
`report/build_report.py`（构建模式参考）、`workflow-out/implementation.md`、
`w1b2-r3-e2-committee.md`、`r3-t4-contrast-report.md`、`_r3-t3-{console,committee,deploy,final-state}-raw.txt`、
`_r3-t7-dt31-verify-raw.txt`（**S5-① 主命令与预期输出对齐源**，仲裁修订 2）、
`_r2-{normal-assess,keeper-loop}-raw.txt`（后者为 **S4 回放主档**，仲裁修订 1）、
`_r1-demo-normal-raw.txt`、`w1b2-{refunded-evidence,r1-demo-normal,r1-s3-assess,r2-adversarial}.md`。
**禁改**：`lyquid/`、`scripts/`、`docs/`、`experiments/`、`agents/`（纯文档轮，全部只读；
`scripts/demo.py:346-357` 仅作只读引用佐证 S4 例外句，不改动）。

## 1. 目标与完成判据

**D2**：`workflow-out/slides/` 下交付 源 + 产物 + README 三件；`.pptx` ≥10 页（本方案定
12 页），每页带 speaker notes；全部数字/tx/地址与 `report/README.md` KEY_HITS 一致。
**D3**：`workflow-out/demo-script.md` 分镜表（镜号/画面/命令/预期输出/时长五列），
总时长 5±1 分钟（240–360 秒），命令逐字取自已档实录且带「出处文件:行」标注。
**共同红线**：零 git 写操作；只写 §0 清单 7 个新文件；不碰代码目录。

## 2. 冻结条款（编码员必守）

1. **零 git 写**：全程仅允许 `git log` / `git status` / `git diff` 只读命令；开工与收尾
   各存证一次 `git log --oneline -1`（期望逐字 `8d093b5 R3 evidence: D-T3-1 fix E2E
   re-verification on fresh instance (T7)`）与 `git status --short`。
2. **数字唯一事实源 = `workflow-out/report/README.md`**（§3 KEY_HITS 27 项 + §5 证据
   索引表）。**三数口径铁律（上一轮终裁已纠正过任务原文误标，不得重蹈）**：
   - `9000 / 980 / 20` 三数同现 = **R1 正常流分账**（`w1b2-r1-demo-normal.md:29、:79`）；
   - **R2 Fulfilled 结算** = bob +980 / broker +20（alice 49000→48000→48000，
     `w1b2-r2-adversarial.md:77-:78、:89`——:77 结算字面值行、:78 split check、
     :89 G6B Fulfilled 行；仲裁修订 3 更正：原引 :102-:105 实为 apply_verdict 行，
     数字本身不变）；R2 对抗流档内**没有** 9000/980/20 三元组（核实无误，保留）；
   - `9000` 作为独立数值 = **R3 funding 中间态**（alice 10000→9000→10000，
     `w1b2-r3-e2-committee.md:98`）。
   幻灯片与分镜中每处数字须带出处标注；与 KEY_HITS 不一致时以 KEY_HITS 为准并登记差异。
3. **只写新文件**：§0 清单之外零写入（含不得修改 `_plan-prev-*` 既有备份件）。
4. **D3 命令逐字实录**：命令列从 `_r3-t3-*` / `_r2-*` / `_r3-t7` 已档实录头部与正文
   提取（实录头部多带 `# command:` 行），不改写参数顺序、不虚构；预期输出逐条对齐
   实录原文行并标 `文件:行`。
5. **构建自检即退出码**：`build_slides.py` 末段自检（页数 / notes 全非空 / KEY_HITS
   字面值抽查）全过才 `BUILD_OK` 退出 0；任何一项不过即非零退出并打印缺失清单。
6. **不嵌字体**：pptx 中文字体名设 `Microsoft YaHei`、console 块用 `Consolas`；字体
   不嵌入，目标机器缺字体时的替代表现写入 `slides/README.md`（如实登记，不算缺陷）。

## 3. D2 幻灯片逐页设计（12 页，16:9）

> 每页列：标题 / 正文要点（数字全部带 KEY_HITS 出处）/ speaker notes 要点。
> 页面文字求精炼（要点式），speaker notes 承载完整口径与出处（含「文件:行」）。

| 页 | 标题 | 正文要点（出处） | speaker notes 要点 |
|---|---|---|---|
| P1 | 封面 | 题目「TrustBridge：基于 Lyquid 平台的 A2A 交易信任桥」；副题 CS5298 期末项目；作者；日期 2026-10-30；基线 HEAD `8d093b5`（KEY_HITS 项） | 一句话定位：四阶段（R0–R3）+ EVM 对照 + 12 页期末报告已交付 |
| P2 | 动机：A2A 信任桥问题 | agent-to-agent 交易缺托管与仲裁层；LLM 评估不可信（R1 真实 LLM 未接：egress 拒私网 `172.18.0.2`、无 `TB_LLM_*` 凭据，`w1b2-r1-s3-assess.md:151、:161-163`）；跨主体资金安全（退款/分账/违约计数） | 为什么不是纯 EVM escrow：引 P6 对照伏笔（地址表委员会含买卖双方） |
| P3 | 架构一页 | ① deal 状态机：Qualified→Funded→（Disputed）→Settled/Refunded（R0 字面 `"state": "Funded"`→`"Refunded"`，`w1b2-refunded-evidence.md:37`）；② oracle 两阶段委员会：staging（e2_configure）→advance/finalize epoch→propose/aggregate（avg_num=4）→`committee_verdict_certified`（cert.signers + validate_cert 四查）；③ keeper 守门人（claim_timeout，deadline_slot 到期退款）；④ NodeClient 通道（eth JSON-RPC + 容器 cast 双通道，宿主直连四端口 10087/11087/12087/13087） | 各组件与 R 轮对应：状态机 R0、接线 R1、三裁决 R2、委员会 R3（引 implementation.md §2） |
| P4 | 演示实录摘录：R3-T3 E2 判级 L2 | console 原文两行（等宽块逐字）：`e2_aggregate: agreed deal=deal-1 verdict=1 from 4 input(s) (avg_num=4)`（`_r3-t3-console-raw.txt:24`）；`committee_verdict_certified: cert.signers RAW = [0, 1, 2, 3] (Vec<SignerID>=Vec<u32>, len=4) deal=deal-1 verdict=1`（`:31`）；判级口径 L2 = 4 提案 + 4 签（`docs/b3-user-test/通过判据.md:23-36`） | 读法讲解：inputs=4（:24，四条 Node 输入行 :20-23 佐证）+ signers=4（:31）+ 四条 signer→Node 映射互异（:32-35）；agreed 行重复两次但 certified/apply 各一次→无重复结算（`w1b2-r3-e2-committee.md:87-89`） |
| P5 | 退款守恒与读回勾稽 | R3 实例 `Lyquid-ybidj3krshf4gqcjk3m3px6mooi6tg74twwaa` @ `0x87006e75a5B6bE9D1bbF61AC8Cd84f05D9140589`（KEY_HITS）；alice 10000 →（fund −1000）9000 →（退款 +1000）10000；bob/broker 恒 0（`w1b2-r3-e2-committee.md:98`）；faucet 全链仅 1 笔（block 333）；T7 新实例复验 exit 0 / `DEMO COMPLETE`（`Lyquid-dpp6…unqa` @ `0x942ED2fa…f01e`，`w1b2-r3-e2-committee.md:164-179`） | **口径强调**：9000 在此是 funding 中间态（铁律三数口径）；status≠effect，一切以读回为准（KEY_HITS R0 判读纪律行） |
| P6 | 实验对照表：纯 EVM Escrow vs Lyquid（四维） | 表四行：① 创建 gas 1,936,008（EVM）/ 3,843,041（Lyquid R3）/ 3,707,457（Lyquid R2）（`r3-t4-contrast-report.md:180-187`）；② 代码量 407（Escrow.sol）vs 2083/1323（六文件含测/去测）vs 2933/2173（含 lib.rs 双口径）（`:60-83`）；③ 信任假设：地址表委员会（`Escrow.sol:81-83/:108`，本轮含买卖双方）vs 平台注册 4 NodeID + threshold=4；④ 裁决不可篡改：EVM 负对照实证（deal-3 三签重放 deal-4 被拒 `non-member signer` rc=1，`:104、:232`）；Lyquid 侧同型实验无数据（如实） | 口径声明：R2/R3 两实例并列不合并；「无数据（原因）」写法沿用报告纪律 |
| P7 | 对照要点解读（诚实口径） | 部署环节 EVM 更低（约 1.98×）；单笔操作无单向结论（createDeal EVM 226,658 vs Lyquid 47,908；fund 反而 EVM 32,713 更低，`r3-t4-contrast-report.md:251`）；行数差不能直接读成复杂度差（Escrow 无单元测试，验证等价物 = 三流+负对照）（`:252`） | 结论克制：不做「谁更便宜」总量结论；两侧工作量不同（20 笔 vs 14 笔） |
| P8 | 里程碑时间线（R0→R3） | R0（2026-10-28）keeper 退款：Funded→Refunded，tx `0x85e4e39b…0838`，999002→1000002，deadline_slot 102 / claim@104（KEY_HITS R0 行）；R1（2026-10-29）接线 + 正常流：Settled，分账 alice=9000 / bob=980 / broker=20（`w1b2-r1-demo-normal.md:29、:79`）；assess_brief 7→4 string（Stack too deep），selector `0x3297eeb6`；R2（2026-10-29）三裁决：Malicious→Refunded（misconduct 1→2）/ Fulfilled→Settled（bob+980、broker+20）/ NotFulfilled→Refunded；实例守恒 77000/3920/80（sum 81000）；R3（2026-10-30）E2 委员会判级 L2（inputs=4 + signers=[0,1,2,3]） | **三数口径复述**（notes 里逐条对 KEY_HITS：R1 三元组 / R2 Fulfilled 结算 / R3 funding 中间态）；R1 真实 LLM 未接如实提 |
| P9 | 信任假设与局限（诚实清单） | 七条：真实 LLM 未接（heuristic 75/["heuristic-mode"]/60000/40）；misconduct 无 getter（仅 console 行）；B3 线下测试未收集；对抗流 node 复跑未执行；对照口径限制（两实例不合并、单机 devnet）；eth 直调路径弱门（`lib.rs:222` TODO(W4)）；status≠effect 平台吞 Err（`_r2-adversarial-raw.txt:6`）（KEY_HITS 局限清单行：`r3-t4-contrast-report.md:107、:212-221`；`implementation.md:28、:407、:511、:603`） | 每条一句「为什么留着」；与报告 §4 局限表同源 |
| P10 | 结论 | 四阶段全链在 devnet 实证（退款/结算/三裁决/4-of-4 认证）；E2 认证是额外信任层、代价可量化（部署 gas 约 1.98×、认证回合 propose 1 + aggregate 10 行 + 回调 1 笔）；诚实边界同 P9 | 一句话总结：信任桥的核心链路全部有读回证据，未证的如实标注 |
| P11 | 后续工作 | W2'/W3：probe SPIKE 清理与 oracle 路线收敛；真实 LLM 接入（`TB_LLM_*` 凭据）；B3 线下用户测试（三文档已备：`docs/b3-user-test/`）；D-T3-1 已修复并 T7 复验（遗留：对抗流 node 复跑） | 与报告 §5/后续清单对齐 |
| P12 | 封底：证据索引与声明 | 证据索引指 `report/README.md` §5（浓缩表同 PDF 附录 A）；AI 使用声明同报告 §5；产物指引：报告 PDF 12 页 / 本幻灯片 / demo 脚本 `workflow-out/demo-script.md` | 口径：全部数字可溯源到「文件:行」 |

### 3.1 `build_slides.py` 技术要点

- python-pptx 1.0.2；`Presentation()` 默认 4:3 → 显式设 `slide_width=Inches(13.333)`、
  `slide_height=Inches(7.5)`（16:9）。
- 版式：`blank` 版式 + 自绘文本框（标题条 / 正文区 / 页脚「第 X / 12 页」）；对照表与
  时间线用 python-pptx 表格（`add_table`）；console 摘录用等宽 `Consolas` 文本框，
  **长行不折断**（摘录行本身 ≤100 字符，选行时已核）。
- speaker notes：每页 `slide.notes_slide.notes_text_frame.text = <完整口径+出处>`。
- 字体：标题/正文 `Microsoft YaHei`；不嵌入（冻结条款 6）。
- 构建后**同进程自检**（脚本尾段，全过才打印 `BUILD_OK` 并退出 0）：
  (a) 重开产物文件，`len(slides)==12` 且 ≥10；(b) 每页 notes 非空；
  (c) 全文本（含 notes）KEY_HITS 字面值抽查 ≥15 项（清单见 §6 GT-b）；
  (d) 误标反向检查（GT-b′ 护栏）：P5 正文必须含完整链条字样 `10000 → 9000 → 10000`
  （或以实际所用箭头字符在脚本内常量声明后程序化拼接比对）；`9000 / 980 / 20`
  三元组字样只允许出现在 P8（R1 时间线条目）与 P8 notes——自检按「出现页集合 ⊆ {P8}」判。

## 4. D3 预录 demo 分镜设计（`workflow-out/demo-script.md`）

### 4.1 分镜表（8 镜，合计 305 秒 ≈ 5 分 05 秒，落在 5±1 分钟内）

> 五列：镜号 / 画面 / 命令（逐字，带出处）/ 预期输出（对齐实录，带行号）/ 时长。
> 「实例说明」：S1–S3 主路径 = **新部署实例实跑**（命令序列照实录形态，实例名/地址/
> TARGET 每轮不同——分镜表逐处注明「以当轮输出为准」；金额/状态/判级行逐字可对）。
> **S4 例外（仲裁修订 1）：主路径即实录回放**——keeper claimed 为 R2 轮一次性链上
> 事件，deal-3 已 terminal（`_r2-keeper-loop-raw.txt:11-13` 三条 `action": "terminal"`
> 行；`w1b2-r2-adversarial.md:148`「deal-1..3 Refunded（超时/keeper）」行——仲裁原引
> :148 经 grep -nF/sed -n 复核无误：:147 = balances 行、:148 = deal-1..3 Refunded 行、
> :149 = deal-5..8 行；上一轮误改为 :147，本轮回正），重跑仅
> 得 terminal；新实例无到期 deal，且 `scripts/demo.py` 的 timeout 流在 node 模式自行
> nudge+claim（`demo.py:346-357`：`while … node.nudge()` + `call(node, "claim_timeout", d)`）
> 不留待 keeper，故**不设实跑 setup 镜**。**S5 主路径 = 命令行展示 + T7 实录输出回放**
> （见 S5 行；仲裁修订 2）。备用路径 = 全实录回放模式（见 §4.3 预案 A）。

| 镜 | 画面 | 命令（出处） | 预期输出（实录对齐） | 时长 |
|---|---|---|---|---|
| S0 | 标题卡（幻灯片 P1） | —（口播） | — | 20s |
| S1 | 终端：devnet 检查 | `docker ps --format "{{.Names}} {{.Status}}"`（形态出处 `implementation.md` §7.2 T3.0；同型输出 `_r3-t4-precheck-raw.txt:5-12`） | 7 容器 Up：multi-tools / multi-node1..4 / multi-registry / multi-anvil | 20s |
| S2 | 终端：部署（或复用）实例 | 主路径：`docker exec multi-tools rm -rf /tmp/tb-lyquid` + `MSYS_NO_PATHCONV=1 docker cp lyquid/. multi-tools:/tmp/tb-lyquid` + 容器内 `cargo check --target wasm32-unknown-unknown` + `shaker deploy -r http://registry:8000/lyquids --endpoint ws://node1:10087/ws --private-key <ANVIL0_KEY> Cargo.toml`（形态出处 `implementation.md` §7.2 T3.1；`_r3-t3-deploy-raw.txt` [QUOTED] 段）；快路径（复用已 Up 实例，备用镜）：`docker exec multi-tools shaker to-hex <实例名>` → 42 字符 TARGET | `created Lyquid-<新名> => 0x<新地址>`、`[deploy exit=0]`（形态对齐 `_r3-t3-deploy-raw.txt` 关键行；实例名/地址以当轮为准）；to-hex 形态实例：`0xc05034ED5191cbc3404956D9b7dFcC7391e99bfc`（T3 实录 42 字符，`_r3-t3-deploy-raw.txt:584` 同值） | 40s |
| S3 | 终端：正常流一条龙（**新部署实例实跑**，单一口径） | `python scripts/demo.py --node http://127.0.0.1:10087 --contract <addr> --flow normal`（命令形态出处 `_r2-normal-assess-raw.txt:3`；`<addr>` = **S2 当轮新部署实例地址**，以当轮 deploy/to-hex 输出为准——该实录 :2 的 `0xFD6F…c351` 为已用实例，**禁填**） | `FLOW 1 — normal: assess -> escrow -> deliver -> settle` → `deal=deal-1 info={…'state': 'Qualified'…}` → `final state=Settled`；分账口播/字幕引 **R1 首次正常流** `final state=Settled balances: alice=9000 bob=980 broker=20`（`_r1-demo-normal-raw.txt:6`；`w1b2-r1-demo-normal.md:29、:79`；R1 亦为零起点实例，同形预期；当轮以新实例实录为准）→ `DEMO COMPLETE`（`_r1-demo-normal-raw.txt:9`）。⚠ `_r2-normal-assess-raw.txt:12-:13` 为**已用实例**输出（deal-9 / 58000/1960/40），不得作为 S3 新实例预期来源。**条件分支**：若 S2 走「复用已 Up 实例」快路径，S3 余额**不得**引 R1 9000/980/20，须以当轮实例实录为准 | 60s |
| S4 | 终端：超时流 keeper（**实录回放镜**，字幕「本镜为已档实录回放（2026-10-29 R2-T6-A 轮）」） | 主路径 = 打开/讲解 `_r2-keeper-loop-raw.txt` 实录（画面即原文，**无执行命令**）；该档出处命令（讲解行，不执行）：`python scripts/keeper.py --node http://127.0.0.1:10087 --contract <addr> --deals deal-3 --interval 5`（`:3` 命令形态，`<addr>` 占位；实例地址逐字见 `:2`（instance 0xFD6F…c351）与 `:7`（contract=0xFD6F…）） | 逐字对齐该档：`[keeper] explicit deals: ['deal-3']`（:6）→ `[keeper] watching ['deal-3'] every 5s`（:8）→ `[keeper 23:39:22] deal-3: {"state": "Refunded", "action": "claimed", "tx": "0x4095005c0e72c139fb99f630d8e20b7ef005596a88dfac8b1fec8717cd5ada02"}`（:10）→ 归因 `ATTRIBUTION VERDICT: PASS`（:30）；口播：keeper 自己的 nudge 挖出过线块（:31-32）。GT-d 对 S4 的口径 = 预期输出行逐一 `grep -nF` 命中该档实录（命令列无执行命令，不参与 grep 项） | 45s |
| S5 | 终端×2：E2 委员会认证 + console 判级（主画面 = 命令行展示 + 实录输出回放） | ①**主命令（`_r3-t7-dt31-verify-raw.txt:3` 逐字）**：`python scripts/demo.py --node http://127.0.0.1:10087 --contract 0x942ED2fa862887Dc698682cc6a86355324F0f01e --instance Lyquid-dpp6ird6knahaun6dokpi6ki2pdnbjxdfunqa --flow committee`——主画面展示该命令行 + T7 实录输出回放（T7 实例 deal-1 已终态，且受 arm/run_round 单次纪律约束，不对该实例重发；若需当轮实跑须换**新实例**执行同型命令，`--contract/--instance` 换当轮值，输出形态对齐本列）。**可选**「已档实录回放」画面（不执行）：`python scripts/demo.py --node http://127.0.0.1:10087 --contract 0x87006e75a5B6bE9D1bbF61AC8Cd84f05D9140589 --instance Lyquid-ybidj3krshf4gqcjk3m3px6mooi6tg74twwaa --flow committee`（`_r3-t3-committee-raw.txt:2` 逐字）②`MSYS_NO_PATHCONV=1 timeout 60 docker exec multi-tools shaker console Lyquid-ybidj3krshf4gqcjk3m3px6mooi6tg74twwaa --endpoint ws://node1:10087/ws`（`_r3-t3-console-raw.txt:2` 逐字；只读流式回放） | ①主路径对齐 T7 实录：`[committee] faucet read-back OK: alice 0 -> 10000 (+10000)`（`:22`）→ `arm read-back OK: armed_deal == deal-1 (pre-arm='')`（`:28`）→ `final state=Refunded balances after={'alice': 10000, 'bob': 0, 'broker': 0}`（`:30`）→ `refund check OK: alice 10000 -> 9000 (after fund) -> 10000 (after verdict); bob/broker unchanged`（`:31`）→ `DEMO COMPLETE`（`:69`）→ `EXIT=0`（`:72-73`）。可选 T3 档若展示，预期输出**必须补** `RuntimeError: [committee] refund accounting mismatch: before={'alice': 0, …}`（committee-raw:41）与 `# demo exit=1`（:43），字幕注明「T3 轮档案（D-T3-1 修复前），单次纪律已在该轮用毕」②判级行（console 实录回放，字幕注明 T3 实例名与「实录回放」——`w1b2-r3-e2-committee.md:141` 口径：console 档为判级唯一依据、rc=124 正常收尾）：`agreed deal=deal-1 verdict=1 from 4 input(s) (avg_num=4)`（console:24）+ `cert.signers RAW = [0, 1, 2, 3] (len=4)`（:31）+ `apply_verdict: deal=deal-1 verdict=1 misconduct=[]`（:36）+ `deal_info … "state":"Refunded"`（:38） | 60s |
| S6 | 表格画面：EVM 对照要点 | —（数据画面，不出终端） | 创建 gas 1,936,008 vs 3,843,041 / 3,707,457（`r3-t4-contrast-report.md:180-187`）；代码量 407 vs 2083/1323 与 2933/2173 双口径（`:60-83`）；负对照 `non-member signer` rc=1（`:104、:232`）；口播：不做单一「谁更便宜」结论 | 40s |
| S7 | 收尾卡 | —（口播 + 报告封面画面） | 指引：12 页报告 `workflow-out/report/trustbridge-final-report.pdf` + 证据索引 `report/README.md` §5 | 20s |

合计 305s（20+20+40+60+45+60+40+20）。表后附「时长合计行」与 5±1 分钟判据说明。

### 4.2 编排与文案要求

- 每镜附「口播要点」两三句（分镜表下的分镜小节）；S3/S5 口播**必须**点出三数口径
  （S3：R1 正常流 9000/980/20；S5：10000→9000→10000 是 funding 中间态，全额退款）。
- 每条命令旁标注「出处文件:行」；命令块可整体复制执行；`<addr>`/`<实例名>`/
  `<ANVIL0_KEY>` 占位符逐一说明替换规则（占位符登记为「录制时替换」，不算虚构）。
- S2 主/备双路径都写全（部署 40s 讲不完整时的引导词：只展示 to-hex 与 created 行）。

### 4.3 录制技巧与风险预案（附后章节）

- **技巧**：终端字号 ≥18pt、深底浅字；每镜独立起止（便于单镜重录）；S5 双终端分屏或
  快切；console 是流式回放（历史事件可达，`implementation.md` §4-9b 实证 305 行），
  `timeout 60` 到点 `rc=124` 是**正常**收尾，字幕注明防误读。
- **预案 A（devnet 不可用）**：全镜头改「实录回放模式」——`cat`/编辑器打开已档日志
  逐段讲解（S3↔`_r1-demo-normal-raw.txt`、S4↔`_r2-keeper-loop-raw.txt`、
  S5↔`_r3-t3-console-raw.txt`），画面即实录原文，零执行风险；片头字幕登记
  「本片为已档实录回放（2026-10-28/29/30 轮次），非当轮实跑」。
- **预案 B（某镜失败重录点）**：S2 部署失败 → 切备用镜（to-hex + 引已档 created 行）；
  S3/S5 实跑失败 → 保留失败前的成功镜，失败镜改实录回放并在片尾差异登记；
  **S4 无重录点**（本镜即回放，仲裁修订 1）。
- **纪律（照 plan 惯例）**：绝不重复 `e2_arm` / `e2_run_verdict_round`（单次纪律）；
  `MSYS_NO_PATHCONV=1` 前缀必带（Git Bash 路径改写，D-T6-1 / 操作手册 §2.1 教训）；
  演示实例与证据实例不混称（S5 引 T3 实例判级行时字幕注明实例名）。

## 5. 子任务拆分与执行顺序

| # | 子任务 | 内容 | 产物 |
|---|---|---|---|
| T1 | 开工基线存证 | `git log --oneline -1` + `git status --short` 只读存证；复跑工具链自验（`python -c "import pptx…"`） | `_r4d2d3-verify-raw.txt` 头段 |
| T2 | （规划期已完成）方案落盘与备份 | 本文 + `_plan-prev-r4d1-final-backup.md`（md5 已对） | plan.md |
| T3 | D2 源文件编写 | `slides/build_slides.py`（§3 逐页数据结构 + §3.1 技术要点 + 尾段自检） | build_slides.py |
| T4 | D2 构建与自检 | `python workflow-out/slides/build_slides.py` → `.pptx` 落盘 + `BUILD_OK`；实跑输出入档 | trustbridge-final-slides.pptx + verify-raw 中段 |
| T5 | D2 README | 构建/验证/复现命令 + KEY_HITS 一致性核对表 + 字体不嵌入登记 | slides/README.md |
| T6 | D3 分镜脚本编写 | `demo-script.md`：§4 分镜表 + 口播要点 + 技巧/预案；**前置**：编码员全文读 `_r2-normal-assess-raw.txt`（S3 预期输出按原文填，不预填） | demo-script.md |
| T7 | 交叉核对 | ①`demo-script.md` 与 KEY_HITS 数字逐条对（重点三数口径）；②slides 与 demo-script 口径一致（同一数字两处不矛盾）；③每条命令 `grep -nF` 回实录逐字验证；④**（仲裁修订补；冷读轮扩为 S3/S4/S5）全部预期输出行逐一 `grep -nF` 回对应实录**——S4 行回 `_r2-keeper-loop-raw.txt`、S5-① 主路径行回 `_r3-t7-dt31-verify-raw.txt`、S5-① 可选 T3 档行回 `_r3-t3-committee-raw.txt`、S5-② 行回 `_r3-t3-console-raw.txt`、**S3 三条预期行（deal=deal-1 行、balances 行、DEMO COMPLETE）编码期静态命中 R1 档 :5/:6/:9，录制当轮命中当轮新实例实录** | 核对记录（含 ④ 的逐行命中输出）入 verify-raw |
| T8 | 收尾存证 | 复跑 `git log --oneline -1`（期望仍 `8d093b5`）+ `git status --short`（期望新增仅 §0 清单件）；全程零 git 写确认 | verify-raw 尾段 |

顺序：T1 → T3 → T4 → T5 → T6 → T7 → T8（T2 已完成）。T7 发现不一致 → 修产物重跑对应验证。

## 6. 验证门（GT，编码员执行并如实登记）

| 门 | 判据 | 验证方式 |
|---|---|---|
| GT-a | `.pptx` 存在且 ≥10 页（方案值 12）、每页 notes 非空 | `build_slides.py` 尾段自检（重开产物遍历）；实跑输出入 `_r4d2d3-verify-raw.txt` |
| GT-b | KEY_HITS 字面值抽查 ≥15 项命中 pptx 全文本（含 notes）；候选清单：`3,843,041`、`3,707,457`、`1,936,008`、`0x87006e75a5B6bE9D1bbF61AC8Cd84f05D9140589`、`0x942ED2fa862887Dc698682cc6a86355324F0f01e`、`0xFD6F7A6a5c21A3f503EBaE7a473639974379c351`、`inputs=4`、`[0, 1, 2, 3]`、`1000002`、`999002`、`77000`、`3920`、`81000`、`407`、`2083`、`1323`、`2933`、`2173`、`980`、`8d093b5`、`2026-10-30`、`non-member signer`、`misconduct` | 自检脚本内程序化抽查（python-pptx 遍历 shapes + notes）；MISSING 清单打印 |
| GT-b′ | 三数口径护栏：`9000`+`980`+`20` 三元组字样仅现于 P8（R1 语境）；P5 含完整链 `10000 → 9000 → 10000` 字样；全片不出现「R2 且 9000/980/20」表述 | 程序化检查（§3.1-(d)）+ 人工复核（复核记录入 verify-raw） |
| GT-c | demo-script 分镜表时长列合计 240–360 秒 | 表内合计行 + 加总说明（305s 设计值） |
| GT-d | demo-script 每条命令带「出处文件:行」且 `grep -nF` 能在对应实录逐字命中（`<addr>`/`<实例名>`/`<ANVIL0_KEY>` 占位符除外，逐一列明替换规则）；**S4 例外口径**：主路径无执行命令，验证对象 = 预期输出行（:6/:8/:10/:30/:31-32）逐一 `grep -nF` 命中 `_r2-keeper-loop-raw.txt`，出处命令行（:3 形态）单独核对；**S5 新口径**：主命令 `grep -nF` 命中 `_r3-t7-dt31-verify-raw.txt:3`（去 `# command: ` 前缀），预期输出行 :22/:28/:30/:31/:69/:72-73 逐一命中该档，可选 T3 档行命中 `_r3-t3-committee-raw.txt`（:2/:41/:43），console 行 :24/:31/:36/:38 命中 `_r3-t3-console-raw.txt`；**S3 口径（冷读轮补）**：命令形态命中 `_r2-normal-assess-raw.txt:3`；三条预期行（deal=deal-1 'Qualified' 行、balances 行 `final state=Settled balances: alice=9000 bob=980 broker=20`、`DEMO COMPLETE`）编码期静态核对命中 R1 档（`_r1-demo-normal-raw.txt:5/:6/:9`），录制当轮再逐一 `grep -nF` 命中当轮新实例实录并记录；**禁引** R2 档 :12-:13（已用实例 deal-9 / 58000/1960/40） | T7 逐条 grep，结果入 verify-raw |
| GT-e | 收尾 `git log --oneline -1` 逐字仍 `8d093b5`；`git status --short` 相对 T1 开工基线：新增仅 §0 清单件（slides/ 3 件 + demo-script.md + 备份件 + verify-raw；plan.md 为 M） | T8 只读存证比对 |
| GT-f | 差异登记段：任何与 KEY_HITS 不一致处、任何降级（工具链失败走 marp/beamer 源）如实列表；无差异写「无」 | slides/README.md §4 + demo-script.md 尾节 |

## 7. 风险与回退

| # | 风险 | 缓解/回退 |
|---|---|---|
| R1 | 执行期 python-pptx 不可用（规划期已实跑 1.0.2 排除） | 若 import 失败：降级交付 marp 源（.md）+ 构建说明，slides/README.md 如实登记「未真出 .pptx」；不得谎称已构建 |
| R2 | **数字误标（最大风险，尤其三数口径）** | 冻结条款 2 铁律 + GT-b′ 程序化护栏 + T7 人工逐条复核；不一致以 KEY_HITS 为准并登记 |
| R3 | pptx 中文/等宽渲染（字体不嵌入） | README 登记目标机字体要求（Microsoft YaHei / Consolas）；缺字体时系统替代不致内容丢失 |
| R4 | 文本抽取盲区（组合形状/表格内文字） | 自检遍历含 table cells、group shapes 递归与 notes_slide |
| R5 | 覆盖 plan.md 丢旧内容 | 已备份 `_plan-prev-r4d1-final-backup.md`（md5 两侧一致，实跑在案） |
| R6 | demo-script 命令与实录不符/预期输出虚构 | 冻结条款 4 + GT-d 逐条 grep；S3 的 R2 normal 余额必须读全文后按原文填，读不到就标「无数据（原因）」 |
| R7 | 误触 git 写操作 | 只允许 git log/status/diff；GT-e 开工/收尾双向存证 |
| R8 | 构建环境异动（Python 版本等） | 无网络依赖、无第三方新装（python-pptx 已在位）；失败即走 R1 降级路径 |

## 8. 规划期已实跑的命令与输出（供编码员复核基线）

```
$ cd trustbridge && git log --oneline -1
8d093b5 R3 evidence: D-T3-1 fix E2E re-verification on fresh instance (T7)
$ python -c "import pptx; print(pptx.__version__)"
1.0.2
$ where pandoc    /    $ where marp
信息: 用提供的模式无法找到文件。 （两者均未找到）
$ python --version
Python 3.14.5
$ cp workflow-out/plan.md workflow-out/_plan-prev-r4d1-final-backup.md
$ md5sum workflow-out/plan.md workflow-out/_plan-prev-r4d1-final-backup.md
771f2a109d13f687e77264304f9ef46a *workflow-out/plan.md
771f2a109d13f687e77264304f9ef46a *workflow-out/_plan-prev-r4d1-final-backup.md
```

勘察文件（规划师实读，均只读；首轮 16 个 + 修订轮核实 4 项）：`report/README.md`（全文）、
`_r3-t3-console-raw.txt`（全文）、`_r3-t3-committee-raw.txt`（头部 + 修订轮补 :40-43 尾段）、
`w1b2-r3-e2-committee.md`（全文）、`_r3-t3-deploy-raw.txt`（头部与关键行）、
`_r2-keeper-loop-raw.txt`（全文）、`_r2-normal-assess-raw.txt`（头部）、
`_r1-demo-normal-raw.txt`（全文）、`r3-t4-contrast-report.md`（全文）、
`implementation.md`（全文）、`_r3-t7-dt31-verify-raw.txt`（修订轮全文 77 行，行号 :3/:22/:28/:30/:31/:69/:72-73 逐一核实）、
`w1b2-r2-adversarial.md`（头部 + 修订轮补 :70-95、:146-155 段，:77/:78/:89/:147 逐一核实）、
`scripts/demo.py`（修订轮只读 :346-357 段，S4 例外句佐证）、
`w1b2-refunded-evidence.md` / `w1b2-r1-demo-normal.md` / `w1b2-r1-s3-assess.md`（各头部日期/实例行）、
`plan.md`（覆盖前头部确认）。

## 9. 仲裁修订记录（修订轮 + 冷读仲裁轮，2026-10-30）

1. **S4 改实录回放为主路径**：命令列主路径 = 讲解 `_r2-keeper-loop-raw.txt`（无执行
   命令）；keeper.py 命令降为出处命令讲解行（:3 形态 + :2/:7 实例地址逐字）；预期输出
   :6/:8/:10/:30/:31-32 不变；画面加字幕「本镜为已档实录回放（2026-10-29 R2-T6-A 轮）」；
   预案 B 注「S4 无重录点」；实例说明补例外句（terminal 一次性事件 + timeout 流自
   nudge+claim 不留待 keeper，不设实跑 setup 镜）。
2. **S5 主命令换 T7 实例**：主命令 = `_r3-t7-dt31-verify-raw.txt:3` 逐字
   （0x942ED2fa…f01e / Lyquid-dpp6…unqa）；预期输出对齐 :22/:28/:30/:31/:69/:72-73；
   原 T3 committee 命令降级为可选回放画面（不执行；若展示须补 :41 RuntimeError 与
   :43 exit=1，字幕注明「D-T3-1 修复前档案，单次纪律已用毕」）；console 命令维持
   `_r3-t3-console-raw.txt:2`，预期输出 :24/:31/:36/:38 不变，字幕注明 T3 实例名与实录回放。
3. **行号修正**：冻结条款 2 的 R2 Fulfilled 出处 `w1b2-r2-adversarial.md:102-:105`
   → `:77-:78、:89`；数字一律未动；「R2 档内无 9000/980/20 三元组」表述保留。
4. **自查登记（冷读仲裁轮回正）**：上一轮将仲裁例外句的
   `w1b2-r2-adversarial.md:148` **误改为 :147**，并误记「:148 为 deal-5..8 行」（实为
   :149）；本轮 grep -n 实测回正为 **:148**（:147 = balances: alice=77000 行、
   :148 = deal-1..3 Refunded（超时/keeper）行、:149 = deal-5..8 行）。其余行号
   （T7 :3/:22/:28/:30/:31/:69/:72-73、committee-raw :41/:43、adversarial :77/:78/:89、
   keeper :11-13、demo.py :346-357）本轮抽查属实，不改。
5. T7-④ 与 GT-d 同步扩为 S4/S5 预期输出行逐一 `grep -nF` 回四档实录，命中记录入
   `_r4d2d3-verify-raw.txt`。受影响文件清单（§0，7 项）结构不变，仅只读素材描述更新。

### 冷读仲裁轮（本轮，4 条，仅改本文件）

6. **:148 回正（§4.1 例外句 + 本节第 4 条改写）**：grep -nF/sed -n 复核仲裁原引
   `w1b2-r2-adversarial.md:148` 无误（:148 = deal-1..3 Refunded（超时/keeper）行；
   :147 = balances 行；:149 = deal-5..8 行）；上一轮误改为 :147 并误记「:148 为
   deal-5..8 行」（实为 :149），本轮回正并如实登记。
7. **S3 修复为「新部署实例实跑」单一口径**：`<addr>` 改为 = S2 当轮新部署实例地址
   （实录 :2 的 0xFD6F…c351 已用实例禁填）；预期输出保留 FLOW 1 / deal-1 'Qualified' /
   final state=Settled，分账 9000/980/20 引 R1 :6 并标注「R1 亦为零起点实例，同形预期；
   当轮以新实例实录为准」；删除「若该实录含完整余额行则以原文逐字入表」，改为警示
   `_r2-normal-assess-raw.txt:12-:13` 为已用实例输出（deal-9 / 58000/1960/40）不得作
   S3 预期来源；补条件分支——S2 走复用快路径时 S3 余额不得引 R1 三元组，以当轮实录为准。
8. **GT-d / T7-④ grep 清单扩为 S3/S4/S5**：S3 三条预期行（deal=deal-1 行、balances 行、
   DEMO COMPLETE）编码期静态命中 R1 档 :5/:6/:9，录制当轮逐一 `grep -nF` 命中当轮新
   实例实录并记录。
9. 本轮自查：全文件无「deal-1..3 Refunded（超时/keeper）」指向 :147 的表述（grep 验证）；
   其余行号（demo.py:346-357、adversarial :77/:78/:89、keeper :11-13）抽查属实未动。
