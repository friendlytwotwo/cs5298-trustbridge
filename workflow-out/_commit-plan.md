# R1 提交建议清单（**未执行任何 git commit**）

生成日期：2026-10-29。基线：`trustbridge` 仓库 HEAD `dc78d2f`（W1-B2 成果已入库；
本轮 R1 改动全部在工作树）。本清单只给建议，不含任何已执行的提交动作。

## §1 现状

```
$ git -C trustbridge status --short
 M README.md
 M agents/common/rpc.py
 M lyquid/src/assessor.rs
 M lyquid/src/lib.rs
 M scripts/demo.py
 M scripts/keeper.py
 M workflow-out/plan.md
?? workflow-out/_collab/  workflow-out/_implementation-prev-w1a-backup.md
?? workflow-out/_plan-prev-w1b2-backup.md  workflow-out/_plan-prev-w1b2-closure-backup.md
?? workflow-out/_pre-task-snapshot-r1.patch
?? workflow-out/_probe_cold_a0.md  workflow-out/_probe_gate_a0.md  workflow-out/_probe_plan_r1_a0.md
?? workflow-out/_r1-*.txt（10 个原始日志）
?? workflow-out/_w1b1-deploy-zz2jue.txt  _w1b1-r1-submodule-state-check.txt  _w1b1-setupdevnet-bootstrap.log
?? workflow-out/w1b2-r1-s3-assess.md  w1b2-r1-demo-normal.md  w1b2-r1-demo-timeout.md
```

> **勘误（2026-10-30 看护核销，原文快照保留不改）**：
> ① 上块「`_r1-*.txt`（10 个原始日志）」少计——实际 **13 个**（C4 引用 12 个 +
> 可选 `_r1-deploy-raw.txt` 1 个，与 §2-C4 可选项合计一致）；
> ② 上块漏列当时已 M 的 `workflow-out/implementation.md`（R1 轮重写），该文件已由
> §5-C7 收录，覆盖面不受影响；
> ③ §2 的「C5（不入库）」与 §5 的 R2-C5 重号：**§5 起 C5–C7 均指 R2 提交序列**，
> R1 的不入库项以下称「R1-不入库」。

`git diff --stat`：README.md 8 行、rpc.py +65、assessor.rs +5、lib.rs 44 行（±）、
demo.py 227 行（±）、keeper.py +49、plan.md 404 行（整轮重写）。

W1-B2 的未提交遗留在本轮开始时已不存在（HEAD `dc78d2f` 即 W1-B2 收尾提交），故本清单
只覆盖 R1 增量；R0/W1-B2 的文件不再出现在待提交面。

## §2 建议提交序列（4 个主题提交 + 1 个说明性不入库项）

### C1 — `R1 S3: assess_brief 7→4 string + export=eth restored (Route A)`

- 文件：`lyquid/src/lib.rs`、`lyquid/src/assessor.rs`
- 内容：签名收拢为 `brief_json/base_url/api_key/model`；`#[derive(Deserialize)]` 上
  `DealBrief`；恢复 `#[method::instance(export = eth)]`；注释改为 R1 恢复口径（7 参
  Stack too deep 记录保留为平台限制存档）。
- 依赖：**必须先于 C2**（C2 的 `_ABI` selector `0x3297eeb6` 与 4 参 wire 形态一一对应；
  先提交 C2 会让仓库处于"rpc.py 指向不存在签名"的中间态）。
- 风险：`lyquid/src/types.rs`/`core.rs` 必须零 diff（本轮实测 `git diff --stat` 空）；
  壳测试 40/40 不随本提交漂移（只有 derive，无测试增删）。

### C2 — `R1 S4: role key table + nudge/discover/assess wrappers; demo/keeper node mode`

- 文件：`agents/common/rpc.py`、`scripts/demo.py`、`scripts/keeper.py`
- 内容：
  - rpc.py：`BROKER_ADDR/ALICE_ADDR/BOB_ADDR`、`nudge()`、`discover_deals()`、
    `assess_brief()` + `_ABI` 新行、`due_deals` 实测注记；
  - demo.py：node 模式身份/发送方矩阵、`--contract` 透传、`--flow all` 门控 + sim-only
    横幅、`--flow adversarial` exit 2、超时流短估算 + nudge + 枚举、终态/建单后读回重试；
  - keeper.py：`--deals` 改可选（缺省枚举）、`--nudge/--no-nudge`（默认 on）。
- 依赖：C1 之后；与 C1 同一次 push 前不要单独部署镜像（deploy 产物需与 C1 源码一致）。
- 风险：sim 行为必须零回退 —— 提交前跑 `python scripts/demo.py --sim --flow all` +
  `--selftest`（本轮实测与 T0 基线逐行一致）；`scripts/demo.py` 的读回重试是唯一
  新增网络时序逻辑，node 模式之外不触发。

### C3 — `R1 docs: SPIKE W1-4 removal + assessor status line`

- 文件：`README.md`
- 内容：:107/:128 两栏 NodeClient 描述更新（移除 SPIKE W1-4）；:28/:41 LLM assessor
  状态行按 T4 实测改为"回放模式已链上驱动 / 真实后端待 egress 与凭据"。
- 依赖：应与 C1/C2 一起或紧随其后（文案描述的是 C1/C2 的结果）。
- 风险：低；不得顺带扩写其他状态行（本轮 diff 仅 4 行）。

### C4 — `R1 evidence: plan + S3 assess + demo normal/timeout transcripts`

- 文件：`workflow-out/plan.md`、`workflow-out/w1b2-r1-s3-assess.md`、
  `workflow-out/w1b2-r1-demo-normal.md`、`workflow-out/w1b2-r1-demo-timeout.md`、
  `workflow-out/_commit-plan.md`，以及被证据文件引用的原始日志：
  `_r1-g2-raw.txt`、`_r1-mock-selftest-raw.txt`、`_r1-console-raw.txt`、
  `_r1-console-fund-raw.txt`、`_r1-deploy-final-raw.txt`、`_r1-demo-normal-raw.txt`、
  `_r1-demo-all-raw.txt`、`_r1-due-deals-raw.txt`、`_r1-rpc-smoke-raw.txt`、
  `_r1-keeper-raw.txt`、`_r1-keeper-nudge-raw.txt`、`_r1-final-state-raw.txt`
- 依赖：C1–C3 之后（证据描述的是这些提交后的行为）。
- 风险：`plan.md` 为整轮重写（404 行 diff），提交前请完整过目；原始日志含部署日志
  （约 20KB×2）与本地路径，无凭据（探针 api_key 为假值且在 md 中已脱敏）。
- 可选：`_r1-deploy-raw.txt`（第一次 deploy 的探索日志）与 `_r1-deploy-final-raw.txt`
  （最终实例）二者保留后者即可；若追求仓库干净可只提交被证据文档引用的那一份。

### C5 —（不入库；与 §5 的 R2-C5 重号，下称「R1-不入库」）`_pre-task-snapshot-r1.patch` 与 R0 期临时件

- `workflow-out/_pre-task-snapshot-r1.patch`：T0 事故恢复凭据（仅含本轮开始时的
  `plan.md` 未提交 diff）。**建议不提交**，留在工作树作本地恢复用；若团队希望保留
  恢复记录，可单列 `chore: R1 pre-task snapshot (recovery only)` 并说明其非代码。
- 上轮遗留未跟踪件（`_collab/`、`_implementation-prev-w1a-backup.md`、
  `_plan-prev-w1b2-*.md`、`_probe_*_a0.md`、`_w1b1-*`）：属 W1-A/W1-B 轮次的存档，
  与本轮无关；建议单独一次 `chore: archive earlier-round workflow-out artifacts`
  或加进 `.gitignore`，避免混进 R1 提交。

## §3 parent 级壳（`verify_core`）归属说明

`workflow-out/verify_core/`（壳 crate，40/40 字面 = 33 lib + 5 escrow + 2 modelcheck）
位于 **`F:\canvus auto\downloads\202609CS5298\workflow-out\verify_core`**，即
**trustbridge 仓库之外**（父目录仓库 `F:\canvus auto` 内，且未被本仓库跟踪）。
本轮 T0/T6 两次跑通 40/40，但**其任何历史修复都不属于 trustbridge 的提交面**；
若要入库，须在父仓库（`F:\canvus auto`）单独开提交，并在信息里注明它是壳/证据工具
而非交付代码。R1 本轮未修改壳，只做只读复跑（不作为本清单任何提交的文件）。
**R3 轮补记（2026-10-30，R3-T6）**：壳仍**零修改**，只做只读复跑（宿主通道
`cargo test --lib --tests` = 33+5+2 = 40/40，见 `_r3-t6-regression-raw.txt` T6.2）；
壳的任何文件都不在 §6 的 R3 提交面内。

## §4 提交顺序与门禁建议

1. C1 → 本地跑 `docker exec … cargo check --target wasm32-unknown-unknown`（容器内，
   先 cp + md5）与父目录壳 `cargo test --lib --tests`；
2. C2 → `python scripts/demo.py --selftest` + `--sim --flow all`（与 T0 基线逐行比对）；
3. C3 → 文案复核（grep `SPIKE W1-4` 在 README/scripts/agents 零命中）；
4. C4 → 证据文件自洽复核（引用的原始日志都在同一提交内）。
5. 全部 push 前重跑 `--flow normal`/`--flow all` 会新建链上 deal，属可接受的实例累积，
   但**不要**把链上地址写进提交信息（地址属证据文档，实例可随时重建）。

**再次声明：以上均为建议，本任务未执行 `git commit`/`git add`/`git push`。**

---

## §5 R2 建议提交序列（2026-10-29 增补；仍未执行任何 git commit/add/push）

> 基线：HEAD `dc78d2f` + R1 工作树（C1–C4 未提交）。R2 只增量描述；**依赖 C1–C4 先行**，
> 否则 C5 的 lib.rs 提交会把 R1 的 assess_brief 改写一并带入错误的主题。

### C5 — `R2 route ①: flat eth wire for open_dispute / apply_committee_verdict`

- 文件：`lyquid/src/lib.rs`
- 内容：
  - `open_dispute` 加 `#[method::network(export = eth)]`（仅属性行 + 注记改写）；
  - `apply_committee_verdict` 签名扁平化为 `(ctx, deal_id, verdict_code: u8, signers: Vec<AgentId>)`
    + `export = eth`，体内由扁平参数重建 `CommitteeCertWire`（校验/裁决/写回链逐字沿用）；
  - Ok 路径追加 `apply_verdict: deal=… verdict=… misconduct=[…]` println（取证缝，
    非共识状态，方法清单不新增）；
  - 注记面五处：模块头、通道注记块、`open_dispute` 前置注记、ACCESS_MATRIX 行内、
    `committee_config` 前置注记。
- 风险：`types.rs`/`core.rs`/`committee.rs`/`assessor.rs` 必须相对 T0 基线零变化
  （`md5sum -c workflow-out/_r2-t0-frozen-baseline.txt`）；`assessor.rs` 对 HEAD 的 `+5`
  属 R1/C1，**不得回退**（lib.rs 的 `serde_json::from_str` 依赖该 derive）。
- 验证：容器 `cargo check --target wasm32-unknown-unknown`（先 `touch src/*.rs` 强制重编，
  见 `_r2-deploy-raw.txt`）+ deploy 后 wire 探针（selector `a32974e3`）。

### C6 — `R2: adversarial flow on-chain + on-chain assess in normal flow; remove sim-only gate`

- 文件：`agents/common/rpc.py`、`scripts/demo.py`
- 内容：
  - rpc.py：`_ABI` 新增 `apply_committee_verdict(string,uint8,string[])`（selector
    `a32974e3`，`cast sig` 实取）；`NodeClient.apply_committee_verdict` 实装（域三元组
    保持、同源根预检、`sender or caller` 回落）；排除注记改写为 R2 口径；
    **`_enc_value("string[]")` 与 `_decode_ret("string[]")` 的元素偏移修正**
    （R1 潜伏缺陷，见 `w1b2-r2-adversarial.md` §5、`w1b2-r2-keeper-timeout.md` §3）；
  - demo.py：`flow_adversarial` 增 node 分支（身份/发送方矩阵、地址制委员会、分支自带
    faucet 10_000 + 每单 fund 前余额断言、Malicious 主场景 + Fulfilled 对照 +
    NotFulfilled 第三场景）；`new_assessed_deal` node 分支改走链上 `assess_brief`；
    `flow_normal` fund 前加静默余额断言；删 `ADVERSARIAL_BANNER` / node `exit 2`；
    node `--flow all` 序列改 `["normal","timeout","adversarial"]`；docstring 同步。
- 依赖：C5 之后（selector 与 wire 形态一一对应；C6 先提交会指向不存在的签名）。
- 风险：sim 行为零回退——提交前跑 `python scripts/demo.py --selftest` +
  `--sim --flow all` 与 T0 基线逐字 diff（R2 实测一致）。
- 注意：**编码器修正会改变 `committee_config` 的实际链上效果**（R1 的 node 运行从未真正
  配置成功）。提交信息里应点明这是行为修正，不是纯重构。

### C7 — `R2 evidence: keeper timeout loop, adversarial three-scenario, normal assess`

- 文件：`workflow-out/w1b2-r2-keeper-timeout.md`、`w1b2-r2-adversarial.md`、
  `w1b2-r2-normal-assess.md`、`workflow-out/_commit-plan.md`、`workflow-out/implementation.md`，
  以及被引用的原始日志：`_r2-t0-frozen-baseline.txt`、`_r2-t0-sim-baseline-raw.txt`、
  `_r2-t0-env-raw.txt`、`_r2-deploy-raw.txt`、`_r2-g3a-sim-after-raw.txt`、
  `_r2-due-nonempty-raw.txt`、`_r2-keeper-loop-raw.txt`、`_r2-adversarial-raw.txt`、
  `_r2-adversarial-attempt1-raw.txt`、`_r2-adversarial-console-raw.txt`、
  `_r2-normal-assess-raw.txt`、`_r2-assess-castcall-raw.txt`、`_r2-node-all-raw.txt`、
  `_r2-final-state-raw.txt`、`_r2-t7-regression-raw.txt`
- 依赖：C5/C6 之后（证据描述的是这两次提交后的行为）。

### C8 —（不入库）`workflow-out/_pre-task-snapshot-r2.patch`

- T0 恢复凭据（本轮开始时的完整 `git diff`，1643 行）。与 R1 的
  `_pre-task-snapshot-r1.patch` 同处置：留工作树，不提交。

**R2 文件面（相对 HEAD 的增量，含 R1 未提交部分时请对照 implementation.md §0）**：
`lyquid/src/lib.rs`、`agents/common/rpc.py`、`scripts/demo.py` 三个 M 文件 +
`workflow-out/` 的文档/日志；`scripts/keeper.py`、`lyquid/src/{types,core,committee,assessor}.rs`、
`lyquid/Cargo.toml`、`README.md` 在 R2 **零改动**。

**再次声明：以上均为建议，本任务未执行 `git commit`/`git add`/`git push`。**

---

## §6 R3 建议提交序列（2026-10-30 增补；仍未执行任何 git commit/add/push）

> 基线：HEAD `dc78d2f` + R1/R2/R3 **未提交**工作树（§2 的 C1–C4、§5 的 C5–C8 均未执行）。
> R3 只做增量描述，**依赖 C1–C8 先行**。原因：`lyquid/src/lib.rs`、`agents/common/rpc.py`、
> `scripts/demo.py` 是三轮共改文件；跳过前序组直接提交 R3 组，会把 R1/R2 的主题一并带入，
> 使提交历史与 §2/§5 的叙述不一致。
>
> 本轮（R3-T6）不做任何提交动作：本节与 §6.1 覆盖表只是**建议清单**。

### R3-C1 — `R3 route ②: certification callback wiring (committee_certified) + lib.rs hook`

- 文件：`lyquid/src/committee_certified.rs`（新，433 行）、`lyquid/src/lib.rs`（M，R3 增量）
- 内容：
  - `committee_certified.rs`：E2 七方法（`e2_configure` / `e2_arm` / `e2_net_config` /
    `propose` / `aggregate` / `committee_verdict_certified` / `e2_run_verdict_round`），
    模块头即「E2 门禁台账」（7 方法 × 面 × 实际门 × 是否触资金）；`E2_AVG_NUM = 4`（编码期常量）。
  - `lib.rs`：模块头 R3 段、`state!` 两字段（`network oracle cert_verdict;`、
    `network e2_armed_deal: String`）、模块声明、ACCESS_MATRIX 注记（矩阵本体零增删）、
    通道注记块 R3 段、`apply_committee_verdict` 行为保持重构（抽出
    `pub(crate) fn apply_cert_and_payout`，逐字搬移校验/裁决/写回/结算链）。
- 依赖：**R1-C1（assess_brief）与 R2-C5（扁平 wire）先行**，否则 `lib.rs` 一笔带入三轮主题
  （沿 §5 开头提醒口径）。
- 风险/门禁：`types.rs`/`core.rs`/`committee.rs` 相对 T0 基线零 diff；
  `assessor.rs` 对 HEAD 的 `+5` 不得回退（`serde_json::from_str` 依赖该 derive）；
  壳 40/40 不随本提交漂移（R3 轮壳零修改、只读复跑，见 §3 末句与 `_r3-t6-regression-raw.txt` T6.2）。

### R3-C2 — `R3: committee flow orchestration + container channel helpers`

- 文件：`agents/common/rpc.py`（M，R3 面）、`scripts/demo.py`（M，R3 面）
- 内容：
  - `rpc.py`：`docker_exec` / `docker_exec_cast` 容器通道助手（`MSYS_NO_PATHCONV=1`）、
    `shaker_to_hex` / `shaker_console`、`node_id_to_bytes32` / `get_node_ids`（四端点 fail-closed）、
    `_ABI` 三行（`e2_arm` / `e2_run_verdict_round` / `e2_net_config`；`e2_configure` 不入表）、
    `NodeClient` 的 `e2_*` 与 oracle advance/finalize/dest_epoch 包装。
  - `demo.py`：`flow_committee`（node-only，plan §3.6 的 1–7 步）、`wait_for` 读回 helper、
    `--instance` 参数与 `DEFAULT_INSTANCE`、`--flow committee` choices、`main()` 的
    `if args.flow != "committee"` fail-closed 门控；`--flow all` 序列不变。
- 依赖：**R3-C1 之后**（selector / wire 形态与链上方法一一对应）。
- 注意：这两个文件同时承载 **R1-C2 与 R2-C6** 的增量——必须按 **C2 → C6 → R3-C2** 顺序
  分别提交各自 hunk；R2-C6 的提交信息已点明「编码器修正是行为修正，不是纯重构」，R3-C2 同理。
- 验证：提交前跑 `python scripts/demo.py --selftest` + `--sim --flow all` 与 T0 基线逐字 diff
  （R3-T6 实测 7 PASS + IDENTICAL，见 `_r3-t6-regression-raw.txt` T6.1）。

### R3-C3 — `R3 fix: faucet read-back before snapshot (D-T3-1 behavior fix)`

- 文件：`scripts/demo.py`（**仅 D-T3-1 修复 hunk**：现 :622-634，13 行替换原 2 行、净 +11 行，
  其后行号整体 +11；余额断言本体 `:703-707` 零改动）
- 性质：**行为修正，非重构**（沿 R2-C6「行为修正」先例口径）。根因：faucet 是 fire-and-forget
  send，`before` 在落账前读取（stale baseline）；修复 = 先读回确认 faucet 落账、再快照。
- 依赖：**R3-C2 之后**（修复位于 `flow_committee` 内）。
- 验证（本轮实跑）：`py_compile` rc=0；`--selftest` 7 PASS；`--sim --flow all` 与 T0 基线
  IDENTICAL；`--sim --flow committee` rc=1 门控不变（`_r3-t6-regression-raw.txt` T6.1）。
  **端到端 committee 重验需新实例（部署/链写），本轮未做**——提交信息里不得声称已验证。

### R3-C4 — `R3 experiments: EVM escrow contrast (Escrow.sol + foundry + runner)`

- 文件：`experiments/evm-contrast/Escrow.sol`、`experiments/evm-contrast/foundry.toml`、
  `experiments/evm-contrast/run-contrast.sh`（目录 `experiments/`）
- 内容：纯 EVM 最小对照（自建 k-of-n ECRECOVER、keccak 顺序证据根、三流 + gas 采集）；
  数据与报告见 R3-C6 的 `r3-t4-contrast-report.md`。
- 依赖：无（不在 `lyquid/` 冻结树内，独立工程）。

### R3-C5 — `R3 docs: B3 user-test kit (manual / criteria / feedback form)`

- 文件：`docs/b3-user-test/操作手册.md`、`docs/b3-user-test/通过判据.md`、
  `docs/b3-user-test/反馈收集表.md`（目录 `docs/b3-user-test/`）
- 内容：组外用户可照跑的操作手册（六节 + 附录）、L2/L1/L0 通过判据（逐条引 console 原文行）、
  四维反馈收集表（空白表单，无示例反馈）。
- 依赖：R3-C3 之后（手册需按修复后行号/函数锚点描述；修复后的新增行标「无已档实录」）。

### R3-C6 — `R3 evidence: final docs + T1/T3/T4/T6 raw logs`

- 文件：
  - 证据文档：`workflow-out/w1b2-r3-e2-committee.md`、`workflow-out/r3-t4-contrast-report.md`
  - 原始日志：`_r3-t1-*`（7 件）、`_r3-t3-*`（4 件）、`_r3-t4-*`（13 件）、
    `_r3-t6-regression-raw.txt`（1 件）
  - 轮文档最终态：`workflow-out/plan.md`、`workflow-out/implementation.md`、
    `workflow-out/_commit-plan.md`
- **移列声明（硬性）**：三份轮文档被多轮改写，只能以**最终态**入库，故从 R1-C4 / R2-C7 的
  文件清单**移列**至本组；C4/C7 的描述保留其**时点语义**（描述当时提交的主题），
  文件清单以本组为准。
- 不重复：`_r2-t0-frozen-baseline.txt`、`_r2-t0-sim-baseline-raw.txt` 已在 R2-C7。

### 不入库 / 归档

- **不入库**：`_pre-task-snapshot-r1.patch` / `_pre-task-snapshot-r2.patch` /
  `_pre-task-snapshot-r3.patch`（恢复凭据，沿 R1-不入库 / C8 处置）、
  `_implementation-prev-*`（3 件自保备份）、`_collab/`（沿 R1-C5 归档建议）。
- **归档**：`_plan-prev-*`（7 件方案逐阶段备份）、`_probe_*`（6 件探针）、
  `_w1b1-*`（3 件 W1-A/W1-B 轮存档）。建议沿用 R1-C5 的做法：另起一次
  `chore: archive earlier-round workflow-out artifacts` 或加 `.gitignore`，避免混进 R3 提交。

### §6.1 覆盖表（硬性）：行数 = 执行时 `git status --porcelain` 行数，零未归属

生成时点：2026-10-30（R3-T6 收尾，`docs/b3-user-test/` 与 `_r3-t6-regression-raw.txt` 已落盘）。
`git status --porcelain` = **96 行**，下表 **96 行**，未归属 = **0**。
分组计数：

| 组 | 行数 |
|---|---|
| C1 | 1 |
| C2 | 1 |
| C3 | 1 |
| C4 | 16 |
| C7 | 18 |
| R3-C1 | 2 |
| R3-C2 | 1 |
| R3-C3 | 1 |
| R3-C4 | 1 |
| R3-C5 | 1 |
| R3-C6 | 30 |
| 不入库 | 6 |
| 不入库/归档 | 1 |
| 归档 | 16 |
| **合计** | **96** |

| # | 状态行（`git status --porcelain` 原样） | 归组 | 备注 |
|---|---|---|---|
| 1 | ` M README.md` | C3 | R1 文案（SPIKE 移除 + 状态行） |
| 2 | ` M agents/common/rpc.py` | R3-C2 | 多轮共改：C2 → C6 → R3-C2 按序分 hunk 提交 |
| 3 | ` M lyquid/src/assessor.rs` | C1 | DealBrief derive（+5），不得回退 |
| 4 | ` M lyquid/src/lib.rs` | R3-C1 | 多轮共改：C1 → C5 → R3-C1 按序分 hunk 提交 |
| 5 | ` M scripts/demo.py` | R3-C3 | 多轮共改：C2 → C6 → R3-C2；本轮 D-T3-1 修复单独 R3-C3 |
| 6 | ` M scripts/keeper.py` | C2 | R1 keeper 改动 |
| 7 | ` M workflow-out/implementation.md` | R3-C6 | 移列自 R1-C4/R2-C7（最终态入库） |
| 8 | ` M workflow-out/plan.md` | R3-C6 | 移列自 R1-C4/R2-C7（最终态入库） |
| 9 | `?? docs/b3-user-test/` | R3-C5 | 目录 3 件：操作手册 / 通过判据 / 反馈收集表 |
| 10 | `?? experiments/` | R3-C4 | 目录 3 件：Escrow.sol / foundry.toml / run-contrast.sh |
| 11 | `?? lyquid/src/committee_certified.rs` | R3-C1 | 新模块（433 行，含 E2 门禁台账） |
| 12 | `?? workflow-out/_collab/` | 不入库/归档 | 沿 R1-C5 归档建议 |
| 13 | `?? workflow-out/_commit-plan.md` | R3-C6 | 移列（本文件最终态） |
| 14 | `?? workflow-out/_implementation-prev-r1-backup.md` | 不入库 | 自保备份 artifact |
| 15 | `?? workflow-out/_implementation-prev-r2-backup.md` | 不入库 | 自保备份 artifact |
| 16 | `?? workflow-out/_implementation-prev-w1a-backup.md` | 不入库 | 自保备份 artifact |
| 17 | `?? workflow-out/_plan-prev-r1-backup.md` | 归档 | 方案逐阶段备份 |
| 18 | `?? workflow-out/_plan-prev-r2-backup.md` | 归档 | 方案逐阶段备份 |
| 19 | `?? workflow-out/_plan-prev-r3-backup.md` | 归档 | 方案逐阶段备份 |
| 20 | `?? workflow-out/_plan-prev-r3t4-backup.md` | 归档 | 方案逐阶段备份 |
| 21 | `?? workflow-out/_plan-prev-r3t5t6-backup.md` | 归档 | 方案逐阶段备份 |
| 22 | `?? workflow-out/_plan-prev-w1b2-backup.md` | 归档 | 方案逐阶段备份 |
| 23 | `?? workflow-out/_plan-prev-w1b2-closure-backup.md` | 归档 | 方案逐阶段备份 |
| 24 | `?? workflow-out/_pre-task-snapshot-r1.patch` | 不入库 | R1-不入库/C5 恢复凭据 |
| 25 | `?? workflow-out/_pre-task-snapshot-r2.patch` | 不入库 | C8 恢复凭据 |
| 26 | `?? workflow-out/_pre-task-snapshot-r3.patch` | 不入库 | R3 恢复凭据（沿 C8 处置） |
| 27 | `?? workflow-out/_probe_cold_a0.md` | 归档 | 探针件（R1-C5 建议） |
| 28 | `?? workflow-out/_probe_gate_a0.md` | 归档 | 探针件（R1-C5 建议） |
| 29 | `?? workflow-out/_probe_impl_a0.md` | 归档 | 探针件（R1-C5 建议） |
| 30 | `?? workflow-out/_probe_plan_r1_a0.md` | 归档 | 探针件（R1-C5 建议） |
| 31 | `?? workflow-out/_probe_plan_r2_a0.md` | 归档 | 探针件（R1-C5 建议） |
| 32 | `?? workflow-out/_probe_plan_r3_a0.md` | 归档 | 探针件（R1-C5 建议） |
| 33 | `?? workflow-out/_r1-console-fund-raw.txt` | C4 | 已归组（C4 原始日志） |
| 34 | `?? workflow-out/_r1-console-raw.txt` | C4 | 已归组（C4 原始日志） |
| 35 | `?? workflow-out/_r1-demo-all-raw.txt` | C4 | 已归组（C4 原始日志） |
| 36 | `?? workflow-out/_r1-demo-normal-raw.txt` | C4 | 已归组（C4 原始日志） |
| 37 | `?? workflow-out/_r1-deploy-final-raw.txt` | C4 | 已归组（C4 原始日志） |
| 38 | `?? workflow-out/_r1-deploy-raw.txt` | C4 | 已归组（C4 原始日志） |
| 39 | `?? workflow-out/_r1-due-deals-raw.txt` | C4 | 已归组（C4 原始日志） |
| 40 | `?? workflow-out/_r1-final-state-raw.txt` | C4 | 已归组（C4 原始日志） |
| 41 | `?? workflow-out/_r1-g2-raw.txt` | C4 | 已归组（C4 原始日志） |
| 42 | `?? workflow-out/_r1-keeper-nudge-raw.txt` | C4 | 已归组（C4 原始日志） |
| 43 | `?? workflow-out/_r1-keeper-raw.txt` | C4 | 已归组（C4 原始日志） |
| 44 | `?? workflow-out/_r1-mock-selftest-raw.txt` | C4 | 已归组（C4 原始日志） |
| 45 | `?? workflow-out/_r1-rpc-smoke-raw.txt` | C4 | 已归组（C4 原始日志） |
| 46 | `?? workflow-out/_r2-adversarial-attempt1-raw.txt` | C7 | 已归组（C7 原始日志） |
| 47 | `?? workflow-out/_r2-adversarial-console-raw.txt` | C7 | 已归组（C7 原始日志） |
| 48 | `?? workflow-out/_r2-adversarial-raw.txt` | C7 | 已归组（C7 原始日志） |
| 49 | `?? workflow-out/_r2-assess-castcall-raw.txt` | C7 | 已归组（C7 原始日志） |
| 50 | `?? workflow-out/_r2-deploy-raw.txt` | C7 | 已归组（C7 原始日志） |
| 51 | `?? workflow-out/_r2-due-nonempty-raw.txt` | C7 | 已归组（C7 原始日志） |
| 52 | `?? workflow-out/_r2-final-state-raw.txt` | C7 | 已归组（C7 原始日志） |
| 53 | `?? workflow-out/_r2-g3a-sim-after-raw.txt` | C7 | 已归组（C7 原始日志） |
| 54 | `?? workflow-out/_r2-keeper-loop-raw.txt` | C7 | 已归组（C7 原始日志） |
| 55 | `?? workflow-out/_r2-node-all-raw.txt` | C7 | 已归组（C7 原始日志） |
| 56 | `?? workflow-out/_r2-normal-assess-raw.txt` | C7 | 已归组（C7 原始日志） |
| 57 | `?? workflow-out/_r2-t0-env-raw.txt` | C7 | 已归组（C7 原始日志） |
| 58 | `?? workflow-out/_r2-t0-frozen-baseline.txt` | C7 | 已归组（C7 原始日志） |
| 59 | `?? workflow-out/_r2-t0-sim-baseline-raw.txt` | C7 | 已归组（C7 原始日志） |
| 60 | `?? workflow-out/_r2-t7-regression-raw.txt` | C7 | 已归组（C7 原始日志） |
| 61 | `?? workflow-out/_r3-t1-node234-channel-raw.txt` | R3-C6 | T1 原始日志 |
| 62 | `?? workflow-out/_r3-t1-nodeinfo-raw.txt` | R3-C6 | T1 原始日志 |
| 63 | `?? workflow-out/_r3-t1-target-raw.txt` | R3-C6 | T1 原始日志 |
| 64 | `?? workflow-out/_r3-t1-th2-console.txt` | R3-C6 | T1 原始日志 |
| 65 | `?? workflow-out/_r3-t1-th2-raw.txt` | R3-C6 | T1 原始日志 |
| 66 | `?? workflow-out/_r3-t1-th4-console.txt` | R3-C6 | T1 原始日志 |
| 67 | `?? workflow-out/_r3-t1-th4-raw.txt` | R3-C6 | T1 原始日志 |
| 68 | `?? workflow-out/_r3-t3-committee-raw.txt` | R3-C6 | T3 原始日志 |
| 69 | `?? workflow-out/_r3-t3-console-raw.txt` | R3-C6 | T3 原始日志 |
| 70 | `?? workflow-out/_r3-t3-deploy-raw.txt` | R3-C6 | T3 原始日志 |
| 71 | `?? workflow-out/_r3-t3-final-state-raw.txt` | R3-C6 | T3 原始日志 |
| 72 | `?? workflow-out/_r3-t4-baseline-md5.txt` | R3-C6 | T4 原始日志/留证件 |
| 73 | `?? workflow-out/_r3-t4-build-raw.txt` | R3-C6 | T4 原始日志/留证件 |
| 74 | `?? workflow-out/_r3-t4-code-size-raw.txt` | R3-C6 | T4 原始日志/留证件 |
| 75 | `?? workflow-out/_r3-t4-evidence-recheck-raw.txt` | R3-C6 | T4 原始日志/留证件 |
| 76 | `?? workflow-out/_r3-t4-flows-raw.txt` | R3-C6 | T4 原始日志/留证件 |
| 77 | `?? workflow-out/_r3-t4-gas-raw.txt` | R3-C6 | T4 原始日志/留证件 |
| 78 | `?? workflow-out/_r3-t4-lyquid-scan-raw.txt` | R3-C6 | T4 原始日志/留证件 |
| 79 | `?? workflow-out/_r3-t4-md5-raw.txt` | R3-C6 | T4 原始日志/留证件 |
| 80 | `?? workflow-out/_r3-t4-precheck-raw.txt` | R3-C6 | T4 原始日志/留证件 |
| 81 | `?? workflow-out/_r3-t4-run1-superseded-flows-raw.txt` | R3-C6 | T4 原始日志/留证件 |
| 82 | `?? workflow-out/_r3-t4-run1-superseded-gas-raw.txt` | R3-C6 | T4 原始日志/留证件 |
| 83 | `?? workflow-out/_r3-t4-run2-superseded-flows-raw.txt` | R3-C6 | T4 原始日志/留证件 |
| 84 | `?? workflow-out/_r3-t4-run2-superseded-gas-raw.txt` | R3-C6 | T4 原始日志/留证件 |
| 85 | `?? workflow-out/_r3-t6-regression-raw.txt` | R3-C6 | T6 回归实录（本轮新建） |
| 86 | `?? workflow-out/_w1b1-deploy-zz2jue.txt` | 归档 | W1-A/W1-B 轮存档（R1-C5 建议） |
| 87 | `?? workflow-out/_w1b1-r1-submodule-state-check.txt` | 归档 | W1-A/W1-B 轮存档（R1-C5 建议） |
| 88 | `?? workflow-out/_w1b1-setupdevnet-bootstrap.log` | 归档 | W1-A/W1-B 轮存档（R1-C5 建议） |
| 89 | `?? workflow-out/r3-t4-contrast-report.md` | R3-C6 | T4 四维对照报告 |
| 90 | `?? workflow-out/w1b2-r1-demo-normal.md` | C4 | 已归组（C4 证据文档） |
| 91 | `?? workflow-out/w1b2-r1-demo-timeout.md` | C4 | 已归组（C4 证据文档） |
| 92 | `?? workflow-out/w1b2-r1-s3-assess.md` | C4 | 已归组（C4 证据文档） |
| 93 | `?? workflow-out/w1b2-r2-adversarial.md` | C7 | 已归组（C7 证据文档） |
| 94 | `?? workflow-out/w1b2-r2-keeper-timeout.md` | C7 | 已归组（C7 证据文档） |
| 95 | `?? workflow-out/w1b2-r2-normal-assess.md` | C7 | 已归组（C7 证据文档） |
| 96 | `?? workflow-out/w1b2-r3-e2-committee.md` | R3-C6 | T1+T3 证据文档 |

> 说明：`M` 行的归组以**最终提交组**为准；多轮共改文件（`lib.rs` / `rpc.py` / `demo.py`）
> 在备注里给出必须按序拆分的组。`?? <目录>/` 一行覆盖目录内全部新文件（`experiments/` 3 件、
> `docs/b3-user-test/` 3 件），逐文件清单见上方各组「文件」段。

**再次声明：本节（§6）与 §6.1 均为建议，本任务未执行 `git commit` / `git add` / `git push`；
`git log --oneline -1` 仍为 `dc78d2f`。**
