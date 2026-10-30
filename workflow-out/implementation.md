# R3 实现说明（编码员，2026-10-30）

> 方案：`workflow-out/plan.md`（独立终裁官定稿；§0 冻结条款 1–6 = 编码基线，正文带
> 「仲裁 R1#x/R2#x」的条款全部保留）。执行基线 = 交付前工作树（含 R1/R2 **未提交**
> 改动，**零回退**）。
> 本文件按轮重建；R2 版已原样备份为 `_implementation-prev-r2-backup.md`
> （md5 `ce21660c59b7d28c140474f8d5c78bcf`，自保 artifact，不入方案清单）。
> **分节纪律**：§1 = R1/R2 已审改动（引用 `_commit-plan.md`，不重述，本轮零回退）；
> **§2 = R3 新增改动（审查焦点）**；§3 门禁总表（R3 口径 + 本轮实际执行状态）；
> §4 命令与输出摘要（全部实跑）；§5 偏离与事实修正；§6 未尽清单。
>
> **本轮任务边界（如实声明）**：本任务 = **代码改动 + 本文件**（即 T2 的写码部分）。
> T1 平台探针梯子、T3 E2 演示实录、T4 对照实验跑数、T5 B3 文档、T6 回归收尾 **不在
> 本任务内**；§3 对它们一律标「未执行」，**不预填任何运行结果**。已实跑的是构建/静态
> 类验证：容器 `cargo check`、`forge build`、`py_compile`、sim 逐字 diff、冻结 md5、
> 恢复快照可逆性。

---

## 0. 基线、环境与恢复凭据

| 项 | 值 / 证据（本轮实跑，见 §4） |
|---|---|
| HEAD | `dc78d2f`（W1-B2 收尾提交） |
| 工作树 | R1/R2 未提交改动 + R3 改动（3 个 M 源文件 + 1 个新模块 + experiments/ + 文档） |
| 冻结基线 | `_r2-t0-frozen-baseline.txt`；本轮复核 `md5sum` 四文件 **全 OK**（types/core/committee/assessor） |
| 冻结门 | `git diff --stat lyquid/src/{types,core,committee}.rs` **空**；`assessor.rs` 对 HEAD 仍 `5 0`（R1 已审，持续在场，严禁回退） |
| devnet | `docker ps`：7 容器 Up（multi-tools / node1-4 / registry / anvil） |
| 宿主 | Python 3.14.5（`python --version`）；Git Bash |
| 容器工具链 | cast/forge **1.7.1**（`cast --version` / `forge --version`）；jq、python3 在位 |
| selector（实取） | `cast sig`：`e2_arm(string)`=0x8b7acf91、`e2_run_verdict_round()`=0x368e198c、`e2_net_config()`=0x2b5d6a4a、`e2_configure(bytes32[],uint16)`=0xcd9cc3c8（仅存档，不入 `_ABI`） |
| NodeID ×4（实取） | `get_node_ids()`：node1..4 的 NodeID 显示串 + bytes32，**与 S2 §1 逐字节一致**（如 node1 `0xa9373057…98fe`） |
| TARGET 形态 | `shaker to-hex Lyquid-tldda6zq…` → `0x9aC6307B3019C01d2878911E285efFDD2ACdcAf9`（≠ R2 合约 `0xFD6F…c351`）——只读命令实测，仅作形态证据 |
| 恢复凭据 | `workflow-out/_pre-task-snapshot-r3.patch`（51667 bytes / 19 hunks，仲裁修订后重生成；真实语义见 §5-1；逆向可 apply 校验通过） |

## 1. R1/R2 已审改动（本轮零回退）

| 文件 | R1/R2 内容（提交组） | R3 处置 |
|---|---|---|
| `lyquid/src/lib.rs` | `assess_brief` 7→4 string（C1）；`open_dispute`/`apply_committee_verdict` eth 导出 + 扁平 wire + apply_verdict println（C5） | **同文件追加** R3 改动（§2.1）；R1/R2 段落逐字保留（只更新指向新 helper 的注记） |
| `lyquid/src/assessor.rs` | `DealBrief` derive（C1，对 HEAD `+5`） | **零触碰**（md5 = T0 基线；在场要求不变） |
| `agents/common/rpc.py` | 角色表/nudge/discover/assess（C2）；`_ABI` 新行 + 编解码器两处修正（C6） | **同文件追加** R3 面（§2.3）；R2 修正逐字保留 |
| `scripts/demo.py` | node 身份/发送方矩阵、读回重试、对抗流上链（C2/C6） | **同文件追加** `flow_committee` 与 `--instance`（§2.4）；`--flow all` 序列与 sim 路径零改动 |
| `scripts/keeper.py` | `--deals` 可选 + `--nudge`（C2） | **零改动** |
| `README.md` | SPIKE W1-4 移除（C3） | **零改动**（方案默认不动 README；状态行更新属可选偏离，未做） |
| `workflow-out/plan.md` | 本方案 | 零改动 |

## 2. R3 新增改动（逐文件，审查焦点）

### 2.1 `lyquid/src/lib.rs`（6 处）

1. **模块头 R3 段**（lib.rs:49-58）：路线② 定位（`committee_certified` = 认证回调接线）、
   helper 单点、`e2_armed_deal` 的共识传递、**「cert 门控的资金路径，不是 probe 类
   SPIKE 例外」**、指向模块头 E2 门禁表。
2. **`state!` 两字段**（lib.rs:119/124）：
   - `network oracle cert_verdict;`（E2 认证主题；先例 `cert_probe` lib.rs:110，
     price-feed:167 声明形态；子模块不能自带 `state!`）；
   - `network e2_armed_deal: String = String::new();`（arming：共识持久、全节点可见；
     未 arm = 空串，propose fail-closed）。
3. **模块声明**（lib.rs:67）：`pub mod committee_certified;`。
4. **ACCESS_MATRIX 审计面注记**（lib.rs:193-194，一行指向）：certified 回调不入矩阵
   （cert 即认证、origin=ZERO 过不了地址门）；门禁台账见模块头 E2 表。**矩阵本体零增删**
   （12 条条目不变，仍保持「每行一个 require 地址门」单点语义）。
5. **通道注记块 R3 段**（lib.rs:264-270）：e2_configure = cast send（编码器零扩展，
   终裁条款 1）；e2_arm/e2_net_config = NodeClient eth 收发；e2_run_verdict_round =
   cast call（严禁 cast send）。
6. **行为保持重构（仲裁 R1#3 / 风险 R7）**：
   - `apply_committee_verdict`（lib.rs:520）保留扁平 wire `(string,uint8,string[])` +
     `require(Access::Committee)` + caller∈signers 检查，其后**整段**改为
     `apply_cert_and_payout(state, deal_id, cert)`；
   - 新增 `pub(crate) fn apply_cert_and_payout`（lib.rs:746）：**成员/阈值读取 →
     evidence 读取 → into_domain → misconduct 镜像桥接 → core::apply_verdict → 写回 →
     apply_payout → println 视图**，逐字搬移（含注释）。`pub(crate)` 是跨模块可见性的
     最小化（方案写「私有 helper」，模块外不可见、方法面不变，见 §5-3）。
   - 行为保持判据 = G2 sim 零回退（本轮已证 IDENTICAL）+ G3 对抗流复跑（T3，未执行）。

### 2.2 `lyquid/src/committee_certified.rs`（新建，433 行）

顶层壳模块（不入 `probe/`：该目录注记明言 W1-B1 SPIKE、W2 移除，`probe/mod.rs:17-18`）。
**E2 门禁台账在模块头**（:28 起，7 方法 × 面 × 实际门 × 是否触资金）。

| 方法 | 行 | 属性 / 面 | 实现要点 |
|---|---|---|---|
| `e2_configure` | :113 | `network(export=eth, eth_guard=creator)` | 镜像 `probe_configure`，落 `cert_verdict` staging；额外 fail-closed：空委员会/`threshold==0` 拒绝（§5-4） |
| `e2_arm` | :161 | `network(export=eth, eth_guard=creator)` | 写 network `e2_armed_deal`；空串拒绝；println 回显（仅 transcript 佐证） |
| `e2_net_config` | :192 | `network(export=eth)`，**`ctx: &_` 只读形** | JSON dump：`armed_deal` + current/staging(threshold,committee,epoch) + `get_epoch` + dest(epoch,change_count)；`fetch_oracle_info("cert_verdict",…)` 口径。**签名与返回类型：`pub fn e2_net_config(ctx: &_) -> LyquidResult<String>`，`_ABI` 返回面 = `string`——属新增 R3 面、非偏离**（终裁条款 2；先例 deal_info）。只读形理由见 §5-2 |
| `propose` | :239 | `instance(group = oracle::two_phase::cert_verdict)`（**字面名**） | 读 network `e2_armed_deal` + `evidence_log` + `deals`；`committee::check_evidence_shape` 派生 verdict（0/1）；fail-closed：未 arm/无 deal/非 Disputed → Err |
| `aggregate` | :289 | `instance(group = oracle::two_phase::cert_verdict)`（**字面名**） | `inputs < avg_num` → None；**提案不一致 → None（拒证）**；无可解码提案 → None；一致 → `CertifiedCallParams{ origin: ZERO, method: "committee_verdict_certified", input: encode_by_fields!(deal_id, verdict_code), target }` |
| `committee_verdict_certified` | :355 | `network(group = oracle::certified::cert_verdict::two_phase)` | `ctx.cert.signers`（RAW u32）→ `ctx.signer_node_id` 逐节点映射为 NodeID 串（未映射者剔除，不猜身份）→ `CommitteeCertWire` → **`crate::apply_cert_and_payout`**。**这是 cert 门控的资金路径**（共享 helper → `apply_payout`（lib.rs:712）→ `credit`（lib.rs:688）真实结算）；**不是** probe 类「SPIKE 例外/非生产面」（probe 零资金且 W2 移除） |
| `e2_run_verdict_round` | :401 | `instance(export = eth)` | 镜像 `probe_run_round`；`E2_AVG_NUM = 4`（编码期常量，:91）；`propose_and_certify` + `submit_certified_call!`；返回 false = 未激活/拒证 |

设计要点（与方案逐条对应）：
- **arming 决策**（§3.2-B）：init 只携带 price-feed 已证的 `avg_num`/`target`，待裁对象走
  共识状态 → 规避「init 第三字段不可解码」风险 R2；
- **每节点独立检视**（§3.2-C）：verdict 由链上证据派生（shape 成立=0，不成立=1），非脚本喂值；
- **cert 门禁**（§3.2-E）：认证回调 origin=ZERO，地址门必然 fail-closed；实质门禁
  = `core::validate_cert` 四查（成员/去重/阈值/evidence_root），`committee_members` 中配置的
  正是真实 NodeID 串 → 伪造 signers 过不了成员检查；
- **只读边界**：本模块只读 escrow 状态，唯一 escrow 写路径是回调经 helper 的裁决结算。

### 2.3 `agents/common/rpc.py`（+约 270 行）

1. **模块 docstring** R3 段（:37-46）：三条新面（get_node_ids / docker_exec(_cast) /
   `_ABI` 三行）与「e2_configure 无此行」的口径。
2. **`_ABI` 三行**（:148-150，selector 容器内 `cast sig` 实取冻结）：
   `e2_arm(string)`→`8b7acf91` bool；`e2_run_verdict_round()`→`368e198c` bool；
   `e2_net_config()`→`2b5d6a4a` **string**。**e2_configure 不入表**（排除注记 :158-162）。
3. **编码器覆盖注记**（:188-190）：「仍无 bytes32/bytes32[]（e2_configure 走 cast 通道，
   编码器零扩展 = 终裁冻结条款 1）」。**编码器零改动**（`_enc_value`/`_is_dynamic`/
   `_decode_ret` 逐字未动）。
4. **容器通道助手**（:282-413）：`docker_exec(*argv, timeout, check)`（`MSYS_NO_PATHCONV=1`
   子进程、文本捕获、失败抛原文；**超时语义**：`check=False` 时把 `TimeoutExpired` 转成
   `CompletedProcess(rc=124, stdout=<已捕获输出>)`——`shaker console` 是流式命令，与宿主
   `timeout 60 docker exec …` 先例同语义；`check=True` 则抛 RuntimeError）、
   `docker_exec_cast(*args)`、`_cast_bool`、
   `shaker_to_hex(instance)`、`shaker_console(instance, endpoint=ws://node1:10087/ws)`
   （check=False：`timeout` 收尾 rc=124 属正常）。
5. **四端点 NodeID**（:364-404）：`node_id_to_bytes32`（demo.sh:199-212 换算段镜像，
   35 字节校验）与 `get_node_ids()`（宿主 urllib POST GetNodeInfo ×4；任一端口不可达即抛，
   fail-closed）。
6. **NodeClient R3 包装**（:660-750）：`e2_arm`（`_send`）、`e2_net_config`（`_view` 解码
   JSON）、`e2_configure_cast`（cast send，字节数组 + anvil#0 钥）、
   `e2_run_verdict_round`（**cast call**）、`oracle_advance_epoch`/`oracle_finalize_epoch`/
   `oracle_dest_epoch_info`/`oracle_dest_epoch`（平台内置，占 cast call 通道）。
   常量：`NODE_PORTS=(10087,11087,12087,13087)`、`CONTAINER=multi-tools`、
   `DEFAULT_RPC_URL=http://node1:10087/api`、`ANVIL0_KEY`（devnet 公开确定性密钥，
   仅出现在容器 cast send 命令行；docstring 的「Python 侧从不持有私钥」仍描述 eth JSON-RPC 写通道）。

### 2.4 `scripts/demo.py`（+约 270 行）

1. **`flow_committee`（:552-717，node-only）**：按 plan §3.6 的 1–7 步——
   env 断言（docker/cast 可用 + **TARGET = `shaker to-hex <实例名>`，断言非零且
   ≠ `--contract`**，:583 区）→ `get_node_ids()` ×4 → **自身**发
   `committee_config(NodeID×4, 4)`（:595，在断言之后）+ `e2_configure_cast(bytes32×4, 4)`
   （cast send）→ `advance`(cast call) → `_wait_dest_epoch`（dest 面轮询，P5）→
   `finalize`(cast call) → `e2_net_config` 打印 → 争议单（faucet + `require_funds` +
   create/fund + 无交付 + dispute）→ `e2_arm` **一次**（:645）+ 读回纪律（见下）→
   `e2_run_verdict_round()` **node1 单次（cast call）** → 终态读回纪律（见下）+
   余额勾稽（alice 净 0、bob/broker 不变）+ console 取证段（**取证源 node1**，
   grep `e2_configure/e2_net_config/e2_arm/e2_propose/e2_aggregate/e2_run_verdict_round/
   committee_verdict_certified/apply_verdict` 行）+ 终态摘要。
   sim 调用即 `SystemExit`（明确报错）；未给 `--instance` 亦 `SystemExit`（fail-closed）。
2. **`wait_for(node, predicate, timeout_s, interval_s, *, what)`（:147，仲裁修订 3）**：
   读回轮询 helper，**间隔递增 1s→2s→4s（cap 4s）**（R5 口径：内层 certified call 晚块
   上链 + 4 节点 validate 轮有耗时，固定 0.4s×5 的 `READ_BACK_ATTEMPTS` 不够）。
   `predicate()` 返回 `(done, value)`，可抛异常立即 abort；超时 RuntimeError 带 last value
   并注明「still pending, not a mismatch」——**pending 与硬失配两类失败语义可区分**。
   两处调用：
   - **arm 读回**（:645-662）：记 `pre_arm` → `e2_arm` 一次 → 轮询 `e2_net_config`
     至 `armed_deal == deal_id`（预算 15s）；空/仍等于 `pre_arm` = pending 继续等；
     第三种值 = 硬失配**立即 abort**；**绝不重复 `e2_arm`**（plan §3.6-5「一次」）。
   - **终态**（:675-687）：轮询 `deal_info` 至 `Refunded`（预算 30s，覆盖 certified call
     晚块 + 4 节点 validate 轮）；停在 `Disputed` = pending 继续等；其他终态（如
     `Settled`）或超时才 abort；**绝不重触发 `run_round`**（单次纪律不变）。
3. **`--instance` 参数**（:730）与常量 `DEFAULT_INSTANCE = ""`（:87）：
   **T3 deploy 实录回填点**（plan §0-#4/§3.6-7；形态先例 `_r1-deploy-raw.txt:423-424`）。
   回填前 committee 流 fail-closed。
4. **`--flow` choices 增 "committee"**（:733）；`flows` 字典增 `committee`（:768）；
   **`--flow all` 序列仍为 `["normal","timeout","adversarial"]`**（:769-773，committee 带
   oracle 配置/activation 副作用，不进 all——G2 逐字门前提）。
5. **main() fail-closed 门控（:764-767，仲裁修订 1）**：默认（地址制）
   `committee_config` 由 `if args.flow != "committee":` 包住——`--flow committee` 跳过，
   改由 `flow_committee` 在 env/TARGET 断言**之后**自置 NodeID 制成员/阈值（plan
   §3.6「先断言后写」序；已核 flow_committee 不依赖该地址制集）。`FakeNode.committee_config`
   静默，故 sim 字面零变化（`--flow all` 仍走本行；`--flow committee --sim` 仍在
   :566-568 退出——node-only 检查在 `--instance` 检查之前）。修复前旧序会在 `--instance` 校验前先发一笔 committee_config tx
   （见 §5-12 的勘误与重录实录）。
6. 常量：`E2_TOPIC="cert_verdict"`、`E2_THRESHOLD=4`（:81；阈值是调用参数，改值不需重部署；
   `avg_num` 才是编码期常量）。

### 2.5 `experiments/evm-contrast/`（新建 3 文件，**不在 lyquid/ 冻结树内**）

- **`Escrow.sol`（407 行）**：纯 EVM 最小对照——建单/托管、notarize（msg.sender 自署）、
  交付/完成、`claimTimeout`（block.timestamp）、`cancel`、`openDispute`、
  `committeeConfig(address[],uint256)`（deployer 门）、
  **`applyVerdict(uint256,uint8,bytes[])` = 自建 k-of-n ECRECOVER**（每 sig 对
  `verdictDigest = keccak256(abi.encode(dealId, verdictCode, evidenceRoot))` 原始签名；
  ecrecover ∈ 成员 + 去重 + ≥ threshold；EIP-2 low-s 防护）、
  `evidenceRoot` = 顺序敏感 keccak 链折叠（含位置；语义对齐 core.rs:225-231，算法族不同）；
  裁决效果 = Fulfilled→Settled 分账 / 其余→全额退款 / `code>=2` → misconduct+1。
  数据采集面：`dealInfo/rolesOf/amountOf/stateOf/deadline/evidenceCount/committeeSize`。
  诚实边界写在合约头注释（委员会由 deployer 地址表承载、签名聚合自建、时间域差异）。
- **`foundry.toml`**：`src="."`（Escrow.sol 在工程根，plan §0-#5 路径）、out/lib、
  optimizer 开；**solc 不钉死**（容器实测解析到 Solc 0.8.37；pragma ^0.8.24）。
- **`run-contrast.sh`（171 行）**：容器内 build→deploy→committeeConfig(4,3)→
  normal→timeout（evm_increaseTime + evm_mine）→adversarial（3-of-4 签名 + NotFulfilled）
  →负向对照（同一签名集重放到另一 deal 必须失败）→`gas-raw.txt`/`report.txt`；
  头注给出宿主 `MSYS_NO_PATHCONV=1 docker cp` 引导命令（纪律同 lyquid 通道）。
  角色 = anvil #0 broker/deployer、#1 buyer、#2 seller、#3 委员会成员。

### 2.6 `workflow-out/_pre-task-snapshot-r3.patch`（新，51667 bytes / 19 hunks）

**真实语义见 §5-1**：pre-task → R3 代码态的三文件 diff（lib.rs / rpc.py / demo.py），
pre-task 侧逐文件 **md5 校验**（lib.rs `a8fdcf06…` 与 `_r2-deploy-raw.txt` 的 R2 部署 md5 一致；
rpc.py `a9443231…`、demo.py `25bfeae5…` 与任务开始时宿主 `md5sum` 一致）。
`git apply -R --check` 通过 = 可把本 patch 逆向还原到 R3 前代码态。

## 3. 门禁总表（R3 口径 + 本轮执行状态）

| 门 | 判据（方案） | 本轮状态 | 依据 |
|---|---|---|---|
| **G0** | 快照存在；四文件 md5 全 OK；sim 基线入档；40/40 入档；七容器 Up | **部分**：快照（语义见 §5-1）✓、md5 四 OK ✓、sim 基线 diff IDENTICAL ✓、七容器 ✓；**壳 40/40 未跑**（壳在仓库外、`lib.rs` 不挂载壳，非本任务） | §4-1/2/7 |
| **G1** | T1 三份日志 + 分级结论表（L2/L1/L0） | **未执行**（T1 阶段） | — |
| **G2** | 容器 `cargo check` 零 error（md5 勾稽在档）；40/40；sim diff **IDENTICAL**；冻结门（三文件 diff 空 + 四文件 md5 OK + assessor +5 在场） | **代码侧子集已过**：`cargo check --target wasm32-unknown-unknown` **rc=0**（`Finished`，33 warnings，新模块仅 7 条 `unused doc comment`＝与 probe 同类的宏注释告警）；sim `--flow all` 与 T0 基线 **IDENTICAL**；三文件 diff 空；四文件 md5 全 OK；assessor `5 0` 在场；**release cdylib 构建成功**（`trustbridge.wasm`）。**壳 40/40 未跑** | §4-3/4b/7/8 |
| **G3** | committee transcript（console 取证源 node1、`--instance` 实例名、signers 映射真实节点、L2 判据 inputs=4+signers=4、TARGET 断言、arm 读回断言、终态 Refunded、余额勾稽、对抗流复跑） | **未执行**（T3 阶段；`DEFAULT_INSTANCE` 待 T3 回填） | — |
| **G4** | Escrow 部署收据 + 三流 + 四维数据 + 报告 | **未执行**（T4 阶段）；本轮仅 `forge build` 成功 + 脚本 `bash -n` | §4-6/9 |
| **G5** | B3 三文档 + 命令与实录一致 | **已交付（R3-T5，2026-10-30）**：三文档在 `docs/b3-user-test/`（操作手册 / 通过判据 / 反馈收集表），命令与预期输出回填自 `_r3-t3-*` 归档实录，修复后新增行标「无已档实录」；**（原状态：未执行 / T5 阶段）** | §9、plan §3-T5.1–T5.3 |
| **G6** | 回归三件套 + `_commit-plan` R3 组 + implementation.md 分节；**未执行任何 git commit** | **已跑（R3-T6，2026-10-30）**：壳 40/40（宿主通道 33+5+2）+ sim `--flow all` 与 T0 基线 IDENTICAL + 冻结门 4×OK；`_commit-plan.md` §6 R3 分组与覆盖表已增补；实现说明已合并（5.13 + §9）；**未执行任何 git commit/add/push**（全程）；**（原状态：部分 / 回归三件套待 T6）** | §9、`_r3-t6-regression-raw.txt` |

## 4. 命令与输出摘要（本轮实跑，全部为构建/静态类验证）

```
# 1) 冻结文件 md5（对 _r2-t0-frozen-baseline.txt）
$ md5sum lyquid/src/{types,core,committee,assessor}.rs
f33e334a… *types.rs   4ae54a47… *core.rs   c5f660a1… *committee.rs   4df7cda6… *assessor.rs   → 全 OK
$ git diff --stat lyquid/src/{types,core,committee}.rs   → 空
$ git diff --numstat lyquid/src/assessor.rs              → 5  0（R1 在场）

# 2) 环境
$ docker ps        → 7 容器 Up（multi-tools/node1-4/registry/anvil）
$ python --version → Python 3.14.5
$ docker exec multi-tools cast --version  → cast Version: 1.7.1
$ docker exec multi-tools forge --version → forge Version: 1.7.1

# 3) selector 实取（容器内）
$ for s in "e2_arm(string)" "e2_run_verdict_round()" "e2_net_config()" "e2_configure(bytes32[],uint16)"; do cast sig "$s"; done
  → 0x8b7acf91 / 0x368e198c / 0x2b5d6a4a / 0xcd9cc3c8

# 4) 新建模块 + lib.rs 的编译门（容器内，强制重编）
$ MSYS_NO_PATHCONV=1 docker exec multi-tools rm -rf /tmp/tb-r3-check
$ MSYS_NO_PATHCONV=1 docker cp lyquid/. multi-tools:/tmp/tb-r3-check
$ MSYS_NO_PATHCONV=1 docker exec -w /tmp/tb-r3-check multi-tools sh -c "touch src/*.rs src/probe/*.rs && cargo check --target wasm32-unknown-unknown"
  → Compiling trustbridge v0.1.0 … Finished dev profile in 27.95s（全新副本全量重编；增量复跑 1.4–1.8s）  （rc=0，零 error）
  （唯一的 “error:” 文本 = ldk git checkout 内 lyquid-template 的 `{{project-name}}`
   提示，R2 部署日志同款、非本 crate 编译错误，构建继续并成功）

# 4b) release cdylib 构建（比 check 更严：含代码生成/链接/ABI 导出生成）
$ MSYS_NO_PATHCONV=1 docker exec -w /tmp/tb-r3-build multi-tools sh -c "touch src/*.rs src/probe/*.rs && cargo build --release --target wasm32-unknown-unknown"
  → Finished `release` profile [optimized] in 31.49s（rc=0，零 error）
  → artifacts: trustbridge.wasm 1,085,891 B；libtrustbridge.rlib

# 5) Python 静态门
$ python -m py_compile agents/common/rpc.py scripts/demo.py           → OK
$ python scripts/demo.py --selftest                                   → 7 PASS，SELFTEST OK
$ python scripts/demo.py --sim --flow all > /tmp/r3-sim-after.txt
$ diff -u workflow-out/_r2-t0-sim-baseline-raw.txt /tmp/r3-sim-after.txt → 无输出（IDENTICAL）
$ python scripts/demo.py --sim --flow committee
  → "[committee] node-only flow: FakeNode has no oracle certification round …"（rc=1）
$ B0=$(python -c "from agents.common.rpc import NodeClient; print(NodeClient('http://127.0.0.1:10087', contract='0xFD6F…c351').block_number())")
$ python scripts/demo.py --node http://127.0.0.1:10087 --contract 0x0000000000000000000000000000000000000000 --flow committee
  → "FLOW 4 — committee: 4-node oracle certification (route ②, E2)" +
    "[committee] --instance <Lyquid-…> is required: shaker console / to-hex take the instance NAME …"
  → rc=1
$ B1=$(同上 block_number)      → block_before=318，block_after=318（**不变 = 零交易**）
  （仲裁修订 1 修复后重录：跳过 main() 默认 committee_config，故 SystemExit 前无任何 tx；
   修复前旧序会先发一笔 committee_config tx —— 见 §5-12）

# 6) EVM 对照工程构建（容器内）
$ MSYS_NO_PATHCONV=1 docker cp experiments/evm-contrast/. multi-tools:/tmp/tb-evm
$ MSYS_NO_PATHCONV=1 docker exec -w /tmp/tb-evm multi-tools forge build
  → Compiling 1 files with Solc 0.8.37 … Compiler run successful!
  （仅 2 条 block-timestamp lint 告警——对照报告须把它写成「时间源信任差异」）

# 7) 四端点 NodeID 与 bytes32（宿主直连，实跑）
$ python -c "from agents.common import rpc; print(rpc.get_node_ids())"
  node1 Node-ve3tav5… → 0xa9373057…98fe ; node2 → 0x4eca21e3…5d7b ;
  node3 → 0xd15cb394…b9eb ; node4 → 0x7434b144…b0fe     （与 w1b1-s2-oracle.md §1 逐字节一致）

# 8) TARGET 形态（只读命令）
$ docker exec multi-tools shaker to-hex Lyquid-tldda6zq… → 0x9aC6307B…DCdcAf9（42 字符）

# 9) 脚本语法
$ bash -n experiments/evm-contrast/run-contrast.sh → BASH_SYNTAX_OK

# 9b) 容器助手超时语义 + console 通道（实跑）
$ python: docker_exec("sh","-c","echo hello; sleep 5", timeout=1.5, check=False)
  → rc=124, stdout='hello\n', elapsed=1.53；同一命令 check=True → RuntimeError（含 stdout 原文）
$ python: shaker_console("Lyquid-tldda6zq…", timeout=8.0)
  → rc=124, elapsed=8.0, stdout 305 行（console 历史回放可达 → 取证段可用）
$ python: shaker_to_hex("Lyquid-tldda6zq…") → 0x9aC6307B…DCdcAf9

# 10) ABI 编解码面（纯本地）
$ python: _ABI e2 三行 = 8b7acf91/368e198c/2b5d6a4a；_sig_types("e2_run_verdict_round()") = ()；
  string 返回解码 round-trip = {"armed_deal":"deal-1",…}

# 11) 恢复快照可逆性
$ git apply -R --check -p1 workflow-out/_pre-task-snapshot-r3.patch → OK（19 hunks；仲裁修订后重生成）

# 12) git 状态
$ git log --oneline -1 → dc78d2f；全程未执行 git add/commit/push

# 13) 仲裁修订后复跑（2026-10-30，本轮修订的验收）
$ python -m py_compile agents/common/rpc.py scripts/demo.py            → OK
$ python scripts/demo.py --selftest                                    → 7 PASS，SELFTEST OK
$ python scripts/demo.py --sim --flow all … + diff 对 T0 基线          → IDENTICAL
$ python scripts/demo.py --sim --flow committee                        → node-only SystemExit（rc=1）
$ 无 --instance node 探针（§4-5 重录）                                  → rc=1，eth_blockNumber 318→318（零交易）
$ wait_for 语义自检（importlib 载入 demo.py，纯本地 predicate，无网络/无链写）：
  cadence  → gaps=[1.0, 2.0]s（再下一次 4.0，cap 4s），total=3.0s
  pending  → timeout_s=1.5 精确在 1.5s 触发，消息含「still pending, not a mismatch」+ last={'state': 'Disputed'}
  mismatch → predicate 抛错即 abort，elapsed=0.0s（不等满预算）
$ git apply -R --check -p1 _pre-task-snapshot-r3.patch                 → OK（19 hunks）
```

## 5. 偏离与事实修正

1. **`_pre-task-snapshot-r3.patch` 的语义（重要，如实登记）**：方案 §0-#15 要求「T0 工作树
   快照 = `git diff` 全量」，而编码开始时工作树已含 **R1/R2 未提交改动**，且本任务在首次
   编辑前**未能**落盘当时的 `git diff`（无从取得完整 pre-task 全量 diff：`_pre-task-snapshot-r2.patch`
   只是 R2 开始时的状态，不是 R2 结束态）。替代件 = **pre-task → R3 代码态**的三文件 diff，
   pre-task 侧逐文件按**已记录 md5** 逐字校验（lib.rs `a8fdcf064f2a5d472531f545b9eea42f` =
   `_r2-deploy-raw.txt` 的 R2 部署 md5；rpc.py `a9443231…`、demo.py `25bfeae5…` = 任务开始时
  宿主 `md5sum`）。用途相同（可逆还原 R3 前的代码态），覆盖面小于方案原意（不含
  文档/README/keeper 等本轮未改文件）。
2. **`e2_net_config` 的 ctx 用只读形（`ctx: &_`）**：由 `&mut _` 改为 `&_`（ImmutableNetworkContext）。
   **不是冻结条款的偏离**——属性 `network(export = eth)`、ABI 签名 `e2_net_config()`、
   返回类型 `LyquidResult<String>` 与 `_ABI` 返回面 `string` 全部照方案；改动的只是 Rust
   形参可变性。理由：eth_call 读通道只路由**只读**方法（R2 实测 §5-4：可变 network 方法在
   eth_call 上恒 `FuncNotFound`，`&_` getter 正常路由），而终裁条款 2 / §3.2-G 要求
   arm 读回断言走 `NodeClient call("e2_net_config()")` —— 只读形是让该口径真实可用的必要
   条件。已通过容器 `cargo check`（§4-4）。
3. **helper 可见性**：`apply_cert_and_payout` 落 `pub(crate)`（方案写「私有 helper」）。
   crate 内跨模块调用所需；对 crate 外不可见，方法清单/ABI/矩阵零变化。
4. **新增 fail-closed 校验（两处，均为方案未禁止的实现细节）**：`e2_configure` 拒绝
   `threshold==0`（probe_configure 只查空委员会）；`propose` 在 armed/存在性之外还要求
   deal 处于 `Disputed`（台账已列该门）。二者只会把「必然失败」提前成显式错误，
   不改变合法路径语义。
5. **`e2_run_verdict_round` 的 `_ABI` 行与执行通道**：`_ABI` 行（`368e198c`/bool）按方案
   要求落表，但 NodeClient 包装**只走 cast call**（docker_exec_cast），不经 `_send`/`_view`
   —— 行本身承担 selector/签名面冻结与交叉核对（S2 通道纪律：cast send 内层静默丢失）。
6. **`docker_exec_cast` 与 console/to-hex 的助手命名**：方案把 advance/finalize/e2_configure/
   console 都归到 `docker_exec_cast()` 名下；实现拆为 `docker_exec_cast()`（cast 子命令）+
   同族 `docker_exec()`（`shaker to-hex`/`shaker console` 这类非 cast 命令）。同一
   `docker exec` 通道、同一 `MSYS_NO_PATHCONV=1` 纪律，行为等价。
7. **`e2_configure` 的 cast send 形态**：`cast send <contract> "e2_configure(bytes32[],uint16)" "[…]" <th> --private-key <anvil#0> --rpc-url http://node1:10087/api`，与 S2
   §2 probe_configure 同形；rpc.py 编码器**零扩展**、`_ABI` 无该行（终裁条款 1 的默认路径，
   未走「扩编码器 + cast calldata 逐字节对照」的例外路径）。
8. **sim `--flow all` 与全部 sim 路径零改动**：逐字 diff **IDENTICAL**（§4-5；新增代码只在
   node-only `flow_committee` 与 rpc.py 新增函数内，且 `--flow all` 序列未变）。
   仲裁修订后复跑仍 **IDENTICAL**（§4-13）。
9. **`_implementation-prev-r2-backup.md`**：重建本文件前对 R2 版 implementation.md 的备份
   （自保 artifact，与 `_implementation-prev-r1-backup.md` 同处置，不入方案清单）。
10. **NEW：`Escrow.sol` 的 `dealInfo` 返回值拆分**：8 返回值 + storage 指针在默认编译管线
    触发 solc `Stack too deep`（与 Lyquid 侧 solc 参数上限同族）；改为 4 返回值 + 独立
    `rolesOf/amountOf` getter（**未启用 viaIR**）。属实现细节，数据采集面完整。
11. **未执行任何 git commit / add / push**（全程；`_commit-plan.md` 未增补 R3 分组——见 §6-6）。
12. **仲裁修订（2026-10-30 采纳，3 条；被驳回的意见未改）**：
    (a) **main() fail-closed 门控**：默认（地址制）`committee_config` 现由
    `if args.flow != "committee":` 包住（demo.py:764-767）。**事实修正**：修复前
    `--node … --flow committee`（无 `--instance`）会在 `--instance` 校验前**先发一笔
    committee_config tx**，因此本文件此前 §4-5 的「零网络调用」断言在修复前
    **为假**；该句已按修复后行为**重录替换**（`eth_blockNumber` 318→318、rc=1，§4-5），
    旧断言文字不再沿用。「先断言后写」序 = plan §3.6；`--flow all` 与 sim 字面零变化
    （G2 复跑 IDENTICAL）。
    (b) **读回纪律加固（T3 前）**：新增 `wait_for(node, predicate, timeout_s, interval_s,
    *, what)`（demo.py:147，间隔递增 1s→2s→4s）；arm 读回（:645-662，预算 15s，
    空/旧值=pending、第三值=硬失配立即 abort，**绝不重复 e2_arm**）与终态 Refunded
    （:675-687，预算 30s，Disputed=pending、其他态/超时 abort，**绝不重触发 run_round**）
    均改走该 helper；超时消息注明「still pending, not a mismatch」，与硬失配两语义可区分。
    (c) `flow_committee` 在 env/TARGET 断言之后**自行**发 NodeID 制 `committee_config`
    （:595），不再依赖 main() 的地址制集。

### 5.13 R3 各阶段偏离总表（R3-T5+T6 合并；索引性质，原文不搬移、不删改）

> 构成 = T2 期 §5 的 12 条 + T3 期 §7.3 的 2 条（D-T3-1/D-T3-2）+ T4 期 §8.4 的 7 条
> （D-T4-1..7）= 21 条既有，加本轮新增 2 条（D-T5-1 / D-T6-1）= **23 条**。
> 本表只做索引：编号 + 一句话 + 原文位置指针；原文段落全部保持原位。

| # | 编号 | 一句话 | 原文位置 |
|---|---|---|---|
| 1 | §5-1 | `_pre-task-snapshot-r3.patch` 实为 pre-task→R3 三文件 diff（非全量快照），pre-task 侧按记录 md5 校验 | §5-1（:307-314） |
| 2 | §5-2 | `e2_net_config` 用只读形 `ctx: &_`（让 eth_call 读通道可用），属性/ABI/返回类型照方案 | §5-2（:315-321） |
| 3 | §5-3 | `apply_cert_and_payout` 落 `pub(crate)`（跨模块调用所需，crate 外不可见） | §5-3（:322-323） |
| 4 | §5-4 | 两处新增 fail-closed 校验：`e2_configure` 拒绝 `threshold==0`、`propose` 要求 deal 处 `Disputed` | §5-4（:324-327） |
| 5 | §5-5 | `e2_run_verdict_round` 的 `_ABI` 行只承担 selector/签名面冻结，执行只走 cast call | §5-5（:328-330） |
| 6 | §5-6 | 容器助手拆为 `docker_exec_cast()` + 同族 `docker_exec()`（同一通道同一纪律） | §5-6（:331-334） |
| 7 | §5-7 | `e2_configure` 的 cast send 形态；编码器零扩展、`_ABI` 无该行 | §5-7（:335-337） |
| 8 | §5-8 | sim `--flow all` 与全部 sim 路径零改动（逐字 diff IDENTICAL） | §5-8（:338-340） |
| 9 | §5-9 | `_implementation-prev-r2-backup.md` 为重建本文件前的自保备份（不入方案清单） | §5-9（:341-342） |
| 10 | §5-10 | `Escrow.sol` 的 `dealInfo` 拆分返回值（避 solc Stack too deep），数据采集面完整 | §5-10（:343-345） |
| 11 | §5-11 | 全程未执行任何 git commit / add / push | §5-11（:346） |
| 12 | §5-12 | 仲裁修订 3 条：main() fail-closed 门控、`wait_for` 读回纪律、flow_committee 自置 NodeID 成员 | §5-12（:347-361） |
| 13 | D-T3-1 | demo 余额断言的 stale baseline（faucet 后立即快照）——**已于 R3-T6 修复（行为修复，见 §9）** | §7.3-1（:479-484）；`w1b2-r3-e2-committee.md:106-121` |
| 14 | D-T3-2 | deploy 日志首写被 `tee /dev/stderr` 截断；已重建并标注 `[RE-RUN]`/`[QUOTED]` | §7.3-2（:485-490） |
| 15 | D-T4-1 | 同一对照实验跑了 3 次（canonical=run-3），作废轮产物另存留证 | §8.4（:570） |
| 16 | D-T4-2 | 计划外新增 5 个留证件（基线 md5 快照 + 4 个作废产物） | §8.4（:571） |
| 17 | D-T4-3 | T4.4 逐笔对拍改在容器内执行（宿主无 jq） | §8.4（:572） |
| 18 | D-T4-4 | T4.5 三个 selector 未识别，如实登记不猜名 | §8.4（:573） |
| 19 | D-T4-5 | plan 引用两处既有日志行号有偏差，报告按实际行号（:25 / :6） | §8.4（:574） |
| 20 | D-T4-6 | 「委员会成员含买卖双方」是实跑事实，不是偏离；按事实表述 | §8.4（:575） |
| 21 | D-T4-7 | T4.5 未做 Lyquid 侧跨单签名重放实验（不在 T4 范围） | §8.4（:576） |
| 22 | **D-T5-1（新）** | 全案 §5 的「演示脚本.md」不在本任务三件之列：按任务陈述交付 操作手册/通过判据/反馈收集表；动线要点并入操作手册第④节 | 本轮新增；plan §1-9 / §4-#4 |
| 23 | **D-T6-1（新）** | 壳 40/40 走**宿主通道**实跑通过（33+5+2），容器 fallback 未启用；规划期「宿主工具链损坏」前提在当前机器状态不成立 | 本轮新增；plan §1-5 / §5-R2；`_r3-t6-regression-raw.txt` T6.2 |

## 6. 未尽清单（如实列出，均非本轮可完成项）

| # | 项 | 状态 / 原因 | 去向 |
|---|---|---|---|
| 1 | T1 平台探针梯子（th2/th4 signers 聚合 + node2-4 通道面） | **未执行**（运行级，非本任务） | T1 |
| 2 | T3 E2 演示（deploy 新实例、`--flow committee`、L2/L1/L0 判定、fallback 预登记执行、对抗流复跑） | **已执行（2026-10-30）→ 判级 L2**（`inputs=4` + `signers=4`）；`DEFAULT_INSTANCE` 已回填；对抗流 node 复跑仍顺延。详见 §7。**R3-T6 补记：对抗流 node 复跑仍未执行**（本轮授权面无链写实跑，计划见 §5-R7） | T3 → §7；对抗流复跑 → 后续/用户安排 |
| 3 | T4 对照实验跑数（deploy/三流/gas）+ `w1b2-r3-evm-contrast.md` | **已执行（2026-10-30，R3-T4）→ 报告 + 四维数据在档**（`r3-t4-contrast-report.md`、§8）；原状态：未执行（仅 `forge build` 与 `bash -n` 通过） | T4 → §8 |
| 4 | T5 B3 三文档 | **已交付（2026-10-30，R3-T5）→ 三文档在 `docs/b3-user-test/`**；原状态：未执行 | T5 → §9 |
| 5 | T6 回归（壳 40/40 + sim diff + 冻结门复跑）与 `_commit-plan.md` R3 分组 | **已执行（2026-10-30，R3-T6）→ 壳 40/40（宿主通道 33+5+2）+ sim IDENTICAL + 冻结门 4×OK**；原状态：未执行（40/40 只读复跑属 T0/T6） | T6 → §9、`_r3-t6-regression-raw.txt` |
| 6 | `_commit-plan.md` R3 主题分组增补 | **已完成（R3-T6）→ §6 R3-C1..C6 + 全覆盖表**；原状态：未做（属收尾交付项，见 §3-G6） | T6 → §9、`_commit-plan.md` §6 |
| 7 | README 状态行更新 | **未做**（方案默认不动；可选偏离需单独登记） | 可选 |
| 8 | Fulfilled 加分对照单（T3 可选项） | **未做** | T3 可选 |
| 9 | 真实 LLM 端到端 | 仍无 `TB_LLM_*` 凭据（R2 结论） | W2'/W3 |
| 10 | R9（forge/solc 复现性）、R11（lyquid 侧 gas 读取通道） | 未触发/未探（T4 才需要） | T4 |
| 11 | L0 降级登记 | **未发生**：T3 首跑 console 判级 = L2（`inputs=4` + `signers=4`），无 L0/L1 分支。详见 §7 | T3 → §7 |

---

## 7. §R3-T3 执行实现说明（编码员，2026-10-30）——单次实跑 + 证据回填

> **性质与边界**：本任务 = R3-T3「E2 四节点委员会演示实跑 + §T3 回填」，方案 = `workflow-out/plan.md`。
> 执行基线 = T2 交付态（HEAD `dc78d2f`）。**唯一代码面改动 = `scripts/demo.py:87` 一行常量回填**；
> lyquid 源码零改动（`E2_AVG_NUM` 保持 4，无 L1 fallback）。
> **结论 = L2 达成**：`e2_aggregate: agreed … from 4 input(s) (avg_num=4)` + `cert.signers RAW = [0, 1, 2, 3] (len=4)`
> + 四条 signer→Node 映射。
>
> **体例说明（偏离登记，文档面）**：本文件头部约定「按轮重建」（R1/R2 期各留 `_implementation-prev-*` 备份）。
> 本轮**改为追加 §7**：原因是 plan §2 明确把 implementation.md 的增量/偏离表更新留给收尾阶段，
> 而 §1/§2 的 R3 代码面描述（仍在树内、仍是审查焦点）不应因本轮实跑而失效或重写；追加不丢任何
> 既有内容，也不需要新增备份文件（方案 §0 文件清单外）。§6 表 #2/#11 已在此同步关闭。

### 7.1 逐文件改动（本阶段，plan §0 清单对照）

| # | 路径 | 动作 | 改动摘要 |
|---|---|---|---|
| #3 | `scripts/demo.py` | 改（1 行） | :87 `DEFAULT_INSTANCE = ""` → `"Lyquid-ybidj3krshf4gqcjk3m3px6mooi6tg74twwaa"`（T3.1 deploy 实录实例名；唯一代码面改动，预登记项） |
| #4 | `workflow-out/w1b2-r3-e2-committee.md` | 改 | §T3 占位（原 :39-41「（待 T3 触发回填。）」）替换为实录段：判级结论 / console 判级摘录（原文+行号）/ 读回勾稽 5 项 / 偏离登记 D-T3-1·D-T3-2 / 原始日志清单 / GT3 a–f 自检；§T1 段落未动 |
| #5 | `workflow-out/_r3-t3-deploy-raw.txt` | 新建 | T3.0 预检 + T3.1 部署（rm/cp、md5 9/9 MATCH、cargo check Finished、shaker deploy、TARGET 推导与断言）+ T3.2 回填声明 + T3.6 收尾自检；含 D-T3-2 的「首写被截断→重建」说明与 `[RE-RUN]`/`[QUOTED]` 标注 |
| #6 | `workflow-out/_r3-t3-committee-raw.txt` | 新建 | `--flow committee` **单次**主跑全 transcript（exit=1，由 D-T3-1 的 demo 内建断言导致；未重跑） |
| #7 | `workflow-out/_r3-t3-console-raw.txt` | 新建 | `shaker console` 全量原始输出（判级唯一依据；rc=124 正常收尾） |
| #8 | `workflow-out/_r3-t3-final-state-raw.txt` | 新建 | T3.5 终态读回（deal_info/三方余额）+ 补充：blocks 0–341 全量 faucet 单次链上扫描 |
| #9–#11 | （条件项，未触发） | 未改/未建 | 无 L1 fallback：`committee_certified.rs:91` `E2_AVG_NUM` 保持 4（md5 仍 `83e358ee…`），无 `_r3-t3-fb-*` |
| — | 冻结四件 / `lib.rs` / `rpc.py` / `keeper.py` / README / `deploy.sh` 等 | 未改 | `md5sum -c _r2-t0-frozen-baseline.txt` 4×OK；`git status --short lyquid/` 与 T2 交付态逐字相同（M assessor.rs、M lib.rs、?? committee_certified.rs） |
| — | 本文件 `workflow-out/implementation.md` | 改（文档） | 追加 §7 + §6 表 #2/#11 交叉指向（见上方体例说明） |

### 7.2 命令与输出摘要（全部本轮实跑；完整原文见 §7.1 的日志件）

**T3.0 预检**
- `docker ps --format "{{.Names}} {{.Status}}"` → 7 容器 Up（multi-tools / node1-4 / registry / anvil，13–14h）
- `md5sum -c workflow-out/_r2-t0-frozen-baseline.txt` → types/core/committee/assessor **4×OK**（附已知 WARNING `1 line is improperly formatted`）`[exit=0]`
- `git diff --stat -- lyquid/src/{types,core,committee,assessor}.rs` → 仅 `assessor.rs | 5 +++++`（R1 已审在场）
- `git status --short lyquid/` → `M assessor.rs` / `M lib.rs` / `?? committee_certified.rs`

**T3.1 部署新实例**
- `docker exec multi-tools rm -rf /tmp/tb-lyquid` → exit 0；`MSYS_NO_PATHCONV=1 docker cp lyquid/. multi-tools:/tmp/tb-lyquid` → exit 0（**原始运行**；重建件中记为 `[QUOTED]`，该容器副本仍在且 md5 9/9）
- 宿主 vs 容器 `md5sum`（src/*.rs + Cargo.toml + Cargo.lock，容器侧需 `sh -c` 承载 glob）→ **9/9 MATCH**，含 `committee_certified.rs 83e358ee…`（新模块首次上容器）
- `touch src/*.rs` + `docker exec -w /tmp/tb-lyquid multi-tools cargo check --target wasm32-unknown-unknown` → 原始 `Finished dev profile … in 5.72s`（exit 0）；重建件 `[RE-RUN]` `Finished … in 1.45s`（exit 0）；唯一 `error:` = ldk 模板 `{{project-name}}` 固有噪音（R2 同款）
- `shaker deploy -r http://registry:8000/lyquids --endpoint ws://node1:10087/ws --private-key <ANVIL0_KEY> Cargo.toml` → `Finished release … 8.00s`、image `sha256:ccf7498b…`、**`created Lyquid-ybidj3krshf4gqcjk3m3px6mooi6tg74twwaa => 0x87006e75a5B6bE9D1bbF61AC8Cd84f05D9140589`**、`[deploy exit=0]`
- `docker exec multi-tools shaker to-hex Lyquid-ybidj…` → `0xc05034ED5191cbc3404956D9b7dFcC7391e99bfc`；断言**非零且 ≠ 合约地址**（条款 6）→ 通过

**T3.2 常量回填**：`demo.py:87` 一行（见 §7.1）；未触发壳 40/40 与 sim diff（Python 常量，只被 committee 流消费）。

**T3.3 主跑（单次）**
- `python scripts/demo.py --node http://127.0.0.1:10087 --contract 0x87006e75a5B6bE9D1bbF61AC8Cd84f05D9140589 --instance Lyquid-ybidj3krshf4gqcjk3m3px6mooi6tg74twwaa --flow committee` → **exit 1**
- 链上主路径全部成功：e2_configure(staged 4) → advance=true → dest_epoch 1 → finalize=true → deal-1 Disputed → `arm read-back OK: armed_deal == deal-1 (pre-arm='')` → `e2_run_verdict_round() -> True` → `final state=Refunded`
- 唯一失败点 = demo 内建余额断言 `RuntimeError: refund accounting mismatch: before={'alice': 0,…} after_fund={'alice': 9000,…} after={'alice': 10000,…}`（demo.py:694）→ **D-T3-1**（faucet 读回竞态，非链上失配）；按纪律**不重跑**

**T3.4 console 判级**
- `MSYS_NO_PATHCONV=1 timeout 60 docker exec multi-tools shaker console Lyquid-ybidj… --endpoint ws://node1:10087/ws` → `rc=124`（正常收尾）
- 判级行齐全：`agreed … from 4 input(s) (avg_num=4)`（console:24）、`cert.signers RAW = [0, 1, 2, 3] (len=4)`（:31）、`signer N -> Node-…` ×4（:32-35）、`apply_verdict … misconduct=[]`（:36）、`deal_info … "state":"Refunded"`（:38）
- **判级 = L2**（无需 fallback，未改 `E2_AVG_NUM`、未重部署）

**T3.5 终态勾稽（独立于 transcript）**
- `NodeClient` 只读快照（block 341）：`deal_info(deal-1).state=Refunded`；`balance_of` alice=10000 / bob=0 / broker=0；`evidence_entries=3`；`e2_net_config.armed_deal="deal-1"`
- 补充链上扫描（blocks 0–341 全量 tx）：`faucet(string,uint128)` **仅 1 笔**（block 333，from broker，agent=alice，amount=10000）→ alice 10000 基线唯一，fund 1000 → 9000，退款 +1000 → 10000（全额退款、bob/broker 不变）
- `FINAL-STATE CHECK: PASS`（4/4 PASS）

**T3.6 收尾自检**
- `md5sum -c _r2-t0-frozen-baseline.txt` → 4×OK；`committee_certified.rs` md5 `83e358ee…`；`sed -n 91p` → `const E2_AVG_NUM: u16 = 4;`
- `git log --oneline -1` → `dc78d2f`（本阶段**未 commit/add/push**）
- 四个 `_r3-t3-*` 日志全部在 `workflow-out/`

### 7.3 偏离与发现（2 项，均已在 §T3 登记）

1. **D-T3-1（demo 代码缺陷，本阶段不修）**：`demo.py:622` faucet 后**立即** `before = snapshot()`（:623），
   读路径滞后一块使 `before[alice]=0`；:692 的 `after[alice] == before[alice]` 因而在 faucet 竞态下必然
   误报为 `refund accounting mismatch`。链上资金语义正确（T3.5 + 链上扫描独立证明）。
   **未修**（本阶段代码面授权仅 demo.py:87 一行）、**未重跑**（plan §T3.3 纪律）。
   建议（下阶段）：基线改为 faucet 落账后读回，或断言改 `after[alice] == after_fund[alice] + 1000`
   （`after_fund` 在 `wait_state(Funded)` 之后读，不受该竞态影响）。
2. **D-T3-2（deploy 日志首写被截断，已重建）**：我在 TARGET 取数用的
   `{ … } >> $LOG 2>&1` 块内含 `tee /dev/stderr`；Git Bash/MSYS 下 `tee` 按路径打开 `/dev/stderr`
   会**截断**重定向目标（已在 /tmp 最小例复现）。重建件 629 行：T3.0/md5/cargo check 为 `[RE-RUN]`
   （只读、针对同一容器副本），deploy 段为 `[QUOTED]`（原始会话输出逐字引述，**刻意不重跑 deploy**）；
   丢失的 ~460 行 warning 无决策内容，已在文件尾「TRANSCRIPT SCOPE NOTE」声明。

**观察（非偏离）**：console 中 aggregate 出现两次 `agreed`（:24/:29，同一 4 输入集重复回放），
但 `certified call submitted` / `committee_verdict_certified` / `apply_verdict` 各仅一次（:30/:31/:36）
→ 无重复结算。

### 7.4 GT3 门禁状态（对照 plan §6）

| 门 | 状态 |
|---|---|
| GT3-a | ✅ 满足（deploy 段为重建件，见 D-T3-2；关键行齐全） |
| GT3-b | ⚠️ **部分满足**：arm 读回 OK / run_round 单次 / Refunded 均在；「余额勾稽 OK」行缺失（D-T3-1 断言打断），实质由 T3.5 独立证明 |
| GT3-c | ✅ 满足（L2 判级可从 console 原文直接读出） |
| GT3-d | ✅ 满足（§T3 回填完成；偏离登记段在档） |
| GT3-e | ✅ 满足（冻结面复验 4×OK；无 fallback，40/40 不触发） |
| GT3-f | ✅ 满足（未 git commit/add/push；lyquid 源零改动） |

### 7.5 遗留（下一阶段）

| # | 项 | 去向 |
|---|---|---|
| 1 | D-T3-1 demo 余额断言 stale baseline 修复（demo.py:622-623 / 692-696） | 收尾阶段（T6）或独立小修 → **已于 R3-T6 修复（行为修复，见 §9；代码现 :622-634 / :703-707）** |
| 2 | 对抗流 node 复跑（全案 §6-T3 尾项 / G3 尾项） | T6 收尾 → **R3-T6 未执行**（本轮授权面无链写实跑）→ 后续/用户安排 |
| 3 | `_commit-plan.md` R3 分组、implementation.md 正式增量/偏离表合并 | T6 收尾 → **已于 R3-T6 完成**（`_commit-plan.md` §6；本文件 §5.13 + §9） |
| 4 | T4 EVM 对照 / T5 B3 备料 | 后续阶段（本轮未做）→ **均已于 R3-T4 / R3-T5 完成**（§8、`docs/b3-user-test/`） |

## 8. §R3-T4 执行实现说明（2026-10-30）

本轮任务性质：**单次实验 + 数据采集 + 报告**，不改任何已交付代码（`lyquid/`、`experiments/evm-contrast/` 全程只读，证据见 8.5 GT4-e）。§0–§7 为本轮之前的内容，未作任何修改；本节为增量。

### 8.1 产物清单（#2–#10 及计划外留证件）

| # | 文件 | 内容 | md5 |
|---|---|---|---|
| 2 | `workflow-out/r3-t4-contrast-report.md` | 四维对照报告（代码量/信任假设/裁决不可篡改性/开销）+ 证据清单 + 如实结论 | `69541198fd91b4d13549a5769dc0606b` |
| 3 | `workflow-out/_r3-t4-precheck-raw.txt` | T4.0：`docker ps` 7 容器全 Up、四工具 which、冻结面 md5 基线 | `b8f7bef57f1a5a955938afd57dc33317` |
| 4 | `workflow-out/_r3-t4-md5-raw.txt` | T4.1/T4.3：拷出 3/3 MATCH + 拷回 2/2 MATCH（含执行过程如实登记） | `d09f2fc9ce798edbdd99bb956687b0f2` |
| 5 | `workflow-out/_r3-t4-build-raw.txt` | T4.2：`forge build` 全量输出，EXIT_CODE=0 | `803dfe6e5c2f3ee23acf87d03cf5a028` |
| 6 | `workflow-out/_r3-t4-flows-raw.txt` | T4.3：容器内 report.txt 原样拷回（run-3） | `db00915f7fbf421e6c3a31619a5b8ddc` |
| 7 | `workflow-out/_r3-t4-gas-raw.txt` | T4.3：容器内 gas-raw.txt 原样拷回（20 行逐笔，run-3） | `3f49b7358d2c11b4972580270ca2c141` |
| 8 | `workflow-out/_r3-t4-evidence-recheck-raw.txt` | T4.4：逐笔 receipt 对拍 20/20 + 终态读回 + 负对照复跑 + 三地址字节码 | `4a729d9f91b2b9c41525b30cfdbca8f0` |
| 9 | `workflow-out/_r3-t4-lyquid-scan-raw.txt` | T4.5：链扫脚本原文 + 全量输出 + 两笔创建交易完整收据 + 9 条既有证据对拍 | `b5195252a39f87afaa124a00af51eafc` |
| 10 | `workflow-out/_r3-t4-code-size-raw.txt` | T4.6：wc 三列口径 + `#[cfg(test)]` 起点 + 口径声明 | `10bc0ec58cf48dee43a133626f3cac11` |
| 12 | `workflow-out/_plan-prev-r3t4-backup.md` | 规划期已建：旧 plan.md 备份（md5 与 plan §0-#12 声明一致） | `cf15233b3ad4db7b7248dddd8467ee3f` |

计划外留证件（见 8.4 D-T4-2）：

| 文件 | 用途 | md5 |
|---|---|---|
| `workflow-out/_r3-t4-baseline-md5.txt` | 冻结面 md5 基线独立快照，供 T4.9 逐字节对拍 | `6fafc26bcbd4300068902cff0f4d22df` |
| `workflow-out/_r3-t4-run1-superseded-gas-raw.txt` | 作废 run-1 的 gas-raw 留证 | `f4bc15e9014546b08e227894eee230b8` |
| `workflow-out/_r3-t4-run1-superseded-flows-raw.txt` | 作废 run-1 的 report 留证 | `37a15e0b0cf7bbacef4bcc0af146c84b` |
| `workflow-out/_r3-t4-run2-superseded-gas-raw.txt` | 作废 run-2 的 gas-raw 留证 | `44ef19a44d91d0444ffe3e6eafb0cebd` |
| `workflow-out/_r3-t4-run2-superseded-flows-raw.txt` | 作废 run-2 的 report 留证 | `b1f7ecc14e8762d11b9cfd768c321e21` |

### 8.2 实跑命令摘要（全部本轮实际执行）

| 阶段 | 命令（宿主 Git Bash；路径相对 `trustbridge/`） | 结果 |
|---|---|---|
| T4.0 | `docker ps`；`MSYS_NO_PATHCONV=1 docker exec multi-tools sh -lc 'which forge cast jq python3'`；`md5sum lyquid/src/*.rs lyquid/Cargo.toml lyquid/Cargo.lock experiments/evm-contrast/*` | 7 容器 Up 15h；四工具齐备；基线入档 |
| T4.1 | `docker exec multi-tools rm -rf /tmp/tb-evm`；`docker cp experiments/evm-contrast/. multi-tools:/tmp/tb-evm`；`docker exec -w /tmp/tb-evm multi-tools md5sum Escrow.sol foundry.toml run-contrast.sh` | 3/3 MATCH |
| T4.2 | `docker exec -w /tmp/tb-evm multi-tools forge build` | `Compiler run successful!`，EXIT_CODE=0 |
| T4.3 | `docker exec -w /tmp/tb-evm multi-tools bash run-contrast.sh`；随后 `docker cp` 拷回 gas-raw.txt / report.txt 并双向 md5 | 三流全 PASS（Settled 5 / Refunded 6 / Refunded 6）+ 负对照 rc=1；拷回 2/2 MATCH |
| T4.4 | 归档 gas-raw 逐字节喂入容器 `/tmp/t4recheck/gas-raw.txt`（md5 两侧一致）→ 容器内循环 `cast receipt --json \| jq` 对拍；再 `cast call stateOf/dealInfo/rolesOf/amountOf/committeeSize/threshold/misconduct/codesize` 读回；最后用 deal-3 的三签对 deal-4 重放 | 20/20 gasUsed、20/20 status 一致；deal-1/2/3/4 = 5/6/6/4；重放 rc=1 `non-member signer` |
| T4.5 | 容器内 `python3 /tmp/t4-lyquid-scan.py`（eth_blockNumber/getBlockByNumber(full)/getTransactionReceipt，块 0..404，endpoint `http://node1:10087/api`）；两笔创建交易 `cast receipt --json` 全文 | 创建交易恰 2 笔：R2 `0xaabbe98a…`@199（0x389241）、R3 `0xc789080c…`@327（0x3aa3e1）；R2 调用 123 笔 / R3 13 笔 |
| T4.6 | `wc -l experiments/evm-contrast/Escrow.sol lyquid/src/*.rs`；`grep -n "cfg(test)" lyquid/src/*.rs` | 407 / 2933（顶层）/ 2083（六文件）；三处 `#[cfg(test)]` 起点 309/92/209 |

### 8.3 数据勾稽关系

1. **代码一致性**：脚本三件套 宿主↔容器 md5 3/3 MATCH（`_r3-t4-md5-raw.txt` 第一部分）。
2. **产物一致性**：容器 gas-raw/report ↔ 宿主归档件 2/2 MATCH（同文件第三部分），故 `_r3-t4-gas-raw.txt` / `_r3-t4-flows-raw.txt` 是容器内脚本的原样产物。
3. **EVM 数据自证**：归档 gas-raw 的 20 行逐笔与链上 receipt 对拍 20/20（gasUsed 与 status 双一致），且复核输入经 md5 证明就是归档件本身（`_r3-t4-evidence-recheck-raw.txt:6-16`）。
4. **终态以读回为准**：deal-1 Settled(5)、deal-2 Refunded(6)、deal-3 Refunded(6)、deal-4 Disputed(4)、misconduct(seller)=0（`_r3-t4-evidence-recheck-raw.txt:50-53,83`）。
5. **Lyquid 数据对拍**：链扫结果与既有日志逐条对上——R3 faucet@333（`_r3-t3-final-state-raw.txt:25` ↔ 扫描 `:288`）、R3 终态块 341（`:4` ↔ `:296`）、R2 keeper 双笔 gasUsed 0x923c/0x8c9c（`_r2-keeper-loop-raw.txt:27-28` ↔ 扫描 `:173-174`）、R2 P2 探针 37,748 gas（`_r2-deploy-raw.txt:762-766` ↔ 扫描 `:161`）；两笔创建交易 hash/block/gas 与 plan §1-5 复验值一致。
6. **代码量三列**与 plan §2 基线三项交叉校验全部 MATCH（`_r3-t4-code-size-raw.txt:65-68`）。
7. **运行时字节码 8709** 双源一致：脚本 summary（`_r3-t4-flows-raw.txt:22`）与 `cast codesize`（`_r3-t4-evidence-recheck-raw.txt:86,121`）。

### 8.4 偏离登记

| 编号 | 偏离 | 事实与处理 |
|---|---|---|
| D-T4-1 | **同一实验跑了 3 次**（run-1 / run-2 / run-3），canonical = run-3 | 原因：执行员两次在「重写 md5 日志」时误把生成日志脚本连同 `rm -rf /tmp/tb-evm` 一起重跑，清掉了容器内已产出的 gas-raw/report，导致 run-1、run-2 的容器侧拷回勾稽无法在归档文件中成型。处理：作废两轮的宿主产物另存留证（8.1 计划外留证件），第三次把「拷出→实跑→拷回」放进同一次执行，勾稽 2/2 在档。全过程在 `_r3-t4-md5-raw.txt` 第四部分如实登记，未删改任何历史输出。副作用：`run-contrast.sh` 内含 `evm_increaseTime 30`（`run-contrast.sh:118`），三次实跑累计把共享 anvil 时间源推进约 90s（plan §5-R4 登记的是单次 +30s）；Lyquid 实例本轮全程只读、未做依赖未来 slot 的操作。 |
| D-T4-2 | 计划外新增 5 个文件 | `_r3-t4-baseline-md5.txt`（冻结面基线独立快照，供 T4.9 逐字节对拍）+ 4 个 run-1/run-2 作废产物留证件。理由：不删证。 |
| D-T4-3 | T4.4 的逐笔对拍在**容器内**执行，不在宿主 | 宿主 Git Bash 无 `jq`（`which jq` → not found，见 `_r3-t4-evidence-recheck-raw.txt` 头部注记），首版宿主侧脚本因此产出空列；改为把归档 gas-raw 字节喂入容器（md5 证明同一性）后在容器内 `cast receipt | jq` 对拍。另增「§〇 输入同一性」与「§七 三地址字节码」两小段。 |
| D-T4-4 | T4.5 有三个 selector **未识别** | `0xeddfc069`（9 笔）、`0x9771a522`（1 笔）、`0x0d8712ee`（1 笔）在仓库 Rust 源码与 `w1b2-s4-rpc.md` 的 selector 表中均无对应；已在 `_r3-t4-lyquid-scan-raw.txt:383-387` 如实登记为「未识别平台方法」，不猜名。已确证的两个：`0xcd9cc3c8`=`e2_configure`、`0x8b7acf91`=`e2_arm`（容器内 `cast sig` 实算 + console 行对位）。 |
| D-T4-5 | plan 引用的两处既有日志行号与实际有偏差 | plan 记 `_r3-t3-final-state-raw.txt:27`（faucet 证明）实为 **:25**；plan 记 `_r2-adversarial-raw.txt:7-9`（status 1 但 Disputed）实为 **:6**。报告与本节一律按**实际行号**引用，并在相应处注明。 |
| D-T4-6 | 报告与实现说明中「委员会成员含买卖双方」的定性 | 这不是偏离，而是本轮实跑暴露的事实（`_r3-t4-flows-raw.txt:23` 的 4 个地址中 buyer/seller 在列），报告 §2-②/§4-1 已按此如实表述，未按「独立第三方委员会」写。 |
| D-T4-7 | T4.5 未做 Lyquid 侧跨单签名重放实验 | 不在 T4 方案范围；报告 §2-③ 已标「无数据（原因）」并只给代码路径证据。 |

### 8.5 GT4 门禁状态（对照 plan §6）

| 门 | 状态 | 依据 |
|---|---|---|
| GT4-a | ✅ 满足 | deal-1 Settled(5) / deal-2 Refunded(6) / deal-3 Refunded(6) / deal-4 Disputed(4) + 负对照重放 rc=1 + misconduct(seller)=0，全部 `cast call` 读回（`_r3-t4-evidence-recheck-raw.txt:50-53,83,100-102`）；#6/#7/#8 均在档 |
| GT4-b | ✅ 满足 | 拷出 3/3 MATCH + 拷回 2/2 MATCH（`_r3-t4-md5-raw.txt`，结论行 `GT4-b: PASS（3/3 + 2/2）`） |
| GT4-c | ✅ 满足 | 报告四维表逐格带 `文件:行号`；无数据处标原因（§2-④-7 数据缺口表）；代码量①维持 plan §2 三列口径（407 / 2083·1323 / 2933·2173，lib.rs 850 计入列 c），未回退为单口径 |
| GT4-d | ✅ 满足 | Lyquid 数字全部来自既有日志行或 #9 链扫行；部署环节双重记载——平台操作日志（`_r3-t3-deploy-raw.txt:74-89` OCI/registry）+ 链上 to=null 创建交易收据全文（`_r3-t4-lyquid-scan-raw.txt` §3）；部署 gas 与部署→终态块跨度已进四维表④（R3: 3,843,041 / 327→341=14 块；R2: 3,707,457 / 199→326=127 块） |
| GT4-e | ✅ 满足 | T4.9 md5 与 T4.0 基线一致（见本节末）；`experiments/`、`lyquid/` 未改；未执行 git commit/add/push |
| GT4-f | ✅ 满足 | 本节含产物清单（8.1）+ 实跑命令摘要（8.2）+ 数据勾稽（8.3）+ 偏离登记（8.4，D-T4-1..7）+ GT4 状态表（8.5） |

## 9. §R3-T5+T6 执行实现说明（编码员，2026-10-30）

> **任务性质**：B3 三文档（R3-T5）+ 回归收尾（R3-T6：D-T3-1 行为修复、回归三件套、
> 提交计划与实现说明合并）。**无实跑部署、无任何链写**（不发交易、不建 deal、不重跑
> committee 流、不重启容器）；唯一代码改动 = `scripts/demo.py` 的 D-T3-1 修复 hunk。
> 全部命令与原始输出见 `workflow-out/_r3-t6-regression-raw.txt`（T6.0/T6.1/T6.2/T6.5 四段）。

### 9.1 产物清单（#3-#9 + md5）

| # | 文件 | 动作 | 内容摘要 | 规模 | md5 |
|---|---|---|---|---|---|
| 3 | `scripts/demo.py` | 改（D-T3-1 修复：13 行替换原 2 行，净 +11） | `pre_tap` 前置读 → `faucet` → `wait_for(faucet_landed, 15s)` 读回 → 打印 `faucet read-back OK` → `before = snapshot()`；余额断言本体零改动 | 784 → 795 行 | `d81c50b1c0f0c15f376b1307e0861a88` |
| 4 | `docs/b3-user-test/操作手册.md` | 新建 | 六节（环境/部署/主跑/console 观察/终态读回/错误排查）+ 三附录；§1.2 依赖与可达性三点（sim 零依赖 / node 需 requests / 四端口可达）；命令与预期输出回填 `_r3-t3-*` 实录并逐条标 `文件:行号`；修复后新增行标「无已档实录」 | 477 行 | `a8af6a6d07eb31cdbd8a726376164ee7` |
| 5 | `docs/b3-user-test/通过判据.md` | 新建 | L2/L1/L0 三层口径（引 `_plan-prev-r3-backup.md` §3.4）+ L2 验收清单（逐条引 console 行）+ 读回勾稽 5 项 + 通用纪律（status≠effect / 两段 agreed / pending vs 硬失配）+ 降级形态 | 143 行 | `70904c0ccc3728403604c9049537f892` |
| 6 | `docs/b3-user-test/反馈收集表.md` | 新建 | 四维空白表单：任务理解（含两道信任模型题 Q1/Q2）/ 操作顺畅度（六节 1-5 分）/ 结果可信度 / 开放意见；无示例反馈 | 123 行 | `caeb682d30fc0016fc7c616dce1ff9e1` |
| 7 | `workflow-out/_r3-t6-regression-raw.txt` | 新建 | T6.0 前置核验 / T6.1 修复前后摘录 + py_compile + selftest + sim diff + 门控 / T6.2 壳 40/40（宿主）/ T6.5 冻结门 + 计数 + 文档引用回验 + 只读复验 + 未做项 | 232 行 | `602dc7e17e4b025bdce9569521ac26f5` |
| 8 | `workflow-out/_commit-plan.md` | 改（§3 末句补记 + §6/§6.1 追加；原文 §1-§5 不动） | §6：R3-C1..C6 提交序列 + 不入库/归档组 + 移列声明；§6.1：96 状态行全覆盖表（零未归属）+ 分组计数；§3：R3 轮壳零修改只读复跑补记 | 187 → 414 行 | `7d4fc151db7c46de2b4b078d5e55195e` |
| 9 | `workflow-out/implementation.md` | 改（§5.13 + §3 G5/G6 + §6 #2-#6 + §7.5 注记 + 本节） | §5.13 偏离总表 23 条（索引，原文不动）；§3 G5/G6 状态格核销；§6 / §7.5 状态注记；§9 产物/命令/勾稽/偏离/门禁/对账 | 555 → 734 行 | 见下方说明 |
| — | `workflow-out/plan.md`（本轮未改，#2 备份件已由规划期建好） | 读 | — | 319 行 | `a808bbfcc4384fd5148530b61db49ff7`（备份件 `a7eb173c…`） |

**md5 说明**：上表 #3-#8 的 md5 为写入完成后的实测值；**#9（本文件）不自引用**——
写入本节后其 md5 才定稿，故不列入表内，最终值由本轮交付回报登记。
`plan.md` md5 为读入时实测，本轮零改动。

### 9.2 实跑命令摘要（T6.0–T6.5，全部实跑；完整输出见 #7）

| 阶段 | 命令 | 结果 |
|---|---|---|
| T6.0 | `docker ps --format "{{.Names}} {{.Status}}"` | 7 容器 Up（16h） |
| T6.0 | `md5sum -c workflow-out/_r2-t0-frozen-baseline.txt` | 4×OK + 已知 `WARNING: 1 line is improperly formatted`，exit 0 |
| T6.0 | `git diff --stat -- lyquid/src/{types,core,committee}.rs`；`git diff --numstat -- lyquid/src/assessor.rs` | 空；`5	0`（R1 在场） |
| T6.0 | `md5sum lyquid/src/committee_certified.rs`；`sed -n 91p …` | `83e358ee…`；`const E2_AVG_NUM: u16 = 4;` |
| T6.0 | `git status --porcelain | wc -l`；`md5sum scripts/demo.py` | 94（规划期 93，执行时点为准）；`4fd99a6a…`（修复前） |
| T6.1 | `python -m py_compile scripts/demo.py` | exit 0 |
| T6.1 | `python scripts/demo.py --selftest` | 7 PASS + `SELFTEST OK`，exit 0 |
| T6.1 | `python scripts/demo.py --sim --flow all > /tmp/r3t6/sim.txt` + `diff -u workflow-out/_r2-t0-sim-baseline-raw.txt /tmp/r3t6/sim.txt` | exit 0；**diff 无输出（IDENTICAL）**，两侧 23 行 |
| T6.1 | `python scripts/demo.py --sim --flow committee` | exit 1，`node-only flow: FakeNode has no oracle certification round …` |
| T6.2 | `cd ../workflow-out/verify_core && cargo test --lib --tests` | exit 0；`33 passed` / `5 passed` / `2 passed`，0 failed = **40/40**（宿主通道） |
| T6.5 | 冻结门四件套复跑；`git status --porcelain | wc -l`；`git log --oneline -1` | 全部同 T6.0；96；仍 `dc78d2f` |
| T6.5 | 三文档引用回验（分域，不抽样） | 72 项自动 PASS + 1 项 token 位置经人工复核 PASS（合计 73 项）；signer↔transcript NodeID 身份闭环 = True |
| T6.5 | 只读快照（NodeClient，无链写） | block 404；`deal-1` Refunded；alice 10000 / bob 0 / broker 0；evidence=3；`armed_deal=deal-1` |

### 9.3 勾稽关系

1. **sim 逐字**：`--flow all` 输出 23 行 = 冻结基线 23 行，`diff -u` 无输出 → 修复只落在
   node-only `flow_committee`，sim 代码路径零触碰。
2. **40 计数**：33(lib) + 5(escrow_lifecycle) + 2(modelcheck_refund) = 40；三条
   `test result: ok … 0 failed` 原文入 #7 T6.2。
3. **冻结 md5**：`types/core/committee/assessor` 4×OK；三文件 `git diff --stat` 空；
   assessor 对 HEAD `5 0`；`committee_certified.rs` md5 与 `E2_AVG_NUM=4` 不变（GT3-f 口径）。
4. **提交覆盖表**：`_commit-plan.md` §6.1 = 96 表行 vs `git status --porcelain` = 96 行，
   未归属 0（分组计数见 §6.1）。
5. **文档引用**：操作手册 36 处"修复后"`demo.py` 全路径引用逐条核对（含仲裁修订新增 :595；另 3 处显式标「修复前」）+ 第二轮仲裁新增裸行号简写 :741 / :741-743 / :752；证据字面值同批核验（TARGET 42 字符、合约 42 字符、实例名 44 字符，第三轮修订补记见 #7 T6.5-7）；
   通过判据的 console 行全量回验 + signer 映射与 transcript NodeID 逐字一致；
   反馈表四维齐备、无示例反馈。

### 9.4 偏离登记（本轮新增 2 条 + D-T3-1 修复登记）

- **D-T5-1（文档面）**：全案 §5 的「演示脚本.md」不在本任务三件之列（任务陈述三件 =
  操作手册 / 通过判据 / 反馈收集表），按任务陈述交付；演示脚本的 console 画面讲解要点
  并入操作手册 §4.4「怎么向用户讲这一屏」。无功能缺失。
- **D-T6-1（通道选择）**：壳 40/40 走**宿主通道**实跑通过（`rustc/cargo 1.99.1`），
  按方案 §5-R2 **未启用容器 fallback**；规划期「宿主工具链损坏」的前提在当前机器状态不成立，
  以实跑为准。壳本轮零修改（`_commit-plan.md` §3 末句已补记）。
- **D-T3-1 修复登记（行为修复，非重构）**：
  - 修复位置 `scripts/demo.py:622-634`：`pre_tap`（发交易前读）→ `faucet` →
    `wait_for(faucet_landed, 15s)` 轮询读回 → 打印 `faucet read-back OK` → `before = snapshot()`；
  - 余额断言本体 `scripts/demo.py:703-707` **零改动**；其语义从「与 faucet 前旧值相等」
    修正为「与 faucet **落账后**基线相等」——这正是缺陷本义（stale baseline）；
  - 验证口径：`py_compile` + `--selftest` + `--sim --flow all` 逐字 diff + `--sim --flow committee`
    门控（四项全过，#7 T6.1）；
  - **诚实边界**：`flow_committee` 的端到端重验需新实例（部署 + 链写），**不在本轮授权面**，
    未执行；修复后新增的 `[committee] faucet read-back OK: …`、`[committee] refund check OK: …`
    与 console 取证段均**无已档实录**（操作手册逐处标注）。
- **仲裁修订登记（2026-10-30，本轮采纳；文档面）**：`docs/b3-user-test/操作手册.md`——
  (a) §1.2 改写为三点：零依赖声明收窄到 **sim 面**（模块级导入只用标准库；`requests` 为
  懒导入 `agents/common/rpc.py:442`、`agents/common/llm.py:48`）；(b) 补 **node 模式硬依赖**
  `pip install -r agents/requirements.txt`（`agents/requirements.txt:4`、`README.md:67`），
  否则首次 eth JSON-RPC（`scripts/demo.py:595` → `agents/common/rpc.py:442`）即抛
  `ModuleNotFoundError: No module named 'requests'`；(c) 可达性修正为 **committee 流需四端口
  10087/11087/12087/13087 全部可达**（`get_node_ids` 任一不可达即 fail-closed，
  `agents/common/rpc.py:91`、`:392-412`），仅跑只读快照或 normal 流时只需 10087；
  (d) §6 表增第 11 行（requests 缺失的排查项）。**§3/§5 流程本体未改**；§5.1 快照由
  §1.2(b) 统一覆盖。修订后引用回验：demo.py 36 处「修复后」引用（含新增 :595）+ rpc.py 11 处
  + llm.py / requirements.txt / README.md 各 1 处 + implementation.md 1 处，共 70 项检查
  （69 自动 PASS + 1 项 token 位置人工复核 PASS）。
- **仲裁修订登记（第二轮，2026-10-30，采纳；文档面）**：`docs/b3-user-test/操作手册.md`——
  (a) §2.1 的 `rm` 行补 `MSYS_NO_PATHCONV=1` 前缀，并补两点：`exit 0` 不能证明 rm 删对了目标
  （实录 `_r3-t3-deploy-raw.txt:57` 原始命令缺前缀，系照引原样、本手册已按 §1.1 补正）；
  **前缀必须带**——Git Bash 会把 `/tmp/tb-lyquid` 改写成宿主 Temp 路径，`rm` 在容器内空删
  （`-f` 掩盖、exit 0）、旧目录存活，`docker cp` 随后合并进陈旧树，而 §2.2 的九文件勾稽对
  容器内多余残留是盲的；(b) §6 第 6 行重写为「显式传入**空** `--instance`（或被环境置空）才
  fail-closed」（gate 只拦空串，`scripts/demo.py:569-573`、`:741`、`:752`），并把
  `implementation.md:250-253` 标注为「**T2 回填前实录，仅证历史行为**」（`DEFAULT_INSTANCE`
  系 T3 部署后回填，`_r3-t3-deploy-raw.txt:49`）；(c) §6 增第 12 行：**未传 `--instance` 不再
  fail-closed**——argparse default 已回填 `DEFAULT_INSTANCE`（`scripts/demo.py:87`、
  `:741-743`、`:752`），会静默对归档旧实例（已终态）发 committee 链写，TARGET 断言拦不住
  （旧实例名推出的 TARGET 与旧合约自洽）；处置 = 换实例必须显式传新实例名、开跑前核对
  SUMMARY 首行 `instance =`。**§3/§5 流程本体未改**。修订后引用回验：demo.py 全路径 39 处
  （36 修复后 + 3 修复前）+ 新增裸行号简写 :741 / :741-743 / :752，demo 检查 54 项；合计
  73 项（54+14+2+3）= 72 自动 PASS + 1 项 token 位置人工复核 PASS。
- **仲裁修订登记（第三轮，2026-10-30，采纳；文档面）**：操作手册 §0 表「已档 TARGET」
  （:10）与 §2.5 预期输出句（:183）的 TARGET 由 **41 字符损坏串**
  `0xc05034ED5191cbc3404956D9b7DfC7391e99bfc`（少 1 字符且 d→D 翻转）更正为**实录 42 字符值**
  `0xc05034ED5191cbc3404956D9b7dFcC7391e99bfc`（`_r3-t3-committee-raw.txt:11`、
  `_r3-t3-deploy-raw.txt:584` 逐字比对 PASS）；§0「适用代码状态」行尾加注本次勘误（41→42 字符）；
  #7 T6.5 段末**追加**补记（不改既有行）。同批核验：合约地址 42 字符、实例名 44 字符，与实录
  一致 PASS。**§3/§5 等其余内容未改**。

### 9.5 G5 + G6 门禁状态

| 门 | 状态 | 依据 |
|---|---|---|
| G5-a | ✅ 满足：三文档在 `docs/b3-user-test/`；手册 36 处修复后 `demo.py` 全路径引用 + 3 处裸行号简写 + rpc.py/impl/新增文件引用全量核对；无虚构输出；修复后未跑的行标「无已档实录」 | 操作手册 §0/§3.3/附录 C；#7 T6.5-③① |
| G5-b | ✅ 满足：L2/L1/L0 与 `_plan-prev-r3-backup.md` §3.4（:116-:121）一致；L2 清单每条引 console 原文行 | 通过判据 §1/§2 |
| G5-c | ✅ 满足：四维齐备（任务理解/操作顺畅度/结果可信度/开放意见），无示例反馈 | 反馈收集表；#7 T6.5-③③ |
| G6-a | ✅ 满足：selftest OK；`--sim --flow all` IDENTICAL；`--sim --flow committee` rc=1 | #7 T6.1 |
| G6-b | ✅ 满足：33+5+2 = 40/40（宿主通道，三条 test result 入档） | #7 T6.2 |
| G6-c | ✅ 满足：三文件 diff 空 + md5 4×OK + assessor +5 + `committee_certified.rs`/`E2_AVG_NUM` 不变 | #7 T6.5-1 |
| G6-d | ✅ 满足：`_commit-plan.md` §6.1 覆盖表 96 = 96，零未归属；含 R3-C1..C6 + 不入库组；D-T3-1 修复 = R3-C3 | `_commit-plan.md` §6 |
| G6-e | ✅ 满足：§5.13 共 23 条可 grep；§3 G5/G6 状态格、§6 #2-#6 状态列、§7.5 注记已核销；§9 在档；§0-§8 原文段落零删除（只改状态格/列并保留「原状态」字样）；对账见 9.6 | 本节 |
| G6-f | ✅ 满足：`git log --oneline -1` = `dc78d2f`；未 commit/add/push；devnet 零链写零重启；新增文件仅方案 §0 清单登记件（#4/#5/#6/#7） | #7 T6.5-2/5/6 |

### 9.6 不丢条目自检（合并前后对账）

方法：`grep -c` 偏离编号 + `awk` 数表行 + `wc -l`（命令见 #7 T6.5 与 9.2）。
「合并前」= T6.0 时点；「合并后」= §5.13 与本轮各状态格写入完成、§9 写入前时点
（§9 自身的编号提及不计入对账，避免自计数）。

| 项 | 合并前 | 合并后 | 判定 |
|---|---|---|---|
| §5 编号条目（1-12） | 12 | 12 | 保留，零删 |
| D-T3-1 出现次数 | 6 | 8 | +2（§5.13 行 + §7.5 注记） |
| D-T3-2 出现次数 | 4 | 6 | +2（§5.13 行 + §5.13 引导句） |
| D-T4-1 出现次数 | 2 | 4 | +2（§5.13 行 + 原有） |
| D-T4-2 出现次数 | 2 | 3 | +1 |
| D-T4-3 / -4 / -5 / -6 / -7 各 | 1 | 2 | 各 +1 |
| D-T5-1 / D-T6-1（本轮新增） | 0 / 0 | 2 / 2 | 新增登记 |
| §5.13 表行 | — | 23 | = 12（T2）+ 2（T3）+ 7（T4）+ 2（本轮） |
| §6 表行 | 11 | 11 | 未删行（仅状态列改写） |
| §7.5 表行 | 4 | 4 | 未删行（仅去向列注记） |
| 本文件总行数 | 555 | 587 | +32（§5.13 块），无删除 |

**收尾声明**：本轮未执行任何 `git commit` / `git add` / `git push`（`git log --oneline -1`
仍为 `dc78d2f`）；未对 devnet 发任何交易、未重启容器；`lyquid/` 源码零改动（冻结四件
md5 4×OK，`committee_certified.rs` md5 与 `E2_AVG_NUM` 不变）。
