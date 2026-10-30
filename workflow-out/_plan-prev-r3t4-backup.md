# R3-T3 方案：E2 四节点委员会演示实跑与 §T3 回填（六阶段拆分①）

> 规划人：规划师（2026-10-30）。任务性质 = **单次实跑 + 证据回填**（用户任务陈述原文），主路径**零改码**（唯一常规代码面触碰 = demo.py 一行常量回填，预登记项）。
> **R3 全案已原样备份**：`workflow-out/_plan-prev-r3-backup.md`（本文件写入前 `cp` 逐字节备份；含终裁冻结条款六条、§3.4 判级阶梯、§3.5/§3.6 执行序原文）。本文引用其内容时标注「全案§x / 条款x」，原件在备份。
> 执行基线 = 当前工作树 = **T2 已交付态**（implementation.md:12：「本任务 = 代码改动 + 本文件（即 T2 的写码部分）」）。R3 代码 = `lyquid/src/committee_certified.rs`（新模块 433 行）+ `scripts/demo.py` `flow_committee`（:552-721）+ `agents/common/rpc.py` R3 面 + `lib.rs` 装配——均已随 R3 代码审查交付，**尚未部署任何含 e2_* 方法的新实例**（用户任务陈述前置事实；R2 实例 `Lyquid-tldda6zq…` @0xFD6F…c351 只有 probe 方法）。

---

## 0. 受影响文件清单（11 项，供审查员核对；#9–#11 为条件项，仅 fallback 触发）

| # | 文件 | 动作 | 时机/条件 |
|---|---|---|---|
| 1 | `workflow-out/plan.md` | 重建（本方案；旧 R3 全案 → #2 备份） | 已执行（本文件） |
| 2 | `workflow-out/_plan-prev-r3-backup.md` | 新建：R3 全案原样备份（终裁条款 + §3.4/§3.5/§3.6 原文存档，后续阶段引用指向此件） | 已执行（cp 逐字节） |
| 3 | `scripts/demo.py` | **一行常量回填**：`DEFAULT_INSTANCE = ""` → T3 deploy 实录实例名（demo.py:87；预登记项，全案§0-#4 / §6-T3） | T3.2（deploy 成功后） |
| 4 | `workflow-out/w1b2-r3-e2-committee.md` | §T3 回填（现占位「（待 T3 触发回填。）」:39-41）：判级结论 + console 摘录 + 读回勾稽 + 降级登记段[如有] + 日志清单 | T3.6 |
| 5 | `workflow-out/_r3-t3-deploy-raw.txt` | 新建：部署实录（T3.0 冻结面自证 + cp/md5 勾稽 + cargo check + shaker deploy + 实例名/地址 + TARGET 推导与断言） | T3.1 |
| 6 | `workflow-out/_r3-t3-committee-raw.txt` | 新建：`--flow committee` 主跑全 transcript | T3.3 |
| 7 | `workflow-out/_r3-t3-console-raw.txt` | 新建：console 原始全输出（**判级唯一依据**，非过滤行） | T3.4 |
| 8 | `workflow-out/_r3-t3-final-state-raw.txt` | 新建：终态勾稽（deal_info=Refunded + balance_of 三方 + misconduct 视图） | T3.5 |
| 9 | `lyquid/src/committee_certified.rs` | **条件**：`E2_AVG_NUM: u16 = 4` → `1`（:91 一行；仅 L1 fallback，条款 5 预登记；非冻结四件之一） | 仅 fallback |
| 10 | `workflow-out/_r3-t3-fb-deploy-raw.txt` | **条件**：fallback 第二轮 cp/deploy 实录（编码期常量改值需重部署） | 仅 fallback |
| 11 | `workflow-out/_r3-t3-fb-committee-raw.txt`、`_r3-t3-fb-console-raw.txt` | **条件**：fallback 重跑 transcript + console（L1 口径取证） | 仅 fallback |

**不改（冻结面/零触碰面，继承全案§0「不改」清单）**：`lyquid/src/types.rs`、`core.rs`、`committee.rs`、`assessor.rs`（冻结四件——本轮规划期已复验，见 §1-实跑 2）；`lyquid/src/lib.rs`、`agents/common/rpc.py`、`scripts/keeper.py`、`scripts/deploy.sh`/`devnet-up.sh`、`README.md`；`ACCESS_MATRIX` 本体；`--flow all` 序列与全部 sim 代码路径（demo.py:770-774 序列不含 committee；`DEFAULT_INSTANCE` 只被 committee 流消费——sim 字面零影响，无需 sim diff 门）。

---

## 1. 已采信前提（任务陈述前置事实 + 本轮规划期实跑核验）

**本轮规划期实跑（2026-10-30，撰写本方案时；命令与结果如实）**：

1. **七容器全 Up**：`docker ps --format "{{.Names}} {{.Status}}"` → multi-tools / node1-4 / registry / anvil 全部 `Up 13 hours`。环境就绪。
2. **冻结面核验通过**（主路径「实跑不改码」的起点自证）：`md5sum -c workflow-out/_r2-t0-frozen-baseline.txt` → types.rs / core.rs / committee.rs / assessor.rs 四行全 `OK`（附带 WARNING `1 line is improperly formatted` = 基线文件注释行的既有无害噪音，R2 同款）；`git diff --stat -- lyquid/src/{types,core,committee,assessor}.rs` → 仅 `assessor.rs | 5 +++++`（R1 已审在场改动，基线内）；HEAD=dc78d2f。
3. **T2 交付在场**：`git status` → `?? lyquid/src/committee_certified.rs`（未跟踪新文件）+ M `scripts/demo.py` / `agents/common/rpc.py` / `lyquid/src/lib.rs` / `lyquid/src/assessor.rs`（assessor 为 R1 遗留）。**如实登记**：`_r3-t0-*`/`_r3-t2-*` 日志不在 workflow-out（T0/T2 执行期未按全案§6 命名归档；本阶段不追溯补写）；风险由 RT1 的容器 cargo check 硬门兜住。
4. **R3 代码面完整核读**（本方案逐条依据）：`committee_certified.rs` 全文 433 行（七方法 + `E2_AVG_NUM`:91=4 + 全部 println 取证形态）；`demo.py:552-721` flow_committee 全读（全案§3.6 步骤 1–7 全部内建）；`rpc.py` R3 助手全读（§3 各命令形态逐一落地）。

**已采信（任务陈述前置事实 + 全案 P 项，不重证）**：

- **T1 完成**（w1b2-r3-e2-committee.md §T1）：th2 双签 / th4 四签聚合实证（`cert.signers RAW=[0,1,2,3] len=4`）；宿主 eth_call 直连 node2–4 三端口全通（11087/12087/13087）→ `docker_exec_cast` 降级**不需要**；GetNodeInfo×4 NodeID 与 S2 表一致（节点身份跨重启稳定，仍按当轮重取）。
- **P1 部署通道**：宿主 `MSYS_NO_PATHCONV=1 docker cp` → `multi-tools:/tmp/tb-lyquid` → md5 勾稽 → 容器内 `shaker deploy`（先例 `_r2-deploy-raw.txt:5/:7-14/:374`）；改 lyquid 码后必须重新 cp+deploy（fallback 即此）。
- **P2 读回纪律**：`status=="0x1"` ≠ 方法 Ok；一切效果以 `deal_info`/`balance_of` 读回复核；读回滞后一块，demo 内建重试（`wait_state`/`wait_for`）。**资金自足**：每 deal faucet + fund 前 `require_funds` 断言。
- **P3 println 证据通道**：instance 方法证据只走 **cast call**；network/instance println 走 `shaker console` 回放（取证源=node1、必须用实例名）。
- **P4 anvil 角色**（rpc.py:64-66/:97）：#0=broker=creator=部署钥（`0xac0974…2ff80`，rpc.py `ANVIL0_KEY`:97）、#1=alice、#2=bob。
- **P5 oracle 两阶段**：configure（creator 门）仅 staging → advance/finalize（平台内置，**只能 cast call**）→ 激活；**dest_epoch 是 finalize 的等待条件**（`get_epoch` finalize 前恒 0，勿用）；run_round cast call；内层 certified call 块内上链（非我方 tx）。
- **条款摘引（原件在备份）**：条款 1 = e2_configure 唯一通道 cast send；条款 4 = e2_arm 写 network 域 + 读回断言走 `e2_net_config()` 解码（console 回显仅佐证）+ run_round 维持 cast call 严禁 send；条款 5 = avg_num 编码期常量（首跑 4；fallback 改 1 须重新 cp/deploy）+ 仅 node1 单次触发 + L2 判据 = console 聚合行 inputs=4+signers=4 + 绝不以单签冒充四节点；条款 6 = TARGET=`shaker to-hex <实例名>`，断言非零且 ≠ 合约地址，入 `_r3-t3-*` 日志。

---

## 2. 目标与判级口径（诚实红线）

**目标**：把 T2 已交付的 flow_committee 在 multi devnet 部署**新实例**并**单次实跑**，取得「四节点委员会认证 → 全额退款」的完整链上证据链，按 L2/L1/L0 判级并回填 §T3。

**判级口径（全案§3.4 + 条款 5，冻结）**——判级只认 `_r3-t3-console-raw.txt` 原文行：

| 级 | 判据（console 原始行） | 处置 |
|---|---|---|
| **L2（目标）** | `e2_aggregate: agreed deal=… verdict=1 from 4 input(s) (avg_num=4)`（**inputs=4**）**且** `committee_verdict_certified: cert.signers RAW = […] (…, len=4)`（**signers=4**）+ 四条 `signer N -> Node-…` 映射行 | 直接回填 §T3 |
| **L1（预登记 fallback）** | inputs<4（表现：run_round false / aggregate 无 agreed 行 / `e2_propose:` 行数<4） | 改 `E2_AVG_NUM`=1（#9）→ 重新 cp/deploy（#10）→ **壳 40/40 复跑**（改 lyquid 码触发）→ 重跑取证（1 提案 + signers=4）→ §T3 显式降级登记 |
| **L0（平台硬限制）** | signers<4（T1 已实证排除该分支；如仍发生） | 三段式诚实报告：平台限制登记 + 单签 certified call 打通情况 + 路线①现状；**绝不以单签冒充四节点**（诚实红线） |

**本阶段不做（防范围蔓延；后续阶段另行发起，在此登记防丢失）**：对抗流 node 复跑（全案§6-T3 尾项/G3 尾项，顺延 T6 收尾）；T4 EVM 对照；T5 B3 备料；`_commit-plan.md` R3 分组与 `implementation.md` 增量（收尾；fallback 发生时降级登记**先落 §T3 证据文档**，implementation.md 偏离表同步留收尾阶段）。

---

## 3. 子任务拆分与执行顺序（T3.0 → T3.6）

> 通则：一切 docker 子进程命令带 `MSYS_NO_PATHCONV=1`（rpc.py:285-287 既有教训，Git Bash 路径改写）；所有原始日志以 `# command:` 头部行记录命令形态（先例 `_r2-normal-assess-raw.txt:3`）。

### T3.0 预检（零改码自证，入 `_r3-t3-deploy-raw.txt` 头部）

1. `docker ps` 七容器 Up（规划期已跑通过一次；执行期重跑入档）。
2. 冻结面复验（命令与判据同 §1-实跑 2）：`git diff --stat` 仅 assessor.rs +5；`md5sum -c workflow-out/_r2-t0-frozen-baseline.txt` 四 OK。
3. 声明入档：主路径不改任何 lyquid 源码（例外 = #3 demo.py 常量回填与条件项 #9，均预登记）。

### T3.1 部署新实例（→ `_r3-t3-deploy-raw.txt`；形态先例 `_r2-deploy-raw.txt`）

1. `docker exec multi-tools rm -rf /tmp/tb-lyquid`
2. `MSYS_NO_PATHCONV=1 docker cp lyquid/. multi-tools:/tmp/tb-lyquid`（先例 :5）
3. **md5 勾稽**：宿主 `md5sum lyquid/src/*.rs lyquid/Cargo.toml lyquid/Cargo.lock` vs `docker exec multi-tools md5sum /tmp/tb-lyquid/src/*.rs …` 逐文件 MATCH（形态 `_container-md5.txt`；**committee_certified.rs 必须在列**——新模块首次上容器，全案§0-#2 的实体核对点）。
4. 强制重编：`docker exec multi-tools sh -c "touch /tmp/tb-lyquid/src/*.rs"` + `docker exec -w /tmp/tb-lyquid multi-tools cargo check --target wasm32-unknown-unknown`（R2 教训：防指纹复用）。判据 = 末行 `Finished …`；已知无害噪音 = `{{project-name}}` error（ldk 模板固有，`_r2-deploy-raw.txt:20-21/:375` 同款，R2 仍 Finished+deploy 成功）。**无 Finished = blocked 如实上报**（本阶段无 lyquid 改码授权，不得现场修码，RT1）。
5. `docker exec -w /tmp/tb-lyquid multi-tools shaker deploy -r http://registry:8000/lyquids --endpoint ws://node1:10087/ws --private-key <ANVIL0_KEY，rpc.py:97> Cargo.toml`（先例 :374）→ 抓 `created Lyquid-<name> => 0x<addr>` 行（先例 :730）→ **实例名 + 地址入档**（§T3 回填与 #3 回填的数据源）。
6. **TARGET 推导与断言**（条款 6）：`MSYS_NO_PATHCONV=1 docker exec multi-tools shaker to-hex Lyquid-<name>` → 断言**非零且 ≠ 步骤 5 合约地址**；推导命令与输出值入档（T1 同款先例 `_r3-t1-target-raw.txt`；demo T3.3 还会内建断言一次，demo.py:580-586——双重独立取证）。

### T3.2 `DEFAULT_INSTANCE` 回填（demo.py:87，一行）

`DEFAULT_INSTANCE = ""` → `"Lyquid-<T3.1 实例名>"`。依据：全案§0-#4「缺省自 deploy 实录回填为脚本常量」。**不触发**壳 40/40（那是 lyquid 测试门，本行是 Python 常量）与 sim diff（`DEFAULT_INSTANCE` 仅 committee 流消费，demo.py:569/:730；`--flow all` 序列不含 committee，:770-774）。fallback 时回填**最终（fb）实例名**。

### T3.3 主跑（→ `_r3-t3-committee-raw.txt`）

单命令形态（全案§3.6 逐字；宿主 python 先例 `_r2-normal-assess-raw.txt:3`）：

```
python scripts/demo.py --node http://127.0.0.1:10087 --contract 0x<新实例地址> --instance Lyquid-<新实例名> --flow committee > workflow-out/_r3-t3-committee-raw.txt 2>&1
```

demo 内建步骤与用户任务陈述执行序 2–5 一一对应（demo.py:552-721）：

| 任务陈述步骤 | demo 落点 | 通道/纪律 |
|---|---|---|
| 2 配置 | :594-601 | `committee_config(NodeID×4, 4)`（broker 门，NodeClient）+ `e2_configure(bytes32[]×4, 4)`（**cast send**，条款 1；rpc.py:685-697）+ advance→dest_epoch 轮询→finalize（**cast call**，rpc.py:717-731；等待条件=dest 面，P5） |
| 3 争议单 | :615-638 | faucet(alice,10_000)→snapshot→`require_funds`（P2 资金自足）→create_deal→fund(alice)→**无交付**→notarize→open_dispute(alice)→wait Disputed（status 0x1 ≠ Ok，一切以读回为准） |
| 4 触发 | :640-669 | `e2_arm(deal_id)` **一次**（NodeClient `_send`，rpc.py:667-675）→ `e2_net_config()` 轮询断言 `armed_deal == deal_id`（15s 预算；空/旧值=pending 等；第三值=硬失配 abort；**绝不重 arm**，demo.py:641-658）→ `e2_run_verdict_round()` **仅 node1 单次、cast call**（rpc.py:699-710；**严禁 cast send**——S2 实证内层静默丢失；返回 false 即 RuntimeError 停，**绝不重触发**） |
| 5 终态轮询 | :671-698 | deal_info 至 Refunded（30s 预算；Disputed=pending；其他终态=abort）+ 余额勾稽（alice 回到 faucet 后基线、bob/broker 不变 = 全额退款）+ console 取证段（:700-713，过滤 8 键；0 行时打印手工补跑命令，不 fail） |

**执行纪律**：主跑**只跑一次**；任何 RuntimeError 都不得通过重跑绕过——异常即转 T3.4 判级/诊断分支（console 查因后按 §2 分支处置），异常 transcript 本身照常入档。

### T3.4 判级与 console 原始取证（→ `_r3-t3-console-raw.txt`）

1. **手工 console 全量取证**（判级唯一依据；demo 内建段只有过滤行，不够）：
   ```
   MSYS_NO_PATHCONV=1 timeout 60 docker exec multi-tools shaker console Lyquid-<实例名> --endpoint ws://node1:10087/ws > workflow-out/_r3-t3-console-raw.txt 2>&1; echo "rc=$?" >> workflow-out/_r3-t3-console-raw.txt
   ```
   （rc=124 = timeout 正常收尾，T1 先例 `_r3-t1-th2-console.txt`；取证源=node1、必须实例名，条款 2。）
2. 按 §2 判据表定级：
   - **L2 达成** → T3.5。
   - **inputs<4** → fallback（预登记，条款 5）：改 `E2_AVG_NUM`=1（#9，一行）→ 重复 T3.1 全部步骤（cp/md5/check/deploy/TARGET → #10 `_r3-t3-fb-deploy-raw.txt`）→ **壳 40/40 复跑**（改 lyquid 码触发：父目录 verify_core `cargo test --lib --tests` 只读复跑，判据 40/40）→ 冻结面复验（committee_certified.rs 非冻结四件，md5 门应仍四 OK）→ `DEFAULT_INSTANCE` 回填 fb 实例名 → 重跑 T3.3/T3.4（#11 fb 日志）→ L1 口径取证（1 提案 + signers=4）。
   - **signers<4** → L0 三段式（§2，诚实红线）。
   - **run_round false / 终态超时** → 先 console 查因：`e2_propose:` 行数（几个节点出了提案）、`e2_aggregate: REFUSE …` 行（拒证原因）。属 inputs 不足 → fallback；属提案不一致（`REFUSE — proposals disagree`，风险 R5 诚实语义）→ **不重触发**，如实登记并上报仲裁。

### T3.5 终态勾稽取证（→ `_r3-t3-final-state-raw.txt`）

独立于 demo transcript 的读回快照（P2 复核口径；NodeClient 只读，宿主 python 一次脚本或 `python -c`）：

1. `deal_info(deal_id)` → `state=Refunded`；
2. `balance_of(alice/bob/broker)` → 与 transcript 勾稽一致（alice==faucet 后基线、bob/broker 不变）；
3. **misconduct 不增实证**：console 的 `apply_verdict: deal=<id> verdict=1 misconduct=[]` 行（lib.rs:791 累计视图 println；demo console 过滤键含 `apply_verdict`，demo.py:702-703）。新实例首个裁决 + NotFulfilled 不 +1（Malicious 才 +1，P7）→ **`misconduct=[]` 即「不增」**；若非空 = 硬失配，如实登记上报。
4. （fallback 时对 fb 实例同套取证，并入本文件或 fb 段落。）

### T3.6 §T3 回填 + 收尾自检（→ `w1b2-r3-e2-committee.md`）

替换 :39-41 占位为 §T3 实录段（镜像 §T1 体例）：

1. **结论行**：判级（L2/L1/L0）+ 实例名/地址 + TARGET 值；
2. **console 摘录**（判级行原文）：`cert.signers RAW` 行、四条 `signer N -> Node-…` 映射行、`e2_aggregate: agreed … from N input(s)` 行、`apply_verdict: … misconduct=[]` 行；
3. **读回勾稽**：arm 读回断言行（`armed_deal == <deal_id>`）、Refunded、余额勾稽行、misconduct 不增；
4. **降级登记段**（如有）：fallback/L0 触发现象（首轮 console 证据）→ 处置（avg_num 改值 + 重部署 + 40/40）→ 最终口径；两实例对照登记；
5. **原始日志清单**：本阶段全套 `_r3-t3-*`。

**收尾自检**（入档声明）：冻结面复验同 T3.0（fallback 后另附 40/40=40/40 在档）；日志交叉核对（§T3 引用的每个日志文件都在 workflow-out）；**未执行任何 git commit/add/push**；主路径 lyquid 源零改动（`git diff` 佐证；fallback 时唯一改动 = `E2_AVG_NUM` 一行并登记）。

---

## 4. 逐文件改动点（#3/#4/#9 的具体 diff 面）

- **`scripts/demo.py:87`**：`DEFAULT_INSTANCE = ""` → `DEFAULT_INSTANCE = "Lyquid-<T3.1 实录实例名>"`（一行；:82-86 注释块已预埋回填说明，核对后无需改）。
- **`workflow-out/w1b2-r3-e2-committee.md:39-41`**：占位「（待 T3 触发回填。）」→ §T3 实录段（结构见 T3.6；§T1 段落 :1-35 不动）。
- **（条件）`lyquid/src/committee_certified.rs:91`**：`const E2_AVG_NUM: u16 = 4;` → `const E2_AVG_NUM: u16 = 1;`（仅此一行；:87-90 注释已预登记 fallback 语义，不改；改后必须重 cp/deploy——常量编译进 wasm）。

---

## 5. 风险与回退（编号登记，执行员逐条知晓）

| # | 风险 | 缓解/回退 |
|---|---|---|
| RT1 | 容器 cargo check 失败（T2 未留容器编译在档实证，`_r3-t2-*` 不在档） | T3.1-4 硬门；无 Finished = **blocked 如实上报**（本阶段无 lyquid 改码授权，不得现场修码）；诚实登记，不绕过 |
| RT2 | deploy 后 advance false / dest_epoch 不涨（staging/target 不匹配） | TARGET 断言重查；重试 advance 一次（全案 R8：失败重试一次后登记）；仍败 = 如实登记上报 |
| RT3 | arm 读回 15s 超时（读路径滞后一块，P2） | demo 内建轮询；超时 = 手动再读 `e2_net_config()` 入档佐证；**绝不重 arm**（重复 arm 违反「一次」纪律且可能覆盖已 armed 的 deal） |
| RT4 | run_round false（inputs<4 / aggregate 拒证 / oracle 未激活） | **不重触发**（多次触发 = 多独立回合，首回合已把 deal 推离 Disputed，core.rs:199 门必败）；console 查因定分支（fallback L1 / 诚实登记上报）；demo :666-669 已内建停 |
| RT5 | 终态 30s 超时停 Disputed（内层 certified call 晚块上链） | 手动延轮询 deal_info 入档；仍 Disputed = console 查因如实登记；**绝不重触发 run_round** |
| RT6 | console 0 行（replay 窗口/relay 时机） | demo 已内建手工补跑提示（:709-713）；T3.4 手工全量取证一次；仍 0 行 = 如实登记——transcript 在但判级依据受损，按可得证据诚实定级并注明缺口 |
| RT7 | fallback 后第一实例残留（Disputed 单挂着） | 无资金风险（每 deal faucet 自足）；§T3 登记两实例，**判级以 fb 实例为准**，`DEFAULT_INSTANCE` 回填 fb 实例名 |
| RT8 | 资金纪律违例 | demo 内建 `require_funds`/snapshot/终态勾稽（:622-624/:688-698）；异常即 abort 不绕过 |
| RT9 | devnet 漂移（容器已 Up 13h） | GetNodeInfo×4 当轮重取内建（demo.py:588-592；禁硬编码，全案§3.3）；NodeID 跨重启稳定已证（T1）；任一端口不可达即 fail-closed（rpc.py:399） |

---

## 6. 阶段收口门禁 GT3（全部实跑取证）

| 门 | 判据 |
|---|---|
| GT3-a | `_r3-t3-deploy-raw.txt` 在档：T3.0 冻结面自证 + md5 全 MATCH（含 committee_certified.rs）+ cargo check `Finished` + `created Lyquid-… => 0x…` 行 + TARGET 推导与断言（非零且 ≠ 合约地址） |
| GT3-b | `_r3-t3-committee-raw.txt` 在档：arm 读回 OK 行 + run_round 单次（transcript 仅一次调用）+ Refunded + 余额勾稽 OK |
| GT3-c | `_r3-t3-console-raw.txt` 在档且含判级行（signers RAW / aggregate inputs）；§2 判级结论可从原文直接读出 |
| GT3-d | §T3 回填完成（结论/摘录/勾稽/日志清单）；fallback 或 L0 时降级登记段在（fb 日志在档） |
| GT3-e | 冻结面收尾复验同 T3.0 通过；fallback 时另加壳 40/40=40/40 在档 |
| GT3-f | 全程未执行 git commit/add/push；主路径 lyquid 源零改动（git diff 佐证；fallback 时唯一改动 = `E2_AVG_NUM` 一行并登记） |
