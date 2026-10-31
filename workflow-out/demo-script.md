# TrustBridge 预录 demo 分镜脚本（D3）

> 方案出处：`workflow-out/plan.md` §4（R4-D2+D3，审查通过）。本文件 = 方案 §0 清单 #6。
> 目标片长：**305 秒 = 5 分 05 秒**（方案判据 5±1 分钟 = 240–360 秒，见 §7）。
> 录制前提：单机 7 容器 devnet 在位（`multi-*`），或走 §5 预案 A 的「全实录回放模式」。
> 纪律摘要（§6）：**绝不重复 `e2_arm` / `e2_run_verdict_round`（单次纪律）**；
> Git Bash 下 docker 路径必带 `MSYS_NO_PATHCONV=1`；演示实例与证据实例不混称。

**读法**：分镜表五列（镜号 / 画面 / 命令 / 预期输出 / 时长），命令与预期输出一律给
「出处文件:行」；占位符 `<addr>` / `<实例名>` / `<ANVIL0_KEY>` 的替换规则在 §3 逐一列明
（占位符属「录制时替换」，不是虚构）。逐字命中校验记录见
`workflow-out/_r4d2d3-verify-raw.txt`（§9）。

---

## 1. 分镜表（8 镜，合计 305 秒）

| 镜号 | 画面 | 命令（逐字，带出处） | 预期输出（对齐实录，带行号） | 时长 |
|---|---|---|---|---|
| **S0** | 标题卡：幻灯片 P1 全屏（题目 / 日期 / 基线 HEAD） | —（纯口播） | —（画面即 P1：`2026-10-30`、`8d093b5`） | 20s |
| **S1** | 终端 A：devnet 自检 | `docker ps --format "{{.Names}} {{.Status}}"`（形态出处 `implementation.md:443`（R3 版，`git show 8d093b5:workflow-out/implementation.md` 取回），§7.2 T3.0 同型命令） | 7 行 `Up`：`multi-tools` / `multi-node1-1` / `multi-node2-1` / `multi-node3-1` / `multi-node4-1` / `multi-registry-1` / `multi-anvil-1`（`_r3-t4-precheck-raw.txt:5-:12`，表头 :5 + 7 行容器） | 20s |
| **S2** | 终端 A：部署新实例（主路径）/ to-hex（备路径） | ① `docker exec multi-tools rm -rf /tmp/tb-lyquid`（`_r3-t3-deploy-raw.txt:57`）② `MSYS_NO_PATHCONV=1 docker cp lyquid/. multi-tools:/tmp/tb-lyquid`（`:58`）③ `MSYS_NO_PATHCONV=1 docker exec -w /tmp/tb-lyquid multi-tools cargo check --target wasm32-unknown-unknown`（`:125`）④ `MSYS_NO_PATHCONV=1 docker exec -w /tmp/tb-lyquid multi-tools shaker deploy -r http://registry:8000/lyquids --endpoint ws://node1:10087/ws --private-key <ANVIL0_KEY> Cargo.toml`（`:59` 形态；该行密钥已脱敏为 `0xac0974...ff80`，全钥见 §3） | 主：`created Lyquid-<新名> => 0x<新地址>`（`:85` 形态）+ `[deploy exit=0]`（`:86` 逐字）备：`docker exec multi-tools shaker to-hex <实例名>`（`:581`）→ 42 字符地址；T3 实录值 `0xc05034ED5191cbc3404956D9b7dFcC7391e99bfc`（`:582`，断言行 `:584`） | 40s |
| **S3** | 终端 A：正常流一条龙（**新部署实例实跑**） | `python scripts/demo.py --node http://127.0.0.1:10087 --contract <addr> --flow normal`（命令形态出处 `_r2-normal-assess-raw.txt:3`；`<addr>` = **S2 当轮新部署实例地址**） | `FLOW 1 — normal: assess -> escrow -> deliver -> settle`（`_r1-demo-normal-raw.txt:3`）→ `deal=deal-1 info={… 'state': 'Qualified' …}`（`:5`）→ `final state=Settled balances: alice=9000 bob=980 broker=20`（`:6`）→ `DEMO COMPLETE`（`:9`）。⚠ **禁引** `_r2-normal-assess-raw.txt:12-:13`（已用实例 deal-9，余额非零起点：该实例已有历史流水，数字量级与零起点实例不同） | 60s |
| **S4** | 终端 A：keeper 超时退款（**实录回放镜**，字幕「本镜为已档实录回放（2026-10-29 R2-T6-A 轮）」） | **无执行命令**（画面 = 打开并讲解 `_r2-keeper-loop-raw.txt` 原文）。出处命令（讲解行，**不执行**）：`python scripts/keeper.py --node http://127.0.0.1:10087 --contract <addr> --deals deal-3 --interval 5`（`:3` 形态；实例地址逐字见 `:2` 与 `:7`） | `[keeper] explicit deals: ['deal-3']`（:6）→ `[keeper] watching ['deal-3'] every 5s`（:8）→ `[keeper 23:39:22] deal-3: {"state": "Refunded", "action": "claimed", …}`（:10）→ `ATTRIBUTION VERDICT: PASS`（:30）→ 归因两行（:31-:32） | 45s |
| **S5** | 终端 A×2（分屏/快切）：E2 委员会认证 + console 判级 | ① **主命令**（`_r3-t7-dt31-verify-raw.txt:3`，去掉 `# command: ` 前缀）：`python scripts/demo.py --node http://127.0.0.1:10087 --contract 0x942ED2fa862887Dc698682cc6a86355324F0f01e --instance Lyquid-dpp6ird6knahaun6dokpi6ki2pdnbjxdfunqa --flow committee`② `MSYS_NO_PATHCONV=1 timeout 60 docker exec multi-tools shaker console Lyquid-ybidj3krshf4gqcjk3m3px6mooi6tg74twwaa --endpoint ws://node1:10087/ws`（`_r3-t3-console-raw.txt:2`，只读流式回放） | ① `[committee] faucet read-back OK: alice 0 -> 10000 (+10000)`（:22）→ `arm read-back OK: armed_deal == deal-1 (pre-arm='')`（:28）→ `final state=Refunded balances after={'alice': 10000, 'bob': 0, 'broker': 0}`（:30）→ `refund check OK: … 10000 -> 9000 (after fund) -> 10000 (after verdict); bob/broker unchanged`（:31）→ `DEMO COMPLETE`（:69）→ `EXIT=0`（:72-:73）② `agreed … from 4 input(s) (avg_num=4)`（console:24）+ `cert.signers RAW = [0, 1, 2, 3]`（:31）+ `apply_verdict: deal=deal-1 verdict=1 misconduct=[]`（:36）+ `"state":"Refunded"`（:38） | 60s |
| **S6** | 表格画面（幻灯片 P6 全屏，无终端） | —（数据画面） | 创建 gas `1,936,008` vs `3,843,041` / `3,707,457`（`r3-t4-contrast-report.md:180-:187`）；代码量 `407` vs `2083` / `1323` 与 `2933` / `2173`（`:60-:83`）；负对照 `non-member signer` rc=1（`:104`、`:232`） | 40s |
| **S7** | 收尾卡（报告封面画面 + 口播） | —（纯口播） | 指引：12 页报告 `workflow-out/report/trustbridge-final-report.pdf` + 证据索引 `workflow-out/report/README.md` §5 | 20s |
| **合计** | — | — | — | **305s ≈ 5 分 05 秒**（判据 240–360s，§7） |

**实例说明**：S1–S3 主路径 = **新部署实例实跑**——命令序列照实录形态，实例名 / 合约地址 /
TARGET 每轮不同，分镜表逐处注明「以当轮输出为准」；金额 / 状态 / 判级行逐字可对。
**S4 例外**：主路径即**实录回放**——keeper 的 `claimed` 是 R2 轮一次性链上事件，deal-3 已
terminal（`_r2-keeper-loop-raw.txt:11-:13` 三条 `"action": "terminal"`；`w1b2-r2-adversarial.md:148`
「deal-1..3 Refunded（超时/keeper）」），重跑只得 terminal；新实例无到期 deal，且
`scripts/demo.py` 的 timeout 流在 node 模式自行 `nudge` + `claim_timeout`
（`scripts/demo.py:346-:357`：`while … node.nudge()` + `call(node, "claim_timeout", d)`）不留待
keeper，故**不设实跑 setup 镜**。
**S5 例外**：主路径 = 命令行展示 + **T7 实录输出回放**（T7 实例 deal-1 已终态，且受
arm/run_round 单次纪律约束，不对该实例重发；若要当轮实跑须换**新实例**执行同型命令）。

---

## 2. 分镜小节（口播要点 + 操作分解）

### S0 标题卡（20s）
- **口播**：一句话定位——「TrustBridge 在 Lyquid 上做一层 A2A 交易信任桥：资金托管、超时退款、
  委员会裁决都由链上强制执行，四个阶段的实跑证据都在仓库里。」接着交代基线
  `8d093b5` 与日期 `2026-10-30`。
- 画面：幻灯片 P1；右下角小字「本片为 devnet 实跑 + 已档实录回放（逐镜标注）」。

### S1 devnet 自检（20s）
- **口播**：「先确认运行环境：7 个容器全 Up——工具容器、四个 Lyquid 节点、registry、anvil。
  这个检查对应我们每轮实验的 T0 预检，7 个容器齐了才开工。」
- 操作：终端 A 执行 `docker ps --format "{{.Names}} {{.Status}}"`（形态出处
  `implementation.md:443`（R3 版，`git show 8d093b5:workflow-out/implementation.md` 取回））；输出与 `_r3-t4-precheck-raw.txt:5-:12` 同形（7 行 `Up`，
  容器名带 compose 后缀 `-1`）。
- 实录原文（表头 + 首行，逐字；`_r3-t4-precheck-raw.txt:5`、`:6`）：

```
CONTAINER ID   IMAGE                                     COMMAND                   CREATED      STATUS        PORTS                                             NAMES
848dda2bd63d   ghcr.io/lyquor-labs/lyquor-tools:v0.8.1   "sleep infinity"          5 days ago   Up 15 hours                                                     multi-tools
```

### S2 部署新实例（40s；备路径 = to-hex + created 行）
- **口播**：「每轮演示都从新实例开始，避免在已用实例上重复 arm。先把源码拷进工具容器、
  编译一次，然后 `shaker deploy`——注意 deploy 的 registry 与 node 端点是容器内网地址。」
- 主路径命令（逐字，见分镜表）：① `rm -rf /tmp/tb-lyquid`（`_r3-t3-deploy-raw.txt:57`）
  ② `docker cp lyquid/. multi-tools:/tmp/tb-lyquid`（`:58`）③ `cargo check --target
  wasm32-unknown-unknown`（`:125`）④ `shaker deploy …`（`:59`）。
- 预期输出（形态）：`Status: created`（`:80`）、`created Lyquid-<新名> => 0x<新地址>`（`:85`）、
  `[deploy exit=0]`（`:86`）；实录实例行：`Lyquid ID: Lyquid-ybidj3krshf4gqcjk3m3px6mooi6tg74twwaa`（`:81`）、
  `Contract: 0x87006e75a5B6bE9D1bbF61AC8Cd84f05D9140589`（`:82`）。
- **备路径（40 秒讲不完时）**：跳过 ①②③，只演示 `docker exec multi-tools shaker to-hex
  <实例名>`（`:581`）与 `created` 行，并口播「完整部署日志见 T3 实录」；to-hex 形态 42 字符：
  `0xc05034ED5191cbc3404956D9b7dFcC7391e99bfc`（`:582`，断言 `:584`：非零且 ≠ 合约地址）。

### S3 正常流一条龙（60s）
- **口播**：「正常流走完 assess → 托管 → 交付 → 结算四步。这是我们 R1 的第一次正常流，
  三个数——`alice=9000`、`bob=980`、`broker=20`——正好守恒：9000 + 980 + 20 = 10000。
  9000 是买方付掉托管金之后的余额，980 是卖方净得（扣 2% 手续费），20 是 broker 费。」
  口播必须点出 **R1 三数口径**（`w1b2-r1-demo-normal.md:29、:79`）。
- 操作：`python scripts/demo.py --node http://127.0.0.1:10087 --contract <addr> --flow normal`
  （形态出处 `_r2-normal-assess-raw.txt:3`）；`<addr>` = S2 当轮新部署实例地址
  （该实录 `:2` 的 `0xFD6F…c351` 为**已用实例，禁填**）。
- 预期输出（三条，逐字；编码期静态命中 R1 档 `_r1-demo-normal-raw.txt:5`、`:6`、`:9`，
  录制当轮再以新实例实录为准）：

```
deal=deal-1 info={'id': 'deal-1', 'buyer': '0x70997970C51812dc3A010C7d01b50e0d17dc79C8', 'seller': '0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC', 'amount': 1000, 'state': 'Qualified', 'timeout_slots': 300, 'deadline_slot': None}
final state=Settled balances: alice=9000 bob=980 broker=20
  DEMO COMPLETE
```

  （`DEMO COMPLETE` 实际在 banner 内，行首有缩进；逐字见 `_r1-demo-normal-raw.txt:9`。）
- **条件分支**：若 S2 走「复用已 Up 实例」快路径，S3 余额**不得**引 R1 的 9000/980/20，
  必须以当轮实例实录为准（该实例已有历史流水，余额量级不同）。
- ⚠ **禁引**：`_r2-normal-assess-raw.txt:12-:13` 是已用实例输出（deal-9，余额非零起点，
  只含该实例的累计流水），不得作为 S3 新实例的预期来源。

### S4 keeper 超时退款（45s；实录回放）
- 画面：打开 `_r2-keeper-loop-raw.txt`，字幕「本镜为已档实录回放（2026-10-29 R2-T6-A 轮）」。
- **口播**：「超时退款这一环由 keeper 守门人兜底。这里展示的是 R2 轮的一次性链上事件：
  keeper 每 5 秒轮询，自己发一笔零值 faucet 把块挖过 deadline，下一块送 `claim_timeout`，
  deal 从 Funded 变 Refunded。后面的归因扫描证明窗口内没有操作者交易——只有 keeper 的两笔。」
- 出处命令（**讲解用，不执行**）：`python scripts/keeper.py --node http://127.0.0.1:10087
  --contract <addr> --deals deal-3 --interval 5`（`:3` 形态）；该轮实例地址逐字见 `:2`
  （`0xFD6F7A6a5c21A3f503EBaE7a473639974379c351`）与 `:7`（`contract=0xFD6F…c351`）。
- 预期输出（逐字，`_r2-keeper-loop-raw.txt`）：

```
:6   [keeper] explicit deals: ['deal-3']
:8   [keeper] watching ['deal-3'] every 5s (guard decides; submissions are free)
:10  [keeper 23:39:22] deal-3: {"state": "Refunded", "action": "claimed", "tx": "0x4095005c0e72c139fb99f630d8e20b7ef005596a88dfac8b1fec8717cd5ada02"}
:30  ATTRIBUTION VERDICT: PASS — every block in (212, 214] carries exactly one tx, all from the keeper sender and all one of the two keeper selectors (nudge=faucet 0xb540def8 / claim_timeout 0x786cfc8f).
:31  => the block that crossed deal-3's deadline (213) was mined by the keeper's own nudge,
:32     so 'keeper loop drove the timeout' holds with no operator tx inside the window.
```

- 讲解补充：`:11-:13` 三条 `"action": "terminal"` 说明该 deal 已终态、重跑无新事件（这正
  是本镜走回放的原因）；`:36` 读回 `balance alice=19000 bob=0 broker=0`。

### S5 E2 委员会认证 + console 判级（60s）
- **口播**：「最后一环是四节点委员会的认证裁决。`e2_configure` 先把 4 个 NodeID 和
  threshold=4 写进 staging，再 advance / finalize epoch 激活；然后 arm 一次、node1 触发一次，
  4 个节点各自提案、聚合成一个证书。资金侧：`10000 → 9000 → 10000`——9000 只是托管金
  锁定的中间态，裁决 NotFulfilled 后全额退回 10000，卖方和 broker 一直是 0。」
  口播必须点出 **funding 中间态口径**（`w1b2-r3-e2-committee.md:98`、`_r3-t7-dt31-verify-raw.txt:31`）。
- ① 主命令（T7 实录，`_r3-t7-dt31-verify-raw.txt:3` 去掉 `# command: ` 前缀）：
  `python scripts/demo.py --node http://127.0.0.1:10087 --contract 0x942ED2fa862887Dc698682cc6a86355324F0f01e --instance Lyquid-dpp6ird6knahaun6dokpi6ki2pdnbjxdfunqa --flow committee`
- ① 预期输出（逐字，`_r3-t7-dt31-verify-raw.txt`）：

```
:22  [committee] faucet read-back OK: alice 0 -> 10000 (+10000)
:28  [committee] arm read-back OK: armed_deal == deal-1 (pre-arm='')
:30  [committee] final state=Refunded balances after={'alice': 10000, 'bob': 0, 'broker': 0}
:31  [committee] refund check OK: alice 10000 -> 9000 (after fund) -> 10000 (after verdict); bob/broker unchanged
:69    DEMO COMPLETE
:72  # EXIT: DEMO COMPLETE banner printed (last statement of main()); no traceback;
:73  # python exit code observed as 0 (EXIT=0 printed by the tee wrapper).
```

  （`:69` 的 `DEMO COMPLETE` 在 banner 内，行首有缩进。）
- ① **可选**「T3 档回放」画面（**不执行**，完整命令单行逐字如下，出处 `_r3-t3-committee-raw.txt:2`）：
  `python scripts/demo.py --node http://127.0.0.1:10087 --contract 0x87006e75a5B6bE9D1bbF61AC8Cd84f05D9140589 --instance Lyquid-ybidj3krshf4gqcjk3m3px6mooi6tg74twwaa --flow committee`
  若展示该档，**必须补**下列两行并加字幕「T3 轮档案（D-T3-1 修复前），单次纪律已在该轮用毕」：

```
:41  RuntimeError: [committee] refund accounting mismatch: before={'alice': 0, 'bob': 0, 'broker': 0} after_fund={'alice': 9000, 'bob': 0, 'broker': 0} after={'alice': 10000, 'bob': 0, 'broker': 0} (NotFulfilled must refund the buyer and leave seller/broker untouched)
:43  # demo exit=1
```

- ② console 判级（`_r3-t3-console-raw.txt:2` 逐字，只读流式回放；字幕注明 T3 实例名
  `Lyquid-ybidj3krshf4gqcjk3m3px6mooi6tg74twwaa` 与「实录回放」）：

```
:24  e2_aggregate: agreed deal=deal-1 verdict=1 from 4 input(s) (avg_num=4)
:31  committee_verdict_certified: cert.signers RAW = [0, 1, 2, 3] (Vec<SignerID>=Vec<u32>, len=4) deal=deal-1 verdict=1
:36  apply_verdict: deal=deal-1 verdict=1 misconduct=[]
:38  deal_info: {"id":"deal-1","buyer":"0x70997970C51812dc3A010C7d01b50e0d17dc79C8","seller":"0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC","amount":1000,"state":"Refunded","timeout_slots":300,"deadline_slot":637}
```

- 判级口径：L2 = 4 提案（`inputs=4`）+ 4 签（`signers=4`，`docs/b3-user-test/通过判据.md:27`）；
  `timeout 60` 到点 `rc=124` 是**正常收尾**（console 为流式历史回放，`_r3-t3-console-raw.txt:3`
  先例），字幕要注明，防止误读为失败。

### S6 EVM 对照要点（40s，数据画面）
- **口播**：「我们拿同一个 anvil 链上的纯 EVM escrow 做对照。部署环节 EVM 更便宜——
  1,936,008 对 3,843,041，大约 1.98 倍；但单笔操作的 gas 没有单向结论，比如 create 反而
  是 Lyquid 便宜，fund 是 EVM 便宜。所以片子里不做『谁更便宜』的总量结论。」
- 画面：幻灯片 P6 四维表；数据出处 `r3-t4-contrast-report.md:180-:187`（gas）、`:60-:83`
  （代码量双口径）、`:104`、`:232`（负对照 `non-member signer`，rc=1）。
- 补充口播（一句）：「EVM 侧的委员会是合约里的一张地址表，本轮还包含买卖双方本人
  （`:91`），所以它不构成交易外的独立信任锚。」

### S7 收尾卡（20s）
- **口播**：「完整论证在 12 页报告里，所有数字都能追到『文件:行』；证据索引在
  `report/README.md` 第 5 节，原始实录全部在 `workflow-out/` 下。谢谢。」
- 画面：幻灯片 P12 + 报告封面。

---

## 3. 占位符与替换规则

| 占位符 | 含义 | 替换规则（录制时） |
|---|---|---|
| `<addr>` | S3 正常流所用合约地址 | = **S2 当轮新部署实例**的 `Contract:` 地址（`_r3-t3-deploy-raw.txt:82` 同形）。**禁止**填 `0xFD6F7A6a5c21A3f503EBaE7a473639974379c351`（`_r2-normal-assess-raw.txt:2` 已用实例） |
| `<addr>`（S4） | keeper 讲解行的合约地址 | = `0xFD6F7A6a5c21A3f503EBaE7a473639974379c351`（`_r2-keeper-loop-raw.txt:2`、`:7` 逐字；该镜为回放，只作讲解） |
| `<实例名>` | S2 备路径 `shaker to-hex` 的实例名 | = 当轮 deploy 输出的 `Lyquid-…` 全名（`_r3-t3-deploy-raw.txt:81` 同形） |
| `<新名>` / `<新地址>` | S2 预期输出的当轮值 | 以当轮 `created` 行为准（`_r3-t3-deploy-raw.txt:85` 形态） |
| `<ANVIL0_KEY>` | 部署签名私钥 | `0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80`（`agents/common/rpc.py:97`；同文件 `:90` 注明为 devnet 公开确定性密钥、**非生产凭据**）。画面**不要**露出全钥：录屏时用环境变量或在后期打码，实录档亦按 R2 先例脱敏（`_r3-t3-deploy-raw.txt:59`） |
| `<addr>`（S5 可选 T3 档） | T3 轮档案地址 | 固定 `0x87006e75a5B6bE9D1bbF61AC8Cd84f05D9140589`（`_r3-t3-committee-raw.txt:2`，回放不执行） |

---

## 4. 录制技巧

1. **终端可读性**：字号 ≥18pt、深底浅字（建议背景 `#101820`、前景 `#E6EDF3`）、
   窗口宽度 ≥1100px；S5 的长行（`cert.signers RAW …` 113 字符）需要宽窗，否则会折行。
2. **每镜独立起止**：每镜单独开始/结束并留 1–2 秒静帧，便于单镜重录而不影响整片拼接。
3. **S5 双终端**：左窗跑 demo（①），右窗 `timeout 60` 跑 console（②），分屏或两次录屏后
   快切；两个画面的字幕分别标「T7 实录回放」与「T3 console 实录回放」。
4. **console 是流式历史回放**：打开即吐全部历史事件（T3 实录 39 行、T7 内建取证 25 行），
   `timeout 60` 到点 `rc=124` 属**正常收尾**；字幕注明「rc=124 = timeout 正常关闭」。
5. **S4 是"读"不是"跑"**：用编辑器打开 `_r2-keeper-loop-raw.txt`，逐行高亮讲解；不要执行
   keeper.py（该 deal 已 terminal，执行只会得到三条 terminal 行，反而削弱画面）。
6. **数字口播与画面一致**：S3 说 9000/980/20，S5 说 10000→9000→10000；两处口径不同
   （R1 分账 vs R3 funding 中间态），不要在口播里混用。
7. **字幕模板**：每镜左上角固定一行小字——`S<n> · <镜名> · <实跑/实录回放> · <日期>`。

---

## 5. 风险预案

### 预案 A（devnet 不可用 → 全镜头改「实录回放模式」）
- 全部镜头改为 `cat` / 编辑器打开已档日志逐段讲解：S3 ↔ `_r1-demo-normal-raw.txt`
  （`:3`、`:5`、`:6`、`:9`）、S4 ↔ `_r2-keeper-loop-raw.txt`、S5-② ↔ `_r3-t3-console-raw.txt`、
  S5-① ↔ `_r3-t7-dt31-verify-raw.txt`、S1/S2 ↔ `_r3-t4-precheck-raw.txt:5-:12` /
  `_r3-t3-deploy-raw.txt:81-:86`。画面即实录原文，零执行风险。
- 片头字幕登记：「本片为已档实录回放（2026-10-28/29/30 轮次），非当轮实跑」。

### 预案 B（某镜失败 → 重录点）
| 镜 | 失败表现 | 处置 |
|---|---|---|
| S2 | deploy 报错 / 超时 | 切备路径（`to-hex` + 引已档 `created` 行，`:581`、`:85`），字幕注明「部署日志见 T3 实录」 |
| S3 | 余额与 R1 不同 | 正常：以当轮实录为准口播（新实例可能已有流水则换新实例重录）；`demo.py` 报错则保留失败前成功段，失败镜改实录回放并在片尾「差异登记」字幕列出 |
| S4 | — | **无重录点**（本镜即回放，无执行） |
| S5 | demo 报错 / console 无输出 | 保留 T7 实录回放（无需实跑）；console 无输出 → 检查 `--endpoint ws://node1:10087/ws` 与实例名，重录该镜 |

---

## 6. 纪律（录制时不得违反）

1. **单次纪律**：绝不重复 `e2_arm`、`e2_run_verdict_round`（`_r3-t3-committee-raw.txt:28` 的
   `禁多次触发`）。N 次触发 = N 个独立回合，首回合已把 deal 推到终态，后续 certified call 必败
   （`docs/b3-user-test/通过判据.md:27`）。
2. **`MSYS_NO_PATHCONV=1` 前缀必带**：Git Bash 会把 `/tmp/...` 改写为 Windows 路径
   （D-T6-1 教训，见 `workflow-out/implementation.md` §7.3（R3 版，`git show 8d093b5:workflow-out/implementation.md` 取回）与操作手册 §2.1）。
3. **实例不混称**：S5-② 的判级行来自 **T3 实例**
   `Lyquid-ybidj3krshf4gqcjk3m3px6mooi6tg74twwaa`，S5-① 来自 **T7 实例**
   `Lyquid-dpp6ird6knahaun6dokpi6ki2pdnbjxdfunqa`；字幕必须分别标注，不要说成同一实例。
4. **T3 档的失败行不得省略**：若展示 T3 committee 回放，`RuntimeError …`（`:41`）与
   `# demo exit=1`（`:43`）必须同屏，并注明「D-T3-1 修复前档案」。
5. **不虚构输出**：所有预期输出均取自「文件:行」实录；当轮输出与实录不同时，口播以当轮为准，
   并在片尾差异登记字幕说明。

---

## 7. 时长合计与判据

| 镜 | S0 | S1 | S2 | S3 | S4 | S5 | S6 | S7 | 合计 |
|---|---|---|---|---|---|---|---|---|---|
| 秒 | 20 | 20 | 40 | 60 | 45 | 60 | 40 | 20 | **305** |

- 加总：20+20+40+60+45+60+40+20 = **305 秒 = 5 分 05 秒**。
- 判据（方案 GT-c）：240–360 秒；305 ∈ [240, 360] ✓（5±1 分钟）。
- **3 分钟版剪辑点（课程原文上限，供选）**：课程要求原文为「8 分钟展示（5 分钟讲解 +
  3 分钟预录 demo）」（方向总结:24）。若必须压到 180 秒，建议按 S0 10 / S1 15 / S2 25 /
  S3 45 / S4 25 / S5 40 / S6 15 / S7 5 = 180 秒剪；台词不变，只压静帧与 S2 部署过程
  （改为备路径 to-hex）。本脚本主设计仍按方案 §4.1 的 305 秒。

---

## 8. 差异登记（GT-f）

| # | 项 | 说明 |
|---|---|---|
| 1 | S1 命令形态 | 方案 §4.1 说「形态出处 `implementation.md` §7.2 T3.0」（R3 版，`git show 8d093b5:workflow-out/implementation.md` 取回）；实测该命令原文在 `implementation.md:443`（R3 版，`git show 8d093b5:workflow-out/implementation.md` 取回；同节 :617 同一取回源、亦为同型），已按实际行号引用；同型输出用 `_r3-t4-precheck-raw.txt:5-:12` |
| 2 | S1 容器名带 compose 后缀 | 实录容器名为 `multi-node1-1` 等（compose 生成名），方案写作 `multi-node1..4` 为简写；分镜表按实录给出全名 |
| 3 | S2 部署命令分行 | `_r3-t3-deploy-raw.txt:59` 把 deploy 命令以 `\n#   ` 折成三行注释形态转写；本脚本拼回单行并保留 `shaker deploy` 原参数顺序（`-r` / `--endpoint` / `--private-key` / `Cargo.toml`），不新增参数 |
| 4 | S2 密钥脱敏 | 实录行密钥已脱敏为 `0xac0974...ff80`（`:59` 注明 full key = ANVIL0_KEY）；本脚本以 `<ANVIL0_KEY>` 占位并给出来源行，不把全钥写进脚本正文 |
| 5 | S3 预期余额来源 | 方案要求「新实例实跑」；编码期静态核对只能命中 R1 档（`_r1-demo-normal-raw.txt:5`/`:6`/`:9`，同为零起点实例、同形预期），录制当轮须再以新实例实录为准 |
| 6 | 3 分钟版 | 课程原文（方向总结:24）的 demo 上限是 3 分钟，方案判据是 5±1 分钟；本脚本按方案执行并给出剪辑点，若课程硬性 3 分钟请用 §7 的 180 秒版 |
| 7 | 时长实测 | 分镜时长为设计值（方案 §4.1），未经实拍计时；实拍后若超出 360 秒，优先压 S2/S6 的静帧 |

---

## 9. 逐字校验记录

本文件所有命令与预期输出行的逐字命中校验（`grep -nF` 回对应实录，含 S3/S4/S5 每条预期行）
的原始输出见 `workflow-out/_r4d2d3-verify-raw.txt` §T7；校验口径：
- 命令：去掉实录头的 `# command: ` 前缀后逐字比对（S2 的 4 条命令按 `:57`/`:58`/`:125`/`:59`
  分别命中；`:59` 为三行注释形态，按片段命中并登记）；
- 预期输出：整行 `grep -nF`（`DEMO COMPLETE` 行含缩进，按去缩进前缀命中并登记）；
- 例外：`<addr>` / `<实例名>` / `<ANVIL0_KEY>` 占位符按 §3 规则替换后不再回测（记录为
  「占位符合法」）。
