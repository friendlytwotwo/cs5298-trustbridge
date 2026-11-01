# R6 重审轮（R6-R2）方案：后端全面审查——安全与正确性深审（规划师，2026-11-01）

仓库定格 `HEAD=f40ce773021640c9ea7e2b87b163a39843067a74`（规划期实跑
`git rev-parse HEAD`）。**任务书称 HEAD=d460047，实际已前移 3 个提交**，差异实证：
`git diff --stat d460047..HEAD -- lyquid/src agents scripts` 为**空**（规划期实跑）——
三个新提交（`7514c71` 上一轮 R6 证据入库 / `f11116e` 归档轮次备份 / `f40ce77`
ZIP 重建登记）零在范围代码改动，**审计面与上一轮逐字节一致**。

**同任务上一轮 R6 已完整跑过并入库（7514c71）**，其结论（旧 plan.md 353 行 +
旧 implementation.md 172 行，本轮规划期已备份，见 §0 #A1/#A2）：P0=0、达准入
P1=0、零代码改动、新登记 P2×6（N1–N6）、R5 台账 15 项全维持登记、G1–G5 全过。

**本轮性质 = 独立重审**：上一轮结论只作**先验台账输入**，不是可照抄的事实。
三重义务：(a) **先验复核**——21 项登记台账逐条按当前代码重新取证（防照抄式
登记）；(b) **新眼扫描**——六焦点全部重开，每个焦点列「本轮增量检查点」（§3），
专找上一轮结论的盲区；(c) **门禁全部重跑**留本轮记录。与上一轮相同的任务书、
相同的纪律与红线、相同的分级规则（P0 必修 / P1 择优 / P2 只登记）。

**铁律（沿上一轮 + 本轮任务书）**：devnet 零链写零部署零重启（全部验证只读：
selftest / sim / py_compile / 容器 cargo check / 壳 crate cargo test）；零 git 写
（不 commit/add/push/branch/tag/restore/stash，沿惯例留人工）；判级行为、
console 打印面、E2_AVG_NUM=4 零变化；`scripts/dashboard.html`、
`docs/b3-user-test/`、`workflow-out/report/`、`workflow-out/slides/`、
`_submission-plan.md` **只读零改动**；types.rs/core.rs **语义改动**必须先复跑
模型检查壳（仓库外父级 `workflow-out/verify_core`，`cargo test --lib --tests`）
40/40 并登记；sim 输出与冻结基线逐字一致。

## 0. 受影响文件清单（15 项 + 伴随产物，供审查员核对）

改动面为**候选面**：findings 落在哪，修复落哪；P2 与复核项零改动。上一轮同面
审计结论为零改动，本轮**预期亦为零至极少改动**；清单外文件（`agents/alice.py`、
`agents/bob.py`、`lyquid/tests/`）在审查范围内但暂无已知必修项，若审计发现 P0
必须落点于此，编码期在 implementation.md 登记扩充理由后再改。

| # | 路径 | 动作 | 说明 |
|---|---|---|---|
| 1 | `lyquid/src/lib.rs` | 审查；P0/P1 落点 | ACCESS_MATRIX（:212-225）/require 单点（:230-246）/16 个 network 方法守卫（:281-640）/credit :693-703·debit :684-690·apply_payout :726-737 记账面/apply_cert_and_payout :766-792 |
| 2 | `lyquid/src/core.rs` | 审查；P0/P1 落点 | 状态机与资金转移（create:49/cancel:82/complete:138/claim_timeout:170/open_dispute:182/apply_verdict:191/validate_cert:235/阈值计数门 :245-247/evidence_root :287-298）；**语义改动→触发 verify_core 义务** |
| 3 | `lyquid/src/types.rs` | 审查；P0 落点（冻结域） | DealState::is_terminal :51-53/Deal::split :140-143/Payout :147-177（settle :165-172 fee min-clamp、total :174-176 裸加 = P2-11）；**语义改动→触发 verify_core 义务** |
| 4 | `lyquid/src/committee.rs` | 审查；P0/P1 落点 | CommitteeCertWire.into_domain（:44-56，`_ => Malicious` 判级行为红线内）/check_evidence_shape（:66-74）/set_members·members shim（:78-90，P2-3） |
| 5 | `lyquid/src/committee_certified.rs` | 审查；P0/P1 落点 | E2_AVG_NUM=4（:91，红线）/e2_configure:113（eth_guard=creator :112，阈值 0 拒 :119-123）/e2_arm:161/e2_net_config:192/committee_verdict_certified:355/e2_run_verdict_round:401 |
| 6 | `lyquid/src/timeout.rs` | 审查；P0/P1 落点 | watcher_step（:42-65，P1-R3 锚点 :61 `.ok?`，规划期实读复核）/SPIKE_1_TRIGGER_REGISTRATION（:86） |
| 7 | `lyquid/src/assessor.rs` | 审查；P0/P1 落点 | build_request:65/AssessmentModel:79/report_json:167/parse_report:184/assess:204（LLM 面，consensus 路径之外） |
| 8 | `agents/common/rpc.py` | 审查；P0/P1 落点 | 编码器（:194-278）/NodeError :165-178·TxError :181-182/_rpc（:441，P1-R1）/_send :464-485/NodeClient 23 方法（:492-749）/FakeNode（:752+）/e2_configure cast 通道（:158-162 注记 + :685-697）/DEFAULT_SENDER :437 |
| 9 | `agents/common/protocol.py` | 审查；P0/P1 落点 | canonical_json（:29-30，P2-5）/digest（:33-34）/evidence_root（:65-90，须与 core.rs:287-298 逐字节同规） |
| 10 | `agents/common/llm.py` | 审查；P0/P1 落点 | OpenAI 兼容面（P1-R2 锚点 :58-68） |
| 11 | `agents/broker.py` | 审查；P0/P1 落点 | live 模式取字段（P1-R2）/双规范化（:38-40，P2-5）/默认成员硬编码（:57-59，P2-7） |
| 12 | `scripts/demo.py` | 审查；P0/P1 落点 | 四流（normal:301/timeout:331/adversarial:389/committee:567）+ B1a/B1b 断言（:322-325/:369-373，规划期实读复核）+ CLI 门（:753-791）；**sim 输出=冻结基线，改动须逐字保持** |
| 13 | `scripts/keeper.py` | 审查；P0/P1 落点 | poll_once（:84-132，_send 直用 :116 + 读回纪律 :123-131）/C1·C2 入参门（:151-158，规划期实读复核） |
| 14 | `workflow-out/plan.md` | 覆写 | 本方案（R6-R2）；**规划期已备份**，见 #A1 |
| 15 | `workflow-out/implementation.md` | 覆写 | R6-R2 实现说明（编码期）：findings 全表 / 先验复核记录 / 修复 diff 摘要 / 门禁实录 / 与上一轮 R6 台账差异说明 |

伴随产物（不占清单）：
- **#A1 `workflow-out/_plan-prev-r6-run2-backup.md`**（**规划期已执行**：`cp` 旧
  plan.md【= 上一轮 R6 方案】，md5 `4e8053581971daf5ede1e6a22c1840f0` 双侧一致，
  实跑在案）；
- **#A2 `workflow-out/_implementation-prev-r6-backup.md`**（**规划期已执行**：
  `cp` 旧 implementation.md【= 上一轮 R6 实现说明】，md5
  `782299b5120ea355d0655c33e19e8457` 双侧一致；编码期覆写 implementation.md 前
  再复核一次 md5）；
- **备份命名说明（审查员重点核对项）**：任务书点名备份 `_plan-prev-r6-backup.md`
  / `_implementation-prev-r5-backup.md`——两件**已由上一轮 R6 按同名惯例产出**
  （现存内容分别为 R5 终版方案 md5 `d8381a05…`、R5 实现说明 md5
  `a92ac140…`，均已随 `f11116e` 入库）。本轮同为 R6，若按点名覆盖写会**毁掉
  这两份 R5 时代文档的工作树唯一副本**，故改用上述非覆盖名，原名两件**保持
  原样零改动**（上一轮的备份义务已履行、本轮不重复履行以免信息损失）。
- **#A3 `workflow-out/_pre-task-snapshot-r6r2.patch` + `workflow-out/_r6r2-orig-*`**
  （编码期开工前：`git diff -- lyquid/src scripts agents` 存 patch + 逐文件
  `cp` 原件 13 份；**回退 = cp 回原件，零 git 写**）；
- **#A4 `workflow-out/_r6-run2-sim-out.txt`**（**规划期已落盘**：本轮 sim 输出，
  与冻结基线 md5 相同，见 §1-4）。

只读素材（零写入）：`scripts/dashboard.html`（⑥ 复核对象，只读；规划期 md5
`a2206ffcca6cbe2fddb632071bf76709` = 上一轮登记值）、`agents/alice.py`、
`agents/bob.py`、`lyquid/tests/{escrow_lifecycle,modelcheck_refund}.rs`、
`workflow-out/_r2-t0-sim-baseline-raw.txt`（冻结基线，md5
`a7cd1bdcd09fb44bff2002cb49e8694c`）、`workflow-out/_plan-prev-r6-backup.md`
（R5 台账原文）、`workflow-out/_plan-prev-r6-run2-backup.md`（上一轮 R6 方案+
实现说明原文）、`workflow-out/demo-script.md`、`docs/演示与运行指南.md`
（行号漂移只登记不改写，P2-12）；`docs/b3-user-test/` 三件、
`workflow-out/report/`、`workflow-out/slides/`、`_submission-plan.md` **零写入**。

## 1. 规划期实跑核实的预置事实（编码员直接采信；标 ✅ 者编码期须复跑）

1. ✅ `git rev-parse HEAD` = `f40ce773021640c9ea7e2b87b163a39843067a74`；任务书
   称 d460047 已前移 3 提交；`git diff --stat d460047..HEAD -- lyquid/src agents
   scripts` 空（零在范围改动）；`git status --short lyquid scripts agents` 空 +
   `git diff --stat -- lyquid/src scripts agents` 空（工作树代码零未落库改动）。
2. ✅ `python scripts/demo.py --selftest` → rc=0，`SELFTEST OK`（尾 3 项 PASS
   实见：deterministic/order-divergent、官方 FNV 向量 ×2）。
3. ✅ `python -m py_compile` 8 个在范围 py 文件（rpc/protocol/llm/alice/broker/
   bob/demo/keeper）→ `PY_COMPILE-ALL-OK`。
4. ✅ `python scripts/demo.py --sim --flow all` → rc=0，输出存
   `workflow-out/_r6-run2-sim-out.txt`，与 `workflow-out/_r2-t0-sim-baseline-raw.txt`
   `diff -u` **零差异**（diff_rc=0，两侧 md5 同为
   `a7cd1bdcd09fb44bff2002cb49e8694c`——逐字一致）。R6-R2 修复后须逐字保持。
5. ⚠ **G4 规划期未跑成**：`MSYS_NO_PATHCONV=1 docker exec … multi-tools cargo
   check` → `failed to connect to the docker API … dockerDesktopLinuxEngine …
   daemon 不在运行`（实跑实录）；容器副本 md5 互证本轮同样未跑成。处置沿风险
   R3：如实登记「规划期未跑+原因」，**编码期重试**；若仍不可用，G4 如实登记
   「未跑」，不虚报（上一轮 7514c71 曾实证容器 md5 `03e3d08b…` = 仓库 lib.rs；
   零改动前提下 G4 缺席不掩盖行为面）。
6. ✅ 模型检查壳位置与挂载实证：壳在**仓库外父级** `workflow-out/verify_core`
   （任务书「仓库外」指此），`src/lib.rs` 与 `tests/*.rs` 以 `#[path]` **绝对
   路径**挂载仓库内 types/core/committee/assessor 与 lyquid/tests 两文件——
   **测的即当前仓库态**；`grep -c '#\[test\]'` 5 个挂载文件 = core 23 +
   committee 4 + assessor 6 + escrow_lifecycle 5 + modelcheck_refund 2 = **40**，
   与任务书门禁「cargo test --lib --tests 40/40」吻合。
7. ✅ **G5 规划期已实跑**：父级 `workflow-out/verify_core` 下
   `cargo test --lib --tests` → **40/40 通过**（33+5+2，0 failed，rc=0）——
   types/core 当前态的模型检查基线新鲜在案；编码期无论是否触语义改动都复跑。
8. ✅ 上一轮两备份件在案且入库：`_plan-prev-r6-backup.md` md5
   `d8381a05788422c01a4496a205ce9fd7`、`_implementation-prev-r5-backup.md` md5
   `a92ac14061798943f5f3be9d066c8af2`（`git ls-files workflow-out` 计 13 个
   备份件，实跑）。
9. ✅ 范围实测（`wc -l` 实跑）：Rust 源 7 文件 **2945 行**（types 197 / core 909 /
   lib 862 / committee 185 / committee_certified 433 / assessor 273 / timeout 86）
   + Rust 测试 2 文件 **365 行** + Python 9 文件 **2434 行**（rpc 962 / demo 810 /
   keeper 179 / protocol 161 / llm 98 / broker 93 / alice 68 / bob 56 /
   `__init__.py` 7）+ dashboard.html 1170 行（只读复核面）。
10. ✅ 负载锚点抽查（规划期实读复核，上一轮行号仍指对位置）：lib.rs:554 阈值门、
   lib.rs:700 checked_add、core.rs:245-247 InsufficientCommittee、timeout.rs:61
   `.ok?`、demo.py:322-325/:369-373 终态断言、keeper.py:151-158 C1/C2、
   dashboard.html:601 SEL 表 + :209/:261/:357/:884 e2_arm 纪律标注、
   protocol.py:29-34 canonical_json/digest——全部命中。
11. ✅ #A1/#A2 备份已落盘（md5 双侧一致，见 §0）。

## 2. 先验台账继承（本轮重评输入 = R5 15 项 + 上一轮 R6 新增 6 项 = 21 项）

原文位置：R5 15 项 = `_plan-prev-r6-backup.md` §2.2/§5；N1–N6 = 上一轮 R6
implementation.md §3（备份于 `_implementation-prev-r6-backup.md`）。上一轮处置
全为「登记不修」；本轮逐项按**当前代码**重新取证后判定 **维持登记 / 升级必修 /
顺带修**，禁止照抄上一轮理由——每条须给本轮新证据（命令输出或行号实读）。

| ID | 位置 | 一句话（先验） |
|---|---|---|
| P1-R1 | rpc.py:441-450 | `_rpc` 对非 JSON 响应/连接异常裸抛 |
| P1-R2 | broker.py:31、llm.py:58-68 | live 模式畸形 LLM 响应裸 traceback |
| P1-R3 | timeout.rs:61 | `watcher_step` 单笔 claim 失败 `.ok?` 中断整轮 |
| P2-1 | rpc.py:56 `field`、alice.py:16 | 死 import 残量（R5 已删 demo SLOT_MS） |
| P2-2 | rpc.py:426/:500/:648/:809/:895-897/:911-915、protocol.py:19、demo.py:16 | 行号注释漂移残量 8 处 |
| P2-3 | committee.rs:78-90、timeout.rs:86、lib.rs:735-737 | 死代码（shim/常量/slash 分支） |
| P2-4 | committee.rs:45-49、rpc.py:919 | `_ => Malicious` 判定面（红线④内）+ sim KeyError |
| P2-5 | protocol.py:30 vs broker.py:38-40 | 双规范化 ensure_ascii 差异（载荷全 ASCII 则分叉不可达） |
| P2-6 | rpc.py:809-813 等 | FakeNode 非镜像面 + `python -O` 下 assert 消失 |
| P2-7 | broker.py:57-59 | 硬编码默认成员 node-1..4 |
| P2-8 | demo.py:358-361 | due 扫描每 deal 3× deal_info（node-only 效率） |
| P2-9 | demo.py:147 | `wait_for` node 形参未用 |
| P2-10 | core.rs:245-247 | `threshold > 成员数` 可配置（fail-closed 方向死锁型） |
| P2-11 | types.rs:174-176 | `Payout::total` 裸加（构造面三形使 total≤amount 恒成立） |
| P2-12 | workflow-out/demo-script.md、docs/演示与运行指南.md | 文档行号漂移（只读件只登记） |
| N1 | lib.rs:412 | notarize 对不存在 deal_id 也建条目（`or_default()` 无存在性检查） |
| N2 | lib.rs:398-416 | notarize 无状态守卫，终态后仍可追加证据 |
| N3 | lib.rs:788-792 | apply_cert_and_payout misconduct 写回先于 payout（fail-stuck 面） |
| N4 | keeper.py:94-96/:116-121 | poll_once 只捕 (NodeError, TxError)，requests 层异常裸抛终止主循环 |
| N5 | alice.py:33/:41、bob.py:25/:33 | CLI 无 sender 选择，node 写通道默认 anvil#0 与角色门不匹配 |
| N6 | keeper.py:115-126 | 重复 claim 竞态下 action 归因失真（status 0x1 但单非本 keeper 所为） |

## 3. 子任务拆分与执行顺序（T0→T8；§3.1–3.6 = 六焦点的核对表与「本轮增量」）

| 序 | 子任务 | 产出/判据 |
|---|---|---|
| T0 | 备份与定格（**规划期已完成大半**） | #A1/#A2/#A4 已落盘；§1 十一项预置事实 |
| T1 | 焦点① 访问控制与攻击面 | §3.1 核对表逐行当前证据 + 滥用路径 5 类重判定 + 增量检查点 |
| T2 | 焦点② 经济不变量 | §3.2 守恒核对表 + fee/溢出边界 + N3 重验 |
| T3 | 焦点③ R5 修复正确性复核 | §3.3 四项「未引入新问题」结论（本轮新证据） |
| T4 | 焦点④ 台账 21 项重评 | §2 表逐条「维持登记/升级必修/顺带修」+ 本轮证据 |
| T5 | 焦点⑤ Python 编码层深审 | §3.5 编码面×调用方一致性 + 错误路径 + 增量面 |
| T6 | 焦点⑥ dashboard 只读交互面复核 | §3.6 三纪律核对表（本轮新证据） |
| T7 | 修复实施（P0 必修、P1 择优） | §4 规则；快照 #A3 先落盘；触语义改动先跑 verify_core |
| T8 | 门禁复跑与产出 | §5 G1-G5 全跑登记；implementation.md 按惯例产出 |

**独立重审纪律（审查员核对项）**：implementation.md 中每个检查点的结论必须
附**本轮**证据（命令 + 输出摘要，或「文件:行号 + 实读引文」）；出现
「沿用上一轮结论」而无本轮证据的条目 = 审查员直接打回（防先验照抄，风险 R6）。

### 3.1 焦点①：访问控制与攻击面（T1）

**矩阵核对表**（期望=任务书；声明=lib.rs:212-225；执行=require 单点
:230-246——caller 经 `ctx.caller: Address` 字符串化进 AgentId 域，Committee 臂
查 `state.committee_members` 空集即拒=fail-closed）。上一轮先验：12 行全 ✓；
本轮每行重新实读给证据：

| 方法 | 矩阵声明 | require 执行点 | 期望（任务书） |
|---|---|---|---|
| faucet :281 | Anyone（:213，TODO(W2) DEMO flag） | 无 require | Anyone ✓ |
| create_deal :296 | Broker（:214） | :308 | Broker ✓ |
| fund :357 | Buyer（:215） | :361 | Buyer ✓ |
| notarize :398 | Anyone+自署名（:216） | :406-409 from==caller | 自署名 ✓ |
| submit_deliverable :419 | Seller（:217） | :423 | Seller ✓ |
| complete :433 | Buyer（:218） | :437 | Buyer ✓ |
| claim_timeout :454 | Anyone permissionless（:219） | 无 require，core 重推导 | permissionless ✓ |
| cancel :468 | Buyer（:220） | :472 | Buyer（任务书未列，核对语义） |
| open_dispute :487 | BuyerOrSeller（:221） | :493 | BuyerOrSeller ✓ |
| apply_committee_verdict :520 | Committee+caller∈signers（:222） | :530 + :531-533 | Committee ✓ |
| committee_config :545 | Broker（:223） | :547 + R5 阈值门 :554 | Broker ✓ |
| getters :566/:583/:594/:605 | Anyone 只读（:224） | 无资金效应 | Anyone ✓ |

**攻击者视角滥用路径 5 类**（每条重新给可达/不可达判定 + 当前代码证据）：
1. **签名/证书重放与跨单复用**：路线① wire 证书无 evidence_root 参数，
   into_domain（committee.rs:44-56）从当前全量证据折叠根；validate_cert
   （core.rs:235-253）四查（成员/去重/阈值/根匹配）；路线② signers =
   `ctx.cert.signers`（committee_certified.rs:356-380，映射失败剔除）。
2. **阈值绕过**：成员域唯一写点 committee_config=Broker 门（:547）；e2 域唯一
   写点 e2_configure=creator（committee_certified.rs:112 + 阈值 0 拒 :119-123）。
3. **重复结算**：终态封死（types.rs:51-53 + require_states :29-37）；
   apply_verdict 仅 Disputed（core.rs:199）；claim_timeout 仅 Funded（:170-178）；
   complete 的 Committee 授权路径（:138-161）与其余路径状态互斥；verify_core
   modelcheck 720 排序背书（本轮 G5 重跑为新鲜证据）。
4. **伪造署名**：notarize 自署名强制（lib.rs:406-409）；check_evidence_shape
   （committee.rs:66-74）只认卖家→买家 + deliverable 匹配；「digest 即身份、
   无签名」为已文档化 demo 信任洞（committee.rs:53 注记），洞内不判新缺陷。
5. **未注资取款**：claim_timeout 仅 Funded+过 deadline（core.rs:170-178）；
   cancel 无证据才可（core.rs:82-92，Qualified=全零 payout，F2 钉死）；
   apply_payout 全零 no-op（lib.rs:726-737 三个 `>0` 门）；faucet 无上限 +
   BROKER=anvil#0 硬编码（lib.rs:208）为已文档化信任洞（:277-279 TODO(W2)）。

**本轮增量检查点**（上一轮结论之外的盲区扫描）：
- certified 回调面不入矩阵的口径（committee_certified.rs 模块头 E2 门禁台账）
  与 ACCESS_MATRIX 的互证关系重新实读（origin=ZERO 使地址门必 fail-closed）；
- `due_deals(now)` 调用方时钟 advisory 口径（lib.rs:599-604）重验 + 有无新增
  把 advisory 当权威的调用方（demo/keeper/dashboard 三面 grep）；
- notarize 面 N1/N2 重验：`evidence_log.entry(..).or_default()`（:412）+
  无 require_states（:398-416）——上一轮判 P2 的理由（裁决前 deal 存在 +
  Disputed 门）逐条重证；
- ACCESS_MATRIX 常量表与方法实现集的**完备性**（有没有方法漏登记矩阵行）：
  `grep -n "pub fn" lib.rs` 全集 × 矩阵 12 行比对（上一轮按方法逐行过，本轮
  反向从方法集扫矩阵遗漏面）。

### 3.2 焦点②：经济不变量（T2）

**资金守恒 = 每个可达转移后 `Payout::total() == deal.amount`（或 Qualified
取消=全零）**。可达转移全集与核对点（上一轮先验=全守恒；本轮重证）：
- `fund`（lib.rs:357-397）：预检 :371-374 → core::fund（core.rs:61）→ debit
  顺序契约；重复 fund 被 require_states 拒。
- `complete`（lib.rs:433-449 BuyerConsent / core.rs:138-161 Committee）：
  `Payout::settle`（types.rs:165-172，fee = saturating_mul/10_000 min-clamp，
  to_seller = amount-fee 恒不 underflow）；fee_bps 上限 core::create
  （core.rs:54-56 InvalidFeeBps）；F1/F4 终态映射测试（core.rs:549-590/:593-615）。
- `claim_timeout`（core.rs:170-178）：仅 Funded+过 deadline → full_refund。
- `cancel`（core.rs:82-92）：无证据退/全零；F2 测试 core.rs:524-544。
- `apply_verdict`（core.rs:191-218）三裁决：Fulfilled→settle、NotFulfilled→
  full_refund、Malicious→full_refund + misconduct+1（:205-208）；**Malicious
  不罚没资金**（slash 分支 lib.rs:735-737 = P2-3 登记死代码，重评见 T4）。
- 记账单点：`credit`（lib.rs:693-703 checked_add；5 调用点 :288/:727/:730/:733/
  :736 全带 `?`）+ `debit` 预检（:684-690）。
**fee 与溢出边界**：`Deal::split`（types.rs:140-143）与 settle 同式；u128 饱和
角由 core 测试钉死（fee_rounding_edges_conservation:476 / split_never_underflows:
499 / verdict_fulfilled_full_fee_still_settled:593）。
**本轮增量**：N3 重验——apply_cert_and_payout 内 misconduct 写回（:788-791）
先于 apply_payout（:792），「平台 Err 无原子回滚 + credit 溢出」双前提下的
fail-stuck 判定重证；P2-11 重证——`Payout::total`（types.rs:174-176）消费点
仅 debug_assert（lib.rs:725）与测试、不在资金决策路径，回绕不可达论证重跑。

### 3.3 焦点③：R5 修复自身正确性复核（T3）

逐项验证「修复无新问题」（对照 `_implementation-prev-r5-backup.md` §1；本轮
给新证据）：
- **A1**：lib.rs:554 `threshold == 0 → Err`；门位在 require（:547）后、状态清写
  （:555-559）前；误伤面 grep 复跑（demo.py:610 E2_THRESHOLD=4、demo.py:792
  THRESHOLD=3、broker.py:59 默认 3——无一传 0）。
- **A2**：lib.rs:700 checked_add；失败在写回前返回 Err 无半写；5 调用点带 `?`。
- **B1a/B1b**：demo.py:322-325（normal 流 Settled 断言）/:369-373（timeout 流
  Refunded 断言）只在 `if node_mode(node):` 分支内；sim 分支零改动——本轮 §1-4
  基线 md5 相同为行为证据。
- **C1/C2**：keeper.py:151-152 `--interval<=0 → p.error`、:156-158 `--deals`
  空表 → p.error；discover 默认路径（:161）不受影响。
每项结论 = 「未引入新问题 / 发现回归（=新 finding 按 §4 分级）」。

### 3.4 焦点④：台账 21 项重评（T4）

对 §2 表逐项：**维持登记 / 升级必修 / 顺带修**（升级 = 说明上一轮登记理由为何
在重审视角下失效 + 改动点 + 门禁影响）。上一轮重点候选的预判（本轮仍需以新证
据定夺）：P1-R3 维持（DoS 型延迟非资金错误、幂等自愈、watcher_step 无驱动方、
重编 wasm 收益近零）；P2-5 维持（载荷域全 ASCII，dashboard 用户输入无交叉比较
点）；P2-10 维持（fail-closed 方向恒拒，非安全洞，W4 处置）；P2-11 维持
（构造面三形 total≤amount + 不在决策路径）；P2-4 维持（判级行为红线④）。
**本轮增量问题**：上一轮 N1–N6 的 P2 定级是否有被低估项（尤其 N3 的
fail-stuck 与 N1 的 notarize 存在性面——若重审发现裁决门实际可绕过则升 P0，
需给出可达链证据）。

### 3.5 焦点⑤：Python 编码层深审（T5）

**编码器支持集**（rpc.py:194-278）：`_enc_value`（string :203-205 / string[]
:206-222 / uint* :223-224 / bool :225-226 / 集外 ValueError :227）、
`_encode_args`（:234-244 动态偏移=head_size+len(tail)）、`_decode_ret`
（:247-273 string[] tail=base+32）、`_sig_types`（:276-278）；**无
bytes32/bytes32[]** = 终裁冻结条款 1（e2_configure 走 cast send，:158-162 +
:685-697）——零扩展合规。
**核对方法**：dump NodeClient `_ABI` 全表 × `_enc_value/_is_dynamic` 支持集 ×
wire 参数与 lib.rs 签名对齐（faucet U128 边界 :286、create_deal 8 参
:296-306、apply_committee_verdict 扁平 (string,uint8,string[]) :520、
committee_config(string[],uint32) :545、claim_timeout→bool :454、
balance_of→uint128 :594、due_deals(uint64)→string[] :605、assess_brief
:639-676、e2_arm/e2_run_verdict_round/e2_net_config）。
**已证对齐面**（联调+上一轮双证，本轮复核不推翻、只登记新证据）：五视图
deal_info/balance_of/evidence_entries_json/due_deals/e2_net_config + 写面
faucet/notarize/create_deal/fund/claim_timeout。
**复核未覆盖面**（本轮主战场）：discover_deals（rpc.py:505）/ assess_brief
（:643-660，trust hole：api_key 进 calldata，doc :652-655）/ cancel（:586）/
submit_deliverable（:572）/ complete（:575）/ open_dispute（:589）/
apply_committee_verdict（:592）的编码面、返回解码与 lib.rs 签名一致性。
**错误路径全查**：NodeError（:165-178 不折叠）/ TxError（:181-182 + :483-485
status≠0x1）/ `_rpc`（:441-450 P1-R1）/ `_view`（:455）/ `_send`（:464-485
断言 status=="0x1" + receipt 返回）：非 JSON 响应、HTTP 错误、超时、
`python -O` 下 assert 消失面（P2-6 交叉；上一轮结论=NodeClient 写路径全 raise
无 assert 依赖，重证）。
**protocol.py × core.rs 逐字节同规**：`"{seq}|{from}|{to}|{payload_digest}|
{slot}\n"` 字段序/分隔符/UTF-8/空表=`cbf29ce484222325`/顺序敏感不重排
（protocol.py:65-90 vs core.rs:287-298）；G2 selftest 七向量为行为证据。
**两个调用方交叉**：agents CLI（alice/broker/bob + keeper 直用 `_send`
keeper.py:116）与 scripts/dashboard.html（→ 焦点⑥）。
**本轮增量**：N4/N5 重验（keeper except 面 :94-96/:116-121；alice.py:33/:41、
bob.py:25/:33 无 sender 选择）+ dashboard ops-reason 非 ASCII 输入的 digest
自算自用无交叉比较点论证重跑。

### 3.6 焦点⑥：dashboard 只读交互面复核（T6）

`scripts/dashboard.html` **只读零改动**（规划期 md5
`a2206ffcca6cbe2fddb632071bf76709` = 上一轮登记值），三项纪律重核对：
1. **选择器冻结一致**：页内 SEL 表（:601：dealInfo=ec78f86e/balance=3e6b4459/
   evidence=16417010/dueDeals=4704839a/e2net=2b5d6a4a）+ OPS 表（:848-890）共
   16 selector × rpc.py `_ABI` 逐一比对；e2_configure/e2_run_verdict_round 无
   页内调用（组标注 :884 指回 demo.py --flow committee）——cast 通道纪律一致。
2. **status 0x1 ≠ 方法 Ok 读回纪律**两调用方都成立：页内 sendTx 说明
   （:814-818）+ runOp 每笔后强制 opsReadback（:916-917）+ LIVE 预设
   liveStepTx 按期望终态 liveWaitState（:985-1001，超时抛错不静默）；agents 侧
   keeper `_read_back`（:123-131）+ demo B1a/B1b。
3. **e2_arm 单次纪律**：LIVE 三预设零调用 e2_arm（8b7acf91 仅手动按钮 op-arm
   :888-889 带 ⚠ 单次标注）；纪律为文档级标注无硬锁——上一轮判定轻微漂移
   登记不修（armed_deal 重写被 propose 的 Disputed 门 + aggregate 拒证
   fail-closed 兜底），本轮重证该兜底论证；页内 LIVE 对抗预设
   committee_config([broker,node-1..3]) 覆盖实例 NodeID 制配置的 ⚠ 警示
   （:1134）重验。
产出 = 三项核对表（一致/漂移；dashboard 只读，若构成 P0 修复只能落
rpc.py/文档侧并说明约束）。

## 4. 修复实施规则（T7）

- **P0（真缺陷：资金语义/守恒、越权可达、误报漏报、fail-closed 失效）必修**：
  逐条给「位置/根因/最小修复/门禁影响」；修复前先落快照 #A3。
- **P1（加固）择优**：准入三条件——不触 §6 红线、改动面小（单文件单点优先）、
  有钉死测试或门禁护航。R5 残留 P1-R1/R2/R3、上一轮 N1–N6（若升级）与本轮新
  发现同池择优。
- **P2 只登记**（不改代码）；行号漂移类编码期实查后只登记。
- **types.rs/core.rs 语义改动义务**：改动前复跑 verify_core 确认 40/40（本轮
  规划期基线已新鲜在案 §1-7），改动后复跑确认仍 40/40，两次输出都登记。
- **lyquid 面任何源码改动**：编码期先 `touch <改动文件>` 再跑容器 cargo check
  并注明重编（容器可用性见 §1-5 ⚠，不可用时如实登记未跑）。
- **console 打印面 / 判级行为 / E2_AVG_NUM=4 / 方法签名 ABI 零变化**；sim 路径
  零改动（输出与冻结基线逐字一致，§1-4）。

## 5. 门禁与产出（T8；命令照抄执行）

| # | 门禁 | 命令 | 通过判据 |
|---|---|---|---|
| G1 | 语法 | `python -m py_compile <全部改动的 py>`（零改动则全 8 件复跑留记录） | rc=0 |
| G2 | 自检 | `python scripts/demo.py --selftest` | rc=0，SELFTEST OK |
| G3 | sim 基线 | `python scripts/demo.py --sim --flow all` 输出 vs `workflow-out/_r2-t0-sim-baseline-raw.txt` `diff -u` | 零差异（本轮规划期两侧 md5 相同证据在案） |
| G4 | Rust 编译（只读） | `MSYS_NO_PATHCONV=1 docker exec -w /tmp/tb-lyquid multi-tools cargo check --target wasm32-unknown-unknown`（有源码改动先 touch 并注明） | rc=0 + warning 数记录；**容器不可用时如实登记未跑+原因（规划期实录 §1-5），不虚报** |
| G5 | 模型检查壳 | 父级 `workflow-out/verify_core`：`cargo test --lib --tests` | **40/40**（规划期已 40/40 在案；编码期复跑登记） |

产出（编码期写入 `workflow-out/implementation.md`，覆写前复核 #A2 备份）：
1. **分级 findings 清单**——每条：ID / 级别 / 位置（文件:行号）/ 问题一句话 /
   本轮证据（命令输出或实读引文）/ 处置（修/登记）；
2. **先验复核表**——21 项台账逐条「本轮证据 + 维持/升级/顺带修」；
3. **已实施修复的 diff 摘要** + G1-G5 门禁复跑结果实录；
4. **与上一轮 R6 台账（N1–N6）及 R5 台账（15 项）的差异说明**——逐条处置映射，
   本轮新 findings 与既有分级的关系。

## 6. 红线表（违反 = 直接 REVISE）

| # | 红线 | 依据 |
|---|---|---|
| ① | devnet 零链写零部署零重启（一切验证只读） | 任务书纪律 |
| ② | 零 git 写（不 commit/add/push/restore/stash…），回退=cp 原件 | 任务书纪律 |
| ③ | `scripts/dashboard.html`、`docs/b3-user-test/`、`workflow-out/report/`、`workflow-out/slides/`、`_submission-plan.md` 只读 | 任务书纪律 |
| ④ | 判级行为（含 committee.rs:45-49 未知 verdict_code→Malicious）、console 打印面、E2_AVG_NUM=4（committee_certified.rs:91）零变化 | 任务书纪律 |
| ⑤ | types.rs/core.rs 语义改动必须先复跑 verify_core 40/40 并登记 | 任务书纪律 |
| ⑥ | sim 输出 = 冻结基线逐字一致（G3）；编码器集外类型零扩展（终裁冻结条款 1，rpc.py:158-162） | 任务书/R3 终裁 |
| ⑦ | 先验照抄禁令：每个检查点结论必须附本轮证据，禁止「沿用上一轮结论」式登记 | 本方案 §3 独立重审纪律 |

## 7. 风险与回退

| 风险 | 概率/影响 | 缓解与回退 |
|---|---|---|
| R1 审计发现 P0 集中于 types.rs/core.rs 语义面 | 低/高 | 触发⑤义务：verify_core 改前改后双跑登记（规划期基线 40/40 在案）；快照 #A3 先行；回退=cp `_r6r2-orig-*` 原件（零 git 写） |
| R2 修复扰动 sim 输出 | 中/中 | G3 逐字 diff（本轮两侧 md5 相同）立即暴露；sim 分支零改动是硬规则；回退=cp 原件重改 |
| R3 容器 multi-tools 不可用（**规划期已发生**，§1-5 ⚠） | 已发生/中 | G4 如实登记「未跑+原因」，编码期重试；零改动前提下 G4 缺席不掩盖行为面（上一轮同环境曾实证通过，7514c71 在案） |
| R4 误改只读件（dashboard.html 等） | 低/高 | 快照比对 + cp 还原；只读件 md5 前后核对（dashboard 规划期基线在案）；git status 实查 |
| R5 findings 面扩大导致轮数吃紧 | 中/中 | P2 只登记 + P1 择优天然限面；P0 全修不动摇；按 T1→T8 顺序收敛 |
| R6 **先验照抄**（把上一轮结论当事实复述，重审流于形式） | 中/高 | 红线⑦：每检查点强制本轮证据；审查员核对证据列非空；§3 各焦点「本轮增量」为必答项 |
| R7 行号漂移（若编码期有改动，文档漂移加剧） | 中/低 | P2-12 惯例只登记不改写（只读件）；改动后 findings 表行号为改动后行号并注明 |
| R8 任务书 HEAD（d460047）与实际（f40ce77）不一致引发审查疑问 | 已消解/低 | §1-1 实证：3 新提交零在范围代码 diff（`git diff --stat d460047..HEAD` 空）；方案按实际 HEAD 定格并如实登记 |
