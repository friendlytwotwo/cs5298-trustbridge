# R3-T4 方案：纯 EVM 对照实验跑数与报告（规划师，2026-10-30）

六阶段拆分②：单次实验+报告任务。不改任何已交付代码（`experiments/evm-contrast/` 三件套与 `lyquid/` 全部只读）；产物全部落在 `workflow-out/`（原始日志 + 报告 + implementation.md 增量小节）。旧 R3-T3 方案已备份为 `_plan-prev-r3t4-backup.md`（本轮规划期 cp 逐字节备份，md5 cf15233b3ad4db7b7248dddd8467ee3f 一致）。

## 0. 受影响文件清单（12 项，供审查员核对）

| # | 文件 | 动作 |
|---|---|---|
| 1 | `workflow-out/plan.md` | 覆盖写（本方案；旧 R3-T3 方案 → #12 备份） |
| 2 | `workflow-out/r3-t4-contrast-report.md` | **新建**：四维对照报告（**报告文件名以本项定义为准**） |
| 3 | `workflow-out/_r3-t4-precheck-raw.txt` | 新建：T4.0 前置核验原始输出 |
| 4 | `workflow-out/_r3-t4-md5-raw.txt` | 新建：宿主↔容器 md5 勾稽（拷出+拷回双向） |
| 5 | `workflow-out/_r3-t4-build-raw.txt` | 新建：forge build 复验原始输出 |
| 6 | `workflow-out/_r3-t4-flows-raw.txt` | 新建：run-contrast.sh 全量 report.txt（名称=脚本:10 既定） |
| 7 | `workflow-out/_r3-t4-gas-raw.txt` | 新建：逐笔 tx/status/gasUsed（名称=脚本:9 既定） |
| 8 | `workflow-out/_r3-t4-evidence-recheck-raw.txt` | 新建：EVM 侧读回执复核 + 终态读回 |
| 9 | `workflow-out/_r3-t4-lyquid-scan-raw.txt` | 新建：Lyquid 两实例只读链扫取数（含 to=null 创建交易行） |
| 10 | `workflow-out/_r3-t4-code-size-raw.txt` | 新建：代码量统计原始输出（wc + cfg(test) 起点行 + 口径声明） |
| 11 | `workflow-out/implementation.md` | 追加 §8 增量小节（不动 §0–§7） |
| 12 | `workflow-out/_plan-prev-r3t4-backup.md` | 已建（本轮规划期）：旧 plan.md 副本 |

**零改动声明**：`lyquid/`（types.rs/core.rs 等全部）、`experiments/evm-contrast/` 在本任务只读；不 git commit / add / push。

## 1. 已采信前提（任务陈述前置事实 + 本轮规划期实跑核验）

任务陈述给出：对照工程 R3 代码轮已交付且容器内 forge build 成功；R2 实例 `Lyquid-tldda6zqdhab2kdysepcqxx73uvm3sxz7wbaa` @ `0xFD6F7A6a5c21A3f503EBaE7a473639974379c351`（对抗流三裁决）；R3 实例 `Lyquid-ybidj3krshf4gqcjk3m3px6mooi6tg74twwaa` @ `0x87006e75a5B6bE9D1bbF61AC8Cd84f05D9140589`（E2 四节点认证，deal-1 Refunded）；multi devnet 全 Up；anvil#0 私钥 `0xac0974…2ff80`（run-contrast.sh:25 全量在档）。

本轮规划期实跑核验（2026-10-30，均在本机执行）：

1. `ls trustbridge/experiments/evm-contrast/` → Escrow.sol、foundry.toml、run-contrast.sh 三件套在位。
2. 通读 `run-contrast.sh`（172 行）：一键 build→deploy（forge create，`--rpc-url http://anvil:8545` + anvil#0，:76）→ committeeConfig(4 成员, threshold=3, :87) → 正常流（create→fund→notarize→deliver→complete, :94-106）→ 超时流（warp+30s→claimTimeout, :109-122）→ 争议流（伪交付→dispute→3-of-4 applyVerdict(NotFulfilled), :125-149）→ 负对照（同签名集重放到另一 deal 必须失败, :153-166）。`send()` 包装（:40-56）逐笔记 tx/status/gasUsed，status≠0x1 即退出；负对照段显式 `set +e` 容错（:160-165）。原始日志名 `_r3-t4-gas-raw.txt`/`_r3-t4-flows-raw.txt` 由脚本头部（:9-10）既定。
3. Escrow.sol（407 行）核验：`openDispute`(:245)/`applyVerdict`(:262) 在位 → **争议流适用**；`threshold`(:83)/`misconduct`(:86) 为 public 自动 getter，脚本 :89/:149 的 cast call 有效。
4. `docker ps`（本轮实跑）→ 7 容器全 Up 14 hours（multi-tools、multi-node1..4、multi-registry、multi-anvil）。
5. Lyquid 侧证据在位且可溯源：R3 终态 `_r3-t3-final-state-raw.txt`（block 341，deal-1 Refunded，faucet tx `0x5a22bd8d…` @ block 333，:27）；四节点认证回合 `_r3-t3-console-raw.txt`（e2_propose→4×aggregate→certified call→apply_verdict，:26-40）；R2 对抗三裁决+补偿 `_r2-adversarial-raw.txt`（:67-86）；keeper faucet/claim_timeout gasUsed=0x923c/0x8c9c（`_r2-keeper-loop-raw.txt`）→ **该链交易带 gasUsed，双方 receipt 对比可行**。**部署归因更正（本轮规划期实跑复验）**：既有日志中的 gasUsed=37748 **不是** R2 部署 gas——它是 R2 部署后 P2 探针交易（tx `0xae6698c7…c1c83b`，block 201，to=实例、contractAddress 空，调 apply_committee_verdict("deal-nope",0,[])，status 0x1 但方法未生效，`_r2-deploy-raw.txt:752-768`，即「status 0x1≠方法 Ok」活例）的 gas。两实例真正的链上创建交易：R2 = tx `0xaabbe98ac5153f0fdaa1a5c7952063f7c19a9fb815492fe2e5bb56ca47fdabda` @ block 199（to=null→contractAddress=0xFD6F…351，gasUsed 0x389241=3,707,457，from anvil#0）；R3 同型 = tx `0xc789080c0ecd0a7be0a440b9506a916491cc82ec914ccd5523999abd677af297` @ block 327（to=null→0x8700…589，gasUsed 0x3aa3e1=3,843,041）；两笔收据本轮已经 `docker exec multi-tools cast receipt … --rpc-url http://node1:10087/api` 只读复验（两 log 均含 register 方法+镜像哈希 ccf7498b…，与 `_r3-t3-deploy-raw.txt:76` OCI sha 一致），但**未见于任何既有日志，须 T4.5 现场取证入档 #9**。同轮实证：该链 JSON-RPC 路径为 `http://node1:10087/api`（根路径 404）。
6. 代码量基线（`wc -l`，本轮实跑）：Escrow.sol 407；lyquid/src 各文件 assessor 273 / committee 185 / committee_certified 433 / core 909 / lib 850 / timeout 86 / types 197，合计 2933（wc total 3340 含 Escrow.sol 407）。其中单元测试 760 行（三处 `#[cfg(test)]`：core.rs:309、committee.rs:92、assessor.rs:209，测试模块均延至文件尾；601+94+65=760），production 为 2173（含 lib.rs 方法层）/ 1323（仅合约本体），供 §2 判级口径、T4.6/T4.7、§4-#10 引用。
7. 冻结面现状（重要）：`git status --porcelain lyquid/ experiments/` → `M lyquid/src/assessor.rs`、`M lyquid/src/lib.rs`、`?? lyquid/src/committee_certified.rs`、`?? experiments/` —— 这是 R3 交付态的**未提交**改动（纪律：不 commit），非本轮所为。因此本轮冻结判据**不能**用「git 干净」，须用任务前后 md5 快照一致（T4.0 基线 / T4.9 复核）。
8. anvil 是 Lyquid rollup 的 sequencing backend（run-contrast.sh:12-14「共享同一 sequencer」+ console `certified call submitted to the sequencing backend`）——EVM 实验的 `evm_increaseTime` 会推进共享时间源，风险登记见 §5-R4。

## 2. 目标与判级口径（诚实红线）

**目标**：跑通对照实验、取齐双方可溯源数据、产出四维对照报告；结论如实——EVM escrow 无多节点委员会认证（委员会=deployer 管理的地址表+自建 ECRECOVER 自证），Lyquid 四节点认证的代价与收益并列。

**判级口径（报告撰写硬约束）**：
- 每个数字必须可溯源：EVM 侧 → `_r3-t4-gas-raw.txt`/`_r3-t4-evidence-recheck-raw.txt` 行；Lyquid 侧 → 本轮链扫行或既有日志 `文件:行号`。无数据的格子写「无数据（原因）」，不外推、不插值。
- 不同实例/不同链的数据并列时标注来源差异（R2 与 R3 是不同实例；gasUsed 与块数分列）。
- 定性维度（信任假设、裁决不可篡改性）必须引代码行号或日志行号；不写营销话术、不堆程度副词。
- **status 0x1 ≠ 方法成功**：终态判定以读回为准（EVM=cast call stateOf 读回；Lyquid=deal_info 读回）；R2 attempt-1「status 0x1 但 Disputed」（`_r2-adversarial-raw.txt`:7-9）作为活例在报告引用。
- 代码量对比必须**三列并注**（wc 口径）：a) Escrow.sol 407 行（单合约全部；无测试代码）；b) Lyquid 合约本体六文件（core/committee_certified/committee/types/assessor/timeout）= 2083（含测试）/ 1323（剥离 `#[cfg(test)]`；core.rs:309 起 601 行、committee.rs:92 起 94 行、assessor.rs:209 起 65 行，共 760 测试行，三处测试模块均延至文件尾）；c) lyquid/src 顶层合计 = 2933（含 lib.rs 方法层与测试）/ 2173（去测试）。**lib.rs（850 行）= 合约导出方法层/平台胶水，计入 Lyquid 合约侧**（列 c）：lib.rs:1-6 自述 "thin platform wrappers: caller guards + ledger effects"；create_deal:296 / fund:357 / notarize:398 / submit_deliverable:419 / complete:433 / claim_timeout:454 / cancel:468 / open_dispute:487 / apply_committee_verdict:520 / committee_config:545 / deal_info:561 均为 pub fn 且构成合约 eth 导出方法面（lib.rs:31-39：未导出方法过 ETH API 即 FuncNotFound，R2 起 open_dispute/apply_committee_verdict 亦 eth 导出）；shaker console 是平台查看通道（lib.rs:571），非本文件归属依据。报告如做代码量对比，须注明 Escrow 的行为验证等价物是 run-contrast.sh 三流+负对照（非单元测试）。**（终裁维持性指令 3：代码量对比严格维持本条三列口径与 #10 口径声明——含/去测试两档、lib.rs 850 计入合约侧列 c——不得回退为单口径 407-vs-2083。）**

## 3. 子任务拆分与执行顺序（T4.0 → T4.9）

**T4.0 前置核验**（→ #3 `_r3-t4-precheck-raw.txt`）：`docker ps` 7 容器全 Up；`docker exec multi-tools sh -lc 'which forge cast jq python3'` 工具齐备（脚本 send() 依赖 jq）；宿主 `md5sum lyquid/src/*.rs lyquid/Cargo.toml lyquid/Cargo.lock` + `md5sum experiments/evm-contrast/*` 留**冻结面基线快照**（§1-7 理由）。

**T4.1 拷贝勾稽**（→ #4 `_r3-t4-md5-raw.txt`）：
```
MSYS_NO_PATHCONV=1 docker exec multi-tools rm -rf /tmp/tb-evm
MSYS_NO_PATHCONV=1 docker cp experiments/evm-contrast/. multi-tools:/tmp/tb-evm
MSYS_NO_PATHCONV=1 docker exec -w /tmp/tb-evm multi-tools md5sum Escrow.sol foundry.toml run-contrast.sh
```
容器内三行 md5 与宿主基线逐一对照，3/3 MATCH 才继续。

**T4.2 build 复验**（→ #5 `_r3-t4-build-raw.txt`）：`MSYS_NO_PATHCONV=1 docker exec -w /tmp/tb-evm multi-tools forge build`。失败即停（前置已言明 build 曾成功，失败属环境回归，按 §5-R3 升级）。

**T4.3 一键三流实跑**（→ #6/#7）：`MSYS_NO_PATHCONV=1 docker exec -w /tmp/tb-evm multi-tools bash run-contrast.sh`；随后按脚本头部（:9-10）既定通道拷回：
```
MSYS_NO_PATHCONV=1 docker cp multi-tools:/tmp/tb-evm/gas-raw.txt workflow-out/_r3-t4-gas-raw.txt
MSYS_NO_PATHCONV=1 docker cp multi-tools:/tmp/tb-evm/report.txt  workflow-out/_r3-t4-flows-raw.txt
```
拷回后在容器内 `md5sum` 两文件，与宿主拷回件对照写入 #4（反向勾稽）。脚本内含 forge create 部署到 anvil#0（:76），无需单独部署步骤。

**T4.4 EVM 侧独立复核**（→ #8）：对 `_r3-t4-gas-raw.txt` **每一笔** tx：`cast receipt <tx> --rpc-url http://anvil:8545 --json` 取 status/gasUsed/blockNumber，与 gas-raw 行对拍；终态读回：`stateOf(1..4)`、`dealInfo`、buyer/seller/broker 余额、`committeeSize`/`threshold`、`misconduct(seller)`、`cast codesize <addr>`。预期：deal-1 Settled(5)、deal-2 Refunded(6)、deal-3 Refunded(6)、deal-4（负对照）Disputed(4) 且重放 applyVerdict rc≠0（脚本 :160-165 已容错记录）。**判据=读回状态，非 status 位**。

**T4.5 Lyquid 侧只读取数**（→ #9 `_r3-t4-lyquid-scan-raw.txt`）：在 multi-tools 容器内用 python（eth_getBlockByNumber full-tx，0..head，head 以 eth_blockNumber 实取为准；endpoint 用 `http://node1:10087/api`——本轮规划期实证根路径 404、JSON-RPC 在 /api（`_r2-deploy-raw.txt:753` 同源），不通则降级复用 T3.5 的 NodeClient 通道——`_r3-t3-final-state-raw.txt`:28 同型只读扫描）扫两实例地址（R3 `0x87006e…`、R2 `0xFD6F7A…`）的全部交易：block/hash/from/selector→方法名/gasUsed。**只读，不发交易**。**扫描判据（双匹配）**：除 to==实例地址的交易外，同时匹配 to==null 且 receipt.contractAddress ∈ {两实例地址} 的**创建交易**，逐笔记 block/hash/from/gasUsed；预期恰两笔——`0xaabbe98a…abda`@199（R2，gasUsed 0x389241）与 `0xc789080c…f297`@327（R3，gasUsed 0x3aa3e1），两 hash 未见于任何既有日志，本轮现场取证入档；**两笔创建交易的完整收据原文（cast receipt --json 全文）必须入档 #9，报告引用以 #9 为准（终裁维持性指令 1）**。输出与既有证据对拍：R3 faucet @333、终态 @341、认证回合 tx；R2 三裁决+补偿裁决 tx。部署环节口径：shaker deploy 虽为平台操作（OCI 镜像+registry，`_r3-t3-deploy-raw.txt`:74-89），但仍在共享链落一笔 to=null 创建交易（receipt.contractAddress=实例地址）——与 EVM forge create 部署 tx 同为 anvil#0 签名者、同链，直接可比。开销维度补：**Lyquid 部署 gasUsed + 部署→终态块跨度**（R3 327→341；R2 199→**#9 链扫实取终点为准，不写死**——参考 326：终裁轮已复核 block 326 含 to=R2 实例交易（本轮规划期 cast block 326 --full 复验 `to 0xFD6F7A6a…c351` 在列）；`_r2-final-state-raw.txt:4` 快照 315 仅作参考标注（终裁维持性指令 2））。

**T4.6 代码量统计**（→ #10）：宿主 `wc -l experiments/evm-contrast/Escrow.sol lyquid/src/*.rs`（命令不变）；运行时字节码以 #6 的 `runtimeBytecodeBytes` 行为准（codesize 复核并入 T4.4）。solloc/cloc 本机不可用（规划期核验），wc 口径可复现且足够。**#10 内容要求**：`grep -n "cfg(test)" lyquid/src/*.rs` 记录三处测试模块起点行（core.rs:309、committee.rs:92、assessor.rs:209，本轮规划期已实跑核验）；口径声明注释写明——计数工具 wc；含/去测试两档；含/不含 lib.rs 方法层两档；`lyquid/src/*.rs` 不含 probe/ 子目录；Escrow.sol 无单元测试（行为验证等价物为 run-contrast.sh 三流+负对照流程）。

**T4.7 报告撰写**（→ #2 `workflow-out/r3-t4-contrast-report.md`）：结构——
1. 实验设置（环境、实例、账户、脚本三件套 md5）；
2. **四维对照表**：①代码量（§2 三列口径：Escrow.sol 407 单合约无测试 / 合约本体六文件 2083 含测试·1323 去测试 / lyquid/src 顶层 2933 含测试·2173 去测试，lib.rs 850 计入合约侧方法层；注明 Escrow 行为验证等价物=run-contrast.sh 三流+负对照）②信任假设（EVM：committeeConfig 仅 deployer 可调 Escrow.sol:107、k-of-n=自建 ECRECOVER :385、委员会为 deployer 管理的地址表、无平台认证 vs Lyquid：平台注册 4 NodeID 委员会 threshold=4、certified call 平台通道）③裁决不可篡改性（EVM：合约存储状态+负对照「签名绑定 deal root」实证 vs Lyquid：cert.signers 链上 Vec<SignerID> 可验+R2 attempt-1 平台吞 Err 活例）④开销（EVM 逐笔 gasUsed/部署 gas/终态块跨度/交易数 vs Lyquid **部署 gasUsed**+链扫逐笔 gasUsed+认证回合消息数+**部署→终态块跨度**；部署对比口径：EVM forge create 部署 tx 与 Lyquid to=null 创建交易同为 anvil#0 签名者、同链，直接可比——shaker deploy 的 OCI/registry 环节无链上对应物，但最终落链的创建交易可直接对比）；
3. 双方链上证据引用清单（地址/tx hash/日志 `文件:行号`）；
4. 如实结论（§2 措辞约束：EVM escrow 无多节点委员会认证（自证或信任单一合约），Lyquid 四节点认证的代价与收益并列）。

**T4.8 implementation.md 增量**（→ #11）：文末追加 `## 8. §R3-T4 执行实现说明（2026-10-30）`：产物清单（#2–#10）、实跑命令摘要、数据勾稽关系、偏离登记（无偏离则记「无」）、GT4 状态表。不改 §0–§7。

**T4.9 收尾自检**：宿主重跑 T4.0 的 md5sum，与基线快照逐一对照（冻结面零改动）；`git status --porcelain` 确认本轮新增仅 workflow-out/ 产物；确认未执行任何 git commit/add/push。

## 4. 逐文件改动点

- **#1 plan.md**：本方案覆盖写（已执行；旧版 → #12 备份）。
- **#2 r3-t4-contrast-report.md**（新建）：§3-T4.7 结构，四维表+证据引用+结论；正文中文；每格数据带溯源标注（`文件:行号`）。
- **#3 _r3-t4-precheck-raw.txt**：docker ps 输出、which 四工具输出、两组 md5 基线（带命令行前缀注释）。
- **#4 _r3-t4-md5-raw.txt**：拷出勾稽（容器 3 行 vs 宿主 3 行 + MATCH 判定行）+ 拷回勾稽（容器内 2 行 vs 宿主 2 行 + MATCH 判定行）。
- **#5 _r3-t4-build-raw.txt**：forge build 全量输出+退出码。
- **#6 _r3-t4-flows-raw.txt**：容器内 report.txt 原样拷回（build/deploy/committee/三流/负对照/summary/DONE 全部段落）。
- **#7 _r3-t4-gas-raw.txt**：容器内 gas-raw.txt 原样拷回（逐笔 label/tx/status/gasUsed + deploy 行）。
- **#8 _r3-t4-evidence-recheck-raw.txt**：逐笔 receipt 复核表 + 终态读回输出（cast call 原文）+ codesize。
- **#9 _r3-t4-lyquid-scan-raw.txt**：链扫脚本原文（注释含 endpoint 与块范围）+ 逐 tx 行 + **创建交易（to=null）行 + 两笔创建交易完整收据原文（cast receipt --json 全文）** + 与既有日志对拍结论行；报告对创建交易的引用以本件为准。
- **#10 _r3-t4-code-size-raw.txt**：wc 原始输出 + cfg(test) 起点行（grep -n）+ 口径声明注释（工具/含去测试两档/含不含 lib.rs 两档/不含 probe 子目录/Escrow 无单元测试）。
- **#11 implementation.md**：文末追加 §8（增量小节，不回改既有章节）。
- **#12 _plan-prev-r3t4-backup.md**：已建（md5 与覆盖前 plan.md 一致）。

## 5. 风险与回退（编号登记，执行员逐条知晓）

- **R1 脚本单步失败**（set -euo pipefail 中断）：先把已产出的 gas-raw/report.txt 拷回留证（部分数据也是证据）；再按失败点用与脚本逐字一致的命令分步手工补跑（仅去 --json 解析差异），补跑段写入 #8 并明确标注「手工补跑」；**不改 `experiments/` 任何文件**（已交付冻结物）——若评估后认为必须改脚本才能继续，停下升级仲裁。
- **R2 forge create --json 解析失败**（jq 取 deployedTo 为空 → 后续全错）：fallback 手工 `forge create Escrow.sol:Escrow --rpc-url http://anvil:8545 --private-key <anvil#0>`（不带 --json，从输出取 deployed to/tx hash），`cast receipt` 补记 deployGasUsed；#6 保留失败原貌。
- **R3 容器工具缺失**（jq/cast/forge/python3 任一）：T4.0 which 预检提前暴露；缺失属环境问题，非本任务可自修，升级处理。
- **R4 共享 sequencer 的 warp 副作用**：anvil 是 Lyquid 的 sequencing backend，`evm_increaseTime(+30s)`（脚本 :118）推进共享时间源。缓解：R3 实例 deal-1 已终态 Refunded（`_r3-t3-final-state-raw.txt`:8 PASS）、历史块不可变、warp 幅度固定 +30s；本轮不再对该实例做任何依赖未来 slot 的操作。rollup slot 与 anvil timestamp 的换算**不在本任务范围**（报告登记一句即可，不展开）。
- **R5 链扫降级**：若链扫发现该 rollup 的部分交易无 gasUsed 字段或 endpoint 全不通 → 开销维度降级为块数/交易数 + 引 R2 既有 gasUsed（`_r2-deploy-raw.txt`/`_r2-keeper-loop-raw.txt`，标注「不同实例、同链型参考值」），报告如实标注数据缺口，不硬凑。
- **R6 anvil/容器外部重启**：已固化的 Lyquid 证据在 rollup 历史块，不受影响；EVM 侧用确定性账户可全量重跑再现。本轮**不主动重启**任何容器；发现容器 Down 先登记再升级。
- **R7 报告措辞偏差**（营销化/不对称比较）：§2 判级口径为硬约束，审查员把关；执行员自查一遍「每个形容词是否有行号支撑」。

## 6. 阶段收口门禁 GT4（全部实跑取证）

| 门 | 判据 |
|---|---|
| GT4-a | 三流终态**读回**齐备：deal-1 Settled / deal-2 Refunded / deal-3 Refunded / deal-4 Disputed（负对照重放失败 rc≠0）+ misconduct(seller) 视图值；#6/#7/#8 在档 |
| GT4-b | md5 勾稽全 MATCH：拷出 3/3 + 拷回 2/2（#4） |
| GT4-c | 报告四维表逐格可溯源（`文件:行号`），无空造数字；无数据处标注原因；代码量①维持 §2 三列口径（含/去测试两档、lib.rs 850 计入合约侧），不得回退为单口径 407-vs-2083 |
| GT4-d | Lyquid 侧数字全部来自既有日志行或 #9 链扫行；部署环节双重记载（平台操作日志 + 链上 to=null 创建交易收据），部署 gas 与部署→终态块跨度进入四维表④，不得以「无链上 deploy tx」为由留空 |
| GT4-e | 冻结面零改动：T4.9 md5 与 T4.0 基线一致；`experiments/`、`lyquid/` 未改；未 git commit/add/push |
| GT4-f | implementation.md §8 含产物清单+偏离登记（无则记「无」）+GT4 状态表 |
