# W1-B2 开发计划与变更方案：S4 RPC 对齐 + deal_info 字面补验 + S3 LLM 接线 + keeper.py（W1 期收官段）

> 撰写：规划师 GLM-5.3，2026-10-25。执行基线 = `1c0e45f`（W1-B1 完成态；W1-B1 旧计划见 git 历史）。
> 修订 R1（仲裁采纳 5 条，2026-10-25）：R1#1 balance_of U128/Vect 实现/D3 豁免；R1#2 角色 sender 明文；R1#3 deal_id 发现回退算法+连跑用例；R1#4 S3 模式契约+后端构造更正；R1#5 timeout 流分支改造+时序明文。
> 修订 R2（冷读仲裁采纳 3 条，2026-10-25）：#1 assess_brief 返回面 String 钉死+序列化单点+证据路径改 cast call 返回值；#2 node 模式 --flow all 过滤+显式命令形+open_dispute 不 eth 化注记；#3 写通道双 sender 探测+回执轮询+决策门双成功条件+退路密钥表。
> 性质：**运行/验证类任务**——一切以真实命令输出为交付，严禁编造运行结果。
> 环境事实（拓扑/端口/容器通道/委员会配置）直接沿用任务给定与 `workflow-out/w1b1-topology.md` 实测存档。

---

## 受影响文件清单（供审查员核对，共 13 项）

| # | 文件 | 动作 |
|---|---|---|
| 1 | `lyquid/src/lib.rs` | 改：S3 instance 评估方法（返回面 String，R2#1）+ 若干 network 方法 `export = eth` 属性面增补 + `balance_of` 返回面 U128 边界转换（R1#1，D3 限制明文豁免）+ 相关注释 |
| 2 | `lyquid/src/assessor.rs` | 改：真后端 `AssessmentModel` 实现（lyquid-llm `call_model`）、RawAssessment 序列化/`report_json()` 单点（R2#1，types.rs 冻结不触）、SPIKE 移除 ×3 |
| 3 | `lyquid/src/timeout.rs` | 改（仅注释，视勾稽结果）：native trigger 不可用→keeper 正式化的登记性注记 |
| 4 | `agents/common/rpc.py` | 改：`NodeClient` 按 S4 实测信封重写（ETH JSON-RPC + ABI 编解码 + 退路密钥常量表 R2#3），SPIKE 移除 ×3；`FakeNode` 不动 |
| 5 | `scripts/demo.py` | 改：`--node` 模式落地（身份映射、**受守卫调用显式角色 sender（R1#2）**、committee_config 条件化、deal_id 发现（R1#3）、est 缩放、timeout 流 due/claim 块移入 sim 分支（R1#5）） |
| 6 | `scripts/keeper.py` | **新建**：生产超时路径守护器 |
| 7 | `scripts/devnet-up.sh` | 改：对准 multi 4 节点栈起法（拓扑 §1） |
| 8 | `scripts/deploy.sh` | 改：对准 multi 通道（multi-tools + registry + `--private-key`） |
| 9 | `README.md` | 改：快速开始、W1 spike 清单、API 状态表 |
| 10 | `workflow-out/implementation.md` | 改：追加 W1-B2 节（journal、偏离登记、SPIKE 勾稽、验收对照） |
| 11 | `workflow-out/w1b2-s4-rpc.md` | **新建**：S4 信封探针 + deal_info 字面补验证据 |
| 12 | `workflow-out/w1b2-s3-llm.md` | **新建**：S3 评估实跑证据（真实或回放，如实） |
| 13 | `workflow-out/w1b2-keeper-e2e.md` | **新建**：keeper 实测 + 端到端证据 |

**明示不动**：`lyquid/src/types.rs`、`lyquid/src/core.rs`（语义冻结红线）、`lyquid/src/committee.rs`、`lyquid/tests/*`（断言不变）、`lyquid/Cargo.toml`（零新增依赖——`lyquid-llm` 已是 git-pin 直接依赖，现状实读）、`agents/common/protocol.py`、`agents/common/llm.py`、`agents/alice.py bob.py broker.py`、工作区根 `workflow-out/verify_core`（临时壳，不属于本仓库）。

---

## 一、目标与验收口径

四项交付，每项按「问题→修复→验证」登记（终稿入 implementation.md W1-B2 节）：

1. **S4 RPC 对齐 + deal_info 字面补验**：`NodeClient.call()` 占位信封（POST `/lyquor/api` + JSON-RPC method 名直传，rpc.py:36-44）替换为 multi v0.8.1 实测信封；在 multi 链上对已部署 escrow 实跑 `deal_info` 字面读并归档（W1-A 仲裁豁免条件 (b) 的遗留验证项就此补办；若仍不可达则如实挂账 + escalate，绝不伪造）。
2. **S3 LLM 接线**：instance 函数内 lyquid-llm `call_model`（JsonSchema）→ 两步提交（评估入 instance 态，`create_deal` 网络提交）；真实后端跑一次资格评估+估时并留证据；API key/网络受限则 TB_LLM 回放模式撑起并如实记录（按任务口径不算失败）。
3. **keeper.py（生产超时路径）**：轮询 `due_deals` → 逐个 `claim_timeout`，多节点端点感知，幂等（链上守卫已保证）；一笔过期 Funded 交易实测「keeper 提交→退款到账」；`devnet-up.sh`/`deploy.sh`/README 同步修正。
4. **端到端**：`python scripts/demo.py --node <url> --contract <addr> --flow normal` 在 multi devnet 上正常流到 `Settled`（真实 RPC，非 sim）；超时流 `--flow timeout --est-ms 200`（fund 后接 `keeper.py --once` 认领）；对抗流 node 模式一律不执行（R2#2，sim-only）。

**硬约束（全程）**：verify_core 壳 39/39 保持（`cd workflow-out/verify_core && cargo test --lib --tests`，**工作区根起算**——壳在工作区根 `../workflow-out/verify_core`，trustbridge 仓库内无此目录，W1-B1 plan 实测口径）；types.rs/core.rs 语义冻结；SPIKE 标记验证后移除并逐处登记（§六）；不新增 crates.io 依赖，Python 端仅标准库+requests；GLM 配额窗口中断即停、按 T 产物文件续跑，不压缩验证步骤。

---

## 二、勘察结论（方案所依据的事实，均本会话实读，编码员直接引用）

1. **真实调用信封（W1-A T4.5 已钉死，implementation.md §④）**：节点 API = ETH JSON-RPC 2.0 `POST {base}/api`；方法以 **Ethereum ABI 裸函数名** 暴露在 lyquid 合约地址上（`faucet(string,uint128)`、`create_deal(string,string,uint128,uint16,string,string,uint64,uint8)`、`fund(string)`、`notarize(string,string,string,string)`、`deal_info(string)`）；回执为 anvil 兼容形状（`status`/`blockNumber`/`transactionHash`/`logs`）。当前 `rpc.py:38` 的 `{base}/lyquor/api` + `{"jsonrpc":"2.0","method":...,"params":list(args)}` 占位形状**与实测通道不符**——这就是 S4 要替换的对象。
2. **multi v0.8.1 读通道开放**：`w1b1-s2-oracle.md:40-42` 实测——单节点 0.8.2-dev 的 "Invalid contract address" 在 multi v0.8.1 不成立，`cast call` 对探针合约读与执行均可用（`probe_run_round()` 经 cast call 返回 true）。W1-B1 已在 multi 链部署**同一 trustbridge 代码**的实例 `Lyquid-rkkfz4d3…` @ `0xcbEAF3BDe82155F56486Fb5a1072cb8baAf547cc`（拓扑 §5b #4）——`deal_info`（network+export=eth，lib.rs:499）在其上的 eth_call 读即任务 1 补验对象（network 方法的 eth_call 在 multi 未实测过，属本轮真探针项）。
3. **非 eth 导出方法现状（lib.rs 实读）**：`submit_deliverable`(:352)、`complete`(:366)、`claim_timeout`(:387)、`cancel`(:401)、`open_dispute`(:417)、`apply_committee_verdict`(:434)、`committee_config`(:483)、`evidence_entries_json`(:516)、`balance_of`(:523)、`due_deals`(:534) 均为 `#[method::network]` **无 export**——ETH API 不可达。keeper（due_deals/claim_timeout）与 demo 正常流（submit_deliverable/complete/balance_of）因此需要 §四 D3 的属性面增补。守卫核对：`claim_timeout` 无 require（permissionless，lib.rs:385-398，core 守卫重推导资格与期限）；`due_deals` 纯视图、caller 提供 now 仅咨询性（:529-538）；`submit_deliverable` 需 Seller、`complete` 需 Buyer、`fund` 需 Buyer。
4. **调用者身份（D4b 钉死，implementation.md §④）**：eth 通道 caller = 交易签名者地址的 EIP-55 串（`ctx.caller.to_string()`，lib.rs:624-627）；`BROKER` 常量已回填 anvil#0 = `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266`。多角色守卫要求**多密钥**：anvil 确定性 dev 账户 #0/#1/#2 分别充任 BROKER/ALICE/BOB（地址以 `eth_accounts`/cast 实测为准）；`create_deal` 有 `buyer != seller` 硬校验（lib.rs:256）——单密钥无法走通正常流，这是 rpc.py 重写必须支持「每调用选 sender」的根据。
5. **区块推进事实（multi compose 实读）**：共享 anvil **无 `--block-time`**（`docker/multi/docker-compose.yaml` anvil 服务 entrypoint 仅 `--host/--port/--state`）→ automine 按交易出块。链上期限 `funded_slot + timeout_slots` 对 `chain_pos().block()`（lib.rs:611-615），**不发生交易则块高不走、期限不可达**——超时流实测须配合小 `est_duration_ms`（`timeout_slots_from_estimate(...).max(1)`，lib.rs:265）与 nudge 交易推进块高。W1-A 实测 60s 估计 → timeout_slots=300。
6. **lyquid-llm v0.8.1 API（ldk 克隆实读）**：`call_model<B: Backend>(backend,&ModelRequest)->LlmResult<ModelResponse>`（`lyquid-llm/src/lib.rs:459`）；后端构造（R1#4 更正后口径）：`OpenAiCompatBackend::openai(api_key:&str)` **硬编码 `https://api.openai.com/v1/responses`**（`backend/openai_compat.rs:96-98`）——自定义端点须用 `chat_completions(provider, base_url).bearer_auth(api_key)`（:117/:132，本轮实读核实）；`.output_format(OutputFormat::json_schema(name,schema))` 链式；`ModelRequest::new(model,prompt).system(..).timeout_ms(..).max_output_tokens(..)`（lib.rs:390-417）；`OutputFormat::JsonSchema{name,schema}`（lib.rs:46）。官方先例 = `lyquid-examples/shopping-assistant/src/lib.rs:113-131`。assessor.rs:14 头注的 v0.7.3 假设面在 v0.8.1 逐一核对无漂移（本轮实读）。
6b. **EthAbiType 实现面（R1#1 更正后口径，ldk 实读）**：`impl<T: EthAbiType> EthAbiType for Vec<T>` 存在（`lyquid/src/runtime/ethabi.rs:395`，fd575e8 与部署同源）——`Vec<String>`（due_deals 返回、committee_config 参数）有实现，无需 JSON 化或 keeper 回退；裸 `u128` 无实现（仅 U8..U64+U64/U128/U256 包装，W1-A §④ 实测同口径）——本轮仅命中 `balance_of` 返回面，以 U128 边界转换解决。
7. **`cast send` 对普通状态变更可用**（W1-A T5：faucet/create_deal/fund 三笔 send 全 status 1）；W1-B1 S2 发现的「cast send 内层提交静默丢失」仅影响**内部再 submit** 的 oracle 类方法——escrow 各方法无内层 submit，不受影响。
8. **S1 结论（keeper 的正当性）**：native trigger 不可用已判（W1-B1 s1-timer 存档），keeper + 链上守卫（`core::claim_timeout` 重推导）即正式方案；幂等由链上守卫保证（对非 Funded 或未到期 deal 再 claim → Err）。
9. **verify_core 壳**：工作区根 `workflow-out/verify_core`（`#[path]` 直编 types.rs/core.rs 的零平台依赖临时 crate，包名 trustbridge；其 Cargo.toml 头注实读），39 = 32(lib)+5(escrow)+2(modelcheck)，W1-B1 T5 实跑全绿（`w1b1-t5-gate.txt`）。
10. **MSYS/端口惯例**（拓扑 §6）：宿主 docker exec/compose run 带容器内路径须 `MSYS_NO_PATHCONV=1`；宿主探活 `127.0.0.1:10087|11087|12087|13087`，容器内命令 `nodeX:10087`；节点 connect-RPC 服务面（GetNodeInfo 等）在 `/lyquor.node.v1.NodeService/*`，与 ETH 面 `/api` 并存。

---

## 三、执行顺序（T0→T7，每 T 产出断点文件，配额中断可续）

### T0 基线与栈确认
1. `git status/log`（确认 HEAD=1c0e45f、工作树净）；`cd workflow-out/verify_core && cargo test --lib --tests`（工作区根起算）→ 39/39 存档 `w1b2-t0-baseline.txt`。
2. 栈确认：`docker ps` 看 multi-node1-4/anvil/registry 是否仍在跑（W1-B1 收尾保留运行，拓扑 §10）；不在则按拓扑 §1 重起（停单节点 `ldk` 栈 → `docker compose -f docker/multi/docker-compose.yaml up -d` → 等 bootstrap 三步完成）。宿主四端口 GetNodeInfo 探活（拓扑 §9 命令）。
3. 实例确认：multi-tools 容器（不存在则按拓扑 §5 命令懒建）内 `shaker list` → 记录 multi 链在册 lyquid 与合约地址（预期含 rkkfz4d3 @ 0xcbEAF3…）。

### T1 任务 1 前半：deal_info 字面补验（零代码改动，用基线实例）
1. 在 multi 实例上以 W1-A T5 同款 cast send 通道造状态（容器内、`--rpc-url http://node1:10087/api`、`--private-key <anvil#0>`）：`faucet(string,uint128)` → `create_deal(string,string,uint128,uint16,string,string,uint64,uint8)`（buyer=anvil#0 地址串，与 W1-A T5 同构，规避单密钥下的 Buyer 守卫问题）→ `fund(string)`。每笔回执（tx/block/status）留档。
2. **字面读**：`cast call --rpc-url http://node1:10087/api 0xcbEAF3… "deal_info(string) returns (string)" "deal-N"` → 期望返回 DealView JSON 字面（与 fund 控制台 `fund:deal_view:` 同构，implementation.md §④）。跨节点抽验一次（node2 通道）作状态同步证据。
3. 若读失败：按实际错误形状登记（通道仍未开 → W1-A 豁免条件 (b) 继续挂账 + **escalate 上报**，不得改代码迁就读通道、不得伪造通过）。
4. 全部命令+逐字输出归档 `w1b2-s4-rpc.md` §A（含失败分支，如有）。

### T2 任务 1 后半：S4 信封探针 + NodeClient 重写
1. **写通道探针（决策门 D2，R2#3 扩面）**：宿主 curl 对 `http://127.0.0.1:10087/api` 实测——① `eth_sendTransaction` 以 `from`=anvil#0（默认 sender）发一笔（faucet calldata 即可）；② `eth_sendTransaction` 以 `from`=anvil#1（**非默认 sender**）再发一笔；③ `eth_getTransactionReceipt` 用当轮 send 的 tx hash 轮询取回执（含 pending 形状与错误形状，逐字归档）；④ `eth_getTransactionCount`/`eth_estimateGas`/`eth_call`/`eth_blockNumber` 的透传与错误形状（JSON-RPC error 对象原样归档）。**决策门（R2#3）：#0 与 #1 双 sender 的 send 均成功才选 eth_sendTransaction 主通道；任一失败即整体走 R1 退路**（subprocess 调容器内 `cast send --private-key`，stdlib 允许），两实现同接口，决策与原始证据登记 `w1b2-s4-rpc.md`。
2. **selector 固化**：容器内 `cast sig "<ABI 签名>"` 逐方法取 4 字节 selector（Python hashlib 无 keccak-256，selector 预计算硬编码进 rpc.py 常量表，表内注明来源命令与输出，评审可复验）。
3. **`agents/common/rpc.py` 重写 NodeClient**（改动点见 §四 D1），`FakeNode` 及 `SLOT_MS/SAFETY` 等不动；移除 3 处 SPIKE(W1-4)（:8/:36/:62）并按 §六登记。
4. 冒烟：`python -c` 级小脚本对 T1 实例走「`deal_info` 读 → 错误形状触发一次（查不存在的 deal）→ `eth_blockNumber`」；输出归档 `w1b2-s4-rpc.md` §B。

### T3 代码合批：S3 接线 + export=eth 增补（一次构建、一次部署）
1. `lyquid/src/assessor.rs`：新增 `LyquidLlmModel`（实现 `AssessmentModel`：`lyquid_llm::call_model` + `OpenAiCompatBackend` + `OutputFormat::json_schema`，schema = 现四字段契约 RawAssessment）；**后端构造（R1#4）：自定义端点 = `OpenAiCompatBackend::chat_completions(provider, base_url).bearer_auth(api_key)`（openai_compat.rs:117/:132），仅默认 OpenAI 端点用 `openai(api_key)`（:96-98，硬编码 api.openai.com）**；**序列化单点（R2#1）：types.rs 冻结且 `AssessmentReport` 无 `Serialize`（types.rs:186-192 实读，derive 仅 Clone/Debug/PartialEq/Eq）——在 assessor.rs（非冻结）为 `RawAssessment` 增补 `serde::Serialize`（并 pub(crate) 化）或新增本地 view struct，向 lib.rs 提供 `report_json()`（或等效）单点**；`HeuristicModel` 保留并转正为「TB_LLM 回放模式」组件（注释改写）；移除 :14/:63/:90 三处 SPIKE 并登记。纯函数（build_request/parse_report/assess）语义零改动。
2. `lyquid/src/lib.rs`：
   - 新增 instance 评估方法（R2#1 wire 形态钉死）：`#[method::instance(export = eth)] pub fn assess_brief(...) -> LyquidResult<String>`，**返回报告 JSON 字符串**（String 的 EthAbiType 有 `deal_info` 先例，lib.rs:499）；`lyquid::println!` 保留为辅证据通道。流程：组 prompt（assessor::build_request）→ 调模型 → `parse_report` → 写 instance `assessment_cache`（现字段键型 DealId 不合「先评估后建 deal」时序，改为按 brief/terms 摘要串键或新增 instance 字段，**只动 instance 域**）→ 经 assessor.rs `report_json()` 单点序列化返回。后端参数（base_url/api_key/model）经方法参数传入（demo 密钥本就可见于 calldata，devnet 语义，注释明示；W2' 再收进配置面）。**模式契约（R1#4）：api_key/base_url 参数任一为空 → HeuristicModel（回放），否则真实 LLM；println 报告行标 `mode=heuristic|llm`。**若 T3 容器编译发现 instance 方法返回 String 的 export=eth 面另有平台限制，按 R10 同款降级路径处理并如实登记，**不得静默改回 `()`**。
   - **export=eth 属性面增补（D3，先例 = W1-A 五方法，implementation.md §④-3/§⑦-4「仅属性面；方法清单/ACCESS_MATRIX 零增删」）**：`submit_deliverable`、`complete`、`claim_timeout`、`cancel`、`due_deals`、`balance_of`、`evidence_entries_json`（视图组）；`committee_config`（Vec 参数 ABI 兼容则加，见风险 R3）；`apply_committee_verdict`（结构体参数，预期 ABI 不可编码——**不加**，对抗流留 sim，登记）；**注记（R2#2）：`open_dispute` 亦不 eth 化（对抗流组件，与 apply_committee_verdict 同留 sim）——消除「未列亦未说明」的清单歧义。**方法清单/ACCESS_MATRIX/函数体零改动，仅属性行 + 行内注释。
   - **`balance_of` 返回面 U128（R1#1）**：`Ok(U128::from(v))`，先例 = W1-A faucet/create_deal 的 amount 边界转换（lib.rs:217-220 同款注释）；这是对 D3「仅属性行」限制的**明文豁免**（唯一一处签名微调，登记入 T7 偏离）；rpc.py 按 uint128 解码，keeper/demo 断言口径不变。
   - 头注与 W1-B2 注记更新。
3. 门：容器内 `cargo check --target wasm32-unknown-unknown` 0 实错（W1-A §⑥ 通道惯例）；`cd workflow-out/verify_core && cargo test --lib --tests` 39/39（lib.rs/assessor.rs 改动均不触 types/core——若壳编译面含 assessor 则同步复验断言数不变）。
4. 部署：multi-tools 容器 `shaker deploy -r http://registry:8000/lyquids --endpoint ws://node1:10087/ws --private-key <anvil#0>`（拓扑 §4 通道）→ 新实例地址/ID 归档；`docker exec … strings …trustbridge.wasm | grep <方法名>` 抽验 ABI 导出名（W1-A §⑦-2 惯例；**抽验清单点名 `assess_brief`**，R2#1）。

> T3 是唯一同时动 Rust 两文件的批次；S3 与 keeper/demo 所需 eth 面合批一次部署，避免多次新实例漂移（`shaker deploy` 每次新建实例，拓扑 §5b）。

### T4 任务 2 收口：S3 实跑证据（`w1b2-s3-llm.md`）
1. 真实后端：宿主可及的 OpenAI 兼容端点（`TB_LLM_BASE_URL`/`TB_LLM_API_KEY`/`TB_LLM_MODEL` 环境变量族，与 agents/common/llm.py:40-42 同名）→ 容器内 **`cast call` 调 `assess_brief`，返回值（报告 JSON 字符串）逐字存档为主证据**（R2#1）；cast call 通道下 instance println 亦可见（implementation.md B-③-5），console 输出作辅证据；base_url/api_key 非空 → mode=llm，后端构造按 R1#4；**明文禁止依赖「`()` 返回读调」或「cast send 取 instance println」两形态**（分别被 B-③-6/B-③-5 封死：cast send 仅 network 方法 println 可见、`()` 返回不可读调）。**`w1b2-s3-llm.md` 记录实际 mode** → 同参数 `create_deal`（两步提交闭环：est_duration_ms/est_confidence 即评估值）→ `deal_info` 佐证 timeout_slots 由评估驱动。命令+逐字输出归档。
2. 若 API key/容器外网受限（R4）：走 TB_LLM 回放模式（HeuristicModel 路径 + Python ScriptedLLM 同构），**如实记录受限证据**（容器内探外网失败的原始输出），按任务口径不算失败、真调用留 demo 录制；SPIKE 登记结论写「已接线+回放验证，真实调用待录制」。
3. assessor.rs 三处 SPIKE 解除登记入 §六表。

### T5 任务 3：keeper.py 新建 + 过期 Funded 实测（`w1b2-keeper-e2e.md` §A）
1. **`scripts/keeper.py` 设计**（stdlib+requests）：
   - 入参：`--endpoints http://127.0.0.1:10087/api,…11087,…12087,…13087`（默认四节点，**端点感知=列表轮转/故障转移**：请求失败或超时换下一端点重试一轮）；`--contract <addr>`（或 `TB_CONTRACT`）；`--interval`/`--once`；`--sender`（默认 anvil#0 地址）。
   - 循环：`eth_blockNumber` → `due_deals(uint64)` eth_call（now=块高；advisory 性质，lib.rs:529 注记，伪造 now 至多扰动信息列表、动钱仍由 claim_timeout 重推导）→ 对每个 due `claim_timeout(string)` 写交易 → 回执后复核 `deal_info`（state=Refunded）与 `balance_of(buyer)` 前后差=amount（**退款到账实证**）。
   - 幂等：链上守卫兜底（重复 claim → Err），keeper 对单 deal 错误捕获不中断循环、下轮 due_deals 自然清空；**双跑验证**（连续两次 `--once`，第二轮零退款零变更即幂等证据）。
   - 日志逐 deal 打印（deal_id、所用端点、tx、退款额），退出码非零当且仅当存在未能认领的 due（server 错误类）。
2. **实测剧本**：T3 新实例上 faucet→create_deal（est_duration_ms=200 → timeout_slots=1，规避 §二-5 块高推进问题）→fund→记 `balance_of(buyer)` 基线→发 1-2 笔 nudge 交易（如 faucet 自转）推进块高过 deadline→`keeper.py --once`→断言 state=Refunded、buyer 余额恢复→再 `--once` 断言幂等。多端点感知证据：`--endpoints` 以 node2 为首跑一轮（或风险可控时停 node1 一轮再复起）。
3. `scripts/devnet-up.sh` 改：multi compose 起栈 + bootstrap 完成等待（GetPeers≥3 探测）+ 四端口探活；`scripts/deploy.sh` 改：multi 通道（multi-tools 懒建 + `ldk_cargo-cache` 卷复用 + `-r http://registry:8000/lyquids` + `--endpoint ws://node1:10087/ws` + `--private-key <anvil#0>` + 部署后打印新合约地址供 `TB_CONTRACT`）。两脚本头部注释保留单节点通道历史口径（标注切换法，不删 W1-A 警告）。

### T6 任务 4：端到端（`w1b2-keeper-e2e.md` §B）
1. `scripts/demo.py` 适配（改动点 §四 D4）→ `python scripts/demo.py --node http://127.0.0.1:10087 --contract <addr> --flow normal` 跑通至 `final state=Settled`（真实 RPC；结算断言=seller/broker 到账 + state 字面）。**角色 sender（R1#2）：node 模式所有受守卫调用显式传 sender——fund/complete/cancel/open_dispute→ALICE(anvil#1)、submit_deliverable→BOB(anvil#2)、notarize 维持 frm→sender 映射、faucet/create_deal/claim_timeout→默认 anvil#0**（实现可 demo 直传或 NodeClient 角色解析 helper）。
2. 超时流（时序明文，R1#5）：① `demo --flow timeout`（fund + 小 est + nudge 推块；node 分支不 claim）；② `keeper.py --once`（内部已断言 state=Refunded）；③ 事后 `deal_info` 复核 Refunded——三者同档 `w1b2-keeper-e2e.md §B`。demo.py 现状的 due_deals+claim_timeout 块在 `hasattr(node,"tick")` 分支**之外**（demo.py:121-125 实读），不存在「天然分流」——D4 将整块移入 sim 分支（或 else 臂），node 分支打印「移交给 keeper」提示后返回、**不打印 final state 断言**。
2b. 连跑用例（R1#3）：同链 normal→timeout 连跑 + 同 flow 二次运行，断言各流作用于**新建 deal**（经 deal_id 发现算法校验 `deal-{pre_max+1}` 存在且 buyer==ALICE，非旧终态 deal）。
3. 对抗流：不在任务 4 硬性范围（apply_committee_verdict 结构体参数未 eth 化，R3）——**保持 sim 验证**并在 README/implementation 登记边界；若 T3 探针发现 cert 竟可 ABI 编码则顺带尝试，不作为验收门。
4. 回归：`python scripts/demo.py --sim`（三流程）+ `--selftest`（7/7）全绿。

### T7 收官：文档 + SPIKE 勾稽 + 终门 + 提交
1. `README.md`：快速开始第 3 步改 multi 实通道并**全部用显式命令形（R2#2）**：`demo --node <url> --contract <addr> --flow normal`、`demo --node <url> --contract <addr> --flow timeout --est-ms 200`（接 `keeper.py --once`）、keeper 用法+TB_CONTRACT；**检查项：README 快速开始任何位置不得出现无 `--flow` 的裸 `demo.py --node` 形式**；「W1 spike 清单」五项逐条销项（S1/S2 W1-B1 已结、S3/S4 本轮结、宏漂移审计 W1-A S5 已结）；API 状态表更新（RPC 信封、deal_info 通道现状、keeper、超时主方案）；布局表 rpc.py/assessor.rs 描述更新；状态表日期推进。
2. `workflow-out/implementation.md` 追加 W1-B2 节：四项「问题→修复→验证」清单、journal（T0-T7）、偏离登记、受影响文件勾稽（13 项）、SPIKE 勾稽（§六表全量落地 + `grep -c "SPIKE(" src/*.rs` 双向复验惯例）、验收对照。
3. 终门：verify_core 39/39 + `--sim` 三流程 + `--selftest` 7/7 + 容器 cargo check 0 错，输出存档 `w1b2-final-gate.txt`；`git add` §清单 13 文件，单提交（信息示例：`W1-B2: S4 RPC alignment + deal_info literal read + S3 LLM wiring + keeper.py`）。

---

## 四、逐文件改动点（编码员执行细则）

**D1 `agents/common/rpc.py`（NodeClient 重写；FakeNode 语义镜像零改动）**
- 构造：`NodeClient(base_url=DEFAULT_NODE, contract=None, sender=None)`；`base_url` 形如 `http://127.0.0.1:10087`（去尾斜杠后拼 `/api`）；`contract` 必填校验（`TB_CONTRACT` 环境变量兜底）；`sender` 默认 anvil#0 地址串。
- 传输核 `_rpc(method, params)`：`requests.post(f"{base}/api", json={"jsonrpc":"2.0","id":1,"method":method,"params":params}, timeout=…)`；错误形状按 T2 实测如实封装（JSON-RPC error 对象 `{code,message,data}` → 异常携带原文，禁止吞成笼统 RuntimeError）。
- ABI 层（纯 stdlib）：`_encode(sig, args)`/`_decode(sig_ret, hex)` 仅覆盖本合约签名集类型（string/uint8/16/32/64/128/bool/string[]/定长组合），selector 常量表（T2 `cast sig` 固化，来源注释）。
- 读 `_view(sig, args)` = `eth_call [{from,to,data},"latest"]`；写 `_send(sig, args, sender)` = eth_sendTransaction（或 R1 退路 subprocess cast send），等待回执 `status==1` 否则携带链上错误上抛。
- 包装方法保持现名、与 FakeNode 同面：`faucet/create_deal/fund/notarize/submit_deliverable/complete/claim_timeout/cancel/open_dispute/apply_committee_verdict/committee_config/deal_info/evidence_entries/balance_of/due_deals`；需签名身份的加 keyword-only `sender=None`（默认客户端 sender；sim 的 FakeNode 无 caller 概念，忽略之）；`due_deals(now=None)` 缺省自动 `eth_blockNumber`；`deal_info/evidence_entries` 维持 `json.loads` 返回 dict/list；`balance_of` 按 uint128 解码（对应 wire 面 U128，R1#1），keeper/demo 断言口径不变。
- `create_deal` 的 deal_id 发现（R1#3 回退算法）：eth_sendTransaction 不返值 → 调用**前**自 n=1 向上探测 `deal_info` 至 miss 记 `pre_max`；调用**后**断言 `deal-{pre_max+1}` 存在且 buyer==ALICE，即为新 deal id；若 T2 探针证实回执 LyteLog 可解析 counter 则优先（登记采用形态）。
- 模块 docstring 改写：两传输一接口口径不变，SPIKE(W1-4) 三处移除，链接 w1b2-s4-rpc.md。

**D2 写通道形态（R2#3 决策门）**：T2 探针为准——**#0 与 #1 双 sender 的 `eth_sendTransaction` 均成功**才选其为主通道落进 `_send`；任一失败即整体走 R1 退路。`w1b2-s4-rpc.md` 登记决策与原始证据；退路实现不得引入非 stdlib 依赖。

**D3 `lyquid/src/lib.rs`**：属性行增补（仅 `#[method::network]` → `#[method::network(export = eth)]`，逐处保留「W1-B2 属性面增补，先例 W1-A 五方法」注释）；新增 `assess_brief` instance 方法 + `assessment_cache` 键型适配（instance 域）；头注 W1-B2 段。函数体/守卫/方法清单零改动。**唯一豁免（R1#1 明文）：`balance_of` 返回面 U128（`Ok(U128::from(...))`，先例 = W1-A faucet/create_deal 边界转换 lib.rs:217-220 同款注释），登记入 T7 偏离。**

**D4 `scripts/demo.py`**：node 模式身份常量（ALICE/BOB/BROKER→anvil#1/#2/#0 地址串，注释「sim 域名串仅 sim 用」）；**角色 sender 明文（R1#2）**：node 模式所有受守卫调用显式传 sender——fund/complete/cancel/open_dispute→ALICE(anvil#1)、submit_deliverable→BOB(anvil#2)、notarize 维持 frm→sender 映射、faucet/create_deal/claim_timeout→默认 anvil#0（实现可 demo 直传或 NodeClient 角色解析 helper）；`committee_config` 仅 sim 调用（node 模式链上委员会配置不属 normal/timeout 流前置；对抗流 sim 保留）；**`flow_timeout` 的 due_deals+claim_timeout 整块移入 sim 分支（或 else 臂）**（demo.py:121-125 实读：该块在 `hasattr(node,"tick")` 分支之外，无「天然分流」可言），node 分支打印「移交给 keeper」提示后返回、不打印 final state 断言（R1#5）；**node 模式 `--flow all` 过滤为 [normal, timeout]，执行前打印显式横幅「adversarial: sim-only（apply_committee_verdict 结构体参数未 eth 化，R3）」，`flow_adversarial` 在 node 模式一律不执行（R2#2）；sim 模式 `all` 行为逐字节不变（回归门覆盖）**；可选 `--est-ms` 覆盖（node 超时流小 est 用）；`--contract` 参数透传 NodeClient；sim 路径行为逐字节不变（回归门保证）。

**D5 `scripts/keeper.py`**（新建，§三 T5-1 规格）；**D6 两 shell 脚本**（§三 T5-3）；**D7 `README.md`/`implementation.md`/三份证据文档**（§三 T7 与各 T 内联）。

---

## 五、风险与回退

| # | 风险 | 缓解/决断 | 回退 |
|---|---|---|---|
| R1 | 节点 `/api` 不透传 `eth_sendTransaction`（无签名后端，或仅默认账户可用） | T2 探针决策门（**双 sender #0+#1 均成功才算过**，R2#3）；退路 subprocess 容器 cast send（multi-tools 懒建，拓扑 §5），同接口替换；**退路形态：rpc.py 常量表 pin anvil #0/#1/#2 地址→私钥映射，表内注明来源（anvil 确定性 dev 账户，anvil CLI 启动横幅/官方文档；地址以 eth_accounts/cast 实测为准，呼应 §二-4）** | 写通道两实现并存，切换由探针结论定，均登记 |
| R2 | multi 上 network 方法 eth_call 读仍失败（与任务给定事实相悖） | T1 先测基线实例；失败则 W1-A 豁免条件 (b) 继续挂账 + escalate 上报，绝不改代码迁就或伪造 | 无代码回退需求（T1 零改动） |
| R3 | `CommitteeCertWire` 结构体参数的 EthAbiType 可编码性未知 → apply_committee_verdict 可能加不上 export（对抗流留 sim） | 以 T3 容器编译为准；`Vec<String>` **有**实现（`impl<T: EthAbiType> EthAbiType for Vec<T>`，ldk `lyquid/src/runtime/ethabi.rs:395` 本轮实读，fd575e8 与部署同源）——due_deals 返回/committee_config 参数不受阻，无需 JSON 化或 keeper 回退；裸 `u128` 无实现仅命中 balance_of（R1#1 已以 U128 边界转换解决） | 不属验收门（任务 4 只卡 normal+timeout） |
| R4 | 容器无外网 / 无 LLM API key → S3 真调用跑不了 | TB_LLM 回放模式撑起 + 受限证据（探外网失败原始输出）如实归档；按任务口径不算失败 | 无需回退；SPIKE 结论如实写「接线完成+回放验证」 |
| R5 | automine 链块高不推进 → 期限不可达 | est_duration_ms=200（timeout_slots=1）+ nudge 交易；剧本写入 T5/T6 | — |
| R6 | 新部署 `--update` 重置状态 / 跨版本 pin（W1-A §⑤ 实测） | 全新部署（新实例）+ demo 幂等重建世界；deploy.sh 头注保留 W1-A 警告 | `docker compose -f docker/multi/docker-compose.yaml down -v` 重置链（实验现场销毁，最后手段） |
| R7 | MSYS 路径改写 / 宿主-容器端点混用 | 全程 `MSYS_NO_PATHCONV=1` 前缀；宿主 `127.0.0.1:100X87`、容器 `nodeX:10087`（拓扑 §6） | — |
| R8 | GLM 配额中断 | 每 T 产物文件即断点；journal 先写后跑；恢复从 T0 核对基线续跑 | 不压缩验证步骤（硬约束） |
| R9 | verify_core 壳被 lib.rs/assessor.rs 改动波及（壳若 #[path] 编入 assessor） | T3 门跑壳 39/39 强制核对；断言数不变 | 单提交整体回退（git checkout）；types/core 未触，壳独立于仓库 |
| R10 | S3 wasm 面编译失败（lyquid-llm 在 Lyquid 目标的 egress 形态） | 官方先例 shopping-assistant 同面编译；失败则 instance 方法降级为「构造 ModelRequest + println 序列化」半接线并如实登记 | assessor.rs seam 结构保证 HeuristicModel 路径始终可用 |

---

## 六、SPIKE 标记处置登记表（假设→验证方式→结论，终稿入 implementation.md）

| 现标记 | 假设 | 验证方式 | 结论（预期落点） |
|---|---|---|---|
| rpc.py:8 信封未知 | POST /lyquor/api + method 直传 | T2 实测：ETH JSON-RPC @ /api、裸 ABI 名、anvil 回执/错误形状 | 移除；结论=ETH ABI 通道，指针 w1b2-s4-rpc.md |
| rpc.py:36 mangling/编码/错误形状 | 同上 | 同上 + `cast sig` selector 固化 | 同上 |
| rpc.py:62 cert wire 2 字段 | root 只在域级证书传 | committee.rs 现读（S5 已核）+ D3 决定 apply_committee_verdict 不 eth 化 | 移除；wire 形态维持域级三元的文档化说明 |
| demo.py:7 --node 待 W1-4 | — | T6 实跑 --node normal→Settled | 移除 |
| assessor.rs:14 import 路径 | v0.7.3 文档面 | ldk v0.8.1 源实读（本轮已核：call_model lib.rs:459 / openai openai_compat.rs:96 / JsonSchema lib.rs:46）+ 容器编译 | 移除；路径钉死 |
| assessor.rs:63 真后端前 Heuristic 兜底 | — | T3/T4 接线+实跑（或 R4 回放）；模式契约（R1#4）：api_key/base_url 任一空→Heuristic，println 标 `mode=heuristic\|llm`；后端构造 = 自定义端点 `chat_completions(provider,base_url).bearer_auth(api_key)`（openai_compat.rs:117/:132）、默认端点 `openai(api_key)`（:96-98） | 移除；HeuristicModel 转正为「TB_LLM 回放模式」组件，注释改写 |
| assessor.rs:90 json crate 故事 | serde_json 待定 | W1-A 已定（Cargo.toml 注释在案） | 移除（补指针） |
| timeout.rs:30 残留 SPIKE 项 | instance 属性/Context/时间接线 | S1 已判（W1-B1）；T7 勾稽逐行核，属 keeper 正式化范围者随本节收口，不属于者保留并注明归属 | 保守处理：只动确证行，cargo check 复验 |

最终 `grep -n "SPIKE(" src/*.rs` + rpc.py/demo.py 全量勾稽（W1-B1 B-④ 惯例：双向无孤儿）。

---

## 七、验证清单（命令级，全部须真实输出存档）

1. `cd workflow-out/verify_core && cargo test --lib --tests` = 39/39（T0/T3/T7 三窗口，工作区根起算）。
2. 容器 `cargo check --target wasm32-unknown-unknown` 0 实错（T3 后）。
3. `cast call … "deal_info(string) returns (string)"` 逐字输出（T1，multi 链基线实例）。
4. S4 探针矩阵原始输出：eth_call / `eth_sendTransaction` **双 sender（#0 与 #1）各 ≥1 例** / `eth_getTransactionReceipt` ≥1 例（含 pending/错误形状）/ eth_blockNumber / 错误形状各 ≥1 例（T2，R2#3）。
5. `assess_brief` 实调证据（真实或回放+受限证据）= **cast call 返回值逐字 + console println 辅证**（T4，R2#1）。
6. keeper 实测：balance_of 前后差、deal_info state=Refunded、双跑幂等、多端点轮转日志（T5）。
7. `python scripts/demo.py --node … --flow normal` 输出含 `final state=Settled`；timeout 时序（R1#5）：demo --flow timeout（fund+小 est+nudge）→ `keeper.py --once`（内部已断言 state=Refunded）→ 事后 deal_info 复核 Refunded，三者同档 `w1b2-keeper-e2e.md §B`（T6）；连跑用例（normal→timeout 连跑、同 flow 二次运行作用于新建 deal）逐字输出（T6-2b）。
8. `python scripts/demo.py --sim`（三流程账目守恒）与 `--selftest`（7/7）全绿（T6/T7）。
9. SPIKE 勾稽 grep 双向 + implementation.md W1-B2 节 + README 快速开始/API 表更新（T7）。

> W1 期至此收官；W2' 正常流开发另行安排，不在本方案范围。
