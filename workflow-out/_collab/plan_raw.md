## 目标

1. **定位（实证化）**：以 D1/D2 已证根因为基，在新部署实例上以分阶段只读探针 `probe_claim_sim`（cast call 可读，A:enter/B:found/C:state/D:now/E:deadline/F:payout/G/H 逐阶段报告）实证 claim_timeout 全路径逐输入无 panic；如仍有故障，探针输出直接定位到阶段。
2. **修复（双修，零 core 改动）**：
   - (a) 消除 D1：以本地 W1-B2 树重部署新实例，使 claim_timeout 进入 eth 导出面；
   - (b) 消除 D2 撞击：keeper.py 写通道由 cast send（必走 estimateGas）改为 eth_sendTransaction 不带 gas + eth_getTransactionReceipt 轮询（selector 已固化 0x786cfc8f）。
3. **闭环**：新实例重放 deal-1（faucet→create_deal→fund，timeout_slots=1 造快过期）→ 过期后 keeper 实测退款 → 五判据 Refunded 证据固化。
4. **硬约束**：types.rs / core.rs 零改动；verify_core 39/39（core 32 + escrow_lifecycle 5 + modelcheck_refund 2）在部署前与探针移除后各复验一次，另加探针加入后一次（共三检查点）；探针独立可移除（移除后 lib.rs 与基线逐字节一致）。

## 前提与已证事实（引编排者 2026-10-28 一手诊断）

- **D1（根因）**：链上实例 @ `0x1c85…dfDA0` 为旧镜像（lib.rs md5 三方互异：部署记录 b54beb9d / 容器 cd9acb36 / 本地 0b7136c3）；`balance_of`/`due_deals` 一律 Barrel(FuncNotFound) 而 `deal_info` 正常 → 部署镜像不含 W1-B2，claim_timeout 根本不在其 eth 导出面；“空 data revert” 是旧镜像路由执行错误，非 wasm panic、非 core 语义 bug。
- **D2**：eth_estimateGas 对 lyquid 合约一律 reverted data 0x（deal_info 亦然）；写通道已固化 = eth_sendTransaction 不带 gas（节点自动注气）+ receipt 轮询 status==0x1（w1b2-s4-rpc.md §B-⑤ 决策门）；2026-10-27 finding 的“新 panic”结论作废。
- **D3**：容器全 Up；deal-1@旧实例 Funded / deadline_slot=95 / 当前块 96+；anvil#0 私钥=buyer=0xf39F…92266；部署通道 = 宿主 docker cp → multi-tools:/tmp/tb-lyquid → 容器内 `shaker deploy -r http://registry:8000/lyquids --endpoint ws://node1:10087/ws --private-key 0xac09…ff80 Cargo.toml`，**每次部署出新地址**，新实例需按 w1a-funded-evidence.txt 序列重放 faucet→create_deal→fund。
- **D4**：claim_timeout（lib.rs:414-425）无 require 守卫（Anyone by design），路径 = current_slot() → core::claim_timeout → apply_payout；core::claim_timeout（core.rs:170-178）纯逻辑零 panic；current_slot()（lib.rs:709-713）`unwrap_or(0)`；ACCESS_MATRIX（lib.rs:180-193）每个 network fn 一行；keeper.py 122 行 stdlib-only，已有 decode_abi_string，cast() 走 docker exec。
- 本地未提交树（lib.rs/assessor.rs/Cargo.toml/rpc.py）= W1-B2 执行基线，全部改动叠放其上、不回退。

## 受影响文件清单（6 个）

| # | 文件 | 性质 | 改动 |
|---|---|---|---|
| 1 | lyquid/src/lib.rs | 源码 | + 探针 `probe_claim_sim`（注释围栏整块，约 +70~90 行）+ ACCESS_MATRIX 一行 |
| 2 | scripts/keeper.py | 源码 | + eth_sendTransaction 通道三函数与 calldata 编码（约 +35~45 行） |
| 3 | workflow-out/plan.md | 文档 | 本方案 |
| 4 | workflow-out/deploy-replay-evidence.txt | 证据 | 新实例部署记录 + 新镜像验证 + deal-1 重放三笔 |
| 5 | workflow-out/probe-claim-sim-evidence.txt | 证据 | 探针 A..H 双通道输出 |
| 6 | workflow-out/claim-refunded-evidence.txt | 证据 | Refunded 五判据终局证据 |

**零改动（冻结）**：lyquid/src/types.rs、lyquid/src/core.rs；**不触碰**：assessor.rs、Cargo.toml、rpc.py（保持 W1-B2 基线原样）。

## 子任务拆分与执行顺序

**T1 基线快照 + 部署前复验（检查点 R1）**
`cp lyquid/src/lib.rs /tmp/baseline-lib.w1b2`，md5 期望 0b7136c3（751 行）；跑 verify_core 39/39。
验收：39/39 全绿；md5 与行数记录入 plan 附录。

**T2 探针开发（lib.rs，详见逐文件改动点）**
验收：编译通过；verify_core 39/39 仍绿（检查点 R1.5，探针不得触碰测试断言面）。

**T3 同步预检**
docker cp 本地树 → multi-tools:/tmp/tb-lyquid；容器内 md5 比对。
验收：容器侧 lib.rs md5 == 本地探针版 md5，记录在案（消除 D1 的前提证明）。

**T4 部署新实例 + 新镜像验证**
按 D3 通道 shaker deploy（出新地址）；只读烟雾测试：`deal_info` 正常 + `balance_of(string)` 可读。
验收：新地址落档；`balance_of` 不再 Barrel(FuncNotFound)（W1-B2 在场的实证，D1 已消除）。

**T5 重放 deal-1（设计决定 3）**
按 w1a-funded-evidence.txt 原序列原通道重放：faucet（buyer=0xf39F…92266）→ `create_deal(deal_id="deal-1", seller="bob", amount=1000, timeout_slots=1)` → fund(1000)；若其写通道在新实例撞 D2，则改走 §B-⑤ eth_sendTransaction 通道（selector 现算）。
验收：`deal_info("deal-1")` 返回串含 `"state":"Funded"`；记录 deadline_slot 与当时 current_slot。
**命名论证**：沿用 deal-1——keeper 配置与 w1a/w1b2 证据链均用此名，shaker deploy 每次新实例故无实例内冲突；与旧实例混淆风险由“所有证据文件显式记录实例地址”对冲。timeout_slots=1 是造快过期的最小等待（约再等 2 slot 即 now>deadline）。

**T6 探针实测（定位阶段）**
等 current_slot > deadline_slot；`cast call probe_claim_sim("deal-1")`；同时 `docker logs multi-node1 | grep probe.claim_sim` 取日志通道。
验收：A..H 全阶段齐 + verdict=predict:claim_timeout-success→Refunded。若 verdict 非成功 → 触发 R4：保存证据、暂停、回报编排者（不做任何 core 改动）。

**T7 keeper.py 修正（设计决定 4，可与 T4–T6 并行）**
验收：`python3 -m py_compile scripts/keeper.py` 过；编码自测：`encode_claim_timeout("deal-1")` 输出与 §逐文件改动点给出的期望 hex 逐字符一致。

**T8 keeper 实测退款**
encode → eth_send（不带 gas）→ wait_receipt。
验收：tx hash + receipt `status=="0x1"`。

**T9 证据固化（设计决定 5）**
五判据齐 → claim-refunded-evidence.txt。验收：见逐文件改动点 §5.6。

**T10 探针移除 + 终态复验（检查点 R2）**
删围栏整块 + 删 ACCESS_MATRIX 行 → `cmp lyquid/src/lib.rs /tmp/baseline-lib.w1b2`（md5 == 0b7136c3）→ verify_core 39/39。
验收：cmp 逐字节无差异 + 39/39 全绿。已验证实例保留 Refunded 终态作证据，不重部署。

## 逐文件改动点

### 5.1 lyquid/src/lib.rs —— 探针（唯一合约源改动）

**放置面（设计决定 1：network 面 export=eth）**，论证：
1. 探针必须读 deals（network 状态）。W1-B1 先例用 instance 面（probe/mod.rs），但 instance 面直读 network 状态**未经验证**，会引入新的未实证读取形态；
2. network 面 export=eth 只读 getter 是已验证可 cast call 的形态（deal_info 同款，D1 实测正常返回）；
3. ACCESS_MATRIX 本就是“每个 network fn 一行”的审计面：network 面探针可被矩阵自然覆盖（加一行 Anyone + probe-removable 注记），instance 面方法反而不在矩阵内、缺审计记录；
4. 代价（探针进入生产导出面）由围栏注释 + ACCESS_MATRIX 注记 + 移除后 cmp 逐字节回基线三重对冲。
结论：network 面，只读，物理上紧邻 deal_info 放置。

**签名**：
```rust
// ==== probe-removable BEGIN: claim_timeout 分阶段探针（调试用，移除步骤见 plan.md）====
#[method::network(export = eth)]
pub fn probe_claim_sim(deal_id: String) -> Result<String, /* 与 deal_info 同款统一错误类型 */>
// ==== probe-removable END ====
```
诊断性结果一律走 `Ok(JSON串)`（含 found:false / not-yet-due / already-refunded），Err 仅保留给与 deal_info 同级的意外路径，保证 cast call 尽量可读、永不因“可诊断状态”revert。

**A~H 各阶段内容**（每阶段一行 `lyquid::println!` 日志通道 + 末尾返回值 eth 通道 = 双通道）：
- **A:enter**：输出 deal_id + 探针版本 `v: