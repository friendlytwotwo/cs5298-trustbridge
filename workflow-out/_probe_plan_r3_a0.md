# R2 方案：对抗流 devnet 全链 E2E + keeper 驱动超时流 + W2' 正常流收尾

> 规划人：规划师（2026-10-29）。执行基线 = 当前工作树（含未提交 R1 改动，**严禁回退**；R1 清单见 `workflow-out/_commit-plan.md` §2 C1–C4）。
> 阶段依据：`../FinalProject_阶段重排_2026-10-27.md` §1 R2（窗口 10-30–11/5）。
> R1 方案已备份为 `workflow-out/_plan-prev-r1-backup.md`（本文件按 R2 重建）。
> 实现说明纪律（任务陈述）：`implementation.md` 必须分节区分「R1 已审改动」与「R2 新增改动」，审查聚焦后者。

---

## 0. 受影响文件清单（供审查员核对，共 12 项）

| # | 文件 | 动作 | 持久性 |
|---|---|---|---|
| 1 | `lyquid/src/lib.rs` | **路线① wire 改造**：`open_dispute` 加 `export = eth`（仅属性行）；`apply_committee_verdict` 签名扁平化 `(deal_id, verdict_code: u8, signers: Vec<AgentId>)` + `export = eth`，体内由扁平参数构造 `CommitteeCertWire` 后**逐字沿用**现有校验/裁决/写回链；Ok 路径追加一条 misconduct println（取证用，先例 fund 的 deal_view println）；注记面五处更新（模块头 :35-36、通道注记 :229-230、:444-445、ACCESS_MATRIX :190 行内注释、:510-513 备查注记） | **持久** |
| 2 | `agents/common/rpc.py` | `_ABI` 新增 `apply_committee_verdict(string,uint8,string[])` 行（selector 容器 `cast sig` 实取后冻结，先例 R1 T3）；`NodeClient.apply_committee_verdict` 由 raise 改为实装（保持 demo 现有**域三元组调用形态不变**，包装层做同源根预检 + wire 扁平化，`sender` 缺省回落 `caller`）；:103-105 排除注记改写 | **持久** |
| 3 | `scripts/demo.py` | `flow_adversarial` 增 node 分支（身份/发送方矩阵 + 地址制委员会 + **自带资金面**（分支头 faucet 10_000 + 每单 fund 前 balance 断言）+ Malicious 主场景 + Fulfilled/NotFulfilled 对照场景，对照仅 node）；`new_assessed_deal` node 分支改走链上 `assess_brief`（回放模式，sim 分支原样）；移除 `--flow adversarial` node 门控（横幅/exit 2/`all` 序列收窄）；docstring 同步 | **持久** |
| 4 | `scripts/keeper.py` | **预计零改动**（循环/nudge/枚举/读回 R1 已备，本轮纯执行；若执行期证明确需微调，须登记偏离后再动） | 预计零 |
| 5 | `workflow-out/w1b2-r2-keeper-timeout.md` | 新建：目标 A 证据（keeper 循环 transcript 六要素表 + 块号/deadline 归因段（＝块扫描列表）+ due_deals 非空附录（deal X，留置 id 登记）+ nudge 产块轨迹） | 交付物 |
| 6 | `workflow-out/w1b2-r2-adversarial.md` | 新建：目标 B 证据（部署/md5 勾稽、Malicious→Refunded+misconduct +1、NotFulfilled→Refunded+misconduct 不增（计数前后对照）、Fulfilled→Settled、余额勾稽、偏离表） | 交付物 |
| 7 | `workflow-out/w1b2-r2-normal-assess.md` | 新建：目标 C 证据（链上 assess(replay)→create→…→Settled 一条龙 + cast call 通道取证） | 交付物 |
| 8 | `workflow-out/_r2-*.txt` | 新建：原始日志（预计 9–13 个：**t0-frozen-baseline（冻结门比对源，G4/G5b/G7 共用）**、t0-sim-baseline、deploy、wire 探针、keeper-loop、due-nonempty、adversarial、console、normal、assess-castcall、终态复核） | 交付物 |
| 9 | `workflow-out/_commit-plan.md` | **增补** R2 主题分组（C5–C7 建议序列，不执行 git commit） | 交付物 |
| 10 | `workflow-out/implementation.md` | 重建：门禁总表（**G4/G5b/G7 行按冻结门新口径**：三文件 vs HEAD 空 + 四文件 md5=T0 基线）+ 「R1 已审改动 / R2 新增改动」分节 + 遗留清单 | 交付物 |
| 11 | `workflow-out/_pre-task-snapshot-r2.patch` | 新建：T0 工作树快照（事故恢复凭据，仅 patch 不 stash） | 自保 artifact |
| 12 | `workflow-out/plan.md` | 本方案（旧案备份见文件头） | 交付物 |

**不改**：`lyquid/src/types.rs`、`core.rs`、`committee.rs`、`assessor.rs`（R2 零触碰——壳 40/40 挂载面 = types/core/committee/assessor，D8 口径，任何一个**相对 T0 基线**的新 diff 都会动摇壳基线）；`lyquid/Cargo.toml`；`agents/alice.py`/`bob.py`/`broker.py`/`llm.py`/`protocol.py`；`scripts/keeper.py`（见 #4）；`README.md`（规划期 grep 核实：README 无 "adversarial/sim-only/对抗" 字样，对抗流 sim-only 状态从未写入 README，R2 无需更新；grep 零命中实录见 §2-6）；`../workflow-out/verify_core/`（壳只读复跑）。**冻结门语义澄清（仲裁意见 1）**：assessor.rs 处于「R1 已改、R2 零触碰」态，其 vs-HEAD diff 非空（恰 `+5`，DealBrief derive）属预期——冻结门语义＝自 T0 基线（`_r2-t0-frozen-baseline.txt`）起不变，**非**对 HEAD 为空。

---

## 1. 已采信前提（任务陈述 + R1 存档，规划不重证）

- **P1 部署通道**：宿主 `docker cp`（**必须 `MSYS_NO_PATHCONV=1`**，R1 偏离登记 §3-2：路径转换曾致旧码假通过）→ `multi-tools:/tmp/tb-lyquid` → md5 勾稽 → 容器内 `shaker deploy -r http://registry:8000/lyquids --endpoint ws://node1:10087/ws --private-key 0xac0974…2ff80 Cargo.toml`（cwd=/tmp/tb-lyquid）。**每次 deploy 全新实例新地址**（同源三 deploy 得两个 digest，R1 implementation.md §3-3），故 R2 改码后必然 redeploy 到**新实例**，R1 实例 `0x4091…D849` 留作存档不再触碰。
- **P2 写通道语义**：`eth_sendTransaction` 无 gas 字段；`status=="0x1"` = 已上链序 **≠ 方法 Ok**（平台吞 Err）——一切效果以 `deal_info`/`balance_of` 读回复核（rpc.py 模块 docstring :24-29；keeper.py:22-25）。读路径滞后一个块已实测（R1 偏离 §3-4），demo/keeper 均内建 5×0.4s 读回重试。
- **P3 通道注记遗产**：shaker 虚拟主机 HTTP 面只服务 `export = http` 的 instance 方法（W1-A 探针）；网络方法走 eth 面（`export = eth`）经 cast/NodeClient；**未导出方法 = FuncNotFound**（w1b2-s4-rpc.md §B-④h 实测）——这就是 open_dispute/apply_committee_verdict 至今链上不可达的机制原因。
- **P4 身份与守卫**：链上 buyer/seller/broker/委员会身份 = anvil 地址字符串（EIP-55），`require` 比较 `ctx.caller.to_string()`（lib.rs:198-214）；角色地址表在 rpc.py:64-66（BROKER_ADDR/ALICE_ADDR/BOB_ADDR；任务陈述"用前核实"→ R1 已核实入档 w1b2-s4-rpc.md §A-0/§B-②，规划期复核见 §2-5）。node 侧"私钥"= 发送方地址选择，Python 不持钥。
- **P5 println 证据通道**：instance 方法（assess_brief）证据走 **cast call**（R1 立下的唯一通道，w1b2-r1-s3-assess.md）；network 方法 println（fund 的 deal_view、deal_info 的 JSON）走 `shaker console` 回放（R1 `_r1-console-fund-raw.txt` 实证可读）。
- **P6 timeout 换算**：`timeout_slots = max(1, est_ms×2/400)`（types.rs:195-197 口径，R1 方案 D7）——est=200ms ⇒ 1 slot。automine 下产块 = 落一笔交易（nudge = 零额 faucet，rpc.py:289-297）。
- **P7 壳基线**：40/40 = 33(lib) + 5(escrow) + 2(modelcheck)，挂载面 types/core/committee/assessor，**lib.rs 不挂载**（R1 方案 D8）——R2 只动 lib.rs，壳字面不受影响的机制保证。
- **P8 任务陈述两处与工作树不符（规划期核实，编码员按本方案口径执行）**：
  1. "ACCESS_MATRIX 加行"——**两行已存在**（lib.rs:189-190），R2 只更新 :190 行内注记（wire 形态从"结构体/无 eth 面"改为"R2 扁平 eth 面"），不加行。
  2. "open_dispute/apply_committee_verdict 现刻意不 eth"——属实（lib.rs:446/:463 均裸 `#[method::network]`），但 `open_dispute(string,string)` 的 **_ABI 行已在**（rpc.py:87，selector `a48ab911`，W1-B2 冻结）——open_dispute 只差 lib.rs 属性行，wire 侧零新增。

---

## 2. 本轮规划期新实证（规划师 2026-10-29 实读/实跑，编码员须知晓）

1. **路线① 的全部 ABI 类型均有 EthAbiType（ldk v0.8.1 源读）**：`ldk/lyquid/src/runtime/ethabi.rs`
   - 裸 `u8`：`impl_eth_abi_uint!(u8, 8, "uint8")`（ethabi.rs:258-276 宏 + 末尾四个落地：u64/u32/u16/u8）——**u128 不在列**（只有 alloy 包装 U64/U128/U256，ethabi.rs:218-260），这正是 W1-B2 R1#1 balance_of 边界的机制根源，也反证 u8 安全；
   - `String`：ethabi.rs:311；`Vec<T>`：`impl<T: EthAbiType> EthAbiType for Vec<T>`（ethabi.rs:395）。
2. **路线① 的活体先例（比源读更强）**：`create_deal` eth 面已带裸 `fee_bps: u16` + `est_confidence: u8` 参数（lib.rs:256-267），R1 在链上实际创建过 deal-1/2/3（R1 implementation.md §2 T5/G4/G5）——**裸 u8 走 eth wire 在本平台版本已有生产性实证**；`committee_config(string[],uint32)` 的 `Vec<AgentId>` 参数同样 eth 导出（lib.rs:515-516）且 R1 node 模式每跑必调（demo.py:328）。
3. **调用面清点（grep 实跑）**：`apply_committee_verdict`/`open_dispute` 的 Python 调用点**仅 demo.py**（demo.py:278/:290；rpc.py 为定义处）；Rust 侧 lib.rs 两方法无任何 crate 内调用者（core.rs 命中全为 core::open_dispute 自身测试）——签名扁平化波及面 = lib.rs 定义处 + rpc.py 包装 + demo.py 调用点，三处全部在本方案清单内。
4. **FakeNode 域三元组形态**（rpc.py:583-625）：`cert = (verdict_code, evidence_root, signers)`，root 由调用侧折叠传入，FakeNode 内对自身证据镜像复核（同源校验的镜像）；Fulfilled→Settled+分账、Malicious→Refunded+misconduct 已对齐 core（rpc.py:611-624）。**保持该接口不变**即可让 demo 对抗流 sim 路径零改动。
5. **工作树基线核实**（`git status`/`git log` 实跑）：HEAD `dc78d2f`，R1 改动 = 6 个 M 文件（README/rpc.py/assessor.rs/lib.rs/demo.py/keeper.py）+ implementation.md/plan.md + workflow-out 未跟踪件，与 `_commit-plan.md` §1 一致。快照 patch 必含全部 M diff。
6. **README 无对抗流状态面**：`grep -n -i -E "adversarial|sim-only|对抗" README.md` 零命中——"对抗流 sim-only"从未写入 README，R2 上链后无需回改（README 不入清单）。
7. **core 裁决语义钉死**（core.rs:182-235）：`open_dispute`：Funded|Submitted → Disputed（core.rs:182-186）；`apply_verdict`：仅 Disputed 可入（:199），Fulfilled → 结算分账、NotFulfilled/Malicious → 全额退款，Malicious 独占 `misconduct[seller] += 1`（:206）；`validate_cert`（:235）= 根匹配 + 阈值 + 成员 + 去重四查。DealState 七态见 types.rs:35-49；deal_info 的 state 字符串 = debug 格式（"Disputed"/"Refunded"/"Settled" 可直接读回，lib.rs DealView :734-757）。
8. **R1 证据里的 brief JSON 形态**（w1b2-r1-s3-assess.md:82）：`{"buyer_profile_digest":"b","seller_profile_digest":"s","terms_digest":"t","license_scope":"online-video,12mo,EU"}`——字段名即 assessor.rs:45-50 DealBrief 四字段；回放模式（空 base_url/api_key）返回固定 `{"qualification_score":75,"risks":["heuristic-mode"],"est_duration_ms":60000,"est_confidence":40}`（R1 implementation.md §2 T3 实录）⇒ est 60000ms → timeout_slots=300，正常流不等 deadline，时序安全。

---

## 3. 目标 / 非目标

**目标**（对应任务 A/B/C）：
- **A（keeper 驱动超时流 E2E）**：`keeper.py` 以**循环模式**（非 `--once`）、显式 `--deals` 只盯新 Funded 短估算 deal **Y**：自动 nudge 产块 → 过 deadline → 自动 `claim_timeout` → `Refunded` + 余额复核 + 块号/deadline 归因（自 keeper 启动至 Refunded 的产块全部来自其自身交易）；另以独立 deal **X** 链上复现 `due_deals` **非空**返回（R1 遗留，R1 implementation.md §4；X/Y 分单，保归因干净）。
- **B（对抗流 devnet 全链）**：路线①（§4）打通后，node 模式跑伪造交付全链：create→fund→卖方 submit（伪造 digest）→买方 open_dispute→broker committee_config（≥threshold 成员）→apply_committee_verdict **Malicious** → `Refunded` + misconduct 计数取证；**Fulfilled 对照** → `Settled`；**NotFulfilled 第三场景** → `Refunded` + misconduct **不增**（println 累计视图与 Malicious 裁决后计数同值）。
- **C（W2' 正常流全 E2E）**：demo `--node --flow normal` 扩展为 assess(**链上回放**)→create→fund→submit→complete→`Settled` 一条龙，S3 证据沿用 cast call 通道。
- 交付三件套：`w1b2-r2-*.md` + `_r2-*.txt`；`_commit-plan.md` R2 增补；`implementation.md` 更新（分节 + 门禁总表 + 遗留清单）。

**非目标**：不做 oracle certified call（路线②延后，理由 §4-3）；不动 types/core/committee/assessor；不新增/删除任何 escrow 方法（方法清单冻结，misconduct 取证走 println 而非新 getter，理由 §6-1）；不做真实 LLM 端到端（无凭据 + egress 拒私网，维持回放，任务陈述明示）；不改 agents/*.py；不清理历史实例（0x1c85…/0xA4899D…/0x4091… 均存档）；不执行任何 git commit/add/push。

---

## 4. B 通道抉择：**路线①（export=eth + wire 参数扁平化）**，路线② 延后至 R3/E2

### 4.1 决定

`open_dispute`：仅加属性 `#[method::network(export = eth)]`（参数 `(DealId, Digest)` = `(String, String)`，_ABI 行已在 rpc.py:87）。
`apply_committee_verdict`：签名 `(ctx, deal_id: DealId, cert: CommitteeCertWire)` → `(ctx, deal_id: DealId, verdict_code: u8, signers: Vec<AgentId>)` + 加 `export = eth`；体内第一行由扁平参数构造 `CommitteeCertWire { verdict_code, signers }`，其后 caller/成员校验、`into_domain`（root 仍由链上证据日志折叠，读-算-校同源不变）、misconduct std 桥、`apply_payout` **逐字不动**。`CommitteeCertWire` 结构体与 `into_domain` 保留（committee.rs 零改动，壳不受扰；serde 面继续服务潜在 native/probe 调用）。

### 4.2 平台机制证据表（审查员把守项）

| 证据 | 来源 | 强度 |
|---|---|---|
| 裸 u8 有 EthAbiType | ethabi.rs:258-280（`impl_eth_abi_uint!(u8,8,"uint8")`） | 平台源 |
| 裸 u8 走 eth wire 活体先例 | create_deal 的 `est_confidence: u8`（lib.rs:256-267），R1 链上实建 deal-1/2/3（R1 implementation.md §2 T5） | **链上实测** |
| Vec\<AgentId\>（=string[]）有 EthAbiType | ethabi.rs:395 | 平台源 |
| Vec\<String\> 活体先例 | committee_config(string[],uint32)（lib.rs:515-516），R1 node 模式每跑必调（demo.py:328） | **链上实测** |
| String 参数 | ethabi.rs:311；全 eth 面通用 | 平台源 |
| 未导出方法 FuncNotFound（现状机制） | w1b2-s4-rpc.md §B-④h | 链上实测 |
| 参数个数安全边界 | 扁平后 3 参数（string+uint8+string[]），远低于 solc Stack-too-deep 的 6×string 实测边界（R1 方案 D3 / w1b2-claim-probe-evidence.txt §2） | 链上实测 |
| 编译期兜底 | T5 容器 `cargo check --target wasm32-unknown-unknown` 不过即停、不部署 | 流程门 |

### 4.3 路线② 延后理由（不是否定，是排期）

1. **语义非零改**：certified call 的签名域是 `Vec<SignerID>`（u32 序号，w1b1-s2-oracle.md §4 形态表），与现行 AgentId 成员域需新映射层——与任务纪律"语义零改"冲突；路线①才满足。
2. **机制可用但流程重**：S2 已证 multi 可用（cert_probe 全回合），但激活依赖 configure→advance→finalize 两阶段（w1b1-s2-oracle.md §3），且 advance/finalize **只能 cast call 通道**（cast send 静默丢内层提交，§3-3）——整套编排属生产路径移植。
3. **阶段表已排**：committee.rs:12-18 明记生产路径 TODO(W4)；`FinalProject_阶段重排` §1 把"4 节点委员会演示（E2）"排在 **R3**（11/6–11/12）。R2 塞入②会挤压 11/5 窗口且引入与"对抗流跑通"目标无关的新风险面。
4. 路线①落地后，`apply_committee_verdict` 的守卫链（成员+签名+阈值+根）原样在线，②未来只替换"证书如何到达"，不动裁决语义——升级路径不被①堵死。

---

## 5. 子任务拆分与执行顺序

> 顺序即依赖序：T1–T3 是同一改动的三层（Rust wire → Python 包装 → 编排），门（G1a/G2a/G3a）不过即停，不进 T5。T5 redeploy 后才有新实例，T6 全部证据跑在新实例上。

### T0 基线与快照
1. `git -C trustbridge diff > workflow-out/_pre-task-snapshot-r2.patch`（恢复凭据；须含全部 M 文件 diff，与 §2-5 清点勾稽）。
2. **冻结文件 T0 基线**（产出 `workflow-out/_r2-t0-frozen-baseline.txt`，G4/G5b/G7 三门的比对源）：
   ```
   $ git diff --numstat lyquid/src/types.rs lyquid/src/core.rs lyquid/src/committee.rs lyquid/src/assessor.rs
   $ md5sum lyquid/src/types.rs lyquid/src/core.rs lyquid/src/committee.rs lyquid/src/assessor.rs
   ```
   两条输出**原文入档**。**自检断言**：前三文件 numstat 为空行；assessor.rs 恰为 `5 0`（= R1 C1 的 DealBrief derive 增量，对照 `_commit-plan.md` §2 C1；lib.rs:613 的 `serde_json::from_str` 依赖该 derive 在场）。规划期已实跑复核：`git diff --numstat <四文件>` 仅出 `5 0 lyquid/src/assessor.rs` 单行，其余三文件空——编码员 T0 复跑须得同形。
3. **G0 门**：父目录壳 `cd ../workflow-out/verify_core && cargo test --lib --tests` → **40/40**（33+5+2）；`python scripts/demo.py --selftest` → 7/7；`python scripts/demo.py --sim --flow all` 三流 transcript 存 `_r2-t0-sim-baseline-raw.txt`（**T4/T7 逐字比对基准**；预期含 `misconduct={'agent-bob': 1}` 行）。
4. 环境：`docker ps`（7 容器 Up）；对 R1 实例 `0x4091…D849` 只读探活一次（`cast call balance_of`，证明栈活，不动其状态）；`env | grep -i "TB_LLM"` 预期空（真实 LLM 门维持关闭）。

### T1 lib.rs wire 改造（路线①核心）
逐点见 §6-1。**G1a 门**：本地 AST 级自查（属性拼写、参数顺序）；真正编译门在 T5 容器（wasm 目标本机无环境）。

### T2 rpc.py 包装层
逐点见 §6-2。**G2a 门**：`python -c "import ast; ast.parse(open('agents/common/rpc.py',encoding='utf-8').read())"`；`_ABI` 新行 selector 先占位、待 T5 cast sig 回填冻结（**占位期间严禁跑 node 模式**）。

### T3 demo.py 编排层
逐点见 §6-3。**G3a 门**：AST parse；`--sim --flow all` 与 T0 基线**逐字一致**（sim 路径零改动的证明）。

### T4 本地回归总门（部署前）
`--selftest` 7/7 + sim 逐字一致 + `grep -rn "ADVERSARIAL_BANNER|sim-only" scripts/demo.py` 零命中（门控拆除干净）+ **冻结门（新口径）**：三文件（types/core/committee）`git diff` 为空，且四文件 md5 与 `_r2-t0-frozen-baseline.txt` 逐项一致（`md5sum -c`）。

### T5 容器构建 + redeploy + wire 探针（新实例）
1. `docker exec multi-tools rm -rf /tmp/tb-lyquid` → `MSYS_NO_PATHCONV=1 docker cp lyquid/. multi-tools:/tmp/tb-lyquid` → **md5 勾稽**（宿主 vs 容器，lib.rs 必列；R1 §3-2 教训：不勾稽不采信）。
2. `docker exec -w /tmp/tb-lyquid multi-tools cargo check --target wasm32-unknown-unknown` → 零 error（**G5a 门**；不过即回 T1，禁止部署）。
3. **G5b（冻结门新口径）**：三文件（types/core/committee）`git diff` 为空，且容器内四文件 md5 与 `_r2-t0-frozen-baseline.txt` 逐项一致（基线文件 `docker cp` 入容器后 `md5sum -c`；兼证 cp 后容器源 = T0 基线源）。
4. `docker exec -w /tmp/tb-lyquid multi-tools shaker deploy -r http://registry:8000/lyquids --endpoint ws://node1:10087/ws --private-key <anvil#0> Cargo.toml` → 记录新 LyquidID + 合约地址（**R2 实例**，此后所有证据用新地址；demo/keeper 显式 `--contract`）。
5. wire 探针（**G5c 门**，容器内 cast，transcript 存 `_r2-deploy-raw.txt`）：`cast sig "apply_committee_verdict(string,uint8,string[])"` → selector 回填 rpc.py 冻结；`cast sig "open_dispute(string,string)"` 对照 rpc.py:87 既有 `a48ab911`；`cast call "balance_of(string) returns (uint128)" <BROKER_ADDR>` → 可读；`cast call "due_deals(uint64) returns (string[])" 0` → 合法空数组（路由性）。
6. （对照探针，预期"失败"取证）`cast send "apply_committee_verdict(string,uint8,string[])" "deal-nope" 0 '[]'` → status 0x1 但 deal 不存在——复证 P2"0x1≠Ok"，同时证明 wire 面已路由（P3 的 FuncNotFound 已消除）。

### T6 E2E 证据跑（新实例，三目标三份证据）

> **资金自足纪律（总则）**：T6-A/B/C 各证据臂**自带 faucet 注资**，禁止依赖任何前序子运行的链上余量（同一新实例上余量虽跨运行留存，也不得计入资金来源）；各臂注资额与预算说明（含 deal X 留置锁定的 1_000）登记进对应证据 md。每次 fund 前 `balance_of(alice)` 读回断言（≥ amount，否则停并记档）——fund 的余额不足是**静默 Err**（lib.rs:332-335 预检 Err 被平台吞掉、tx status 仍 0x1，rpc.py:24-29），不得依赖 deal_info 的 deadline_slot=None 事后暴露。

**T6-A 目标 A（keeper 循环 + due_deals 非空）**——双 deal（X/Y）分工，归因隔离是设计点：
1. **deal X = due_deals 取证专用**：`python -c` 驱动（R1 §2 T5-3 同款手法，复用 rpc.py）：`faucet(alice, 10_000)`（**足额注资**，沿用 demo.py:196 flow_normal 先例；faucet 无守卫、累加制，lib.rs:241-252）→ `create_deal(est_ms=200)` → **fund 前断言 `balance_of(alice) ≥ 1_000`**（资金门，T6 总则；不足即停并记档）→ `fund(alice)` → 读回取 deadline_slot（5×0.4s 重试）→ 手动 `node.nudge()` 推块**过 deadline**（"产块后重读"纪律）→ `node.due_deals()`（缺省 now=当前块）→ **非空含 deal X** → `_r2-due-nonempty-raw.txt`（同文件留过块前空/过块后非空对照）。**X 取证后留置不 claim，其 deal id 登记进证据文档**（收尾可由 alice `cancel` 回收或补一笔 `claim_timeout`，动作与本目标归因无关，登记即可；**X 留置锁定 1_000 计入本臂预算**：10_000 ≥ X 1_000 + Y 1_000 + 余量）。
2. **deal Y = keeper 驱动专用**：同一驱动脚本新建 deal Y（est_ms=200）→ **fund 前断言 `balance_of(alice) ≥ 1_000`**（步 1 注资 10_000 已覆盖 X 留置 1_000 + Y 1_000；不足即停并记档）→ `fund(alice)` → 读回取 `deadline_slot`（= funded_slot+1）→ **记录当前块高**（归因基准）。
3. 起 keeper **循环**，**必须显式 `--deals deal-Y`、禁用缺省枚举**——keeper.py:154 缺省走 `discover_deals`，会枚举到 X 并在首轮先 claim X，其 nudge/claim 交易先产块，污染 Y 的归因。命令：后台 `python scripts/keeper.py --node http://127.0.0.1:10087 --contract <新地址> --deals deal-Y --interval 5`（无 `--once`、默认 nudge on）。
4. 轮询 `deal_info(Y)` 至 `Refunded`（预计 1–2 轮：keeper 首轮 nudge 产块至 deadline、同轮 claim 放行——guard 语义为 `now ≥ deadline`，core.rs:173-174）→ 停 keeper；`balance_of(alice)` 复核全额回流。
5. **归因证据（块扫描路线）**：keeper transcript 不可作 tx 级归因源——keeper.py:106-109 的 nudge 只打静态行且丢弃 `node.nudge()` 回执（rpc.py:297 的 `nudge()` 不返回 receipt），`_r1-keeper-nudge-raw.txt:9-10` 实证 transcript 只有 claim hash。改由外层驱动脚本做块扫描：
   a) **探针**：步 2 起 keeper 前，驱动先 `eth_getBlockByNumber("latest", true)` 一次，确认返回含 `input` 的完整 tx 对象，**探针结果入档**；若不可得则退化路线：`eth_getBlockByNumber(n, false)` 取 tx hash 列表 → 逐 hash `eth_getTransactionByHash` 取 from/to/input；
   b) 记录 `start_block` 后起 keeper；Refunded 读回后对 `(start_block, 终块]` **逐块取 tx**，按 `from` = keeper sender 且 `input` 前 10 字节归属：`0xb540def8` = faucet(nudge)、`0x786cfc8f` = claim_timeout（两 selector 已冻结于 rpc.py:75/:85）；逐块列表写入 `_r2-keeper-loop-raw.txt` 归因段；
   c) **归因判据**：窗口内每块恰一笔 tx 且全部归属 keeper 两 selector（automine 一 tx 一块，P6）——证明自 keeper 启动至 Refunded 的产块全部来自 keeper 自身交易、期间无操作者交易，「循环驱动过 deadline」归因成立；
   d) **扫描窗口须在 deal X 的收尾动作（cancel/claim）之前关闭**，操作者交易不得落入窗口。
   keeper.py 维持零改动；块扫描由外层 `python -c` 驱动脚本承担（§6-4）。
6. `_r2-keeper-loop-raw.txt` 必含：`[keeper] explicit deals: ['deal-Y']` 行、`nudge: zero-value faucet sent` 行、claim 轮 tx hash、`"action": "claimed"`、读回复核、**块号/deadline 归因段**。
**门 G6A**：六要素齐——循环模式（非单发）+ nudge 产块 + 自动 claim + Refunded + due_deals 非空（deal X）+ 块号/deadline 归因段在场（deal Y）。

**T6-B 目标 B（对抗流三场景）**：`python scripts/demo.py --node http://127.0.0.1:10087 --contract <新地址> --flow adversarial`，一次运行含三场景（编排见 §6-3）：
- Malicious 主场景取证链：`deal_info` 状态阶梯 Funded→Submitted→**Disputed**（open_dispute 生效的直接读回证据）→**Refunded**；`balance_of` 买方全额回流；misconduct 走 apply_verdict 的 println（`shaker console` 回放取证，P5 通道）；
- Fulfilled 对照：Disputed→**Settled** + 卖方入账分账勾稽（fee = amount×fee_bps/10⁴）；
- **NotFulfilled 第三场景**：第三单同 wire 同编排形状（伪造 digest 同 Malicious 场景），cert `(1, root, signers)` → 预期 **Refunded** + alice 全额回流 + bob/broker 余额不变。**misconduct 对照点**：§6-1 的 println 每个 Ok 路径都打行且为**累计视图**，NotFulfilled 的证据不是「无行」，而是其 println 中 misconduct 计数**不增**（与 Malicious 裁决后计数同值）——console 取证须带 deal id 与计数前后对照；
- transcript 存 `_r2-adversarial-raw.txt` + console 侧 `_r2-adversarial-console-raw.txt`。
**门 G6B**：三裁决终态——`Refunded`[Malicious，misconduct +1] / `Refunded`[NotFulfilled，misconduct 不增] / `Settled`——全取证 + 状态阶梯含 Disputed。

**T6-C 目标 C（正常流一条龙）**：`python scripts/demo.py --node … --flow normal`（node 分支已改链上 assess）：`assess_brief(replay)` 证据行（报告 JSON）→ create（est 取链上报告）→ fund → submit → complete → `Settled` + 余额勾稽（alice −1000 / bob +980 / broker +20）；另取 **cast call 直证**一份（R1 唯一通道纪律）：`docker exec multi-tools cast call … "assess_brief(string,string,string,string) returns (string)" '<demo 同款 brief>' '' '' ''` → 与流内报告逐字段一致。transcript 存 `_r2-normal-assess-raw.txt` + `_r2-assess-castcall-raw.txt`。
**门 G6C**：一条龙含链上 assess 步 + cast call 直证同源 + Settled + 勾稽。

### T7 终验回归
壳 40/40 复跑；sim `--flow all` 与 T0 逐字一致复跑；**冻结门（新口径）**：三文件（types/core/committee）`git diff` 为空 + 四文件 md5 与 `_r2-t0-frozen-baseline.txt` 逐项一致（`md5sum -c`）；`grep -rn "sim-only" scripts/ agents/` 零命中；全部 `_r2-*.txt` 与证据 md 引用勾稽（引用的日志都在档）。

### T8 交付件收尾
`w1b2-r2-*.md` ×3 成文（每份：命令原文、输出要素表、偏离登记）；`_commit-plan.md` 增补 §5 R2 组（C5 = lib.rs 路线① wire + 注记；C6 = rpc.py/demo.py 对抗流与 assess 接线 + 门控拆除；C7 = R2 证据与文档；依赖 C1–C4 先行；仍不执行 commit）；`implementation.md` 重建（§R1 已审改动引 _commit-plan C1–C4 不重述 / §R2 新增改动逐文件 / 门禁总表 G0–G7 / 遗留清单）。

---

## 6. 逐文件改动点

### 6.1 `lyquid/src/lib.rs`（T1）

1. **`open_dispute`（:446-458）**：属性 `#[method::network]` → `#[method::network(export = eth)]`，行内注记："R2 路线①：对抗流上链；参数 (String,String) 全 ABI 兼容，_ABI 行 W1-B2 已冻结（rpc.py:87）"。签名/体零改动。
2. **`apply_committee_verdict`（:463-508）**：
   - 属性 → `#[method::network(export = eth)]`；
   - 签名：`cert: committee::CommitteeCertWire` → `verdict_code: u8, signers: Vec<AgentId>`；
   - 体首插一行构造：`let cert = committee::CommitteeCertWire { verdict_code, signers };`（其后整段逐字沿用：require(Committee) → caller∈signers → entries 取日志 → into_domain 折叠根 → misconduct std 桥 → core::apply_verdict → Ok 写回 → apply_payout）；
   - **Ok 路径追加一条 println（本方案唯一函数体新增）**：`apply_payout` 成功后 `lyquid::println!("apply_verdict: {} misconduct={}", deal_id, view)`（view = state.misconduct 迭代成的 `"k:v,…"` 串或 Vec debug，实现取简）。**正当性**：misconduct 无 getter 且方法清单冻结（不得新增方法），println 是既有观测缝（fund 的 deal_view lib.rs:347-352、deal_info lib.rs:544 双先例）；println 非共识状态、零语义影响；
   - 文档注释更新：wire 形态说明（扁平参数 → 体内构造 wire 结构 → into_domain 折叠，读-算-校同源不变）+ 诚实边界（扁平 wire 仍无签名，demo 占位性质未变，真实 oracle 认证 TODO(W4)）。
3. **注记面五处**：模块头 :35-36（"deliberately stay non-eth" → "R2 起两者均 eth（①扁平 wire）；oracle 认证 TODO(W4)"）；通道注记块 :228-230（"未列入者"句改历史记录：W1-B2 曾刻意不 eth 化，R2 路线①解除，指向本 plan）；:444-445 W1-B2 注记同步改写；ACCESS_MATRIX :190 行内注释更新（"wire 无签名为 demo 占位" → "R2 起扁平 eth wire（verdict_code+signers），仍无签名、真实认证 TODO(W4)"）；:510-513 committee_config "本导出仅备查"注记更新（R2 起对抗流实调）。

### 6.2 `agents/common/rpc.py`（T2）

1. `_ABI` 新行：`"apply_committee_verdict(string,uint8,string[])": ("<cast-sig 实取>", ("string", "uint8", "string[]"), None)`——编码器已支持 uint8/string[]（rpc.py:142-161），零扩展；:103-105 排除注记改写为 R2 口径（结构体 wire 已扁平化 + selector 冻结来源）。
2. `NodeClient.apply_committee_verdict`（:386-395）实装，**保持域三元组接口**：
   ```python
   def apply_committee_verdict(self, deal_id, cert, caller=None, *, sender=None):
       verdict_code, cert_root, signers = cert
       # 同源根预检（镜像链上 into_domain 折叠；root 过期早失败，省一笔必败交易）
       if evidence_root(self.evidence_entries(deal_id)) != cert_root:
           raise RuntimeError("committee cert evidence_root mismatch (client-side precheck)")
       self._send("apply_committee_verdict(string,uint8,string[])",
                  (deal_id, int(verdict_code), list(signers)),
                  sender or caller or self.sender)
       return True   # 与 notarize/claim_timeout 同款"回执无返回值"不对称注记
   ```
   `sender or caller` 回落使 demo 既有形态 `node.apply_committee_verdict(deal_id, cert, <principal>)` 在 node 模式直接成立（principal=BROKER_ADDR 即发送方，守卫 caller∈members ∧ caller∈signers 命中）。
3. `FakeNode` **零改动**（rpc.py:583-625 域三元组接口保持——两传输同形态是 sim 输出零回退的结构保证）。

### 6.3 `scripts/demo.py`（T3）

1. **门控拆除**：删 `ADVERSARIAL_BANNER`（:57-58）与 main() node 分支横幅/exit 2（:318-323）；node 的 `--flow all` 序列改 `["normal","timeout","adversarial"]`（:332，与 sim 对齐）；docstring :16-18 门控段改写为"对抗流 R2 起上链（路线①扁平 wire）"。
2. **`flow_adversarial` node 分支**（sim 分支 :267-293 逐字不动）：
   - 身份：`alice, broker, bob = role_ids(node)` 替代 ALICE/BROKER/BOB 常量；发送方按既有矩阵（fund/open_dispute→alice、submit_deliverable→bob、create/faucet→默认 #0）经 `call(..., sender=)`；
   - **资金面（node 分支自带）**：分支开头 `faucet(alice, 10_000)`（同 demo.py:196 先例）；三单每单 fund 前各加 `balance_of(alice) ≥ 1_000` 断言（资金门，T6 总则）。资金链依据：Malicious/NotFulfilled 走 `Payout::full_refund` → alice 各回流 1_000（types.rs:156）；**Fulfilled 走 `Payout::settle`，`refund_to_buyer: 0`**（types.rs:165-173，:170）——apply_payout 只触发 seller/broker 两 credit 分支（lib.rs:685-689），buyer 退款分支（lib.rs:691-693）不执行 → alice 对该单 0 回流，故第三单 fund 前必须有分支内自筹余量。sim 分支 demo.py:267 的 `faucet(ALICE, 1_000)` 属逐字范围、**原位不动**（防 sim transcript 中 alice 余额打印漂移破坏 G3a/T4 逐字比对）；
   - 委员会（node）：`committee = [BROKER_ADDR] + COMMITTEE[1:]`（= [broker 地址, node-1..3]；链上成员只是字符串集合，node-1..3 不呼叫仅占位；signers = committee[:THRESHOLD] 含 BROKER_ADDR——caller∈members ∧ caller∈signers ∧ len=3≥threshold 全中）；main() 的 `committee_config` 按模式取 sim 名单或地址名单；
   - cert 折叠：`entries = node.evidence_entries(deal_id)`（两传输同接口）→ `cert = (2, evidence_root(entries), signers)` → `node.apply_committee_verdict(deal_id, cert, broker)`（§6-2 包装自动扁平化发送）；
   - **Malicious 主场景**终态打印（node 版）：状态阶梯（Disputed→Refunded）+ alice 余额复核 + misconduct 提示行指向 console 取证；
   - **Fulfilled 对照（仅 node）**：第二单 create→fund→submit（**合规** deliverable digest）→ alice open_dispute → cert `(0, root, signers)` → 终态 `Settled` + bob/broker 分账勾稽。目的：同一条 apply_committee_verdict wire 上裁决三态映射（core.rs:191-235）的链上正反对照，避免"只会退款"的单边证据；
   - **NotFulfilled 第三场景（仅 node）**：第三单 create→fund→bob submit（**伪造** digest，同 Malicious 场景形状）→ alice open_dispute → cert `(1, evidence_root(entries), signers)` → apply_committee_verdict → 断言终态 `Refunded` + alice 全额回流 + bob/broker 余额不变；misconduct 取证口径见 §5 T6-B（println 累计视图**计数不增**，console 带 deal id 与计数前后对照；core.rs:203-210 递增仅在 Malicious 分支）。（三对照场景均仅 node；sim 分支仍逐字不动，G3a/T4 逐字比对不受影响。）
3. **`new_assessed_deal` node 分支（目标 C）**：sim 分支（get_llm 回放，:172-174）逐字不动；node 分支改：
   ```python
   brief = json.dumps({"buyer_profile_digest": sha256(f"profile:{alice}"),   # 确定性摘要即可
                       "seller_profile_digest": sha256(f"profile:{bob}"),
                       "terms_digest": terms_digest,                          # §2-8 四字段契约
                       "license_scope": "online-video,12mo,EU"}, sort_keys=True)
   rep = node.assess_brief(brief)          # 回放模式：空 base_url/api_key（rpc.py:424-441）
   print(f"assess_brief (on-chain, mode=replay): {rep}")   # node-only 证据行
   ```
   est 取 `rep["est_duration_ms"]/["est_confidence"]`（回放固定 60000/40 → timeout_slots=300，§2-8）；`terms_digests()` 前移到 assess 之前（brief 内嵌 terms_digest）——sim 分支求值顺序同步前移但**输出不变**（digest 计算无副作用）。
4. docstring 同步（对抗流 node 可用 + assess 双通道说明）。

### 6.4 `scripts/keeper.py`
零改动（§0-#4）。T6-A 全用既有面：`--interval 5` 循环 + **显式 `--deals deal-Y`**（禁用缺省枚举——keeper.py:154 的 `discover_deals` 会枚举到 deal X，理由见 §5 T6-A 步 3）、默认 nudge、`_send` 直取回执、读回复核。块扫描归因（eth_getBlockByNumber 逐块取 tx + selector 归属，替代不可行的 tx-hash 逐笔回执路线，见 §5 T6-A 步 5）由外层 `python -c` 驱动脚本承担——keeper.py:106-109 的 nudge 只打静态行且 :159-162 的轮循环不打印块号/不回传 nudge 回执，故维持零改动。

---

## 7. 风险与回退

| # | 风险 | 概率/影响 | 缓解与回退 |
|---|---|---|---|
| R1 | 扁平 wire 意外编译失败（宏 codegen 边角） | 低/中 | §4-2 证据表覆盖全部类型+活体先例；T5a cargo check 门不过即回 T1 修（如 u8 需换 U8 边界转换——U128 同款先例 lib.rs:241-252——属等价回退位，语义仍零改） |
| R2 | selector 冻结错 | 低/高 | T5 cast sig 实取回填 + 回执 LyteLog 交叉核对（R1 §B-⓪ 手法）；rpc.py 占位期间禁跑 node 模式 |
| R3 | sim 输出漂移 | 低/高 | 结构保证：FakeNode 零改动 + demo sim 分支逐字不动 + 两传输同调用形态；T4/T7 两次逐字比对门 |
| R4 | status 0x1 假成功（守卫拒绝被吞） | 中/中 | 全部效果走 deal_info/balance_of 读回；apply 失败时 deal 停留 Disputed 即暴露；NodeError 原文入证据 |
| R5 | misconduct println 取不到（console 缓冲怪癖） | 中/低 | P5 先例（fund println 已证可读）；若不可读：证据降级为 Refunded+余额+core 单测（misconduct 计数 core.rs:206 有测试覆盖），偏离如实登记，不伪造 |
| R6 | due_deals 取证与 keeper 驱动同单混跑致归因污染 | 低/中 | T6-A 双 deal 分工：due_deals 用 deal X 先取证后留置不 claim；keeper 显式 `--deals deal-Y` 只盯 Y（缺省枚举会带上 X，禁用）；块扫描归因（逐块取 tx + selector 归属）佐证 |
| R7 | 委员会配置/签名集不匹配致 gate 拒绝 | 中/低 | §6-3 成员/签名集已对守卫逐条核算；失败时 NodeError 原文定位，一次修正重跑预算 |
| R8 | 新旧实例地址混用（R1/R2 证据串栈） | 低/高 | R2 全部命令显式 `--contract <新地址>`；证据 md 首行记录实例地址+LyquidID；R1 实例只读不动 |
| R9 | keeper 后台循环管理（Windows/Git Bash） | 低/低 | 后台起、轮询 deal_info 至终态即停；异常时 transcript 仍在档，可一次重试 |
| R10 | 配额中断 | 中/— | T0 快照 patch + 步骤化断点续跑；任一门失败即停在该门，不带着未过门的状态进下一步 |

**回退总纲**：代码层——本轮全部改动可由 `_pre-task-snapshot-r2.patch` 反向恢复（R1 改动本就在基线内，回退不伤 R1）；链上层——shaker 每次新实例，旧实例不受新部署影响；无任何不可逆操作（不 commit、不动 R1 实例、不删档）。

---

## 8. 证据与交付物规划

| 交付 | 内容要点 |
|---|---|
| `w1b2-r2-keeper-timeout.md` | keeper 循环 transcript 六要素表（循环非单发/nudge 行/claim tx/Refunded/余额复核/**块号-deadline 归因段（归因段＝块扫描列表）**）+ due_deals 非空前后对照（deal X，留置 id 登记）+ 偏离登记位 |
| `w1b2-r2-adversarial.md` | 部署记录+md5 勾稽表；Malicious 场景状态阶梯（含 Disputed 读回）+ misconduct console 原文；Fulfilled 对照 Settled+分账勾稽；NotFulfilled 场景 Refunded+misconduct 不增对照（println 计数前后同值，带 deal id）；路线①机制证据表引用（§4.2） |
| `w1b2-r2-normal-assess.md` | 一条龙 transcript（链上 assess 证据行→Settled）+ cast call 直证同源对照 + 余额勾稽 |
| `_r2-*.txt` | **t0-frozen-baseline（冻结门比对源）** / t0-sim-baseline / deploy / wire 探针 / due-nonempty / keeper-loop / adversarial(+console) / normal-assess / assess-castcall / 终态复核（md 引用的每个日志都在档） |
| `_commit-plan.md` 增补 | §5 R2 组 C5（lib.rs wire）/ C6（rpc+demo 接线与门控拆除）/ C7（证据与文档），含"依赖 C1–C4 先行"提醒；**不执行 commit** |
| `implementation.md` | 「R1 已审改动」节（引 _commit-plan C1–C4，不重述）+「R2 新增改动」节（逐文件）+ 门禁总表（G0/G1a/G2a/G3a/G4/G5a-c/G6A-C/G7；**其中 G4/G5b/G7 行按冻结门新口径写**：三文件 vs HEAD 空 + 四文件 md5=T0 基线）+ 遗留清单（oracle ②、真实 LLM、**Fulfilled/NotFulfilled 的 sim 面仍缺**等如实列出） |

---

## 9. 纪律对照表（任务陈述逐条落点）

| 纪律 | 落点 |
|---|---|
| 壳 40/40 | T0/T7 两时点；机制保证 = 壳挂载面不含 lib.rs（P7）；四冻结文件 T0 基线比对门 T4/T5b/T7 三查；assessor.rs 对 HEAD 的 +5 是 R1 已审改动、必须持续在场（lib.rs:613 依赖该 derive），不得回退 |
| types.rs/core.rs 零改动 | §0 不改清单 + T0 基线冻结门；misconduct 桥维持 lib.rs 现状（lib.rs:494-505 不动） |
| MSYS_NO_PATHCONV=1 + md5 勾稽 | T5-1（P1 教训） |
| status 0x1 ≠ 成功，读回执复核 | T5-6 对照探针 + 全 E2E 的 deal_info/balance_of 门 |
| instance println 只走 cast call | T6-C cast call 直证（assess_brief）；network println 走 console（P5） |
| due_deals 非空需产块后重读 | T6-A 步 1（deal X：nudge 过 deadline → 读 → 非空） |
| 不执行 git commit | 全程；`_commit-plan.md` 仅建议 |
| 实现说明分节（R1 已审 vs R2 新增） | §8 implementation.md 结构 |
