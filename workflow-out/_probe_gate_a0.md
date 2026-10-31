# R6 方案：后端全面审查——安全与正确性深审轮（规划师，2026-11-01）

仓库定格 `HEAD=d4600474515ef2973899cc9754f854628288a878`（规划期实跑
`git rev-parse HEAD` 确认；任务书称 d460047，一致；工作树代码零未落库改动，
仅 workflow-out 下历史备份 untracked）。R6 = **审查 + 分级修复轮**。与 R5
（健康性/健壮性，P0=0）的差异 = **更深的安全审计视角**，六个重点：
① 访问控制与攻击面 ② 经济不变量 ③ R5 修复自身正确性复核
④ R5 登记未修 15 项重评 ⑤ Python 编码层深审 ⑥ dashboard 只读交互面复核。

**铁律（沿 R5 + R6 任务书）**：devnet 零链写零部署零重启（全部验证只读：
selftest / sim / py_compile / 容器 cargo check / 壳 crate cargo test）；
零 git 写（不 commit/add/push/branch/tag/restore/stash，沿惯例留人工）；
判级行为、console 打印面、E2_AVG_NUM=4 零变化；`scripts/dashboard.html`、
`docs/b3-user-test/`、`workflow-out/report/`、`workflow-out/slides/`、
`_submission-plan.md` **只读零改动**；types.rs/core.rs **语义改动**必须先复跑
模型检查壳（仓库外 `workflow-out/verify_core`，`cargo test --lib --tests`）
40/40 并登记；**P0 真缺陷必修、P1 加固择优、P2 只登记**。

## 0. 受影响文件清单（15 项 + 伴随产物，供审查员核对）

改动面为**候选面**：findings 落在哪，修复落哪；P2 与复核项零改动。清单外文件
（含 `agents/alice.py`、`agents/bob.py`、`lyquid/tests/`）在审查范围内但暂无
已知必修项，若审计发现 P0 必须落点于此，编码期在 implementation.md 登记扩充
理由后再改。

| # | 路径 | 动作 | 说明 |
|---|---|---|---|
| 1 | `lyquid/src/lib.rs` | 审查；P0/P1 落点 | ACCESS_MATRIX（:212-225）/require 单点（:230-246）/16 个 network 方法守卫（:281-640）/credit·apply_payout 记账面 |
| 2 | `lyquid/src/core.rs` | 审查；P0/P1 落点 | 状态机与资金转移（create:49/cancel:82/complete:138/claim_timeout:170/open_dispute:182/apply_verdict:191/validate_cert:235）；**语义改动→触发 verify_core 义务** |
| 3 | `lyquid/src/types.rs` | 审查；P0 落点（冻结域） | DealState/Verdict/Deal::split（:140-143）/Payout（:147-177，total 裸加 = P2-11）；**语义改动→触发 verify_core 义务** |
| 4 | `lyquid/src/committee.rs` | 审查；P0/P1 落点 | CommitteeCertWire.into_domain（:44-56，`_ => Malicious` 判级行为红线内）/check_evidence_shape（:66-74）/set_members·members shim（:78-90，P2-3） |
| 5 | `lyquid/src/committee_certified.rs` | 审查；P0/P1 落点 | E2_AVG_NUM=4（:91，红线）/e2_configure:113/e2_arm:161/e2_net_config:192/committee_verdict_certified:355/e2_run_verdict_round:401 |
| 6 | `lyquid/src/timeout.rs` | 审查；P0/P1 落点 | watcher_step（:42-65，P1-R3 锚点 :61 `.ok?`）/SPIKE_1_TRIGGER_REGISTRATION（:86） |
| 7 | `lyquid/src/assessor.rs` | 审查；P0/P1 落点 | build_request:65/AssessmentModel:79/report_json:167/parse_report:184/assess:204（LLM 面，consensus 路径之外） |
| 8 | `agents/common/rpc.py` | 审查；P0/P1 落点 | 编码器（:194-278）/NodeError·TxError（:165-183）/_rpc（:441，P1-R1）/NodeClient 23 方法（:492-749）/FakeNode（:752+） |
| 9 | `agents/common/protocol.py` | 审查；P0/P1 落点 | canonical_json（:29-30，P2-5）/digest（:33-34）/evidence_root（:65-90，须与 core.rs:287-298 逐字节同规） |
| 10 | `agents/common/llm.py` | 审查；P0/P1 落点 | OpenAI 兼容面（P1-R2 锚点 ：58-68 `r.json()["choices"][0]…`） |
| 11 | `agents/broker.py` | 审查；P0/P1 落点 | live 模式取字段（P1-R2）/双规范化（:38-40，P2-5 实读在案）/默认成员硬编码（:57-59，P2-7） |
| 12 | `scripts/demo.py` | 审查；P0/P1 落点 | 四流（normal:301/timeout:331/adversarial:389/committee:567）+ B1a/B1b 断言（:366/:319）+ CLI 门（:753-791）；**sim 输出=冻结基线，改动须逐字保持** |
| 13 | `scripts/keeper.py` | 审查；P0/P1 落点 | poll_once（:84-132，_send 直用 ：116 + 读回纪律 ：124-131）/C1·C2 入参门（:151-158） |
| 14 | `workflow-out/plan.md` | 覆盖写 | 本方案（R6）；**规划期已备份**，见 #A1 |
| 15 | `workflow-out/implementation.md` | 覆盖写 | R6 实现说明（编码期）：findings 全表 / 修复 diff 摘要 / 门禁实录 / R5 台账差异说明 |

伴随产物（不占清单）：#A1 `workflow-out/_plan-prev-r6-backup.md`（**规划期已执行**
`cp` 旧 R5 plan.md，md5 `d8381a05788422c01a4496a205ce9fd7` 两侧一致，实跑在案）；
#A2 `workflow-out/_implementation-prev-r5-backup.md`（编码期覆写 implementation.md
前 `cp`，md5 双侧核对）；#A3 `workflow-out/_pre-task-snapshot-r6.patch` +
`workflow-out/_r6-orig-*`（编码期开工前：`git diff -- lyquid/src scripts agents`
存 patch + 逐文件 `cp` 原件；**回退 = cp 回原件，零 git 写**）；#A4
`workflow-out/_r6-baseline-sim-out.txt`（**规划期已落盘**，§1-3 的本轮 sim 输出）。

只读素材（零写入）：`scripts/dashboard.html`（⑥ 的复核对象，只读）、
`agents/alice.py`、`agents/bob.py`、`lyquid/tests/{escrow_lifecycle,modelcheck_refund}.rs`、
`workflow-out/_r2-t0-sim-baseline-raw.txt`（冻结基线）、
`workflow-out/_plan-prev-r6-backup.md`（R5 台账原文）、
`workflow-out/demo-script.md`、`docs/演示与运行指南.md`（行号漂移只登记不改写，
P2-12）；`docs/b3-user-test/` 三件、`workflow-out/report/`、`workflow-out/slides/`、
`_submission-plan.md` **零写入**。

## 1. 规划期实跑核实的预置事实（编码员直接采信；标 ✅ 者编码期须复跑）

1. ✅ `git rev-parse HEAD` = `d4600474515ef2973899cc9754f854628288a878`；工作树
   无未落库代码改动（`git status --short` 过滤 workflow-out untracked 后为空）。
2. ✅ `python scripts/demo.py --selftest` → rc=0，`SELFTEST OK`（尾 3 项 PASS
   实见：deterministic/order-divergent、官方 FNV 向量 ×2）。
3. ✅ `python scripts/demo.py --sim --flow all` → rc=0，与
   `workflow-out/_r2-t0-sim-baseline-raw.txt` `diff -u` **零差异**
   （`BASELINE-DIFF-IDENTICAL`）；输出存 `workflow-out/_r6-baseline-sim-out.txt`。
   R6 修复后须逐字保持（B1a/B1b 断言在 node 分支，sim 面零改动即可保持）。
4. ✅ `python -m py_compile` 8 个在范围 py 文件（rpc/protocol/llm/alice/broker/
   bob/demo/keeper）→ `PY_COMPILE-ALL-OK`。
5. ✅ `MSYS_NO_PATHCONV=1 docker exec -w /tmp/tb-lyquid multi-tools cargo check
   --target wasm32-unknown-unknown` → `Finished dev profile … 0.80s`，rc=0，
   33 条既有 warning（与 R5 记录同量级）；规划期无源码改动故**未 touch**。
   编码期 lib.rs 等有改动，须先 `touch src/<改动文件>` 再跑并注明重编。
6. ✅ 容器镜像一致性：`docker exec multi-tools md5sum /tmp/tb-lyquid/src/lib.rs`
   = `03e3d08b9b41e00d4eb782d58b4de4ac` = 仓库 `lyquid/src/lib.rs` md5——
   容器副本 = 改动前源，编码期 touch/重编前提成立。
7. 范围实测（`wc -l`）：Rust 源 7 文件 **2945 行**（types 197 / core 909 /
   lib 862 / committee 185 / committee_certified 433 / assessor 273 / timeout 86，
   lib.rs 862 = R5 修复后 +12）+ Rust 测试 2 文件 **365 行**（181+184）+
   Python 9 文件 **2434 行**（rpc 962 / demo 810 / keeper 179 / protocol 161 /
   llm 98 / broker 93 / alice 68 / bob 56 / `__init__.py` 7）。
8. ✅ verify_core 测试计数实测（`grep -c '#\[test\]'`）：core 23 + committee 4 +
   assessor 6 + escrow_lifecycle 5 + modelcheck_refund 2 = **40**——壳 crate
   `src/lib.rs`（14 行）与 `tests/*.rs`（各 5 行）仅以 `#[path]` 绝对路径挂载
   仓库内 types/core/committee/assessor 与 lyquid/tests 两文件，**测的即当前
   仓库态**；任务书门禁「cargo test --lib --tests 40/40」的 40 与此吻合
   （规划期未跑 cargo test，编码期按 §5-G5 复跑）。
9. 备份双件之一已落盘：`_plan-prev-r6-backup.md`（md5 两侧一致，见 §0 #A1）。

## 2. R5 台账继承（焦点④的输入；原文 = `_plan-prev-r6-backup.md` §2.2/§5）

15 项未修（3×P1-R + 12×P2），原位置与原处置照录；**注意 R5 已顺带修掉其中
两处半**（P2-1 的 demo.py `SLOT_MS` 死 import；P2-2 的 keeper.py:19-20/:68、
demo.py:92-93/:117/:416、lib.rs:400 共 6 处行号注释）——编码期逐项按**当前
代码**实查残量后再判定。

| ID | 原位置 | 原处置摘要 |
|---|---|---|
| P1-R1 | rpc.py:441-450 | `_rpc` 对非 JSON 响应（网关/HTML 错误页）`r.json()` 裸抛、连接异常裸抛；登记不修（控制改动面） |
| P1-R2 | broker.py:31、llm.py:62 | live 模式畸形 LLM 响应 → KeyError/IndexError 裸 traceback；登记不修（仅真实后端路径） |
| P1-R3 | timeout.rs:54-63 | `watcher_step` 单笔 claim 失败 `?` 整轮中断；登记不修（watcher 无许可且幂等，下轮自愈） |
| P2-1 | rpc.py:56 `field`、demo.py:63 `SLOT_MS`（R5 已删）、alice.py:16 | 死 import；残余按当前代码实查 |
| P2-2 | 10 处行号注释漂移（6 处 R5 已修） | 残余 4 处：rpc.py:426/:500/:895+911-915、protocol.py:19 |
| P2-3 | committee.rs:78-90 shim、timeout.rs:86、lib.rs:723-725 slash 分支 | 死代码登记不删（lyquid 面删除须重编 wasm） |
| P2-4 | committee.rs:45-49 `_ => Malicious`、rpc.py:919 sim KeyError | 判定面漂移；链侧改映射=判级行为变更（红线），W4 处置 |
| P2-5 | protocol.py:30 vs demo.py:256/:388、broker.py:38-40 | 双规范化并存（ensure_ascii 差异）；当前载荷全 ASCII 无分叉 |
| P2-6 | rpc.py:809-813、:826/:855/:871/:879/:887/:894 | FakeNode 非镜像面 + assert 守卫 `python -O` 下消失；sim 定位=编排冒烟 |
| P2-7 | broker.py:57-59 | 硬编码默认成员 node-1..4（与 rpc.py:398 口径相悖；agent CLI 独立入口） |
| P2-8 | demo.py:350-354 | due 扫描每 deal 3 次 deal_info（node-only 效率） |
| P2-9 | demo.py:147-176 | `wait_for` 的 node 形参未使用（签名稳定性优先） |
| P2-10 | core.rs:245-247 | `threshold > 成员数` 可配置 → 恒 InsufficientCommittee（fail-closed 方向死锁型） |
| P2-11 | types.rs:174-176 | `Payout::total` 裸加法（u128 理论回绕面；types.rs 冻结约束） |
| P2-12 | workflow-out/demo-script.md、docs/演示与运行指南.md | 行号引用类文档漂移；编码期实查后只登记不改写（只读件） |

## 3. 子任务拆分与执行顺序（T0→T8；§3.1–3.6 = 六焦点的逐文件锚点与判据）

| 序 | 子任务 | 产出/判据 |
|---|---|---|
| T0 | 备份与定格（**规划期已完成大半**） | #A1 已落盘；§1 九项预置事实 |
| T1 | 焦点① 访问控制与攻击面 | §3.1 核对表 + 滥用路径判定（每条可达/不可达 + 代码证据） |
| T2 | 焦点② 经济不变量 | §3.2 守恒核对表（全部可达转移 × Payout 四分支）+ fee/溢出边界结论 |
| T3 | 焦点③ R5 修复正确性复核 | §3.3 逐项「未引入新问题」结论（含误伤核查） |
| T4 | 焦点④ R5 台账 15 项重评 | §3.4 逐项「维持登记 / 升级必修」判定 + 理由 |
| T5 | 焦点⑤ Python 编码层深审 | §3.5 编码面×调用方一致性核对表 + 错误路径判定 |
| T6 | 焦点⑥ dashboard 只读交互面复核 | §3.6 三项纪律核对（选择器/读回/单次） |
| T7 | 修复实施（P0 必修、P1 择优） | §4 规则；快照 #A3 先落盘；verify_core 义务触发则先跑 |
| T8 | 门禁复跑与产出 | §5 G1-G5 全跑登记；implementation.md 按惯例产出 |

### 3.1 焦点①：访问控制与攻击面（T1）

**矩阵核对表**（期望值=任务书原文；声明=lib.rs:212-225 实读；执行=require
单点 lib.rs:230-246 实读：caller 经 `ctx.caller: Address` 字符串化进 AgentId 域，
Committee 行查 `state.committee_members` **空集即拒=fail-closed**）：

| 方法（lib.rs） | 矩阵声明 | require 使用 | 期望（任务书） |
|---|---|---|---|
| faucet :281 | Anyone（:213，TODO(W2) DEMO flag） | 无 require（Anyone 等价） | Anyone ✓ |
| create_deal :296 | Broker（:214） | :308 `require(Access::Broker,…)` | Broker ✓ |
| fund :357 | Buyer（:215） | 方法内（编码期实读行号） | Buyer |
| notarize :398 | Anyone+自署名（:216「from 强制等于 caller」） | 方法内 + from==caller 断言 | 自署名 ✓ |
| submit_deliverable :419 | Seller（:217） | 方法内 | Seller |
| complete :433 | Buyer（:218） | 方法内 | Buyer |
| claim_timeout :454 | Anyone（:219 permissionless） | 方法内（守卫在 core 重推导） | permissionless ✓ |
| cancel :468 | Buyer（:220） | 方法内 | （任务书未列，核对 Buyer 语义） |
| open_dispute :487 | BuyerOrSeller（:221） | 方法内 | BuyerOrSeller ✓ |
| apply_committee_verdict :520 | Committee（:222，signers 含 caller） | 方法内（成员门+证书校验） | Committee ✓ |
| committee_config :545 | Broker（:223） | 方法内 + R5 threshold>0 门 | Broker ✓ |
| getters :566/:583/:594/:605 | Anyone（:224 只读） | 只读无资金效应 | Anyone ✓ |

逐行核对「声明=执行」；任何漂移按 §4 分级。

**攻击者视角滥用路径（5 类，逐条给可达/不可达判定 + 证据）**：
1. **签名/证书重放与跨单复用**：demo 域证书无签名占位（lib.rs:222 诚实边界），
   防重放依赖 `validate_cert`（core.rs:235-253）把 `evidence_root` 绑定到**本单
   当前全量证据序列**（:249-251，错配 → MissingCert，TODO(W4) 专用变体）；e2
   域认证签名 = `ctx.cert.signers`（committee_certified.rs:355-356）。核对点：
   跨单复用证书是否被 root 绑定挡死；signers 与 caller 的关系（矩阵 ：222
   「signers 包含 caller」在 :520 方法体的执行证据）。
2. **阈值绕过**：成员域阈值源 = `committee_config` 写入的 network 状态；计数门
   core.rs:245-247（`signers.len() < threshold` → InsufficientCommittee）；重复
   signer 去重 core.rs:241-243；e2 域阈值 = oracle `set_threshold`
   （committee_certified.rs:119-123 阈值 0 已拒，R5 P1-1 镜像）。核对点：两域
   阈值源是否都可被非授权方改写（committee_config=Broker 门；e2_configure 门=
   部署钥，rpc.py:685-697 走 cast）。
3. **重复结算**：终态封死（types.rs:51-53 is_terminal + core.rs require_states
   各转移）；apply_verdict 仅 Disputed（core.rs:199）；claim_timeout 仅 Funded
   （core.rs:171）；complete 的 Committee 授权路径（core.rs:123-138）与
   apply_verdict 的状态互斥。核对点：同一笔资金经「complete×2 / complete 后
   verdict / verdict 后 claim」等排序是否全部被状态机拒绝（已有 modelcheck
   720 排序背书，R5 §2.1 引 modelcheck_refund.rs:118-184；本轮复核该结论仍
   覆盖当前代码）。
4. **伪造署名**：notarize 自署名强制（lib.rs:216，from==caller，仲裁#3）；归属
   可信性链条 = committee.rs:63-65 注记 + check_evidence_shape（:66-74）只认
   卖家→买家方向条目 + deliverable 匹配。核对点：from≠caller 的条目能否入库；
   伪造 acceptance 条目（payload 冒充）在 demo 域的可达性（digest 即身份，
   无签名——诚实边界，判定其是否仍在已文档化信任洞范围内）。
5. **未注资取款**：claim_timeout 全额退仅 Funded 且过 deadline（core.rs:170-178，
   未到 → DeadlineNotReached）；cancel 仅无证据时（P2 台账 R5「cancel_only_
   without_evidence」core 测试 ：432）；apply_payout 全零 no-op（lib.rs:697-699，
   R5 F2，编码期实读复核）。核对点：Qualified（未注资）状态所有取款路径是否
   封死；faucet 无上限 + BROKER 常量 = anvil#0 硬编码（lib.rs:208）作为**已
   文档化 demo 信任洞**（lib.rs:277-279 TODO(W2)）重申，不判新缺陷。

### 3.2 焦点②：经济不变量（T2）

**资金守恒 = 每个可达转移后 `Payout::total() == deal.amount` 且四方分账与状态
一致**。可达转移全集与核对点：
- `fund`（lib.rs:357-397）：预检→core::fund（core.rs:61）→debit 顺序契约
  （R5 §2.1 实证，编码期实读行号复核）；重复 fund 被 require_states 拒。
- `complete`（lib.rs:433 + core.rs:138-168）：Buyer 授权 → `Payout::settle`
  （types.rs:165-172，fee = saturating_mul/10_000 的 min(amount) 钳制，
  to_seller = amount-fee 恒不 underflow，types.rs:159-164 doc 契约）；fee_bps
  上限在 core::create（core.rs:49-59 InvalidFeeBps，lib.rs:317-319 注记）。
- `claim_timeout`（core.rs:170-178）：仅 Funded + 过 deadline → 全额退
  （Payout::full_refund）。
- `cancel`（core.rs:82-110）：无证据时退；已提交证据后 cancel 被拒（cancel 与
  late-evidence 竞态类被状态机消除，types.rs:29-33 doc）。
- `apply_verdict`（core.rs:191-218）三裁决：Fulfilled→settle、NotFulfilled→
  full_refund、Malicious→full_refund + misconduct+1（core.rs:205-208）；
  终态映射 F4 修复（:213-216，fee_bps=10_000 时 Fulfilled 仍 = Settled）。
  **Malicious 不罚没资金**——slash_to_treasury 分支在 lib.rs:723-725 为 P2-3
  登记死代码；本轮重评：维持登记 vs 删除（删除须重编 wasm）vs 升级实现。
- 记账单点：`credit`（R5 A2 改 checked_add，5 个调用点 = faucet + apply_payout
  内 4 处 :715/:718/:721/:724，implementation.md A1-A2 在案）与 `debit` 预检
  （lib.rs:680-683，编码期实读复核）。
**fee 与溢出边界**：`Deal::split`（types.rs:140-143）与 `Payout::settle` 同式；
u128 饱和角由 core 测试钉死（`fee_rounding_edges_conservation`:476、
`split_never_underflows`:499、`verdict_fulfilled_full_fee_still_settled`:593）；
`Payout::total` 裸加法（types.rs:174-176，P2-11）重评——入账侧已有 credit
checked_add 拦截，回绕需 faucet 级荒谬值，判定维持登记/升级并说明。

### 3.3 焦点③：R5 修复自身正确性复核（T3）

逐项验证「修复无新问题」（对照 implementation.md（R5）§1）：
- **A1**（P1-1）：lib.rs committee_config 函数体内 `threshold == 0 → Err`
  （"committee threshold must be > 0"，镜像 e2 域 committee_certified.rs:119-123
  与 core.rs:245-247 计数门失效机理）。复核：误伤面=全库调用点均非 0
  （demo.py:595 E2_THRESHOLD=4、demo.py:777 THRESHOLD=3、broker.py:59 默认 3，
  implementation.md A1 实证；编码期 grep 复跑）；门的位置在 require 之后、
  状态清写之前（顺序正确性）。
- **A2**（P1-2）：credit 签名 `-> LyquidResult<()>` + checked_add（5 调用点加
  `?`）。复核：错误路径上抛后状态是否半写（credit 在余额写回前失败 = 无副作用，
  编码期实读核对）；wasm release 无溢出检查的前提仍成立。
- **B1a/B1b**（P1-3）：demo.py:366 timeout 流 node 分支终态断言、:319 normal 流
  终态断言（status 0x1 ≠ 方法 Ok 的读回纪律，rpc.py 模块 docstring 口径）。
  复核：断言只加在 node 分支、sim 分支零改动（基线逐字面保持的前提）。
- **C1/C2**（P1-4）：keeper.py:151-152 `--interval <= 0 → p.error`、:157-158
  `--deals` 解析空表 → p.error。复核：fail-closed 退出而非静默空转；discover
  默认路径（:161）不受影响。
- 每项给出「未引入新问题 / 发现回归（=新 finding 按 §4 分级）」结论。

### 3.4 焦点④：R5 未修 15 项重评（T4）

对 §2 表逐项给出：**维持登记 / 升级必修**（升级 = 说明为何 R5 的登记理由在
R6 安全视角下失效 + 改动点 + 门禁影响）。重点候选（规划师预判，编码期以
证据定夺）：
- P1-R3：timeout.rs:61 `.ok?` 单笔失败中断整轮——安全视角影响 = 阻塞同轮后续
  due 单 claim（DoS 型延迟，非资金错误）；幂等 + keeper 每轮重试自愈；重编
  wasm 成本。倾向维持登记，除非 T1 发现守卫面依赖 watcher 及时性。
- P2-5：非 ASCII 载荷下 protocol.py:30（ensure_ascii=False）与 broker.py:38-40
  （默认 ensure_ascii=True）digest 分叉——当前载荷全 ASCII（T5 实查所有
  envelope 字段域），分叉不可达 → 维持登记；若可达 → 升级。
- P2-10：`threshold > 成员数` 可配置（core.rs:245-247）——fail-closed 方向
  （恒拒），非安全洞 → 维持登记，建议 W4 与 EvidenceMismatch 一并处理。
- P2-11：types.rs:174-176 裸加——入账侧 checked_add 已拦截，types.rs 冻结
  约束 → 维持登记（除非 T2 发现绕过 credit 的入账点）。
- P2-4：链侧 `_ => Malicious`（committee.rs:45-49）——**判级行为红线**，
  维持登记，W4 oracle 签名认证处置。

### 3.5 焦点⑤：Python 编码层深审（T5）

**编码器全类型核对**（rpc.py:194-278 实读在案）：`_enc_value`（string :203-205 /
string[] :206-222（R2 偏移修正内注）/uint* :223-224 /bool :225-226 /集外抛
ValueError :227）、`_encode_args`（:234-244，动态偏移=head_size+len(tail)）、
`_decode_ret`（:247-273，string[] tail=base+32 R2 修正）、`_sig_types`
（:276-278）。**仍无 bytes32/bytes32[]** = 终裁冻结条款 1（e2_configure 走
cast send 通道，rpc.py:160-162 注记 + :685-697 实现）。
**核对方法**：先 dump NodeClient `_ABI` 全表（`__init__` 区，编码期实读行号）
逐行 × `_enc_value/_is_dynamic` 支持集 × wire 参数与 lib.rs 方法签名对齐
（faucet(U128 边界转换 lib.rs:286)、create_deal 9 参、apply_committee_verdict
扁平 (uint8,string[]) lib.rs:263 注记）。
**已证对齐面**（任务书列名，本轮复核不推翻、只登记新证据）：五视图
deal_info/balance_of/evidence_entries_json/due_deals/e2_net_config + 五写面
faucet/notarize/create_deal/fund/claim_timeout（含页内 sha256 规范化与 FNV
证据根逐字节一致）。
**复核未覆盖面**（本轮主战场）：
- discover_deals（rpc.py:505）/ assess_brief（:643-660，trust hole：api_key 进
  calldata，doc :652-655）/ cancel（:586）/ submit_deliverable（:572）/
  complete（:575）/ open_dispute（:589）/ apply_committee_verdict（:592）
  的编码面、返回解码与 lib.rs 签名一致性；
- NodeError（:165-178，携带原始错误不折叠）/ TxError（:181-182，status≠0x1）/
  `_rpc`（:441-450，P1-R1 重评）/ `_view`（:455）/ `_send`（:464-485，断言
  status=="0x1" + receipt 返回）全错误路径：非 JSON 响应、HTTP 错误、超时、
  `python -O` 下 assert 消失面（P2-6 交叉）；
- protocol.py：canonical_json（:29-30）/digest（:33-34）/evidence_root
  （:65-90）vs core.rs:287-298 **逐字节同规**（字段序、分隔符、UTF-8、空表=
  `cbf29ce484222325`、顺序敏感不重排）；P2-5 双规范化残面实查（所有
  envelope/payload 字段域是否全 ASCII）；
- 两个调用方交叉：agents CLI（alice/broker/bob 的 rpc.py 用法 + keeper 直用
  `_send` keeper.py:116）与 scripts/dashboard.html（只读，页内编码/选择器
  与本表一致性 → 焦点⑥）。

### 3.6 焦点⑥：dashboard 只读交互面复核（T6）

`scripts/dashboard.html` **只读零改动**，复核三项纪律：
1. **选择器冻结一致**：页内调用的方法 selector 与 `_ABI`/容器 cast 通道一致
   （e2_configure 走 cast send、e2_run_verdict_round 走 cast call——cast send
   对内部异步提交类方法 status 1 但内层静默丢失，S2 §3/§4 实证口径，
   rpc.py:699-710 doc）。
2. **status 0x1 ≠ 方法 Ok 的读回纪律**在两个调用方（页内 + agents/keeper）都
   成立：keeper 榜样 = 提交后 `_read_back` 终态判定（keeper.py:124-131）；
   demo B1a/B1b（demo.py:366/:319）。核对页内发交易后的读回逻辑同口径。
3. **e2_arm 单次纪律**：rpc.py:667-675 doc「单次发送全节点生效」+ 门=creator
   （部署钥 anvil#0）；核对页内与 demo 侧调用是否有重复 arm 面。
产出 = 三项核对表（一致/漂移；漂移只登记——dashboard 只读，若漂移构成
P0 则在 §4 分级时说明「修复只能落在 rpc.py/文档侧」的约束）。

## 4. 修复实施规则（T7）

- **P0（真缺陷：资金语义/守恒、越权可达、误报漏报、fail-closed 失效）必修**：
  逐条给「位置/根因/最小修复/门禁影响」；修复前先落快照 #A3。
- **P1（加固）择优**：准入三条件——不触 §6 红线、改动面小（单文件单点优先）、
  有钉死测试或门禁护航。R5 残留 P1-R1/R2/R3 与本轮新发现 P1 同池择优。
- **P2 只登记**（不改代码）；行号漂移类（P2-2 残余、P2-12）编码期实查后只登记。
- **types.rs/core.rs 语义改动义务**：改动前先复跑 verify_core 确认 40/40 基线，
  改动后复跑确认仍 40/40，两次输出都登记（壳 crate `#[path]` 绝对路径挂载，
  测的即当前仓库态，§1-8）。
- **lyquid 面任何源码改动**：编码期先 `touch <改动文件>` 再跑容器 cargo check
  并注明重编（§1-5/6 前提已核实）。
- **console 打印面 / 判级行为 / E2_AVG_NUM=4 / 方法签名 ABI 零变化**；
  sim 路径零改动（`--sim --flow all` 输出须与冻结基线逐字一致，§1-3）。

## 5. 门禁与产出（T8；命令照抄执行）

| # | 门禁 | 命令 | 通过判据 |
|---|---|---|---|
| G1 | 语法 | `python -m py_compile <全部改动的 py>` | rc=0 |
| G2 | 自检 | `python scripts/demo.py --selftest` | rc=0，SELFTEST OK |
| G3 | sim 基线 | `python scripts/demo.py --sim --flow all` 输出 vs `workflow-out/_r2-t0-sim-baseline-raw.txt` `diff -u` | 零差异（BASELINE-DIFF-IDENTICAL） |
| G4 | Rust 编译（只读） | `MSYS_NO_PATHCONV=1 docker exec -w /tmp/tb-lyquid multi-tools cargo check --target wasm32-unknown-unknown`（有源码改动先 touch 并注明） | rc=0；warning 数记录 |
| G5 | 模型检查壳 | 仓库外 `workflow-out/verify_core`：`cargo test --lib --tests` | **40/40**（仅 types/core 语义有改动时强制；未改也建议复跑一次留记录） |

产出（编码期写入 `workflow-out/implementation.md`，覆盖前备份 #A2）：
1. **分级 findings 清单**——每条：ID / 级别（P0/P1/P2）/ 位置（文件：行号）/
   问题一句话 / 证据（代码引用或命令输出）/ 处置（修/登记）；
2. **已实施修复的 diff 摘要** + G1-G5 门禁复跑结果实录；
3. **与 R5 台账的差异说明**——15 项逐条「维持登记/升级必修/已顺带修」+
   本轮新 findings 与 R5 分级的映射。

## 6. 红线表（违反 = 直接 REVISE）

| # | 红线 | 依据 |
|---|---|---|
| ① | devnet 零链写零部署零重启（一切验证只读） | 任务书纪律 |
| ② | 零 git 写（不 commit/add/push/restore/stash…），回退=cp 原件 | 任务书纪律 |
| ③ | `scripts/dashboard.html`、`docs/b3-user-test/`、`workflow-out/report/`、`workflow-out/slides/`、`_submission-plan.md` 只读 | 任务书纪律 |
| ④ | 判级行为（含 committee.rs:45-49 未知 verdict_code→Malicious）、console 打印面、E2_AVG_NUM=4（committee_certified.rs:91）零变化 | 任务书纪律 |
| ⑤ | types.rs/core.rs 语义改动必须先复跑 verify_core 40/40 并登记 | 任务书纪律 |
| ⑥ | sim 输出 = 冻结基线逐字一致（G3）；编码器集外类型零扩展（终裁冻结条款 1，rpc.py:160-162） | 任务书/R3 终裁 |

## 7. 风险与回退

| 风险 | 概率/影响 | 缓解与回退 |
|---|---|---|
| R1 审计发现 P0 集中于 types.rs/core.rs 语义面 | 低/高 | 触发 ⑤义务：verify_core 改前改后双跑登记；快照 #A3 先行；回退=cp `_r6-orig-*` 原件（零 git 写） |
| R2 修复扰动 sim 输出（B1a/B1b 在 node 分支，误改 sim 分支） | 中/中 | G3 逐字 diff 立即暴露；回退=cp 原件重改；sim 分支零改动是硬规则 |
| R3 容器 multi-tools 不可用 | 低/中 | G4 如实登记「未跑」，不虚报；编码期重试；规划期已验证可用（§1-5） |
| R4 误改只读件（dashboard.html 等） | 低/高 | 快照比对 + cp 还原；git status 实查（只读件不得出现在 diff） |
| R5 findings 面扩大导致轮数吃紧 | 中/中 | P2 只登记 + P1 择优天然限面；P0 全修不动摇；轮内按 T1→T8 顺序收敛，审查员按 §0 清单核对改动面 |
| R6 清场删除 workflow-out/{plan,implementation,ledger}.md 后 R5 台账丢失 | 已缓解 | R5 台账全文内嵌本方案 §2（原文另有 `_plan-prev-r6-backup.md` 双保险） |
| R7 行号漂移（本轮改动后 demo-script.md / docs 漂移加剧） | 高/低 | P2-12 惯例：只登记不改写（只读件） |
