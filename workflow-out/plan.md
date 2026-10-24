# W1-B1 开发计划与变更方案：平台机制探针（多节点拓扑 + S1 timer 语义 + S2 委员会认证回合）

执行基线：代码 `275cd94`（W1-A 已完成，工作树另有文档提交 `f83ab52`；W1-A 旧计划见 git 历史 `f83ab52:workflow-out/plan.md`）。本计划为运行/验证类任务：**一切结论以实际执行的命令与真实输出为交付**，严禁编造运行结果。

---

## 受影响文件清单（供审查员核对，共 10 项）

| # | 文件 | 动作 |
|---|---|---|
| 1 | `lyquid/src/probe/mod.rs` | **新建**：探针模块挂载 + 模块说明（SPIKE 登记锚点） |
| 2 | `lyquid/src/probe/s1_timer.rs` | **新建**：S1 timer 探针合约（arm/on_timer/probe_mark_fire/probe_reset_net/get_report；instance+network 双观测域，exactly-once 以共识 network 计数 delta 判定） |
| 3 | `lyquid/src/probe/s2_oracle.rs` | **新建**：S2 认证探针（configure/propose/aggregate/on_certified/run_round/bump_threshold/config 含 dest epoch 观测；`eth_guard = creator` 守卫，无 constructor/initializer——冷读仲裁修订） |
| 4 | `lyquid/src/lib.rs` | **改**：仅 2 处——①`pub mod probe;` 挂载一行；②若 state! 宏限定 crate 级单例（R1 风险），在既有 state! 块末尾追加探针 state 字段（含 S1 network 域 probe_net_fires/probe_net_last_fire_ms，主 escrow 字段零改动） |
| 5 | `lyquid/Cargo.toml` | **预期零改动**；仅当 oracle 类型需要平台 feature 传递时动 feature 行（裁定 1 豁免路径，逐行登记），**不新增任何直接依赖** |
| 6 | `lyquid/src/timeout.rs` | **改（仅注释/SPIKE 标记）**：S1 实验结论落地后按"假设→验证方式→结论"纪律改写 timer 相关标记（W1-A §③ 同款），逻辑零改动 |
| 7 | `workflow-out/implementation.md` | **改**：追加 W1-B1 节（journal + SPIKE 勾稽 + 实验结论表链接） |
| 8 | `workflow-out/w1b1-topology.md` | **新建**：多节点拓扑文档（实际起法 + 验证输出 + 信任模型差异 + ldk_cargo-cache 卷复用登记 + 人工验证命令清单） |
| 9 | `workflow-out/w1b1-s1-timer.md` | **新建**：S1 结论表（三项实验 a/b/c + native trigger 可用性判定 + 原始输出存档） |
| 10 | `workflow-out/w1b1-s2-oracle.md` | **新建**：S2 认证回合完整证据（命令 + 输出 + 委员会成员编码表/示例数组 + epoch 两阶段激活全程 + ctx.cert.signers 形态与 W1-A ctx 事实交叉核对） |

不动：`types.rs`、`core.rs`（语义冻结）、`committee.rs`、`assessor.rs`、`lyquid/tests/*`（断言不变；39 测试门在工作区根 verify_core 壳执行，见 §②）、`scripts/deploy.sh`（单节点通道保持原样）、ldk 官方克隆（`../ldk`，只运行不落盘）。

---

## ① 目标

1. **T1 多节点拓扑发现**：找到官方多节点 devnet 方案并实际起 ≥2 节点、验证节点间通信，产出可复用的起法文档；若官方方案不可用则如实记录并给出替代方案与信任模型差异。
2. **T2 S1 timer 语义（最高优先）**：部署含 trigger 注册的最小探针，实验 `TriggerMode::Once(ms)`：a) 触发次数（恰一次？——**判定域 = 共识 network 计数 delta：(net_fires − baseline) == 本轮成功 arm 节点数**，每轮 reset→baseline→arm）b) kill/重启全部节点服务后是否重复触发（anvil/registry 保持运行；重启前后读 instance+network 两组计数，如实登记 instance 状态是否复位，节点卷持久不作前提）c) 触发延迟与设定周期比；产出结论表（注明判定域，与 timeout.rs:75-77 SPIKE_1 验收口径对齐）并判定 native trigger 可用/不可用（不可用则记录后转 keeper 模式，不算失败——主方案 keeper+链上守卫已实现）。
3. **T3 S2 委员会认证回合**：移植 price-feed oracle 骨架为探针（去外网依赖），跑通一次 `propose_and_certify` 认证调用 + `set_threshold`，验证 `ctx.cert.signers` 真实形态并与 W1-A ctx 事实交叉核对，产出完整证据（命令+输出）。

**越界防护**：不做 S3 llm、S4 RPC/deal_info 补验、keeper.py（W1-B2 另行调用）。

---

## ② 勘察事实基线（本轮实读，编码员直接引用，不重复发现）

### 官方多节点方案已存在（T1 主通道确认）

- `../ldk/docker/multi/docker-compose.yaml`：**4 节点**（node1-4，全 mesh UPC 内网 `:10080`）+ 共享 `anvil` sequencer（`ws://anvil:8545`，state 持久化卷）+ 本地 OCI `registry:3`（host `:8000`）+ `setup-devnet` bootstrap。host 端口映射 **10087/11087/12087/13087**（compose :48/:57/:66/:75）——与任务预期完全一致。
- 起法（`../ldk/docker/multi/README.md:30-38`）：`docker compose -f docker/multi/docker-compose.yaml up -d`（从 ldk 仓库根执行）。
- bootstrap 幂等序列（compose :11-18）：等 node1 GetNodeInfo → GetLyquidInfo 无 contract 则 `shaker deploy --is-bartender --reference ghcr.io/lyquor-labs/lyquids:bartender-v0.8.1` → 等 GetPeers ≥3 → `shaker availability activate --committee auto --threshold 1`。
- 节点配置（`node1.toml`）：`base="devnet"`、`sequencer="ws://anvil:8545"`、确定性 node_key seed（peer ID 稳定：`Node-j3fcdy…` 等）、`[[peers]]` 指向 node2-4:10080、image fallback repos = 本地 registry 优先。
- **版本对齐利好**：multi 默认全套 **v0.8.1** 镜像（node/tools/bartender reference，compose :2/:16/:44），与 SDK 锁 `rev=fd575e8`（v0.8.1，W1-A D7）完全对齐；比单节点 main-latest（0.8.2-dev）更干净，W1-A 的 `IncompatibleLdk` 风险在此环境不存在同款问题。
- **端口冲突**：单节点 compose（`../ldk/docker-compose.yaml:6`）也绑 host 10087。两 compose 项目目录不同（ldk 根 vs `docker/multi`），compose v2 默认项目名不同（`ldk` vs `multi`），但 host 端口绑定互斥 → **起 multi 前必须先 `docker compose down`（ldk 根项目，保留卷）**，单节点用 `scripts/devnet-up.sh` 随时可恢复。
- **multi 无常驻 tools 服务**（compose 只有 one-shot setup-devnet）→ 探针部署通道见 §③ T2 第 6 步。
- 多节点下 shaker 部署需带 registry reference 与 endpoint（README:103-110 例：`shaker deploy -r 'http://127.0.0.1:8000/lyquids' --endpoint 'ws://127.0.0.1:10087/ws' <Cargo.toml>`）——与单节点 `scripts/deploy.sh` 的差异点，写入拓扑文档。

### S1 timer 平台面（T2 依据）

- `TriggerMode` 枚举：`../ldk/primitives/src/lib.rs:159-168` —— `Recurrent(u64)` / `Once(u64)`（"Trigger once, delayed by the specified milliseconds (0 for immediate)"）/ `Commit`（仅 network functions，slot commit 后）/ `Stop`。
- `trigger!` 宏：`../ldk/lyquid/src/runtime/mod.rs:405-424`，落 host API `lyquor_api::trigger(group, method, input, mode)`（:323）。price-feed 实际用法参照 `trigger!(update_history(), TriggerMode::Commit)`（price-feed/src/lib.rs:412，目标为 instance 方法）。
- **调用与观测通道（修订指令 2 口径，端点基准行）**：W1-A 已证 eth_call 对非-bartender lyquid 回 `Invalid contract address`、view 导出不可 tx 发送（implementation.md:119 实测限制 3，三通道全闭）→ 探针可调用方法一律声明为**非 view 的 `export = eth`**，调用通道 = **容器内**（multi-tools）`cast send <探针> "fn(...)" <args> --rpc-url http://nodeX:10087/api`（fund 先例：`LyquidResult<()>` cast send 实测成功，implementation.md:118 实测限制 2）——**服务名+容器端口：容器内 node2 也是 `node2:10087`，11087/12087/13087 仅宿主侧映射有效**（compose :57/:66/:75）；宿主侧命令（如 T1 curl 探活）用 `127.0.0.1:10087/11087/…` 并标注『宿主』。println 观测一律经 **shaker console 取回**（带端点 `--endpoint ws://nodeX:10087/ws`，或依赖容器 `LYQUOR_ENDPOINT` env，README:85 形态）+ `lyquor_api::systime()`（runtime/mod.rs:311）做时间戳。
- **跨调用 A 档已证**：instance 方法内经 `call!((self_id).方法(命名参数) -> (返回解包))` 调用同 lyquid 的 network 方法（timeout.rs:52-59 实录，basicswap 形态，`ctx.lyquid_id` 为目标）——S1 探针的共识观测面（on_timer → probe_mark_fire）按此落地。
- `timeout.rs` 现存 7 处 SPIKE 标记中 timer 相关项即 S1 验证对象（W1-A §③ 表遗留），实验结论落地后逐处登记改写。
- **SPIKE_1 验收口径**（timeout.rs:75-77）：4 节点 + 过期 deal 下 (a) exactly one refund lands（guard 去重）(b) killing/restarting nodes never double-refunds (c) firing latency < 2x the trigger period——S1 三项实验与之逐条对齐，结论表注明判定域。

### S2 认证平台面（T3 依据，price-feed 骨架逐点对应）

- **state 声明形态**：`network oracle price_feed;`（`../ldk/lyquid-examples/price-feed/src/lib.rs:167`）——oracle 变量在 state! 块内单行声明。
- **initialize**：`Oracle::initialize(&self, ctx, target: OracleTarget, committee: Vec<NodeID>, threshold: u16) -> bool`（`../ldk/lyquid/src/runtime/oracle/source.rs:540`）；epoch=0 才有效。**仅写入 staging（source.rs:536-539）**——configure 后不直接生效，需 advance/finalize epoch 两阶段激活（见 T4 第 3 步）。
- **set_threshold**：`set_threshold(&self, ctx, target, new_thres: u16) -> bool`（source.rs:591）；**epoch=0 恒 false（source.rs:268-271）**、与 staging 相同亦 false——`probe_bump_threshold` 探针直接包它，且必须在激活（epoch>0）之后调用。
- **两阶段组方法**：propose/aggregate 挂 `#[method::instance(group = oracle::two_phase::<state_var>)]`（price-feed:258/:299），认证回调挂 `#[method::network(group = oracle::certified::<state_var>::two_phase)]`（price-feed:399）。
- **认证调用**：`o.propose_and_certify(&mut ctx, target, init_params: Bytes, None, None) -> LyquidResult<Option<CertifiedCallParams>>` + `submit_certified_call!(call)`（price-feed:458-468）。
- **ctx.cert.signers 形态**：`ctx.cert.signers.clone()` → 逐个 `ctx.signer_node_id(signer_id as u64)` 映射为 `Vec<NodeID>`（price-feed:401-406）——**signers 原始形态是数字 signer id 列表（u64 域），需映射**。这与 W1-A 实测的 `CallContext`（仅 origin/caller/input/lyquid_id/node_id 字段，`$V7/lyquid/src/lib.rs:162`）交叉核对：`cert` 是 network 方法 ctx 上认证回调特有的附加字段，W1-B1 实测其真实类型与内容并登记。
- **委员会配置**：`configure_committee`（price-feed:207-236）——官方版 initializer 专属守卫 + `threshold = len/2+1`（**探针版显式传 threshold，守卫改平台内建 `eth_guard = creator`——冷读仲裁修订，见 §④；平台仅自动执行名为 `constructor` 的函数（ldk lib.rs:59-66 文档 + proc lib.rs:355-370 特判），probe_constructor 不会部署期执行，initializer state 恒 ZERO 会使镜像守卫拒绝一切 caller，故一并删除**）；multi bootstrap 的 `availability activate --committee auto --threshold 1` 已把 4 节点注册为 **availability 委员会**（README:76-77），oracle 委员会是 lyquid 内独立配置。**成员来源与编码（修订指令 1）**：主通道 = **GetNodeInfo×4**（宿主 `127.0.0.1:10087|11087|12087|13087` 或容器内 `node1-4:10087`，取 `.node_id.value`，官方 demo.sh:186-198 同款）；GetPeers 仅作交叉核对，且必须**四节点 GetPeers 结果取并集**（单次调用自排除只得 3 个）。**编码转换**（镜像官方 demo.sh:190-215 Python 段）：`.node_id.value` 去 `"Node-"` 前缀 → base32 解码（补 `=` padding，长度须 35 字节）→ 取前 32 字节 → `"0x" + hex`；ABI 面形态 = `bytes32[]`（官方 run.sh:256 `configure_committee(bytes32[])` 实证）。
- **oracle 激活两阶段（host 内建方法，官方 demo_activate_oracle = demo.sh:307-362；冷读仲裁修订：全程 cast send 提交＋观测驱动，无"返回 true"门）**：configure 仅入 staging；激活 = `__lyquor_oracle_advance_epoch(string,address,bool)`（topic = oracle state 变量名，address = `shaker to-hex <LyquidID>`，demo.sh:183 同款）**cast send 提交——回执仅证已提交（cast send 不承载函数 bool 返回；官方 demo 的 advance/finalize 走 cast call 读 bool——demo.sh demo_call_at——本环境 eth_call 已证不可用故不采用）** → **等 destination epoch 推进**（`__lyquor_oracle_dest_epoch_info` 面 = runtime/oracle/mod.rs:91-102 + internal.rs:196；advance 前记 dest epoch 为 old，轮询至 new>old，官方 demo_oracle_epoch 同款语义，60s deadline；**等待条件不得用 get_epoch——StateVar::get_epoch 读 current.epoch（source.rs:583-588→:289-291），current 仅 finalize_epoch 写入（source.rs:409），finalize 前恒 0 = 死等**；观测实现 = probe_config 的 dest epoch 打印（§④），不可达则 probe_dest_epoch 包装方法 cast send＋console println，SPIKE 登记最终形态）→ `__lyquor_oracle_finalize_epoch(string,address,bool)` 同为 cast send 提交＋观测确认 → finalize 后 probe_config 确认 **get_epoch>0 且 current 生效**（get_epoch 的正确用法仅在 finalize 后；官方 demo_wait_for_committee 语义，run.sh:258）。**重发一律由"观测不满足"驱动，禁止以任何"返回 true"为门**。
- **threshold=1 语义**（README:76）："preserves single-endpoint pushes while still exercising registry-backed cross-node certification and Pending → Live transition"——S2 主回合用 threshold 1 单端点跑通；threshold 2 双节点聚合列为可选加分项（时间允许才做）。

### 现有代码挂载点

- crate 根 = `trustbridge/lyquid/`（`Cargo.toml` name="trustbridge"，cdylib+rlib）。`lib.rs:18-22` 五个 `pub mod`；state! 块 lib.rs:35-50（network 7 字段 + instance 2 字段）。W1-A 方法面：faucet/create_deal/fund/notarize/submit_deliverable/complete/claim_timeout/cancel/open_dispute/apply_committee_verdict/committee_config/deal_info（lib.rs:188-473 等）。
- 测试门（修订指令 3 口径）：**lyquid crate 本体在宿主不可跑 `cargo test`**（实测 4 错 NativeGuestAbi，指令给定）。39 断言经**工作区根 verify_core 壳**执行：`../workflow-out/verify_core`（相对 trustbridge；独立临时 crate，以 `#[path]` 直编仓库内 types.rs/core.rs、零平台依赖、包名 trustbridge 使 `use trustbridge::core` 原样解析——其 Cargo.toml 头注释实读），命令 `cd workflow-out/verify_core && cargo test --lib --tests`（工作区根起算），仲裁人实跑 = 39/39（指令给定）。探针纯增量不触 types/core，壳测试不受影响；部署产物编译核验维持容器内 `cargo check --target wasm32-unknown-unknown`。
- 部署通道（W1-A 固化）：宿主无 shaker；docker cp 源码入 `ldk-tools-1` 容器 + 容器内 shaker deploy（`scripts/deploy.sh`）。multi 环境无该容器，见 §③ T2 第 6 步。

---

## ③ 子任务拆分与执行顺序

> 每个 T 完成即写 `workflow-out/implementation.md` journal（GLM 5 小时窗口中断恢复点）；中断即停，续跑从 journal 恢复，不压缩验证步骤。

### T0 基线核对（不写代码）
1. `cd trustbridge && git status`（确认干净、HEAD=f83ab52）+ `git log --oneline -3`。
2. `cd workflow-out/verify_core && cargo test --lib --tests 2>&1 | tail -5`（工作区根起算；壳以 #[path] 直编 types/core，不触探针）—— 39/39 全绿基线存档 `trustbridge/workflow-out/w1b1-t0-baseline.txt`。
3. `docker ps` 记录单节点 devnet 现状（ldk-node-1 / ldk-tools-1 healthy）。

### T1 多节点拓扑发现与实测（交付 w1b1-topology.md）
1. `docker compose -p ldk -f ../ldk/docker-compose.yaml down`（停单节点，保留卷）。
2. `docker compose -f ../ldk/docker/multi/docker-compose.yaml up -d`；`logs -f setup-devnet` 观察 bootstrap 三步（bartender 幂等部署 → GetPeers≥3 → availability activate）。
3. 节点间通信验证（四节点逐一 + mesh）：
   - 【宿主】`curl -s --data '{}' -H 'content-type: application/json' http://127.0.0.1:10087|11087|12087|13087/lyquor.node.v1.NodeService/GetNodeInfo` ×4；
   - `GetPeers` ×4（每节点应见 ≥3 peers，Node-ID 与 node1-4.toml 预置 peer ID 比对）；
   - `GetLyquidInfo` ×4（同一 bartender contract 全网可见 = 跨节点状态同步证据）；
   - `shaker availability status --endpoint ws://node1:10087/ws`（经 setup-devnet 容器跑，README:68-70）。
4. 全部原始输出存档进 `w1b1-topology.md`（含起停/回退命令、与单节点通道差异表、**ldk_cargo-cache 卷复用登记**——`docker volume ls` 本轮实测存在该命名卷；fd575e8 git db 在卷内、down 不清卷（指令给定），multi-tools 与 setup-devnet 退路共用它免重拉依赖，无需"down 前拷贝 db"步骤、信任模型：anvil 单 sequencer 排序 + registry 分发 + availability gate 委员会 ≠ 生产拜占庭假设，如实登记为 W1-B 后续边界条件）。
5. **失败降级路径**（如实记录，不编造）：若镜像拉取失败/起不来 → 记录失败输出，降级为"单节点 + 如实标注"跑 S1/S2（b 实验"重启全部节点"=重启单节点，标注降级），并在拓扑文档给出多容器互联替代方案讨论及信任模型差异。

### T2 探针代码（S1+S2 一次成型，一次部署）
1. **先验 R1**（state! 单例性）：读 `state!` 宏定义（`grep -rn "macro_rules! state" ../ldk/lyquid/src/`），确认可否在子模块二次调用。可行 → probe 模块自带 state!；不可行 → 探针字段并入 lib.rs state! 块末尾（追加 `probe_*` 前缀字段，主 escrow 9 字段零改动）。**判定以 `cargo check` 实际编译结果为准**。
2. 写 `probe/s1_timer.rs`（§④ 详设）。
3. 写 `probe/s2_oracle.rs`（§④ 详设，propose 返回内生成值，**零外网 HTTP**——规避容器出网不确定性，price-feed 的 Binance/Coinbase fetch 全部剔除）。
4. `lyquid/src/lib.rs` 挂载（清单 #4 的 1-2 处最小改动）。
5. 测试门 + 编译核验：`cd workflow-out/verify_core && cargo test --lib --tests`（39/39 保持，工作区根起算）→ 存档输出；部署产物编译核验 = **容器内** `cargo check --target wasm32-unknown-unknown`（W1-A T3 惯例；探针代码进 wasm cdylib 面，lyquid 本体宿主 cargo test 不跑——NativeGuestAbi 4 错实测，修订指令 3）。
6. **部署到 multi node1**：起临时工具容器并**复用单节点项目的 cargo 命名卷**（`ldk_cargo-cache`，`docker volume ls` 本轮实测存在；fd575e8 git db 在卷内、down 不清卷——免重拉依赖，无需"down 前拷贝 db"步骤，修订指令 4）：`docker run -d --name multi-tools --network multi_default -e LYQUOR_ENDPOINT=ws://node1:10087/ws -v ldk_cargo-cache:/usr/local/cargo <lyquor-tools:v0.8.1 镜像> sleep infinity`（替代单节点 ldk-tools-1 角色；`LYQUOR_ENDPOINT` env 使容器内 shaker console 默认指向 node1——单节点 compose tools 同款 env 机制）→ `docker cp lyquid multi-tools:/tmp/tb` → 容器内 `shaker deploy -r http://registry:8000/lyquids --endpoint ws://node1:10087/ws --private-key <anvil#0> Cargo.toml`（reference+endpoint+private-key 三参数，README:103-110 + demo.sh:166-167 官方先例——**deploy signer 与后续 cast send 同用 anvil#0 钥，S2 的 eth_guard=creator 守卫才匹配（冷读仲裁修订）**）。若临时容器方案受阻，退路 = `docker compose -f docker/multi/docker-compose.yaml run --rm -v ldk_cargo-cache:/usr/local/cargo setup-devnet bash`（同镜像同网络同卷）。部署输出存档；卷复用事实登记进拓扑文档。

### T3 S1 timer 实验（最高优先，交付 w1b1-s1-timer.md）
实验环境 = T1 multi（4 节点）；T1 失败则单节点降级并标注。
- **0) 通道先行证明（前置硬门，修订指令 2）**：首个实验前，于 node1 完成一次真实 `probe_arm` 调用——**容器内（multi-tools）** `cast send <探针地址> "probe_arm(uint64)" 5000 --private-key <anvil#0> --rpc-url http://node1:10087/api`（服务名+容器端口；fund 先例 implementation.md:118）——并以 `shaker console --endpoint ws://node1:10087/ws <探针>` 取回 arm 登记 println（容器 env `LYQUOR_ENDPOINT` 已设则可省 `--endpoint`，**存档实际生效命令**）；**命令与输出存档进 w1b1-s1-timer.md，未存档不得进入实验 a/b/c**。若当轮实测证明 shaker console 可带参调用并存档，方可将后文"cast send 调用"措辞改为 console 通道（默认不走此径）。
- **a) 触发次数（判定域 = 共识 network 计数，delta 口径——冷读仲裁修订）**：先等步骤 0 的 5000ms 触发落地（观测其 NET FIRE println 或等 ≥5s）→ cast send `probe_reset_net` 清零 network 计数 → `probe_get_report()` 记 **baseline** → 于指定节点集逐节点 arm（**至少 node1+node2**；均在容器内执行，通道分别为 `--rpc-url http://node1:10087/api` 与 `--rpc-url http://node2:10087/api`——**容器内 node2 端口是 10087 不是 11087**，11087 仅宿主侧映射；delay=5000；**分母 = 各节点 arm println 实际成功登记数，非计划 armed 数**）→ 周期轮询 `probe_get_report()`（cast send 触发 + shaker console `--endpoint ws://nodeX:10087/ws` 取回 println，报告打包 instance+network 两组计数）至触发后再观察 ≥3 个周期 → **exactly-once 判定 = (probe_net_fires − baseline) == 本轮成功 arm 节点数**（instance probe_fires 仅作节点本地对照，如实登记）。
- **b) kill/重启节点服务（anvil/registry 保持运行，修订指令 2）**：`docker compose -f docker/multi/docker-compose.yaml kill node1 node2 node3 node4 && docker compose -f docker/multi/docker-compose.yaml up -d`——**只杀节点服务**，规避 SIGKILL 丢 anvil `--state`（anvil 仅退出时落盘、无 --state-interval）导致链回退、network 计数比对失效；该口径与 SPIKE_1 验收"killing/restarting nodes"（timeout.rs:76）域一致，结论表注明。up 后：bootstrap 重跑行为如实存档 → **读数比对前先记链连续性证据**（`cast block-number --rpc-url http://node1:10087/api`（容器内）与 GetLyquidInfo 输出各一次，与重启前比对）→ node1/node2 两条容器内通道分别再调 `probe_get_report()` → **重启前后两组计数逐项登记**：network 计数是否增加（重复触发判定，判定域）；instance 计数是否复位（**"节点数据卷持久"不作前提，降级为待观测项，以实测为准**）。
- **b+) 链重置观测（可选独立小节，不作判定依据）**：如需另测全栈 kill（含 anvil，链状态可能回退/重置），单列小节标注『链重置观测』，仅登记现象，**不得作为重复触发判定依据**（判定只认实验 b 的节点服务重启域）。
- **c) 触发延迟与周期比**：对 delay ∈ {2000, 5000, 10000}（至少 3 组）**每组重复同一 reset→baseline→arm→delta 序列（冷读仲裁修订）**，记录每组 (last_fire_at − registered_at, 设定 ms) 比值（对照 SPIKE_1 验收 (c)：latency < 2x period，timeout.rs:77）；Recurrent(2000) 补一组对照（周期性佐证，可选）。
- 每步命令+原始输出存档；**结论表（注明判定域 = 共识 network 计数，与 timeout.rs:75-77 SPIKE_1 验收逐条对齐）**：实验/观测/结论/对主方案影响（native trigger 可用 → keeper 之外多一路径；不可靠 → 登记 + 主方案转 keeper 模式，不算失败）。
- 结论落地：改写 `timeout.rs` timer 相关 SPIKE 标记（假设→验证方式→结论三列登记，逻辑不动）。

### T4 S2 认证回合（交付 w1b1-s2-oracle.md）
1. **成员获取与编码（修订指令 1）**：GetNodeInfo×4 取 `.node_id.value`（宿主 `127.0.0.1:10087|11087|12087|13087`，容器内 `node1-4:10087`）；GetPeers×4 结果**取并集**作交叉核对（单次调用自排除只得 3 个）。按 demo.sh:190-215 转换：去 `"Node-"` 前缀 → base32 解码 35 字节 → 前 32 字节 → `"0x"+hex`；4 个预解码值（node1-4.toml 预置 peer ID 可预先离线换算）作为**示例数组写入 w1b1-s2-oracle.md**（实跑值以 GetNodeInfo 实测为准）。
2. **configure**：容器内 `cast send <探针> "probe_configure(bytes32[],uint16)" "[0x…,0x…,0x…,0x…]" 1 --private-key <anvil#0> --rpc-url http://node1:10087/api`（数组 = 第 1 步 4 个 hex；`Vec<NodeID>` 的 ABI 面即 bytes32[]，threshold=1；**守卫 = 平台内建 `eth_guard = creator`（冷读仲裁修订）——cast send 与 shaker deploy 用同一 anvil#0 钥即匹配**；内部 `cert_probe.initialize(...)` **仅入 staging**），`shaker console --endpoint ws://node1:10087/ws <探针>` 取回 println。
3. **激活两阶段（插在 configure 与 run_round 之间；镜像 demo.sh:307-362 + run.sh:255-259；冷读仲裁修订：cast send 提交＋观测驱动）**：
   a. `cast send <探针> "__lyquor_oracle_advance_epoch(string,address,bool)" "cert_probe" "$(shaker to-hex <探针LyquidID>)" false --rpc-url http://node1:10087/api`——topic = oracle state 变量名 `cert_probe`，address = shaker to-hex 的 lyquid ID（demo.sh:183 同款）；**cast send 回执仅证已提交（不承载 bool 返回；官方 demo 的 advance/finalize 走 cast call 读 bool——demo.sh demo_call_at——本环境 eth_call 已证不可用，不采用"轮询至返回 true"口径）**，提交后按 b 观测。
   b. **等 destination epoch 推进**：advance 前记 dest epoch 为 old（`probe_config()` 的 dest epoch 打印，见 §④；底层 = `ctx.network.__internal.oracle_dest_epoch_info`——internal.rs:196 / oracle/mod.rs:91-102 面，可达性以编译/实测为准，不可达则另设 `probe_dest_epoch` 包装方法 cast send＋console println，SPIKE 登记最终形态）→ 轮询至 new>old（60s deadline，官方 demo_oracle_epoch 同款语义）；**观测不满足才重发 a 的 cast send——重发由观测驱动，禁止以任何"返回 true"为门**。**不得以 get_epoch 作等待条件**：StateVar::get_epoch 读 current.epoch（source.rs:583-588→:289-291），current 仅 finalize_epoch 写入（source.rs:409），finalize 前恒 0 = 死等。
   c. `cast send <探针> "__lyquor_oracle_finalize_epoch(string,address,bool)" "cert_probe" "$(shaker to-hex <探针LyquidID>)" false --rpc-url http://node1:10087/api`（**同为 cast send 提交＋观测确认**）→ `probe_config()` 确认 **get_epoch>0 且 current 阈值/委员会生效**（get_epoch 的正确用法仅在 finalize 后；对照官方 demo_wait_for_committee 4 语义）。
   d. **epoch 转变全程记入 w1b1-s2-oracle.md**：旧/新 **dest** epoch、finalize 后 current epoch、current/staging 阈值变化、各节点可见性（node2 通道 probe_config 对照）。
4. 激活确认后才 `probe_run_round()`（容器内 cast send + console 取回；内部 `propose_and_certify` + `submit_certified_call!`）→ console 观察触发序列：propose println → aggregate println → certified 回调 `probe_on_certified` println（**打印 ctx.cert.signers 原始值、逐元素类型、映射后 NodeID**）。
5. `probe_bump_threshold(2)`（**必须 epoch>0，否则 source.rs:268-271 恒 false**）→ console 取回 set_threshold 返回值 println；`probe_config()` 同法读 current/staging 配置回显（epoch/threshold 变化）。
6. （可选加分，时间允许）node2 上同法 run_round，验证 threshold=2 双签聚合后 signers 长度=2。
7. 证据整编：完整命令+输出 + 委员会成员编码表（含示例数组）+ epoch 激活全程 + **ctx.cert.signers 形态结论**（原始域/映射关系/与 W1-A CallContext 事实的交叉核对表）。

### T5 收尾与提交
1. `implementation.md` 追加 W1-B1 节（journal、SPIKE 勾稽更新——新增探针标记逐处登记、S1/S2 结论指针、遗留 W1-B2 边界条件）。
2. 三份 w1b1-*.md 补人工验证命令清单（拓扑文档尾部汇总版：从零复现全部实验的命令序列）。
3. 测试门终跑：`cd workflow-out/verify_core && cargo test --lib --tests` 39/39 存档（T0/T5 双端存档，工作区根起算）；`git add` 上述 10 文件，单提交（信息：W1-B1 platform probes: multi-node topology + S1 timer semantics + S2 certification round）。
4. 环境处置：`multi-tools` 临时容器 `docker rm -f`；multi 栈保留运行（W1-B2 可能复用）并在文档注明恢复/切换单节点命令。

---

## ④ 逐文件改动点详设

### 1. `lyquid/src/probe/mod.rs`（新建）
- 模块文档注释：用途（W1-B1 平台探针）、纪律（SPIKE 登记、实验后标记处置）、不进 escrow 主路径的边界声明。
- `pub mod s1_timer;` + `pub mod s2_oracle;`。
- SPIKE(W1-B1) 起始标记清单锚点（登记于 implementation.md）。

### 2. `lyquid/src/probe/s1_timer.rs`（新建，最小 trigger 面，instance+network 双观测域）
- state（并入或模块内，随 R1 判定）：
  - instance 域：`probe_fires: u64 = 0;`、`probe_registered_at_ms: u64 = 0;`、`probe_last_fire_at_ms: u64 = 0;`、`probe_arm_delay_ms: u64 = 0;`
  - **network 域（共识观测面，修订指令 1）**：`probe_net_fires: u64 = 0;`、`probe_net_last_fire_ms: u64 = 0;`
- `#[method::instance(export = eth)] pub fn probe_arm(ctx: &mut _, delay_ms: u64)`（**非 view**，cast send 通道）：清零 instance 计数、`systime()` 记 registered_at、存 delay、`trigger!(probe_on_timer(...), TriggerMode::Once(delay_ms))`、println 登记（含节点标识，配合多节点 arm 对照）。
- `#[method::instance] fn probe_on_timer(...)`（trigger 目标，无 export）：instance `probe_fires += 1`、`systime()` 记 last_fire_at、println "FIRE #n at t=…"，随后**经 `call!` 调 network 方法 `probe_mark_fire` 落共识计数**（形态镜像 timeout.rs:52-59 已证 A 档：`call!((self_id).probe_mark_fire(fired_at_ms: u64 = t) -> (ok: LyquidResult<bool>)).ok?`）。**SPIKE(W1-B1)**：目标方法签名/参数编码形态以 trigger! 宏展开（runtime/mod.rs:405-424 encode_by_fields!）与 price-feed update_history 同款为准，编译不过即按 rustc 报错修正并登记。
- `#[method::network(export = eth)] pub fn probe_mark_fire(ctx: &mut _, fired_at_ms: u64) -> LyquidResult<bool>`（**非 view**，cast send 亦可达）：network `probe_net_fires += 1`、`*probe_net_last_fire_ms = fired_at_ms`、println "NET FIRE #n"——**exactly-once 判定域**。
- `#[method::network(export = eth)] pub fn probe_reset_net(ctx: &mut _)`（**非 view**，cast send 可达，形态同 probe_mark_fire；冷读仲裁修订）：清零 `probe_net_fires`/`probe_net_last_fire_ms` + println 确认——实验 a/c 每轮 **baseline 前置步骤**。
- `#[method::instance(export = eth)] pub fn probe_get_report(ctx: &mut _)`（**非 view**，返回 `LyquidResult<()>`——`()` 返回 cast send 不受影响，fund 先例 implementation.md:118；观测走 println）：println JSON 串一次打包 **instance 域（fires/registered_at/last_fire_at/delay）+ network 域（net_fires/net_last_fire_ms）两组计数**——console 单次调用取全量观测。
- 对照组 `probe_arm_recurrent(interval_ms)`（Recurrent，实验 c 可选）。

### 3. `lyquid/src/probe/s2_oracle.rs`（新建，price-feed 骨架去外网移植）
- **通道纪律（修订指令 2；端点口径同 §② 基准行）**：本文件全部可调用方法（configure/run_round/bump_threshold/config，及如需的 dest_epoch 包装）一律**非 view 的 `export = eth`**（constructor 已删，见下——冷读仲裁修订）；调用 = **容器内** cast send `--rpc-url http://nodeX:10087/api`（服务名+容器端口，node2 容器内亦为 10087；11087/12087/13087 仅宿主侧），println 观测 = `shaker console --endpoint ws://nodeX:10087/ws` 取回（T4 措辞同此）。
- state：`network oracle cert_probe;`（对齐 price-feed:167 oracle 声明形态；**initializer state 字段删除——冷读仲裁修订：平台仅自动执行名为 `constructor` 的函数（ldk lib.rs:59-66 + proc lib.rs:355-370 特判），probe_constructor 不部署期执行，initializer 恒 ZERO 只会让镜像 price-feed:209-213 的守卫拒绝一切 caller**）、`network probe_rounds: u64 = 0;`、`network probe_last_signers_raw: Vec<u64> = Vec::new();`、`network probe_last_signers_nodes: Vec<String> = Vec::new();`、`instance probe_propose_count: u64 = 0;`。
- **probe_constructor 删除（冷读仲裁修订）**：平台只自动执行名为 `constructor` 的函数（proc lib.rs:356-370 仅对 `func.sig.ident == "constructor"` 特判；ldk lib.rs:59-66：必须命名 constructor、network、无返回），probe_constructor 不会部署期执行——探针不设 constructor，configure 守卫改走平台内建 `eth_guard = creator`；**不得给共享 escrow crate 加真 constructor**（现无 constructor，加了改变主合约部署行为，另案分析）。
- `#[method::network(export = eth, eth_guard = creator)] pub fn probe_configure(ctx: &mut _, node_ids: Vec<NodeID>, threshold: u16) -> LyquidResult<bool>`（cast send ABI 面 = `probe_configure(bytes32[],uint16)`，成员编码见 §② 委员会配置条）：**守卫 = 平台内建 `eth_guard = creator`（官方 `__lyquor_oracle_initialize` 同款，runtime/oracle/mod.rs:147；合法域 = mutable network eth 导出 main/node group，proc lib.rs:950-961——默认 main group 满足，编译报域错按此调整并 SPIKE 登记；无 initializer 守卫分支，冷读仲裁修订）** + 非空校验 + `OracleTarget{seq_id: sequence_backend_id()?, target: LVM(ctx.lyquid_id)}` + `cert_probe.initialize(...)`（price-feed:207-236 逐点镜像；**仅入 staging，激活两阶段见 T4 第 3 步**）。
- `#[method::instance(group = oracle::two_phase::cert_probe)] fn probe_propose(ctx: &mut _, avg_num: u16, target: OracleTarget) -> LyquidResult<ProbeProposal>`：返回内生成提案（round 序号 + 本节点标识 + systime），**零 HTTP**；println 观测。
- `#[method::instance(group = oracle::two_phase::cert_probe)] fn probe_aggregate(ctx: &_) -> LyquidResult<Option<CertifiedCallParams>>`：镜像 price-feed:299-360（inputs 数 ≥ avg_num → 聚合 → 构造 CertifiedCallParams）；SPIKE(W1-B1) 标记聚合返回构造细节，以编译+实跑为准。
- `#[method::network(group = oracle::certified::cert_probe::two_phase)] fn probe_on_certified(ctx: &mut _, payload: ProbeRound)`：**核心观测点**——println `cert.signers` 原始值（含类型形态）、逐个 `ctx.signer_node_id(id as u64)` 映射结果（price-feed:400-406 镜像）、写 network 记录、`probe_rounds += 1`。
- `#[method::instance(export = eth)] pub fn probe_run_round(ctx: &mut _) -> LyquidResult<bool>`：`propose_and_certify(&mut ctx, target, encode(avg_num=1, target), None, None)` + `submit_certified_call!`（price-feed:447-472 镜像）+ println 各阶段。
- `#[method::instance(export = eth)] pub fn probe_bump_threshold(ctx: &mut _, new_thres: u16) -> LyquidResult<bool>`：包 `cert_probe.set_threshold(target, new_thres)`（source.rs:591 面；**epoch=0 恒 false——须在激活后调用**）+ println 返回值。
- `#[method::instance(export = eth)] pub fn probe_config(ctx: &_)`：println `config_current/config_staging/get_epoch`（source.rs:562-589 面）**+ dest epoch（冷读仲裁修订：读 `ctx.network.__internal.oracle_dest_epoch_info(topic, full_config)`——internal.rs:196 / runtime/oracle/mod.rs:91-102 面；可达性以编译/实测为准，不可达则另设 `probe_dest_epoch` 包装方法 cast send＋console println，SPIKE 登记最终形态）——T4-3b 的等待观测源**。

### 4. `lyquid/src/lib.rs`（最小挂载）
- `pub mod probe;`（`pub mod assessor;` 之后一行）。
- 文件头 W1 注释块补一行：W1-B1 探针已挂载、指向 probe/mod.rs 与 w1b1-*.md。
- （仅 R1 判定需要时）state! 块末尾追加探针字段（S1 network 域 probe_net_fires/probe_net_last_fire_ms + S1 instance 域 + S2 域，均 probe_ 前缀），块内加注释行"probe state (W1-B1)，主 escrow 字段零改动"。

### 5. `lyquid/Cargo.toml`
- 预期零改动。`OracleTarget/CertifiedCallParams` 等类型若不在默认导出面而需 feature，仅改 lyquid 依赖行的 features 数组（裁定 1 传递 crate 豁免路径），逐行注释登记；**任何情形不新增 crate**。

### 6. `lyquid/src/timeout.rs`（仅 T3 结论落地）
- 编码员先读全文，列出 timer 相关 SPIKE 标记清单 → T3 结论表逐处对应改写（假设→验证方式→结论，W1-A §③ 三列纪律）；不改任何逻辑/签名/断言。

### 7-10. 文档四件
- `w1b1-topology.md`：§③-T1 的全部内容（起法/验证输出/差异表/**ldk_cargo-cache 卷复用事实**/信任模型/降级记录）+ 人工验证命令清单汇总。
- `w1b1-s1-timer.md`：实验 a/b/c 命令与原始输出 + 结论表 + native trigger 判定 + keeper 模式衔接说明。
- `w1b1-s2-oracle.md`：T4 全部命令与输出 + ctx.cert.signers 形态结论 + W1-A CallContext 交叉核对表。
- `implementation.md`：W1-B1 节（T0-T5 journal、SPIKE 新增/处置勾稽、结论指针、W1-B2 边界）。

---

## ⑤ 风险与回退

| # | 风险 | 缓解 | 回退 |
|---|---|---|---|
| R1 | `state!` 宏 crate 级单例，probe 模块内二次调用编译失败 | T2 第 1 步先读宏定义 + cargo check 实判 | 探针字段并入 lib.rs state! 块末尾（追加不改旧），硬约束"不污染主路径"仍满足（方法/逻辑独立成文件） |
| R2 | multi 镜像（ghcr v0.8.1 全家桶 + bartender reference + registry:3 + anvil foundry）拉取失败 | 逐服务 `docker compose up <svc>` 分步定位；失败输出如实存档 | 降级单节点跑 S1/S2（b 实验降级语义如实标注），拓扑文档记录 + 替代方案讨论；不算任务失败 |
| R3 | 10087 端口互斥导致单节点/多节点切换踩坑 | §③-T1 显式 `-p ldk down` 先停单节点 | 单节点 `scripts/devnet-up.sh` 恢复；multi `down`（保留卷）/`down -v`（重置） |
| R4 | multi 无常驻 tools 容器，部署通道形态变化 | 临时容器 `multi-tools` **复用 `ldk_cargo-cache` 命名卷**（`docker volume ls` 本轮实测存在；fd575e8 git db 在卷内、down 不清卷，免重拉依赖——§③-T2 第 6 步双通道同挂该卷，修订指令 4） | setup-devnet `run --rm -v ldk_cargo-cache:/usr/local/cargo` 通道；再不行退单节点部署（S1/S2 语义仍在，跨节点项标注降级） |
| R5 | native trigger 不可靠（Once 不触发/重启重放/延迟漂移） | 三项实验即为其探测；探针 println 全程留痕 | 主方案不依赖 native trigger（keeper + 链上守卫已实现）：记录后转 keeper 模式，登记 implementation.md，**不算失败** |
| R6 | S2 认证回合卡在 aggregate/两阶段组细节（宏 group 命名、CertifiedCallParams 构造） | price-feed 逐行镜像 + rustc 报错驱动修正 + SPIKE 登记 | threshold=1 + 单节点 propose 已足够验证 ctx.cert.signers 形态（README:76 语义）；跨节点双签列为可选加分不阻塞 |
| R7 | `shaker deploy --update` 状态重置（deploy.sh 头注释已警示） | 探针实验幂等：arm 清零 instance 计数、**每轮实验前 cast send `probe_reset_net` 清零 network 计数（冷读仲裁修订）**，reset→baseline→arm→delta 序列自洽 | 需要状态延续时重新 arm/reset 并在结论表标注轮次 |
| R12 | `eth_guard = creator` 实跑校验不过（creator 记录与 cast send 签名者不一致） | deploy 与 cast send 同用 anvil#0 钥（T2 第 6 步 `--private-key`，demo.sh:166-167 先例）；合法域条件（proc lib.rs:950-961）编译期即暴露 | 退路 = 恢复 `export = eth` 的 `probe_set_initializer`（T4 步骤 2 前显式 cast send 钉 caller）并如实存档（冷读仲裁修订备选）；**不得给共享 escrow crate 加真 constructor**（现无 constructor，加了改变主合约部署行为，另案分析） |
| R8 | GLM 配额 5 小时窗口中断 | 每个 T 收尾即写 implementation.md journal；中断即停不压缩验证 | 续跑从 journal 恢复（T 序号即断点粒度） |
| R9 | 误碰 W1-B2 范围（S3/S4/keeper.py） | 本计划无对应文件；代码审查对照受影响文件清单 | — |
| R11 | cast send 通道对探针方法不可达（参数编码/返回型被节点拒） | §③-T3 第 0 步前置硬门先行证明，未存档不进实验；方法签名按 fund 先例收敛（基础类型参数 + `LyquidResult<()>`/bool 返回） | 实测失败输出存档；必要时收敛签名形态（如 Vec<NodeID> 改逐个 add）重编译重部署，SPIKE 登记 |
| R10 | verify_core 壳 39/39 或类型冻结被破坏 | T0 基线存档 + T2/T5 两端 `cd workflow-out/verify_core && cargo test --lib --tests` 对照（工作区根起算）；探针纯增量不触 types/core | git 单提交整体回退（探针全新增文件，checkout 即净） |

---

## ⑥ 验收口径（编码员自检 + 审查员核对）

1. 测试门：`cd workflow-out/verify_core && cargo test --lib --tests` = 39/39（工作区根起算；T0 与 T5 双端存档输出）；部署产物编译核验 = 容器内 `cargo check --target wasm32-unknown-unknown`；全文不以 lyquid 本体宿主 cargo test 为门（NativeGuestAbi 4 错实测）。
2. 多节点：4 节点 GetNodeInfo + GetPeers≥3×4 + GetLyquidInfo 同 contract×4 真实输出 + ldk_cargo-cache 卷复用登记，均在 `w1b1-topology.md`。
3. S1：**通道先行证明在前**（probe_arm 容器内 cast send + console 带端点取回，命令与输出存档，未存档不进实验）；a/b/c 三实验各有命令+原始输出；a 判定域 = 共识 network 计数 **delta 口径：(probe_net_fires − baseline) == 本轮成功 arm 节点数**（每轮 reset→baseline→arm，至少 node1+node2，容器内服务名端点 nodeX:10087，分母 = arm println 实际成功数；冷读仲裁修订）；b 只杀节点服务（anvil/registry 保持运行），读数前有链连续性证据（block-number/GetLyquidInfo 前后比对），重启前后 instance+network 双组计数逐项登记（"节点数据卷持久"不作前提）；全栈 kill 仅在『链重置观测』独立小节且不作判定依据；结论表含 native trigger 判定（可用/不可用二选一，不可用附 keeper 衔接说明），判定域与 timeout.rs:75-77 SPIKE_1 验收对齐。
4. S2：成员来源 GetNodeInfo×4（GetPeers 并集交叉核对）+ 编码转换表（含示例数组）；configure（`probe_configure(bytes32[],uint16)`，`eth_guard = creator` + deploy/cast 同钥 anvil#0）→ **两阶段激活：advance 提交 → dest epoch 推进（probe_config dest epoch 观测，观测不满足驱动重发）→ finalize 提交 → get_epoch>0 且 current 生效确认（冷读仲裁修订，无"返回 true"门）** → run_round → on_certified println（cast send + console 取回）+ set_threshold 返回值（epoch>0 后）+ ctx.cert.signers 原始形态与映射后 NodeID + epoch 转变全程，全部真实输出在 `w1b1-s2-oracle.md`。
5. `timeout.rs` timer SPIKE 标记按三列纪律登记处置，逻辑零改动（diff 仅注释）。
6. 无新增直接依赖；`Cargo.toml` 若动仅 feature 行且带登记注释。
7. implementation.md W1-B1 节完整，含 journal 与断点恢复说明。
