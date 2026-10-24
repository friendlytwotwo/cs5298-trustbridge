# W1-A 实现说明（S5 宏漂移审计编译清零 + escrow 上 devnet 走到 Funded）

执行基线：`workflow-out/plan.md`（独立终裁官定稿）。代码仓 `trustbridge/`（git）。
提交序列：T0.5 基线 `5d0380f` → S5 编译清零 `4b0df10` → 部署/登记 `a1721b7`（+ 本次 T6 文档提交）。

---

## ① 用户 3 条裁定（登记口径）

裁定原文逐字记录存于定稿会话（任务流），仓库内无副本；为免凭空重建，此处按方案对裁定的**落地锚点**登记：

| # | 裁定要点（按方案锚点） | 本段落地 |
|---|---|---|
| 1 | （冷读仲裁意见 2 落地）**BROKER=caller 身份链**：不采纳 whoami getter，走自署名探针（notarize 哑 deal）钉死 caller 串 | D4b 已执行：`"0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"`（EIP-55）经探针钉死并回填 BROKER（§④） |
| 2 | **版本对齐属平台要求，非依赖浮动**（D7 的执行化口径）：仅凭证据触发，触发即换 rev 并全量重对照重验证 | D7 已凭节点日志证据触发：三处 pin `tag="v0.7.3"` → `rev="fd575e88a920448e646f23968775e52982c5201c"`，对照/重编译/重部署/重跑全通过（§⑤） |
| 3 | （同批流程裁定）**编码员职责边界**：实测命令即交付物；如实回报，不虚报运行结果 | 本文档所有"已验证"均为本轮实跑；不可达项如实标注（§⑦ shaker test 未跑项） |

## ② 传递 crate 登记（F12 实测）

| crate | 锁定版本 | 依据 |
|---|---|---|
| `talc` | **5.1.1** | `lyquid/Cargo.lock`（当前锁，D7 后）实测。裁定文本写 5.0.3——**与实测不符，按实测登记 5.1.1**（平台解析结果，非我方选择） |
| `ahash` | **0.8.12** | 同上，与裁定文本一致 |
| `lyquid` / `lyquid-llm` / `lyquid-test` | 0.8.1 @ `rev=fd575e8…` | D7 后锁（§⑤）；talc/ahash 为 ldk feature 传递依赖，非新增直依（红线豁免） |

## ③ SPIKE 登记表（23 行全量；grep↔表双向勾稽 `grep -c "SPIKE(" src/*.rs` = lib.rs 10 + timeout.rs 7 + assessor.rs 3 + committee.rs 2 + types.rs 1 = 23，core.rs 0）

### 处置/登记 15 行（S5 内落地或登记结论）

| 位点 | 假设 | 验证方式（本轮实跑/实读） | 处置 |
|---|---|---|---|
| lib.rs:8（现 :10 区） | 文件头 W1 待验总说明 | S5 完成 | 改为"S5 已验证 + 残余指向 W1-B" |
| lib.rs:53（现 :57） | 平台是否导出 LyquidResult | `$V7/lyquid/src/lib.rs:199`（v0.7.3）与 v0.8.1 同面实读 | 改结论：已导出同名同形，本地别名退役为 `pub use lyquid::LyquidResult;` |
| lib.rs:59（现 :65） | 错误构造器形态 | v0.7.3 `LyquidError` 枚举 :172-189（无 `msg`）+ erc20:31 同款 | 改结论：`LyquidError::LyquidRuntime(String)` |
| lib.rs:182（现 :203） | caller 访问器 | `CallContext.caller: Address`（:162）+ erc20:161 `ctx.caller` | 改结论：`ctx.caller`；BROKER 经 D4b 探针回填（§④） |
| lib.rs:236（现 :259） | network Err 是否原子回滚 | 设计不依赖该假设（fund 预检使两语义均正确）；T5 fund status=1 行为证据 | 登记：不依赖；devnet 实跑为证 |
| lib.rs:356（现 :384） | network HashMap→Vec 确定性迭代语法 | `state.committee_members.iter()` 编译通过 + :358 顺序无关性论证（ahash 种子确定） | 登记结论 |
| lib.rs:491（现 :524） | 真实 slot/height 访问器 | bartender:90-96 `lyquor_api::chain_pos()` + primitives `.block()`（u64） | 改结论：`.block()` 落地单点 |
| lib.rs:501（现 :537） | current_slot 替换为 ctx 派生 | `chain_pos()` 为无 ctx host API（runtime/mod.rs:299），单点形态保留 | 改结论；实证：T5 后 deal `created_slot=31`/`deadline_slot=331` 与链高一致 |
| lib.rs:505（现 :542） | caller 提取（ctx.from/signer） | CallContext 字段实证 | 改结论：`caller_agent(&ctx.caller)` = `caller.to_string()`（形态 D4b 钉死） |
| lib.rs:510（现 :550） | caller_agent 体内标记 | 同上 | 改结论，随 :505 落地 |
| timeout.rs:29 | 引用型注记（剩余清单） | inline 四项（34/41/44/49）全部落地 | 改写：inline 已验证，残余仅 W1-1 两处（:13/:67） |
| timeout.rs:34 | `#[method::instance]` 属性与 Context 形态 | template:48 `ctx: &mut _` 同款 + 编译通过 | 改结论 |
| timeout.rs:41 | instance fn 内取共识时间 | `crate::current_slot` 单点复用（内部 `chain_pos()`，无 ctx 依赖）+ 编译 | 改结论 |
| timeout.rs:44 | call! 跨调用形态 | **A 档**：basicswap:31 命名参数+返回解包语法，目标 `ctx.lyquid_id`（InstanceContext 字段），编译通过——无需 B 档 | 改结论（A 档落地） |
| timeout.rs:49 | guard 幂等（Funded-only, terminal-safe） | core 测试既钉（阶段一，壳 39/39 持续为证） | 登记结论 |

### 保留 8 行（W1-B 范围，标记原文未动）

| 位点 | 假设 | 保留理由 |
|---|---|---|
| timeout.rs:13 | trigger 语义需 W1-1 在 4 节点 devnet 证明 | S1/W1-B 范围 |
| timeout.rs:67 | W1-1 验收标准（kill/重启不双退、延迟上限） | S1/W1-B 范围 |
| assessor.rs:14 | lyquid-llm 导入路径（v0.7.3 实证面） | S3/W1-B 范围 |
| assessor.rs:63 | 真实后端接线前 fallback 说明 | S3/W1-B 范围 |
| assessor.rs:90 | json crate story 待定 | S3/W1-B 范围 |
| committee.rs:46 | 委员会证据集与 network evidence_log 同源假定 | S2 域（读-算-校同源已钉） |
| committee.rs:70 | Vec-in-network-state 语法待验 | S2 域（S5 编译通过即旁证） |
| types.rs:18 | devnet slot 长度参数 | S1/W1-B 定时语义（实测注：devnet `SLOT_MS` 语义下 60000ms→300 slots，见 T5 输出 `timeout_slots:300`） |

### 追加行（方案 §5.6-③ 预留）

| 追加 | 内容 |
|---|---|
| D7 触发行 | 见 §⑤：rev 上移 `fd575e8`（v0.8.1），全量对照后代码零改动、重部署重验证通过 |
| D6 追加行 | 不适用（A 档直接编译通过，B 档未启用，≤5 遗留预算消耗 **0**） |

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

1. **`shaker test`（guest 单测）未跑**：`shaker test /tmp/tb-lyquid/Cargo.toml` 失败于下载自定义 sysroot `rust-std-1.99.0-wasm32-unknown-unknown.tar.xz`（github.com 容器/宿主均不可达，Connection refused / connect timeout；全本机镜像/卷亦无该归档）。原始错误全文存档 `w1a-t3-shaker-test-blocked.txt`。替代证据（如实定性）：`lyquid/tests/` 纯核心测试与壳挂载文件同源，壳 39/39 覆盖同一断言面；native `cargo test` 不可行（平台 crate 仅 wasm 可编译）。
2. **deal_info 字面输出通道替换**：节点读路径限制（§④-3），字面 `"state":"Funded"` 由 fund 控制台输出承载（内容 = deal_info body 的同一序列化）。deal_info 自身编译、部署、ABI 注册均在案（wasm 导出节含 `maindeal_info`）。
3. **committee.rs 意外修法**（§5.3 赋权范围内）：`CommitteeCertWire` 补 `#[derive(serde::Serialize, serde::Deserialize)]`——method 宏入参解码要求；纯 serde（trustbridge 与壳同款依赖），**零 `lyquid::` 路径**，领域逻辑零改动；壳 39/39 持续全绿为证。
4. **lib.rs 三项通道形态适配**（超出 §5.1 预设、由 T4.5 实测强制，逐条已内注释）：`export = eth` 五方法属性面；faucet/create_deal `amount: U128`（边界转换）；fund Ok 路径 `lyquid::println!` 输出 DealView。三者的 native 语义/方法清单/矩阵均未变。
5. **hashbrown/std 桥**（S5 新形态发现，登记）：v0.7.3/0.8.1 network state `HashMap` = hashbrown+ahash（prelude 别名），领域 `MisconductLog` = std HashMap（types.rs:181，冻结）——`apply_committee_verdict` 经 std 镜像传入/Ok 写回桥接（lib.rs 平台层，计数单点仍在 core::apply_verdict）。
6. **超范围交付**：容器 `docker cp` 已把 `_lyquor-node-bin`（节点二进制副本，二进制分析用）与 `_wsprobe.py` 留在 `workflow-out/`——诊断中间产物，未入库（.gitignore 外的手工管理，可删）。

## ⑧ 验收口径对照（§2 六条）

1. **S5 编译清零（通道限定）**：✅ 选定通道 0 错（`w1a-t3-cargo-check-final.txt`，D7 后终态）；shaker test 未跑（§⑦-1，≤5 遗留预算消耗 0）。
2. **壳不回退**：✅ 39/39 × 4 轮。
3. **escrow 部署**：✅ `Lyquid-rkkfz4d3…` @ `0x4A67…5319`（Platform 0.8，hosted；`w1a-deploy-output.txt`）。
4. **走到 Funded**：✅ faucet→create_deal→fund 全经 PoC 通道（ETH API），fund 过 Buyer+余额+core 三重守卫；字面 `"state":"Funded"` 经 console（`w1a-funded-evidence.txt`）。
5. **deploy.sh 校正**：✅ 按 D8 实测通道重写并复跑通过（复跑产出 ss7x5ed 实例，见部署档案尾注）。
6. **implementation.md**：✅ 本文件（SPIKE 23 行双向勾稽 + talc/ahash F12 + 裁定锚点登记）。
