# R3-T4 对照报告：纯 EVM Escrow 与 Lyquid 托管（四维）

- 执行轮次：R3-T4（2026-10-30）
- 方案：`workflow-out/plan.md`（本轮定稿）
- 本报告所有数字均带溯源标注（`文件:行号` 或 `文件 §节`）。凡无数据处一律写「无数据（原因）」，不外推、不插值。

## 0. 阅读须知（口径约定）

1. **判级以读回为准，status 0x1 ≠ 方法成功。** EVM 侧终态用 `cast call stateOf` 读回（`_r3-t4-evidence-recheck-raw.txt:50-53`）；Lyquid 侧用 `deal_info` 读回（`_r3-t3-final-state-raw.txt:5`）。「status 0x1 但状态未变」的活例见 `_r2-adversarial-raw.txt:6` 与 `_r2-deploy-raw.txt:762-766`（P2 探针交易）。
2. **来源差异必须并列标注。** EVM 数据来自本轮 run-3（2026-10-30 12:04，合约 `0x976C2147…`）；Lyquid 数据来自 R2（`0xFD6F7A…`，2026-10-29 轮次）与 R3（`0x87006e…`，2026-10-30 轮次）两个**不同实例**。两实例的数据不合并、不互相替代。
3. **EVM 侧「委员会」与 Lyquid 侧「委员会」不是同一种东西**，见 §2-②。
4. 本报告中的 gasUsed 全部取自链上 receipt（EVM：`_r3-t4-evidence-recheck-raw.txt` 逐笔对拍；Lyquid：`_r3-t4-lyquid-scan-raw.txt` 链扫读取 `eth_getTransactionReceipt`）。
5. 本文不写营销话术；定性判断均附代码行或日志行。

## 1. 实验设置

### 1.1 环境（本轮实跑）

| 项 | 值 | 来源 |
|---|---|---|
| 容器 | 7 个全 Up（multi-tools / multi-node1..4 / multi-registry / multi-anvil） | `_r3-t4-precheck-raw.txt:5-12` |
| 容器工具 | forge、cast、jq、python3 齐备（rc=0） | `_r3-t4-precheck-raw.txt:14-19` |
| forge 版本 | 1.7.1（Commit 4072e487…） | `_r3-t4-precheck-raw.txt:22-25` |
| EVM 侧 RPC | 容器内 `http://anvil:8545`（宿主无端口映射） | `run-contrast.sh:12-14` |
| Lyquid RPC | 容器内 `http://node1:10087/api`；根路径 404 | `_r3-t4-lyquid-scan-raw.txt:150-152` |
| 共享性 | 两侧同一 anvil 链（同一 sequencer） | `run-contrast.sh:12-14`；`_r3-t4-lyquid-scan-raw.txt:152` |

### 1.2 EVM 侧（本次 run-3，canonical）

| 项 | 值 | 来源 |
|---|---|---|
| Escrow.sol md5 | `a0dc82822b327d38bb13b07080f85872` | `_r3-t4-md5-raw.txt` 拷出 3/3 MATCH |
| foundry.toml md5 | `640194e587e96f8a6cc90983c70e8a55` | 同上 |
| run-contrast.sh md5 | `8b0a3454e4139f65000a5ad40b928482` | 同上 |
| build | `Compiler run successful!`，EXIT_CODE=0（solc 0.8.37） | `_r3-t4-build-raw.txt:5-24` |
| 合约地址 | `0x976C214741b4657bd99DFD38a5c0E3ac5C99D903` | `_r3-t4-flows-raw.txt:22` |
| 部署交易 | `0x4e99b421a157bd7a1c15e86acb949660e5fb639edff1333fe0e5a417160c7447` @ block 384 | `_r3-t4-flows-raw.txt:22`；block 见 `_r3-t4-evidence-recheck-raw.txt:42` |
| 运行时字节码 | 8709 bytes | `_r3-t4-flows-raw.txt:22`；独立复核 `_r3-t4-evidence-recheck-raw.txt:86` |
| deployer/broker | `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266`（anvil#0） | `_r3-t4-flows-raw.txt:23` |
| buyer | `0x70997970C51812dc3A010C7d01b50e0d17dc79C8`（anvil#1） | 同上 |
| seller | `0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC`（anvil#2） | 同上 |
| committee4 | `0x90F79bf6EB2c4f870365E785982E1f101E93b906`（anvil#3） | 同上 |
| 委员会配置 | 4 成员、threshold=3（成员即上述四个地址） | `_r3-t4-gas-raw.txt:2`；读回 `_r3-t4-evidence-recheck-raw.txt:75-82` |

### 1.3 Lyquid 侧（R2 / R3 实例，历史轮次）

| 项 | 值 | 来源 |
|---|---|---|
| R2 实例 | `Lyquid-tldda6zqdhab2kdysepcqxx73uvm3sxz7wbaa` @ `0xFD6F7A6a5c21A3f503EBaE7a473639974379c351` | `_r2-final-state-raw.txt:2`；创建交易 `_r3-t4-lyquid-scan-raw.txt:156` |
| R2 创建交易 | `0xaabbe98a…abda` @ block 199，gasUsed `0x389241` = 3,707,457 | `_r3-t4-lyquid-scan-raw.txt:156,300` |
| R3 实例 | `Lyquid-ybidj3krshf4gqcjk3m3px6mooi6tg74twwaa` @ `0x87006e75a5B6bE9D1bbF61AC8Cd84f05D9140589` | `_r3-t3-final-state-raw.txt:2`；创建交易 `_r3-t4-lyquid-scan-raw.txt:157` |
| R3 创建交易 | `0xc789080c…f297` @ block 327，gasUsed `0x3aa3e1` = 3,843,041 | `_r3-t4-lyquid-scan-raw.txt:157,303` |
| R3 委员会 | 平台注册 4 个 NodeID、threshold=4 | `_r3-t3-final-state-raw.txt:10`（`current:{committee:4,threshold:4}`）；console `_r3-t3-console-raw.txt:5` |
| R3 broker | `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266`（BROKER 常量，broker 代建单） | `lyquid/src/lib.rs:208`；`_r3-t3-console-raw.txt` 的 create_deal 发送者见 `_r3-t4-lyquid-scan-raw.txt:289` |

**账户映射差异（先声明，避免误读）**：EVM 侧 `createDeal` 的 `msg.sender` 即 buyer（`Escrow.sol:130-131` 注释）；Lyquid 侧 `create_deal` 由 broker 代建（`lib.rs:214` 的 `Access::Broker`）。两侧「谁发起建单」语义不同，属于对照边界。

## 2. 四维对照

### ① 代码量（wc 口径，三列并注）

**硬约束**：本维度按 plan §2 的三列口径给出，不回退为「407 vs 2083」单口径。

| 列 | 范围 | 含测试 | 去测试 | 来源 |
|---|---|---|---|---|
| a | `experiments/evm-contrast/Escrow.sol`（单合约全部） | **407** | 407（无测试代码） | `_r3-t4-code-size-raw.txt:7` |
| b | Lyquid 合约本体六文件（core / committee_certified / committee / types / assessor / timeout） | **2083** | **1323** | `_r3-t4-code-size-raw.txt:9-14,54-56` |
| c | `lyquid/src/*.rs` 顶层合计（含 lib.rs 850 行方法层） | **2933** | **2173** | `_r3-t4-code-size-raw.txt:8-14,54-56` |

去测试口径的构成（三处 `#[cfg(test)]` 均延至文件尾，故去测试 = 起始行号 − 1）：

| 文件 | 总行 | `#[cfg(test)]` 起始行 | 测试行 |
|---|---|---|---|
| `core.rs` | 909 | 309 | 601 |
| `committee.rs` | 185 | 92 | 94 |
| `assessor.rs` | 273 | 209 | 65 |
| 合计 | — | — | **760** |

来源：`_r3-t4-code-size-raw.txt:40-42`（grep -n）、`:58-63`（派生计算）。

**口径声明（必须照录）**：计数工具 `wc -l`（含空行与注释，未做有效代码行折算；solloc/cloc 本机不可用）；含/去测试两档；含/不含 `lib.rs` 两档——`lib.rs`（850 行）是合约导出方法层/平台胶水，按 plan §2 判级口径**计入 Lyquid 合约侧**（列 c），其自述见 `lyquid/src/lib.rs:1-6`，eth 导出方法面见 `lib.rs:296/357/398/419/433/454/468/487/520/545/561`；`lyquid/src/*.rs` 为顶层 glob，**不含 `probe/` 子目录**（`probe/` 三个文件见 `_r3-t4-code-size-raw.txt:30-36`，不计入任何一档）；**Escrow.sol 无单元测试**，其行为验证的等价物是 `run-contrast.sh` 的三流（normal / timeout / adversarial）+ 负对照流程（`_r3-t4-flows-raw.txt:26-41`），非单元测试。

**运行时字节码（补充数据，非同质比较）**：Escrow 8709 bytes（`_r3-t4-flows-raw.txt:22`）；Lyquid R3 实例 16846 bytes、R2 实例 16219 bytes（`_r3-t4-evidence-recheck-raw.txt:120-123`）。Lyquid 实例字节码是平台运行时封装（含 VM 解释面），与 Escrow 的编译产物不同质，**不作等价比较**，此处仅补数据完整性。

### ② 信任假设

| 判据 | 纯 EVM Escrow（本轮 run-3） | Lyquid（R3 实例） |
|---|---|---|
| 委员会来源 | 合约内的**地址表**：`committeeMembers` / `isCommitteeMember` / `threshold` 为合约存储（`Escrow.sol:81-83`），无任何身份注册机制 | **平台注册的 4 个 NodeID**：`e2_configure` 把 4 个 NodeID 与 threshold=4 写入 oracle staging（`_r3-t3-console-raw.txt:5`；`_r3-t3-final-state-raw.txt:10` 读回 `committee:4,threshold:4`） |
| 谁能配置委员会 | **仅 deployer**：`require(msg.sender == deployer, "not deployer")`（`Escrow.sol:108`） | `e2_configure` 的 eth 守卫 = creator（部署钥），另有 Lyquid 层 `committee_config` 的 Broker 门（`lib.rs:223`）；本实例委员会由部署钥配置（`_r3-t4-lyquid-scan-raw.txt:285` block 330） |
| 成员是「谁」 | **4 个普通 EOA 地址**，本轮分别是 deployer/broker、buyer、seller 与一个额外账户（`_r3-t4-flows-raw.txt:23`；读回 `_r3-t4-evidence-recheck-raw.txt:77-80`）。**其中包含本笔交易的买卖双方本人**——委员会未引入任何交易外的第三方 | 4 个由平台管理的节点 NodeID（`_r3-t3-console-raw.txt:31-35` 逐个映射到 `Node-…` 串） |
| 阈值 | 3-of-4（`_r3-t4-gas-raw.txt:2`；读回 threshold=3，`_r3-t4-evidence-recheck-raw.txt:76`） | 4-of-4（threshold=4，`_r3-t3-final-state-raw.txt:10`） |
| 裁决来源的可验证性 | 合约内**自建 ECRECOVER**：`applyVerdict` 自己按 `ecrecover` 恢复签名者并查 `isCommitteeMember`（`Escrow.sol:270-272`），签名对象是合约自己算出的 digest | 平台认证回调：`committee_verdict_certified` 读取平台已验证的 `ctx.cert.signers`（`committee_certified.rs:355-374`），再经 `core::validate_cert` 四查后落地；eth 直调路径 `apply_committee_verdict` 另有「Committee 地址门、无签名校验」的弱路径，源码自述为 TODO(W4)（`lib.rs:222`） |
| 托管资金 | 合约自身持有（`fund` 为 payable，`Escrow.sol:176`） | 平台 ledger：`balance_of(alice)` 等由实例状态维护（`_r3-t3-final-state-raw.txt:6-8`） |
| 超时域 | `block.timestamp`（`Escrow.sol:204,227`），本轮用 `evm_increaseTime 30` + `evm_mine` 推进（`run-contrast.sh:118-119`；`_r3-t4-flows-raw.txt:30-31`） | slot（`timeout_slots` / `deadline_slot`，`_r3-t3-final-state-raw.txt:5`） |

**如实说明**：EVM 侧的「委员会」在本轮配置下不构成独立信任锚——成员是 deployer 可任意指定的地址表，且本轮包含买卖双方本人；合约不验证任何链下证据，只验证「这些地址对合约自算的 digest 签了名」。Lyquid 侧的 committee 是平台注册的节点集合，阈值 4/4，裁决落地前有平台证书校验；但 eth 直调路径（R2 轮次使用）只做地址门、不验签名（`lib.rs:222`），两条路径的强度不同，本报告并列给出，不合并。

### ③ 裁决不可篡改性

| 判据 | 纯 EVM Escrow | Lyquid |
|---|---|---|
| 签名绑定对象 | `digest = keccak256(abi.encode(dealId, verdictCode, evidenceRoot(dealId)))`（`Escrow.sol:304-306`）——绑定 deal ID、裁决码与**当前全量证据**的折叠根（`:310-318`） | 平台证书 + `cert.signers`（`Vec<SignerID>`，`committee_certified.rs:356`）；落地前 `core::validate_cert` 检查「全员 ∈ committee_members + 去重 + \|signers\| ≥ threshold + evidence_root 匹配」（`committee_certified.rs:341-352` 注释） |
| 重放/跨单复用 | **实证拒绝**：把 deal-3 的 3 个签名重放到 deal-4，`rc=1`，revert 原因 `non-member signer`（`_r3-t4-flows-raw.txt:40-41`；独立复跑 `_r3-t4-evidence-recheck-raw.txt:100-104`），deal-4 读回仍为 Disputed（`:53`；重放后读回 `:102`） | 无数据（本轮未做 Lyquid 侧跨单重放实验；该项不在 T4 范围） |
| 裁决后状态 | deal-1 Settled(5) / deal-2 Refunded(6) / deal-3 Refunded(6) / deal-4 Disputed(4)，全部 `cast call` 读回（`_r3-t4-evidence-recheck-raw.txt:50-53`） | R3 deal-1 Refunded（`deal_info` 读回，`_r3-t3-final-state-raw.txt:5`；console `_r3-t3-console-raw.txt:38`） |
| 「status 成功 ≠ 方法成功」的实证 | 负对照本身即一例：交易被拒时 `cast send` 返回非零（估计 gas 阶段 revert），未产生 status=1 的假成功（`_r3-t4-flows-raw.txt:40`） | **活例**：R2 attempt-1 中 `apply_committee_verdict` 交易 status `0x1`，但 deal-4 停留 Disputed（平台吞 Err，`_r2-adversarial-raw.txt:6`）；另一例 P2 探针 `0xae6698c7…` status `0x1` 但方法未生效（`_r2-deploy-raw.txt:762-766`；本轮链扫复核该 tx 见 `_r3-t4-lyquid-scan-raw.txt:161`） |
| 违约累计视图 | `misconduct(seller)` 为 public getter（`Escrow.sol:86`），NotFulfilled 不加罚：读回 0（`_r3-t4-evidence-recheck-raw.txt:83`；`_r3-t4-flows-raw.txt:38`） | 无 getter（`_r3-t3-final-state-raw.txt:15`：`MISCONDUCT VIEW: no getter (lib.rs:781 prints only)`），仅 console 行 `apply_verdict: … misconduct=[]`（`_r3-t3-console-raw.txt:36`） |

**如实说明**：两侧都能证明「同一签名集不能跨单复用」这一性质吗？EVM 侧本轮有实证（负对照）；Lyquid 侧没有做同型实验，只有代码路径（`core::validate_cert` 的 evidence_root 匹配）作为机制证据。报告不把「代码里有校验」写成「已实测」。

### ④ 开销

#### ④-1 EVM 侧逐笔（run-3，共 20 笔 = deploy + 19 操作）

| # | 操作 | tx（前 12 位） | gasUsed (hex) | gasUsed (dec) |
|---|---|---|---|---|
| 1 | deploy（forge create） | `0x4e99b421a1…` | 0x1d8a88 | 1,936,008 |
| 2 | committeeConfig(4,3) | `0x3352179486…` | 0x3e436 | 255,030 |
| 3 | normal:createDeal | `0x58cee1bda6…` | 0x37562 | 226,658 |
| 4 | normal:fund | `0x4925cd7091…` | 0x7fc9 | 32,713 |
| 5 | normal:notarize(acceptance) | `0x3e731cf7cd…` | 0x21b58 | 138,072 |
| 6 | normal:submitDeliverable | `0x590d86334e…` | 0xd303 | 54,019 |
| 7 | normal:complete | `0x1f14770174…` | 0xe2fe | 58,110 |
| 8 | timeout:createDeal | `0x9bed7ca02a…` | 0x33296 | 209,558 |
| 9 | timeout:fund | `0x2effa65b65…` | 0x7fc9 | 32,713 |
| 10 | timeout:claimTimeout | `0x9db8927eff…` | 0xa6f3 | 42,739 |
| 11 | adv:createDeal | `0x04392b676d…` | 0x33296 | 209,558 |
| 12 | adv:fund | `0xfe89a16cfa…` | 0x7fc9 | 32,713 |
| 13 | adv:notarize(acceptance) | `0x1f54df84e5…` | 0x21b58 | 138,072 |
| 14 | adv:submitDeliverable(forged) | `0xee3804d440…` | 0xd303 | 54,019 |
| 15 | adv:notarize(dispute) | `0xe610059260…` | 0x1d880 | 120,960 |
| 16 | adv:openDispute | `0xf386da8f57…` | 0xcfaa | 53,162 |
| 17 | adv:applyVerdict(3-of-4) | `0x13d646071e…` | 0x16d5e | 93,534 |
| 18 | adv2:createDeal | `0xb8797cd774…` | 0x33296 | 209,558 |
| 19 | adv2:fund | `0x131e778e4f…` | 0x7fc9 | 32,713 |
| 20 | adv2:openDispute | `0xedd1a31938…` | 0xcf04 | 52,996 |
| — | **合计** | 20 笔 | — | **3,982,905** |

来源：`_r3-t4-gas-raw.txt:1-20`（逐行 hex 原值）；逐笔 receipt 对拍 20/20 一致（`_r3-t4-evidence-recheck-raw.txt:40`）；decimal 合计由该 20 行 hex 换算（同文件 `:41`）。

分流量合计（同源换算）：normal 5 笔 509,572；timeout 3 笔 285,010；adversarial 7 笔 702,018；负对照（adv2）3 笔 295,267。
注：首笔 `createDeal` 为 226,658，其余两笔为 209,558（同一调用、同一参数形状；差值 17,100 未进一步归因，不做机制推测）。

#### ④-2 Lyquid R3 侧逐笔（共 14 笔 = 创建 + 13 调用）

| block | 方法 | gasUsed (hex) | gasUsed (dec) | tx（前 12 位） |
|---|---|---|---|---|
| 327 | **创建交易**（to=null） | 0x3aa3e1 | **3,843,041** | `0xc789080c0e…` |
| 329 | `committee_config(string[],uint32)` | 0xb576 | 46,454 | `0x639a31306f…` |
| 330 | `e2_configure(bytes32[],uint16)` | 0xa26c | 41,580 | `0x6da2c2a382…` |
| 331 | 平台系统调用（selector 未识别，见注） | 0xe459 | 58,457 | `0xc406f0b56f…` |
| 332 | 平台系统调用（未识别） | 0xd83e | 55,358 | `0x52ebf5bd52…` |
| 333 | `faucet(string,uint128)` | 0x923e | 37,438 | `0x5a22bd8dfc…` |
| 334 | `create_deal(…)` | 0xbb24 | 47,908 | `0xa352794726…` |
| 335 | `notarize(…)` | 0xaca1 | 44,193 | `0x5bd6187952…` |
| 336 | `notarize(…)` | 0xaca1 | 44,193 | `0xda29bd4761…` |
| 337 | `fund(string)` | 0x8cae | 36,014 | `0x26540383b2…` |
| 338 | `notarize(…)` | 0xaca1 | 44,193 | `0xa9e6d7fc9e…` |
| 339 | `open_dispute(string,string)` | 0x97e3 | 38,883 | `0xbcf15e77f5…` |
| 340 | `e2_arm(string)` | 0x9540 | 38,208 | `0x3739bfe923…` |
| 341 | 认证回调（未识别 selector，见注） | 0xcd09 | 52,489 | `0x7a9f9b4fe2…` |
| — | **合计（含创建）** | — | **4,428,409** | — |

来源：`_r3-t4-lyquid-scan-raw.txt:284-296`（逐行）；汇总 `:303`。

注（未识别 selector，如实登记）：`0xcd9cc3c8` = `e2_configure(bytes32[],uint16)`、`0x8b7acf91` = `e2_arm(string)` 已用容器内 `cast sig` 实算确认（`_r3-t4-lyquid-scan-raw.txt:388-389`）；`0xeddfc069`（block 331/332/341）与 R2 的 `0x9771a522`(319)、`0x0d8712ee`(323) 在仓库源码与既有 selector 表中均无法对应，标为未识别、不猜测名称（`:383-387`）。其中 block 341 与 console「certified call submitted」同回合（`_r3-t3-console-raw.txt:30-31`）。

#### ④-3 Lyquid R2 侧（不同实例，仅作并列参考）

| 项 | 值 | 来源 |
|---|---|---|
| 创建交易 | block 199，3,707,457 gas | `_r3-t4-lyquid-scan-raw.txt:156,300` |
| 调用交易 | 123 笔，gas 合计 5,145,171 | `_r3-t4-lyquid-scan-raw.txt:299`（合计 8,852,628 含创建，同处） |
| 方法级（中位） | create_deal 47,930 / fund 35,925 / notarize 44,215 / submit_deliverable 38,871 / open_dispute 38,883 / apply_committee_verdict 43,061 / claim_timeout 35,996 / committee_config 42,775 | 由 `_r3-t4-lyquid-scan-raw.txt` 逐行数据算得（样本见 `:259,267,275`） |
| 部署→最后实例交易块跨度 | 199 → 326 = **127 块** | `_r3-t4-lyquid-scan-raw.txt:301` |
| 终态参考读数点 | block 315（`deal_info` 快照，非链上终点） | `_r2-final-state-raw.txt:4` |

#### ④-4 部署环节直接对比（同链、同 anvil#0 签名者）

| 项 | EVM Escrow（run-3） | Lyquid R3 | Lyquid R2 |
|---|---|---|---|
| 创建交易 | `0x4e99b421…c7447`（to=null→`0x976C…D903`） | `0xc789080c…f297`（to=null→`0x8700…0589`） | `0xaabbe98a…abda`（to=null→`0xFD6F…c351`） |
| block | 384 | 327 | 199 |
| gasUsed | **1,936,008** | **3,843,041** | **3,707,457** |
| 来源 | `_r3-t4-gas-raw.txt:1`；block `_r3-t4-evidence-recheck-raw.txt:42` | `_r3-t4-lyquid-scan-raw.txt:157,303` | `_r3-t4-lyquid-scan-raw.txt:156,300` |

口径说明：两者同为 anvil#0 签名、同链、同一 to=null 创建交易形态（receipt.contractAddress = 实例地址），故部署 gas 可直接对比。差异的外部因素：Lyquid 的 shaker deploy 还包含 OCI 镜像/registry 环节（`_r3-t3-deploy-raw.txt:74-89`），该环节**无链上对应物**，不进入本表。

#### ④-5 交易数与块跨度

| 项 | EVM（run-3） | Lyquid R3 | Lyquid R2 |
|---|---|---|---|
| 实例相关交易数 | 20（deploy+19） | 14（创建+13） | 124（创建+123） |
| 块跨度（部署块→最后实例交易块） | 384→404 = **20 块** | 327→341 = **14 块** | 199→326 = **127 块** |
| 来源 | `_r3-t4-evidence-recheck-raw.txt:42` | `_r3-t4-lyquid-scan-raw.txt:304` | `:301` |

注意：EVM 侧一轮实验含 3 条完整业务流 + 1 次负对照（`_r3-t4-flows-raw.txt:26-41`）；Lyquid R3 只含 1 条业务流（deal-1）+ 认证回合。**两者工作量不同，交易数与总量不构成同工作量对比**，本表只陈述事实。

#### ④-6 认证回合的消息开销（Lyquid 侧独有）

| 项 | 数量 | 来源 |
|---|---|---|
| 链上回调交易（认证落地） | 1 笔（block 341，52,489 gas） | `_r3-t4-lyquid-scan-raw.txt:296` |
| `e2_propose` 日志 | 1 行 | `_r3-t3-console-raw.txt:19` |
| `e2_aggregate` 日志 | 10 行（两轮，每轮 4 输入 + 1 agreed） | `_r3-t3-console-raw.txt:20-29` |
| `e2_aggregate: agreed` | 2 次（同一裁决被聚合两次） | `_r3-t3-console-raw.txt:24,29` |
| `committee_verdict_certified` 执行日志 | 6 行（RAW signers + 4 次 signer 映射 + applied） | `_r3-t3-console-raw.txt:31,32-35,37` |
| `e2_arm` / `e2_configure` 链上交易 | 1 + 1 笔 | `_r3-t4-lyquid-scan-raw.txt:285,295` |

EVM 侧对应位置：`applyVerdict` 为**单笔交易传入 3 个签名**（`_r3-t4-gas-raw.txt:17`），无链下多轮消息；签名由调用方在链下对 digest 签好后一次性提交（`run-contrast.sh:142-147`）。

#### ④-7 数据缺口（如实列出）

| 缺口 | 原因 |
|---|---|
| Lyquid 侧 calldata 字节数 | 本轮未采集该指标（不在 T4.6/T4.5 范围）；EVM 侧同为无数据 |
| Lyquid 侧跨单签名重放实验 | 未做（见 §2-③）；仅有代码路径证据 |
| Lyquid 实例「业务逻辑」字节码尺寸 | 实例字节码为平台运行时封装（16846/16219），无法与 Escrow 的 8709 同质比较（`_r3-t4-evidence-recheck-raw.txt:120-123`） |
| 两侧相同工作量的端到端 gas 对比 | 两侧本轮业务流内容不同（EVM 三流+负对照 vs Lyquid 单流+认证），且结算单位不同（gasUsed 可比，但 block.timestamp 与 slot 的时间语义不同）；报告只做逐操作对比 |
| R2 与 R3 合并统计 | 两实例不同、轮次不同，按要求并列不合并 |
| 三个平台 selector 的方法名 | 仓库源码与既有 selector 表均无对应，标为未识别（`_r3-t4-lyquid-scan-raw.txt:383-387`） |

## 3. 链上证据引用清单

| 项 | 值 | 来源 |
|---|---|---|
| EVM 合约地址 | `0x976C214741b4657bd99DFD38a5c0E3ac5C99D903` | `_r3-t4-flows-raw.txt:22` |
| EVM 部署 tx | `0x4e99b421a157bd7a1c15e86acb949660e5fb639edff1333fe0e5a417160c7447` | `_r3-t4-gas-raw.txt:1` |
| EVM 正常流终态 | deal-1 Settled(5) | `_r3-t4-evidence-recheck-raw.txt:50`；`_r3-t4-flows-raw.txt:28` |
| EVM 超时流终态 | deal-2 Refunded(6) | `_r3-t4-evidence-recheck-raw.txt:51`；`_r3-t4-flows-raw.txt:32` |
| EVM 争议流终态 | deal-3 Refunded(6)，misconduct(seller)=0 | `_r3-t4-evidence-recheck-raw.txt:52,83`；`_r3-t4-flows-raw.txt:37-38` |
| EVM 负对照 | deal-4 Disputed(4)；重放 rc=1 `non-member signer` | `_r3-t4-evidence-recheck-raw.txt:53,100-104`；`_r3-t4-flows-raw.txt:40-41` |
| EVM 3-of-4 签名 | buyer / seller / committee4 三签（原文入档） | `_r3-t4-flows-raw.txt:36` |
| EVM verdict digest 绑定 | `keccak(abi.encode(dealId,verdictCode,evidenceRoot))` | `Escrow.sol:304-306` |
| R2 实例 + 创建 tx | `0xFD6F7A…c351` ← `0xaabbe98a…abda` @199 | `_r3-t4-lyquid-scan-raw.txt:156` |
| R3 实例 + 创建 tx | `0x87006e…0589` ← `0xc789080c…f297` @327 | `_r3-t4-lyquid-scan-raw.txt:157` |
| R2 P2 探针（status 1 未生效） | `0xae6698c7…c1c83b` @201，gas 37,748 | `_r3-t4-lyquid-scan-raw.txt:161`；`_r2-deploy-raw.txt:762-766` |
| R2 attempt-1（status 1 但 Disputed） | `apply_committee_verdict` 被平台吞 Err | `_r2-adversarial-raw.txt:6` |
| R3 faucet 单笔 | `0x5a22bd8d…4352` @333 | `_r3-t4-lyquid-scan-raw.txt:288`；`_r3-t3-final-state-raw.txt:25` |
| R3 认证回合 | propose→2×aggregate(4 inputs)→certified call→apply_verdict | `_r3-t3-console-raw.txt:19-37` |
| R3 终态读回 | deal-1 Refunded，balances alice=10000/bob=0/broker=0 | `_r3-t3-final-state-raw.txt:5-8` |
| R2 keeper 双笔 gas | faucet 0x923c @213 / claim_timeout 0x8c9c @214 | `_r3-t4-lyquid-scan-raw.txt:173-174`；`_r2-keeper-loop-raw.txt:27-28` |
| 代码量原始 | wc 三列 + cfg(test) 行 | `_r3-t4-code-size-raw.txt:7,40-42,42-56` |
| 篡改面：脚本 md5 | 3/3 一致（拷出）+ 2/2 一致（拷回） | `_r3-t4-md5-raw.txt`（GT4-b PASS） |

## 4. 结论（如实）

1. **EVM escrow 没有多节点委员会认证。** 它的「委员会」是合约内一张由 deployer 可随时覆盖配置的地址表（`Escrow.sol:107-125`，本轮 4 个成员、threshold=3），k-of-n 由合约自己 `ecrecover` 自证（`Escrow.sol:270-279`），没有任何交易外身份层或平台认证；本轮该地址表还包含买卖双方本人（`_r3-t4-flows-raw.txt:23`）。因此在这个配置下，裁决的信任来源仍是「买方+卖方+一个附加账户」这组地址，而不是独立的多方认证。
2. **EVM 侧的可篡改性防护是真实生效的，但范围有限。** 负对照实证了「同一签名集不能跨 deal 复用」（`_r3-t4-flows-raw.txt:40-41`），因为签名对象绑定了 dealId、裁决码与证据根（`Escrow.sol:304-306`）。该防护只约束「签名不能挪用」，不约束「谁有资格被写进委员会」。
3. **Lyquid 的四节点认证是额外的信任层，代价可量化。** 收益：委员会由平台注册的 4 个 NodeID 构成、threshold 4/4，认证回调读平台已校验的 `cert.signers` 并做 `validate_cert` 四查（`committee_certified.rs:341-374`），裁决落链前多一道与地址表无关的身份校验。代价：部署 gas 更高（3,843,041 vs EVM 1,936,008，约 1.98×；R2 为 3,707,457）、认证回合需要额外汇总消息（本轮 propose 1 + aggregate 10 行 + 认证回调 1 笔，`_r3-t3-console-raw.txt:19-37`）、且强依赖平台通道的可用性与语义（R2 已暴露 `status 0x1` 但方法未生效的失败模式，`_r2-adversarial-raw.txt:6`）。
4. **单笔操作的 gas 对比没有单向结论。** EVM 侧 `createDeal`（226,658/209,558）、`notarize`（138,072）、`openDispute`（53,162）、`applyVerdict`（93,534）高于 Lyquid 对应方法（create_deal 47,908 / notarize 44,193 / open_dispute 38,883 / apply_committee_verdict 43,073）；`fund` 反而 EVM 更低（32,713 vs 36,014）。部署环节则是 EVM 更低。两侧结算单位与业务流内容不同，本报告不做单一「谁更便宜」的总量结论。
5. **代码量的对比必须带口径。** 单看合约本行数，Escrow.sol 407 行 vs Lyquid 合约本体 2083 行（含测试）/1323 行（去测试）；若按 plan §2 把 `lib.rs` 方法层计入合约侧，Lyquid 侧为 2933/2173 行。两侧测试策略不同（Escrow 无单元测试、用三流+负对照验证），行数差不能直接读成「复杂度差」。
6. **共同前提**：两侧都跑在同一个 anvil 链上，EVM 实验的 `evm_increaseTime` 会推进共享时间源（plan §5-R4 已登记）。本轮该操作只影响 EVM 合约的 deadline 判定，未对 Lyquid 实例做任何依赖未来 slot 的操作；Lyquid 侧本轮只读。
