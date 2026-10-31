# R5 实现说明（编码员，2026-10-31）

> 方案：`workflow-out/plan.md`（R5 审查+择优修复轮，规划期 HEAD
> `093dd06aafbcfa5236f665dee9745df7836066fd`，编码开工前实跑
> `git rev-parse HEAD` 复核一致；下文「§x」均指该方案文件）。
> 本轮性质：**代码改动 + 只读门禁**；零链写零部署零重启（红线⑥/G6），
> 零 git 写（红线④，不 commit，沿轮次惯例留人工）。
> 改写注记：本文件为 R5 覆盖写（方案 §0-#7）；上一版 R4-D4 实现说明已于
> 规划期备份至 `_implementation-prev-r4-backup.md`（两侧 md5
> `079fc6cbd238142ee72945b151896884` 逐字一致，编码期覆写前实跑复核）。

改动面恰为方案 §0 清单 #1–#3（lib.rs / demo.py / keeper.py）+ workflow-out
文档件。

## 0. S1 快照与回退件（已落盘）

| 件 | 实录 |
|---|---|
| `workflow-out/_pre-task-snapshot-r5.patch` | `git diff -- lyquid/src scripts agents >` 输出 **0 字节**（预期空 diff，改动前无未落库代码） |
| `workflow-out/_r5-orig-lib.rs` | `cp` 原件，md5 `382576388eee813ac427806847641a09`（与容器 `/tmp/tb-lyquid/src/lib.rs` md5 一致，实证容器副本=改动前源） |
| `workflow-out/_r5-orig-demo.py` / `_r5-orig-keeper.py` | `cp` 原件 |
| 回退方式 | `cp workflow-out/_r5-orig-<名> <原路径>`，零 git 写 |

## 1. 已修复项与逐文件改动摘要

### A. `lyquid/src/lib.rs`（P1-1 + P1-2 + 顺带 P2-2 一处）

- **A1（P1-1）`committee_config` 阈值 fail-closed**：`require(Access::Broker)?`
  及其 TODO 注释之后、`committee_members.clear()` 之前插入
  `if threshold == 0 { return Err(lyquid_error("committee threshold must be > 0")); }`
  （附 4 行 R5 注记，指明镜像 e2 域 committee_certified.rs:119-123 与
  core.rs:245-247 计数门失效机理）。措辞对齐既有平台层校验
  `"amount must be > 0"`（lib.rs:320）风格。方法签名/ABI/console 零变化。
  误伤核查（实跑 grep）：全库 `committee_config` 调用点仅 demo.py:595
  （E2_THRESHOLD=4）、demo.py:777（THRESHOLD=3）、broker.py:59（默认
  threshold=3，实读 broker.py:55-59）——**无一传 0**，已归档证据流零影响。
- **A2（P1-2）`credit` 溢出防御**：签名改 `-> LyquidResult<()>`，裸
  `bal + amount` 改 `bal.checked_add(amount).ok_or_else(|| lyquid_error("balance overflow"))?`
  后写回 `new`（附 5 行 R5 注记：wasm release 无溢出检查、escrow 路径不可达、
  可达面仅 faucet 级荒谬输入）。调用点加 `?` 共 5 处：`faucet`（原 :288）+
  `apply_payout` 内 4 处（原 :715/:718/:721/:724；apply_payout 本就返回
  LyquidResult，方案 :712 实读属实）。改动前实跑
  `grep -rn "credit(" lyquid/src lyquid/tests`：恰 5 个调用点 + 定义 1 处，
  无隐藏调用面。
- **A3（顺带 P2-2）** lib.rs:400 注释 `committee.rs:58` → `committee.rs:66-74`
  （实跑 `grep -n check_evidence_shape committee.rs`：函数签名 :66，
  函数体至 :74，与方案引用一致）。

### B. `scripts/demo.py`（P1-3 + 顺带 P2-1/P2-2）

- **B1a（P1-3 timeout 流 node 分支）**：`after = read_back(...)`（原 :358）
  之后、print 之前插入终态断言（附 3 行 R5 注记）：
  `if after.get("state") != "Refunded": raise RuntimeError(...timeout claim did not reach Refunded...claim likely swallowed on-chain; inspect keeper/console)`。
  位于 `if node_mode(node):` 块内 → sim 字面零变化（G3 实证）。
- **B1b（P1-3 normal 流）**：`final = read_back(node, deal_id)`（原 :318）
  之后、print 之前插入
  `if node_mode(node) and final.get("state") != "Settled": raise RuntimeError(...complete did not reach Settled...(rpc.py status-0x1 caveat))`。
  node_mode 守卫 + 断言零打印 → sim 字面零变化（G3 实证；sim 侧
  FakeNode.complete 状态不符本就 raise，rpc.py:859-866，双保险）。
- **B2（顺带 P2-1）** import 行删死 import `SLOT_MS`（grep 实证 demo.py 全文
  仅 import 行出现，无第二处引用）。
- **B3（顺带 P2-2）** 3 处注释行号改指实际位置：`keeper.py:56-58`→`:69-70`、
  `keeper.py:60-68`→`:73-81`、`core.rs:203-210`→`:202-209`（均实读核对：
  keeper.py READ_BACK 常量在 :69-70、`_read_back` :73-81；core.rs 裁决映射
  match 块 :202-209）。

### C. `scripts/keeper.py`（P1-4 + 顺带 P2-2）

- **C1（P1-4）**：`args = p.parse_args()` 后加
  `if args.interval <= 0: p.error("--interval must be >= 1 (0/negative would busy-loop or crash)")`
  （置于 `NodeClient` 构造**之前**，拒绝零网络）；`--deals` 分支解析后
  `if not deals: p.error("--deals parsed to an empty list; nothing to watch")`。
  **离线探针实证**（`--contract 0xabc`；`NodeClient.__init__` 实读确认仅存
  base_url/contract，无网络 I/O）：
  - `--interval 0` → argparse error，rc=2；
  - `--interval -3` → 同上，rc=2；
  - `--deals ","` → "empty list" error，rc=2。
  三者均零主循环日志、零请求发出。
- **C2（顺带 P2-2）** 模块 docstring 与注释 3 个行号引用改指实际位置：
  `rpc.py:330-337`→`:578-584`、`rpc.py:241-262`→`:464-485`、
  `rpc.py:301-311`→`:549-559`（实跑 grep：`_send` :464、`_poll_deal` :549、
  `claim_timeout` wrapper :578）。

## 2. 门禁实录（G1–G6 全部只读，编码期实跑）

| 门 | 命令（实跑） | 结果 |
|---|---|---|
| G1 | `python -m py_compile scripts/demo.py scripts/keeper.py` | `PY_COMPILE-ALL-OK` |
| G2 | `python scripts/demo.py --selftest` | 7 项全 PASS + `SELFTEST OK` |
| G3 | `python scripts/demo.py --sim --flow all > /tmp/r5-g3-sim-after.txt 2>&1` 后 `diff -u workflow-out/_r2-t0-sim-baseline-raw.txt /tmp/r5-g3-sim-after.txt` | **`BASELINE-DIFF-IDENTICAL`**（diff 零输出，rc=0；两侧 md5 同为 `a7cd1bdcd09fb44bff2002cb49e8694c`）——sim 基线逐字保持，硬门通过 |
| G4 | `docker cp lyquid/src/lib.rs multi-tools:/tmp/tb-lyquid/src/lib.rs` + `MSYS_NO_PATHCONV=1 docker exec -w /tmp/tb-lyquid multi-tools sh -c "touch src/lib.rs && cargo check --target wasm32-unknown-unknown"` | `Finished \`dev\` profile ... in 4.50s`；`trustbridge (lib) generated 33 warnings`（与规划期基线 33 条持平，**无新增**）。**重编注记**：lib.rs 有改动 → cp+touch 后 lib 重编（方案 §1-5 预告义务已履行；cp 前实跑 md5 证明容器副本=改动前原件）。同步注记：`/tmp/tb-lyquid` 非 bind mount，同步约定即 docker cp（容器副本 md5 与本地原件一致证实） |
| G5 | `git diff --stat` | 代码改动恰 `lyquid/src/lib.rs`（28 行）/`scripts/demo.py`（23 行）/`scripts/keeper.py`（13 行）；**types.rs / core.rs 零出现**（红线①，模型检查复跑义务不触发） |
| G6 | 全程未跑任何 `--node` 流、未 deploy、未重启容器 | 零链写零部署零重启 ✓（本轮链侧接触仅 docker cp 源码 + cargo check 编译，非链操作） |

## 3. 未修复项处置（引用方案 §2 编号，未新增未漏项）

- **P0**：0 项（方案 §2.1 诚实结论，编码期复核未发现新 P0）。
- **P1-R1**（rpc.py `_rpc` 非 JSON 响应裸抛）、**P1-R2**（broker/llm live 模式
  畸形响应裸 traceback）、**P1-R3**（timeout.rs `watcher_step` 单笔失败整轮
  中断）：登记不修，理由同方案 §2.2/§5——控制改动面 / 仅真实后端 live 路径 /
  已交付触发路径有 keeper.py 覆盖且改动须重编 wasm 收益边际。
  **rpc.py / protocol.py / broker.py / alice.py / timeout.rs / committee.rs /
  committee_certified.rs 本轮零打开零改动**（G5 实证）。
- **P2-1**：仅清 demo.py `SLOT_MS`（因 P1-3 已打开的文件）；rpc.py `field`、
  alice.py `Acceptance`/`Deliverable` 登记（文件未打开）。
- **P2-2**：修方案指定 6 处（lib.rs 1 + demo.py 3 + keeper.py 3 引用/2 处编辑），
  其余 4 处（rpc.py:426/:500/:895+911-915、protocol.py:19）登记不修（文件未
  打开）。已修 6 处全部实读核对后落笔。
- **P2-3/4/5/6/7/8/9/10/11**：全部只登记，处置理由见方案 §2.3（P2-4 受红线②
  禁止；P2-3 删除须重编 wasm 零行为收益；余类推）。
- **P2-12（文档漂移）编码期实查结果**：
  - `workflow-out/demo-script.md:36` 锚点 `scripts/demo.py:346-:357` → 改后
    实际 `:353-:364`（B1b 插入 +7 行所致；nudge while 循环现于 :353、
    claim 调用现于 :364，grep 实证）。**登记不改正**（红线⑤）。
  - `docs/演示与运行指南.md`：grep 全文 **零行号锚点** → 无漂移可登记。
  - 两文件均零改写。

## 4. 红线合规自检

| 红线 | 实证 |
|---|---|
| ① types.rs/core.rs 零触碰 | G5 diff --stat 两文件零出现；壳 crate 模型检查复跑义务不触发 |
| ② lyquid 判级行为三面 | console 打印面（faucet `log!`、fund deal_view `println`、apply_verdict `println`）逐行未动（diff 中无任何 log!/println 行变化）；E2_AVG_NUM 所在 committee_certified.rs 未打开；两个 network 方法签名逐字不变，`credit` 为 crate 内私有 helper 非 ABI 面；归档证据流阈值恒 3/4（§1-A1 误伤核查） |
| ③ 只读清单零写入 | docs/b3-user-test/、workflow-out/report/、slides/、_submission-plan.md 未触碰（G7 status 无出现） |
| ④ 零 git 写 | 全程仅 `git diff`/`git status`/`git rev-parse` 只读命令；无 add/commit/push/branch/tag/restore/stash |
| ⑤ 行号漂移文档只登记 | §3 P2-12：漂移已登记，两文档零改写 |

## 5. S7 终核与交付面

编码期结束时实跑 `git status --short`：改动 = 三个代码文件 + workflow-out
文档件（`plan.md`/`_probe_cold_a0.md`/`_probe_gate_a0.md` 为开工前规划师已
落盘改动，S0 登记在案；本编码期新增/覆盖的 workflow-out 件 =
`_pre-task-snapshot-r5.patch`、`_r5-orig-{lib.rs,demo.py,keeper.py}`、本
文件）。未 commit（红线④）。

**交付面**：`lyquid/src/lib.rs`、`scripts/demo.py`、`scripts/keeper.py`
（代码三件）+ `workflow-out/implementation.md`（本文件）+ §0 快照件。
