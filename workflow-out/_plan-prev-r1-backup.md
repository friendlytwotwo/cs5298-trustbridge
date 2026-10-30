# R1 接线收尾方案：S3 LLM 接线取证 + S4 RPC 对齐收尾 + demo --node 正常流到 Settled

> 规划人：规划师（2026-10-29）。执行基线 = 当前工作树（含未提交 W1-B2 成果，**严禁回退**）。
> 阶段依据：`../FinalProject_阶段重排_2026-10-27.md` §1 R1（窗口 10-28 下午–10-29）、§2 六条设计输入（全部按已验证事实采信）。
> 上一轮（W1-B2 收尾）方案已备份为 `workflow-out/_plan-prev-w1b2-closure-backup.md`（本文件按 R1 重建）。
> R0 devnet 实测已完成：退款证据 `workflow-out/w1b2-refunded-evidence.md`、探针证据 `workflow-out/w1b2-claim-probe-evidence.txt`（采信，不重证）。

---

## 0. 受影响文件清单（供审查员核对，共 12 项）

| # | 文件 | 动作 | 持久性 |
|---|---|---|---|
| 1 | `lyquid/src/lib.rs` | `assess_brief` 签名 7→4 string（`brief_json`+`base_url`+`api_key`+`model`）并**恢复 `export = eth`**；方法体语义零改动（解析 brief 后走原 mode 契约） | **持久**（Route A） |
| 2 | `lyquid/src/assessor.rs` | `DealBrief` 增 `#[derive(serde::Deserialize)]` 一行（+注释）；**禁增删 `#[test]`**（保壳 40/40 字面） | **持久**（Route A） |
| 3 | `agents/common/rpc.py` | 新增密钥表常量（BROKER/ALICE/BOB 地址）、`nudge()`、`discover_deals()`、`assess_brief()` view 封装 + `_ABI` 新行；`due_deals` docstring 按实测注记 | **持久** |
| 4 | `scripts/demo.py` | node 模式实装：`--contract` 透传、角色→anvil 地址/私钥发送方映射、notarize sender 映射、`--flow all` 门控 + sim-only 横幅、timeout 流短估算 + nudge + 枚举适配；清除 SPIKE W1-4 标记 | **持久** |
| 5 | `scripts/keeper.py` | `--deals` 可选（缺省枚举 deal-N，设计输入①适配）、`--nudge` 助推开关（设计输入⑤）；R0 实测行为默认保留 | **持久** |
| 6 | `README.md` | 移除 SPIKE W1-4 标记两处（:107/:128 英中双栏）；LLM assessor 状态行按 R1-A 实测结果更新（条件项） | **持久** |
| 7 | `workflow-out/w1b2-r1-s3-assess.md` | 新建：S3 证据（部署记录+md5 自证+镜像自证 + assess_brief 回放/真实调用取证 + 证据通道登记） | 交付物 |
| 8 | `workflow-out/w1b2-r1-demo-normal.md` | 新建：正常流证据（faucet→create_deal→fund→submit→complete 全链 transcript + Settled 字面 + 余额勾稽） | 交付物 |
| 9 | `workflow-out/w1b2-r1-demo-timeout.md` | 新建：超时流证据（短估算建单 + nudge 轨迹 + 枚举 due + Refunded + 余额勾稽 + due_deals wire 面实测附录） | 交付物 |
| 10 | `workflow-out/_commit-plan.md` | 新建：全部未提交改动（W1-B2 遗留 + R1）的分主题提交建议清单（**不执行 git commit**） | 交付物 |
| 11 | `workflow-out/_pre-task-snapshot-r1.patch` | 新建：T0 工作树快照（事故恢复凭据，仅作 patch 不 stash） | 自保 artifact |
| 12 | `workflow-out/plan.md` | 本方案（旧案已备份 #见文件头） | 交付物 |

**不改**：`lyquid/src/types.rs`、`lyquid/src/core.rs`（语义冻结，双时点 `git diff` 勾稽）；`lyquid/Cargo.toml`（lyquid-llm git pin 已在工作树，R1 零增量）；`agents/alice.py`/`bob.py`/`broker.py`/`agents/common/llm.py`/`protocol.py`；`../workflow-out/verify_core/`（壳已修复到位，R1 不触碰）。

---

## 1. 已采信前提（任务陈述 + R0/W1-B2 存档，规划不重证）

- **D1 部署通道**：宿主 `docker cp trustbridge/lyquid/. multi-tools:/tmp/tb-lyquid`（覆盖）→ 容器内 `shaker deploy -r http://registry:8000/lyquids --endpoint ws://node1:10087/ws --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 Cargo.toml`（cwd=/tmp/tb-lyquid）；每次 deploy 全新实例新地址。容器名实测为 **`multi-tools`**（implementation.md §4-4，非 multi-tools-1）。
- **D2 写通道决策**（§B-⑤）：`eth_sendTransaction` 无 gas 字段 + `eth_getTransactionReceipt` 轮询 `status=="0x1"`；status=1 ≠ 方法 Ok（读回复核必做）。`NodeClient._send`（rpc.py:241-262）已实现。
- **D3 Stack too deep 边界**（implementation.md §2.3，证据 w1b2-claim-probe-evidence.txt §2）：7×string 参数的 instance 桩触发 solc 栈溢出；**6×string 参数桩编译通过**（签名变体实测）。这是 Route A 的直接依据：4×string < 6×string。
- **D4 println 证据通道**（implementation.md §4-6）：`docker logs` 不含任何 lyquid println；`shaker console <lyquid_id>` 缓冲回放完整可读（W1-B2 探针实证）；cast call 返回值可读（设计输入⑥）。
- **D5 守卫矩阵**（lib.rs:182-207）：create_deal=Broker、fund=Buyer、submit_deliverable=Seller、complete=Buyer、claim_timeout=Anyone、notarize 任何人可提交但 **`from` 参数必须等于 caller**（lib.rs:367-369 `from != caller → Err`）；`caller_agent(&ctx.caller) = caller.to_string()`（lib.rs:736-739）——**链上 buyer/seller 身份 = anvil 地址字符串**（W1-B2 T3 先例：buyer=DEFAULT_SENDER 地址串过守卫，w1b2-s4-rpc.md §A-1 笔 2）。
- **D6 双 sender 已验范围**（w1b2-s4-rpc.md §B-①②）：#0 与 #1 的 `from` 每调用可选已实测；**#2 作为 sender 未实测**——demo 首跑即其首次验证，结果登记进证据（见 R5）。
- **D7 timeout 换算**：`timeout_slots = max(1, est_ms×2/400)`（types.rs:195-197 口径）——est=200ms ⇒ 1 slot（R0 keeper 同款）；agent 侧回放评估 est=60000ms ⇒ 300 slots。
- **D8 壳基线**：40/40 = 33(lib, 含工作树 assessor 第 6 测) + 5(escrow) + 2(modelcheck)，w1b2-shell-rebaseline.txt:188-191 实跑存档；壳挂载面 = types/core/committee/**assessor**（lib.rs 不挂载）。
- **D9 due_deals 现状**：lib.rs:571-575 `due_deals(uint64) -> Vec<DealId>` 带 `export = eth` 已随 W1-B2 镜像部署成功（编译/部署均过），但**wire 面从未被调用验证**（NodeClient 冒烟时为旧实例 FuncNotFound，w1b2-s4-rpc.md §C[5]；R0 keeper 走显式 --deals）。设计输入①裁定按枚举适配，on-chain wire 面仅作实测附录。

## 2. 本轮规划期新实证（规划师 2026-10-29 实跑，编码员须知晓）

1. **multi devnet 当前 DOWN**：`docker ps` 守护进程可达（rc=0）但**零容器运行**——与任务陈述"容器全 Up"不符（可能已被停栈）。恢复命令：`docker compose -f "F:\canvus auto\downloads\202609CS5298\ldk\docker\multi\docker-compose.yaml" up -d`（compose 文件在位，已核实存在；w1b1-topology.md:14 同款）。节点 API `curl -s -m 3 http://127.0.0.1:10087/api` 当前无响应（与零容器一致）。**起栈后 setup-devnet one-shot 需跑完再探活**（w1b1-topology.md:17）。
2. **宿主工具链在位**：`cargo 1.99.1` ✓（W1-B2 修复后未再损坏）、`Python 3.14.5` ✓。
3. **任务陈述"rpc.py 已有密钥表"不成立（已核实）**：rpc.py 仅有 `DEFAULT_SENDER`（#0 地址，rpc.py:57）；#1/#2 地址只存在于证据文档 w1b2-s4-rpc.md:20-23。**密钥表属本方案新增项**（T2），非"用前核实"既存物。
4. **SPIKE W1-4 标记残留两处**：`scripts/demo.py:7`（docstring "(after SPIKE W1-4)"）与 `README.md:107/:128`（"NodeClient (devnet placeholder, SPIKE W1-4)" 英中双栏）。README:27-28/:40-41 的 "SPIKE-gated" 属 spike #1（timeout trigger/LLM 后端），**非 W1-4，不属本任务清除面**（其中 LLM 状态行按 R1-A 结果条件更新，见 §6-6）。
5. **宿主无 LLM 凭据**：`env | grep -i "TB_\|LLM"` 为空——规划期不可假定真实 LLM 可用；G-init ④ 门在**编码员执行时**重查环境（用户可能在执行时注入 TB_LLM_BASE_URL/API_KEY/MODEL）。
6. **demo.py node 模式缺口清点**（实读 demo.py:160-191）：无 `--contract` 透传（NodeClient 构造必炸 ValueError，rpc.py:210-212）；身份用 agent 名（node 模式必被守卫拒，D5）；`--flow all` 无门控（对抗流 `apply_committee_verdict` 在 NodeClient 直接 raise，rpc.py:351-353，flow_adversarial 会崩）；timeout 流依赖 FakeNode.tick（node 模式无对应分支）。

## 3. 目标 / 非目标

**目标**（= 交付三件套 + 附加两件）：
1. **A/S3**：`assess_brief` 在 multi devnet 上被真实驱动并留证据——回放模式（HeuristicModel）为**保底必达**；真实 LLM 通道（LyquidLlmModel）一律经 **cast call** 取证：先以本地 mock base_url 探 egress（假 api_key），通过后按需以真实凭据复跑；不可达则 **NodeError 原文 + 如实登记**（任务明示"或回放兑底+如实记录"）。
2. **B/S4**：rpc.py 补齐密钥表与对齐收尾（nudge/枚举/assess_brief 封装），SPIKE W1-4 标记清零。
3. **C/demo**：`python scripts/demo.py --node http://127.0.0.1:10087 --contract <新实例>` 正常流到 `state=="Settled"` + 余额勾稽（seller +980 / broker +20 / buyer −1000，amount=1000、fee_bps=200），全链 transcript 留档。
4. 附加：`_commit-plan.md` 分主题提交建议（不执行 commit）；全部证据 `w1b2-r1-*` 命名入 workflow-out。

**非目标**：不动 types.rs/core.rs 语义；不做对抗流上链（apply_committee_verdict 保持 sim-only，R2 范围）；不改 anvil#2 之外的新账户矩阵；不清理历史实例（0x1c85…/0xA4899D… 均为实验存档）；不修 ldk/平台自身；不做 W2' 的 E2E 收尾与真实触发器。

## 4. 总体策略（Route 决策）

**Route A（首选，本方案主线）**：把 `assess_brief` 的 7 个 string 参数收拢为 4 个（`brief_json` 一个 JSON 串 + `base_url`/`api_key`/`model` 三个后端参数），恢复 `#[method::instance(export = eth)]`。依据 D3：6×string 桩已证可编译，4×string 更浅。仓内无调用方（D3/implementation.md §2.3），改参零破坏。恢复导出后：
- **回放取证通道** = `cast call "assess_brief(string,string,string,string)" '<brief_json>' '' '' ''`——空 base_url/api_key 走 HeuristicModel（mode 契约，lib.rs:626-633），**cast call 直接返回报告 JSON**（设计输入⑥首选通道），println mode 行经 `shaker console` 双证。
- **真实 LLM 通道** = 同 calldata 带 `base_url/api_key/model` 的 **cast call**（eth_call 节点本地执行；SPIKE-1 与 w1b1-s2-oracle.md:41 已证 instance 方法经 call 可执行、返回值与 println 可达；方法 Err 以 JSON-RPC error 浮出，NodeError 可取原文）。**egress 待探针验证**（README.md:142 明示 egress 约束属待验证项，本轮不断言「需 tx 上下文」）。执行顺序：先以**本地可控 mock base_url**（宿主或容器内可达的临时 HTTP 服务，返回合法 chat_completions 形状）探 cast call egress——返回 `mode=llm` 报告 JSON 即**真实通道证据成立**（api_key 用假值，避免真实凭据进节点日志）；mock 通过后再**按需**以真实凭据复跑（仍 cast call；**证据文件中 api_key 必须脱敏**：只留 sha256 前 8 位 + 末 4 位，lib.rs:595-597 已有"DO NOT log the key"纪律）。若 eth_call 不 egress：NodeError 原文入档 + 如实登记「R1 平台 eth_call 无 http egress（实测）」，回放证据即 S3 交付面——**不得以 cast send 充当证据通道**。

**Route B（兜底，G2/G3 失败时）**：若 4×string 桩仍触发 Stack too deep（D3 证据外的意外）或 **cast call 不可用**（instance+eth 方法 eth_call 不可路由），则回退：lib.rs 撤回 export 属性（保留 4 参签名或整体回滚到 T0 快照态），S3 证据文件如实登记"assess_brief 在 R1 平台限制下不可远程驱动，S3 接线止于代码面 + 壳测试面，证据通道=登记性偏离"——任务明示此路可接受（"或选回放兑底并如实登记证据通道"）。**Route B 不阻塞目标 B/C**（demo/create_deal 不依赖 assess_brief，两步提交的第二步本就是 agent 侧评估后直接 create_deal，demo.py:73-86 现状）。

**C/demo 身份策略**：node 模式下三角色的**链上身份与发送方**统一映射到 anvil 确定性账户——BROKER=#0（DEFAULT_SENDER，create_deal/faucet/committee_config 发送方）、ALICE(buyer)=#1、BOB(seller)=#2（D6：#2 首验）。deal 的 buyer/seller 参数 = 地址字符串（D5 守卫按 `caller.to_string()` 精确比较）；notarize 的 `from` 参数 = 发送方地址串（自署名守卫）。sim 模式行为**零变化**（回归门勾稽）。

## 5. 子任务与执行顺序

### G-init 预检门（四项全过才进 T0；任一失败按处置后复检，复检仍不过 → escalate）

- ① `docker ps` 见 multi 栈容器（anvil/registry/node1-4/tools）Up。**当前实测 DOWN**（§2-1）→ `docker compose -f "F:\canvus auto\downloads\202609CS5298\ldk\docker\multi\docker-compose.yaml" up -d`，等待 one-shot setup-devnet 跑完（`docker compose -f <同上> logs setup-devnet`），复检。
- ② 节点探活：`curl -s -X POST http://127.0.0.1:10087/api -H 'content-type: application/json' --data '{"jsonrpc":"2.0","id":1,"method":"eth_blockNumber","params":[]}'` 返回含 `result`。
- ③ 宿主 `cargo --version` 可执行（当前 1.99.1 ✓）。
- ④ **S3 真实凭据决策门**：执行时环境查 `TB_LLM_BASE_URL`/`TB_LLM_API_KEY`/`TB_LLM_MODEL` 三者——仅决定 T4 mock egress 探针通过后**是否以真实凭据复跑**（全非空 → 复跑；任一缺失 → 不复跑 + 证据文件如实登记缺项，合法路径非失败）。**mock egress 探针本身无条件执行**（假 api_key、本地 mock base_url，不依赖凭据；见 §4 真实 LLM 通道 / T4-2）。

### T0 基线快照 + 三重基线确认（门 G0）

1. `git -C trustbridge diff > workflow-out/_pre-task-snapshot-r1.patch`（含全部未提交 W1-B2+R0 改动；仅恢复凭据，**不 stash/checkout/reset**）。
2. 壳基线：`cd "F:\canvus auto\downloads\202609CS5298\workflow-out\verify_core" && cargo test --lib --tests` → 预期 **33/5/2 = 40/40** 全绿（D8；失败即停，先修壳再谈 R1——壳不属于本方案改动面，失败 escalate）。
3. demo 基线：`python scripts/demo.py --selftest`（7 向量全 PASS）+ `python scripts/demo.py --sim --flow all`（三流跑通、DEMO COMPLETE）——sim 回归对照基准。
4. **G0 门**：上述全绿。不过 → escalate（基线已坏，R1 无从谈起）。

### T1 Rust 改动（lib.rs + assessor.rs，门 G1）

按 §6-1/§6-2 实施。容器编译检查（**先 cp 后查**，与 T3 合并为一次 cp 亦可）：
`docker exec multi-tools rm -rf /tmp/tb-lyquid && docker cp lyquid multi-tools:/tmp/tb-lyquid && docker exec -w /tmp/tb-lyquid multi-tools cargo check --target wasm32-unknown-unknown`（W1-B2 实测口径：host target 对 ldk 永远失败不具判据意义，implementation.md §4-3）。
**G1 门**：wasm check 零 error；`git diff lyquid/src/types.rs lyquid/src/core.rs` 输出为空。

### T2 Python/文档改动（rpc.py + demo.py + keeper.py + README）

按 §6-3/§6-4/§6-5/§6-6 实施。语法与导入门：
`python -c "import ast; [ast.parse(open(f, encoding='utf-8').read()) for f in ('scripts/demo.py','scripts/keeper.py','agents/common/rpc.py')]"` + `python scripts/demo.py --sim --flow all` 复跑（sim 回归零回退）+ `grep -rn "SPIKE W1-4" .` 零命中（workflow-out 存档除外）。
**门**：三项全过。

### T3 新实例部署（门 G2）

1. `docker cp` 已在 T1 完成（若 T1 后又有 Rust 改动须重新 cp + md5 比对杜绝 D1 型旧镜像复发：宿主 `md5sum lyquid/src/lib.rs` vs `docker exec multi-tools md5sum /tmp/tb-lyquid/src/lib.rs`）。
2. 容器内 `shaker deploy -r http://registry:8000/lyquids --endpoint ws://node1:10087/ws --private-key 0xac09…ff80 Cargo.toml`（cwd=/tmp/tb-lyquid），记录新实例 id/地址。
3. **G2 门（镜像自证）**：对新地址 (a) `cast call "balance_of(string) returns (uint128)" <任意agent>` 可路由；(b) `cast sig "assess_brief(string,string,string,string)"` 取 selector 后 `cast call <地址> "assess_brief(string,string,string,string)" '<brief_json>' '' '' ''` **返回四字段报告 JSON**（heuristic 定数 `{"qualification_score":75,"risks":["heuristic-mode"],"est_duration_ms":60000,"est_confidence":40}`，assessor.rs:89）——此即 Route A 的 P1 探针，一次通过则 G3 主证据已得。deploy 阶段若复现 Stack too deep → Route B（§4）。
4. 部署输出、md5、G2 两条原始输出全部存 `workflow-out/w1b2-r1-s3-assess.md` §1。

### T4 S3 取证收尾（门 G3）

1. **回放通道证据**（G2(b) 已覆盖则整理入档）：cast call 原始返回 + `docker exec multi-tools shaker console <lyquid_id>` 回放中的 `assess_brief: mode=heuristic report={...}` 行（D4 通道，双证）。
2. **真实 LLM 通道仅经 cast call 取证**：① egress 探针——`cast call <地址> "assess_brief(string,string,string,string)" '<brief_json>' '<mock_base_url>' '<假api_key>' '<model>'`（mock 服务返回合法 chat_completions 形状）；**成功**：cast call 返回 `mode=llm` 报告 JSON + `shaker console` 回放 `mode=llm` 行**双证**入档；**失败**：NodeError 原文入档 + 如实登记不可达原因（如「R1 平台 eth_call 无 http egress（实测）」）。**不使用 cast send 取证**（SPIKE-1 实测 instance 方法 send 通道 console 静默、Err 被平台吞掉、status 恒 0x1——「原始错误入档」经 send 不可得）。② mock 通过且 G-init ④ 凭据齐备时，按需以真实凭据同款 **cast call** 复跑（api_key 脱敏纪律不变）。
3. **G3 门**：回放证据双通道在档（或 Route B 登记在档）。

> **编码员备注（cache 写语义）**：cast call 下 `assessment_cache` 写（lib.rs:647）为节点本地临时态、**不落链**——S3 目标是取证而非缓存持久化，本轮无消费方，**不构成缺口**；回放通道取证步骤（§4 回放取证通道 / T4-1）不变。

### T5 demo --node 实测（门 G4/G5）

预置：`TB_CONTRACT=<新地址>` 或 `--contract` 传参。
1. **正常流**：`python scripts/demo.py --node http://127.0.0.1:10087 --contract <新地址> --flow normal`。全链输出（含 notarize 序列、每步 deal_info、终态与三余额）原样存 `workflow-out/w1b2-r1-demo-normal.md`。
   **G4 门**：`state=="Settled"` 字面 + 勾稽 `alice = faucet−1000`、`bob = +980`、`broker = +20`（fee=1000×200/10000）+ #2 作为 sender 首验结果登记（D6）。
2. **门控演示 + 超时流**：`python scripts/demo.py --node … --flow all` → 应只见 normal+timeout 两流且打出 "adversarial: sim-only" 横幅；timeout 流证据（短估算 deal 建单、nudge 轨迹、枚举 due 列表、claim、`state=="Refunded"`、余额 +1000 勾稽）存 `workflow-out/w1b2-r1-demo-timeout.md`。
   **G5 门**：横幅字面 + Refunded 字面 + 勾稽成立；`--flow adversarial` 显式指定时 demo 退出码≠0 且打印同款横幅（门控行为钉死）。
3. **due_deals wire 附录**：对同实例 `cast call "due_deals(uint64) returns (string[])" <当前块高>` ——无论返回列表还是 FuncNotFound，原始输出入 timeout 证据附录并在 rpc.py `due_deals` docstring 补一行实测注记（D9 收口）。

### T6 终验（门 G6）

1. sim 回归：`python scripts/demo.py --sim --flow all` + `--selftest` 全过（T0 基线对照）。
2. 壳复跑：`cd ../workflow-out/verify_core && cargo test --lib --tests` → **40/40 字面不变**（assessor 只加 derive，无测试增删）。
3. 冻结勾稽：`git diff --stat lyquid/src/types.rs lyquid/src/core.rs` 为空；`grep -rn "probe_claim_sim\|W1-B2-claim-debug" lyquid/ scripts/ agents/` 零命中（防 W1-B2 探针复发）；`grep -rn "SPIKE W1-4" README.md scripts/ agents/` 零命中。
4. **G6 门**：四项全过。

### T7 提交建议清单（无门，交付物）

`git -C trustbridge status --short` + `git diff` 全量过目后，写 `workflow-out/_commit-plan.md`：按主题给出建议提交序列（W1-B2 S3 接线 / W1-B2 S4 NodeClient / W1-B2 claim 闭环与 keeper v2 / W1-B2 证据组 / R1 S3 重导出 / R1 S4 密钥表与 demo node 模式 / R1 证据组 / parent 级壳修复单独说明——verify_core 在 trustbridge 仓库外，须注明其不入库归属），每条含建议 message、涉及文件、依赖顺序、风险注记。**不执行任何 git commit**。

## 6. 逐文件改动点

### 6-1 `lyquid/src/lib.rs`（Route A 核心，T1）

- `assess_brief`（现 :606-653）签名：
  ```rust
  #[method::instance(export = eth)] // R1 恢复导出：7→4 string（solc 6-string 实测边界，D3）
  pub fn assess_brief(
      ctx: &mut _,
      brief_json: String,   // DealBrief 四字段的 JSON 串（R1 wire 形态）
      base_url: String,
      api_key: String,
      model: String,
  ) -> LyquidResult<String> {   // 返回类型钉死不变（设计输入③）
      let brief: assessor::DealBrief = serde_json::from_str(&brief_json)
          .map_err(|e| lyquid_error(&format!("brief parse: {e}")))?;
      // ……以下方法体（mode 契约、assess、report_json、cache 键、println）零改动
  }
  ```
- 头部文档注释更新：撤下导出的偏离登记段（:600-605）改写为"R1 已恢复导出（4×string 形态，7×string 的 Stack too deep 记录留作平台限制存档）"；brief 四参数改为一参 JSON 的 wire 形态说明；后端参数明文上链的 demo trust hole 注释**保留**。
- cache 键与 println 行不变（键仍由 brief 四字段拼成，只是改从解析后的 brief 取）。
- **不改**：ACCESS_MATRIX 既有行（assess_brief 本就无守卫行）、其余方法、state! 块。

### 6-2 `lyquid/src/assessor.rs`（T1，最小面）

- `pub struct DealBrief`（:40-45）上加 `#[derive(serde::Deserialize)]` + 一行注释（R1 wire 形态：lib.rs 从 brief_json 单参解析）。字段名即 JSON 键名（snake_case，与 build_request 的入参同名，无 serde rename 需要）。
- **禁增删 `#[test]`**（保壳 33+5+2=40 字面；brief 解析的运行面验证由 G2(b)/G3 on-chain 探针承担）。

### 6-3 `agents/common/rpc.py`（T2，S4 收尾）

- **密钥表常量**（DEFAULT_SENDER 下方，来源注记 w1b2-s4-rpc.md §A-0 eth_accounts + §B-② 回执 from 验证）：
  ```python
  BROKER_ADDR = DEFAULT_SENDER            # anvil#0（create_deal/faucet/committee_config 发送方）
  ALICE_ADDR  = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"  # anvil#1 = buyer（B-① 双 sender 已验）
  BOB_ADDR    = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"  # anvil#2 = seller（sender 首验=R1 demo，D6）
  ```
  注：节点侧 dev 签名后端按 `from` 字段签名（rpc.py 模块 docstring 已载），Python 侧**不需要私钥**——任务陈述"#0/#1/#2 私钥"按平台机制落实为**地址选择**；deploy 用的 anvil#0 私钥仍只在 shaker 命令行。
- **`nudge(sender=None)`**：`self._send("faucet(string,uint128)", (self._addr(sender), 0), sender)`——benign 零额 faucet 自送，专为 automine 造一块（设计输入⑤；R0 T3 同款手法）。
- **`discover_deals(limit=10_000) -> list[str]`**：从 deal-1 起 `_deal_exists` 探测到首个缺口返回存量列表（复用 create_deal 的发现循环 rpc.py:280-283 同型；设计输入① keeper 枚举适配的 NodeClient 落点）。
- **`assess_brief(brief_json, base_url="", api_key="", model="") -> dict`**：`_view` + `_ABI` 新行 `"assess_brief(string,string,string,string)": (selector, ("string",)*4, "string")`——selector 由编码员在容器 `cast sig "assess_brief(string,string,string,string)"` 实取后**冻结进表**（先例：表头 provenance 注记）；docstring 注明 cast call 通道 + mode 契约 + api_key 上链可见的 trust hole。
- **`due_deals` docstring** 补一行：wire 面实测结果占位（T5-3 填：可路由 / FuncNotFound → 用 discover_deals）。

### 6-4 `scripts/demo.py`（T2，node 模式实装）

- **docstring**：删除 "(after SPIKE W1-4)"（:7）；补 node 模式说明（角色映射表、flow 门控、timeout 短估算偏离）。
- **角色映射**：新增模块级
  ```python
  from agents.common.rpc import ALICE_ADDR, BOB_ADDR, BROKER_ADDR  # (rpc.py 新常量)
  def role_ids(node):
      """node 模式:链上身份=anvil 地址串(D5);sim 模式:agent 名(现状零变化)。"""
      if isinstance(node, NodeClient):
          return ALICE_ADDR, BROKER_ADDR, BOB_ADDR   # alice, broker, bob
      return ALICE, BROKER, BOB
  ```
  各 flow 开头 `alice, broker, bob = role_ids(node)` 取用（faucet/建单/balance_of/notarize frm-to 全走映射值）。notarize helper 增可选 `sender=None` 透传（node 模式 `sender=frm`，满足自署名守卫 D5；sim 模式不传、行为不变）。
- **发送方矩阵**（node 模式）：faucet/committee_config/create_deal→默认(BROKER)；fund/complete→`sender=alice`；submit_deliverable→`sender=bob`；notarize→`sender=frm 对应地址`；claim_timeout→默认（Anyone）。
- **main()**：`--contract`（default None，node 模式透传 NodeClient；缺省时依赖 TB_CONTRACT，NodeClient 自带报错口径 rpc.py:210-212）；构造改 `NodeClient(args.node, contract=args.contract)`。
- **flow 门控**（设计输入④）：node 分支下 `args.flow=="all"` → `seq=["normal","timeout"]` + `banner("adversarial: sim-only — apply_committee_verdict 不在 eth 导出面(plan R3)，对抗流请 --sim")`；`args.flow=="adversarial"` → 打印同款横幅后 `sys.exit(2)`。sim 分支行为零变化。
- **flow_timeout node 分支**（设计输入⑤+①）：
  - 建单**不走 agent 侧 LLM 评估**（est=60000 ⇒ 300 slots 不可演示），直接 `node.create_deal(alice, bob, 1000, 200, <terms>, <accept>, est_ms=200, est_conf=90, sender=默认)` ⇒ timeout_slots=1（D7；R0 keeper/T3 replay 同款先例）——**登记为 demo 偏离**：node 超时流用短估算直建，60s 评估路径由正常流覆盖（正常流不受 deadline 约束）。
  - `fund(sender=alice)` → 读 `deal_info` 取 deadline_slot → **nudge 循环**：`while node.block_number() <= deadline: node.nudge()`（打印每次块高，轨迹入证据）。
  - due 发现：`due = [d for d in node.discover_deals() if node.deal_info(d)["state"]=="Funded" and block >= deadline]`（枚举适配的活演示，设计输入①）+ 打印。
  - `claim_timeout(d)` → 读回 `Refunded` + `balance_of(alice)` +1000 勾稽。
- **flow_normal**：仅身份/发送方映射替换，评估仍走 `get_llm()`（默认 ScriptedLLM est=60000——正常流无 deadline 等待，不受影响）；`new_assessed_deal` 的 create_deal 参数 buyer/seller 用映射地址。

### 6-5 `scripts/keeper.py`（T2，最小增量）

- `--deals` 改可选：缺省时 `deals = node.discover_deals()`（启动日志打印发现列表与来源 "discovered"）；显式传参行为与 R0 完全一致（证据可复跑）。
- `--nudge`（默认 **on**，`--no-nudge` 关闭）：poll 轮内存在 Funded deal 时先 `node.nudge()` 一笔再尝试 claim（设计输入⑤；docstring 登记默认值理由：R0 实测时外部预 nudged，等价行为内建化）。
- 其余（_send 直取回执、读回复核重试、日志格式）零改动。

### 6-6 `README.md`（T2）

- :107 与 :128 两栏同步：`common/rpc.py NodeClient (devnet placeholder, SPIKE W1-4) + FakeNode …` → `NodeClient (ETH JSON-RPC, S4 对齐: multi v0.8.1 实测; 角色密钥表/nudge/枚举内建) + FakeNode …`。
- :28/:41 LLM assessor 状态行（"real backend call SPIKE-gated"）：按 T4 实测结果改写——真实 LLM 跑通 → "real backend call driven on devnet (R1; replay default)"；仅回放 → "instance seam wired; on-chain driven in replay mode (R1); real backend pending egress/credentials"。**不扩写其他内容**。

### 6-7 证据文件（新建，格式要点）

- `w1b2-r1-s3-assess.md`：§1 部署（命令、实例 id/地址、md5 三方、G2(a)(b) 原始输出）§2 回放双通道证据（cast call 返回 + shaker console mode 行）§3 真实 LLM 结果 = cast call 返回的 report JSON 或 NodeError 原文（不可达原因登记；api_key 脱敏）§4 偏离登记（4 参签名 wire 形态、Route B 若触发）。
- `w1b2-r1-demo-normal.md`：命令行原文、角色映射打印、每步 deal_info（Qualified→Funded→Submitted→Settled）、notarize 序列、终态三余额与勾稽算式、tx hash（可取处：NodeClient 各步回执——demo 正常流不强求逐 tx 留痕，终态字面+勾稽为主）。
- `w1b2-r1-demo-timeout.md`：命令行、门控横幅字面、短估算建单 deal_info、nudge 块高轨迹、枚举 due 打印、claim 后 Refunded 字面 + 余额勾稽、due_deals wire 实测附录、#2 sender 首验结论（D6）。
- `_commit-plan.md`：见 T7。

## 7. 风险与回退

| # | 风险 | 概率 | 缓解/回退 |
|---|---|---|---|
| R1 | 4×string 桩仍 Stack too deep（D3 证据外） | 低 | Route B（§4）：撤 export 属性重新部署，S3 转登记性偏离；A 目标按"回放兑底+如实记录"合法达成 |
| R2 | instance+eth 方法 eth_call 不可路由（G2(b) P1 失败） | 中 | 直接 Route B（撤 export、登记性偏离；cast send 不作证据通道） |
| R3 | devnet 起栈失败 / setup-devnet 不收敛 | 中 | G-init ① 处置后复检；复检不过 escalate（环境属编排者面） |
| R4 | 真实 LLM egress 不通 / 凭据缺失 | 中 | mock egress 探针（cast call）失败 → NodeError 原文入档 + 如实登记，回放证据独立成立；凭据缺失 → 不做真实凭据复跑（mock 证据已立真实通道），缺项登记（任务明示可接受） |
| R5 | anvil#2 作为 sender 被拒（D6 未验） | 低 | 唯一理论依据是 anvil 确定性账户全量 eth_accounts 在列（§A-0 十账户）+ #1 已验同机制；失败则登记并用 #1 兼任 buyer/seller 的降级映射（buyer=#1/seller=#1 将触发 buyer==seller 守卫 lib.rs:292——不可行），**正确降级 = seller 亦用 #0 地址串**（守卫仅比对 caller 与 deal.seller 相等，#0 可作 seller；登记偏离后重跑）；仍败 escalate |
| R6 | notarize 自署名守卫拒发（from ≠ caller 串形差异，如 EIP-55 大小写） | 低 | 地址常量统一 EIP-55 串（w1b2-s4-rpc.md §A-0 原样拷贝）；若节点比较为小写不敏感/敏感差异，以实测错误文本为准修正常量并登记 |
| R7 | demo timeout 流 nudge 后 due 列表空（读滞后） | 低 | keeper 同款读回重试（5×0.4s，R0 实测口径）纳入 demo 读回 |
| R8 | sim 回归回退 | 低 | T2/T6 双时点跑 `--sim --flow all`；回退即修（Python 改动均走映射层，不动 sim 分支逻辑） |
| R9 | 误伤 W1-B2 未提交基线 | 低 | T0 快照 patch 兜底 `git apply -R`；全程禁 stash/checkout/reset |
| R10 | 壳 40/40 漂移（assessor derive 引发意外） | 低 | derive 无行为面；G6 复跑门 + 漂移即停查（壳不改，问题必在 assessor 编辑本身） |

**总回退闸**：文件级改动均有 T0 快照 + git 可恢复；链上新实例为临时造物无需回滚；历史实例（0x1c85…/0xA4899D…）保持原样（证据存档）。

## 8. 验收清单（硬约束与目标映射）

- [ ] 壳全绿 40/40 字面不变：`cd ../workflow-out/verify_core && cargo test --lib --tests` = 33/5/2（T0 与 T6 双时点）
- [ ] core 语义冻结：`git diff lyquid/src/types.rs lyquid/src/core.rs` 空（T1 与 T6 双时点）
- [ ] demo/keeper/assessor 改动不越 §0 清单（审查员对照）
- [ ] A/S3：w1b2-r1-s3-assess.md 含回放双通道证据（或 Route B 登记性偏离 + 原因）；真实 LLM 结果或缺失登记在档
- [ ] B/S4：rpc.py 密钥表/nudge/discover/assess_brief 封装在位；`grep -rn "SPIKE W1-4" README.md scripts/ agents/` 零命中
- [ ] C/demo：w1b2-r1-demo-normal.md 含 `state=="Settled"` 字面 + 三余额勾稽（+980/+20/−1000）；w1b2-r1-demo-timeout.md 含横幅字面 + `state=="Refunded"` + +1000 勾稽 + due_deals wire 附录
- [ ] sim 回归：`--selftest` 7 向量 + `--sim --flow all` 三流与 T0 基线一致
- [ ] 探针零残留：`grep -rn "probe_claim_sim\|W1-B2-claim-debug" lyquid/ scripts/ agents/` 零命中
- [ ] 附加：`_commit-plan.md` 在档（分主题、含 parent 级 verify_core 归属说明、未执行任何 git commit）
