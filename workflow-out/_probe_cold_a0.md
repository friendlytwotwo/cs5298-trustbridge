# R3 方案：E2 四节点委员会演示（路线②）+ 纯 EVM 对照实验 + B3 用户测试备料

> 规划人：规划师（2026-10-30）。执行基线 = 当前工作树（含未提交 R1+R2 改动，**严禁回退**；分组见 `workflow-out/_commit-plan.md` §2 C1–C4 + §5 C5–C8，均已获代码审查通过）。
> 阶段依据：`../FinalProject_阶段重排_2026-10-27.md` §1 R3（窗口 11/6–11/12）。
> R2 方案已备份为 `workflow-out/_plan-prev-r2-backup.md`（本文件按 R3 重建）。
> 实现说明纪律（任务陈述）：`implementation.md` 继续分节「已审（R1/R2）/新增（R3）」，审查聚焦本轮新增。
> **诚实红线（任务陈述原文）**：若 oracle 路线碰到平台硬限制，允许降级方案但必须如实登记限制与降级理由，**不得伪造"四节点签署"表象**。

> **终裁定稿冻结条款（2026-10-30，六条全 accept；本节起为定稿与编码基线——后续轮次不得削弱，任何新增偏离须在 implementation.md §5 偏离表显式登记；正文各节带「仲裁 R1#x/R2#x」标注的条款全部保留）**：
> 1. **e2_configure 唯一通道** = `docker_exec_cast` cast send（与 S2 probe_configure 完全同形：`cast send $CTR "e2_configure(bytes32[],uint16)" "[4×0x…]" <th> --private-key <anvil#0> --rpc-url http://node1:10087/api`）；rpc.py 编码器零扩展、`_ABI` 不增该行；:139-142 覆盖注记同步「仍无 bytes32[]（e2_configure 走 cast 通道）」。如编码期确需 NodeClient 直发，**唯一许可路径** = 先扩 `_enc_value`/`_is_dynamic` 支持 bytes32/bytes32[] 且与容器内 `cast calldata` 逐字节对照通过（R2 教训 implementation.md §5-1）——**默认禁止**（§0-#3/§3.2-A）。
> 2. **--instance 参数**（committee 流必填校验 + 缺省自 deploy 实录回填脚本常量，`_r1-deploy-raw.txt:423-424` 形态）、**端口梯常量** {10087,11087,12087,13087}→node1..4、rpc.py `get_node_ids` 四端点轮询；**console 取证源=node1、必须用实例名**；四端点定位=**观测/诊断面**（与条款 5 联动），不作主路径触发（§0-#4/§3.4-4）。
> 3. **E2 门禁台账**（committee_certified.rs 模块头 7 方法×面×实际门×是否触资金 + lib.rs:166-170 矩阵审计面注释加一行指向）+ **ACCESS_MATRIX 本体零增删**（保持「每行一个 require 地址门」单点语义）；implementation.md R3 段描述 `committee_verdict_certified` 必须用「**cert 门控的资金路径**（共享 helper → apply_payout lib.rs:718 → credit lib.rs:694 真实结算）」，**禁用 probe 类「SPIKE 例外/非生产面」措辞**（§0-#2/§3.2-E/H/§0-#13）。
> 4. **e2_arm = `#[method::network(export = eth, eth_guard = creator)]` 写 network 域 `e2_armed_deal`**，NodeClient `_send` 单发全节点生效；arm 后读回断言口径 = **NodeClient call("e2_net_config()") 解码 JSON，断言 armed_deal == deal_id**（console 回显行仅 transcript 佐证）；**不得回退 instance 域 cast call 形态**；run_round 维持 **cast call**（严禁 cast send 对内部异步提交类方法，S2 §3/§4 实证）（§3.2-B/§3.2-G/§3.6-5/R4）。
> 5. **avg_num = 编码期常量**（首跑 4；fallback 改 1 须重新 cp/deploy）；**仅 node1 单次触发**（propose 经 UPC 广播自带全节点提案，protocol.rs:312/:316；**禁多次触发**——首回合已把 deal 推离 Disputed，core.rs:199 门必败）；T1 只证 signers 聚合（th2/th4）+通道面；**L2 判据 = T3 首跑 console 聚合行 inputs=4+signers=4**；fallback = avg_num=1 + 重新 deploy + L1 口径取证 + 显式降级登记；L0 = 三段式诚实报告，**绝不以单签冒充四节点**（本文件头部诚实红线）（§3.2-F/§3.4/G3）。
> 6. **TARGET = `docker exec multi-tools shaker to-hex <实例名>`**（T1 = R2 实例 `Lyquid-tldda6zq…`；T3 = `--instance` 传入值），断言**非零且 ≠ 实例合约地址（--contract）**，推导命令与输出值入 `_r3-t1-target-raw.txt` 与 `_r3-t3-*` 日志，并纳入 demo env 断言（§3.6-1/§3.6-3/T1/G3）。

---

## 0. 受影响文件清单（供审查员核对，共 15 项）

| # | 文件 | 动作 | 持久性 |
|---|---|---|---|
| 1 | `lyquid/src/lib.rs` | **三处**：① `state!` 块增 `network oracle cert_verdict;`（E2 认证 topic，先例 cert_probe lib.rs:97；probe/mod.rs:13-16 已证子模块不能自带 state!）+ **network 字段** `e2_armed_deal: String`（§3.2-B arming 用；**仲裁 R2#1-a**：network 域=共识持久+全节点可见，arm 单次发送即全体生效，无需每节点）；② 模块声明 `pub mod committee_certified;` + 模块头/通道注记块增 R3 段（:37-44 区域续写）；③ **行为保持重构**：从 `apply_committee_verdict`（:484-542）体内提取私有 helper `apply_cert_and_payout(state, deal_id, cert_wire)`（成员/阈值读取→evidence 读取→into_domain→misconduct 镜像桥接→core::apply_verdict→写回→apply_payout→println 视图，逐字搬移），`apply_committee_verdict` 保留扁平 wire + `require(Access::Committee)` + caller∈signers 检查后调 helper——**wire 形态/权限门/裁决语义零变化**（行为保持判据见 §6-G3） | **持久** |
| 2 | `lyquid/src/committee_certified.rs` | **新建**（~250 行，顶层壳模块；不入 `probe/`——该目录注记明言 W1-B1 SPIKE、W2 移除，E2 是演示级准生产接线）。七方法（完整设计见 §3.2）：`e2_configure`、`e2_arm`、`propose`/`aggregate`（**字面名**，s2_oracle.rs:8-13 硬约束）、`committee_verdict_certified`（认证回调）、`e2_run_verdict_round`、`e2_net_config`。**不走 ACCESS_MATRIX 地址门矩阵，但绝非 probe 类 SPIKE 例外（仲裁 R1#3）**：probe 网络方法不入矩阵属零资金+W2 移除的例外（probe/mod.rs:17-18），**本模块是 cert 门控的资金路径**——`committee_verdict_certified` 经共享 helper → `apply_payout`（lib.rs:718，内经 `credit` lib.rs:694）真实结算，§3.5 主场景即全额退款；故**自带门禁台账**：模块头 E2 门禁表（§3.2-H：7 方法 × 面 × 实际门 × 是否触资金），lib.rs:166-170 矩阵审计面注释加一行指向该表（矩阵本身零增删，保持「每行一个 require 地址门」的单点语义） | **持久** |
| 3 | `agents/common/rpc.py` | `get_node_ids()`（宿主 curl ×4 端口 GetNodeInfo，w1b1-topology.md:159 形态 + S2 §1 b32 换算段移植）；`_ABI` 增 **3 行**（e2_arm(string) / e2_run_verdict_round()（返回 bool）/ **e2_net_config()（返回类型冻结为 string）**——**不含 e2_configure**，selector 容器内 `cast sig` 实取后冻结，R1 T3 纪律先例 _commit-plan.md §2-C2；NodeClient 对 e2_net_config 走既有 call 通道，`_decode_ret` 已支持 string，先例 deal_info lib.rs:567 / evidence_entries_json lib.rs:584）+ 对应 NodeClient 包装；**e2_configure 走 cast 通道（仲裁 R1#1 选 B）**：`bytes32`/`bytes32[]` 不在编码器支持集（rpc.py:140-142 明示 string/uint*/bool/string[]；`_enc_value` 对其余抛 `unsupported ABI type`、`_is_dynamic` 仅识 string/string[]——本轮实读核实），demo 经 `docker_exec_cast()` 以 `cast send $CTR "e2_configure(bytes32[],uint16)" "[<4×0x…>]" <th> --private-key <anvil#0> --rpc-url http://node1:10087/api` 调用（**S2 probe_configure 同形实证先例**，w1b1-s2-oracle.md §2:27-30 status 1 + console 确认 staged）；**编码器零扩展**（R2 教训：编码器改动曾致链上垃圾串，implementation.md §5-1，能不动则不动）；**编码期如确需 NodeClient 直发 e2_configure：默认禁止，唯一许可路径 = 先扩 `_enc_value`/`_is_dynamic` 支持 bytes32/bytes32[] 且与容器内 `cast calldata` 逐字节对照通过（终裁冻结条款 1）**；`docker_exec_cast()` 宿主子进程助手承担 advance/finalize/e2_configure/console（§3.6）；:139-142 编解码器覆盖注记同步「仍无 bytes32[]（e2_configure 走 cast 通道）」；排除注记增 R3 口径 | **持久** |
| 4 | `scripts/demo.py` | 新增 `flow_committee`（**node-only**：sim 调用即明确报错退出；`--flow` choices 增 "committee"；**`--flow all` 序列与全部 sim 代码路径零改动**——G2 逐字 diff 门的硬前提）。**四端点机制=观测/诊断面（仲裁 R2#2 后降级：propose 经 UPC 广播（protocol.rs:312/:316），node1 单次触发即得全节点提案——主路径无需四端点触发）**：端口梯常量 {10087,11087,12087,13087}→node1..4（与 `get_node_ids()` 轮询共用同一张表）；T3 首跑 inputs<4 时用作逐节点排查诊断（NodeClient×4 各建[构造=base_url+contract，rpc.py:245]或 docker_exec_cast 对容器内 nodeN:10087；宿主 eth_call 直连 node2-4 未证，诊断前先试通——S2 仅实证容器内 node2/3 可读，w1b1-s2-oracle.md §3）。**`--instance Lyquid-…` 可选参数**（committee 流必填校验；缺省自 T3 deploy 实录回填为脚本常量——deploy 日志输出实例名，`_r1-deploy-raw.txt:423-424` 先例 `created Lyquid-ffy2ydso… => 0xF8e3…`；shaker console 必须用实例名，implementation.md:204 命令示例）；**console 取证源定为 node1**（部署 endpoint 即 ws://node1:10087/ws，S2 全程 node1 先例）。步骤见 §3.6 | **持久** |
| 5 | `experiments/evm-contrast/Escrow.sol` | **新建**（~200-260 行，功能面对照表见 §4.2：正常流+超时流+争议/委员会 k-of-n ECRECOVER 裁决最小对照） | **持久** |
| 6 | `experiments/evm-contrast/foundry.toml` | **新建**（forge 1.7.1 已实证容器内可用，§2-实证 1） | **持久** |
| 7 | `experiments/evm-contrast/run-contrast.sh` | **新建**（容器内执行：build→deploy→三流→gas/代码量采集 dump；`MSYS_NO_PATHCONV=1 docker cp` 进 /tmp/tb-evm，纪律同 lyquid 通道） | **持久** |
| 8 | `workflow-out/w1b2-r3-e2-committee.md` | **新建**：目标 A 证据（T1 平台探针梯子结论表 + T3 四节点签署实录：配置/激活/裁决/console signers 明细/读回勾稽/降级登记段[如有]） | 交付物 |
| 9 | `workflow-out/w1b2-r3-evm-contrast.md` | **新建**：目标 B 对照报告（四维表格+数据+双方链上证据引用，见 §4.3） | 交付物 |
| 10 | `workflow-out/_r3-*.txt` | **新建**：原始日志（预计 14–19 个，命名见 §6 T 阶梯，含 TARGET 推导 2 份（T1/T3）与 node2-4 通道取证 1 份；fallback 发生时另增 deploy/console 第二套） | 交付物 |
| 11 | `docs/b3-user-test/`（3 文件：操作手册.md / 演示脚本.md / 反馈收集表.md） | **新建**：目标 C 备料（见 §5；真实测试由用户线下安排，文档须自足——组外用户无仓库上下文可照跑） | 交付物 |
| 12 | `workflow-out/_commit-plan.md` | **增补** R3 主题分组（建议序列：R3 代码 / experiments+B3 文档 / 证据+文档收尾；**不执行 git commit**，先例 §5） | 交付物 |
| 13 | `workflow-out/implementation.md` | **增量更新**：门禁总表（R3 口径）+「R1/R2 已审 / R3 新增」分节 + 偏离 + 未尽清单（含降级登记[如有]）。**措辞纪律（仲裁 R1#3）**：R3 段描述 `committee_verdict_certified` 必须用「**cert 门控的资金路径**（经共享 helper → apply_payout lib.rs:718 → credit lib.rs:694 真实结算）」，**不得类推 probe 的「SPIKE 例外/非生产面」措辞**（probe 零资金且 W2 移除，本模块触资金）；登记 E2 门禁台账位置（committee_certified.rs 模块头表 + lib.rs 矩阵注释指向行）；**并登记 e2_net_config 的签名与返回类型（`-> LyquidResult<String>`、`_ABI` 返回面=string）——属新增 R3 面、非偏离**（e2_net_config 本就是方案指定的 arm 读回面，冷读仲裁修订 1-5） | 交付物 |
| 14 | `workflow-out/plan.md` | 本方案（旧案备份 `_plan-prev-r2-backup.md`） | 交付物 |
| 15 | `workflow-out/_pre-task-snapshot-r3.patch` | **新建**：T0 工作树快照（`git diff` 全量，事故恢复凭据；先例 R1/R2 同名件） | 自保 artifact |

**不改（冻结面/零触碰面）**：`lyquid/src/types.rs`、`core.rs`、`committee.rs`、`assessor.rs`（壳 40/40 挂载面 = types/core/committee/assessor，R1 方案 D8 口径；四文件相对 `_r2-t0-frozen-baseline.txt` 的 md5 必须全 OK——G0 复核 + G6 复跑）；`lyquid/Cargo.toml`（新模块只依赖 probe 已用的同一批 crate 面：lyquid prelude / lyquor_api / lyquor_primitives，s2_oracle.rs:29-31 先例，零新依赖）；`agents/alice.py`/`bob.py`/`broker.py`/`llm.py`/`protocol.py`；`scripts/keeper.py`（E2 不涉 keeper）；`scripts/deploy.sh`/`devnet-up.sh`；`README.md`（R3 收尾若需状态行更新，作为可选偏离项单独登记后再动，默认不动）；`../workflow-out/verify_core/`（壳只读复跑）。`--flow all` 与 sim 全路径（demo.py）零改动。

---

## 1. 已采信前提（任务陈述 + R1/R2 存档，规划不重证）

- **P1 部署通道**（任务陈述 + R2 方案 P1）：宿主 `MSYS_NO_PATHCONV=1 docker cp` → `multi-tools:/tmp/tb-lyquid` → md5 勾稽 → 容器内 `shaker deploy -r http://registry:8000/lyquids --endpoint ws://node1:10087/ws --private-key <anvil#0> Cargo.toml`。**改码后必须重新 cp+deploy 新实例**（shaker 每次全新实例）；R2 实例 `0xFD6F…c351` 只作 T1 探针的实验台（其 probe 方法已部署，零改码操作）。
- **P2 写通道与资金纪律**（R2 方案 P2 + 任务陈述）：`status=="0x1"` ≠ 方法 Ok；一切效果以 `deal_info`/`balance_of` 读回复核；读回滞后一块，demo 内建重试（`wait_state`）。**资金自足**：多 deal 每 deal faucet + fund 前 `balance_of` 断言（`require_funds` helper，R2 已备）。
- **P3 println 证据通道**（任务陈述 + R1/R2 先例）：instance 方法证据只走 cast call（assess_brief 先例 w1b2-r1-s3-assess.md）；network 方法 println 走 `shaker console` 回放（`_r1-console-fund-raw.txt` 先例；S2 §4 认证回调 println 亦经 console 取得）。
- **P4 anvil 角色**（任务陈述 + rpc.py:64-66）：#0=broker=`0xf39F…9266`（部署/creator 同钥）、#1=alice=buyer=`0x7099…79C8`、#2=bob=seller=`0x3C44…93BC`。
- **P5 oracle 认证回合机制**（w1b1-s2-oracle.md，S2 全套实证）：configure（`eth_guard=creator`，仅 staging）→ advance/finalize（**平台内置 `__lyquor_oracle_advance_epoch(string=topic,address,bool)`，只能 cast call 通道**——cast send status 1 但内层提交静默丢失，S2 §3 通道修正）→ run_round（cast call）→ 内层 certified call 上链（块内非我方 tx 实证，S2 §4）→ 认证回调可见 `ctx.cert.signers: Vec<SignerID=u32>` + `ctx.signer_node_id(u64) -> NodeID`（显示形 `Node-…`，S2 §4 逐行实录）。dest_epoch 是 advance→finalize 的等待条件（get_epoch 在 finalize 前恒 0，probe_net_config 注记）。
- **P6 两阶段方法硬约束**（s2_oracle.rs:8-21）：`propose`/`aggregate` 字面名（ldk syntax.rs:447/:470 宏臂逐字匹配）；serde 按字段名解码（`decode_by_fields!`）；init 字段 `avg_num`/`target` 是 price-feed 已证形态。**S2 遗留：threshold=2 双签聚合未执行**（w1b1-s2-oracle.md §6）——**多签聚合是否可达是本轮 T1 探针的正主问题**，方案不预设结论。
- **P7 裁决校验单点**（core.rs:191-252，本轮实读）：`apply_verdict` 仅 Disputed 可入；`validate_cert` 四查 = signers 全员 ∈ members + 去重 + |signers|≥threshold + evidence_root 匹配当前全量证据折叠（core.rs:235-252）；NotFulfilled → 全额退款、misconduct **不**增（Malicious 独占 +1，:206）；终态由裁决映射（:213-216）。
- **P8 路线① 现状**（lib.rs:484-542 实读）：扁平 wire `(string,uint8,string[])`；`require(Access::Committee)` 地址门（lib.rs:218）+ caller∈signers（lib.rs:502）；占位串成员（demo.py:60 `COMMITTEE = [BROKER, "node-1",…]`）——**E2 要替换的正是"broker 单点签署 + 占位串成员"两个占位性质**（implementation.md §6-#9）。
- **P9 sim/壳回归口径**（R1 方案 D8/P7 + R2 G7）：40/40 = 33 lib + 5 escrow + 2 modelcheck；**lib.rs 不挂载壳**——本轮 lib.rs 改动不影响壳字面；sim `--flow all` 逐字 diff 是零回退硬门。

## 2. 本轮规划期新实证（规划师 2026-10-30 实读/实跑，编码员须知晓）

1. **forge 工具链容器内可用（目标 B 最大风险提前排除）**：实跑 `docker exec multi-tools sh -c "…forge build"`（Smoke.sol 冒烟，建后即删）→ `Compiling 1 files with Solc 0.8.37 / Compiler run successful!`。forge 1.7.1 + solc 0.8.37 自动获取可用（`which forge cast shaker` 三者俱在）。
2. **anvil JSON-RPC 从 multi-tools 容器内可达**：实跑 `docker exec multi-tools wget -qO- http://anvil:8545 --post-data='{"jsonrpc":"2.0","method":"eth_chainId",…}'` → 服务端返回 JSON-RPC 错误封包（-32600，wget 头形态所致）——**有响应=HTTP 连通成立**。目标 B 的 forge create 走 `--rpc-url http://anvil:8545` 容器内执行。
3. **宿主无 forge、anvil 无宿主端口映射**：宿主 `forge --version` 不可用；`docker port multi-anvil-1` 输出为空。**结论：EVM 轨全部操作在 multi-tools 容器内执行**（与 lyquid 通道同构），宿主只做 docker cp/exec。
4. **GetNodeInfo 宿主直连形态**（w1b1-topology.md:150-160 实录）：`curl -s --data '{}' -H 'content-type: application/json' http://127.0.0.1:$p/lyquor.node.v1.NodeService/GetNodeInfo`，$p ∈ {10087,11087,12087,13087}。NodeID→bytes32 换算（demo.sh:199-212 镜像）S2 §1 已逐字节双重验证。
5. **certified 回调 origin 语义线索**（s2_oracle.rs:148 实读）：`CertifiedCallParams { origin: Address::ZERO, … }`——认证回调的 caller 域为 ZERO/节点侧，**不可能通过地址制 require 门**。这从机制上决定了 §3.2-E 的门禁设计（cert 即认证，不走地址门）。
6. **demo 流程结构**（demo.py:242-371, 469-498 实读）：三 flow + 每流自前置 `committee_config`（:497-498 总配置与 :371 对抗流自配置并存，后配置覆盖先配置）——**E2 流自前置 NodeID 制配置与既有流零冲突**。
7. **instance 方法可读 network 状态**（s2_oracle.rs:294-317 probe_config 先例）：`ctx.network.*` 在 instance 方法内只读可达——`propose` 内读 network `evidence_log`/`deals` 可行（编译+实跑双验证放 T2/T3 门）。
8. **七容器全 Up**（本轮 `docker ps` 实跑）：multi-tools / node1-4 / registry / anvil（与任务陈述一致）。
9. **rpc.py 编码器支持面（仲裁 R1#1 材料，本轮实读核实）**：模块 docstring 明示覆盖集 = `string / uint8..uint128 / bool / string[]`，无 bytes32/bytes32[]（rpc.py:139-142）；`_enc_value` 对集外类型抛 `unsupported ABI type`（:177 区域）；`_is_dynamic` 仅识 `("string","string[]")`（:180-181）——e2_configure 的 `bytes32[]` 走 NodeClient 须扩编码器，走 cast 通道则零改动（已选 B，§0-#3）。另核实 lib.rs:694 `fn credit`、:718 `fn apply_payout`（仲裁 R1#3 资金路径引用）；implementation.md:204 console 命令需 `Lyquid-…` 实例名；`_r1-deploy-raw.txt:423-424` deploy 日志输出 `created Lyquid-ffy2ydso… => 0xF8e3…`（--instance 缺省回填来源）。

## 3. 目标 A：E2 四节点委员会演示（路线②）

### 3.1 总体形态

新增 oracle topic `cert_verdict`（lib.rs state! 一行）+ 顶层壳模块 `committee_certified.rs`（探针→演示级接线的正主化；probe/ 的 cert_probe 保留不动，作为机制对照面）。裁决经 `propose_and_certify` 多节点认证后，由内层 certified call 送达 `committee_verdict_certified` 网络回调；回调把 `ctx.cert.signers` 映射为 NodeID 字符串、以 `CommitteeCertWire` 形态进入**与路线①完全相同的校验/裁决/写回链**（§0-#1 的 helper）——路线①②共享 core 单点，信任模型唯一。

### 3.2 逐方法设计（committee_certified.rs）

- **A. `e2_configure(ctx, node_ids: Vec<NodeID>, threshold: u16) -> bool`**：`#[method::network(export = eth, eth_guard = creator)]`，镜像 probe_configure（s2_oracle.rs:61-86）但落 `cert_verdict` staging。creator=anvil#0=部署钥（P4；guard 先例 S2 §2）。**调用通道（仲裁 R1#1 选 B）**：demo 走 `docker_exec_cast` cast send——`cast send $CTR "e2_configure(bytes32[],uint16)" "[<4×0x…>]" <th> --private-key <anvil#0> --rpc-url http://node1:10087/api`，与 S2 probe_configure 完全同形（w1b1-s2-oracle.md §2:27-30 实证：status 1 + console `staged committee of 4 nodes`）；rpc.py 编码器零扩展、`_ABI` 无此行（NodeClient 直发的例外许可路径与默认禁止，见 §0-#3/终裁冻结条款 1）。
- **B. `e2_arm(ctx, deal_id: DealId)`**：**`#[method::network(export = eth, eth_guard = creator)]`（仲裁 R2#1-a）**，写 **network 域** `e2_armed_deal`（共识持久、全节点可见）——经 NodeClient `_send`（eth_sendTransaction，R1/R2 已证写通道）**单次发送即全体节点生效**，无需每节点 arm。**门=creator（作者定）**：arm 决定"委员会下一轮裁哪一单"，属演示编排面，与 e2_configure 同口径 fail-closed；无门会让任意 caller 改写 armed deal 干扰演示——终局安全仍由 cert 门兜底（§3.2-E），此处收紧是纵深防御。**为什么需要 arming**：init 只携带 price-feed 已证的 `avg_num`/`target` 二字段（P6——init 携带第三字段未经平台实证，不冒险），待裁对象经共识状态传递给全体节点的 propose。**读回断言（口径统一，冷读仲裁修订 1-3）**：arm 后 NodeClient call("e2_net_config()") 解码返回 JSON，断言 `armed_deal == deal_id`（P2 读回复核口径；§3.2-G，不新增 getter——方法面纪律；console 回显行仅作 transcript 佐证而非断言载体）。**终裁冻结条款 4：此 network 域形态为定稿，不得回退 instance 域 cast call 形态**。
- **C. `propose(ctx, avg_num: u16, target: OracleTarget) -> VerdictProposal`**：`#[method::instance(group = oracle::two_phase::cert_verdict)]`，字面名。**每节点独立检视**：读 armed deal + network `evidence_log[deal_id]` + `deals[deal_id]`（实证 2-7），跑 `committee::check_evidence_shape(entries, deal)`（committee.rs:66-74，**只读调用**，committee.rs 零改动）→ **verdict 由链上证据派生**：shape 成立→Fulfilled(0)，不成立→NotFulfilled(1)。`VerdictProposal { deal_id, verdict_code, node, ts_ms }`（serde 字段名即解码契约，P6）。未 arm 的节点 propose 返回 Err/拒绝（fail-closed）。
- **D. `aggregate(ctx) -> Option<CertifiedCallParams>`**：`#[method::instance(group = oracle::two_phase::cert_verdict)]`，字面名。inputs < avg_num → None（等更多提案）；**提案间 verdict 不一致 → None（拒证，诚实语义：委员会未达成一致就不出证）**；一致 → `CertifiedCallParams { origin: Address::ZERO, method: "committee_verdict_certified", input: encode_by_fields!(deal_id: String, verdict_code: u8), target }`。println 记录聚合视图（inputs 数、各节点 verdict）。
- **E. `committee_verdict_certified(ctx, deal_id: DealId, verdict_code: u8) -> bool`**：`#[method::network(group = oracle::certified::cert_verdict::two_phase)]`，认证回调（probe_on_certified 的生产化）。**性质定位（仲裁 R1#3）**：这是 **cert 门控的资金路径**——回调经共享 helper → `apply_payout`（lib.rs:718，内经 `credit` lib.rs:694）真实结算，§3.5 主场景即全额退款；非 probe 类可豁免审计的 SPIKE 面。**门禁设计（本方案核心决策，依据实证 2-5）**：不走 `require` 地址门（亦即不入 ACCESS_MATRIX——矩阵外不等于无审计，台账见 §3.2-H）——certified call 的 origin=ZERO，地址门必然 fail-closed；**认证来源 = 证书本身**：`ctx.cert.signers` 逐个 `ctx.signer_node_id` 映射为 NodeID 显示串 → 作为 `CommitteeCertWire.signers` → 进入共享链，由 `core::validate_cert`（P7 四查：全员 ∈ committee_members + 去重 + 阈值 + evidence_root 匹配）完成实质门禁。**committee_members 里配置的正是真实 NodeID 串**（§3.3），伪造 signers 过不了成员检查——这正是"多节点认证替换单点签署"的信任升级点。回调 println 取证：RAW signers、逐节点映射、verdict、deal_id（console 可见，P5）。evidence_root 与路线①同源：回调内读 network evidence_log 折叠（into_domain 单点，core.rs:225-231 契约）。
- **F. `e2_run_verdict_round(ctx) -> bool`**：`#[method::instance(export = eth)]`，镜像 probe_run_round（s2_oracle.rs:195-223）；**`avg_num` 为编码期常量：首跑取 4（L2 编排），fallback 改 1 须重新 cp/deploy（仲裁 R2#2，§3.4 预登记）**；`submit_certified_call!` 提交内层认证调用。**仅 node1 单次触发**（propose 经 UPC 广播自带全节点提案，§3.4-L2）。
- **G. `e2_net_config(ctx) -> LyquidResult<String>`（冷读仲裁修订 1-1）**：`#[method::network(export = eth)]` 属性不变；**返回 JSON dump 串**（`_ABI` 返回面=string，`_decode_ret` 已支持，先例 deal_info lib.rs:567 / evidence_entries_json lib.rs:584），至少含 `armed_deal`（未 arm 时为空串）+ 现行 dump 面：current/staging threshold、committee、src epoch、dest epoch/change_count（`fetch_oracle_info("cert_verdict", …)` 口径不变，镜像 probe_net_config s2_oracle.rs:257-281——advance→finalize 的等待条件面，P5）；console println 保留但**降级为佐证而非断言载体**（断言走 NodeClient call 解码，§3.2-B）。

- **H. E2 门禁台账（仲裁 R1#3 选 b；落点 = committee_certified.rs 模块头表 + lib.rs:166-170 矩阵审计面注释加一行指向）**。不选 (a) 的理由：ACCESS_MATRIX 的设计语义是「每行一个 network fn 的 **require 地址门**、`require` 是唯一执行点」（lib.rs:185-205），certified 方法不经 require，入矩阵须写「此行不经 require」的特例——破坏「一瞥即得的审计面」。台账形态（7 方法 × 面 × 实际门 × 是否触资金）：

  | 方法 | 面 | 实际门 | 触资金 |
  |---|---|---|---|
  | e2_configure | network-eth | `eth_guard = creator`（部署钥） | 否（仅 oracle staging） |
  | e2_arm | network-eth | `eth_guard = creator`（演示编排面，与 e2_configure 同口径；写共识状态） | 否 |
  | propose | instance-two_phase | armed 检查 fail-closed；只读 network 状态 | 否 |
  | aggregate | instance-two_phase | 一致性拒证；只组装 certified call | 否 |
  | committee_verdict_certified | network-certified | **cert 门 = core::validate_cert（成员+去重+阈值+evidence_root）；对直调 fail-closed**（require 只见 caller，而 certified caller=ZERO 必败；合法路径 = 平台 certified call） | **是**（apply_payout 结算） |
  | e2_run_verdict_round | instance-eth | 无门（仅发起认证回合；安全域=oracle 委员会本身） | 否 |
  | e2_net_config | network-eth | 无门（只读观测 dump） | 否 |

  **probe 先例不可类推（仲裁 R1#3）**：probe 网络方法不入矩阵属 SPIKE 例外（probe/mod.rs:17-18 明言 W2 移除/退役）**且零资金**（不触 apply_payout/credit）；本模块触资金，必须自带台账。

### 3.3 成员/阈值真实性（committee_config NodeID 制）

E2 流程前置两处配置，**同源对齐**（都来自当轮 GetNodeInfo×4 实取，**禁硬编码**——NodeID 标识节点而非实例，同 devnet 跨实例稳定，换 devnet 必变）：

| 配置面 | 调用 | 值 |
|---|---|---|
| escrow 成员域 | `committee_config(members, threshold)`（既有方法 lib.rs:551，broker 地址门不变） | members = 4×NodeID 显示串（`Node-ve3t…` 形），threshold = 4（或 T1 登记的降级值） |
| oracle 认证域 | `e2_configure(bytes32[], uint16)`（新，creator 门） | 同 4 节点的 bytes32 形（S2 §1 换算），threshold 同值 |

映射闭环：oracle signer_id →（`signer_node_id` 运行时映射）→ NodeID 显示串 → ∈ committee_members。**两域阈值同值**，证据文档注明对齐关系。R2 地址制对抗流不受影响（实证 2-6：各流自前置配置）。

### 3.4 T1 平台探针梯子（先证多签聚合，再写生产码）

**S2 遗留的 threshold=2 双签聚合未执行**（P6）是本轮最大平台未知数。T1 在 R2 实例 `0xFD6F…c351`（probe 方法已部署，零改码）上跑：

1. 宿主 curl GetNodeInfo×4 → 当轮 NodeID/bytes32（`_r3-t1-nodeinfo-raw.txt`；顺带取证宿主对 {11087,12087,13087} 的连通性）；
2. `probe_configure(4×bytes32, threshold=2)` → advance/finalize（cast call + dest_epoch poll）→ `probe_run_round` → console：**cert.signers 长度是否 ≥2 且映射到 ≥2 个不同节点**（`_r3-t1-th2-raw.txt`）；
3. 若 ② 成立：`probe_bump_threshold(4)` → 二次 advance/finalize → run_round → console：**signers=4？**（`_r3-t1-th4-raw.txt`）；
4. **通道面取证（仲裁 R1#2）**：容器内 `cast call --rpc-url http://nodeN:10087/api … dest_epoch_info`（N∈{2,3,4}——S2 已证 node2/node3 容器内可读，w1b1-s2-oracle.md §3 跨节点可见性；node4 补测）+ 宿主 eth_call 直连 node2-4 的 instance 方法通道试探（`_r3-t1-node234-channel-raw.txt`）——宿主 eth_call 直连 node2-4 **未证**（S2 仅实证 node1:10087 cast call 形态，w1b1-s2-oracle.md §8:136），不通则 L2 触发降级 docker_exec_cast（§3.6-5），仍不通=降级 L1 并显式登记；
5. **参与度分级结论表**（写入 w1b2-r3-e2-committee.md §T1）：
   - **L2（目标形态）**：4 提案（inputs=4）+ 4 签（signers=4）——**arm 一次（network 域单发全节点生效，§3.2-B）+ node1 单次触发 + avg_num=4**；机制依据（仲裁 R2#2 核证）：propose 经 UPC 广播（protocol.rs:312/:316）→ 单次触发即全部委员会节点各出一提案；**不可多次触发**——N 次触发=N 个独立回合，首回合裁决已把 deal 从 Disputed 推到终态，后续 certified call 在 core.rs:199 的 Disputed 门必败；
   - **L1（可接受的四节点签署）**：1 提案 + 4 签（signers=4，avg_num=1）——签名集来自全部 4 节点即"四节点签署"成立；独立检视叙事由 propose 的证据派生承载（提案节点跑检视，其余节点签的是各自 replay 的同一聚合）；
   - **L0（平台硬限制）**：threshold>1 时 certify 无法聚齐（run_round 恒 false / signers 恒 1）——路线②只能单签送达。**降级处置**：交付"L2/L1 不可达的平台限制登记 + 单签 certified call 打通 + 路线①现状"三段式诚实报告，演示与手册按实际级别描述，**绝不以单签冒充四节点**（诚实红线）。

**T1 的证明边界与 avg_num 决策（仲裁 R2#2）**：T1 只证两件事——signers 聚合（th2/th4：threshold>1 时 certify 能否聚齐多节点签名）与通道面（容器内跨节点可读性）；**多提案路径 T1 证不了**（probe_run_round 硬编码 avg_num=1，s2_oracle.rs:208，观察不到 inputs>1 的聚合行为）。**avg_num=4 是 T2 编码期选择**（首跑 L2 编排：arm 一次 + node1 单次触发）；**L2 的证据在 T3 首跑**：console 聚合行须同时见 inputs=4 + signers=4。**预登记 fallback（G3 判据）**：T3 首跑提案数 <4（UPC 广播聚合不如预期）→ 改 avg_num=1（L1 口径：1 提案 + 4 签）+ **重新 cp/deploy**（编码期常量改值需重部署）→ 按 L1 口径取证并显式登记降级；若 signers 也聚不齐（T1 已前置发现），按 L0 三段式处置。四端点触发（NodeClient×4 / docker_exec_cast 对 nodeN:10087）**降级为诊断手段**：仅当 T3 首跑 inputs<4 且需排查"某节点未收到提案"时逐节点观测用，不作主路径。

### 3.5 演示场景

**主场景 = NotFulfilled（证据派生）**：卖家收货款后不交付（deliverable_digest=None）→ 买家 open_dispute → 4 节点各自检视证据链（check_evidence_shape=False）→ 认证裁决 NotFulfilled → 全额退款、misconduct 不增（P7；与 R2 路线① Malicious 场景互补，misconduct 对照点=不增）。**为什么选证据派生**：verdict 由各节点对链上证据的独立计算得出，非脚本喂值——这是"真实 4 节点检视"的最诚实形态，排除"演示脚本伪造裁决"的质疑面。**可选加分（不阻塞）**：Fulfilled 对照单（先 notarize+submit_deliverable 再 dispute → shape 成立 → Settled 分账），同一机制第二场景，时间盒允许才做。

### 3.6 单命令演示形态（demo.py `flow_committee`）

```
python scripts/demo.py --node http://127.0.0.1:10087 --contract 0x<新实例> --instance Lyquid-<新实例名> --flow committee
```

步骤（node-only；sim 调用即报错退出，不进 `--flow all`）：
1. env 断言（contract/endpoint/docker 可用性 + **TARGET 检查**：推导见步骤 3，断言非零且 ≠ `--contract`）+ GetNodeInfo×4（rpc.py 新 `get_node_ids`）；
2. `committee_config(NodeID×4, 4)`（broker，NodeClient）→ `e2_configure(bytes32×4, 4)`（**docker_exec_cast cast send 通道**，仲裁 R1#1-B；S2 同形先例 w1b1-s2-oracle.md §2:27-30）；
3. **TARGET 推导（仲裁 R2#3）**：`docker exec multi-tools shaker to-hex <instance>`（实例名 = `--instance` 传入值）→ 断言 **非零且 ≠ `--contract`**（TARGET 是 LVM 域地址，先例 w1b1-s2-oracle.md:22：TARGET `0x8a94…91f5` ≠ 实例合约 `0xcbEA…47cc`；推导命令与输出值写入 `_r3-t3-*` 原始日志）→ advance/finalize：`docker exec multi-tools cast call … "__lyquor_oracle_advance_epoch(string,address,bool)" "cert_verdict" $TARGET false` + dest_epoch poll + finalize（rpc.py 新 `docker_exec_cast` 助手；平台内置方法不占方法清单）；
4. 建争议单：faucet + `require_funds` 余额断言（P2 纪律）→ create_deal → fund（alice）→ **无交付** → open_dispute（alice）→ 读回 Disputed；
5. `e2_arm(deal_id)` **一次**（network 方法，NodeClient `_send` 单发全节点生效，仲裁 R2#1-a）→ **NodeClient call("e2_net_config()") 解码 JSON，断言 armed_deal == deal_id**（冷读仲裁修订 1-3；console 回显行仅 transcript 佐证）→ `e2_run_verdict_round()` **仅 node1 单次触发**（propose UPC 广播自带全节点提案，§3.4-L2，仲裁 R2#2；**通道纪律**：run_round 沿 S2 实证的 cast call 形态（w1b1-s2-oracle.md §8:136），**严禁 cast send**——S2 §3/§4 已证 cast send 对内部异步提交类方法 status 1 但内层静默丢失）；
6. 轮询 `deal_info` 至 Refunded + `balance_of` 勾稽（buyer 全额）+ misconduct 视图对照（console println：NotFulfilled 不增）；
7. console 取证段（`timeout 60 docker exec multi-tools shaker console <Lyquid-…> --endpoint ws://node1:10087/ws` 抓 signers/verdict/aggregate 行；**实例名**经 `--instance` 参数传入或缺省自 T3 deploy 实录回填的脚本常量（deploy 日志输出实例名，`_r1-deploy-raw.txt:423-424` 先例；shaker console 必须用实例名，implementation.md:204）；**取证源 = node1**，§0-#4）+ 终态摘要打印。

## 4. 目标 B：纯 EVM 对照实验

### 4.1 目录与工具链（已实证，§2-1/2/3）

`trustbridge/experiments/evm-contrast/`（新目录，**不在 lyquid/ 冻结树内**——任务陈述明确）。foundry 工程 docker cp 进 `/tmp/tb-evm`，容器内 `forge build` + `forge create --rpc-url http://anvil:8545 --private-key <anvil#0>`。**同一 anvil** = multi devnet 共享 sequencer（w1b1-topology.md:97 `ws://anvil:8545`，Lyquid 实例底层同链）——双方链上证据同链可比。

### 4.2 Escrow.sol 功能面（与 Lyquid escrow 逐能力对照）

| 能力 | Lyquid 面 | Solidity 面 |
|---|---|---|
| 建单/资金托管 | create_deal + fund（network fn） | createDeal(参数同域) + fund() payable |
| 证据公证 | notarize（append-only，from==caller 自署名） | notarize（msg.sender 隐式自署） |
| 交付/完成 | submit_deliverable + complete | submitDeliverable + complete |
| 超时 | claim_timeout（slot 域） | claimTimeout（block.timestamp 域） |
| 取消 | cancel | cancel |
| 争议 | open_dispute | openDispute |
| 委员会配置 | committee_config（broker 门） | committeeConfig(address[] members, uint threshold)（deployer 门） |
| **裁决送达** | 路线②：oracle certified call（平台提供 propose/certify/signers/内层上链全套）+ 路线①：扁平 wire | applyVerdict(dealId, verdictCode, bytes[] sigs)：**k-of-n ECRECOVER 自建**——每 sig 对 keccak256(abi.encode(dealId, verdictCode, evidenceRoot)) 签名，ecrecover ∈ members、去重、≥threshold；evidenceRoot=链上 entries 顺序敏感 keccak 折叠（语义对齐 core::evidence_root 的绑定契约 core.rs:225-231，算法族不同如实注明） |
| 裁决效果 | core::apply_verdict 单点（分账/退款/misconduct） | 同语义 payout 分账/退款（misconduct 计数映射） |

### 4.3 对比维度与数据采集（报告表格形态）

| 维度 | 采集法（双侧） |
|---|---|
| 代码量 | Solidity：Escrow.sol 实际行数；Lyquid：两种口径——领域面（types.rs+core.rs+committee.rs）与装配面（+lib.rs）；**定性行**：oracle 认证全套（propose/certify/签名聚合/内层上链）平台自带 vs EVM 侧 ECRECOVER 聚合必须自写（代码量对比的核心论点） |
| 信任假设 | 表格四行：路线①（单点签署占位）/ 路线②（多节点认证，阈值可配）/ EVM k-of-n（自建签名聚合+密钥管理自带）/ EVM 单仲裁人（朴素替代，**报告注明为假设变体，不实现**）——谁认证委员会本身、谁能伪造裁决、拜占庭容限几何 |
| 裁决不可篡改性 | 双侧机制描述 + 链上证据：Lyquid certified call 落块 tx（内层交易哈希，S2 §4 同法）vs EVM applyVerdict 收据；evidence_root/keccak 绑定语义对照（core.rs:225-231 防篡改契约 vs Solidity 等价实现） |
| 部署/调用开销 | gas：forge create 收据 vs shaker deploy 的 anvil 收据（deploy 输出含 tx hash）；逐操作 gasUsed 双侧（fund/complete/claimTimeout/裁决各取 eth_getTransactionReceipt——rpc.py 补只读收据 gas 读取助手[容器内 cast receipt 通道，见 R11]） |

产出：`workflow-out/w1b2-r3-evm-contrast.md`（四维表格 + 原始数据 + 双方 tx/块引用 + 诚实边界段：对照的是同等功能的最小实现而非最优 Solidity 实现；gas 受 anvil automine 形态影响注明）+ `_r3-t4-*.txt`。

## 5. 目标 C：B3 组外用户测试备料（docs/b3-user-test/，3 文件）

- **操作手册.md**：前置环境（容器 Up 检查命令、实例地址获取、宿主 Python 依赖）、四条动线（正常流/超时流/对抗流/委员会流）+ 对照实验各一节——逐步命令、**每步预期输出**（引 T3/T4 实录回填，不虚构）、每流通过判据表、常见故障排查 4-6 条（实例不存在/余额不足需 faucet/读回滞后重试/cast 通道用错/advance 未完成就 finalize）。
- **演示脚本.md**：10-15 分钟动线（讲稿要点 × 命令 × 预期画面 × 时间分配），重点段=四节点签署的 console 画面如何讲解（signers 逐节点映射行）。
- **反馈收集表.md**：每流任务完成度评分（1-5）、易用性、两道信任模型理解题（委员会认证从哪来/裁决能否被单点篡改）、自由反馈栏。
- 纪律：文档命令必须与 T3/T4 实跑一致（从实录回填）；真实测试由用户线下安排（任务陈述），文档按"无仓库上下文的组外用户可照跑"标准自足。

## 6. 子任务拆分、执行顺序与门禁

```
T0 基线（G0）→ T1 平台探针梯子（G1，降级决策点）→ T2 R3 代码+构建+回归（G2）
→ T3 E2 演示（G3）→ T4 EVM 对照（G4）→ T5 B3 备料（G5）→ T6 收尾（G6）
```

| T | 内容 | 原始日志 |
|---|---|---|
| **T0** | `_pre-task-snapshot-r3.patch`（git diff 全量）；四冻结文件 md5 对 `_r2-t0-frozen-baseline.txt` 复核；sim 基线 `--sim --flow all`；壳 40/40（父目录 verify_core `cargo test --lib --tests`）；`docker ps` 七容器 | `_r3-t0-sim-baseline-raw.txt`、`_r3-t0-env-raw.txt` |
| **T1** | §3.4 探针梯子（R2 实例 `Lyquid-tldda6zq…`（implementation.md:11-13），零改码；**TARGET 显式推导**：`docker exec multi-tools shaker to-hex <实例名>` + 断言非零且 ≠ 实例地址 `0xFD6F…c351`，推导与值入日志——仲裁 R2#3）；**只证 signers 聚合（th2/th4）与通道面**（多提案路径不可证：probe_run_round 硬编码 avg_num=1，s2_oracle.rs:208——仲裁 R2#2）+ 参与度分级结论表 + node2-4 通道面取证（观测/诊断面：跨节点 dest_epoch 可见性，node4 补测） | `_r3-t1-nodeinfo-raw.txt`、`_r3-t1-target-raw.txt`、`_r3-t1-th2-raw.txt`、`_r3-t1-th4-raw.txt`、`_r3-t1-node234-channel-raw.txt` |
| **T2** | 写码（§0 #1–#4）→ `MSYS_NO_PATHCONV=1 docker cp` + md5 勾稽 → 容器 `touch src/*.rs` + `cargo check --target wasm32-unknown-unknown`（R2 教训：必须强制重编）→ 壳 40/40 复跑 → sim `--flow all` 与 T0 基线逐字 diff | `_r3-t2-container-md5.txt`、`_r3-t2-cargo-check-raw.txt`、`_r3-t2-sim-diff.txt` |
| **T3** | cp+deploy 新实例（deploy 实录含实例名→回填 demo `--instance` 缺省常量；**TARGET=`shaker to-hex` 推导 + 断言入 `_r3-t3-*` 日志**，仲裁 R2#3）→ 单命令 `--flow committee` 全 transcript（**L2 首跑判据：console 聚合行 inputs=4 + signers=4**；不达 → 预登记 fallback：avg_num=1 + 重新 cp/deploy + L1 口径取证，仲裁 R2#2）→ 读回复核 → **对抗流 node 复跑**（helper 重构行为保持判据：Malicious 单仍 Refunded + misconduct +1，对照 R2 w1b2-r2-adversarial.md 结果） | `_r3-t3-deploy-raw.txt`、`_r3-t3-committee-raw.txt`、`_r3-t3-console-raw.txt`、`_r3-t3-final-state-raw.txt`、`_r3-t3-adversarial-regression-raw.txt`（fallback 发生时另增 deploy/console 第二套） |
| **T4** | §4 对照实验（build→deploy→三流→数据采集→报告） | `_r3-t4-build-raw.txt`、`_r3-t4-deploy-raw.txt`、`_r3-t4-flows-raw.txt`、`_r3-t4-gas-raw.txt` |
| **T5** | B3 三文档（命令/输出从 T3/T4 实录回填） | （交付物本身即证据） |
| **T6** | 回归套件复跑（40/40 + sim diff + 冻结门=G2 口径：三文件 `git diff --stat` 空 + 四文件 `md5sum -c _r2-t0-frozen-baseline.txt` 全 OK + assessor.rs +5 在场保留）→ `_commit-plan.md` R3 分组 → `implementation.md` 增量 → 证据交叉复核（引用的日志都在） | `_r3-t6-regression-raw.txt` |

**门禁表**：

| G | 判据（全部实跑取证） |
|---|---|
| G0 | 快照存在；md5 四文件全 OK；sim 基线入档；40/40 入档；七容器 Up |
| G1 | T1 三份日志 + 分级结论表入档；**若 ≤L0：降级决定+限制登记已写入证据文档，后续按降级口径执行** |
| G2 | 容器 cargo check 零错误（md5 勾稽在档）；40/40 = 40/40；sim diff **IDENTICAL**；冻结门口径（冷读仲裁修订 2）= **types.rs/core.rs/committee.rs 三文件 `git diff --stat` 为空，且 `md5sum -c workflow-out/_r2-t0-frozen-baseline.txt` 四文件全 OK**；`lyquid/src/assessor.rs` 对 HEAD 的 +5（R1 已审 `#[derive(Deserialize)]`，lib.rs:649 assess_brief 依赖）为 **T0 基线在场改动，持续保留、严禁回退**（与 §0 md5 口径、implementation.md:163-164、R2 G4/G5b 先例 implementation.md:154/:156 对齐；凭据：HEAD=dc78d2f，四文件 git diff --stat 仅 assessor.rs 5/0，md5sum -c 四 OK） |
| G3 | committee transcript：console（**取证源=node1，`--instance` 实例名**）见 signers 映射到真实节点（数量=登记级别，L2/L1 须 4）；**L2 首跑判据=聚合行 inputs=4 + signers=4（仲裁 R2#2）**；不达时预登记 fallback 已执行（avg_num=1 + 重新 deploy + L1 口径取证）或 L0 降级显式登记；TARGET 推导与断言（非零且 ≠ `--contract`）在 `_r3-t3-*` 日志；**arm 读回断言（`e2_net_config()` 解码 armed_deal == deal_id）在 demo transcript，console 回显行在档**（冷读仲裁修订 1-4）；deal_info 终态 Refunded；balance 勾稽；misconduct 不增对照；对抗流复跑与 R2 结果一致 |
| G4 | Escrow 部署收据（anvil 同链）；三流收据/转账证据；四维表数据齐（双侧）；报告落盘 |
| G5 | 三文档齐；命令与 T3/T4 实录一致（抽查 grep）；通过判据/反馈表在 |
| G6 | 回归三件套全绿（40/40 + sim diff + **G2 冻结门口径**：三文件 diff 空、四文件 md5 OK、assessor.rs +5 在场保留）；_commit-plan R3 组在；implementation.md 分节/偏离/未尽齐（含 e2_net_config 签名/返回类型登记）；**未执行任何 git commit/add/push** |

## 7. 风险与回退（编号登记，编码员逐条知晓）

| # | 风险 | 缓解/回退 |
|---|---|---|
| R1 | **四签聚合不可达**（S2 §6 未证；T1 正主） | §3.4 阶梯：L2→L1→L0；L0 = 平台限制登记 + 单签路线②打通 + 诚实标注，**绝不伪造四节点** |
| R2 | init 携带第三字段不可解码 | 已规避：arming 方案（§3.2-B），init 保持 price-feed 二字段形态 |
| R3 | certified 回调 caller=ZERO 过不了地址门 | 设计即如此（§3.2-E）：cert 即认证，core::validate_cert 实质门禁；若 T3 实测认证回调 caller 另有形态，如实登记后按实测调整 |
| R4 | `propose` 内读 network 状态（armed deal / evidence_log / deals）受阻 | instance 内只读 network 先例（probe_config，s2_oracle.rs:294-317，实证 2-7）；**arming 已迁 network 域（仲裁 R2#1-a），propose 读 armed deal = network 同域只读，不再依赖 instance 写路径**（措辞更正，仲裁 R2#1：s2_oracle.rs:93-97 的 instance 写是**合约内平台驱动写**，非宿主通道先例）；T2 编译门 + T3 实跑门双卡；仍受阻则降级=verdict 由 aggregate 侧统一派生（弱化"每节点独立检视"叙事并登记） |
| R5 | 节点间 evidence/round 同步滞后致 aggregate 拒证 | 拒证是诚实语义（None=未达成一致）；demo 轮询重试 + 间隔递增；持续失败=降级登记 |
| R6 | 新 topic 的 state! 字段/宏展开不兼容 | 镜像 cert_probe 逐字形态（先例已编译+实跑）；T2 容器 check 是硬门 |
| R7 | helper 重构改变路线①行为 | 行为保持判据 = G2 sim 零回退 + G3 对抗流复跑逐字段对照 R2；任何偏差=回退重构，改为回调内少量重复代码（**宁可重复不可漂移**） |
| R8 | 新实例 oracle staging/激活失败 | advance/finalize 等待条件用 dest_epoch（P5，勿用 get_epoch）；失败重试一次后登记 |
| R9 | forge/solc 正式构建时获取不可复现（冒烟已过） | 冒烟实录入档（§2-1）；复发则查 `~/.svm` 缓存持久化；再失败=目标 B 阻塞，登记并 escalate |
| R10 | 资金/实例纪律违例 | P2 纪律逐 deal 断言；R2 实例只做 T1 探针操作（probe_configure/run_round 属 probe 面，不触 escrow 资金）；R3 新实例承载演示 |
| R11 | lyquid 侧收据 gas 读取通道未知（node API 是否透传 eth_getTransactionReceipt） | T4 先探（容器内 cast receipt 经 node API 与 anvil 直连各试一次）；不通则统一走 anvil 直连只读取数，不阻塞流程 |
| R12 | **宿主 eth_call 直连 node2-4 的 instance 方法通道未证**（S2 仅实证 node1:10087 cast call，w1b1-s2-oracle.md §8:136）——**仲裁 R2#2 后主路径已不依赖**（node1 单次触发即全节点提案），此风险仅影响诊断手段可用性 | T1 通道面试探（跨节点 dest_epoch 容器内可读性，node4 补测）；T3 需逐节点排查时先试 NodeClient×4 宿主直连、不通降级 `docker_exec_cast` 对容器内 nodeN:10087（cast call 形态）；诊断通道全不可通=只能按 T3 首跑现象直接走 fallback（avg_num=1 + L1 口径）并登记 |

## 8. 验收对照（任务交付 a/b/c）

- a) `w1b2-r3-e2-committee.md` + `w1b2-r3-evm-contrast.md` + `_r3-*.txt`（§6 清单）入档 ✓
- b) `_commit-plan.md` R3 分组增补（建议序列，**不执行 git commit**）✓
- c) `implementation.md` 增量：门禁总表（G0–G6 实跑结果）+ 偏离（预登记 §7 中实际发生者）+ 未尽（L0 降级[如发生]、Fulfilled 加分未做[如跳过]、R9/R11 阻塞[如发生]）✓
