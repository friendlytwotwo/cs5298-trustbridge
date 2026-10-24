# W1-A 实现说明（S5 宏漂移审计编译清零 + escrow 上 devnet 走到 Funded）


执行基线：`workflow-out/plan.md`（独立终裁官定稿）。代码仓 `trustbridge/`（git）。
提交序列：T0.5 基线 `5d0380f` → S5 编译清零 `4b0df10` → 部署/登记 `a1721b7` → T6 登记 `740e810`。
**修订轮 R1（代码基线不变 740e810，仅文档/证据修订，单独提交）**：① deal_info http 读路径尝试失败并撤 ✅（§④-3/§⑦-2/§⑧.4，存档 `w1a-deal-info-evidence.txt`）；② §① 裁定原文不可再取证、两行降级（§①）；③ shaker test 复跑成功 0 tests（§⑦-1/§⑧.1，存档 `w1a-t3-shaker-test.txt`）；④ SPIKE 行号 @740e810 重算双列（§③/§⑧.6）。
**修订轮 R2（代码基线不变 fa3980e，仅文档/证据修订，单独提交）**：① §① 裁定原文经仲裁人向主控会话取证取回，逐字誊录+出处注记+逐条映射（§①）；② deal_info 第三通道（cast send）复跑失败，三通道全闭补登（§④-3/§⑧.4，追加于 `w1a-deal-info-evidence.txt` R2 节）。
**修订轮 R3（代码基线不变 fa3980e，仅文档/证据修订，单独提交）**：§⑧.4 经仲裁豁免结案（豁免原文逐字引录，偏离登记永续保留 + W1-B 遗留验证项），§④-3/§⑦-2 同步补登第三通道与 wasm 导出核验，`w1a-deal-info-evidence.txt` 追加 R3 结案节。

---

## ① 用户 3 条裁定（登记口径）

### 裁定原文逐字誊录（R2 经仲裁人向主控会话取证取回；含半角标点，一字不改）

> 【用户已裁定(写入 implementation.md 开头)】1) features=["ldk"] 引入的传递 crate(talc 5.0.3/ahash 0.8.12)豁免于"不新增 crates.io 依赖"约束——它们是平台官方 feature 的组成,登记即可;2) devnet=平台 0.8 与 SDK v0.7.3 的版本对齐属于 S5 范围:若 0.7.3 构建的 Lyquid 被 0.8 平台拒绝或宏/行为不匹配,允许把 git 锁从 tag v0.7.3 上移到已克隆的 ldk main HEAD(记录 commit hash),这算平台要求而非依赖浮动;3) SPIKE 纪律:标记可在假设被验证后移除/改写,每处登记(假设→验证方式→结论)。

### 出处与效力精度注记（如实登记）

三条裁定由**主控会话（orchestrator）于任务启动时写入任务文本**，本轮经仲裁人向主控取证取回。效力精度：**第 2、3 条 = 主控直接授权；第 1 条 = 主控裁定 + 终端用户默示**（启动即继续、未逐字批复）——按此精度登记，不得统称"用户逐字裁定"；如需终端用户逐字确认第 1 条，留待下次交互补认。

### 附注：R1"不可再取证"检索记录（降为附注）

R1 曾在本机可达记录（`trustbridge/.zcode/workflow-runs|workflow-drafts`、`202609CS5298/.workbuddy/memory`、`trustbridge/docs/`、W1 Spike 执行计划文档）穷尽检索裁定原文无果——检索过程属实，唯范围不含主控会话，故当时结论被 R2 取证推翻。

### 逐条映射（落地证据）

| 裁定 | 落地 |
|---|---|
| 裁定 1（传递 crate 豁免） | → §② F12：裁定写 talc 5.0.3、实测锁 **5.1.1** 的差异登记维持现状（talc/ahash 为 ldk feature 传递依赖，非新增直依） |
| 裁定 2（版本对齐属 S5） | → §⑤ D7：`rev="fd575e88a920448e646f23968775e52982c5201c"` 即"上移到已克隆的 ldk main HEAD（**记录 commit hash**）"要求的执行；触发证据 = 节点托管层 IncompatibleLdk 实录 |
| 裁定 3（SPIKE 纪律） | → §③ 表"假设→验证方式→结论"三列结构本身；23 处标记逐行登记、双向勾稽 |

**原裁定表两行的降级归属（维持 R1 不变）**：

- **计划决策 D4b 落地**（BROKER=caller 身份链）：自署名探针钉死 caller 串 `"0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"`（EIP-55）并回填 BROKER——证据见 §④。
- **流程纪律**（编码员职责边界）：实测命令即交付物、不虚报运行结果——R1 对 §⑦-1 误记的更正即该纪律的执行。

## ② 传递 crate 登记（F12 实测）

| crate | 锁定版本 | 依据 |
|---|---|---|
| `talc` | **5.1.1** | `lyquid/Cargo.lock`（当前锁，D7 后）实测。裁定文本写 5.0.3——**与实测不符，按实测登记 5.1.1**（平台解析结果，非我方选择） |
| `ahash` | **0.8.12** | 同上，与裁定文本一致 |
| `lyquid` / `lyquid-llm` / `lyquid-test` | 0.8.1 @ `rev=fd575e8…` | D7 后锁（§⑤）；talc/ahash 为 ldk feature 传递依赖，非新增直依（红线豁免） |

## ③ SPIKE 登记表（23 行全量；行号 = 原 T6 稿 → **现 @740e810 重算**；计数勾稽 `grep -c "SPIKE(" src/*.rs` = lib.rs 10 + timeout.rs 7 + assessor.rs 3 + committee.rs 2 + types.rs 1 = 23，core.rs 0）

### 处置/登记 15 行（S5 内落地或登记结论）

| 位点（原→现@740e810） | 假设 | 验证方式（本轮实跑/实读） | 处置 |
|---|---|---|---|
| lib.rs 8→8 | 文件头 W1 待验总说明 | S5 完成 | 改为"S5 已验证 + 残余指向 W1-B" |
| lib.rs 53→57 | 平台是否导出 LyquidResult | `$V7/lyquid/src/lib.rs:199`（v0.7.3）与 v0.8.1 同面实读 | 改结论：已导出同名同形，本地别名退役为 `pub use lyquid::LyquidResult;` |
| lib.rs 59→65 | 错误构造器形态 | v0.7.3 `LyquidError` 枚举 :172-189（无 `msg`）+ erc20:31 同款 | 改结论：`LyquidError::LyquidRuntime(String)` |
| lib.rs 182→220 | caller 访问器 | `CallContext.caller: Address`（:162）+ erc20:161 `ctx.caller` | 改结论：`ctx.caller`；BROKER 经 D4b 探针回填（§④） |
| lib.rs 236→276 | network Err 是否原子回滚 | 设计不依赖该假设（fund 预检使两语义均正确）；T5 fund status=1 行为证据 | 登记：不依赖；devnet 实跑为证 |
| lib.rs 356→412 | network HashMap→Vec 确定性迭代语法 | `state.committee_members.iter()` 编译通过 + :358（现 :414 附近）顺序无关性论证（ahash 种子确定） | 登记结论 |
| lib.rs 491→573 | 真实 slot/height 访问器 | bartender:90-96 `lyquor_api::chain_pos()` + primitives `.block()`（u64） | 改结论：`.block()` 落地单点 |
| lib.rs 501→586 | current_slot 替换为 ctx 派生 | `chain_pos()` 为无 ctx host API（runtime/mod.rs:299），单点形态保留 | 改结论；实证：T5 后 deal `created_slot=31`/`deadline_slot=331` 与链高一致 |
| lib.rs 505→591 | caller 提取（ctx.from/signer） | CallContext 字段实证 | 改结论：`caller_agent(&ctx.caller)` = `caller.to_string()`（形态 D4b 钉死） |
| lib.rs 510→599 | caller_agent 体内标记 | 同上 | 改结论，随 591 落地 |
| timeout.rs 29→30 | 引用型注记（剩余清单） | inline 四项（现 37/43/47/56）全部落地 | 改写：inline 已验证，残余仅 W1-1 两处（现 13/75） |
| timeout.rs 34→37 | `#[method::instance]` 属性与 Context 形态 | template:48 `ctx: &mut _` 同款 + 编译通过 | 改结论 |
| timeout.rs 41→43 | instance fn 内取共识时间 | `crate::current_slot` 单点复用（内部 `chain_pos()`，无 ctx 依赖）+ 编译 | 改结论 |
| timeout.rs 44→47 | call! 跨调用形态 | **A 档**：basicswap:31 命名参数+返回解包语法，目标 `ctx.lyquid_id`（InstanceContext 字段），编译通过——无需 B 档 | 改结论（A 档落地） |
| timeout.rs 49→56 | guard 幂等（Funded-only, terminal-safe） | core 测试既钉（阶段一，壳 39/39 持续为证） | 登记结论 |

### 保留 8 行（W1-B 范围，标记原文未动）

| 位点（原→现@740e810） | 假设 | 保留理由 |
|---|---|---|
| timeout.rs 13→13 | trigger 语义需 W1-1 在 4 节点 devnet 证明 | S1/W1-B 范围 |
| timeout.rs 67→75 | W1-1 验收标准（kill/重启不双退、延迟上限） | S1/W1-B 范围 |
| assessor.rs 14→14 | lyquid-llm 导入路径（v0.7.3 实证面） | S3/W1-B 范围 |
| assessor.rs 63→63 | 真实后端接线前 fallback 说明 | S3/W1-B 范围 |
| assessor.rs 90→90 | json crate story 待定 | S3/W1-B 范围 |
| committee.rs 46→53 | 委员会证据集与 network evidence_log 同源假定 | S2 域（读-算-校同源已钉） |
| committee.rs 70→77 | Vec-in-network-state 语法待验 | S2 域（S5 编译通过即旁证） |
| types.rs 18→18 | devnet slot 长度参数 | S1/W1-B 定时语义（实测注：60000ms→300 slots，见 T5 输出 `timeout_slots:300`） |

### 追加行（方案 §5.6-③ 预留）

| 追加 | 内容 |
|---|---|
| D7 触发行 | 见 §⑤：rev 上移 `fd575e8`（v0.8.1），全量对照后代码零改动、重部署重验证通过 |
| D6 追加行 | 不适用（A 档直接编译通过，B 档未启用，≤5 遗留预算消耗 **0**） |

### 行号双向复验（修订轮 R1 实测 @740e810）

命令（在 `trustbridge/lyquid`）：

    grep -n "SPIKE(" src/*.rs

输出（23 行，行号即上表现列）：

    src/committee.rs:53 / :77
    src/assessor.rs:14 / :63 / :90
    src/lib.rs:8 / :57 / :65 / :220 / :276 / :412 / :573 / :586 / :591 / :599
    src/types.rs:18
    src/timeout.rs:13 / :30 / :37 / :43 / :47 / :56 / :75

勾稽判定：**正向**——上列 23 行 grep 命中逐一可在本表找到归属行（处置 15：lib.rs 10 + timeout.rs 5；保留 8：timeout.rs 2 + assessor.rs 3 + committee.rs 2 + types.rs 1）；**反向**——本表 23 行逐一可反查至上述 grep 行，无孤儿。修订前原表行号为 T6 稿时点值，本次全部按 HEAD 重算更正。

## ④ T4.5 调用信封 + D4b 探针 + T5 Funded

### 调用信封（invocation envelope，T4.5 实测钉死）

- **首选通道（shaker serve）证伪**：代理建立成功（`proxying http://127.0.0.1:8080/ => <id>.<vhost> @ http://node:10087`），但 `POST /、/api、/faucet、/api/faucet、/rpc、/call、/lyquid` 全部 `Not found`——虚拟主机 HTTP 面只服务 `export = http` 的 instance 方法；方法清单冻结不得新增包装方法 → **转 D8b 备选**。
- **实采通道（ETH API，D8b 备选）**：
  - URL：`http://node:10087/api`（容器内；宿主等价 `http://127.0.0.1:10087/api`）
  - 方法：`cast send <CONTRACT> "<ABI签名>" <参数…> --private-key $KEY --rpc-url http://node:10087/api`
  - 参数编码：Ethereum ABI（`faucet(string,uint128)`、`create_deal(string,string,uint128,uint16,string,string,uint64,uint8)`、`fund(string)`、`notarize(string,string,string,string)`、`deal_info(string)`）
  - 响应形状：anvil 兼容回执（`status`/`blockNumber`/`transactionHash`/`logs`；每笔成功 tx 携带平台 LyteLog，内含 tag+参数可辨识）
  - KEY：anvil devnet #0（`0xac09…ff80` = `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266`）
  - 通道落地面：faucet/create_deal/fund/notarize/deal_info 五方法加 `export = eth`（仅属性面；方法清单/ACCESS_MATRIX 零增删）
- **实测限制（如实登记）**：
  1. v0.7.3/0.8.1 的 `EthAbiType` 无裸 `u128`（仅 U8..U64 + `U64/U128/U256` 包装，ethabi.rs:218-281）→ faucet/create_deal 的 `amount` 改收 `U128`，边界 `.to::<u128>()` 转回领域域（数值语义不变，native/call! 面不变，W1-B RPC 对齐以此为准）。
  2. 官方文档明示 `()` 返回不可经 ETH API 读调用——实测**发送**不受影响（faucet/fund 均 `LyquidResult<()>`，`cast send` 成功）。
  3. 节点读路径缺陷：`eth_call` 对非-bartender lyquid 一律 `Invalid contract address`（对照：同 selector 对 bartender `0x9fE4…a6e0` 可路由可执行）→ `deal_info`（view 导出，亦不可作 tx 发送）在本 devnet 不可达。**deal_info 的字面输出转由 fund 的 Ok 路径经 `lyquid::println!` 输出同一 DealView JSON**（`shaker console` 取回；console 非共识状态，语义零影响）。
  4. **http 读路径尝试失败（修订轮 R1，仲裁指令 1）**：将 deal_info 改 `export = http`（完整合法形态 `#[method::network(export = http, method = "GET", path_prefix = "/deal-info")]`）→ proc 宏在方法类别面拒绝：``error: `export = http` is only supported on #[lyquid::method::instance]``（v0.8.1 lyquid/proc/src/lib.rs:366/381；两次属性形态迭代+完整编译输出存档 `w1a-deal-info-evidence.txt` 与 `_dealinfo-http-attempt-full.txt`）。http 导出仅限 instance 方法，deal_info 改 instance = 类别语义变更，红线禁止——"新实例 + shaker serve 实调 deal_info"无构建物可部署，路径实测失败，代码已还原（export=eth，还原后通道复验 0 错）。
  5. **第三通道实测失败（修订轮 R2，仲裁人已跑、修订方复跑）**：`cast send 0x4A679253410272dd5232B3Ff7cF5dbB88f295319 "deal_info(string)" "deal-1" --private-key <anvil#0> --rpc-url http://node:10087/api` → `Error: Failed to estimate gas: server returned an error response: error code -1: Call(ErrorObject { code: ServerError(3), message: "execution reverted", data: Some(RawValue("0x")) })`（EXIT:1，与仲裁人输出一致；追加存档于 `w1a-deal-info-evidence.txt` R2 节）。根因：只读导出不被链上 selector 路由注册为交易可执行。**至此三通道全闭：eth_call（Invalid contract address，两地址）/ export=http（proc 宏类别面拒绝）/ cast send（execution reverted）**——deal_info 字面执行在当前平台面无通道。

### D4b 探针（caller 串钉死）

- 探针：`cast send <ADDR> "notarize(string,string,string,string)" "probe-deal-d4b" "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266" "bob" "deadbeef"` → **status 1（Ok(seq)，命中）**
  - rkkfz4 实例 tx `0x9f1b5c34f5ead0e16eace6f9d4c77b2ac0dbb699760512a96c299cb39924abc3`；zz2jue 实例 tx `0x2c07d9486a62fc94a1d8dc4c690a013077a5018dfe32e7a7582d206bb115cd09`
- **钉死结论：`ctx.caller.to_string()` = `"0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"`（EIP-55 checksummed hex）**；已回填 `BROKER` 常量（lib.rs），create_deal 的 broker 守卫经 T5.2 实证活化。
- 探针副作用：哑 deal_id 下留一条 evidence_log 条目（D4b-3 预告过，devnet 可接受）。

### T5 四步（全部经 PoC 通道；终实例 `Lyquid-rkkfz4d3tvxcp4aflxpqu26gxmhyxepvei3qa` @ `0x4A679253410272dd5232B3Ff7cF5dbB88f295319`）

| 步 | 命令（cast send …） | tx | block | status |
|---|---|---|---|---|
| faucet(A, 1000000) | `"faucet(string,uint128)" A 1000000` | `0x8670ba33…8b2cd0` | 29 | 1 |
| create_deal(A, "bob", 1000, 200, …) | `"create_deal(string,string,uint128,uint16,string,string,uint64,uint8)" …` | `0x5965503f…8ba9dd1` | 30 | 1 |
| fund("deal-1") | `"fund(string)" "deal-1"` | `0xfde05b2f…37b076be` | 31 | 1 |
| 状态字面 | `shaker console Lyquid-rkkfz4d3…` | — | — | — |

控制台输出（与 deal_info 同一 DealView 序列化）：

```
fund:deal_view: {"id":"deal-1","buyer":"0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266","seller":"bob","amount":1000,"state":"Funded","timeout_slots":300,"deadline_slot":331}
```

**`"state":"Funded"`（字面，存档 `workflow-out/w1a-funded-evidence.txt`）**。
首实例 zz2jue 上同路径亦全部通过（PoC tx `0x0d301eac…` 等，`workflow-out/w1a-call-poc.txt`）。

## ⑤ D7 触发记录

- **触发判据 (a) 命中**（证据 = `docker logs ldk-node-1` 实测）：
  `failed to load Lyquid … error=Hosting(…, VmRuntime(VM(Instance(Artifact(IncompatibleLdk { image: "0.7.3", node: "0.8.2-dev", hint: "rebuild the Lyquid against lyquid 0.8.2-dev or upgrade the node" })))))`
  部署（sequencing）层接受 v0.7.3 产物，但**托管/VM 层拒绝**——escrow 上链后不可 hosting、console/读路由全不可用。
- **执行**：Cargo.toml 三处 `tag="v0.7.3"` → `rev="fd575e88a920448e646f23968775e52982c5201c"`（本地 `../ldk` 克隆 v0.8.1，F15；完整 hash `git rev-parse` 实测）+ `cargo update` 重锁。
- **对照登记**（0.7.3 ↔ 0.8.1，`--strip-trailing-cr` diff 实测）：prelude.rs **逐字一致**；`LyquidError`/`CallContext`/`NetworkContextImpl` 系列字段一致；`call!` 宏一致；ethabi impls 一致（含 U128、无裸 u128）；`chain_pos()` 一致。**代码零改动即编译通过**（换锁后 `cargo check --target wasm32-unknown-unknown` → Finished，0 错）。
- **重部署**：`Platform Version: 0.8`；节点日志 `Lyquid discovered and hosted lyquid_id=Lyquid-zz2jue…`（首次完整 hosting；`shaker list --hosted-only` 含之）。
- **回退口径**（R8）：恢复 T0.5 基线 commit `5d0380f` 的 `lyquid/Cargo.toml/Cargo.lock`。**注意**：跨 LDK 大版本 `--update` 会让节点重放旧时代槽位时 pin 住 sequencing（wsd6v4 实例实测 `execution failure left sequencing pinned`）——跨此边界应全新部署（deploy.sh 头注已登记）。
- **离线工程注记**：容器无外网，fd575e8 对象经宿主 shallow 克隆仅含单 commit 树，用 `git pack-objects`（commit+tree+全 blob，无历史遍历）注入容器 cargo git db（origin 指向本地 bare，`cargo update` 离线可解析）。

## ⑥ T0 目标门与基线

- **选定检查通道**：`docker cp <lyquid>` 入 `ldk-tools-1` → 容器内 `cargo check --target wasm32-unknown-unknown`。工具链实测：`rustup target list --installed` = wasm32-unknown-unknown + x86_64-unknown-linux-gnu；`cargo 1.99.0`；`shaker 0.8.2-dev+3c9d09c`；`cast` 在容器。宿主通道不可达（平台 crate 宿主编译 4×E0425 NativeGuestAbi，容器内亦复现——native `cargo test` 因此不可行，F14a 双向印证）。
- **新编译基线**（features 后、S5 前）：**73 错**（`w1a-t0-baseline-cargo-check.txt`；分桶 lib.rs 69 / timeout.rs 4 / 四挂载文件 **0**——红线前提成立）。错误面 E0425×51 / E0433×16 / E0599×1。基线首行另有 `{{project-name}}` 包名报错：git checkout 内 lyquid-template 成员被 workspace 扫描的**通道固有噪声**，不计入错误数、与本次改动无关（终态输出仍含该行）。
- **T0.5 基线 commit：`5d0380f`**（lyquid/Cargo.toml features+注释、Cargo.lock、build.rs 平台模板文件入库；`git status` 随后干净）。
- **devnet 探活**（T0 实测）：`/api` 空 body → `-32700 Parse error`；`eth_chainId` → `0x7a69`；compose ps = ldk-node-1 + ldk-tools-1 (healthy)。
- **壳**：`verify_core` 39/39（32+5+2），T0/T1-T3 窗口/终态共 4 轮全绿。

## ⑦ 未跑/偏离项（如实登记）

1. **`shaker test`（guest 单测）已跑、全绿（0 tests 空转：guest 单测面仅跑 lib 单测、当前为 0；断言覆盖由宿主壳 39/39 承担）**。修订轮 R1 在容器 `/tmp/tb-lyquid`（src/*.rs + Cargo.toml + Cargo.lock 与 HEAD 逐文件 md5 一致，对照存档 `_container-md5.txt`）复跑：`shaker test Cargo.toml` → `running 0 tests` / `test result: ok. 0 passed; 0 failed` / **EXIT:0**（成功输出存档 `w1a-t3-shaker-test.txt`）。更正：T6 稿 §⑦-1 曾据 `w1a-t3-shaker-test-blocked.txt` 记为"未跑/被阻断"——经仲裁指出并复核，该文件实为一次**成功**的 shaker test（v0.7.3 时点，Finished test profile 23.69s → 0 tests ok），系本人当时仅看头部模板噪声行即误判，该文件已删除。补充：S5 当轮确有两次真实的 sysroot 下载失败尝试（github 不可达），其逐字实录另档 `w1a-t3-shaker-test-sysroot-download-failed.txt`（修订轮尝试复现失败时下载已成功、EXIT:0，系当时 transient 网络状况，故以会话实录形式归档并明示非本次实跑）。
2. **deal_info 字面输出通道替换**：节点读路径限制（§④-3），字面 `"state":"Funded"` 由 fund 控制台输出承载（内容 = deal_info body 的同一序列化）。deal_info 自身编译、部署、ABI 注册均在案（wasm 导出节含 `maindeal_info`）。**修订轮 R1 补记**：已按仲裁指令尝试 http 读路径（export=http 于 network 方法）——平台 proc 宏在方法类别面硬性拒绝（http 仅限 instance 方法），存档 `w1a-deal-info-evidence.txt`。**R2 补记**：第三通道（cast send）复跑失败（execution reverted），三通道全闭（§④-3 第 5 条）。**R3 结案**：偏离已经仲裁裁准（§⑧.4 引豁免原文）；**W1-B 遗留验证项：读路由修复后补跑 deal_info 实调并存档**。部署产物核验（可复现）：`docker exec ldk-tools-1 strings /tmp/tb-lyquid/lyquid_tools_target/wasm32-unknown-unknown/release/trustbridge.wasm | grep deal_info` → 命中 `maindeal_info`（多次）与 `__lyquid_method_network_3oANTF_deal_info`。
3. **committee.rs 意外修法**（§5.3 赋权范围内）：`CommitteeCertWire` 补 `#[derive(serde::Serialize, serde::Deserialize)]`——method 宏入参解码要求；纯 serde（trustbridge 与壳同款依赖），**零 `lyquid::` 路径**，领域逻辑零改动；壳 39/39 持续全绿为证。
4. **lib.rs 三项通道形态适配**（超出 §5.1 预设、由 T4.5 实测强制，逐条已内注释）：`export = eth` 五方法属性面；faucet/create_deal `amount: U128`（边界转换）；fund Ok 路径 `lyquid::println!` 输出 DealView。三者的 native 语义/方法清单/矩阵均未变。
5. **hashbrown/std 桥**（S5 新形态发现，登记）：v0.7.3/0.8.1 network state `HashMap` = hashbrown+ahash（prelude 别名），领域 `MisconductLog` = std HashMap（types.rs:181，冻结）——`apply_committee_verdict` 经 std 镜像传入/Ok 写回桥接（lib.rs 平台层，计数单点仍在 core::apply_verdict）。
6. **超范围交付**：容器 `docker cp` 已把 `_lyquor-node-bin`（节点二进制副本，二进制分析用）与 `_wsprobe.py` 留在 `workflow-out/`——诊断中间产物，未入库（.gitignore 外的手工管理，可删）。

## ⑧ 验收口径对照（§2 六条）

1. **S5 编译清零（通道限定）**：✅ 选定通道 0 错（`w1a-t3-cargo-check-final.txt`，D7 后终态）；shaker test 已跑全绿（0 tests）（§⑦-1，存档 `w1a-t3-shaker-test.txt`，EXIT:0）。
2. **壳不回退**：✅ 39/39 × 4 轮。
3. **escrow 部署**：✅ `Lyquid-rkkfz4d3…` @ `0x4A67…5319`（Platform 0.8，hosted；`w1a-deploy-output.txt`）。
4. **走到 Funded**：✅（经仲裁豁免结案，偏离登记如下）——deal_info 未实际执行（三通道全闭，`w1a-deal-info-evidence.txt`）；字面 `"state":"Funded"` 由 fund Ok 路径控制台输出承载，与 deal_info 输出同源同构（同一共识状态 + 同一 DealView::from + serde_json::to_string，lib.rs:292-298 / :473-487）；deal_info 自身已编译、部署、ABI 注册在案（release wasm 导出节含 maindeal_info）。仲裁豁免原文：'【仲裁豁免（W1-A 独立仲裁人 GLM-5.3，第 3 轮，2026-10-24）】完成定义第 4 条中 deal_info 实际执行之子要求，在本 devnet 构建（node main-latest 0.8.x）经三通道实测不可达（eth_call 拒绝非-bartender 读路由 / export=http 被 proc 宏类别面禁止 / cast send 交易 revert），属节点侧限制非实现缺陷；据此按已裁准偏离结案。条件：(a) 偏离登记永续保留，任何处不得表述为 deal_info 已实际执行；(b) W1-B 或节点读路由修复后补跑 deal_info 实调并存档（遗留验证项）；(c) 本豁免仅覆盖第 4 条 deal_info 子要求，不及其余验收条目。
5. **deploy.sh 校正**：✅ 按 D8 实测通道重写并复跑通过（复跑产出 ss7x5ed 实例，见部署档案尾注）。
6. **implementation.md**：✅ 本文件（SPIKE 23 行双向勾稽 + talc/ahash F12 + 裁定登记——**三条裁定原文逐字誊录及出处/效力精度注记见 §①**（主控会话任务文本，R2 经仲裁人取证取回），逐条映射：裁定 1→§② F12、裁定 2→§⑤ D7、裁定 3→§③ 表结构）。**修订轮 R1 行号复验证据**：命令 `grep -n "SPIKE(" src/*.rs`（@740e810）输出 23 行 = lib.rs 8/57/65/220/276/412/573/586/591/599 + timeout.rs 13/30/37/43/47/56/75 + assessor.rs 14/63/90 + committee.rs 53/77 + types.rs 18，与 §③ 表现列逐一对应、无孤儿（正反双向，摘录见 §③"行号双向复验"）。

---

# W1-B1 实现说明（平台机制探针：多节点拓扑 + S1 timer 语义 + S2 认证回合）

执行基线：`workflow-out/plan.md`（独立终裁官定稿）。代码基线 f83ab52（W1-A 完成态）。**本节 journal 与全部实验证据分档**：S1 → `w1b1-s1-timer.md`，S2 → `w1b1-s2-oracle.md`，拓扑/环境 → `w1b1-topology.md`，证据存档 `w1b1-t0-baseline.txt` / `w1b1-t2-gate.txt` / `w1b1-t2-cargo-check-final.txt` / `w1b1-t2-deploy.txt` / `w1b1-t5-gate.txt`（未入库伴档：`_w1b1-r1-submodule-state-check.txt`、`_w1b1-setupdevnet-bootstrap.log`、`_w1b1-deploy-zz2jue.txt`）。

## B-① Journal（T0→T5，2026-10-24）

| T | 内容 | 结果 | 断点产物 |
|---|---|---|---|
| T0 | git 基线（HEAD=f83ab52）、verify_core 39/39、docker ps（单节点在跑）、`ldk_cargo-cache` 卷在册 | 全过 | `w1b1-t0-baseline.txt` |
| T1 | 停单节点（`-p ldk down`，保卷）→ 起 multi 4 节点 v0.8.1 → bootstrap 三步完成（bartender `Lyquid-f7vljmg2…`→0x9fE4…a6e0，availability 4 节点 threshold 1）→ GetNodeInfo/GetPeers/GetLyquidInfo ×4 + availability status 全过 | 拓扑可用 | `w1b1-topology.md`、`_w1b1-setupdevnet-bootstrap.log` |
| T2 | R1 先验（state! 子模块）→ probe 三文件 + lib.rs 挂载 → 容器 cargo check 0 实错 → 39/39 → multi-tools 部署（4 实例迭代，最终 #4 rkkfz4d3） | 部署成功 | `w1b1-t2-cargo-check-final.txt`、`w1b1-t2-deploy.txt`、`_w1b1-r1-submodule-state-check.txt` |
| T3 | 通道先行证明 → 实验 a（reset→baseline→arm×2→delta）/ b（kill 节点服务→链连续性→双组计数）/ c（三组 delay + Recurrent 对照） | 全实录 | `w1b1-s1-timer.md` |
| T4 | 成员换算 → configure → 两阶段激活（cast call 通道）→ run_round 认证回合（on_certified 全链路 console 留痕）→ bump_threshold true/false | 认证回合跑通 | `w1b1-s2-oracle.md` |
| T5 | timeout.rs timer SPIKE 落地（仅注释，cargo check 复验）→ 三份 w1b1 文档 → 终跑测试门 → 提交 → 环境处置 | 本节 | `w1b1-t5-gate.txt` |

中断恢复说明：本轮未发生配额中断；各 T 产物文件即断点粒度（与方案 R8 约定一致）。

## B-② 受影响文件清单勾稽（10 项）

| # | 文件 | 实际改动 |
|---|---|---|
| 1 | `lyquid/src/probe/mod.rs` | 新建（模块文档 + `pub mod s1_timer/s2_oracle`；R1 记录在案） |
| 2 | `lyquid/src/probe/s1_timer.rs` | 新建（arm/arm_recurrent/on_timer/mark_fire/reset_net/get_report/**net_report（新增，通道适配）**） |
| 3 | `lyquid/src/probe/s2_oracle.rs` | 新建（configure/propose/aggregate/on_certified/run_round/bump_threshold/config + **net_config（新增）**；propose/aggregate 命名见 B-③-2） |
| 4 | `lyquid/src/lib.rs` | 3 处：`pub mod probe;`、文件头 W1-B1 注记、state! 块末尾 probe 字段（S1 instance×4 + S1 network×2 + S2 network×4 含 `network oracle cert_probe;` + S2 instance×1，主 escrow 字段零改动） |
| 5 | `lyquid/Cargo.toml` | **零改动**（方案预期兑现；无新增依赖、无 feature 变更） |
| 6 | `lyquid/src/timeout.rs` | 仅注释/SPIKE 标记三列落地（timeout.rs:2-19 模块头、:28-35 wire note、:65-84 SPIKE_1 段；`cargo check` 复验 Finished 0 实错），逻辑/签名/断言零改动 |
| 7 | `workflow-out/implementation.md` | 本节 |
| 8-10 | `w1b1-topology.md` / `w1b1-s1-timer.md` / `w1b1-s2-oracle.md` | 新建（含各自人工复现命令清单） |

伴档入库（超出 10 项清单的纯增量证据文件，随本提交一并入库以便文档引用不断链）：`w1b1-t0-baseline.txt`、`w1b1-t2-gate.txt`、`w1b1-t2-cargo-check-final.txt`、`w1b1-t2-deploy.txt`、`w1b1-t5-gate.txt`。`_` 前缀诊断伴档按 W1-A §⑦-6 惯例不入库。

## B-③ 偏离与发现登记（逐条，全部 SPIKE 或正文标注）

1. **R1 判定（state! 单例）——实证不可行，走方案既定回退**。先验读宏：`state!` 展开为调用点 `pub mod __lyquid`（ldk lyquid/src/runtime/syntax.rs:105-127），而一切方法包装宏硬编码 `crate::__lyquid::*` 上下文（syntax.rs:257 等）。cargo check 实证（子模块 state! + 探针字段，完整输出 `_w1b1-r1-submodule-state-check.txt`）：E0609 `no field probe_r1_canary on &mut __lyquid::NetworkState`（方法面解析到 crate 根 escrow state）+ E0616 `__internal ... is private`（子模块重复生成面冲突）。→ 探针字段并入 lib.rs state! 块末尾（probe_ 前缀 + 注释行，方案 §④-4 原案）。
2. **two_phase 方法命名偏离方案 §④**：宏臂字面匹配 `fn aggregate` / `fn propose`（syntax.rs:447/470），方案的 `probe_propose/probe_aggregate` 拼写无法进入 oracle 机制——落地为 `propose`/`aggregate`（group 前缀 `oracle::two_phase::cert_probe` 区分）。certified 回调名自由（`probe_on_certified`）。
3. **serde 字段名契约 + 官方 demo 潜在缺陷**：encode/decode_by_fields 按 serde 字段名严格对应（primitives/src/lib.rs:461-486；本地 serde 最小复现：`_avg_num` 无法解码 `avg_num` 编码 → `missing field`）。price-feed（rev fd575e8）propose 声明 `_avg_num/_target` 与其 run_round 编码 `avg_num/target` 不匹配，属上游 demo 潜在 bug；探针统一正确拼写（`avg_num`/`target`/`round` 三处编解码同名），s2_oracle.rs 模块头注明。
4. **`__internal` 不可达 → 方案既定回退**：`ctx.network.__internal.oracle_dest_epoch_info` 的字段无 pub（proc lib.rs:1521；cargo check E0616）——dest epoch 观测改走 host API `lyquor_api::fetch_oracle_info`（runtime/mod.rs:322；平台 `validate_finalize_epoch` 同款，source.rs:461-472），probe_config/probe_net_config 双份落档。
5. **SPIKE-1（console 可见性）**：v0.8.1 节点 console 转发按**执行通道**区分——cast send（链序）仅 network 方法 println 可见；cast call（节点本地）instance+network 均可见。适配：新增 network 观测原语 `probe_net_report`/`probe_net_config`，`probe_bump_threshold` network 化（方案 §④ 写 instance——通道适配偏离，s2_oracle.rs:224 SPIKE 标注），arm 成功分母 = cast send 回执 status。
6. **SPIKE-2（cast call 可用，方案前提修正）**："eth_call 不可用"是 W1-A 单节点 0.8.2-dev 实测；本 multi v0.8.1 读+执行均可用（`__lyquor_oracle_dest_epoch_info` 结构化读、`() `返回仍不可读调与 W1-A 一致）。激活与 run_round 改走官方 demo 的 cast call 形态（demo.sh:319-362/257-259）——cast send 通道下内层跨节点提交静默丢失（advance ×2 与 run_round 各一次实录；机制在节点侧未深挖），cast call 首试即 true。**激活等待仍按方案"观测驱动"**：dest epoch cast call 轮询（0→1 实录），无"返回 true 门"依赖。
7. **SPIKE-3（S1 结论）**：native instance trigger（Once/Recurrent）注册成功（arm status 1、无节点侧报错）但**在 multi v0.8.1 devnet 从不触发**——a：delta 0/2；b：重启 0→0 无重放（链连续 42→46）；c：三组 delay + Recurrent 产块 60s 全零。**native trigger 判定 = 不可用 → 主方案 keeper 模式（不算失败）**；timeout.rs 三处 SPIKE 标记按三列纪律落地。
8. **部署语义**：`shaker deploy` 每次创建新实例（4 个实例沿革见 w1b1-topology.md §5b；W1-A R8 已警示）， Lyquid ID 由部署者+内容确定性派生（#4 与 W1-A 主实例同 ID，异链无冲突）。
9. **单节点交叉验证未完成（S1 判定的版本维度未标定）**：切回单节点后 shaker deploy 被 rust-std sysroot 下载阻断（github 不可达：容器 TLS 掐断/拒连/挂起三种形态 ×4 次尝试；宿主直连亦不通；sysroot 缓存不随 `ldk_cargo-cache` 卷持久化，随容器层丢失——w1b1-topology.md §5 边界登记）。**"不触发"结论严格限定 multi v0.8.1 环境**；0.8.2-dev 是否同病留 W1-B2 网络可达时补测。

## B-④ SPIKE 新增标记勾稽（grep `SPIKE(W1-B1)` = 6 处，双向无孤儿）

| 位点 | 内容 | 处置 |
|---|---|---|
| s1_timer.rs:36 | trigger 目标形态（默认组 instance 方法 + `= expr` 注册期冻结） | 结论（编译+部署佐证） |
| s1_timer.rs:105 | console 通道按执行域区分（SPIKE-1 摘要） | 登记观察结论 |
| s2_oracle.rs:109 | CertifiedCallParams 构造形态镜像 price-feed | 结论（S2 回合实跑验证） |
| s2_oracle.rs:224 | bump_threshold instance→network 化（方案偏离） | 登记（通道适配） |
| s2_oracle.rs:247 | `__internal` 私有 → fetch_oracle_info 回退 | 结论（E0616 实证） |
| s2_oracle.rs:284 | 同 247（probe_config 侧注记） | 同上 |

timeout.rs 的 SPIKE(W1-1)（原保留行 timeout.rs:13/75）在本轮**结案改写**（三列假设→验证→结论，:2-19/:28-35/:65-84），W1-A §③"保留 8 行"表相应减 2（余 6 行属 S2/S3 域不动）。types.rs:18（slot 参数）未动——本轮未测 slot 时长语义。

## B-⑤ 验收口径对照（plan §⑥ 七条）

1. 测试门 ✅：`cd workflow-out/verify_core && cargo test --lib --tests` = 39/39（T0/T2/T5 三档存档 w1b1-t0-baseline / w1b1-t2-gate / w1b1-t5-gate）；部署产物编译核验 = 容器内 `cargo check --target wasm32-unknown-unknown`（w1b1-t2-cargo-check-final.txt，0 实错；`{{project-name}}` 行为 W1-A §⑥ 已登记通道噪声）。
2. 多节点 ✅：4 节点 GetNodeInfo + GetPeers≥3×4（并集=4 ID 与 toml 预置一致）+ GetLyquidInfo 同 contract×4 + ldk_cargo-cache 卷复用实测登记，全在 w1b1-topology.md §2-§5。
3. S1 ✅（多节点环境）：通道先行证明在前（w1b1-s1-timer.md §0，含通道不可见的如实登记与适配）；a/b/c 命令+原始输出齐全；a 判定域=共识 network 计数 delta（0 ≠ 2）；b 只杀节点服务、链连续性证据（42→46）+ 双组计数逐项；结论表注明判定域并对齐 timeout.rs:75-77 口径；native trigger 判定=**不可用**（附 keeper 衔接）。
4. S2 ✅：成员来源 GetNodeInfo×4 + 并集交叉核对 + 编码表/示例数组；configure（bytes32[] + creator 守卫 + 同钥）；两阶段激活 advance→dest epoch 推进→finalize→激活确认（dest epoch=1 + full config 4 成员 threshold1 + node2/3 可见）；run_round 认证回合 + on_certified println + ctx.cert.signers 原始形态（Vec<SignerID>=[0]）与映射（→Node-ve3tav…）+ set_threshold true/false——全部真实输出在 w1b1-s2-oracle.md。**通道偏离（cast send→cast call）已 SPIKE-2 登记**。
5. timeout.rs ✅：三处标记三列落地，diff 仅注释，`cargo check` 复验通过。
6. 依赖 ✅：`lyquid/Cargo.toml` 零改动（git diff 空即证）。
7. implementation.md ✅：本节含 journal 与断点说明。

## B-⑥ W1-B2 边界条件（后续输入）

1. keeper.py（W1-B2 范围）：watcher 的驱动端；S1 结论已锁"native trigger 不可依赖"。
2. S1 单节点复测（0.8.2-dev）：网络可达时补部署（w1b1-s1-timer.md §5-1）。
3. cast-send 通道下内层跨节点提交丢失（advance/run_round 同症）与 instance println console 丢失（SPIKE-1）：节点侧机制，可在 W1-B2 向平台求证或升级节点版本复测。
4. threshold=2 双签聚合（S2 加分项）未执行；bump 已入 staging，二轮 advance/finalize 即可激活。
5. 读路径补验（W1-A R3 豁免遗留项）：本环境 eth_call 可用——**deal_info 实调补跑仍未做**（本轮未部署 escrow 主合约实例，不留混探针实例；W1-B2 在干净部署上补）。
6. 环境现场：multi 栈保留运行（W1-B2 可复用；实例 #3/#4 的探针状态在卷内）；单节点切回命令见 w1b1-topology.md §7/§10。
