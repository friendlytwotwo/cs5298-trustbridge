# R3-T5+T6 方案：B3 三文档与回归收尾（规划师，2026-10-30）

六阶段拆分③：文档 + 回归任务，**无实跑部署、无任何链写**（不发交易、不建新 deal、不重跑
committee 流）。前置：T3 E2 已 L2 达成（实例 `Lyquid-ybidj3krshf4gqcjk3m3px6mooi6tg74twwaa`
@ `0x87006e75a5B6bE9D1bbF61AC8Cd84f05D9140589`，`w1b2-r3-e2-committee.md` §T3 + `_r3-t3-*` 四件）；
T4 对照报告已交付（`r3-t4-contrast-report.md`，implementation.md §8）。旧 T4 方案已备份为
`_plan-prev-r3t5t6-backup.md`（本轮规划期 cp 逐字节备份，md5 `a7eb173cab74ccd8c4a873d0ad9a8d56`
两侧一致）。R3 全案（含 §3.4 判级阶梯、§5 B3 定义、T5/T6 行）存于 `_plan-prev-r3-backup.md`。

## 0. 受影响文件清单（9 项，供审查员核对）

| # | 文件 | 动作 |
|---|---|---|
| 1 | `workflow-out/plan.md` | 覆盖写（本方案；旧 T4 方案 → #2 备份） |
| 2 | `workflow-out/_plan-prev-r3t5t6-backup.md` | 已建（本轮规划期 cp，md5 `a7eb173c…` 一致） |
| 3 | `scripts/demo.py` | **改（D-T3-1 行为修复）**：:622-623 区插入 faucet 读回确认后再快照；:692-696 断言本体零改动（详见 §4-#3） |
| 4 | `docs/b3-user-test/操作手册.md` | **新建**（目录一并新建；全案 §5 既定位 `docs/b3-user-test/`） |
| 5 | `docs/b3-user-test/通过判据.md` | **新建** |
| 6 | `docs/b3-user-test/反馈收集表.md` | **新建** |
| 7 | `workflow-out/_r3-t6-regression-raw.txt` | **新建**：T6 回归实录（selftest / sim 逐字 diff / 壳 40/40 / 冻结门 / 修复 diff 摘要） |
| 8 | `workflow-out/_commit-plan.md` | 增补 §6 R3 提交序列 + 全部 M/?? 文件覆盖表（执行时 `git status --porcelain` 逐行归组） |
| 9 | `workflow-out/implementation.md` | §5 追加 R3 偏离总表（不删原文）+ §3/§6 状态核销 + 文末追加 §9（本轮执行说明） |

**零改动声明**：`lyquid/` 全部（types.rs/core.rs/committee.rs/assessor.rs/lib.rs/committee_certified.rs
md5 不变）、`experiments/`、`agents/`、`scripts/keeper.py`、README、全部 `_r3-t3-*`/`_r3-t4-*`
既有日志只读；不 git commit / add / push。

## 1. 已采信前提（任务陈述前置 + 本轮规划期实跑核验）

1. **判级口径出处**：任务述「引用 plan.md §3.4」——§3.4 现存于 R3 全案备份
   `_plan-prev-r3-backup.md:108` 起（L2/L1/L0 定义在其第 5 点「参与度分级结论表」：
   L2 = inputs=4 + signers=4；L1 = 1 提案 + 4 签（avg_num=1）；L0 = 平台硬限制三段式诚实报告，
   绝不以单签冒充四节点）。T5 判据文档引用时写明该路径（plan.md 已按阶段覆盖写，全案冻结条款
   与 §3.4 以备份件为准）。
2. **L2 已达成**：console 判级行（`_r3-t3-console-raw.txt` 原文行号）——:24
   `e2_aggregate: agreed deal=deal-1 verdict=1 from 4 input(s) (avg_num=4)`、:31
   `cert.signers RAW = [0, 1, 2, 3] (Vec<SignerID>=Vec<u32>, len=4)`、:32-:35 四条
   `signer N -> Node-…` 映射（四个互不相同 NodeID）、:30/:31/:36 certified/裁决各仅一次、
   :38 `deal_info … "state":"Refunded"`；读回勾稽 5 项与 GT3 a–f 见
   `w1b2-r3-e2-committee.md` §T3（:91-:99、:144-:153）。
3. **D-T3-1 病灶在位**（本轮实读 `scripts/demo.py`）：:622 `node.faucet(alice, 10_000)` 后
   **立即** :623 `before = snapshot()`（读路径滞后一块 → before[alice]=0，实录
   `_r3-t3-committee-raw.txt:41` 以 `refund accounting mismatch` 误报收尾）；:692-696 断言
   `after == before` 语义本身正确，根因是 stale baseline。`node.faucet` 为 fire-and-forget
   send（`agents/common/rpc.py:492-494`），`balance_of` 为 view（rpc.py:628-630）；
   `wait_for(node, predicate, timeout_s, interval_s, *, what)`（demo.py:147-176，间隔递增
   1s→2s→4s、pending/硬失配两语义可区分、**仅 node 路径使用**）是现成读回轮询 helper；
   `require_funds`（demo.py:179-188）读回断言余额门。链上事实（faucet 恰一次、全额退款、
   bob/broker 恒 0）由 `_r3-t3-final-state-raw.txt:19-28`（blocks 0-341 全量扫描仅 1 笔
   faucet@333）与 :11-16（4/4 PASS）独立证明。
4. **sim 逐字比对基线**：`_r2-t0-sim-baseline-raw.txt`（23 行冻结件）；比对方法先例 =
   implementation.md:245-246（`python scripts/demo.py --sim --flow all > /tmp/…; diff -u
   workflow-out/_r2-t0-sim-baseline-raw.txt /tmp/…` → 无输出 IDENTICAL）。
5. **壳 40/40 通道**：壳 crate 位于**仓库外** `F:\canvus auto\downloads\202609CS5298\workflow-out
   \verify_core`（`_commit-plan.md` §3 已登记归属），`cargo test --lib --tests` = 33(lib)+5
   (escrow_lifecycle)+2(modelcheck_refund)=40（`_r2-t7-regression-raw.txt:3-9` 宿主先例）。
   **关键约束（本轮实读）**：`verify_core/src/lib.rs:4-13` 与 `tests/escrow_lifecycle.rs:4`、
   `tests/modelcheck_refund.rs:4` 的 `#[path]` 指向**宿主绝对路径** `F:/canvus auto/…`（Windows
   盘符形）——Linux 容器内将按相对路径解析（`<crate>/src/F:/…`、`<crate>/tests/F:/…`）。
   **本轮规划期实跑**（2026-10-30，宿主）：`rustc --version` → 1.99.1；`cd
   ../workflow-out/verify_core && cargo test --lib --tests` → **33+5+2 全 passed、0 failed
   （40/40）**——任务述「宿主工具链损坏」在当前机器状态**不成立**，以实跑为准；容器通道
   降级为 fallback（规格见 §5-R2，零文件改动的目录形映射法）。
6. **冻结门**（G2 口径，全案 T6 行）：三文件 `git diff --stat lyquid/src/{types,core,committee}.rs`
   空 + `md5sum -c _r2-t0-frozen-baseline.txt` 四 OK（已知 WARNING 1 line improperly formatted
   属正常，`_r2-t7-regression-raw.txt:20-25`）+ `assessor.rs` 对 HEAD `+5` 在场；
   `committee_certified.rs` md5 `83e358ee…` 与 `E2_AVG_NUM=4` 不变（GT3-f 口径）。
7. **提交面现状**：本轮勘察 `git status --porcelain` = **93 个 M/??**（8 M：README/rpc.py/
   assessor.rs/lib.rs/demo.py/keeper.py/implementation.md/plan.md；?? 含 experiments/、
   committee_certified.rs、_collab/、_r1-/_r2-/_r3-* 日志、备份件、probe 件等）。
   `_commit-plan.md` 现有 §2 R1 序列（C1-C4 + R1-不入库）、§3 壳归属、§5 R2 序列（C5-C8），
   **无 R3 分组**。多轮共改文件的入库归属须重排（见 §4-#8）。
8. **implementation.md 现状**（555 行）：§5 偏离与事实修正 = T2 期 12 条（:307-361）；T3 偏离
   D-T3-1/D-T3-2 在 §7.3（:445-457）；T4 偏离 D-T4-1..7 在 §8.4（:534-545）；§6 未尽清单
   11 行（:363-377，#4 T5/#5/#6 T6/#3 T4 待核销）；§7.5 遗留表把「对抗流 node 复跑」排向
   T6（:479）——**本任务陈述未授权任何链写实跑**，该项只能如实登记为遗留（§5-R7）。
9. **docs/ 布局**：`trustbridge/docs/` 在位（5 份项目文档），`docs/b3-user-test/` 不存在，
   本轮新建（全案 §5 既定路径，`_plan-prev-r3-backup.md` §5「docs/b3-user-test/，3 文件」）。
   全案 §5 三件 = 操作手册/演示脚本/反馈收集表；**任务陈述三件 = 操作手册/通过判据/反馈收集表**
   （演示脚本不在本任务面）——按任务陈述交付，登记 D-T5-1（§4-#4）。
10. **环境**：本轮实跑 `docker ps` → 7 容器全 Up 15 hours（multi-tools / node1-4 / registry /
    anvil）。宿主 Python 3.14.5、Git Bash；容器 cast/forge 1.7.1（implementation.md §0）。

## 2. 目标与诚实红线

**目标**：①交付 B3 三份面向组外用户的文档（命令/输出/判据全部回填自已档实录，可照跑、可复核）；
②完成 D-T3-1 行为修复并以 selftest + sim 逐字 + 壳 40/40 收口回归；③`_commit-plan.md` 增补
R3 分组覆盖全部 M/?? 文件；④implementation.md 合并 R3 各阶段偏离与增量（不丢条目）。

**诚实红线（硬约束）**：
- 三文档**只引用已发生的真实证据**（`_r3-t3-*`/`_r2-*`/console 原文行、代码 `文件:行号`），
  不虚构输出、不引用未来事件；无已档实录的预期行为（如修复后新增的 faucet 读回行）只能写
  「预期将打印（代码行）+ 本行无已档实录（修复后未重跑，诚实边界）」。
- 修复的验证口径如实：selftest + sim 逐字 diff + py_compile + `--sim --flow committee`
  node-only 门控行为；**flow_committee 端到端重验需新实例，不在本任务授权面**（无实跑部署），
  不得伪装已验证。
- 判级只认 console 原文行与读回（status≠effect）；引用行号一律用实查行号（D-T4-5 教训：
  plan 引用与实际行号曾有偏差，引用前逐条回验）。
- 冻结面（lyquid 全树）零改动；全程不 git commit/add/push。

## 3. 子任务拆分与执行顺序（依赖序；编号沿任务陈述，执行序说明理由）

> 执行序 = **T6.0 → T6.1 → T6.2 → T5.1 → T5.2 → T5.3 → T6.3 → T6.4 → T6.5**。
> 理由：①修复（T6.1）先行——操作手册必须如实标注「已档实录 = 修复前行为」，先定稿修复才能
> 写准这条边界；②三文档（T5）次之；③提交计划（T6.3）与 implementation 合并（T6.4）最后——
> 两者都必须覆盖本轮全部新产物（三文档 + 回归日志 + 修复 diff）。

**T6.0 前置核验**（→ #7 头部）：`docker ps` 7 容器 Up；`md5sum -c workflow-out/_r2-t0-frozen-baseline.txt`
4×OK；`git diff --stat lyquid/src/{types,core,committee}.rs` 空 + `git diff --numstat
lyquid/src/assessor.rs` = `5 0`；`git status --porcelain | wc -l` 记数（基线 93，本轮将新增
≥6：#2/#4/#5/#6/#7 + plan 备份之外的新日志）；修复前 `md5sum scripts/demo.py` 留档。

**T6.1 D-T3-1 行为修复**（→ #3 + #7 第一段）：
1. 按 §4-#3 改 demo.py（faucet 后读回确认再快照）；`python -m py_compile scripts/demo.py`。
2. `python scripts/demo.py --selftest` → 预期 `SELFTEST OK`（7 PASS，先例
   `_r2-t7-regression-raw.txt:11-12`）。
3. `python scripts/demo.py --sim --flow all > /tmp/r3-t6-sim.txt` → `diff -u
   workflow-out/_r2-t0-sim-baseline-raw.txt /tmp/r3-t6-sim.txt` → **预期无输出（IDENTICAL）**
   （修复只在 node-only `flow_committee` 内，先例 implementation.md:245-246 / §5-8）。
4. `python scripts/demo.py --sim --flow committee` → 预期 node-only 报错退出 rc=1（门控行为
   不因修复漂移，先例 implementation.md:247-248）。
5. 以上命令与输出全部原样入 #7（写日志**不用** `tee /dev/stderr`——D-T3-2 教训）。

**T6.2 壳 40/40 复跑**（→ #7 第二段）：主通道 = 宿主（R2 先例逐字）：`cd
../workflow-out/verify_core && cargo test --lib --tests` → 预期三条 `test result: ok`
33+5+2（0 failed）。宿主失败才启用容器 fallback（§5-R2 规格照抄执行，含 md5 勾稽）。
无论哪条通道，#7 须含完整命令行 + 三条 test result 行 + （容器通道时）勾稽记录。

**T5.1 操作手册**（→ #4）：结构（六节，命令序列全部取自实录并标 `文件:行号`）：
①前置环境（`docker ps --format` 7 容器 Up——`_r3-t3-deploy-raw.txt` T3.0 段；宿主 Python 依赖；
实例名/地址/TARGET 获取方式）；②部署（`MSYS_NO_PATHCONV=1 docker cp lyquid/. multi-tools:/tmp/tb-lyquid`
→ md5 勾稽 9/9 → `touch src/*.rs` + 容器 `cargo check --target wasm32-unknown-unknown` →
`shaker deploy -r http://registry:8000/lyquids --endpoint ws://node1:10087/ws --private-key
<anvil#0> Cargo.toml` → `created Lyquid-… => 0x…`；证据 `_r3-t3-deploy-raw.txt`（deploy 段
[QUOTED] 性质如实注明）；`shaker to-hex <实例名>` → TARGET 且断言非零 ≠ 合约）；③主跑建单
（`python scripts/demo.py --node http://127.0.0.1:10087 --contract 0x8700…589 --instance
Lyquid-… --flow committee`；逐步预期输出引 `_r3-t3-committee-raw.txt:10-29` 原文行：env/TARGET
OK、node1-4 NodeID、committee_config、e2_configure staged、advance True、dest_epoch poll、
finalize True、net_config activated、assess_brief、deal-1 Qualified→Funded→Disputed、arm 读回 OK、
run_verdict_round True、final Refunded；**:30-41 的 RuntimeError 段如实收录并标注 = D-T3-1
修复前行为 + 修复后该点预期（引 demo.py 打印语句，注明无已档实录）**）；④console 观察
（`MSYS_NO_PATHCONV=1 timeout 60 docker exec multi-tools shaker console <实例名> --endpoint
ws://node1:10087/ws`；关键行引 `_r3-t3-console-raw.txt:5/:15/:19-:24/:30-:38`；**必须用实例名
不是地址**；rc=124 = 正常超时收尾——`:39`，常见误判点）；⑤终态读回（NodeClient 只读快照命令
形态与 4/4 PASS 输出——`_r3-t3-final-state-raw.txt:4-16`；一切以读回为准）；⑥常见错误排查表
（每条带真实证据）：console 用地址而非实例名 / rc=124 误判失败 / 余额断言误报（D-T3-1 活例，
修复说明）/ advance 返回 False（staging-target mismatch，demo.py:606-607）/ arm 读回第三值即
abort 绝不重 arm（demo.py:648-658）/ 无 `--instance` 调 committee 流 fail-closed rc=1
（implementation.md:250-253 重录实录）。附录：其他三动线（normal/timeout/adversarial）与 EVM
对照实验的**已档证据指针**（`w1b2-r1-demo-normal.md` 等 + `r3-t4-contrast-report.md`）——
只给指针不复制命令（本任务证据面 = `_r3-t3-*`）。

**T5.2 通过判据**（→ #5）：①判级口径 L2/L1/L0 三层表（引 `_plan-prev-r3-backup.md` §3.4 第 5
点原文要义：L2 = inputs=4+signers=4（arm 一次 + node1 单次触发 + avg_num=4）；L1 = 1 提案+4 签；
L0 = 三段式诚实报告绝不单签冒充；fallback 触发条件）；②L2 验收清单（逐条引 console 原文行：
:24 / :31 / :32-:35 四映射且 NodeID 与 transcript node 行一致 / :30+:31+:36 各仅一次（无重复
结算）/ :38 Refunded）；③读回勾稽清单（5 项：arm 单次+读回、run_round 单次、终态 Refunded、
余额全额退款、misconduct 不增——`w1b2-r3-e2-committee.md` :93-:99 + `_r3-t3-final-state-raw.txt`
:11-:16）；④通用纪律（status≠effect 只认读回；R2 attempt-1「status 0x1 但 Disputed」活例
`_r2-adversarial-raw.txt:6`（D-T4-5 校正后行号）；两段 `agreed` 重复回放 ≠ 重复裁决——
`w1b2-r3-e2-committee.md` :87-:89）；⑤L1/L0 时的降级验收形态（按 §3.4 原文，注明本轮 L2 已
达成、未触发）。

**T5.3 反馈收集表**（→ #6）：四维结构（任务陈述口径）：任务理解（含两道信任模型理解题：委员会
认证从哪来 / 裁决能否被单点篡改——全案 §5 既有题面）/ 操作顺畅度（每步 1-5 分行项，对应操作
手册六节）/ 结果可信度（判据可复核性：console 行与读回勾稽是否亲眼可见）/ 开放意见（自由栏）。
纯表单，不虚构「示例反馈」。

**T6.3 `_commit-plan.md` 增补**（→ #8，文末追加 §6）：R3 提交序列（依赖序：先 lyquid 后
agents/scripts 后 experiments 后证据）：
- **R3-C1 lyquid**：`lyquid/src/committee_certified.rs`（新）+ `lyquid/src/lib.rs`（M，R3 增量；
  依赖 R1-C1/R2-C5 先行提交，否则 lib.rs 一笔带入三轮主题——沿 §5 既有提醒口径）。
- **R3-C2 agents/scripts R3 面**：`agents/common/rpc.py` + `scripts/demo.py` 的 R3 增量
  （flow_committee/--instance/容器通道助手；依赖 R3-C1 的方法面）。
- **R3-C3 D-T3-1 行为修复**：`scripts/demo.py` 修复 hunk 单独成提交（行为修复非重构，提交
  信息点明 —— R2-C6「行为修正」先例口径）；排在 R3-C2 之后。
- **R3-C4 experiments**：`experiments/evm-contrast/` 三件套（Escrow.sol/foundry.toml/
  run-contrast.sh）。
- **R3-C5 B3 文档**：`docs/b3-user-test/` 三件。
- **R3-C6 证据**：`w1b2-r3-e2-committee.md`、`r3-t4-contrast-report.md`、
  `_r3-t1-*/_r3-t3-*/_r3-t4-*` 全部原始日志、`_r3-t6-regression-raw.txt`、
  `implementation.md`/`plan.md`/`_commit-plan.md` **最终态**——三份轮文档被多轮改写，只能以
  最终态入库，从 R1-C4/R2-C7 的文件清单**移列**至本组（在 §6 里显式声明移列，C4/C7 描述保留
  时点语义）；`_r2-t0-frozen-baseline.txt`/`_r2-t0-sim-baseline-raw.txt` 已在 R2-C7，不重复。
- **不入库/归档**：`_pre-task-snapshot-r3.patch`（恢复凭据，沿 C8/R1-不入库处置）、
  `_plan-prev-*`/`_implementation-prev-*` 备份、`_probe_*`、`_collab/`（沿 R1-C5 归档建议）。
- **覆盖表（硬性）**：执行时 fresh `git status --porcelain` 逐行归组（C1–C8 + R3-C1..C6 +
  不入库），表行数 = 状态行数，零未归属；`_r1-*`/`_r2-*` 已在 C4/C7 清单者标「已归组」，两清单
  之外的遗留件（如 `_w1b1-*`）显式归「归档」组。§3 壳归属说明补一句：R3 轮壳仍零修改、只读复跑。
- 同时收录 D-T3-1 修复 = R3-C3（上文），文末保留「未执行任何 git commit」声明。

**T6.4 implementation.md 合并增量与偏离表**（→ #9，**只追加/改状态格，不删任何原文段落**）：
1. §5 文末追加「**5.13 R3 各阶段偏离总表**」：21 条索引 = T2 §5-1..12（在位）+ T3 D-T3-1/D-T3-2
   （§7.3）+ T4 D-T4-1..7（§8.4）+ 本轮新增（D-T5-1 演示脚本不在任务面 / D-T6-1 壳通道实况），
   每条一行：编号 + 一句话 + 原文位置指针；**原文不搬移不删改**；D-T3-1 行加注「已于 R3-T6 修复
   （行为修复，见 §9）」。
2. §3 门禁表：G5 行状态更新为已交付（指向 §9 与 #4-#6）；G6 行更新为回归三件套已跑
   （40/40 + sim IDENTICAL + 冻结门，指向 §9）。
3. §6 未尽清单：#3（T4）/#4（T5）/#5/#6（T6）状态核销（改状态列，原文字保留）；#2「对抗流
   node 复跑」维持**未执行**并补原因（本任务授权面无链写实跑）→ 去向改为「后续/用户安排」。
4. 文末追加「**## 9. §R3-T5+T6 执行实现说明**」：产物清单（#4-#9 + md5）、实跑命令摘要
   （T6.0-T6.2 全部）、勾稽关系（sim 逐字/40 计数/冻结 md5/commit 覆盖表行数）、偏离登记
   （D-T5-1、D-T6-1、D-T3-1 修复登记：行为修复非重构，验证口径与诚实边界）、G5+G6 门禁
   状态表。
5. **不丢条目自检**：合并前后 `grep -c` 偏离编号（12+2+7+新增）与 §6 行数逐条对账，写入 §9。

**T6.5 收尾自检**（→ #7 尾部 / §9）：重跑 T6.0 冻结门四件套（md5 四 OK、三文件 diff 空、
assessor +5、committee_certified.rs md5 与 E2_AVG_NUM 不变）；`git status --porcelain` 与
T6.0 记数对照（新增仅本轮 6+ 产物）；`git log --oneline -1` 仍 `dc78d2f`（未 commit/add/push）；
三文档引用抽查（每份 ≥5 处 `文件:行号` 逐一 grep 回验）。

## 4. 逐文件改动点

- **#1 plan.md**：本方案覆盖写（已执行；旧件 → #2）。
- **#2 _plan-prev-r3t5t6-backup.md**：已建（md5 `a7eb173c…` 一致，见 §0）。
- **#3 scripts/demo.py（D-T3-1 行为修复，~+14 行，两处病灶一次闭环）**：
  现 :622-623（`node.faucet(alice, 10_000)` + `before = snapshot()`）替换为：
  ```python
  pre_tap = node.balance_of(alice)
  node.faucet(alice, 10_000)

  def faucet_landed():
      bal = node.balance_of(alice)
      if bal - pre_tap >= 10_000:
          return True, bal
      return False, bal  # 读路径滞后（pending），继续等

  tapped = wait_for(node, faucet_landed, timeout_s=15.0, interval_s=1.0,
                    what="faucet read-back")
  print(f"[committee] faucet read-back OK: alice {pre_tap} -> {tapped} (+{tapped - pre_tap})")
  before = snapshot()
  ```
  要点：`pre_tap` 在**发交易前**读（无未决写，确定值）；`>=` 而非 `==`（单笔 faucet 原子落账，
  链上恰一次已由 `_r3-t3-final-state-raw.txt:24-26` 证明）；复用 `wait_for`（pending/硬失配语义
  可区分、仅 node 路径）；打印行与 arm 读回 OK（demo.py:662）同风格。**:692-696 断言本体零改动**
  ——其根因（stale baseline）已由读回确认消除；`before/after_fund/after` 语义不变（before 语义
  从「faucet 前旧值」修正为「faucet 落账后基线」，这正是缺陷本义）。**登记为行为修复非重构**
  （implementation.md §9 + `_commit-plan.md` R3-C3）。改动全部位于 node-only `flow_committee`
  内 → sim 代码路径零触碰（§3-T6.1-3 逐字门预期不变）。
- **#4 docs/b3-user-test/操作手册.md**（新建）：§3-T5.1 六节结构 + 附录指针；中文；「无仓库
  上下文的组外用户可照跑」标准自足（全案 §5 纪律）；每步 = 命令 + 预期输出（引实录行）+ 常见
  错误；头部注明证据基线日期与实例（已终态，用户复刻需自行部署新实例——部署节即为此提供命令）。
  **D-T5-1 登记**：全案 §5 的「演示脚本.md」不在本任务三件之列，按任务陈述交付；其动线要点
  （console 画面讲解）并入操作手册第④节一段。
- **#5 docs/b3-user-test/通过判据.md**（新建）：§3-T5.2 五部分；每条判据带 `文件:行号`。
- **#6 docs/b3-user-test/反馈收集表.md**（新建）：§3-T5.3 四维表单（Markdown 表格，含填写说明）。
- **#7 _r3-t6-regression-raw.txt**（新建）：头部（日期/HEAD `dc78d2f`/纪律声明）+ 四段
  （T6.0 冻结门与环境 / T6.1 修复摘要（修复前后相关行摘录 + py_compile + selftest + sim diff
  原始输出 + node-only rc=1）/ T6.2 壳 test result 三行（通道+完整命令行）/ T6.5 收尾）。
- **#8 _commit-plan.md**：文末追加 §6 R3 序列 + 覆盖表（§3-T6.3 规格）；§1 现状块不动（历史
  快照，勘误先例保留原文）；「再次声明未执行 git commit」收尾。
- **#9 implementation.md**：§3-T6.4 四处改动（5.13 总表 / §3 状态格 / §6 状态列 / 追加 §9），
  原文段落零删除。

## 5. 风险与回退（编号登记，执行员逐条知晓）

- **R1 修复后 sim 逐字 diff 非空**：即 abort 排查——修复只允许在 `flow_committee` node 路径内
  （`wait_for` docstring 明言仅 node 路径）；**绝不为凑一致修改基线件或 sim 代码**；若定位到
  意外波及（不应发生），回退 = 恢复 #2 备份前的 demo.py 区段（`git diff` 可逆）并升级仲裁。
- **R2 壳宿主通道执行时损坏**（规划期 2026-10-30 实跑通过 40/40，但以执行时点为准）：fallback
  容器通道，**零文件改动**：① `docker cp` verify_core → multi-tools:/tmp/tb-vc；② 因
  `#[path]` 为 Windows 绝对形（§1-5），Linux 下解析为相对路径，须在容器内**重建同名目录形**：
  `mkdir -p "/tmp/tb-vc/src/F:/canvus auto/downloads/202609CS5298/trustbridge/lyquid/src"` 与
  `"/tmp/tb-vc/tests/F:/canvus auto/downloads/202609CS5298/trustbridge/lyquid/tests"`，并把
  types/core/committee/assessor 四件与两测试件 docker cp 到对应位置；③ 宿主↔容器 md5 勾稽
  （10 件逐一 MATCH，`MSYS_NO_PATHCONV=1` 前缀）；④ `docker exec -w /tmp/tb-vc multi-tools
  cargo test --lib --tests` → 40/40。若该映射法仍失败 → **如实登记未能复跑并升级**（壳在
  仓库外，不得为跑通而修改壳的任何文件——#[path] 字符串属壳本体）。
- **R3 D-T3-1 修复无端到端重验**：如实登记（§2 诚实红线）；不得为「验证修复」擅自部署新实例
  或对既有实例发交易（任务授权面 = 无实跑部署；deal-1 已终态、重触发违反单次纪律）。
- **R4 三文档引用行号漂移/虚构**：撰写约束 = 只用本轮勘察实读行号；T6.5 抽查回验（每份 ≥5 处
  grep 证实被引行确含被引内容）；发现漂移即改文档不改证据。
- **R5 implementation 合并丢条目**：只追加不搬移；§9 记合并前后对账（偏离编号 grep 计数 +
  §6 行数）；任何需要改写原文的诉求 → 改为追加注记 + 指针，不删除。
- **R6 提交覆盖表遗漏**：以执行时 fresh `git status --porcelain` 生成，行数对账（§3-T6.3
  「覆盖表（硬性）」判据 + §6-G6-d）；本轮新增产物（#2/#4-#7）全部入表。
- **R7 对抗流 node 复跑**（全案 §7.5-2 排向 T6）不在本任务授权面（无链写实跑）：在
  implementation.md §6-#2 与 §9 如实登记为遗留（去向：后续阶段/用户安排），不静默丢弃、
  不假跑。
- **R8 回归日志写入方式**：禁 `{ … } >> $LOG 2>&1` 块内 `tee /dev/stderr`（D-T3-2 截断教训，
  已在 /tmp 复现）；统一直接重定向或分段追加。
- **R9 共享环境副作用**：本轮全程无链写、无 warp、无容器重启；devnet 只读使用（`docker ps`、
  壳测试、只读 grep）。若发现容器 Down：登记并升级，不自行重启。

## 6. 阶段收口门禁 G5+G6（全部实跑取证）

| 门 | 判据 |
|---|---|
| G5-a | 三文档在 `docs/b3-user-test/` 在档；操作手册命令序列与实录逐字一致（抽查回验 ≥5 处 `文件:行号`）；无虚构输出、无未来事件 |
| G5-b | 通过判据的 L2/L1/L0 口径与 `_plan-prev-r3-backup.md` §3.4 一致；L2 验收清单每条引 console 原文行（:24/:31/:32-35/:30/:36/:38） |
| G5-c | 反馈收集表四维齐备（任务理解/操作顺畅度/结果可信度/开放意见），无虚构示例反馈 |
| G6-a | `python scripts/demo.py --selftest` → SELFTEST OK；`--sim --flow all` 与 `_r2-t0-sim-baseline-raw.txt` **diff 无输出（IDENTICAL）**；`--sim --flow committee` rc=1 门控行为不变（#7 在档） |
| G6-b | 壳 `cargo test --lib --tests` → **33+5+2 = 40/40**（宿主或容器通道，完整命令行与 test result 三行入 #7；容器通道含 md5 勾稽 10/10） |
| G6-c | 冻结门复验：三文件 `git diff --stat` 空 + `md5sum -c _r2-t0-frozen-baseline.txt` 4×OK + `assessor.rs +5` 在场 + `committee_certified.rs` md5 `83e358ee…` 不变 + `E2_AVG_NUM=4` 不变 |
| G6-d | `_commit-plan.md` §6 覆盖表行数 = 执行时 `git status --porcelain` 行数，零未归属；R3 序列含 R3-C1..C6 + 不入库组；D-T3-1 修复收录为 R3-C3 |
| G6-e | implementation.md：5.13 总表 21+ 条可 grep；§3 G5/G6 状态格、§6 状态列已核销；§9 在档；合并前后条目对账记录在 §9；§0-§8 原文段落零删除 |
| G6-f | 未执行任何 git commit/add/push（`git log --oneline -1` 仍 `dc78d2f`）；devnet 零链写零重启；新增文件仅 §0 清单 + 表内登记件 |
