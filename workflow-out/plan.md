# W1-A 段开发计划与变更方案（S5 宏漂移审计编译清零 + escrow 上 devnet 走到 Funded）

代码基线 = `912a4ae`（其上仅两个 docs 提交，HEAD=`4a8528a`）。本方案全部"基线事实"于本轮勘察实测（命令与出处见 §1）；任务给定且本轮未复跑的环境事实（devnet/bartender/壳 39/39）单列并标注。

---

## 0. 受影响文件清单（供审查员核对，共 11 项）

仓库内（trustbridge，9 个）：

| # | 文件 | 性质 |
|---|------|------|
| 1 | `trustbridge/lyquid/src/lib.rs` | **改**：S5 主体——prelude 导入、15 个方法 ctx 签名改写（占位 `_` 仅限宏标注签名）、**状态访问单点 reborrow `let state = &mut *ctx.network`**（体内 `state.<field>`，标量 `*` 解引用）、helper 状态穿参、错误构造替换、`require`/`caller_agent` 具体类型化（`&Address`/`&__lyquid::NetworkState`，先转 AgentId 再比较）、`current_slot` 落地、10 处标记处置/登记（含文件头 :8；守卫矩阵/桥接结构/fail-closed 语义不变） |
| 2 | `trustbridge/lyquid/src/timeout.rs` | **改**：补 `use lyquid::prelude::*`、`call!` 按 basicswap 语法改写、ctx 签名改写（审查结论①） |
| 3 | `trustbridge/lyquid/src/assessor.rs` | **预计零改动**：lyquid-llm 引用全在注释/SPIKE 门控块（assessor.rs:15-17 实测为注释）；红线 = 保持零平台依赖，T0 分桶若出现意外错误才动，且不得引入 lyquid 引用 |
| 4 | `trustbridge/lyquid/src/committee.rs` | **预计零改动**：仅 `use crate::types::*; use crate::core;`（committee.rs:26-27 实测），零平台依赖；红线同上 |
| 5 | `trustbridge/lyquid/src/types.rs` | **零改动**：领域语义冻结（硬约束） |
| 6 | `trustbridge/lyquid/src/core.rs` | **零改动**：领域语义冻结（硬约束） |
| 7 | `trustbridge/lyquid/Cargo.toml` | **条件改**：仅当版本对齐预案触发（D7）时 `tag="v0.7.3"` → `rev="<main HEAD>"`；其余不动 |
| 7b | `trustbridge/lyquid/build.rs` | **既有未登记文件**（平台模板必需，随 T0.5 基线提交入库）：本轮实测与 `$V7/lyquid-template/build.rs` **逐字节相同**（cmp→IDENTICAL），且 `$V7/lyquid/src/lib.rs:268` 定义 `WASM_STACK_POINTER="__stack_pointer"`——**保留入库，不得删除** |
| 8 | `trustbridge/scripts/deploy.sh` | **改**：按部署实测的真实形态校正（shaker 运行通道、路径、`--input` 形态） |

workflow-out（非仓库，2 个）：

| # | 文件 | 性质 |
|---|------|------|
| 9 | `trustbridge/workflow-out/implementation.md` | **新建**：开头登记用户 3 条裁定；逐 SPIKE 登记表（假设→验证方式→结论）；传递 crate 登记（含实测版本修正，见 §1 事实 F12） |
| 10 | `trustbridge/workflow-out/` 证据存档（`w1a-deploy-output.txt`、`w1a-call-poc.txt`、`w1a-funded-evidence.txt` 等） | **新建**：shaker 部署输出、T4.5 调用 PoC 请求/响应全文、faucet/create_deal/fund/deal_info 的真实命令输出（完成定义"输出为证"）；含 T0 目标门工具链输出与新编译基线 |

**不改**：`workflow-out/verify_core/`（壳）——其挂载的 types/core/committee/assessor 四文件零平台依赖是 39/39 的前提（红线见 §5.3）；`agents/`、`scripts/demo.py`、`scripts/devnet-up.sh`（RPC 对齐属 W1-B/S4，勿越界）；`../ldk/`（平台仓库只读参照）。

---

## 1. 基线事实（全部本轮实测；命令+出处）

| # | 事实 | 实测方式与结果 |
|---|------|----------------|
| F1 | 工作 crate 位置与基线 | `trustbridge/lyquid`（src: lib/types/core/committee/assessor/timeout）；`git log --oneline -3` → `4a8528a` docs、`a8ca9fb` docs、`912a4ae` Phase4——代码基线之上仅两个纯文档提交 |
| F2 | cargo check 基线 = **73 错（已过时）** | `trustbridge/workflow-out/t0-baseline-cargo-check.txt` 末行：`error: could not compile trustbridge (lib) due to 73 previous errors`。**时效警告（仲裁轮实测）**：该基线文件 mtime 22:53 早于 Cargo.toml features 编辑 22:58——73 错为 feature 前旧基线，不得再作对照数；且宿主通道本身不可达（F14a）。**T0 在选定通道（T0 目标门）重取新基线**，登记错误总数/形态/命令全文，此后一切计数以新基线为准 |
| F3 | SPIKE 标记基线 | `grep -c "SPIKE("` → lib.rs **10**、timeout.rs **7**、assessor.rs 3、committee.rs 2、types.rs 1、core.rs 0（共 23）。lib.rs 的 9 个实质位点 = 53,59,182,236,356,491,501,505,510（grep 逐行核对，与任务给定一致；第 10 处是文件头总说明 lib.rs:8） |
| F4 | 平台依赖锁定 | Cargo.toml：`lyquid = { git=..., tag="v0.7.3", features=["ldk"] }`、`lyquid-llm`（同 tag）、serde/serde_json 直依（注释已登记为锁图内传递）；`[lib] crate-type = ["cdylib","rlib"]`。Cargo.lock 解析 rev=`3b10b6ad...`，源码检出在 `~/.cargo/git/checkouts/ldk-b72281d44a8ce511/3b10b6a`（下称 `$V7`） |
| F5 | v0.7.3 prelude 内容 | `$V7/lyquid/src/runtime/prelude.rs` 全文：宏 `state/log/call/trigger/upc/print/println/submit_certified_call/...`；类型 `HashMap/new_hashmap/Address/ChainPos/TriggerMode/LyquidError/LyquidResult`；`pub use crate::method::{self}`（→ `method::network/instance`）；`lyquor_api`。**`CallContext` 不在 prelude** |
| F6 | LyquidError 真实形态 | `$V7/lyquid/src/lib.rs:172-189`：枚举 `Init/LyquorInput/LyquorOutput/LyquidInput/LyquidOutput/LyquorRuntime(String)/LyquidRuntime(String)/InputCert/OracleError(String)`——**无 `msg` 构造器**；`:199` 平台已导出 `pub type LyquidResult<T>` |
| F7 | 方法签名与状态访问（erc20 实证） | `$V7/lyquid-examples/erc20/src/lib.rs:128-182`：`#[method::network(export = eth)] fn transfer(ctx: &mut _, to: Address, ...) -> LyquidResult<bool>`——**ctx 类型写 `_` 占位**；状态经 **`ctx.network.balances`** 访问；caller = **`ctx.caller`**（`CallContext.caller: Address`，`$V7/lyquid/src/lib.rs:165-172`）；内部 helper 以 `state: &mut __lyquid::NetworkState` 穿参（erc20:14-27） |
| F8 | template 同款实证 | `$V7/lyquid-template/src/lib.rs:17-53`：`ctx: &mut _` + `*ctx.network.greeting = ...`；instance 状态锁模式 `ctx.instance.per_user_count.write()`（:48-49） |
| F9 | 无 export 属性合法 | `$V7/lyquid/proc/src/lib.rs:136` `export: Option<ExportKind>`（Option，可缺省）；price-feed:399 另有 `group=` 参数。trustbridge 的裸 `#[method::network]`（15 个，lib.rs 实数=审查结论③）= native 导出形态，语法层面成立 |
| F10 | 时间源 | `$V7/bartender/src/lib.rs:90-96`：`lyquor_api::chain_pos()?.block().saturating_add(...)`——`lyquor_api::chain_pos()` 返回 `ChainPos`（`$V7/primitives/src/lib.rs:66-74`：u128 打包 block<<32\|idx，`.block()` 取 u64）。**不需要 ctx，单点函数形态可保** |
| F11 | call! 真实语法 | `$V7/lyquid-examples/basicswap/src/lib.rs:31`：`call!((token).transfer(to: Address = to, amount: U256 = amount) -> (success: LyquidResult<bool>)).success?`——命名参数+返回解包形态。timeout.rs 现写的 `call!(ctx, due_deals(now))` **不匹配此语法** |
| F12 | 传递 crate 实测版本 | Cargo.lock：`ahash 0.8.12`（与裁定文本一致）、**`talc 5.1.1`（裁定文本写 5.0.3，实测锁定为 5.1.1——v0.7.3 平台解析结果）**。implementation.md 按实测登记并注明差异 |
| F13 | shaker 通道（本轮实测 help 摘录） | 容器名实测 `ldk-tools-1`（healthy）+ `ldk-node-1`。`docker exec ldk-tools-1 shaker --help` 实测：`deploy`=Build and deploy；`test`=**Run Lyquid guest unit tests with cargo test**（dev-dep lyquid-test 已在 Cargo.toml）；`console`=**Get the console output from a running Lyquid**（仅取输出，**非交互调用通道**）；`serve`=**Proxy localhost HTTP traffic to a Lyquid's virtual host on a local node**（`shaker serve --help` 实测：`-e/--endpoint` 默认 `ws://node:10087/ws`、`--listen` 默认 `127.0.0.1:8080`）；另实测 `cast 1.7.1` 在 tools 容器。`$V7/README.md:48-57`：deploy 在 tools 容器内跑、容器内连 `node:10087`。**trustbridge 不在 compose 卷挂载内**（compose 项目在 `../ldk/`），部署/编译通道需 T4.0 实测探明。节点 `/api` 行为（仲裁轮实测）：eth_chainId→`0x7a69`、faucet→`-32601`（方法不在信封可达集）、`/lyquor/api`→Not found |
| F14 | 环境事实（任务给定，本轮未复跑） | Docker 29.8.2 运行中；devnet 单节点 :10087、tools 容器 healthy；bartender 已部署（`Lyquid-f7vljmg2... @ 0x9fE4...a6e0`）；节点 API=JSON-RPC 2.0 POST /api（空 body 回 Parse error 属预期）；宿主 cargo 1.99.1 可用；壳 39/39 全绿。**T0 须全部复测**后才作为本段前提。**F14a 宿主通道不可达（仲裁轮实测）**：平台 crate 宿主编译 4 错 E0425 `NativeGuestAbi`；宿主 rustup 仅装 `x86_64-pc-windows-msvc`；`--target wasm32` 先撞 ldk workspace 模板 Cargo.toml 的 `{{project-name}}` 非法包名——**宿主 cargo 命令一律仅作诊断，验收通道见 T0 目标门**。容器工具链本轮实测：`docker exec ldk-tools-1 rustup target list --installed` → `wasm32-unknown-unknown` + `x86_64-unknown-linux-gnu`；cargo 1.99.0 |
| F15 | 版本上移落点 | 本地 `ldk/` 克隆 `git log -1` = `fd575e8`、`git describe` = **v0.8.1**（= devnet 镜像 main-latest 对应源）。D7 预案的 rev 目标即此 HEAD（若触发，重执行本方案 §3 各项对照用本地克隆即可，无需再拉远端） |
| F16 | 壳结构 | `workflow-out/verify_core/src/lib.rs`：`#[path]` 绝对路径挂 types/core/committee/assessor 四模块，包名 trustbridge；壳 Cargo.toml 仅 serde/serde_json——四挂载文件**必须保持零平台依赖**（lib.rs/timeout.rs 不挂载） |

---

## 2. 目标与验收口径（= 任务完成定义，逐条以真实输出为证）

1. **S5 编译清零（通道限定）**：在 **T0 目标门选定的检查通道**（容器内 `cargo check --target wasm32-unknown-unknown`（经挂载或 docker cp）或 `shaker test <manifest>`）上 → **0 错**（或 ≤5 且逐条注明属上游形态必需遗留；**≤5 预算的计数以该通道为准**）；随后同通道 `shaker test`（guest 单测，S5 后才允许跑——审查结论②）全绿。宿主 `cargo check`/`cargo test` 不可达（F14a），仅诊断用，不作验收。
2. **壳不回退**：`cd workflow-out/verify_core && cargo test --lib --tests` → **39/39 全绿**（T0 复测基线后，每个改动窗口收尾各复跑一次）。
3. **escrow 部署**：shaker 部署 trustbridge cdylib 上 devnet，拿到 Lyquid id + 地址（输出存档）。
4. **走到 Funded**：`faucet → create_deal → fund → deal_info` **全部经 T4.5 PoC 通过的调用通道**（shaker serve 代理或 cast+eth 导出）在 devnet 实际执行，`deal_info` 输出 `state: Funded`（每步真实输出存档 §0-#10）。
5. **deploy.sh 校正**：按 3-4 的真实通道改写并复跑通过。
6. **implementation.md**：开头 3 条用户裁定；逐 SPIKE 登记表覆盖 §6 全部 **23 处标记**（表行 23 行 = 处置/登记 15 + 保留 8；每行：假设→验证方式→结论/保留理由）；talc/ahash 登记（F12 实测版本）。

**红线**（硬约束内化）：types.rs/core.rs 语义零改动、测试断言不变；不新增 crates.io 直接依赖（serde/serde_json 为既有登记直依；talc/ahash 为 ldk feature 传递，豁免）；devnet 只做 faucet/create_deal/fund 测试交易；W1-B 范围（S1-S4、多节点、RPC 对齐、demo.py 三流程）不做。

---

## 3. 设计决策（审查重点）

### D1 宏与类型解析：`use lyquid::prelude::*;` 单行导入（lib.rs/timeout.rs 各一）

`state!/log!/method::network/new_hashmap/HashMap/LyquidError/LyquidResult/lyquor_api/ChainPos/TriggerMode` 全部经 prelude 可达（F5）。lib.rs 头部加一行即可让现有 `state!`/`#[method::network]`/`new_hashmap` 宏名解析（当前 E0433 类错误的根治）。timeout.rs 按审查结论①补同款导入 + 保持 `crate::` 限定（`crate::current_slot`、`crate::LyquidResult` 已是限定形态，timeout.rs:21-22）。

### D2 错误桥：`LyquidError::LyquidRuntime(String)` + 平台 `LyquidResult` 再导出

- `lyquid_error(msg)` 改为 `LyquidError::LyquidRuntime(msg.to_string())`（erc20:31 实证同款；SPIKE@59 验证完成）。
- lib.rs:56 自定义别名改为 `pub use lyquid::LyquidResult;`（F6：平台已导出同名同形；SPIKE@53 验证完成）。timeout.rs:22 `use crate::LyquidResult;` 无需变。
- `bridge_core_err` 的穷举 match 结构不变（core::TransitionError 枚举未动）。

### D3 状态访问模型：`ctx.network.<field>` + helper 状态穿参（erc20 镜像）

v0.7.3 的 `state!` 宏**不注入裸标识符**——方法体内一律 `ctx.network.deals` / `ctx.network.balances`（F7/F8）。改法：

1. 每个 `#[method::network]` 方法签名 `ctx: Context` → **`ctx: &mut _`**（有状态写）/ **`ctx: &_`**（纯读 getter，erc20 `totalSupply` 同款）；`#[method::instance]` 同理。
2. 方法体内**不做逐处 `ctx.network.` 前缀**——每方法开头**单点 reborrow** 取别名：写方法 `let state = &mut *ctx.network;`、只读 getter `let state = &*ctx.network;`，体内一律 `state.<field>`。依据（仲裁轮 rustc 实测）：逐处 `ctx.network.` 前缀在多字段并存时触发 E0502（同时可变+不可变借用 ctx.network）；单点 reborrow 后字段级分离借用编译通过。**点名 fund（lib.rs:233-240）与 apply_committee_verdict（:376-377）必须此形态**（同方法内 get 与 get_mut 并存的最深借用嵌套）。**标量字段统一解引用**：`*state.committee_threshold`（:360 读处 `*state.committee_threshold as usize`、:395 赋值处 `*state.committee_threshold = threshold`）、`*state.deal_counter`（198-199）——宏生成字段为 RwLock/leak 句柄形态，erc20 `*state.total_supply` 同款（erc20:131）。
3. 自由 helper `debit/credit/apply_payout` 增加 `state: &mut __lyquid::NetworkState` 首参（erc20 `update/get_balance` 同款），方法内调用点传 `&mut ctx.network`。`current_slot/lyquid_error/bridge_core_err` 不触状态签名不变；**`require/caller_agent` 改收具体类型**（D4：`caller: &Address` + `state: &__lyquid::NetworkState`），逻辑/矩阵/fail-closed 零改动。**硬约束：`ctx: &_`/`&mut _` 占位类型仅允许出现在 `#[method::*]` 标注的方法签名**（占位 `_` 由宏展开替换；普通自由函数参数用之 = rustc 1.99.1 E0121 编译错，仲裁轮实测）。平台 `CallContext`（`$V7/lyquid/src/lib.rs:162`，仅 origin/caller/input/lyquid_id/node_id 字段）**无 network 字段**，不得作为自由函数参数类型使用；`__lyquid` 模块由 lib.rs:31 既有 `state!` 生成，erc20 自由 helper 惯例即经此路径可达（`$V7/erc20:15-27`）。
4. `apply_committee_verdict` 内 `committee_members.iter()`（SPIKE@356）：改 `ctx.network.committee_members.iter()`；**确定性论证已有**（lib.rs:358 顺序无关性注释——`contains`+阈值比较与迭代顺序无关），登记即结。

### D4 caller 身份落地：`ctx.caller` 地址字符串化 + BROKER 常量回填部署者地址

- `caller_agent` 改为具体类型签名：`fn caller_agent(caller: &Address) -> LyquidResult<AgentId> { Ok(caller.to_string()) }`（erc20 自由 helper 惯例，`$V7/erc20:15-27`；`Address` 经 prelude 导入。alloy Address 的 Display/checksum 具体形态在 T5 用 devnet 实测输出钉死，登记进 implementation.md）。
- `require` 改为具体类型签名：`fn require(access: Access, caller: &Address, state: &__lyquid::NetworkState, deal: Option<&Deal>) -> LyquidResult<AgentId>`——**体内先转换 `let caller: AgentId = caller.to_string();`**，此后 `d.buyer == caller`（:140-142 三处比较）、`state.committee_members.get(&caller)`（:147）均在 AgentId 域内进行（&Address 与 AgentId/String 不能直接比较，先归一到 AgentId 再比）。match 结构/fail-closed 语义零改动。全部调用点统一 `require(access, &ctx.caller, &ctx.network, deal)`；`&ctx.network` 的传参强转以 erc20:130 `_mint(&mut ctx.network, ctx.caller, …)` 为实证。
- **身份链对齐（走 Funded 的关键）**：`create_deal` 守卫 `caller == BROKER`、`fund` 守卫 `caller == deal.buyer`。devnet 单一调用者（shaker 通道默认账户，地址 A）下：`BROKER` 常量改为 A 的同款字符串（T4 实测回填）；`create_deal(buyer=A 的字符串, seller=任意≠A, ...)` → `fund(deal_id)` 即过双门禁。`seller` 无门禁（submit_deliverable 才校验，不在本段路径）。
- ACCESS_MATRIX、`require` 的 match 结构、fail-closed 语义**零改动**——设计本意即"W1 换掉 caller_agent 一处，全矩阵活化"（lib.rs:104-106 既有注释）。

**D4b BROKER=caller 身份链机制（冷读仲裁意见 2 落地）**——**全 crate 无方法回显 caller**（faucet 返回 `()`，lib.rs:159-165），"T5 首步实测 `to_string()` 输出"不可执行，改走探针路径：

1. **地址来源**：T4.0/T4.5 实测选定并登记——节点 `/api` 的 `eth_accounts`（F13 已证 /api JSON-RPC 可用）或 shaker serve/deploy 输出，取得候选地址 A（hex 形态）。
2. **自署名探针（PoC 通过后、回填 BROKER 前执行）**：`notarize(<哑deal_id>, from=<候选A串>, to=<任意>, digest=<非空>)`。机制依据：lib.rs:263-266 的 `from == caller` 校验**先于一切状态写入**，且 notarize **不查 deal 存在性**（:269 `evidence_log.entry(deal_id).or_default()` 直接为哑 id 建条目）——故 **`Ok(seq)` ⟺ 候选串与 `ctx.caller.to_string()` 完全一致**（含大小写与 EIP-55 形态）；报 `"self-signed only"` 即形态不符，换小写/checksum 再试。
3. **钉死与回填**：探针钉死的字符串写入 implementation.md 及证据存档；随后回填 BROKER、重新编译部署（digest 变更重置状态符合预期，R7）；T5 的 create_deal buyer 参数用**同一字符串**。注记：探针会在哑 deal_id 下留一条 evidence_log（devnet 可接受，按 R7 登记）。
4. **不采纳 whoami getter 备选**：方法清单与 ACCESS_MATRIX 冻结（§0-#1、§9），不破例；探针路径无需新增方法。

### D5 时间源：`lyquor_api::chain_pos()` 单点落地

`current_slot()` 改为 `lyquor_api::chain_pos().map(|p| p.block()).unwrap_or(0)`（F10 bartender 同款；`lyquor_api` 经 prelude 可达，无 ctx 参数——`pub(crate)` 单点函数形态保留，timeout.rs 的 G5 单点约束不破坏）。SPIKE@491/501 验证完成。`ChainPos::block()` 返回 u64 块高，与 `timeout_slots_from_estimate` 的槽语义在 devnet 上按实测块时登记换算注记（不改编码）。

### D6 timeout.rs `call!`：basicswap 语法改写，两档兜底

v0.7.3 的 `call!` 是**跨 Lyquid** 调用形态（F11），同 crate 方法间调用需以自身 LyquidID 为目标。改写：

```rust
let self_id = ctx.lyquid_id; // CallContext 字段（F6 区段）
let due = call!((self_id).due_deals(now: u64 = now) -> (due: LyquidResult<Vec<DealId>>)).due?;
```

- **A 档（首选）**：上式编译通过即收（watcher_step ctx 改 `&mut _`）。
- **B 档（兜底）**：宏解析不过 → watcher_step 的两处跨调用退回注释 + SPIKE 注记升级（"call! 同 crate 自调用形态未在 v0.7.3 证实，留 S1/W1-B"），函数体退化为返回空 Vec 的可编译骨架——**不在 Funded 验收路径上**，计入 ≤5 遗留预算并逐条注明。两档均不碰 `core::due_for_timeout` 语义。
- timeout.rs 的 7 个 SPIKE：3 个属 S5（instance 属性/ctx 形态、instance 内共识时间、call! 形态——随本节处置）；4 个属 S1/W1-1（trigger 语义、kill/重启验收标准等）**保留标记不动**。

### D7 版本对齐预案（裁定 2 的执行化）：仅凭证据触发

- **触发判据**（任一成立）：(a) 0.8 devnet/shaker 拒绝 v0.7.3 构建的 cdylib（部署报版本/digest 错）；(b) T1-T3 编译清零中发现 v0.7.3 宏行为与 erc20/template 实证矛盾且无法以 v0.7.3 形态收敛。
- **执行**：Cargo.toml 三处 `tag="v0.7.3"` → `rev="fd575e8..."`（完整 hash 以 `git -C ../ldk rev-parse HEAD` 实测为准，F15）+ `cargo update` 重锁 → 用本地 `ldk/` 克隆重跑 §3 各项对照（prelude/erc20 于 0.8.1 的差异逐条登记）→ 重编译重部署。
- **登记**：implementation.md 记录触发证据、目标 commit hash、行为差异清单——平台要求，非依赖浮动（裁定 2 原文口径）。
- **回退**：恢复到 T0.5 基线 commit（`git checkout <base-commit> -- lyquid/Cargo.toml lyquid/Cargo.lock`）。**不得回退到 4a8528a**——那是 features 前状态，回退到它将使 ldk 的 method/runtime 模块不存在（feature 门控，Cargo.toml 注释在案）、无法编译。
- **不触发即不动**：v0.7.3 编译过且 0.8 平台接受部署 → 锁保持 tag（部署成功本身即"接受"证据，登记之）。

### D8 部署通道：T4.0 实测三选一，deploy.sh 按实测固化

shaker 官方通道在 tools 容器内（F13），但 compose 卷挂载在 `../ldk/`，trustbridge 大概率不可见。探明顺序：
1. `docker compose -f ../ldk/docker-compose.yaml exec -it tools shaker --help` + `docker inspect` 查 tools 卷——若宿主路径已映射则直接容器内部署（deploy.sh 固化该形态）；
2. 否则 `docker cp trustbridge/lyquid tools:/work/trustbridge` 后容器内部署（deploy.sh 固化 cp+exec 两步）；
3. 否则查宿主 shaker 可用性（`shaker --version`；上一轮 bartender 部署成功，其通道形态可作为直接线索——T4.0 一并复盘上轮部署命令）。
`--input` 形态按实测校正（现脚本 `0x00` vs README 无 0x 前缀长 hex——以部署成功输出为准）。

**D8b 调用通道（T4.5 PoC 的设计依据，硬门禁）**：`shaker console` 不是调用通道（F13 实测 help：仅 Get the console output）。首选 `shaker serve <LYQUID_ID>`——本地 HTTP 代理到 Lyquid 虚拟主机（默认 endpoint `ws://node:10087/ws`、listen `127.0.0.1:8080`，本轮实测 help）；PoC＝经代理实际调用 `faucet` 一步并存档请求/响应全文。备选＝目标方法加 `export = eth`（D9 属性面）后用容器内 `cast 1.7.1`（实测在 tools）以 eth ABI 调用。**PoC 未通过不得进 T5**。调用信封（invocation envelope：URL/方法名/参数编码/响应形状）在本段落地并写入 implementation.md——S4 的完整 RPC 对齐仍留 W1-B。

---

## 4. 子任务拆分与执行顺序

依赖链：T0 复测+目标门 → **T0.5 基线收口 commit** → T1 lib.rs（最大块）→ T2 timeout.rs → T3 编译清零循环（选定通道） → T4 部署通道+escrow 上链 → **T4.5 调用通道 PoC（硬门禁）+ caller 形态探针** → T5 Funded 路径 → T6 文档收口。D7 预案可在 T3/T4 处插入。**每子任务收尾跑壳 39/39**（F16：lib.rs/timeout.rs 不在壳内，正常应恒绿；一旦红=触碰四挂载文件，立即回退该步）。

| # | 子任务 | 内容 | 涉及文件 | 验收 |
|---|--------|------|----------|------|
| T0 | 基线复测、错误分桶与**目标门** | 复跑壳 39/39、devnet 探活（`curl -s -X POST http://127.0.0.1:10087/api -H "Content-Type: application/json" -d '{}'` 预期 -32700 Parse error；`docker compose -f ../ldk/docker-compose.yaml ps`）；**目标门**：实测 tools 容器工具链（`docker exec ldk-tools-1 rustup target list --installed`、`cargo --version`——本轮已预演：wasm32-unknown-unknown+x86_64-linux-gnu、cargo 1.99.0），选定检查/测试通道＝容器内 `cargo check --target wasm32-unknown-unknown`（经挂载或 docker cp）或 `shaker test <manifest>`（F13 实测 help：Run Lyquid guest unit tests with cargo test）；在选定通道**重取编译基线**（F2 的 73 错已过时），登记错误总数/形态/命令全文并分桶 | 无改动 | 壳 39/39；目标门通道选定+工具链输出；新基线（总数/形态/命令全文）；devnet 三探活输出 |
| **T0.5** | **基线收口 commit** | 将现存未提交改动提交为显式基线 commit（本轮实测 `git status`：`M lyquid/Cargo.toml`（features/注释，19 行）、`M lyquid/Cargo.lock`（+79 行）、`?? lyquid/build.rs`（平台模板必需，§0-7b）——三者正是 features 补齐的现场，不提交则基线不可复现）；**hash 登记入 implementation.md**，此后一切回退以该 commit 为锚（D7/R8） | lyquid/Cargo.toml, lyquid/Cargo.lock, lyquid/build.rs | 基线 commit hash 入档；`git status` 干净 |
| T1 | lib.rs 平台接线（S5 主体） | D1 导入 → D2 错误桥/Result 再导出 → D3 ctx 签名+单点 reborrow+helper 穿参（15 个网络方法逐一）→ D4 caller_agent+BROKER 占位（`"TBD"`，T4.5 探针后回填）→ D5 current_slot → 9 处 SPIKE 按 §6 处置 | lib.rs | 选定通道错误数较新基线大幅下降（分桶对比）；壳 39/39 |
| T2 | timeout.rs 接线 | D1 导入 + D6 call! 改写（A 档，B 档兜底）+ ctx 签名 + 3 处 S5-SPIKE 处置、4 处 S1-SPIKE 保留 | timeout.rs | 选定通道无 timeout.rs 新增错误（或 B 档计入预算）；壳 39/39 |
| T3 | 编译清零循环（选定通道） | 在 T0 目标门选定的通道上迭代 `cargo check --target wasm32-unknown-unknown` 至 0 错（≤5 遗留逐条注明：每条记文件/错误码/为何属上游形态必需；**预算计数以该通道为准**）；随后 `shaker test`（guest 单测，S5 后首跑） | lib.rs/timeout.rs（迭代修正） | 选定通道 check 0 错（或 ≤5 注明）；shaker test 全绿；壳 39/39 |
| T4 | 部署通道 + escrow 上链 | D8 探明通道 → deploy.sh 校正 → 部署 cdylib → 拿 Lyquid id+地址存档；**T4.5 探针钉死 caller 串后**回填 BROKER 常量并重新编译部署（digest 变更重置状态符合预期，R7） | deploy.sh, lib.rs(BROKER), 证据存档 | 部署成功输出；**探针请求/响应存档（D4b）**；deal 所需守卫身份链就绪 |
| **T4.5** | **调用通道 PoC（硬门禁）+ caller 形态探针** | 首选 `shaker serve <LYQUID_ID>`（D8b：本地 HTTP 代理，默认 endpoint ws://node:10087/ws、listen 127.0.0.1:8080）：起代理后**实际调用 `faucet` 一步并存档请求/响应全文**；**PoC 通过后执行 D4b 自署名探针**（notarize 哑 deal）钉死 caller 字符串形态；备选＝faucet 等方法加 `export = eth` 后以容器内 `cast 1.7.1` 调用。**PoC 未通过不得进 T5**；调用信封（envelope：URL/方法名/参数编码/响应形状）随 PoC 落地 | 证据存档（w1a-call-poc.txt） | faucet PoC 请求+响应存档；**探针 Ok(seq) 确认候选串与 ctx.caller.to_string() 一致（含大小写/EIP-55）**；信封形态可复用至 T5 四步 |
| T5 | Funded 路径实测 | **全部经 T4.5 PoC 通过的通道**：`faucet(A, N)` → `create_deal(A, seller, amount, fee_bps, digests..., est...)` → `fund(deal_id)` → `deal_info(deal_id)`（**A = D4b 探针钉死的 caller 字符串**，buyer 参数同串）——**每步真实输出存档**，终态 `state: Funded` | 证据存档 | 4 步输出 + Funded 终态 |
| T6 | 文档收口 | implementation.md：3 条裁定开头 + §6 SPIKE 登记表全 23 处（处置/登记 15 + 保留 8）+ talc/ahash 实测登记（F12）+ D7 是否触发及证据 | implementation.md | 登记表与代码内标记双向勾稽（grep 23 行 ↔ §6 表 23 行，任一方向无孤儿行） |
| T7 | （条件）D7 版本上移 | 仅凭触发判据执行；重对照+重编译（选定通道）+重部署+登记 | Cargo.toml, Cargo.lock, implementation.md | 上移后 T3-T5 全部重验通过 |

commit 建议：**T0.5 基线 commit 先行且独立**（现存 features/lock/build.rs 改动——与 T1 起的任何工作不混合）；随后 T1+T2+T3 一个 commit（S5 编译清零）；T4+T5+T6 一个 commit（部署与登记）；T7 独立 commit。编码员不自行 push。

---

## 5. 逐文件具体改动点

### 5.1 `src/lib.rs`（守卫语义/桥接结构/方法清单零增删）

1. **:14 附近**（`use types::*;` 后）加 `use lyquid::prelude::*;`（D1）。
2. **:53-56**：删除自定义 `pub type LyquidResult<T> = ...`，改 `pub use lyquid::LyquidResult;`；SPIKE 注释改写为结论（"v0.7.3 lyquid/src/lib.rs:199 已导出同名类型，别名退役"）。
3. **:58-61**：`lyquid_error` 体改 `LyquidError::LyquidRuntime(msg.to_string())`；SPIKE@59 改结论（枚举形态实证 `$V7/lyquid/src/lib.rs:172-189`，erc20:31 同款）。
4. **15 个 `#[method::network]` 签名**：`ctx: Context` → `ctx: &mut _`（faucet/create_deal/fund/notarize/submit_deliverable/complete/claim_timeout/cancel/open_dispute/apply_committee_verdict/committee_config）或 `ctx: &_`（deal_info/evidence_entries_json/balance_of/due_deals 四个纯读 getter）；方法体内 `let _ = ctx;` 行删除（ctx 现被使用）。占位 `_` 仅限此类宏标注方法签名（D3 硬约束，E0121）。
5. **状态访问（单点 reborrow，D3-2）**：每方法开头 `let state = &mut *ctx.network;`（写方法）或 `let state = &*ctx.network;`（只读 getter），体内一律 `state.<field>`，**不逐处 `ctx.network.` 前缀**（E0502，见 D3-2）。裸标识符 → `state.` 前缀全清单：`deals`(220,228,233,278,282,291,296,313,325,329,342,345,376,404,**431**)、`balances`(240,418,439-450)、`evidence_log`(269,370,413)、`committee_members`(359,391-393；**147 在 require 体内，随 D4 走 `state.`**)、`committee_threshold`(**360 读 as usize、395 赋值，均 `*` 解引用**)、`deal_counter`(198-199，`*` 解引用)、`misconduct`(377)。**全部标量字段统一 `*` 解引用**（宏生成字段为 RwLock/leak 句柄，erc20 `*state.total_supply` 同款，D3-2）。
6. **helper 穿参**：`debit/credit` 加 `state: &mut __lyquid::NetworkState`；`apply_payout` 同（其内部 credit 调用随之传 state）；各调用点传 `&mut ctx.network`。`faucet/fund/complete/claim_timeout/cancel/apply_committee_verdict` 内调用点逐一改。
7. **:500-503**：`current_slot()` 体改 `lyquor_api::chain_pos().map(|p| p.block()).unwrap_or(0)`；SPIKE@491/501 改结论（bartender:92-95 实证）。`pub(crate)` 可见性保持（timeout.rs 依赖）。
8. **:509-512 + :136**：`caller_agent(_ctx)` → `fn caller_agent(caller: &Address) -> LyquidResult<AgentId> { Ok(caller.to_string()) }`（具体类型，非 `&_` 占位——自由函数禁用占位，E0121，见 D3）；SPIKE@505/510 改结论（`CallContext.caller: Address`；字符串形态以 T5 实测钉死并登记）。`require(access, ctx, deal)`（:136）→ `fn require(access: Access, caller: &Address, state: &__lyquid::NetworkState, deal: Option<&Deal>) -> LyquidResult<AgentId>`，**体内先 `let caller: AgentId = caller.to_string();` 再比较**（D4），:147 `state.committee_members.get(&caller)`；逻辑/矩阵/fail-closed 零改动。**caller_agent 全部调用点＝lib.rs:137（require 内，随新签名）与 :263（notarize 直调，改 `caller_agent(&ctx.caller)?`）**。require 调用点统一 `require(access, &ctx.caller, &ctx.network, deal)`。
9. **:114**：`BROKER` 常量值先置 `"TBD-CALLER-ADDR"`（T1 阶段），**T4.5 探针（D4b-2）钉死后**回填真地址串（与 create_deal buyer 参数同一字符串）；doc 注明"W1-A：devnet 部署者地址探针钉死后回填，W2 换真实部署流程"。
10. **SPIKE 处置**：按 §6 表——9 处中 7 处改写为结论注记（53/59/182/491/501/505/510 类）、236 登记设计不依赖+devnet 证据、356 登记顺序无关论证+编译通过证据；文件头 :8 总说明更新为"S5 已验证，残余 SPIKE 见 W1-B 各项"。
11. **不动**：ACCESS_MATRIX(118-131)、require 逻辑(136-150，签名/类型链按 D4 换但判定结构不动)、bridge_core_err 穷举(71-100)、**fund 预检顺序(234-247)——仅语义顺序不动（先拒余额不足再转状态再 debit），借用结构随 D3-2 单点 reborrow 调整**、apply_payout 结构(471-486)、TREASURY、DealView/serde 派生、create_deal 输入校验(189-197)。

### 5.2 `src/timeout.rs`

1. **:21-22 后**加 `use lyquid::prelude::*;`（审查结论①；`crate::types::DealId`/`crate::LyquidResult`/`crate::current_slot` 限定保持）。
2. **:36-37**：`#[method::instance]` 保留；`ctx: Context` → `ctx: &mut _`。
3. **:46/:51**：`call!` 按 D6 A 档改写（self_id 取 `ctx.lyquid_id`）；B 档兜底形态见 D6。
4. **SPIKE 处置**：:34-35（instance 属性/Context 形态）、:41-42（instance 内共识时间）、:44-45（call! 形态）→ 随实现改结论；:49-50（guard 幂等，core 已钉）→ 登记结论；:57-69 trigger!/W1-1 三处 → **保留**（S1 范围）；:12-14 文档头 R1 引述保留。

### 5.3 `src/assessor.rs` / `src/committee.rs` / `src/types.rs` / `src/core.rs`

**红线：四文件保持零平台依赖**（F16 壳前提）。T0 分桶若显示 73 错全落 lib.rs/timeout.rs（预期——F2 尾部样本佐证；assessor E0277 族已在阶段三消解），则本段四文件**一字不动**。若意外出现：仅允许不引入 `lyquid::` 路径的修法（如缺 use crate:: 限定）；任何必须引平台路径的修法 = 红线冲突，停手上报（改壳或改挂载策略超出本段授权）。

### 5.4 `Cargo.toml`（仅 D7 触发时）

三处 git 依赖 `tag="v0.7.3"` → `rev="<fd575e8 完整 hash>"`；[features]/[lib]/[profile] 不动；注释同步登记触发证据。**未触发则零改动。**

### 5.5 `scripts/deploy.sh`

按 D8 实测通道重写执行段（通道三选一）+ `--input` 实测形态 + 部署后验证行（serve 代理探活或 deal_info 实调）；文件头 SPIKE 注释改为实测结论；保留"digest 变更即重置状态"警示（demo 幂等设计依据）。

### 5.6 `workflow-out/implementation.md`（新建）

结构：①用户 3 条裁定原文（任务给定，逐字）；②talc 5.1.1/ahash 0.8.12 传递登记（F12，注明与裁定文本 5.0.3 的差异及实测依据）；③SPIKE 登记表 = §6 的 23 行全量（处置/登记 15 + 保留 8；+ 若 D6 走 B 档、D7 触发的追加行）；④T4.5 PoC 的**调用信封（invocation envelope：URL/方法名/参数编码/响应形状）** + **D4b 探针钉死的 caller 字符串及证据** + T5 四步命令与输出摘录（Funded 为证）；⑤D7 触发与否及证据；⑥T0 目标门：选定通道、工具链输出、新编译基线（总数/形态/命令全文）+ **T0.5 基线 commit hash**。

---

## 6. SPIKE 处置表（implementation.md 登记表的母本；行号 = 本轮 grep 实测，23 处全量）

**处置/登记 15 行（S5 范围内落地或登记结论）**：

| 位点 | 假设（原文） | 验证方式（本段） | 处置 |
|------|--------------|------------------|------|
| lib.rs:8 | 文件头 W1 待验总说明 | S5 完成 | 更新为"已验证+残余指向 W1-B" |
| lib.rs:53 | 平台是否导出 LyquidResult | `$V7/lyquid/src/lib.rs:199` 实读 | 改结论：已导出，别名退役为 re-export |
| lib.rs:59 | 错误构造器形态 | 同上 :172-189 + erc20:31 | 改结论：`LyquidRuntime(String)` |
| lib.rs:182 | caller 访问器（eth_guard 式） | erc20:161 `ctx.caller` + CallContext 定义 | 改结论：`ctx.caller: Address`；BROKER 地址回填（D4） |
| lib.rs:236 | network Err 是否原子回滚 | 设计论证（lib.rs:237-239 预检使两语义均正确）+ T5 实跑 | 登记：不依赖该假设；fund 成功输出为行为证据 |
| lib.rs:356 | HashMap→Vec 确定性迭代语法 | 编译通过 + 顺序无关论证（:358） | 登记：iter 顺序无关；ctx.network 前缀修正 |
| lib.rs:491 | 真实 slot/height 访问器 | bartender:92-95 `lyquor_api::chain_pos()` | 改结论：`.block()` 落地单点 |
| lib.rs:501 | current_slot 替换为 ctx 派生 | 同上（无需 ctx，单点形态保留） | 改结论：`lyquor_api::chain_pos()` 落地 |
| lib.rs:505 | caller 提取（ctx.from/signer） | CallContext 字段实证 | 改结论：`ctx.caller.to_string()`（形态 T5 钉死） |
| lib.rs:510 | （caller_agent 体内标记） | 同上 | 改结论：随 :505 一并落地 |
| timeout.rs:29 | 引用型注记："what remains is exactly the SPIKE(W1) items marked inline below"（剩余清单） | S5 落地后 inline 清单（:34/:41/:44/:49）已解 | **改写结论**：剩余清单更新——inline 项已验证，残余仅 W1-1 两处（:13/:67） |
| timeout.rs:34 | `#[method::instance]` 属性与 Context 形态 | template:48 `ctx: &mut _` + 编译 | 改结论 |
| timeout.rs:41 | instance fn 内取共识时间 | `crate::current_slot` 单点保持 + 编译 | 改结论：复用 D5 单点 |
| timeout.rs:44 | call! 跨函数调用形态 | basicswap:31 语法改写编译 | A 档改结论 / B 档保留+升级注记 |
| timeout.rs:49 | guard 幂等（Funded-only, terminal-safe） | core 测试既钉（阶段一） | 登记结论 |

**保留 8 行（W1-B 范围，标记不动）**：

| 位点 | 假设（原文） | 保留理由 |
|------|--------------|----------|
| timeout.rs:13 | trigger 语义需 W1-1 在 4 节点 devnet 证明 | S1/W1-B 范围 |
| timeout.rs:67 | W1-1 验收标准（kill/重启不双退、延迟上限） | S1/W1-B 范围 |
| assessor.rs:14 | lyquid-llm 导入路径（v0.7.3 实证面） | S3/W1-B 范围 |
| assessor.rs:63 | 真实后端接线前的 fallback 说明 | S3/W1-B 范围 |
| assessor.rs:90 | json crate story 待定 | S3/W1-B 范围 |
| committee.rs:46 | 委员会证据集与 network evidence_log 同源假定 | S2 域（读-算-校同源已由阶段 3b 契约钉） |
| committee.rs:70 | Vec-in-network-state 语法待验 | S2 域（S5 编译通过即旁证，正式验证留 S2） |
| types.rs:18 | devnet slot 长度参数 | S1/W1-B 定时语义 |

计数勾稽（grep 实测 23 = F3）：**处置/登记 15**（lib.rs 10 + timeout.rs 29,34,41,44,49）+ **保留 8**（timeout.rs 13,67 + assessor.rs 14,63,90 + committee.rs 46,70 + types.rs 18）= 23。

---

## 7. 风险与回退

| # | 风险 | 概率 | 缓解/回退 |
|---|------|------|-----------|
| R1 | v0.7.3 宏展开与 erc20 实证仍有出入（T3 迭代超预期） | 中 | 分桶推进每轮登记；≤5 遗留逐条注明（任务硬约束明示允许）；新形态差异对照 `$V7` 源码定位，不猜 |
| R2 | 0.8 devnet 拒 v0.7.3 构建产物 | 中 | D7 预案：rev 上移 `fd575e8`（本地克隆可查 0.8.1 源）；回退 = 恢复 tag 锁 |
| R3 | call! 同 crate 自调用形态 A 档失败 | 中 | B 档兜底（D6）；watcher_step 不在 Funded 路径，计入遗留预算 |
| R4 | tools 容器不见 trustbridge 路径 | 高（挂载在 ldk） | D8 三通道探明；docker cp 为最稳兜底 |
| R5 | caller 地址与 BROKER/buyer 身份链对不齐（Address 字符串形态不确定；**全 crate 无方法回显 caller**——faucet 返回 `()`（lib.rs:159-165），旧表述"T5 首步实测 to_string 输出"不可执行，已删） | 中 | 按 **D4b 探针机制**：T4.0/T4.5 从节点 /api `eth_accounts`（F13 已证 JSON-RPC 可用）或 shaker serve/deploy 输出取候选地址 A（hex）；PoC 通过后以 notarize 自署名探针（D4b-2）钉死形态——`Ok(seq)` 即候选串与 `ctx.caller.to_string()` 完全一致（含 EIP-55）；三处（BROKER/buyer 参数/比较）统一用探针验证过的同一字符串 |
| R6 | 四挂载文件被误触 → 壳红 | 低 | 每子任务收尾跑壳；红即回退该步（§5.3 红线） |
| R7 | devnet 状态污染（重复部署/faucet） | 低 | 只做测试交易（硬约束）；shaker deploy --update 重置语义已知（deploy.sh 头注释）；compose down/up 全重置为最后手段（devnet 是单节点测试网，无真实资金） |
| R8 | 整体回退 | — | 代码：回退到 **T0.5 基线 commit**（`git checkout <base-commit> -- lyquid/Cargo.toml lyquid/Cargo.lock`，T1-T6 改动另行 revert）；**4a8528a 为 features 前状态（ldk method/runtime 模块不存在、无法编译），不得作为回退目标**；部署：devnet 重置；workflow-out 产物为新增文件，可直接删除 |
| R9 | 最后一线审查第 5 条在外部文本 "plan.md:15,176 / ……" 处**截断**，全文未达（终裁收尾动作） | —（流程项） | **定稿签发前须向审查方取回该条全文核对**。可见部分指向 assessor 零依赖红线（本轮已核验：assessor.rs:14-17 实测为注释、四挂载文件零 lyquid 引用——§0-#3 与 §5.3 红线已覆盖）；若取回后诉求超出该范围，按新增意见另行处置 |

---

## 8. 人工验证命令（交付说明照抄执行并附输出）

```text
# 0) 基线复测（T0）
cd "F:\canvus auto\downloads\202609CS5298\workflow-out\verify_core" && cargo test --lib --tests
#   要求: 39/39 全绿（F14 任务给定，T0 复测后为本段前提）
curl -s -X POST http://127.0.0.1:10087/api -H "Content-Type: application/json" -d '{}'
#   预期: -32700 Parse error（仲裁轮实测：/api 空 body 或 {} 均回 Parse error；
#         /lyquor/api 回 Not found——两路径勿混）
docker compose -f "F:\canvus auto\downloads\202609CS5298\ldk\docker-compose.yaml" ps
#   要求: node + tools 健康

# 1) S5 编译清零（T3 收口；通道 = T0 目标门选定，宿主命令仅诊断——平台 crate 宿主不可编，F14a）
#    通道 A（容器内 wasm32 检查；crate 经挂载或 docker cp 进 ldk-tools-1）:
docker exec ldk-tools-1 sh -c "cd /work/trustbridge && cargo check --target wasm32-unknown-unknown 2>&1 | tail -3"
#    ⚠ 占位路径（终裁提示，非 must-fix）: /work/trustbridge 为 D8 三选一（挂载/docker cp/宿主 shaker）
#      未定形态的占位写法——T4.0 实测探明后按真实通道改写本命令行再入交付说明，勿照抄未验证路径
#      （D8/R4 已有兜底，此处仅防照抄）
#    通道 B（guest 单测，shaker test；dev-dep lyquid-test 已在 Cargo.toml）:
docker exec ldk-tools-1 shaker test ./trustbridge/lyquid/Cargo.toml
#   要求: 通道 A 0 错（或 ≤5 且 implementation.md 逐条注明，计数以选定通道为准）；通道 B 全绿
#   （S5 后才允许跑通道 B——审查结论②；宿主 cargo check/test = E0425 NativeGuestAbi 等 4 错，仅诊断不作验收）

# 2) 壳复跑（每子任务收尾 + 最终）
cd "F:\canvus auto\downloads\202609CS5298\workflow-out\verify_core" && cargo test --lib --tests
#   要求: 39/39 恒绿

# 3) escrow 部署 + 调用 PoC + Funded（T4/T4.5/T5，通道按 D8/D8b 实测固化后的 deploy.sh）
bash "F:\canvus auto\downloads\202609CS5298\trustbridge\scripts\deploy.sh"
#   要求: 部署成功输出（Lyquid id + 地址）存档 workflow-out/w1a-deploy-output.txt
#   T4.5 硬门禁（PoC 未过不得进 T5）: 起代理 docker exec ldk-tools-1 shaker serve <LYQUID_ID>
#   （默认 listen 127.0.0.1:8080 → ws://node:10087/ws），经代理实际调用 faucet 一步，
#   请求/响应全文存档 workflow-out/w1a-call-poc.txt（备选: export=eth + 容器内 cast 1.7.1）
#   T5 四步全部经 PoC 通道执行并存档每步输出:
#   faucet(<caller>, N) -> create_deal(<caller>, <seller>, ...) -> fund(<deal_id>) -> deal_info(<deal_id>)
#   要求: deal_info 输出 state: Funded —— 存档 workflow-out/w1a-funded-evidence.txt

# 4) SPIKE 勾稽（T6）
cd "F:\canvus auto\downloads\202609CS5298\trustbridge\lyquid"
grep -n "SPIKE(" src/*.rs
#   要求: 共 23 处，与 §6 表一一对应（处置/登记 15 = lib.rs 10 + timeout.rs 29,34,41,44,49；
#         保留 8 = timeout.rs 13,67 + assessor.rs 3 + committee.rs 2 + types.rs 1）；
#         grep 输出每一行均须能在 §6 表找到归属，反之亦然（双向勾稽，T6 验收口径）
```

## 9. 边界（本段不做）

- S1 timer / S2 委员会 oracle / S3 lyquid-llm / S4 RPC 包格式——W1-B 另行调用（timeout.rs 的 trigger 族标记保留即此意）。
- 多节点拓扑发现（compose 单节点现状维持）。
- demo.py 三流程全程（本段只到 Funded；Settled/对抗流属 W2'）。
- types.rs/core.rs 任何语义改动；ACCESS_MATRIX/require/bridge_core_err/fund 预检结构改动。
- 新增 crates.io 直接依赖（serde/serde_json 既有登记除外；talc/ahash 为 feature 传递豁免）。
