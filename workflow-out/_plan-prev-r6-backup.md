# R5 方案：代码健康与健壮性审查轮（规划师，2026-10-31）

仓库定格 `HEAD=093dd06aafbcfa5236f665dee9745df7836066fd`（规划期实跑
`git rev-parse HEAD` 确认，全部已入库）。R5 = **审查 + 择优修复轮**：
两级目标 ① 健康性（死代码 / 重复逻辑 / 注释-实现漂移 / 错误处理风格）② 健壮性
（边界与极值输入 / 异常与资源路径 / 网络读回时序 / fail-closed 门控完整性 /
重入与重复结算 / Python 编码与序列化边界）。

**铁律**：devnet 零链写零部署零重启（本轮全部验证只读：sim / selftest /
py_compile / 容器 cargo check）；零 git 写（不 commit/add/push/branch/tag/
restore/stash）；types.rs/core.rs 语义零触碰（见 §6 红线表 → 不触发壳 crate
模型检查复跑义务）；lyquid 判级行为三面（console 打印面、E2_AVG_NUM=4、方法
签名 ABI）零变化。

## 0. 受影响文件清单（8 项，供审查员核对；#1–#3 是全部代码改动面）

| # | 路径 | 动作 | 说明 |
|---|---|---|---|
| 1 | `lyquid/src/lib.rs` | 修改 | P1-1（committee_config 阈值 fail-closed）+ P1-2（credit 溢出防御）+ 1 处注释行号顺带修正；**不触 types.rs/core.rs** |
| 2 | `scripts/demo.py` | 修改 | P1-3（timeout 流 node 分支终态断言 + 扩展覆盖 flow_normal 终态断言）+ 死 import 清理 + 3 处注释行号顺带修正；**sim 路径零改动** |
| 3 | `scripts/keeper.py` | 修改 | P1-4（--interval/--deals 入参 fail-closed）+ 3 处注释行号顺带修正 |
| 4 | `workflow-out/plan.md` | 覆盖写 | 本方案；旧 R4-D4 方案已备份（#5） |
| 5 | `workflow-out/_plan-prev-r5-backup.md` | 新建（备份） | **规划期已执行**：`cp` 旧 plan.md，md5 `10ba155ae1bb1c759ded9eb72fbe5a81` 两侧一致（实跑输出在案） |
| 6 | `workflow-out/_implementation-prev-r4-backup.md` | 新建（备份） | **规划期已执行**：`cp` 旧 implementation.md，md5 `079fc6cbd238142ee72945b151896884` 两侧一致 |
| 7 | `workflow-out/implementation.md` | 覆盖写 | R5 实现说明（编码期）：findings 全表 / diff 摘要 / 门禁实录 / 未修复处置理由 |
| 8 | `workflow-out/_pre-task-snapshot-r5.patch` + `workflow-out/_r5-orig-{lib.rs,demo.py,keeper.py}` | 新建（快照） | 编码期开工前：`git diff -- <范围文件>` 存 patch + 逐文件 `cp` 原件；**回退 = cp 回原件（零 git 写）** |

只读素材：`lyquid/src/{types,core,committee,committee_certified,assessor,timeout}.rs`、
`lyquid/tests/{escrow_lifecycle,modelcheck_refund}.rs`、`agents/common/{rpc,protocol,llm}.py`、
`agents/{alice,broker,bob}.py`、`workflow-out/_r2-t0-sim-baseline-raw.txt`、
`workflow-out/demo-script.md`、`docs/演示与运行指南.md`（行号漂移只登记不改写，
红线⑤）；`docs/b3-user-test/` 三件、`workflow-out/report/`、`slides/`、
`_submission-plan.md` **零写入**（红线③）。

## 1. 规划期实跑核实的预置事实（编码员直接采信；标 ✅ 者编码期须复跑）

1. ✅ `git rev-parse HEAD` = `093dd06aafbcfa5236f665dee9745df7836066fd`；工作树
   仅 workflow-out 历史备份 untracked，无未落库代码改动。
2. ✅ `python scripts/demo.py --selftest` → 7 项全 PASS + `SELFTEST OK`。
3. ✅ `python scripts/demo.py --sim --flow all` 重定向输出与
   `workflow-out/_r2-t0-sim-baseline-raw.txt` `diff -u` **零差异**
   （`BASELINE-DIFF-IDENTICAL`，rc=0）——修复后须逐字保持。
4. ✅ `python -m py_compile` 全部 8 个在范围 py 文件通过（`PY_COMPILE-ALL-OK`）。
5. ✅ `MSYS_NO_PATHCONV=1 docker exec -w /tmp/tb-lyquid multi-tools cargo check
   --target wasm32-unknown-unknown` → `Finished dev profile in 5.40s`
   （33 条既有 warning，规划期无源码改动故**未 touch**；编码期 lib.rs 有改动，
   须先 `touch src/lib.rs` 再跑并注明重编）。
6. 审查范围内文件实测 19 个 / 约 5665 行：Rust 源 7 文件 2933 行
   （types 197 / core 909 / lib 850 / committee 185 / committee_certified 433 /
   assessor 273 / timeout 86）+ Rust 测试 2 文件 365 行 + Python 8 文件 2412 行
   + 冻结基线 24 行。
7. 备份双件已落盘（md5 两侧一致，见 §0 #5/#6）：`_plan-prev-r5-backup.md`、
   `_implementation-prev-r4-backup.md`。

## 2. Findings 分级清单（证据 = 本轮逐行通读 + grep 实证）

### 2.1 P0（真缺陷：资金语义/守恒、误报漏报、fail-closed 失效）——本轮 0 项

诚实结论：**未发现 P0**。核过的高危面全部已有防线与钉死测试：
- 资金守恒：`Payout::total()==amount` 由 core 测试钉死（core.rs:344-519，含
  `fee_bps=10_000`、`u16::MAX`、u128 饱和角）；`apply_payout` 全零 Payout
  no-op（lib.rs:697-699，F2）；`fund` 预检→core::fund→debit 顺序契约
  （lib.rs:364-377）。
- 重入/重复结算：终态封死 + Disputed/Funded/Submitted 状态互斥，双 closed
  deadline 边界的两种同槽排序均无双付（core.rs:98-110 + tests
  modelcheck_refund.rs:118-184，720 排序 ×2 变体 0 违例）；路线② 二次回调被
  `core.rs:199` Disputed 门拒（committee_certified.rs:58-59 注记）。
- fail-closed：`--instance` 空串已拦（demo.py:569-573）、TARGET 非零且
  ≠--contract 已断言（demo.py:581-584）、`--flow committee` 先断言后写
  （demo.py:769-777）、`get_node_ids` 任一端口不可达即抛（rpc.py:399-406）、
  e2 域阈值 0 已拒（committee_certified.rs:119-123）。**成员域阈值唯一缺口
  在 escrow 域 `committee_config`，见 P1-1（不足 P0 的理由见该条）。**
- Python 编码边界：docker_exec 强制 utf-8 + errors="replace"（rpc.py:301-302）、
  digest 链 UTF-8（protocol.py:33-34）、selftest 钉死两侧 FNV 向量
  （demo.py:191-210，规划期 PASS）。

### 2.2 P1（健壮性加固）——修 4 项（§4），登记 3 项（§5）

| ID | 级别 | 位置 | 问题与证据 | 处置 |
|---|---|---|---|---|
| P1-1 | 修 | lib.rs:545-556 | `committee_config` 接受 `threshold == 0`：计数门 `signers.len() < threshold`（core.rs:245-247）对 0 永假 → 成员域阈值门失效为"仅剩成员身份+去重"。e2 认证域同输入显式拒绝（committee_certified.rs:119-123），两域口径不一致。**不判 P0 的理由**：触发前提是 Broker 主动配置非法值（require(Access::Broker)，lib.rs:547）；wire 无签名占位下计数门本就是弱断言（lib.rs:511-513 诚实边界）；归档证据流只用 3/4（demo.py:73/:81）。但它是 ask 点名的"成员域阈值"fail-closed 缺口，**必修** | lib.rs 函数体内加 `threshold == 0 → Err`，措辞对齐既有平台层校验（"…must be > 0"，lib.rs:320-326 同风格） |
| P1-2 | 修 | lib.rs:688-691 | `credit` 用裸 `bal + amount`：wasm release 无溢出检查，`faucet`（Access::Anyone，lib.rs:213/:281-291）可给任意 agent 注入接近 u128::MAX 后二次 faucet **回绕其余额**（记账损坏）。`debit` 有预检（lib.rs:680-683）而 credit 无对称防御；apply_payout 四个 credit 点（lib.rs:715/:718/:721/:724）同受益。**不判 P0 的理由**：escrow 路径金额 ≤ amount 不可能回绕（Payout::total ≤ escrowed，lib.rs:713 debug_assert + core 测试钉死），可达面仅 faucet 级荒谬输入；且 faucet 无上限本身是已文档化 demo 信任洞（lib.rs:277-279） | `checked_add` → None 即 `Err("balance overflow")`；签名改 `-> LyquidResult<()>`，调用点 `faucet` 1 处 + `apply_payout` 内 4 处加 `?`（grep 实证全库仅此 5 个调用点） |
| P1-3 | 修 | demo.py:358-360（timeout 流）＋ demo.py:316-321（normal 流） | timeout 流 node 分支：claim 后 `read_back` 只打印不断言，若链上静默 Err（status 0x1 ≠ 方法 Ok，rpc.py:24-29 实测口径）会打印 `final state=Funded … (made whole)` ——**误报**。normal 流同类问题：complete/fund/submit_deliverable 结果弃置（call 为裸派发，demo.py:231-238），rpc.py:24-29 吞 Err 口径下 complete 静默失效仍打印 `final state=…` 并 rc=0 打出 `DEMO COMPLETE`（demo.py:788-791 无 try/except）——与 timeout 流同类误报。对照：adversarial/committee 流均有终态断言（demo.py:487-489/:701-702） | timeout node 分支加 `state != "Refunded" → RuntimeError`；normal 流补终态断言（B1b，仅 node 路径）；**sim 分支零改动**（sim 的 claim/complete 失败本就 assert 抛出——rpc.py:871-875/:859-866，打印恒真值，基线逐字面不受影响） |
| P1-4 | 修 | keeper.py:145-156 | `--interval 0` → 主循环 `time.sleep(0)` 满速 hammer 节点；负值 `time.sleep(-n)` 直接 ValueError 崩溃；`--deals ","` → 过滤后空表静默 watch 空集（keeper.py:150-151），证据运行模式下是无声空转 | main() 入参加 `args.interval <= 0 → p.error(...)`；`--deals` 解析后空表 `p.error(...)`（fail-closed 退出而非静默空转） |
| P1-R1 | 登记 | rpc.py:441-450 | `_rpc` 对非 JSON 响应（网关/HTML 错误页）`r.json()` 裸抛 JSONDecodeError、连接异常裸抛 —— 操作员可见原始错误可定位，包装属错误信息美化 | 登记不修：控制改动面 |
| P1-R2 | 登记 | broker.py:31、llm.py:62 | live 模式（TB_LLM=openai）畸形 LLM 响应 → KeyError/IndexError 裸 traceback；脚本回放模式确定性不受影响 | 登记不修：仅真实后端路径 |
| P1-R3 | 登记 | timeout.rs:54-63 | `watcher_step` 单笔 claim 失败 `?` 整轮中断（:59-60 注记自认）——已交付触发路径是 keeper.py；watcher 无许可且幂等，下轮重试自愈；改动须重编 wasm，收益边际 | 登记不修 |

### 2.3 P2（健康/风格，只登记；顺带清理仅限因 P1 已打开的文件）

| ID | 位置 | 证据 | 处置 |
|---|---|---|---|
| P2-1 | 死 import：rpc.py:56 `field`、demo.py:63 `SLOT_MS`、alice.py:16 `Acceptance`/`Deliverable` | grep 实证：rpc.py/alice.py 无第二处引用；demo.py 仅 import 行出现 | demo.py 因 P1-3 已打开 → 顺带删 `SLOT_MS`；rpc.py/alice.py 不打开 → 只登记 |
| P2-2 | 注释行号漂移 10 处 | keeper.py:19-20（`rpc.py:330-337`→实为 :578-584；`rpc.py:241-262`→实为 :464-485）、keeper.py:68（`rpc.py:301-311`→实为 :549-559）、demo.py:92-93（`keeper.py:56-58`→实为 :69-70）、demo.py:117（`keeper.py:60-68`→实为 :73-81）、demo.py:416（`core.rs:203-210`→实为 :202-209）、lib.rs:400（`committee.rs:58`→check_evidence_shape 实为 :66-74）、rpc.py:426（`lib.rs:624`→require 实为 :230-246）、rpc.py:500（`lib.rs:241`→faucet 实为 :280-291）、rpc.py:895+911-915（`lib.rs:365-368`/:369-371→实为 :530-533/:756-758）、protocol.py:19（`rpc.py:49`→notarize 包装实为 :564-570） | keeper.py/demo.py/lib.rs 已打开 → **顺带修本文件内 6 处**；rpc.py/protocol.py 不打开 → 登记 4 处 |
| P2-3 | 死代码（登记不删） | committee.rs:78-90 `set_members`/`members` shim（grep 全库无调用点，lib.rs:748 仅注释提及）；timeout.rs:86 `SPIKE_1_TRIGGER_REGISTRATION`（文档性归档常量）；lib.rs:723-725 slash 分支（:702-704 注记明言 intentional dead code, W4） | 登记：均在 lyquid 面，删除须重编 wasm 换零行为收益 |
| P2-4 | 判定面漂移（**红线②禁止改链侧**） | 未知 verdict_code：链上 `_ => Malicious`（committee.rs:45-49），sim dict 索引 KeyError（rpc.py:919） | 登记：链侧改映射即判级行为变更；真实修复 = W4 oracle 签名认证（lib.rs:511-513 已登记占位） |
| P2-5 | 双规范化策略并存 | protocol.py:30 `canonical_json` `ensure_ascii=False` vs demo.py:256/:388、broker.py:38-40 `json.dumps(sort_keys=True)`（ensure_ascii 默认 True） | 登记：当前载荷全 ASCII 无分叉；非 ASCII 时两域 digest 会分叉，W4 收敛单点 |
| P2-6 | FakeNode 非镜像面 + assert 守卫 | rpc.py:809-813 注记明言"其余校验故意不镜像"；assert 式守卫（rpc.py:826/:855/:871/:879/:887/:894）在 `python -O` 下消失 | 登记：sim 定位 = 编排冒烟，语义真值在 Rust core |
| P2-7 | broker.py:57-59 硬编码默认成员 `node-1..4` | 与 rpc.py:398"禁硬编码 NodeID"口径相悖；agent CLI 独立入口，demo 主链路不经它（flow_committee 自行发 NodeID 制配置） | 登记 |
| P2-8 | demo.py:350-354 due 扫描每 deal 调 3 次 `deal_info`（node-only 效率） | 同函数内重复读 | 登记不修：正确性无涉，改了反而扰动 node 路径 |
| P2-9 | `wait_for(node, …)` 的 `node` 形参未使用（demo.py:147-176） | 函数体零引用 | 登记不修：签名稳定性优先，调用点 4 处 |
| P2-10 | `threshold > 成员数` 可配置（config 时不校验） | 只会令后续裁决恒 `InsufficientCommittee`（core.rs:245-247）——fail-closed 方向的死锁型配置，非安全洞 | 登记为按设计接受 |
| P2-11 | `Payout::total` 裸加法（types.rs:174-176） | u128 理论回绕面，仅 faucet 级荒谬值可达；types.rs 冻结 | 登记：P1-2 已在 credit 单点拦截入账侧 |
| P2-12 | 行号引用类文档漂移 | `workflow-out/demo-script.md`、`docs/演示与运行指南.md`（两文件在盘已确认）引用 demo.py/keeper.py 行号，本轮改动后可能漂移 | 编码期实查后**只登记漂移条目不改写**（红线⑤） |

## 3. 子任务拆分与执行顺序（编码期）

1. **S1 快照**：`git diff -- lyquid/src scripts agents > workflow-out/_pre-task-snapshot-r5.patch`
   （预期空 diff，留档）；`cp` lib.rs/demo.py/keeper.py → `workflow-out/_r5-orig-*`（回退 = cp 回，零 git 写）。
2. **S2 Rust 侧**（§4-A 两处 + 顺带 P2-2 的 lib.rs 注释）→ `touch src/lib.rs` +
   G4 cargo check（注明重编原因：lib.rs 有改动）。
3. **S3 Python 侧**（§4-B/§4-C + 顺带 P2-1/P2-2 的 demo/keeper 项）→ G1 py_compile。
4. **S4 门禁复跑**：G2 selftest → G3 sim 基线逐字 diff（**硬门，逐字节**）→
   G5 `git diff --stat` 核查改动面 = 受影响清单 #1–#3，且不含 types.rs/core.rs。
5. **S5 文档漂移核查**（P2-12）：grep demo-script.md 与 docs/演示与运行指南.md
   的行号锚点，登记实际漂移，不改写。
6. **S6 implementation.md 覆盖写**（R5 版）：findings 全表、已修 diff 摘要、
   门禁命令与输出实录、P1-R/P2 未修复处置理由（引用本方案 §2 编号）。
7. **S7 终核**：`git status --short` 确认零 git 写、改动面闭合；不 commit
   （红线④，沿轮次惯例留人工）。

## 4. 具体改动点（逐文件）

### A. `lyquid/src/lib.rs`（P1-1 + P1-2 + 顺带注释）

- **A1（P1-1）** `committee_config`（:545-556）：`require(...)?` 之后插入
  `if threshold == 0 { return Err(lyquid_error("committee threshold must be > 0")); }`。
  不改签名/ABI/console；`demo.py` 全部调用点为 3/4（demo.py:73/:776/:595），
  keeper/broker 均不传 0 → 已归档证据流零影响。
- **A2（P1-2）** `credit`（:688-691）：
  `let new = bal.checked_add(amount).ok_or_else(|| lyquid_error("balance overflow"))?;`
  插入后写回 `new`；签名 `-> LyquidResult<()>`。调用点 5 处加 `?`：
  faucet :288；apply_payout 内 :715/:718/:721/:724（apply_payout 本就返回
  LyquidResult，:712）。
- **A3（顺带 P2-2）** :400 注释 `committee.rs:58` → `committee.rs:66-74`。

### B. `scripts/demo.py`（P1-3 + 顺带 P2-1/P2-2）

- **B1a（P1-3，timeout 流）** flow_timeout node 分支（:358 `after = read_back(...)`
  之后、print 之前）插入：
  `if after.get("state") != "Refunded": raise RuntimeError(f"{deal_id}: timeout claim did not reach Refunded (state={after.get('state')!r}) — claim likely swallowed on-chain; inspect keeper/console")`。
  位于 `if node_mode(node):` 块内（:340-360）→ sim 字面零变化。
- **B1b（P1-3 扩展，normal 流）** flow_normal 的 `final = read_back(node, deal_id)`
  （:318）之后、print（:319）之前插入（`if node_mode(node):` 守卫，仅 node 路径）：
  `if final.get("state") != "Settled": raise RuntimeError(f"{deal_id}: complete did not reach Settled (state={final.get('state')!r}) — write likely swallowed on-chain (rpc.py status-0x1 caveat)")`。
  断言零打印 → G3 sim 基线逐字门不受影响（基线该行为
  `final state=Settled balances: alice=9000 bob=980 broker=20`，
  _r2-t0-sim-baseline-raw.txt:7；且 FakeNode.complete 状态不符即 raise，
  rpc.py:859-866，sim 恒通过——双保险）。
- **B2（顺带 P2-1）** :63 import 删 `SLOT_MS`。
- **B3（顺带 P2-2）** :92-93、:117、:416 三处注释行号改指实际位置。

### C. `scripts/keeper.py`（P1-4 + 顺带 P2-2）

- **C1（P1-4）** :147 `args = p.parse_args()` 后加
  `if args.interval <= 0: p.error("--interval must be >= 1 (0/negative would busy-loop or crash)")`；
  :150-151 `--deals` 分支解析后 `if not deals: p.error("--deals parsed to an empty list; nothing to watch")`。
- **C2（顺带 P2-2）** :19-20、:68 三处注释行号改指实际位置。

## 5. 未修复项处置理由（汇总）

- **P0 全零**：见 §2.1，高危面均有既有防线 + 钉死测试，不虚报缺陷凑数。
- **P1-R1/R2/R3**：登记理由见 §2.2 表（改动面控制 / 仅 live 路径 / 已交付路径
  覆盖且收益边际）。
- **P2 全部只登记**（任务书分级定义）；其中 P2-1/P2-2 的"顺带清理"严格限制在
  因 P1 已打开的 3 个文件内，其余文件零打开零改动。
- **红线②禁止类**：P2-4 链侧未知 verdict_code 映射，判级行为冻结，W4 处置。

## 6. 红线合规表与门禁

| 红线 | 本方案合规性 |
|---|---|
| ① types.rs/core.rs 模型检查钉死 | **两文件零改动**（G5 用 `git diff --stat` 证明）→ 不触发壳 crate 模型检查复跑义务；若审查期要求扩入语义改动，先停下走 verify_core `cargo test --lib --tests 40/40` 复跑登记流程，未跑不动 |
| ② lyquid 判级行为 | A1/A2 不触 console 打印面（faucet `log!` :289、fund deal_view :386-390、apply_verdict println :786-792 全不动）、不触 E2_AVG_NUM（committee_certified.rs 不打开）、不触方法签名 ABI（两个 network 方法签名逐字不变；`credit` 是 crate 内私有 helper 非 ABI 面）。归档证据流阈值恒 3/4、金额合规 → 行为零漂移 |
| ③ 只读清单 | docs/b3-user-test/ 三件、workflow-out/report/、slides/、_submission-plan.md 零写入 |
| ④ 零 git 写 | 不 commit/add/push/branch/tag/restore/stash；回退用 cp 原件（§3-S1） |
| ⑤ 行号漂移文档 | demo-script.md、docs/演示与运行指南.md 只登记不改写 |

**门禁（编码期全复跑，全部只读）**：
- G1 `python -m py_compile <全部改动 py 文件>`
- G2 `python scripts/demo.py --selftest` → `SELFTEST OK`
- G3 `python scripts/demo.py --sim --flow all` 输出与
  `workflow-out/_r2-t0-sim-baseline-raw.txt` 逐字 `diff` → **必须零差异**
  （P1-3/B2/B3 均 node 分支或注释/import，sim 字面不变）
- G4 `MSYS_NO_PATHCONV=1 docker exec -w /tmp/tb-lyquid multi-tools cargo check
  --target wasm32-unknown-unknown`（lib.rs 有改动 → 先 `touch src/lib.rs`
  并在实现说明注明重编）
- G5 `git diff --stat` 改动面核查（= 清单 #1–#3 + workflow-out 文档件）
- G6 全程零链写零部署零重启（不跑任何 `--node` 流）

## 7. 风险与回退

| 风险 | 缓解/回退 |
|---|---|
| lib.rs 改动编译失败（宏展开借用/`?` 传播） | A2 调用点全部在已有 `LyquidResult` 返回函数内；cargo check 是硬门，失败即 `cp workflow-out/_r5-orig-lib.rs lyquid/src/lib.rs` 整体回退 A 组（Python 修复独立成立） |
| credit 签名变化牵出隐藏调用点 | grep 实证全库仅 5 个调用点（§4-A2）；cargo check 全量兜底 |
| sim 基线 diff 失败（Python 改动泄漏 sim 面） | B1/B2/B3 均 node 分支/注释/import；若仍漂移，逐行定位改为 node-only 写法，基线逐字一致是硬门不放过 |
| threshold 拒绝误伤既有流 | 全库 grep `committee_config` 调用点：demo.py:595(E2_THRESHOLD=4)/:776(THRESHOLD=3)、broker.py:59(threshold=3)——无一传 0 |
| 改动引发连锁文档漂移 | §3-S5 实查登记（红线⑤，不改写） |
| 最坏情形 | 四文件各自 cp 原件还原 + implementation.md 如实登记"未修复"，零链上残留（本轮无任何链操作） |
