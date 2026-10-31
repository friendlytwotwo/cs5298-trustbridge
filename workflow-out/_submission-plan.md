# TrustBridge 提交清单与全量交叉复核（R4-D4）

> **方案出处**：`workflow-out/plan.md`（R4-D4，2026-10-30，规划期落盘；旧 R4-D2+D3 方案已原样备份于
> `workflow-out/_plan-prev-r4d2d3-backup.md`）。本文件为该方案 §0 清单 #3 的唯一交付产物。
> **生成日期**：2026-10-30。
> **基线 HEAD 存证**：`git log --oneline -1` → `8d093b5 R3 evidence: D-T3-1 fix E2E re-verification on
> fresh instance (T7)`（开工 T0 与收尾 T7 两次实跑，逐字一致；见 §5）。
> **纪律执行声明**：① **零 git 写**——全程只执行 `git log` / `git status` / `git diff` / `git ls-files` /
> `git show` / `git rev-list` / `git check-ignore` 只读命令，未执行任何 `add/commit/push/branch/tag/
> restore/stash`；② **只登记不修改**——复核发现的不一致一律登记于 §2.e，未改动任何 R0–R3/R4-D1/D2/D3
> 产物（唯一例外是本轮按工作流约定改写的 `workflow-out/implementation.md`，见 §2.e-E8 与
> `implementation.md` §5-D1）；③ **全部结论来自实跑**——§1 的入库状态取自 `git ls-files` /
> `git log --oneline -1 -- <file>` / `git status --short`，§2 的每一项均附命令与逐字输出，未跑项显式
> 标注「未跑」；④ **本任务不生成 ZIP**（§3.1 仅供人工执行）。

---

## §1 ZIP 内容清单

### 1.1 主交付三件（均在盘、均**未入库**）

| # | 文件（ZIP 内相对路径） | 内容 | 规模 | 指纹（本轮 `md5sum` 实跑） | 入库状态 |
|---|---|---|---|---|---|
| 1 | `workflow-out/report/trustbridge-final-report.pdf` | A4 中文期末报告，12 页（`PAGES=12`，§2.d） | 478,929 B / 12 页 | `18c90f03c89d622b1eece0024ff25385` | 未入库（`?? workflow-out/report/`） |
| 2 | `workflow-out/slides/trustbridge-final-slides.pptx` | 16:9（13.333×7.5 in）期末幻灯片，12 页，每页 speaker notes | 81,155 B / 12 页 | `a2495e35786d6c17a91341a61235af9b`（含 zip 时间戳，重建即变） | 未入库（`?? workflow-out/slides/`） |
| 3 | `workflow-out/demo-script.md` | 预录 demo 分镜脚本：8 镜（S0–S7），合计 305 s（5 分 05 秒） | 25,555 B / 285 行 | `cd78c6471b4bfe55e5d92b5a97b34bb7` | 未入库（`?? workflow-out/demo-script.md`） |

配套源文件 / 说明件（建议一并入 ZIP，人工可决定取舍）：

| 文件 | 作用 | 规模 | md5（实跑） | 入库状态 |
|---|---|---|---|---|
| `workflow-out/report/build_report.py` | 报告唯一源文件（reportlab Platypus，全文内嵌） | — | `8fed4b29c02a45aa190407e1d86d6753` | 未入库 |
| `workflow-out/report/README.md` | 报告构建 / 验证 / 证据索引 / 开工基线 | 195 行 | `d3c9470e1172e224256cf31484c11e12` | 未入库 |
| `workflow-out/slides/build_slides.py` | 幻灯片唯一源文件（python-pptx，尾段自检） | 1,013 行 | `25ccb29fdad6d5189c3edfcf7102fc59` | 未入库 |
| `workflow-out/slides/README.md` | 幻灯片构建 / 验证 / KEY_HITS 一致性核对表 | 245 行 | `3f742722007c03ccff7f38126ddb3b69` | 未入库 |
| `workflow-out/r3-t4-contrast-report.md` | EVM Escrow vs Lyquid 四维对照报告（P6 数据源） | 253 行 | `69541198fd91b4d13549a5769dc0606b` | 已入库（3af0460） |
| `workflow-out/implementation.md` | 实现说明（本轮改写为 R4-D4 版；R4-D2+D3 原版逐字保留于其附录 A） | — | 见 `implementation.md` §5-D1 | 未入库（` M`） |
| `workflow-out/_submission-plan.md` | 本文件 | — | — | 未入库（新建） |

> 指纹一致性：三件 md5 与各 README 记载值逐字一致（`report/README.md:10`、`slides/README.md:219`、
> `implementation.md`（D2+D3 版）§1-#4），无漂移。

### 1.2 已入库代码面（`git diff --name-status dc78d2f..HEAD`，实跑）

**提交序列（`git log --oneline dc78d2f..HEAD`，实跑 15 条，`git rev-list --count` = 15）**：

```
8d093b5 R3 evidence: D-T3-1 fix E2E re-verification on fresh instance (T7)
d292012 chore: archive earlier-round workflow-out artifacts
3af0460 R3 evidence: final docs + T1/T3/T4/T6 raw logs
826fa50 R3 docs: B3 user-test kit (manual / criteria / feedback form)
944a5a1 R3 experiments: EVM escrow contrast (Escrow.sol + foundry + runner)
d1e6f5f R3 fix: faucet read-back before snapshot (D-T3-1 behavior fix)
5634880 R3: committee flow orchestration + container channel helpers
c150d31 R3 route ②: certification callback wiring (committee_certified) + lib.rs hook
efc256c R2 evidence: keeper timeout loop, adversarial three-scenario, normal assess
785a944 R2: adversarial flow on-chain + on-chain assess in normal flow; remove sim-only gate
6f8f82a R2 route ①: flat eth wire for open_dispute / apply_committee_verdict
c31d701 R1 evidence: S3 assess + demo normal/timeout transcripts + raw logs
e43d8d2 R1 docs: SPIKE W1-4 removal + assessor status line
f36d24e R1 S4: role key table + nudge/discover/assess wrappers; demo/keeper node mode
acb7315 R1 S3: assess_brief 7->4 string + export=eth restored (Route A)
```

**已入库面逐文件（去重后 103 个文件 = 95 A + 8 M；`git diff --name-status dc78d2f..HEAD` 分组）**：

| 组（`_commit-plan.md` 对照） | 提交 | 状态 | 文件（逐文件） |
|---|---|---|---|
| C1（§2-C1） | acb7315 | M | `lyquid/src/lib.rs`、`lyquid/src/assessor.rs` |
| C2（§2-C2） | f36d24e | M | `agents/common/rpc.py`、`scripts/demo.py`、`scripts/keeper.py` |
| C3（§2-C3） | e43d8d2 | M | `README.md` |
| C4（§2-C4） | c31d701 | A（16） | `_r1-console-fund-raw.txt`、`_r1-console-raw.txt`、`_r1-demo-all-raw.txt`、`_r1-demo-normal-raw.txt`、`_r1-deploy-final-raw.txt`、`_r1-deploy-raw.txt`、`_r1-due-deals-raw.txt`、`_r1-final-state-raw.txt`、`_r1-g2-raw.txt`、`_r1-keeper-nudge-raw.txt`、`_r1-keeper-raw.txt`、`_r1-mock-selftest-raw.txt`、`_r1-rpc-smoke-raw.txt`、`w1b2-r1-demo-normal.md`、`w1b2-r1-demo-timeout.md`、`w1b2-r1-s3-assess.md`（均在 `workflow-out/` 下） |
| C5（§5-C5，R2） | 6f8f82a | M | `lyquid/src/lib.rs` |
| C6（§5-C6，R2） | 785a944 | M | `agents/common/rpc.py`、`scripts/demo.py` |
| C7（§5-C7，R2） | efc256c | A（18） | `_r2-adversarial-attempt1-raw.txt`、`_r2-adversarial-console-raw.txt`、`_r2-adversarial-raw.txt`、`_r2-assess-castcall-raw.txt`、`_r2-deploy-raw.txt`、`_r2-due-nonempty-raw.txt`、`_r2-final-state-raw.txt`、`_r2-g3a-sim-after-raw.txt`、`_r2-keeper-loop-raw.txt`、`_r2-node-all-raw.txt`、`_r2-normal-assess-raw.txt`、`_r2-t0-env-raw.txt`、`_r2-t0-frozen-baseline.txt`、`_r2-t0-sim-baseline-raw.txt`、`_r2-t7-regression-raw.txt`、`w1b2-r2-adversarial.md`、`w1b2-r2-keeper-timeout.md`、`w1b2-r2-normal-assess.md` |
| R3-C1（§6） | c150d31 | A+M | A `lyquid/src/committee_certified.rs`；M `lyquid/src/lib.rs` |
| R3-C2（§6） | 5634880 | M | `agents/common/rpc.py`、`scripts/demo.py` |
| R3-C3（§6） | d1e6f5f | M | `scripts/demo.py` |
| R3-C4（§6） | 944a5a1 | A（3） | `experiments/evm-contrast/Escrow.sol`、`experiments/evm-contrast/foundry.toml`、`experiments/evm-contrast/run-contrast.sh` |
| R3-C5（§6） | 826fa50 | A（3） | `docs/b3-user-test/反馈收集表.md`、`docs/b3-user-test/操作手册.md`、`docs/b3-user-test/通过判据.md` |
| R3-C6（§6） | 3af0460 | A（28）+M（2） | A：`workflow-out/_commit-plan.md`、`_r3-t1-node234-channel-raw.txt`、`_r3-t1-nodeinfo-raw.txt`、`_r3-t1-target-raw.txt`、`_r3-t1-th2-console.txt`、`_r3-t1-th2-raw.txt`、`_r3-t1-th4-console.txt`、`_r3-t1-th4-raw.txt`、`_r3-t3-committee-raw.txt`、`_r3-t3-console-raw.txt`、`_r3-t3-deploy-raw.txt`、`_r3-t3-final-state-raw.txt`、`_r3-t4-baseline-md5.txt`、`_r3-t4-build-raw.txt`、`_r3-t4-code-size-raw.txt`、`_r3-t4-evidence-recheck-raw.txt`、`_r3-t4-flows-raw.txt`、`_r3-t4-gas-raw.txt`、`_r3-t4-lyquid-scan-raw.txt`、`_r3-t4-md5-raw.txt`、`_r3-t4-precheck-raw.txt`、`_r3-t4-run1-superseded-flows-raw.txt`、`_r3-t4-run1-superseded-gas-raw.txt`、`_r3-t4-run2-superseded-flows-raw.txt`、`_r3-t4-run2-superseded-gas-raw.txt`、`_r3-t6-regression-raw.txt`、`r3-t4-contrast-report.md`、`w1b2-r3-e2-committee.md`；M：`workflow-out/implementation.md`、`workflow-out/plan.md` |
| 归档（§6「不入库 / 归档」） | d292012 | A（25） | `_collab/llm_call.py`、`_collab/plan_raw.md`、`_collab/planner_sys.txt`、`_collab/planner_user.txt`、`_collab/probe_bigmodel.txt`、`_collab/probe_deepseek.txt`、`_collab/probe_sys.txt`、`_collab/probe_user.txt`、`_collab/probe_user2.txt`、`_plan-prev-r1-backup.md`、`_plan-prev-r2-backup.md`、`_plan-prev-r3-backup.md`、`_plan-prev-r3t4-backup.md`、`_plan-prev-r3t5t6-backup.md`、`_plan-prev-w1b2-backup.md`、`_plan-prev-w1b2-closure-backup.md`、`_probe_cold_a0.md`、`_probe_gate_a0.md`、`_probe_impl_a0.md`、`_probe_plan_r1_a0.md`、`_probe_plan_r2_a0.md`、`_probe_plan_r3_a0.md`、`_w1b1-deploy-zz2jue.txt`、`_w1b1-r1-submodule-state-check.txt`、`_w1b1-setupdevnet-bootstrap.log` |
| T7 复验（方案 §1-2 的「8d093b5 = T7 复验」） | 8d093b5 | A（1）+M（4） | A `workflow-out/_r3-t7-dt31-verify-raw.txt`；M `docs/b3-user-test/操作手册.md`、`docs/b3-user-test/通过判据.md`、`workflow-out/implementation.md`、`workflow-out/w1b2-r3-e2-committee.md` |

**交付代码面（ZIP 应含的非 workflow-out 文件）**：`README.md`、`agents/common/rpc.py`、
`lyquid/src/{assessor,committee_certified,lib}.rs`、`scripts/{demo,keeper}.py`、
`experiments/evm-contrast/{Escrow.sol,foundry.toml,run-contrast.sh}`、
`docs/b3-user-test/{操作手册,通过判据,反馈收集表}.md` —— 共 13 个文件（**6 M + 7 A**，其中
`committee_certified.rs`、`experiments/` 三件、`docs/b3-user-test/` 三件为全新增）。

**`_commit-plan.md` 头部时点语义登记（不改原文）**：该文件 :1 标题与 :3 起始句写「**未执行任何
git commit**」，撰写基线为 `dc78d2f`（:3）；而 `git log --oneline dc78d2f..HEAD` 实跑为 **15 个提交**
（上文逐字）。二者不矛盾：前者是**撰写时点的语义快照**（当时确实零提交），后者是**入库后的实跑事实**；
按方案 §3-5「入库状态必须来自实跑 git」的口径，本清单的入库判定一律以 `git log` / `git ls-files` 为准。
同一文件 :26-:32 的「勘误」段（看护核销）与 :272-:274 的「移列声明」属既有登记，本次复核未发现与之冲突的项。

### 1.3 证据索引：w1b2-* 13 份（逐份一行）

> 说明列取自各文件头部（`head -4` 实跑）或 `report/README.md` §5 对应行；「对应原始日志」列为该文档
> 内实际引用的 `_r*` 档（实跑 `grep -ohE '_[A-Za-z0-9_-]*\.(txt|md)'` 提取，b3 已逐档 `test -f`）；
> 入库提交号为 `git log --oneline -1 -- workflow-out/<file>` 实跑值。

| # | 文件 | 说明（取自文件头部 / report §5） | 对应原始日志 | 规模 | 入库提交 |
|---|---|---|---|---|---|
| 1 | `w1b2-t0-baseline.txt` | W1-B2 T0 baseline（HEAD `1c0e45f`） | 自身即基线档（无外部引用） | 11 行 | dc78d2f |
| 2 | `w1b2-s4-rpc.md` | S4：RPC 信封探针 + `deal_info` 字面补验证据（2026-10-25，基线 `1c0e45f`） | `w1b1-s2-oracle.md`（同轮存档） | 162 行 | dc78d2f |
| 3 | `w1b2-claim-probe-evidence.txt` | T2–T4 证据：新实例部署 + `probe_claim_sim` 分阶段佐证（A~H） | 无 `_r*`（引用 `_w1b2_t3_replay.py` 与本组 md） | 218 行 | dc78d2f |
| 4 | `w1b2-claim-revert-finding.md` | R0 发现：`claim_timeout` 空 data revert（调试记录，已标 SUPERSEDED：根因 = D1 旧镜像） | 无 `_r*`（引用同组 md） | 37 行 | dc78d2f |
| 5 | `w1b2-refunded-evidence.md` | T6 证据：keeper v2 实测 `claim_timeout` 退款成功（Funded → Refunded；tx `0x85e4…0838`） | 无 `_r*`（引用 `_w1b2_t3_replay.py`、同组 md） | 110 行 | dc78d2f |
| 6 | `w1b2-shell-rebaseline.txt` | T0 壳修复与重定基线证据（verify_core 本地签名存根，40/40） | 无 `_r*`（引用同组 md） | 193 行 | dc78d2f |
| 7 | `w1b2-r1-s3-assess.md` | R1 · S3 证据：`assess_brief` 4×string 导出恢复 + 链上取证 | `_r1-g2-raw.txt`、`_r1-console-raw.txt`、`_r1-deploy-final-raw.txt`、`_r1-mock-selftest-raw.txt`、`_r1-rpc-smoke-raw.txt` | 188 行 | c31d701 |
| 8 | `w1b2-r1-demo-normal.md` | R1 · `demo.py --node` 正常流证据（G4 门；alice=9000 bob=980 broker=20） | `_r1-demo-normal-raw.txt`、`_r1-console-fund-raw.txt`、`_r1-final-state-raw.txt` | 89 行 | c31d701 |
| 9 | `w1b2-r1-demo-timeout.md` | R1 · `demo.py --node` 门控演示 + 超时流证据（G5 门） | `_r1-demo-all-raw.txt`、`_r1-due-deals-raw.txt`、`_r1-final-state-raw.txt`、`_r1-keeper-nudge-raw.txt`、`_r1-keeper-raw.txt` | 146 行 | c31d701 |
| 10 | `w1b2-r2-keeper-timeout.md` | R2 目标 A：keeper 循环驱动超时流 + `due_deals` 非空 | `_r2-keeper-loop-raw.txt`、`_r2-due-nonempty-raw.txt` | 112 行 | efc256c |
| 11 | `w1b2-r2-adversarial.md` | R2 目标 B：对抗流 devnet 全链（路线① 扁平 wire，三裁决场景） | `_r2-adversarial-raw.txt`、`_r2-adversarial-attempt1-raw.txt`、`_r2-adversarial-console-raw.txt`、`_r2-deploy-raw.txt`、`_r2-final-state-raw.txt`、`_r2-node-all-raw.txt` | 192 行 | efc256c |
| 12 | `w1b2-r2-normal-assess.md` | R2 目标 C：正常流一条龙（链上 assess 回放）+ `cast call` 直证 | `_r2-normal-assess-raw.txt`、`_r2-assess-castcall-raw.txt`、`_r2-adversarial-console-raw.txt` | 72 行 | efc256c |
| 13 | `w1b2-r3-e2-committee.md` | R3 目标 A：E2 四节点委员会（T1 平台探针梯子 + T3 演示实录 + T7 复验 §T7） | `_r3-t1-*`（7 件）、`_r3-t3-{committee,console,deploy,final-state}-raw.txt`、`_r3-t7-dt31-verify-raw.txt` | 181 行 | 8d093b5 |

**非证据件（单列说明，不计入 13 份）**：

- `workflow-out/_w1b2_t3_replay.py`（2,286 B）：W1-B2 的 T3 重放辅助脚本，已入库 `dc78d2f`，属工具而非证据文档。
- `workflow-out/_plan-prev-w1b2-backup.md`、`workflow-out/_plan-prev-w1b2-closure-backup.md`：W1-B2 两轮**方案备份**，已入库 `d292012`（归档提交），属方案留档而非证据。
- `workflow-out/w1b2-claim-probe-evidence.txt` / `w1b2-claim-revert-finding.md` 内的 SUPERSEDED 标注：历史结论已被 W1-B2 收尾闭环推翻（根因 = D1 旧镜像），按「原文快照不改」惯例保留，引用时须连带引用其 SUPERSEDED 声明。

### 1.4 其余证据 / 日志归组总表（组内计数为 `ls` 实跑，入库状态为 `git ls-files` 实跑）

| 组 | 计数 | 归属（`_commit-plan.md` 组号） | 已入库状态 | 备注 |
|---|---|---|---|---|
| `_r1-*` | 13 | C4（c31d701） | **全部入库**（tracked 13/13） | R1 原始日志（部署/正常流/超时流/keeper/selftest 等） |
| `_r2-*` | 15 | C7（efc256c） | **全部入库**（15/15） | R2 原始日志（deploy/keeper-loop/adversarial/normal-assess/t0 冻结基线等） |
| `_r3-*` | 26 | R3-C6（3af0460）+ T7（8d093b5） | **全部入库**（26/26） | T1 7 件 + T3 4 件 + T4 13 件 + T6 1 件 + T7 1 件 |
| `_r4d2d3-verify-raw.txt` | 1 | 无（R4-D2+D3 编排期新增） | **未入库**（`??`） | 686 行验证实录，R4-D2+D3 轮的逐条 grep 记录（§T7 `CHECKS_TOTAL=65 / FAILS=0`） |
| `w1a-*` | 8 | 早于基线的轮次存档 | **全部入库**（`a1721b7` 等，均早于 dc78d2f） | W1-A 探针/部署证据 |
| `w1b1-*` | 8 | 早于基线的轮次存档 | **全部入库**（`1c0e45f`） | W1-B1 拓扑/计时/oracle 证据 |
| `t0-*` | 2 | 早于基线的轮次存档 | **全部入库**（`f83ab52`） | T0 基线的 `cargo check` / `cargo test --no-run` 输出 |
| `_w1b1-*` | 3 | 归档（d292012） | **全部入库**（3/3） | W1-A/W1-B 轮存档 |
| `_commit-plan.md` / `r3-t4-contrast-report.md` / `w1b2-*`（13） | 15 | R3-C6 / C4 / C7 | 见 §1.2、§1.3 | 文档类，已逐份落表 |

> 逐份入库状态可用同一条命令复核：
> `git ls-files workflow-out/ | sed 's|^workflow-out/||' | grep -E '^(_r1|_r2|_r3|_w1b1|w1a|w1b1|t0)-' | wc -l` = **75**
> （13+15+26+3+8+8+2）；本轮实跑 `git ls-files workflow-out/` = **119** 条，且上述各组在盘（`ls`）与
> tracked 逐组相等 —— 即除 `_r4d2d3-verify-raw.txt` 外无未入库项。

### 1.5 在盘未入库清单（`git status --short` 实跑：T0 = 19 条，T7 = 20 条 = 19 + 本文件；逐条见 §5）

| 类别 | 条目 | 处置建议（指向 §3.2） |
|---|---|---|
| R4 交付产物（4 条） | `?? workflow-out/report/`、`?? workflow-out/slides/`、`?? workflow-out/demo-script.md`、`?? workflow-out/_r4d2d3-verify-raw.txt` | 建议入库（交付主件 + 验证实录） |
| 本轮新增（1 条，仅 T7 出现） | `?? workflow-out/_submission-plan.md`（本文件） | 建议入库或随交付包提交 |
| 改写件（2 条） | ` M workflow-out/implementation.md`（本轮 R4-D4 改写）、` M workflow-out/plan.md`（规划期覆盖为 R4-D4 方案） | 建议入库（最终态） |
| 评审探针被动更新（4 条） | ` M workflow-out/_probe_{cold,gate,impl,plan_r1}_a0.md` | 非本轮写入；按 `_commit-plan.md` §6「归档」惯例处置 |
| 轮次备份（6 条） | `?? workflow-out/_plan-prev-r4d1-backup.md`、`_plan-prev-r4d1-final-backup.md`、`_plan-prev-r4d2d3-backup.md`、`_implementation-prev-r1-backup.md`、`_implementation-prev-r2-backup.md`、`_implementation-prev-w1a-backup.md` | 建议不入库（沿 `_commit-plan.md` §6「不入库」惯例），或单列 `chore:` 归档 |
| 恢复凭据（3 条） | `?? workflow-out/_pre-task-snapshot-{r1,r2,r3}.patch` | 建议不入库（沿 R1-不入库 / C8 处置）；`_pre-task-snapshot.patch`（无后缀）已于 `dc78d2f` 入库，不在未入库面 |

> 精确行数：T0 `git status --porcelain | wc -l` = **19**（6 `M` + 13 `??`，其中 `report/`、`slides/` 各算
> 一行目录）；T7 = **20**（6 `M` + 14 `??`，+1 = 本文件）。上表 19 条为 T0 面，另单列「本轮新增」1 条即为 T7 面。

---

## §2 全量交叉复核（a/b/c/d 四项全部实跑）

### 2.a 三文档数字一致性：27 键 × 3 文档命中矩阵

**数字唯一事实源**：`workflow-out/report/README.md` §3(b) 的 KEY_HITS 27 项（命令逐字在 :71）。

#### (1) 报告：逐字复跑 `report/README.md:71` 命令

```bash
python -c "import pypdf; t=''.join(p.extract_text() or '' for p in pypdf.PdfReader('workflow-out/report/trustbridge-final-report.pdf').pages); keys=['0x85e4e39b628a358ef7cd61bfc8c87e67a730c76617a823a6001a87ea86ae0838','3,843,041','3,707,457','1,936,008','0x87006e75a5B6bE9D1bbF61AC8Cd84f05D9140589','0x942ED2fa862887Dc698682cc6a86355324F0f01e','0xFD6F7A6a5c21A3f503EBaE7a473639974379c351','0x3297eeb6','non-member signer','misconduct','inputs=4','signers=4','1000002','999002','77000','3920','81000','407','2083','1323','2933','2173','980','8d093b5','2026-10-30','无数据（原因）','第 5 节']; miss=[k for k in keys if k not in t]; print('KEY_HITS=%d/%d'%(len(keys)-len(miss),len(keys))); print('MISSING=%s'%miss)"
```

实跑输出（逐字）：

```
KEY_HITS=27/27
MISSING=[]
RC=0
```

#### (2) 幻灯片：python-pptx 全文本（正文 + 表格 + notes）逐键判定

提取口径：递归遍历 shapes（GROUP 递归进入；当前版无组形状，属前瞻）；`has_text_frame` 取
`text_frame.text`；`has_table` 的 GraphicFrame 逐行逐格取 `cell.text`（本轮实测 **P6、P8 各 1 张表**：
`P6_HAS_TABLE=True`、`P8_HAS_TABLE=True`）；`notes_slide.notes_text_frame.text` 非空页纳入。
脚本与命令见 §4-C2。实跑输出（摘要）：

```
SLIDES=12
BODY_LEN= [285, 508, 776, 698, 999, 693, 502, 873, 853, 442, 463, 470]
NOTES_EMPTY= []
KEY_HITS=25/27
MISSING=['0x85e4e39b628a358ef7cd61bfc8c87e67a730c76617a823a6001a87ea86ae0838', '第 5 节']
P6_HAS_TABLE= True
P8_HAS_TABLE= True
RC=0
```

**P6 分页映射复核（方案 T2 硬性要求）**：`3,707,457` / `407` / `2083` / `1323` / `2933` / `2173`
六键 = **全部命中且命中页 = P6**（逐键 `BODY pages=[6]`），与 `slides/README.md:169-182` 的
P6 映射一一对应 —— 提取器未漏表格，无「文档未命中」误判。

两处诚实未命中的形态原因（**均非冲突**）：

- `0x85e4e39b…0838`：P8 正文以**缩略展示形态** `0x85e4e39b…0838` 出现（`slides/README.md:178` 已登记），
  P8 notes 并写明「完整哈希见 `w1b2-refunded-evidence.md:14/:24`」；完整 66 字符串在幻灯片中不出现属设计选择。
- `第 5 节`：幻灯片全片无此字面（三文档侧重不同：报告给「§5 证据索引」，幻灯片给 P12 的路径指引）。

#### (3) demo 脚本：`demo-script.md` 全文逐键 `grep -cF`

命令：`grep -cF -- "<key>" workflow-out/demo-script.md` × 27（§4-C3）。实跑计数（按上表键序）：

```
1:0  2:2  3:1  4:2  5:3  6:2  7:3  8:0  9:2 10:2 11:1 12:1 13:0 14:0
15:0 16:0 17:0 18:1 19:1 20:1 21:1 22:1 23:6 24:6 25:2 26:0 27:1
```

即 **19 命中 / 8 未命中**（未命中 = #1 完整 tx hash、#8 `0x3297eeb6`、#13 `1000002`、#14 `999002`、
#15 `77000`、#16 `3920`、#17 `81000`、#26 `无数据（原因）`）。

#### (4) 27 × 3 命中矩阵（每格为 命中 / 未命中 / 冲突 三态之一）

| # | 键（KEY_HITS 序） | 报告（PDF） | 幻灯片（PPTX） | demo 脚本（MD） |
|---|---|---|---|---|
| 1 | `0x85e4e39b…0838`（完整 66 字符） | 命中 | **未命中**（P8 为 `0x85e4e39b…0838` 缩略形态） | 未命中 |
| 2 | `3,843,041` | 命中 | 命中（P6/P7；notes P10） | 命中（2 处） |
| 3 | `3,707,457` | 命中 | 命中（P6） | 命中（1 处） |
| 4 | `1,936,008` | 命中 | 命中（P6/P7；notes P10） | 命中（2 处） |
| 5 | `0x87006e75a5B6bE9D1bbF61AC8Cd84f05D9140589` | 命中 | 命中（P5） | 命中（3 处） |
| 6 | `0x942ED2fa862887Dc698682cc6a86355324F0f01e` | 命中 | 命中（P5） | 命中（2 处） |
| 7 | `0xFD6F7A6a5c21A3f503EBaE7a473639974379c351` | 命中 | 命中（P6 notes） | 命中（3 处） |
| 8 | `0x3297eeb6` | 命中 | 命中（P8） | 未命中 |
| 9 | `non-member signer` | 命中 | 命中（P6） | 命中（2 处） |
| 10 | `misconduct` | 命中 | 命中（P8/P9） | 命中（2 处） |
| 11 | `inputs=4` | 命中 | 命中（P4/P8） | 命中（1 处） |
| 12 | `signers=4` | 命中 | 命中（P4） | 命中（1 处） |
| 13 | `1000002` | 命中 | 命中（P8；notes P3） | 未命中 |
| 14 | `999002` | 命中 | 命中（P8；notes P3） | 未命中 |
| 15 | `77000` | 命中 | 命中（P8） | 未命中 |
| 16 | `3920` | 命中 | 命中（P8） | 未命中 |
| 17 | `81000` | 命中 | 命中（P8） | 未命中 |
| 18 | `407` | 命中 | 命中（P6） | 命中（1 处） |
| 19 | `2083` | 命中 | 命中（P6） | 命中（1 处） |
| 20 | `1323` | 命中 | 命中（P6） | 命中（1 处） |
| 21 | `2933` | 命中 | 命中（P6） | 命中（1 处） |
| 22 | `2173` | 命中 | 命中（P6） | 命中（1 处） |
| 23 | `980` | 命中 | 命中（P8） | 命中（6 处，均为 R1 分账语境） |
| 24 | `8d093b5` | 命中 | 命中（P1/P9；notes P3） | 命中（6 处） |
| 25 | `2026-10-30` | 命中 | 命中（12 页页脚 + 正文） | 命中（2 处） |
| 26 | `无数据（原因）` | 命中 | 命中（P6/P12） | 未命中 |
| 27 | `第 5 节` | 命中 | 未命中（全片无此字面） | 命中（1 处） |
| — | **合计** | **27 命中 / 0 未命中 / 0 冲突** | **25 命中 / 2 未命中 / 0 冲突** | **19 命中 / 8 未命中 / 0 冲突** |

**冲突判定与扫描（结论：0 冲突）**：按方案口径「同一数据点在文档中出现且值与 KEY_HITS 不同」才登记
冲突。扫描方法（§4-C4/C5）：对两份非事实源文档做**结构化抽取**——全部 42 字符地址、全部 8 位 hex
selector、全部 ≥4 位数字——再与 KEY_HITS 值域人工比对：

- 幻灯片：地址 3 个（`0x8700…` / `0x942E…` / `0xFD6F…`）**全部落在 KEY_HITS 内**；selector 3 个
  （`0x3297eeb6` = KEY_HITS 第 8 键、`0x85e4e39b` 为 tx hash 前缀、`0x942ED2fa` 为地址前缀）；
  额外大数字 11,308 / 30,266 / 5,378 / 47,908 / 226,658 / 32,713 / 36,014 为**对比报告的逐笔
  gas / 成本数**（`r3-t4-contrast-report.md`，slides P7/P10 引用），47000 / 48000 / 49000 为 **R2 余额
  序列**（`w1b2-r2-adversarial.md:77-:78、:89`），35996 为 **R0 回执 gasUsed**（`w1b2-refunded-evidence.md`），
  60000 为 **R1 heuristic 回放常量**（`w1b2-r1-s3-assess.md:83`），10087–13087 为**四节点端口**
  （`agents/common/rpc.py:91`）——均**不与任何 KEY_HITS 键同点异值**。
- demo 脚本：地址 8 个（含 devnet 账户 `0x3C44…`、`0x7099…`、keeper tx `0x4095…`、to-hex
  `0xc050…`、ANVIL0 私钥前缀），selector 2 个（keeper 的 `0xb540def8` / `0x786cfc8f`），均为 KEY_HITS
  之外的补充语境；`980` 的 6 处（`demo-script.md:23、:79、:80、:90、:95、:206`）**逐一核对均为 R1
  分账口径**，无一处与 R2/R3 语境混用。
- 数字口径铁律复核：R1 分账 9000/980/20（`demo-script.md:23`、`:79`、`:90`）、R2 结算 bob +980 /
  broker +20（幻灯片 P8 notes「R2 行只写 bob +980 / broker +20」）、R3 funding 中间态
  10000→9000→10000（`demo-script.md:127`、`:206`）三处口径分列、互不混用。

**未命中 ≠ 错误**（方案口径）：三文档侧重不同；未命中项**不构成冲突**，无需修正。若人工希望统一口径，
可选建议（非必需、**本任务未执行**）：① demo 脚本 S0/S7 口播各补一句「完整数字以 12 页报告与
`report/README.md` §5 为准」；② 幻灯片 P8 的缩略哈希保持现状（notes 已给指向）。两条建议均不改动任何数字。

### 2.b 证据索引齐套性（双向）

#### b1 索引 → 盘（`report/README.md` §5 出处列全部文件）

```bash
sed -n '109,136p' workflow-out/report/README.md | grep -oE '(workflow-out|docs)/[^ `|]+\.(md|txt|py|rs|sol)' | sed 's/[:：、].*$//' | sort -u
```

实跑：**10 个唯一文件**，逐个 `test -f` **10/10 OK**（逐字）：

```
OK   docs/b3-user-test/通过判据.md
OK   workflow-out/_r3-t3-console-raw.txt
OK   workflow-out/_r3-t7-dt31-verify-raw.txt
OK   workflow-out/implementation.md
OK   workflow-out/r3-t4-contrast-report.md
OK   workflow-out/w1b2-r1-demo-normal.md
OK   workflow-out/w1b2-r1-s3-assess.md
OK   workflow-out/w1b2-r2-adversarial.md
OK   workflow-out/w1b2-r3-e2-committee.md
OK   workflow-out/w1b2-refunded-evidence.md
```

#### b2 盘 → 索引（w1b2 范围，`comm -3` 双向零差异）

```bash
sed -n '/^### 1\.3 /,/^### 1\.4 /p' workflow-out/_submission-plan.md | grep -oE '`w1b2-[A-Za-z0-9_.-]+\.(md|txt)`' | tr -d '`\r' | sort -u > /tmp/idx.txt
ls workflow-out/w1b2-* | xargs -n1 basename | sort > /tmp/disk.txt
echo "IDX=$(wc -l < /tmp/idx.txt) DISK=$(wc -l < /tmp/disk.txt)"
comm -3 /tmp/disk.txt /tmp/idx.txt
echo "DIFF_LINES=$(comm -3 /tmp/disk.txt /tmp/idx.txt | wc -l)"
```

实跑输出（逐字）：

```
IDX=13 DISK=13
DIFF_LINES=0
```

（`comm -3` 本体**无输出** = 索引所指 13 份 100% 在盘、在盘 13 份 100% 被索引，**双向零差异**。
注：本机 `grep` = ugrep 7.8.4，其在 Windows 上输出 CRLF，故管道内必须 `tr -d '\r'`——不加则
`comm` 会因行尾 `\r` 把 13 份全部误报为差异（`DIFF_LINES=26`），该误报本轮已实测复现并修正。）

#### b3 w1b2 索引行「对应原始日志」列逐档 `test -f`

```bash
cat workflow-out/w1b2-*.md workflow-out/w1b2-*.txt | grep -ohE '_[A-Za-z0-9_-]*\.(txt|md)' | tr -d '\r' | sort -u
```

实跑：**34 个唯一 `_r*` 档**，逐个 `test -f` **34/34 OK**（逐字列表见 §4-C6；`tr -d '\r'` 必要——
w1b2 部分文档为 CRLF，不去 `\r` 会全部误判 MISS）。

### 2.c `demo-script.md` 可复制性抽查（15 条 = 命令级 9 + 输出级 6，命令级 ≥5 达标）

口径：命令级 = 对实录 `# command: ` 前缀后的命令串 `grep -nF`（占位符按 `demo-script.md` §3 规则；
`<addr>` 在 `_r2-*.txt` 中为**实录内字面占位符**，逐字 grep）；输出级 = 对预期输出行 `grep -nF`。
每条均同时 grep `demo-script.md`（证明脚本内确有该字面）与对应实录（证明字面可回抄）。

| # | 级别 | 镜号 / 内容 | 出处（预期行） | 实跑命令（`workflow-out/` 下） | 结果 |
|---|---|---|---|---|---|
| 1 | 命令级 | S2-① 清目录 | `_r3-t3-deploy-raw.txt:57` | `grep -nF -- 'docker exec multi-tools rm -rf /tmp/tb-lyquid' _r3-t3-deploy-raw.txt` | **命中** `57:`（demo :22） |
| 2 | 命令级 | S2-② 拷源码 | `:58` | `grep -nF -- 'MSYS_NO_PATHCONV=1 docker cp lyquid/. multi-tools:/tmp/tb-lyquid' _r3-t3-deploy-raw.txt` | **命中** `58:`（demo :22） |
| 3 | 命令级 | S2-③ cargo check 片段 | `:125` | `grep -nF -- 'docker exec -w /tmp/tb-lyquid multi-tools cargo check --target wasm32-unknown-unknown' _r3-t3-deploy-raw.txt` | **命中** `125:`（demo :22；该 `# command:` 行前段另有 `touch`，按片段命中并登记） |
| 4 | 命令级 | S2-④ deploy 参数序片段 | `:59` | `grep -nF -- '--endpoint ws://node1:10087/ws' _r3-t3-deploy-raw.txt` | **命中** `59:`（三行注释形态，按片段命中并登记；demo :22/:25/:227） |
| 5 | 命令级 | S2 备路径 to-hex 片段 | `:581` | `grep -nF -- 'docker exec multi-tools shaker to-hex' _r3-t3-deploy-raw.txt` | **命中** `581:`（demo :22/:73） |
| 6 | 命令级 | S3 正常流一条龙 | `_r2-normal-assess-raw.txt:3` | `grep -nF -- 'python scripts/demo.py --node http://127.0.0.1:10087 --contract <addr> --flow normal' _r2-normal-assess-raw.txt` | **命中** `3:`（demo :23/:82） |
| 7 | 命令级 | S4 keeper 讲解行 | `_r2-keeper-loop-raw.txt:3` | `grep -nF -- 'python scripts/keeper.py --node http://127.0.0.1:10087 --contract <addr> --deals deal-3 --interval 5' _r2-keeper-loop-raw.txt` | **命中** `3:`（demo :24） |
| 8 | 命令级 | S5-① T7 主命令 | `_r3-t7-dt31-verify-raw.txt:3` | `grep -nF -- 'python scripts/demo.py --node http://127.0.0.1:10087 --contract 0x942ED2fa862887Dc698682cc6a86355324F0f01e --instance Lyquid-dpp6ird6knahaun6dokpi6ki2pdnbjxdfunqa --flow committee' _r3-t7-dt31-verify-raw.txt` | **命中** `3:`（demo :25/:129） |
| 9 | 命令级 | S5-② console 命令 | `_r3-t3-console-raw.txt:2` | `grep -nF -- 'MSYS_NO_PATHCONV=1 timeout 60 docker exec multi-tools shaker console Lyquid-ybidj3krshf4gqcjk3m3px6mooi6tg74twwaa --endpoint ws://node1:10087/ws' _r3-t3-console-raw.txt` | **命中** `2:`（demo :25） |
| 10 | 输出级 | S1 devnet 自检 7 行 `Up` | `_r3-t4-precheck-raw.txt:5-:12` | `grep -nF -- 'multi-tools' _r3-t4-precheck-raw.txt` + `sed -n '5,12p'` | **命中** `6:`（另 `14:` 为命令回显）；`:5` 表头 + `:6` multi-tools、`:7` node1、`:8` node4、`:9` node2、`:10` node3、`:11` registry、`:12` anvil = 7 行齐（demo :21/:22/:25/:61/:68/:73） |
| 11 | 输出级 | S2 `[deploy exit=0]` | `_r3-t3-deploy-raw.txt:86` | `grep -nF -- '[deploy exit=0]' _r3-t3-deploy-raw.txt` | **命中** `86:`（demo :22/:71） |
| 12 | 输出级 | S3 结算分账 | `_r1-demo-normal-raw.txt:6` | `grep -nF -- 'final state=Settled balances: alice=9000 bob=980 broker=20' _r1-demo-normal-raw.txt` | **命中** `6:`（demo :23/:90） |
| 13 | 输出级 | S4 归因判定 | `_r2-keeper-loop-raw.txt:30` | `grep -nF -- 'ATTRIBUTION VERDICT: PASS' _r2-keeper-loop-raw.txt` | **命中** `30:`（demo :24/:114） |
| 14 | 输出级 | S5-① 退款勾稽 | `_r3-t7-dt31-verify-raw.txt:31` | `grep -nF -- 'refund check OK: alice 10000 -> 9000 (after fund) -> 10000' _r3-t7-dt31-verify-raw.txt` | **命中** `31:`（demo :136） |
| 15 | 输出级 | S5-② 四签证据 | `_r3-t3-console-raw.txt:31` | `grep -nF -- 'cert.signers RAW = [0, 1, 2, 3]' _r3-t3-console-raw.txt` | **命中** `31:`（demo :25/:157） |

**汇总：15/15 命中（命令级 9/9、输出级 6/6），0 未命中。** 命令级 ≥5 的判据达标（9 ≥ 5）。

**可选（不计入 ≥5）：S1 命令级出处**——命令源只认 HEAD：`git show 8d093b5:workflow-out/implementation.md`
的 `:443`、`:617` 实跑命中（下方输出）。**时点说明**：T4 执行时盘上 `implementation.md` 为 R4-D2+D3
208 行版，该字面仅出现在 `:153`（T9 记录行）与 `:190`（GT-d 脚注）两处**提及**，均非命令源；本轮改写后
盘上为 R4-D4 版（附录 A 保留原版），同名命令串只出现在 `:123`（§4「T4-可选」登记行）、`:423`
（附录 A · D2+D3 版 §4「T9 仲裁修订」行）、`:460`（附录 A · GT-d 脚注）三处——**仍全部是「提及」而非
命令源**。上述行号为 2026-10-31 终裁修订**最终态** `grep -n` 实跑定位（`grep -n 'docker ps --format'
workflow-out/implementation.md` → `123:` / `423:` / `460:`，共 3 处）；盘上文档再增删会使行号漂移，
届时一律以 `grep -n` 实跑定位为准，**不得按行号盲引**。故 S1 维持输出级（#10）口径。

```
443:- `docker ps --format "{{.Names}} {{.Status}}"` → 7 容器 Up（multi-tools / node1-4 / registry / anvil，13–14h）
617:| T6.0 | `docker ps --format "{{.Names}} {{.Status}}"` | 7 容器 Up（16h） |
rc=0
```

### 2.d 可打开性复验（逐字命令 + 逐字输出）

```bash
python -c "import pypdf; r=pypdf.PdfReader('workflow-out/report/trustbridge-final-report.pdf'); print('PAGES=%d'%len(r.pages))"
python -c "from pptx import Presentation; p=Presentation('workflow-out/slides/trustbridge-final-slides.pptx'); print('SLIDES=%d'%len(p.slides)); print('NOTES_EMPTY=%s'%[i for i,s in enumerate(p.slides,1) if not (s.has_notes_slide and s.notes_slide.notes_text_frame.text.strip())])"
```

实跑输出（逐字）：

```
PAGES=12
SLIDES=12
NOTES_EMPTY=[]
```

环境先探（T0 实跑）：`python -c "import pypdf,pptx; print(pypdf.__version__, pptx.__version__)"` →
`6.19.0 1.0.2`；`python --version` → `Python 3.14.5` —— 与 `report/README.md` §1 / `slides/README.md` §1 的先例一致。

### 2.e 不一致登记总表（**除 E8 外全部仅登记，未修改任何他阶段产物**；E8 是本轮按工作流约定对 `implementation.md` 的改写，已单列）

| 编号 | 位置 | 事实（实跑） | 与谁不一致 | 建议（以 KEY_HITS / git 实跑为准） | 处置状态 |
|---|---|---|---|---|---|
| E1 | `_commit-plan.md:1`、`:3` | 标题「未执行任何 git commit」，基线 `dc78d2f` | `git log dc78d2f..HEAD` = 15 提交（实跑） | 视为**撰写时点语义**；入库判定以 git 实跑为准（§1.2 已落表） | 仅登记，未修改 |
| E2 | HEAD 版 `implementation.md` §9.1 #4/#5 | 记 `操作手册.md` 477 行、`通过判据.md` 143 行 | 现盘 `wc -l` 实跑 = **481** / **144** 行（8d093b5 修改过两文件） | 以现盘为准；`_commit-plan.md` §6.1 与 `report/README.md` 未受影响 | 仅登记，未修改 |
| E3 | 幻灯片 P8 | 完整 tx hash 未出现（缩略形态 `0x85e4e39b…0838`） | KEY_HITS 第 1 键 | **未命中非冲突**（notes 已给完整哈希出处）；无需修正 | 仅登记，未修改 |
| E4 | `demo-script.md` | 8 键未命中（#1/#8/#13/#14/#15/#16/#17/#26） | KEY_HITS | **未命中非冲突**（demo 侧重命令与画面，非全量数字表）；可选口播补充句（§2.a 末） | 仅登记，未修改 |
| E5 | `report/README.md:133`（§5 局限行） | 裸指针 `workflow-out/implementation.md:28、:407、:511、:603`；另 PDF 封面引 `implementation.md:28-:31` | 该文件现盘为 R4-D4 版；指针仅对 **HEAD/R3 版（751 行）** 有效 | `report/README.md` 与 PDF 按方案只读冻结不回改；取回命令 `git show 8d093b5:workflow-out/implementation.md`。本轮已逐行实取核对：`:28` = devnet 行（`docker ps`：7 容器 Up）、`:407` = 真实 LLM 端到端局限行、`:511` = 对抗流 node 复跑「R3-T6 未执行」行、`:603` = §9.1 #6 反馈收集表「四维空白表单…无示例反馈」——四处均落在 HEAD 版实际行内。建议提交说明 / ZIP 附注引用本行 | 仅登记，未修改（本文件即附注） |
| E6 | `slides/README.md:3`、`demo-script.md:3` | 自称「方案：`workflow-out/plan.md`（R4-D2+D3…）」 | 现盘 `plan.md` 已为 R4-D4 版 | 对应备份 `_plan-prev-r4d2d3-backup.md` 在盘可查；无需修正 | 仅登记，未修改 |
| E7 | T0 `git status --short` | 实跑 **19 条**（6 M + 13 ??） | 方案 §1-3 预列 **18 条** | 差 1 条 = 规划期新建 `_plan-prev-r4d2d3-backup.md`（方案 §0-#2），正常；以 T0 实跑为基线（§5） | 仅登记，未修改 |
| E8 | `workflow-out/implementation.md` | 本轮按工作流约定改写为 R4-D4 版；**R4-D2+D3 原版（208 行，md5 `b421a1997fdfd160219a4789cf934278`）逐字保留于新文件附录 A** | 方案 §3-2「只写 §0 清单 3 个文件」 | 工作流协议要求实现说明写入 `implementation.md`；以「附录 A 逐字保留 + 不入库存档照旧」两全；`git status` 该文件本就在 T0 基线（` M`），不新增条目 | 已登记（`implementation.md` §5-D1） |

> 其余核对**全部一致**（不列入上表）：三件 md5 与 README 记载一致；`git ls-files workflow-out/` = 119，
> 与 §1.4 各组 tracked 计数逐组相等；`_pre-task-snapshot.patch` 已于 `dc78d2f` 入库故不出现在 `??` 面
> （`git log --oneline -1 -- workflow-out/_pre-task-snapshot.patch` = `dc78d2f`）。

---

## §3 人工待办清单

### 3.1 ZIP 打包命令（二选一；**本任务未执行**，仅供人工复制运行）

> 环境实测：PowerShell **5.1.26100.9711**；`Compress-Archive` / `Expand-Archive` / `Get-FileHash`
> 均可用（`Get-Command` 实跑）；PATH 上的 `tar` 为 GNU tar 1.35（`F:\Git\usr\bin\tar.exe`）；
> 无 `7z`、无 `zip`、无 `pwsh`（`command -v` 实跑均 rc=1）——故下列命令只用 PowerShell 5.1 + tar。
> **`tar` 的盘符路径坑（仲裁实测）**：GNU tar 1.35 的 `-f` 接**盘符绝对路径**须加 `--force-local`
> （否则报 `Cannot connect to C:`、rc=128）；`-C` 接盘符绝对路径**同样失败**（仲裁实测 rc=2）——故 3.1.2
> 解压一律 `Set-Location` 到目标目录后**相对解压、不用 `-C`**。
> **切勿整目录压缩 `lyquid/`**：该目录含 `lyquid/target`（构建产物，`du -sh lyquid` = **1.3G**，已 gitignore），
> 要用代码面请走 3.1.2 的 `git archive`（只含已入库文件）。

**3.1.1 最小交付包版（staging 法：三件 + 说明件 + B3 三件，不含代码面；PS 5.1 实测通过形态）**

```powershell
$root="F:\canvus auto\downloads\202609CS5298\trustbridge"
$stage=Join-Path $env:TEMP "tb-stage-311"
$zip="F:\canvus auto\downloads\202609CS5298\TrustBridge-CS5298_deliverables_2026-10-30.zip"
Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory (Join-Path $stage 'workflow-out\report') -Force|Out-Null
New-Item -ItemType Directory (Join-Path $stage 'workflow-out\slides') -Force|Out-Null
New-Item -ItemType Directory (Join-Path $stage 'docs') -Force|Out-Null
Set-Location $root
Copy-Item "workflow-out\report\*" (Join-Path $stage 'workflow-out\report')
Copy-Item "workflow-out\slides\*" (Join-Path $stage 'workflow-out\slides')
Copy-Item "workflow-out\demo-script.md","workflow-out\implementation.md","workflow-out\r3-t4-contrast-report.md","workflow-out\_submission-plan.md" (Join-Path $stage 'workflow-out')
Copy-Item "docs\b3-user-test" (Join-Path $stage 'docs') -Recurse -Force
Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $zip -Force
Get-FileHash $zip -Algorithm MD5
```

**预期 ZIP 内路径结构（仲裁 staging 法实测）**：

- `workflow-out\report\` **3 件**：`trustbridge-final-report.pdf`、`README.md`、`build_report.py`
- `workflow-out\slides\` **3 件**：`trustbridge-final-slides.pptx`、`README.md`、`build_slides.py`
- `workflow-out\` 下 **4 个单件**：`demo-script.md`、`implementation.md`、`r3-t4-contrast-report.md`、`_submission-plan.md`
- `docs\b3-user-test\` **3 件**：`操作手册.md`、`通过判据.md`、`反馈收集表.md`
- 两份 `README.md` **各归其目录**（`workflow-out\report\README.md` / `workflow-out\slides\README.md`），不再同名冲突。

> ⚠ **禁用形态**：PS 5.1 的 `Compress-Archive -Path` 收**显式文件路径清单**（如
> `@('workflow-out\report\README.md','workflow-out\slides\README.md', …)`）会**扁平化到 ZIP 根**、
> 并让**同名条目互相覆盖**（实测：两份 `README.md` 只剩一份）——故一律走 staging 目录 +
> `(Join-Path $stage '*')` 通配，不要直接传文件清单。
> **条目名分隔符坑**：PS 5.1 `Compress-Archive` 写入的 ZIP **条目名用反斜杠分隔**
> （`.NET ZipFile.Entries.FullName` 实读形如 `lyquid\Cargo.toml`；本轮 TEMP 小样本复测同形
> `a\f.txt`）；用**正斜杠通配**核对（如 `lyquid/*`）会**误报 0**——注④ 的「lyquid 误判」即源于此，
> 核对须用 `-like 'lyquid\*'`（或先统一把 `/` 归一成 `\` 再比）。

**3.1.2 代码面 + 交付件版（= 已入库代码面 `8d093b5` + 叠加 workflow-out 交付件）**

```powershell
$root  = "F:\canvus auto\downloads\202609CS5298\trustbridge"
$stage = Join-Path $env:TEMP "tb-submit-8d093b5"
$tar   = Join-Path $env:TEMP "tb-head-8d093b5.tar"
$zip   = "F:\canvus auto\downloads\202609CS5298\TrustBridge-CS5298_full_2026-10-30.zip"
Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $stage | Out-Null
Set-Location $root
git archive --format=tar -o $tar 8d093b5
Set-Location $stage
tar --force-local -xf $tar
Copy-Item "$root\workflow-out\report"  "$stage\workflow-out" -Recurse -Force
Copy-Item "$root\workflow-out\slides"  "$stage\workflow-out" -Recurse -Force
Copy-Item "$root\workflow-out\demo-script.md","$root\workflow-out\implementation.md","$root\workflow-out\r3-t4-contrast-report.md","$root\workflow-out\_submission-plan.md" "$stage\workflow-out" -Force
Remove-Item $zip -Force -ErrorAction SilentlyContinue
Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $zip -Force
Get-FileHash $zip -Algorithm MD5
```

说明：① `git archive 8d093b5` 导出**仅已入库文件**（无 `lyquid/target`、无未跟踪件），含
`workflow-out/` 全部 119 个 tracked 证据件与 `docs/b3-user-test/` 三件；② 随后 4 条 `Copy-Item`
用**盘上现版**覆盖/新增：`report/`、`slides/`、`demo-script.md`、`implementation.md`、
`r3-t4-contrast-report.md`、`_submission-plan.md`；③ 归档内 `workflow-out/plan.md` 为 HEAD（R3 轮）版 ——
如需交付当前 R4-D4 方案，加一行 `Copy-Item "$root\workflow-out\plan.md" "$stage\workflow-out" -Force`；
④ **仲裁端到端实测**：该形态产出的 ZIP 含 `report\` 3 件、`slides\` 3 件、`docs\b3-user-test\` 3 件，
`plan.md` 在档，**无 `lyquid/target`**（`lyquid` 已入库源码 **15 件**在档：`Cargo.toml`、`Cargo.lock`、
`build.rs`、`src\*.rs`、`tests\*.rs`，均 tracked、无未跟踪构建产物）、**无 `report\report` 嵌套**
（`git ls-tree 8d093b5 -- workflow-out/report workflow-out/slides` 本轮复跑为**空输出**，即两目录在
8d093b5 未 tracked；`workflow-out` tracked 仍 119 条；另以独立命令覆盖 lyquid：
`git ls-tree -r --name-only 8d093b5 | grep -c '^lyquid/'` = **15**，`git ls-tree 8d093b5` 中 lyquid 为
`040000 tree`（非 submodule））；
ZIP 的 md5 每次重建都变（zip 内时间戳），仲裁样例值 `3235AD36D9B5182A29CFDE1F54824091` 系 TEMP 产物；
仲裁复跑值 `540BEA48FE150B148505626D9962802B`（与前者不同，恰证「md5 每次重建都变」），仅供对照。

### 3.2 提交前检查单（**截止 11/19 12:00**）

| # | 事项 | 依据 / 命令 | 状态 |
|---|---|---|---|
| 1 | **R4 产物入库决策**：`report/`、`slides/`、`demo-script.md`、`_r4d2d3-verify-raw.txt`、`_submission-plan.md`、`implementation.md`（R4-D4 版）、`plan.md`（R4-D4 版）是否随本轮入库；备份/patch 6+3 条按「不入库/归档」处置 | 本文件 §1.5；`_commit-plan.md` §6「不入库 / 归档」惯例；`git status --short` | 待人工 |
| 2 | **§2.a 冲突项修正**：本轮 **0 冲突**；未命中 2（幻灯片）+ 8（demo）已判定非冲突，无需改数 | 本文件 §2.a；§2.e-E3/E4 | 已核验（无需动作） |
| 3 | **PDF/PPTX 终验**：重开复核页数与 notes、核对 md5 后登记 | 本文件 §2.d 两条命令；1.1 指纹表 | 本轮已跑（PAGES=12 / SLIDES=12 / NOTES_EMPTY=[]） |
| 4 | **demo 实拍完成**：按 `demo-script.md` 8 镜录制并计时（305s 设计值） | 本文件 §3.4 | 待人工 |
| 5 | **B3 反馈回收**：三份文档发组外用户，回收反馈表 | 本文件 §3.3 | 待人工（当前无已收集反馈） |
| 6 | **终裁记录复核签认**：五份位置逐份打开核对 | 本文件 §3.5 | 待人工 |
| 7 | **ZIP 打包 + md5 登记**：执行 §3.1 任一命令，记录 `Get-FileHash` 值 | 本文件 §3.1 | 待人工（本任务不生成 ZIP） |
| 8 | **git 入库动作**（add/commit/push/branch/tag）：一律由人工执行 | 方案冻结条款 1（本任务零 git 写） | 待人工 |

### 3.3 B3 线下测试安排

- **三份文件**（`docs/b3-user-test/`，已入库 `826fa50`，`wc -l` 本轮实跑）：`操作手册.md` **481 行**、
  `通过判据.md` **144 行**、`反馈收集表.md` **123 行**（合计 748 行）。
- **当前状态**：反馈收集表为**空白表单、无已收集反馈**（`git show HEAD:workflow-out/implementation.md`
  §9.1 #6 原文：「四维空白表单：…；无示例反馈」）；B3 组外测试**尚未开展**。
- **建议安排**：11/19 12:00 截止前留出 **≥3 天回收 + 整理窗口**（即最迟 11/15 发出、11/18 收齐）：
  ① 向 1–3 名组外同学发操作手册 + 通过判据 + 反馈表；② 让其按手册 §2–§5 在 devnet 上跑
  committee 流（单次纪律：不重复 `e2_arm` / `e2_run_verdict_round`，`demo-script.md` §6-1）；
  ③ 回收后按 `_commit-plan.md` 的「不入库/归档」惯例决定是否入库反馈件；④ 若无法安排，**如实登记
  「B3 未开展」**（报告 §4 局限表已含此项）。

### 3.4 demo 实拍提示

- **S3 当轮新实例**：S3 的预期输出只能静态命中 R1 档（`_r1-demo-normal-raw.txt:5/:6/:9`），
  **录制当轮必须以新部署实例实录为准**（`demo-script.md` §8-5、§3 `<addr>` 规则：`<addr>` = S2 当轮
  `Contract:` 地址，**禁填** `0xFD6F7A6a5c21A3f503EBaE7a473639974379c351`）。S1/S2 同理以当轮输出为准
  （实例名/地址每轮不同）。
- **占位符替换**：`<addr>` / `<实例名>` / `<新名>` / `<新地址>` / `<ANVIL0_KEY>` 逐条规则见
  `demo-script.md` §3；画面**不要**露出全钥（`agents/common/rpc.py:97`，`:90` 注明 devnet 公开确定性密钥）。
- **单次纪律**：绝不重复 `e2_arm` / `e2_run_verdict_round`（`demo-script.md` §6-1）；T3 档失败行
  （`RuntimeError …`、`# demo exit=1`）若展示必须同屏并注明「D-T3-1 修复前档案」。
- **`MSYS_NO_PATHCONV=1` 前缀必带**（`demo-script.md` §6-2，D-T6-1 教训）；console 的 `timeout 60` 到点
  `rc=124` = 正常收尾，字幕注明。
- **预案 A/B**：devnet 不可用 → 全镜头改「实录回放模式」（§5 预案 A）；单镜失败 → 按 §5 预案 B 处置
  （S4 无重录点，S2 可切备路径 to-hex）。
- **时长**：8 镜设计值合计 305s（240–360 判据内），实拍计时后若超 360s，优先压 S2/S6 静帧
  （`demo-script.md` §7 附 180s 剪辑点）。

### 3.5 终裁记录复核清单（五份位置索引，`grep -n '终裁'` 实跑定位）

| 轮次 | 文件（均在 `workflow-out/`） | 实跑命中行 | 内容要点 |
|---|---|---|---|
| R2 | `_plan-prev-r2-backup.md`（287 行） | **:279**（§10 终裁采纳项对照）、:281（表头「终裁项 / 本方案落点」）、:224（正文提及） | 编码员逐条落实、不得弱化 |
| R3 | `_plan-prev-r3-backup.md`（230 行） | **:9**（终裁定稿冻结条款，六条全 accept）、:25/:75/:76（条款正文内标注） | 后续轮次不得削弱；新增偏离须在 `implementation.md` §5 登记 |
| T4 | `_plan-prev-r3t4-backup.md`（177 行） | **:4、:14**（对 R3 备份的引用声明） | 本文引用 R3 内容时标「全案§x / 条款x」，原件在备份 |
| T5T6 | `_plan-prev-r3t5t6-backup.md`（121 行） | **:48、:73**（终裁维持性指令所在行） | 代码量三列并注 / T4.5 Lyquid 侧只读取数 |
| D1 | `_plan-prev-r4d1-final-backup.md`（231 行） | **:139-:144**（角色表：规划师/审查员/仲裁/终裁官/人工）、**:146-:148**（佐证材料段） | :148 明示仲裁修订登记段 `:347-:361、:663-:696` 与终裁条款引用 `:3-:4` |

**附：`implementation.md` HEAD 版仲裁修订登记段（只读取回核对，实跑）**

```bash
git show HEAD:workflow-out/implementation.md | sed -n '347,361p'
git show HEAD:workflow-out/implementation.md | sed -n '663,696p'
```

实跑核对结论：`:347-:361` = **§4 第 12 条「仲裁修订（2026-10-30 采纳，3 条；被驳回的意见未改）」**
（(a) `main()` fail-closed 门控；(b) 读回纪律加固 `wait_for`；(c) `flow_committee` 自行发 NodeID 制
`committee_config`）；`:663-:696` = **文档面仲裁修订三轮登记**（`docs/b3-user-test/操作手册.md` 的
§1.2 依赖/可达性、§2.1 `MSYS_NO_PATHCONV=1` 补正、§0/§2.5 的 TARGET 41→42 字符勘误），并给出引用回验计数
（第一轮 70 项、第二轮 73 项）。HEAD 版共 751 行（`wc -l` 实跑），与盘上 R4-D4 版为不同版本 —— 取回时
**必须**走 `git show 8d093b5:…`，不得对盘上版 grep。

---

## §4 命令附录（§2 全部命令逐字，供人工一键重跑）

工作目录：`F:\canvus auto\downloads\202609CS5298\trustbridge`（Git Bash；`grep` 实为 ugrep 7.8.4，
`-F` 固定串语义）。

**C1 报告 KEY_HITS（2.a-1）** —— 见 §2.a 正文第 (1) 段（完整一行 `python -c`）。

**C2 幻灯片 12 页全文本逐键判定（2.a-2）**

```bash
python - <<'PY'
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
prs=Presentation('workflow-out/slides/trustbridge-final-slides.pptx')
keys=['0x85e4e39b628a358ef7cd61bfc8c87e67a730c76617a823a6001a87ea86ae0838','3,843,041','3,707,457','1,936,008','0x87006e75a5B6bE9D1bbF61AC8Cd84f05D9140589','0x942ED2fa862887Dc698682cc6a86355324F0f01e','0xFD6F7A6a5c21A3f503EBaE7a473639974379c351','0x3297eeb6','non-member signer','misconduct','inputs=4','signers=4','1000002','999002','77000','3920','81000','407','2083','1323','2933','2173','980','8d093b5','2026-10-30','无数据（原因）','第 5 节']
def texts(sh):
    out=[]
    if sh.shape_type==MSO_SHAPE_TYPE.GROUP:
        for s in sh.shapes: out.extend(texts(s))
        return out
    if getattr(sh,'has_text_frame',False) and sh.has_text_frame: out.append(sh.text_frame.text)
    if getattr(sh,'has_table',False) and sh.has_table:
        for r in sh.table.rows:
            for c in r.cells: out.append(c.text)
    return out
body=[];notes=[]
for s in prs.slides:
    t=[]
    for sh in s.shapes: t.extend(texts(sh))
    body.append('\n'.join(t))
    notes.append(s.notes_slide.notes_text_frame.text if s.has_notes_slide else '')
print('SLIDES=%d'%len(prs.slides))
print('NOTES_EMPTY=',[i for i,n in enumerate(notes,1) if not n.strip()])
miss=[]
for k in keys:
    bp=[i+1 for i in range(len(body)) if k in body[i]]
    ap=[i+1 for i in range(len(body)) if k in (body[i]+'\n'+notes[i])]
    if not ap: miss.append(k)
    print('%2d %-45s BODY=%-12s ALL=%s'%(keys.index(k)+1,k[:44],bp,ap))
print('KEY_HITS=%d/%d'%(len(keys)-len(miss),len(keys)))
print('MISSING=%s'%miss)
print('P6_HAS_TABLE=',any(getattr(sh,'has_table',False) and sh.has_table for sh in prs.slides[5].shapes))
print('P8_HAS_TABLE=',any(getattr(sh,'has_table',False) and sh.has_table for sh in prs.slides[7].shapes))
PY
```

**C3 demo 脚本 27 键 `grep -cF`（2.a-3）**

```bash
cd workflow-out
for k in '0x85e4e39b628a358ef7cd61bfc8c87e67a730c76617a823a6001a87ea86ae0838' '3,843,041' '3,707,457' '1,936,008' '0x87006e75a5B6bE9D1bbF61AC8Cd84f05D9140589' '0x942ED2fa862887Dc698682cc6a86355324F0f01e' '0xFD6F7A6a5c21A3f503EBaE7a473639974379c351' '0x3297eeb6' 'non-member signer' 'misconduct' 'inputs=4' 'signers=4' '1000002' '999002' '77000' '3920' '81000' '407' '2083' '1323' '2933' '2173' '980' '8d093b5' '2026-10-30' '无数据（原因）' '第 5 节'; do printf "%s\t%s\n" "$(grep -cF -- "$k" demo-script.md)" "$k"; done
```

**C4 幻灯片结构化冲突扫描（2.a 冲突判定）**

```bash
python - <<'PY'
import re
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
prs=Presentation('workflow-out/slides/trustbridge-final-slides.pptx')
def texts(sh):
    out=[]
    if sh.shape_type==MSO_SHAPE_TYPE.GROUP:
        for s in sh.shapes: out.extend(texts(s))
        return out
    if getattr(sh,'has_text_frame',False) and sh.has_text_frame: out.append(sh.text_frame.text)
    if getattr(sh,'has_table',False) and sh.has_table:
        for r in sh.table.rows: out.append(' | '.join(c.text for c in r.cells))
    return out
pages=[]
for s in prs.slides:
    t=[]
    for sh in s.shapes: t.extend(texts(sh))
    if s.has_notes_slide: t.append(s.notes_slide.notes_text_frame.text)
    pages.append('\n'.join(t))
full='\n'.join(pages)
print('ADDRS=',sorted(set(re.findall(r'0x[0-9a-fA-F]{40}', full))))
print('SELECTORS=',sorted(set(re.findall(r'0x[0-9a-fA-F]{8}\b', full))))
print('BIG_NUMS=',sorted(set(re.findall(r'(?<![\d,])[\d][\d,]{4,}(?![\d,])', full))))
PY
```

**C5 demo 脚本结构化冲突扫描（2.a 冲突判定）**

```bash
python - <<'PY'
import re
full=open('workflow-out/demo-script.md',encoding='utf-8').read()
print('ADDRS=',sorted(set(re.findall(r'0x[0-9a-fA-F]{40}', full))))
print('SELECTORS=',sorted(set(re.findall(r'0x[0-9a-fA-F]{8}\b', full))))
print('NUMS=',sorted(set(re.findall(r'(?<![\d,])[\d][\d,]{3,}(?![\d,])', full))))
PY
```

**C6 b1 / b2 / b3** —— 见 §2.b 三段命令；b3 的逐档 `test -f`：

```bash
cd workflow-out
cat w1b2-*.md w1b2-*.txt | grep -ohE '_[A-Za-z0-9_-]*\.(txt|md)' | tr -d '\r' | sort -u > /tmp/b3_refs.txt
while IFS= read -r f; do if test -f "$f"; then echo "OK   $f"; else echo "MISS $f"; fi; done < /tmp/b3_refs.txt
```

**C7 15 条抽查（2.c）** —— 逐条命令见 §2.c 表格「实跑命令」列。

**C8 页数复验（2.d）** —— 见 §2.d 两条 `python -c`。

**C9 T1 入库面采集（§1.2/§1.4）**

```bash
git log --oneline -1
git status --short
git log --oneline dc78d2f..HEAD
git rev-list --count dc78d2f..HEAD
git diff --name-status dc78d2f..HEAD
git ls-files workflow-out/ | wc -l
git ls-files workflow-out/ | grep w1b2
for f in $(git ls-files workflow-out/ | grep w1b2); do printf "%s\t%s\n" "$(git log --oneline -1 -- "$f" | cut -c1-7)" "$f"; done
for c in acb7315 f36d24e e43d8d2 c31d701 6f8f82a 785a944 efc256c c150d31 5634880 d1e6f5f 944a5a1 826fa50 3af0460 d292012 8d093b5; do echo "### $c"; git show --stat --name-status --format="" $c; done
```

**C10 终裁记录定位（§3.5）**

```bash
cd workflow-out
for f in _plan-prev-r2-backup.md _plan-prev-r3-backup.md _plan-prev-r3t4-backup.md _plan-prev-r3t5t6-backup.md _plan-prev-r4d1-final-backup.md; do echo "=== $f"; grep -n '终裁' "$f"; done
cd ..
git show HEAD:workflow-out/implementation.md | sed -n '347,361p'
git show HEAD:workflow-out/implementation.md | sed -n '663,696p'
git show 8d093b5:workflow-out/implementation.md | grep -nF 'docker ps --format "{{.Names}} {{.Status}}"'
```

---

## §5 红线自查

**1. 零 git 写（前后存证对比）**

T0（开工第一动作）实跑：

```
$ git log --oneline -1
8d093b5 R3 evidence: D-T3-1 fix E2E re-verification on fresh instance (T7)

$ git status --short
 M workflow-out/_probe_cold_a0.md
 M workflow-out/_probe_gate_a0.md
 M workflow-out/_probe_impl_a0.md
 M workflow-out/_probe_plan_r1_a0.md
 M workflow-out/implementation.md
 M workflow-out/plan.md
?? workflow-out/_implementation-prev-r1-backup.md
?? workflow-out/_implementation-prev-r2-backup.md
?? workflow-out/_implementation-prev-w1a-backup.md
?? workflow-out/_plan-prev-r4d1-backup.md
?? workflow-out/_plan-prev-r4d1-final-backup.md
?? workflow-out/_plan-prev-r4d2d3-backup.md
?? workflow-out/_pre-task-snapshot-r1.patch
?? workflow-out/_pre-task-snapshot-r2.patch
?? workflow-out/_pre-task-snapshot-r3.patch
?? workflow-out/_r4d2d3-verify-raw.txt
?? workflow-out/demo-script.md
?? workflow-out/report/
?? workflow-out/slides/

$ git status --porcelain | wc -l
19
```

T7（收尾）实跑：

```
$ git log --oneline -1
8d093b5 R3 evidence: D-T3-1 fix E2E re-verification on fresh instance (T7)

$ git status --short
 M workflow-out/_probe_cold_a0.md
 M workflow-out/_probe_gate_a0.md
 M workflow-out/_probe_impl_a0.md
 M workflow-out/_probe_plan_r1_a0.md
 M workflow-out/implementation.md
 M workflow-out/plan.md
?? workflow-out/_implementation-prev-r1-backup.md
?? workflow-out/_implementation-prev-r2-backup.md
?? workflow-out/_implementation-prev-w1a-backup.md
?? workflow-out/_plan-prev-r4d1-backup.md
?? workflow-out/_plan-prev-r4d1-final-backup.md
?? workflow-out/_plan-prev-r4d2d3-backup.md
?? workflow-out/_pre-task-snapshot-r1.patch
?? workflow-out/_pre-task-snapshot-r2.patch
?? workflow-out/_pre-task-snapshot-r3.patch
?? workflow-out/_r4d2d3-verify-raw.txt
?? workflow-out/_submission-plan.md
?? workflow-out/demo-script.md
?? workflow-out/report/
?? workflow-out/slides/

$ git status --porcelain | wc -l
20

$ git diff --name-only -- lyquid scripts agents experiments docs README.md
（空输出）

$ git log --oneline -1
8d093b5 R3 evidence: D-T3-1 fix E2E re-verification on fresh instance (T7)
```

**与 T0 基线逐条比对**：① 6 条 `M` 与 **13 条** T0 已有 `??` **逐字相同**（其中 `implementation.md`
内容被本轮改写，状态行不变，见 §2.e-E8）；② **唯一新增** = `?? workflow-out/_submission-plan.md`
（本文件）→ `20 = 19 + 1`；③ HEAD 逐字仍为 `8d093b5`；④ 代码面 `git diff --name-only -- lyquid
scripts agents experiments docs README.md` **空输出**（零改动）；⑤ 全程零 `git add/commit/push`。

全程未执行任何 `git add` / `commit` / `push` / `branch` / `tag` / `restore` / `stash`；
所有 git 命令均为只读（`log` / `status` / `diff` / `ls-files` / `show` / `rev-list` / `check-ignore`）。

**2. 新增 / 覆盖文件清单（相对 T0 基线）**

| 文件 | 动作 | 说明 |
|---|---|---|
| `workflow-out/_submission-plan.md` | **新建** | 本任务唯一交付产物（本文件） |
| `workflow-out/implementation.md` | 改写（原为 ` M` 状态） | 工作流约定要求实现说明写入该路径；**R4-D2+D3 原版 208 行逐字保留于其附录 A**（md5 `b421a1997fdfd160219a4789cf934278` 为改写前实跑值），见 §2.e-E8 |
| `workflow-out/plan.md` | 规划期覆盖（非本轮） | R4-D4 方案本身；旧版在 `_plan-prev-r4d2d3-backup.md` |
| `workflow-out/_plan-prev-r4d2d3-backup.md` | 规划期新建（非本轮） | 方案 §0-#2 备份件 |

**3. 未修改他阶段产物声明**：除上表 `implementation.md`（工作流约定）外，未写入任何
R0–R3 / R4-D1/D2/D3 产物 —— `report/README.md`、`slides/**`、`demo-script.md`、
`r3-t4-contrast-report.md`、全部 `_r*` / `w1b2-*` / 备份件 / 探针件、`docs/b3-user-test/` 三件、
`lyquid/`、`scripts/`、`docs/`、`experiments/`、`agents/` **零写入**（T7 `git status` 与 T0 逐条比对可证：
状态行集合只**新增本文件** `?? workflow-out/_submission-plan.md`，其余 19 条逐字相同；代码面
`git diff --name-only -- lyquid scripts agents experiments docs README.md` 空输出）。

**4. 未能执行的检查及原因**

| 检查 | 状态 | 原因 |
|---|---|---|
| ZIP 打包（§3.1 两条命令） | **未跑** | 方案 §3-6 冻结条款：本任务不生成 ZIP，命令仅供人工执行 |
| devnet / `docker` / `scripts/demo.py` / `keeper.py` / `shaker deploy` / `cargo` | **未跑** | 本任务为纯文档收尾，不产生新链上证据；预期输出一律引用既有档案（§2.c 均命中） |
| demo 实拍与计时 | **未跑** | 需人工录制（§3.4）；305s 为设计值 |
| B3 组外测试与反馈回收 | **未跑** | 需组外用户（§3.3）；反馈表当前为空白表单 |
| 幻灯片目视复核 / PDF 目视复核 | **未跑（本轮）** | 本轮只做页数与 notes 复验（§2.d）；目视结论沿用 D2/D3 轮记录（`slides/README.md` §3-(e)、`report/README.md` §3-(d)） |

**5. 复现性**：本文件 §2 的每一条结论都可由 §4 附录命令逐字重跑；§1 的每个入库状态都可由 §4-C9
的 git 命令重新取数。
