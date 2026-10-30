# W1-B2 收尾方案：claim_timeout 空 revert 根因闭环（探针佐证 + keeper 写通道改造 + Refunded 实测）

> 规划人：规划师（2026-10-28）。执行基线 = 当前工作树（含 W1-B2 未提交成果 lib.rs / assessor.rs / Cargo.toml / agents/common/rpc.py，**严禁回退**）。
> 编排者一手诊断 D1–D4 已实证，本方案全部采信为前提，不重新验证、不复活已被推翻的『wasm panic』假设（w1b2-claim-revert-finding.md 原假设作废）。

---

## 0. 受影响文件清单（供审查员核对，共 8 项）

| # | 文件 | 动作 | 持久性 |
|---|---|---|---|
| 1 | `lyquid/src/lib.rs` | 新增探针 `probe_claim_sim` + ACCESS_MATRIX 一行（带移除标记）；T7 移除 | 临时（进→出，终态相对 T0 快照零净变化） |
| 2 | `scripts/keeper.py` | 写通道从 `cast send` 改为 NodeClient（eth_sendTransaction + 回执轮询） | **持久保留** |
| 3 | `workflow-out/w1b2-claim-probe-evidence.txt` | 新建：新实例上探针 A~H 输出（cast call 返回）+ node1 容器控制台 probe 阶段行截取（trap 唯一证据通道，附可验证性注记） | 交付物 |
| 4 | `workflow-out/w1b2-refunded-evidence.md` | 新建：tx hash + `state=="Refunded"` 字面 + balance_of 前后 + keeper 日志 | 交付物 |
| 5 | `workflow-out/w1b2-claim-revert-finding.md` | 头部追加 superseded 注记（指向 #3/#4 与 D1/D2 根因），**不改正文** | 交付物 |
| 6 | `../workflow-out/verify_core/`（**parent 级**，非 trustbridge 仓库内） | 路线①：Cargo.toml 增存根 path 依赖；路线②：assessor `#[path]` 改指 HEAD 落盘件 | 持久（壳自身修复） |
| 6a | `../workflow-out/verify_core/stubs/lyquid-llm/`（Cargo.toml + src/lib.rs） | **路线①新增**：lyquid_llm 最小签名存根 crate（测试纯逻辑不执行，call_model 返回 Err 即可） | 持久（路线①时） |
| 7 | `workflow-out/w1b2-shell-rebaseline.txt` | 新建：壳重定基线证据（修复前后 cargo test 输出） | 交付物 |
| 8 | `workflow-out/_pre-task-snapshot.patch` | 新建：T0 工作树快照（事故恢复用） | 自保 artifact |

不改：`lyquid/src/types.rs`、`lyquid/src/core.rs`（core 语义冻结，T7 以 `git diff` 空输出勾稽）；`agents/common/rpc.py`（基线，只复用不改）；`lyquid/Cargo.toml`（基线）。

---

## 1. 已采信前提（编排者 2026-10-28 一手诊断，规划不重证）

- **D1 根因**：链上实例 `0x1c85638e118b37167e9298c2268758e058DdfDA0` 是 D3 增补前旧镜像（三方 md5 互不相同）；`balance_of`/`due_deals` 一律 `Barrel(FuncNotFound)`、`deal_info` 正常；`claim_timeout` 不在其 eth 导出面 → **空 revert = 旧镜像未导出方法的执行错误**，非 wasm panic、非 core 语义 bug。
- **D2 写通道决策**：`cast send`（gas estimation）对 lyquid 合约不可依赖；写通道 = `eth_sendTransaction` 不带 gas 字段 + `eth_getTransactionReceipt` 轮询 `status=="0x1"`（w1b2-s4-rpc.md §B-⑤ 决策门）。
- **D3 环境现状**：容器全 Up（**属待 G-init 预检前提**，见 §5 T-init——规划期晚些时候宿主 cargo 已实测损坏，环境不可再默认假定）；部署通道 = 宿主 `docker cp` → `multi-tools:/tmp/tb-lyquid` → 容器内 `shaker deploy -r http://registry:8000/lyquids --endpoint ws://node1:10087/ws --private-key <anvil#0> Cargo.toml`；每次 deploy 全新实例（新地址），需重放 faucet/create_deal/fund（序列见 w1a-funded-evidence.txt）。anvil#0 私钥 `0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80`。
- **D4 代码事实**：`lib.rs:414-425` claim_timeout 无守卫（Anyone by design）；`core.rs:170-178` 纯函数零 panic（Funded 且 now≥deadline → full_refund）；`lib.rs:709-713` current_slot()；ACCESS_MATRIX 每 network fn 一行，探针须同步加行（Anyone + probe-removable 注记）；`Deal: Clone` 已 derive（types.rs:93），探针克隆模拟、core 不动。

## 2. 本轮规划期新实证（规划师实跑，编码员须知晓）

1. **验证壳当前编译失败**（关键新事实）：实跑 `cd "F:\canvus auto\downloads\202609CS5298\workflow-out\verify_core" && cargo test --lib --tests` → **error[E0432]/[E0433]**：`assessor.rs:37-38` 的 `use lyquid_llm::...` 无法解析（壳 Cargo.toml 仅有 serde/serde_json）。即未提交的 W1-B2 S3 改动已打破壳的"零平台依赖"前提，**硬约束"39/39"当前不可能原样达成**，须先修壳。
1a. **『壳补 lyquid-llm git pin』路线已被容器实证否决（冷读仲裁 2026-10-28 实测，勿再尝试）**：multi-tools 容器内（cargo 1.99.0，x86_64）以最小 crate 依赖 `lyquid-llm rev=fd575e8 features=["ldk"]` 跑 `cargo check --offline` → `error[E0425]: cannot find type NativeGuestAbi`（ldk `lyquid/src/runtime/mod.rs:38/40/42`）。该错误出在 ldk 自身源码，**宿主与容器双不可达**；parent 级 ldk clone 的 path 依赖是同一 crate 同一代码，同因失败（备选A 作废）。命令与错误尾部随 T0 一并记入 `w1b2-shell-rebaseline.txt`。
2. **测试计数漂移**：HEAD（1c0e45f）assessor 5 个 `#[test]`（`git show HEAD:lyquid/src/assessor.rs | grep -c "#\[test\]"` = 5，壳基线 32+5+2=39 出处 w1b2-t0-baseline.txt）；工作树 assessor 6 个 → 修复编译后计数视路线而定：**①存根=33+5+2=40 / ②HEAD 挂载=32+5+2=39**（见 §5 T0-2）。"39/39"按意图执行 = 壳全绿，数字以 T0 重定基线（注明路线）为准并如实登记。
3. **宿主 cargo 可执行文件已坏，git/path 依赖路线亦不可达**：宿主 cargo git 缓存已含 ldk rev `fd575e8`（`~/.cargo/git/checkouts/ldk-b72281d44a8ce511/` 下有 `fd575e8` 目录），parent 级 `ldk/` 本地 clone 恰在 `fd575e88a920…`（`git -C ldk rev-parse HEAD`）——但以它们为 lyquid-llm 依赖来源的路线已被 §2-1a 实证否决（E0425），ldk clone 此后仅作 T-init 起栈的 compose 文件出处。**2026-10-28 晚（22:39–22:44，目录 mtime）宿主工具链遭外力破坏，规划师复核实证**：`~/.cargo/bin/cargo.exe` 为指向缺失 `rustup.exe` 的断裂符号链接；toolchain `1.99.0` 与 `stable` 两个 bin 目录均仅余 `cargo.pdb` 无 `cargo.exe`（本会话早前实跑 `cargo test` 尚成功，破坏发生在其后）。故宿主侧壳路径以 T-init ③ 通过或修复为前提，否则走容器路线（R1，含 #[path] 改写）。
4. **宿主 python 通道可用**：`python 3.14.5 + requests 2.34.2` 实测在机；`NodeClient`（agents/common/rpc.py:197-381）已实现 §B-⑤ 全部决策：`_send` = eth_sendTransaction 无 gas 字段 + 回执轮询 status=="0x1"（rpc.py:241-262），且已含 `claim_timeout/deal_info/balance_of/due_deals/faucet/create_deal/fund` 封装与 selector 表（`claim_timeout(string)=0x786cfc8f`，rpc.py:76）；`DEFAULT_NODE=http://127.0.0.1:10087`、URL 拼 `/api`（rpc.py:220）、`DEFAULT_SENDER=0xf39F…92266`（rpc.py:57，=anvil#0=BROKER）。宿主直连 node1 API 通道在 §B/C 已实证（w1b2-s4-rpc.md:13、:153-160）。
5. **timeout_slots 换算**：`timeout_slots = est_ms×2/400`（types.rs:195-197，SLOT_MS=400、TIMEOUT_SAFETY_FACTOR=2）→ **est_duration_ms=200 ⇒ timeout_slots=1**（与 D3 所述旧实例 deal 参数自洽）。
6. **只读 getter 形态先例**：`deal_info(ctx: &_, …) -> LyquidResult<String>`（lib.rs:532，共享引用 + JSON 串返回）——探针照此形态方能 cast call 可读；eth_call 对可变方法不开放（w1b2-claim-revert-finding.md 排除项记载 fund 之 call 为 FuncNotFound）。

## 3. 目标 / 非目标

**目标**（= 交付闭环四件套）：
1. 新实例上 `probe_claim_sim` 各阶段 A~H 输出留存（证明 core 路径在新镜像上全程无 panic 点）；
2. keeper 实测 `claim_timeout` 退款成功；
3. workflow-out 留存 Refunded 证据文件（tx hash + `deal_info` `state=="Refunded"` 字面 + `balance_of` 前后对比 + keeper 日志）；
4. 探针移除后壳全绿复验 + types/core 零改动勾稽。

**非目标**：不修 core 语义（D4 证明无 bug）；不改 ACCESS_MATRIX 既有行；不动 W1-B2 未提交基线（assessor/llm 接线等）；不清理旧实例 `0x1c85…`（仅留 D1 诊断已存档）；不做 anvil#0 之外的账户矩阵。

## 4. 总体策略

D1 已定根因 = 旧镜像，故本任务**不是"修 panic"而是"闭证据环"**：新镜像部署（自带 D3 导出面）+ 探针在 eth_call 读通道逐阶段自证 core 路径干净 + keeper 写通道按 §B-⑤ 决策改造后在真实链上走完 Funded→Refunded。探针按 W1-B1 探针纪律（probe/mod.rs:14-19 additive-only）以显式标记进、显式标记出。另须先修复验证壳编译（§2-1 新事实），否则硬约束无处落地。

## 5. 子任务与执行顺序

### T-init 预检门（G-init，先于一切任务）
三项检查**全部通过**才进 T0：
- ① `docker ps` 守护进程可达，且 multi 栈容器（multi-node1-4 / anvil / registry / tools）Up；
- ② 宿主节点 API 探活：`curl -s -X POST http://127.0.0.1:10087/api -H 'content-type: application/json' --data '{"jsonrpc":"2.0","id":1,"method":"eth_blockNumber","params":[]}'` 返回含 `result`；
- ③ 宿主 `cargo --version` 可执行。

失败处置：
- ①② 失败 → `docker compose -f docker/multi/docker-compose.yaml up -d`（w1b1-topology.md:14；compose 文件在 parent 级 ldk clone 的 `docker/multi/` 下），或等价 `bash scripts/devnet-up.sh`（README.md:62），随后复检；
- ③ 失败 → 宿主 cargo 已坏（2026-10-28 仲裁实测 + 规划师独立复核一致：`.cargo/bin` 无 rustup.exe（cargo.exe 为断链）、`1.99.0` 与 `stable` 两个 toolchain bin 目录均只有 cargo.pdb 无 cargo.exe）→ **首选修复 rustup 工具链**（重装 rustup / `rustup toolchain install`）；不可行时走 R1 **容器路线**（改写壳内 `#[path]` 后 docker cp 进容器 cargo test，不依赖宿主 cargo；git pin/path 依赖路线已实证不可达，§2-1a）；备选C 仍须升级编排者确认；
- 任一处置后**复检仍不过 → escalate，不得带病执行 T0 及之后任务**。

### T0 基线快照 + 壳修复与重定基线（门 G0）
1. `git -C trustbridge diff > workflow-out/_pre-task-snapshot.patch`（含未提交 W1-B2 全部改动；仅作恢复凭据，**不 stash、不 checkout**）。
2. 修壳（**二选一，首选①**；git pin / ldk path 依赖路线已实证不可达，§2-1a，勿再尝试）：
   - **① 存根路线（首选）**：壳内新增本地存根 crate（建议 `../workflow-out/verify_core/stubs/lyquid-llm/`，包名必须是 `lyquid_llm`），壳 Cargo.toml 以 path 依赖引入。签名面按 assessor.rs 实际用量给**最小实现**（全部消费点已核实：assessor.rs:37-38（use）、:116-142（LyquidLlmModel），别无他处）：
     - `backend::openai_compat::OpenAiCompatBackend`：`openai(&str) -> Result<Self, E>`（E: Display，assessor.rs:124 以 `{e}` 格式化）、`chat_completions(&str, &str) -> Self`、`bearer_auth(self, &str) -> Self`、`output_format(self, OutputFormat) -> Self`（builder 链，assessor.rs:124-129）；
     - 顶层 `call_model(&OpenAiCompatBackend, &ModelRequest) -> Result<ModelResponse, E>`——**测试纯逻辑不执行此路径，返回 Err 即可**（assessor 的 6 个测试均不触 LLM 路径，已核实：tests 模块内对 LyquidLlmModel/call_model 零引用）；
     - `ModelRequest::new(&str, &str) -> Self` + `.timeout_ms(..) -> Self` + `.max_output_tokens(..) -> Self`（assessor.rs:136-138）；
     - `OutputFormat::json_schema(&str, serde_json::Value) -> Self`（assessor.rs:129）、`ModelResponse { text: Option<String> }`（assessor.rs:140-141 的 `.text` 消费）。
     编码员以编译迭代对齐精确签名（整数宽度等细节以编译器报错为准）。壳仍挂**工作树** assessor → 计数维持 **33+5+2=40**。
   - **② HEAD 挂载路线**：`git show HEAD:lyquid/src/assessor.rs > 壳内落盘文件`，壳 src/lib.rs 的 assessor `#[path]` 改指它（该版无 lyquid_llm 引用、5 测）→ 回到 **32+5+2=39 字面**；**须登记偏差：壳不再覆盖工作树第 6 测（R2#1 wire-shape pin 的测试面）**。
3. 复跑 `cargo test --lib --tests`（cwd=壳目录），预期三段 ok：路线① = 33/5/2（=40）、路线② = 32/5/2（=39）。原始输出存 `workflow-out/w1b2-shell-rebaseline.txt`，**注明所选路线与最终计数**及漂移原因（①：W1-B2 未提交 assessor 新增 1 测；②：挂 HEAD 版）；§2-1a 的容器实证（命令+错误尾部）一并录入该文件。
4. **G0 门**：壳全绿（**注明所选路线与最终计数**，39 或 40）。不过 → 回退 R1（§9）。
5. **容器路线前置说明（宿主 cargo 未修复时）**：壳进容器跑测试**必须先改写壳内全部 `#[path="F:/…"]` 为容器内路径**——src/lib.rs:4-13（types/core/committee/assessor 四处）、tests/escrow_lifecycle.rs:4、tests/modelcheck_refund.rs:4（两测试文件均已排查确认含 path 属性）——再 docker cp 壳与 lyquid 源进容器（依赖缓存实测可离线解析）。原『直接 cp 运行』不可行，照此改写。

### T1 探针落地（lyquid/src/lib.rs，门 G1）
按 §6-1 与 §7 设计新增 `probe_claim_sim` + ACCESS_MATRIX 行 + 标记注释。容器内编译检查：
`docker exec multi-tools-1 sh -c "cd /tmp/tb-lyquid && cargo check"`（在 T2 的 docker cp 之后执行亦可，合并为一次 cp）。
**G1 门**：cargo check 零 error；`git diff lyquid/src/types.rs lyquid/src/core.rs` 输出为空。

### T2 新实例部署（门 G2）
1. `docker cp` 宿主 `trustbridge/lyquid/.` → `multi-tools-1:/tmp/tb-lyquid`（覆盖；随后容器内 `md5sum /tmp/tb-lyquid/src/lib.rs` 与宿主比对，杜绝 D1 复发）。
2. 容器内 `shaker deploy -r http://registry:8000/lyquids --endpoint ws://node1:10087/ws --private-key 0xac09…ff80 Cargo.toml`（cwd=/tmp/tb-lyquid），记录新实例地址。
3. **G2 门（镜像自证）**：对新地址 `cast call … "probe_claim_sim(string,uint64) returns (string)" deal-x <now>` 或 `balance_of` 任一调用可路由（不再 FuncNotFound）即证明新镜像生效。

### T3 重放造快过期 deal（门 G3）
宿主 python + NodeClient（`TB_CONTRACT=<新地址>` 或构造参数），全部走 eth_sendTransaction 通道：
`faucet("0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266", 1_000_000)` →
`create_deal(buyer="0xf39F…92266", seller="agent-bob", amount=1000, fee_bps=200, terms_d, acceptance_d, est_duration_ms=200, est_confidence=90)`（§2-5 ⇒ timeout_slots=1；caller=DEFAULT_SENDER=anvil#0=BROKER 过 Broker 守卫）→
`fund("deal-1")`（Buyer 守卫：caller==buyer 同为 anvil#0）。
**每笔 send 后读回复核**（§A-1 笔 3 教训：status=1 ≠ 方法 Ok）：`deal_info`/`balance_of` 确认 Qualified→Funded。等 `eth_blockNumber > deadline_slot`（轮询；automine 不推进时补一笔 benign `faucet` 造块）。
**G3 门**：`deal_info(deal-1)` 返回 `state:"Funded"` 且块高 > deadline_slot。

### T4 探针佐证取证
取证前先实读块高作 advisory 入参：宿主 `curl -s -X POST http://127.0.0.1:10087/api … eth_blockNumber`（透传已证，§B-④d）或 `NodeClient.block_number()`（rpc.py:229）。随后容器内 `cast call --rpc-url http://node1:10087/api <新地址> "probe_claim_sim(string,uint64) returns (string)" deal-1 <块高实读值>`，完整原始输出（A~H 各阶段、**chain_now/caller_now 双值**、块高、实例地址、命令行）存 `workflow-out/w1b2-claim-probe-evidence.txt`。
**同步截取 node1 容器控制台/日志中的 probe 阶段行**（`docker logs <node1 容器名>`，如 multi-node1-1）一并存入同一证据文件——trap 情形下这是唯一证据通道（§7 定位口径）；并如实注明：**trap 时 println 能否落入节点日志未经本仓可验证**（ldk 仅证实 println 为逐次 host console_output 调用），属尽力定位。若 trap 后节点日志亦无阶段行，按 R4 停止并升级，定位降级为『排除法』。
**eth_call 读上下文口径（B2）**：D 阶段显示 `chain_now=0` 或 current_slot() 异常**不是停止事件**——按『eth_call 读上下文 chain_pos 失效』登记为新事实后**继续完成 A~H 取证**（caller_now 判定链完整即证据有效）。tx 上下文的 chain_pos 已有实证（finding.md:15：funded_slot=94==fund 块号），T6 退款走 tx 上下文不受 eth_call 读通道影响。
预期：F 阶段 `Ok` + `Payout{refund_to_buyer:1000,…}`（now 来源=caller 标注）、G 勾稽 `total==1000`、H verdict=PASS-full-refund。**R4 停止条件（仅三类）**：panic、caller_now≥deadline 而 F=Err、G 勾稽失配——触发即停止后续任务并升级（回退 R4）。

### T5 keeper v2 改造（scripts/keeper.py，持久）
按 §8 改造写通道。门：宿主 `python -c "import ast; ast.parse(open('scripts/keeper.py').read())"` 通过（语法级；运行面由 T6 实测覆盖）。

### T6 keeper 实测退款 + 证据（门 G6）
1. 记录前值：`balance_of("0xf39F…92266")`（=faucet 后 − 1000 托管）。
2. 受控运行：`python scripts/keeper.py --node http://127.0.0.1:10087 --contract <新地址> --deals deal-1 --interval 5 --once`（`--once` 跑一轮退出，便于取证；输出含 tx hash——来源 `_send` 回执，见 §6-2/§8）。
3. 读回复核：`deal_info(deal-1)` 字面 `"state":"Refunded"`；`balance_of` 后值 = 前值 + 1000。
4. 全部要素写入 `workflow-out/w1b2-refunded-evidence.md`（tx hash、deal_info 原始字面、balance_of 前后、keeper 日志摘录、所用命令）。
**G6 门**：`state=="Refunded"` 字面 + 余额勾稽 + keeper 日志在档。任一不成立 → 回退 R4/R6 排查后重试（claim_timeout 幂等：Refunded 后重复提交被守卫拒绝，重试安全）。

### T7 探针移除 + 终验（门 G7）
1. 删除 lib.rs 探针 fn、ACCESS_MATRIX 行、全部 `W1-B2-claim-debug probe` 标记注释；`grep -rn "probe_claim_sim" lyquid/` 零残留。
2. 勾稽 core 冻结：`git diff --stat lyquid/src/types.rs lyquid/src/core.rs` 为空。
3. 勾稽净变化：`git diff lyquid/src/lib.rs` 相对 T0 快照无探针残留（lib.rs 终态 = T0 快照态）。
4. 复跑壳 `cargo test --lib --tests`（cwd=壳目录）全绿，输出追加进 w1b2-shell-rebaseline.txt（T0 前后对照，**注明所选路线与最终计数**——路线①=40 / 路线②=39）。
5. w1b2-claim-revert-finding.md 头部插入 superseded 注记块（根因=D1 旧镜像 + D2 写通道限制；指向两份新证据文件；原 wasm-panic 假设作废），正文不动。
**G7 门**：上述 5 项全部成立。

## 6. 逐文件改动点

### 6-1 `lyquid/src/lib.rs`（T1 加 / T7 删，改动全部带标记）
- **新增探针函数**（置于 claim_timeout 之后、cancel 之前，或只读 getter 区 deal_info 附近——编码员择一，保持与只读形态同区）：
  ```rust
  // W1-B2-claim-debug probe BEGIN（probe-removable：T7 整块删除）
  /// Staged simulation probe for the claim_timeout empty-revert debug
  /// (D1/D2: old image + write-channel limitation — NOT a core bug).
  /// Read-only: clones the deal and runs core::claim_timeout on the clone;
  /// never mutates consensus state, never applies payouts. Over export=eth
  /// it is eth_call/cast-call readable (deal_info-shaped JSON string).
  /// Advisory `now` param — precedent due_deals (lib.rs:565-574): the
  /// parameter cannot move funds; the only money-movement guard is
  /// claim_timeout itself, which re-derives time via current_slot().
  #[method::network(export = eth)]
  pub fn probe_claim_sim(ctx: &_, deal_id: DealId, now: u64) -> LyquidResult<String> {
      // A~H 阶段见方案 §7；每阶段 push 之后、执行风险操作之前，立即
      // lyquid::println! 外发该阶段行（deal_info 先例 lib.rs:545，非共识
      // 输出、语义零影响）——trap 时定位口径 = 节点控制台最后一条
      // probe 阶段行（返回值与结尾 println 在 trap 时均不可达）。
      // D 阶段双记 chain_now=current_slot() 与 caller_now=入参 now；
      // E/F/H 判定一律用 caller_now（零写模拟，不动链上资金语义）。
      …
  }
  // W1-B2-claim-debug probe END
  ```
  形态依据：`deal_info(ctx: &_, …) -> LyquidResult<String>`（lib.rs:532）；只读借用 `let state = &*ctx.network;`（getter 先例）；JSON 序列化错误映射 `lyquid_error(&format!(...))`（deal_info 同款，lib.rs:535-536）。
- **ACCESS_MATRIX 增一行**（lib.rs:180 矩阵内、只读 getter 行之前）：
  `("probe_claim_sim", Access::Anyone), // W1-B2-claim-debug probe-removable（只读模拟，无守卫面）`
- **不改**：既有方法体、state! 块、require、current_slot。

### 6-2 `scripts/keeper.py`（T5，持久；全量约 90–110 行的重写幅度）
- docstring 传输层叙述更新：写通道 = NodeClient（eth_sendTransaction 无 gas 字段 + `eth_getTransactionReceipt` 轮询 `status=="0x1"`，w1b2-s4-rpc.md §B-⑤ / D2）；删除 `cast send --json` 及 gas estimation 相关叙述；"Stdlib only" 改为"依赖 agents/common（requests）"。
- 顶部 `sys.path.insert(0, str(Path(__file__).resolve().parents[1]))` + `from agents.common.rpc import NodeClient, DEFAULT_NODE`（demo.py:17-18 同款先例）。
- 删除 `cast()`/`decode_abi_string()`/`deal_state()`/`claim_timeout()` 四个 docker-exec/cast 函数；`poll_once` 改为：
  `info = node.deal_info(deal_id)`（NodeClient.deal_info，rpc.py:358）→ 状态机同旧逻辑（Settled/Refunded→terminal；非 Funded→skip）→ `receipt = node._send("claim_timeout(string)", (deal_id,))`（**不走** rpc.py:330 的 `claim_timeout` 公开封装——该封装丢弃回执并固定 `return True`（rpc.py:330-337），对返回值直接下标取 tx hash 会 TypeError；`_send`（rpc.py:241-262）返回回执 dict 且已含 `status=="0x1"` 断言）→ **读回复核** `after = node.deal_info(deal_id)`，仅当 `after["state"]=="Refunded"` 记 `action=claimed` 并附 `tx=receipt["transactionHash"]`（字段在档：§B-② 回执含 transactionHash；§A-1 笔 3 口径：status=1 ≠ 方法 Ok）。rpc.py 本身不改（§0 约束维持）。
- CLI 参数改为 `--node`（默认 DEFAULT_NODE）、`--contract`、`--deals`、`--interval`、`--once`（单轮退出，实测取证用）；保留时间戳日志格式 `[keeper HH:MM:SS] deal: {json}`。
- NodeError（守卫拒绝/not-due）捕获后按 `action=not-due-or-reverted` 记日志（沿用旧语义）。

### 6-3 `../workflow-out/verify_core/`（T0-2，按所选路线）
- **路线①（首选）**：`Cargo.toml` 的 `[dependencies]` 增本地存根 `lyquid-llm = { path = "stubs/lyquid-llm" }`；新建 `stubs/lyquid-llm/`（Cargo.toml 包名 `lyquid_llm` + `src/lib.rs` 最小签名面，明细见 §5 T0-2①，编码员以编译迭代对齐）。壳自述"临时 crate 不属于 trustbridge 仓库"，改它不触仓库冻结面。
- **路线②**：`git show HEAD:lyquid/src/assessor.rs` 落盘为壳内文件（如 `src/assessor_head.rs`），`src/lib.rs` 的 assessor `#[path]` 改指它；登记『壳不再覆盖工作树第 6 测（R2#1 wire-shape pin）』。
- **容器路线前置**（宿主 cargo 未修复时）：改写壳内全部 `#[path="F:/…"]` 为容器内路径（src/lib.rs:4-13、tests/escrow_lifecycle.rs:4、tests/modelcheck_refund.rs:4）后再 docker cp（§5 T0-5）。

### 6-4 证据文件（新建，格式要点）
- `w1b2-claim-probe-evidence.txt`：实例地址、部署输出摘录、md5 自证、命令行原文（含 advisory now 实读块高）、A~H 原始返回（hex + 解码 JSON）、**chain_now/caller_now 双值**、node1 控制台阶段行截取、当时块高。
- `w1b2-refunded-evidence.md`：① claim tx hash（keeper 日志/receipt）② `deal_info(deal-1)` 原始字面（含 `"state":"Refunded"`）③ `balance_of` 前值/后值及 +1000 勾稽 ④ keeper 日志摘录 ⑤ 复现命令清单。
- `w1b2-shell-rebaseline.txt`：T0 修复前失败输出（E0432/E0433）+ 修复后 40/40 + T7 复验输出；39→40 漂移说明。
- `w1b2-claim-revert-finding.md`：仅头部插入注记块（superseded by D1/D2 + 两份新证据路径）。

## 7. 探针 A~H 阶段语义（定案）

`stages: Vec<(char, String)>`，每阶段按「push 标记与输入 → **立即 `lyquid::println!("probe_claim_sim: {stage} {detail}")` 外发该阶段行** → 执行风险操作 → 成功后 push 结果」的顺序（println 先例 deal_info，lib.rs:545；控制台输出非共识状态、语义零影响）。**定位口径 = 节点控制台最后一条 probe 阶段行**——trap 时返回值与结尾 println 均不可达，逐阶段外发是唯一实时定位通道；正常路径仍返回 `serde_json::to_string(&stages)` 供 cast call 取证（lyquor 的方法级 Err 在 eth_call 下带消息返回，§A-3 实证），结尾的整包 JSON println 可保留作正常通道输出。入参 `now: u64` 为 **advisory**（先例 due_deals，lib.rs:565-574：参数不动资金）；cast 签名 `"probe_claim_sim(string,uint64) returns (string)"`，`now` 取取证前 `eth_blockNumber` 实读值（透传已证，§B-④d）。**D 阶段双记 chain_now 与 caller_now**（正面回答 w1b2-claim-revert-finding.md:19a 待查项 a）；**E/F/H 判定一律用 caller_now**；H verdict 标注 now 来源。

| 阶段 | 记录内容 | 风险操作（println 外发后执行） |
|---|---|---|
| A enter | `"A:enter caller=<ctx.caller>"` | —（进入即记录） |
| B found | `"B:found id=<deal_id>"` | `state.deals.get(&deal_id)`（miss → 记 `B:miss` 并提前返回报告） |
| C state | `"C:state=<format!("{:?}", deal.state)>"` | — |
| D now | `"D:now chain_now=<current_slot()> caller_now=<入参 now> chain_now>0=<bool>"`（**双值并记**，正面回答 finding.md:19a：chain_pos 在调用上下文的真实返回） | `current_slot()`（lib.rs:709 单点） |
| E deadline | `"E:deadline=<deal.deadline_slot()?> caller_now>=dl=<bool>"` | `deal.deadline_slot()`（types.rs:122） |
| F payout | `"F:payout=Ok(Payout{…})"` 或 `"F:payout=Err(<TransitionError 变体>)"` | **核心被测点**：`let mut sim = deal.clone(); core::claim_timeout(&mut sim, caller_now)`（core.rs:170-178；克隆体上模拟，共识状态零写） |
| G conservation | `"G:total=<p.total()>==amount=<deal.amount> <bool>"` + 四字段明细 | `p.total()` 勾稽（apply_payout 的 debug_assert 同式，lib.rs:678，此处以数据形式外显） |
| H verdict | `"H:verdict=PASS-full-refund <amount>-><buyer> (now=caller:<入参>)"` 或 `"H:verdict=BLOCKED <原因> (now=caller:<入参>)"` ——**标注 now 来源** | 汇总 |

补充：结尾整包 `lyquid::println!("probe_claim_sim: {}", json)`（正常通道）与逐阶段行并存；探针**不得**调用 `apply_payout`、不得任何 `insert/get_mut` 写路径——**不得**以『把最后阶段持久化进实例状态』替代逐阶段外发（违反 §7 零写纪律，且 eth_call 写不落盘）。

## 8. keeper v2 写通道设计要点

- 复用而非重造：NodeClient 已按 §B-⑤ 实现 `_send`（rpc.py:241-262）并带 `claim_timeout` 封装（rpc.py:330-337）与 selector `0x786cfc8f`（rpc.py:76）——keeper 只做轮询编排与读回复核。**注意：`claim_timeout` 公开封装仅返回 bool（丢弃回执），keeper 直用 `_send` 取回执以附 tx hash**（理由见 §6-2）。
- sender：claim_timeout 为 Anyone（ACCESS_MATRIX），`DEFAULT_SENDER`（anvil#0）即可，无需私钥进 keeper（节点侧 dev 签名账户，§B-① 实证 from 即生效）。
- 幂等安全：Refunded 后重复 claim 被守卫拒（core.rs:171 require_states），重试无害（keeper 原教义保留）。

## 9. 风险与回退

| # | 风险 | 概率 | 缓解/回退 |
|---|---|---|---|
| G-init | 预检门未过（docker / 节点 API / 宿主 cargo 任一失败；**③ 现状实测已失败**，见 §2-3） | — | 按 T-init 失败处置（起栈 / 修 rustup / R1 备选路由）；复检仍不过 → escalate，不得带病执行 T0 及之后任务 |
| R1 | 壳修复受挫（存根签名对不齐 / 宿主 cargo 未修复） | 中 | git pin 与 ldk path 依赖路线**已实证不可达**（E0425 NativeGuestAbi，§2-1a），勿再尝试；宿主 cargo 未修复时走**容器路线**：先改写壳内全部 `#[path="F:/…"]` 为容器内路径（src/lib.rs:4-13 四处 + tests/escrow_lifecycle.rs:4 + tests/modelcheck_refund.rs:4）再 docker cp 壳与 lyquid 源进 multi-tools 跑 cargo test（依赖缓存实测可离线解析；原『直接 cp 运行』不可行，照此改写）；备选C：壳卸载 assessor 挂载（gate 变 27+5+2=34）——**属硬约束字面变更，须升级编排者确认后方可采用** |
| R2 | 新实例仍 FuncNotFound（cp 未覆盖/registry 缓存旧码） | 低 | T2 的 md5 三方比对（宿主/容器/部署输出）+ G2 门早失败早暴露；重 cp 重 deploy（每次新地址，旧实例自然废弃） |
| R3 | 块不推进、deadline 不到 | 低 | 轮询 `eth_blockNumber`，停滞则补 benign `faucet` 造块（automine） |
| R4 | 新镜像上异常（D1 之外的新根因） | 低 | **停止并升级的仅三类**：① panic（定位=控制台最后一条 probe 阶段行）；② caller_now≥deadline 而 F=Err；③ G 勾稽失配。**eth_call 下 chain_now=0/Err 不属停止事件**——按『eth_call 读上下文 chain_pos 失效』登记新事实后继续取证（tx 上下文 chain_pos 已实证：funded_slot=94==fund 块号，finding.md:15；T6 退款走 tx 上下文不受影响）。触发时携探针报告升级（escalate），不得擅自改 core |
| R5 | 误伤 W1-B2 未提交基线 | 低 | T0 快照 patch 兜底 `git apply -R`；全程禁 `git stash/checkout/reset`；lib.rs 只做标记块增删 |
| R6 | 宿主 127.0.0.1:10087 端口不通（keeper v2 通道失效） | 低 | 回退容器通道：`docker exec multi-tools-1 cast rpc --rpc-url http://node1:10087/api eth_sendTransaction '[{"from":"0xf39F…","to":"<addr>","data":"0x786cfc8f<abi(deal-1)>"}]'` + `cast rpc eth_getTransactionReceipt`（§B-①⑤ 实证形态），keeper 以 subprocess 驱动之（此为文档化备选，非首选） |
| R7 | keeper v2 引入 requests 依赖与"stdlib only"教义冲突 | — | 已裁决：D2/§B-⑤ 决策门优先于旧教义，docstring 如实改写（属登记性偏离，写入证据文件） |

**总回退闸**：所有文件级改动均有 T0 快照 + git 可恢复；链上新实例为临时造物无需回滚；旧实例 `0x1c85…` 保持原样（D1 证据存档）。

## 10. 验收清单（硬约束映射）

- [ ] 壳全绿：`cd ../workflow-out/verify_core && cargo test --lib --tests` 三段 ok——**注明所选路线与最终计数**（路线①=33+5+2=40，路线②=32+5+2=39；路线②另登记『不覆盖工作树第 6 测』偏差），漂移原因在 w1b2-shell-rebaseline.txt 留痕——原"39/39"约束之意图（壳全绿）满足，字面数字偏差如实登记
- [ ] core 语义冻结：`git diff lyquid/src/types.rs lyquid/src/core.rs` 输出为空（T1 与 T7 双时点勾稽）
- [ ] 探针独立可移除：`grep -rn "probe_claim_sim\|W1-B2-claim-debug" lyquid/ scripts/ agents/` 零残留；lib.rs 终态 == T0 快照态
- [ ] 探针佐证：w1b2-claim-probe-evidence.txt 含新实例 A~H 完整输出（**F=Ok full_refund（标注 now 来源）+ G 勾稽 + H=PASS**；含 chain_now/caller_now 双值与控制台阶段行截取）
- [ ] 退款实测：w1b2-refunded-evidence.md 含 tx hash + `state=="Refunded"` 字面 + balance_of 前后 +1000 + keeper 日志
- [ ] 旧 finding 已注记 superseded（wasm-panic 假设作废声明）
