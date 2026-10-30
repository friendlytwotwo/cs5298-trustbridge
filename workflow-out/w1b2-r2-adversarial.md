# R2 目标 B 证据：对抗流 devnet 全链（路线①扁平 wire，三裁决场景）

> 实例：`Lyquid-tldda6zqdhab2kdysepcqxx73uvm3sxz7wbaa` @
> `0xFD6F7A6a5c21A3f503EBaE7a473639974379c351`；平台 0.8 / LDK 0.8.1；
> 镜像 `sha256:98b40bf8a733783e5b5768f37c0557ebf075c0fcf088aaa75c9b077fa2e42d17`。
> 原始日志：`_r2-deploy-raw.txt`（部署 + md5 + G5a/G5b + wire 探针）、
> `_r2-adversarial-raw.txt`（三场景 transcript + 编码器交叉校验 + attempt 1 记录 + 补偿裁决）、
> `_r2-adversarial-attempt1-raw.txt`（失败首跑原文）、
> `_r2-adversarial-console-raw.txt`（println 累计视图）、`_r2-final-state-raw.txt`。
> 采集时间 2026-10-29 23:32–23:42。

---

## §1 部署与构建勾稽（T5）

```
$ docker exec multi-tools rm -rf /tmp/tb-lyquid
$ MSYS_NO_PATHCONV=1 docker cp lyquid/. multi-tools:/tmp/tb-lyquid
  MATCH    src/lib.rs  a8fdcf064f2a5d472531f545b9eea42f
  MATCH    src/types.rs  f33e334a2c256da6f2cf08927add165e
  MATCH    src/core.rs  4ae54a4717daf35284ffe76d0ebd0b32
  MATCH    src/committee.rs  c5f660a13d5c18b5798bfb675fa8729e
  MATCH    src/assessor.rs  4df7cda64e7e9eb4483c0b8be64068aa
  MATCH    src/timeout.rs  f842d432143365261e012336d89dc678
  MATCH    Cargo.toml  08f94560a1f0a231088055ad834974ee
$ docker exec -w /tmp/tb-lyquid multi-tools cargo check --target wasm32-unknown-unknown   # 先 touch src/*.rs
   Compiling trustbridge v0.1.0 (/tmp/tb-lyquid)
       Finished `dev` profile [unoptimized + debuginfo] target(s) in 1.00s      # G5a：零 error
$ docker exec -w /tmp/tb-g5b multi-tools md5sum -c frozen.txt                              # G5b
   lyquid/src/types.rs: OK / core.rs: OK / committee.rs: OK / assessor.rs: OK
$ docker exec -w /tmp/tb-lyquid multi-tools shaker deploy … --private-key 0xac09…ff80 Cargo.toml
   Status: created
   Lyquid ID: Lyquid-tldda6zqdhab2kdysepcqxx73uvm3sxz7wbaa
   Contract: 0xFD6F7A6a5c21A3f503EBaE7a473639974379c351
```

**力证编译不是假通过**：`touch src/*.rs` 后必须重编 crate，日志出现
`Compiling trustbridge v0.1.0`（1.00s）——R1 §3-2「旧 target 假通过」教训的流程化落实。
`G5b` 的两个口径（三文件 `git diff` 为空 + 四文件 `md5sum -c`）在同段就地取证。

## §2 wire 探针（G5c，新实例）

| 探针 | 结果 | 含义 |
|---|---|---|
| `cast sig "apply_committee_verdict(string,uint8,string[])"` | `0xa32974e3` | rpc.py `_ABI` 冻结值来源 |
| `cast sig "open_dispute(string,string)"` | `0xa48ab911` | 与 rpc.py 既有冻结值**一致**（未漂移） |
| `cast call balance_of(string)` | `0` | 读通道可用 |
| `cast call due_deals(uint64) 0` | `[]` | 合法空数组（路由性） |
| `cast send apply_committee_verdict "deal-nope" 0 '[]'` | `status 1 (success)`；LyteLog 记录 method=`apply_committee_verdict`、input 首 4 字节 `a32974e3`、参数 `deal-nope` | **P2 复证**：`0x1` = 已排序 ≠ 方法 Ok |
| `cast call deal_info("deal-nope")`（紧接着） | `Barrel(Lyquid(LyquidRuntime("no such deal")))` | deal 确实不存在 ⇒ 上一笔是**被吞的 Err** |

### 2.1 新机制注记：eth_call 对**写方法**恒返回 FuncNotFound

探针中 `cast call apply_committee_verdict` / `cast call open_dispute` 报
`Execution error: Barrel(FuncNotFound).`。机制对照（同日志）：

```
$ cast call … "fund(string)" "deal-nope"          → Barrel(FuncNotFound)          # R1 就已 eth 导出的写方法
$ cast call … "deal_info(string)" "deal-nope"     → Barrel(Lyquid(…"no such deal"))# 只读 getter 正常路由
$ cast send … "no_such_method(string)" "x"        → Failed to estimate gas … execution reverted
```

结论：**FuncNotFound 是 eth_call 通道对「写方法」的固有响应**，不是「未导出」的判据；
写方法的可达性只能由 eth_sendTransaction 侧证明（此时 LyteLog 记下方法名与 selector）。
因此 R2 的「FuncNotFound 已消除」应精确表述为：**写通道上两方法已路由**（本节第 5 行
探针 + 下节三场景的实际裁决结果），eth_call 上的 FuncNotFound 属通道属性、与导出无关。

## §3 三场景（一次 `--flow adversarial` 运行，同一 wire）

```
$ python scripts/demo.py --node http://127.0.0.1:10087 --contract 0xFD6F…c351 --flow adversarial
[adversarial] faucet(alice,10000) -> balance_of(alice)=39000 (self-funded arm; T6 general rule)
assess_brief (on-chain, mode=replay): {'qualification_score': 75, 'risks': ['heuristic-mode'], 'est_duration_ms': 60000, 'est_confidence': 40}
[malicious] deal=deal-6 state ladder: Qualified -> Funded -> Submitted -> Disputed (timeout_slots=300)
[malicious] final state=Refunded  alice 49000 -> 48000 (after fund) -> 49000 (after verdict)  bob 0->0  broker 0->0
[fulfilled] deal=deal-7 state ladder: Qualified -> Funded -> Submitted -> Disputed (timeout_slots=300)
[fulfilled] final state=Settled  alice 49000 -> 48000 (after fund) -> 48000 (after verdict)  bob 0->980  broker 0->20
[fulfilled] split check OK: fee=20, bob +980, broker +20
[not-fulfilled] deal=deal-8 state ladder: Qualified -> Funded -> Submitted -> Disputed (timeout_slots=300)
[not-fulfilled] final state=Refunded  alice 48000 -> 47000 (after fund) -> 48000 (after verdict)  bob 980->980  broker 20->20
DEMO_EXIT=0
```

**G6B 三裁决终态表**

| 场景 | verdict_code | 终态 | 买方回流 | 卖方/经纪人 | misconduct |
|---|---|---|---|---|---|
| Malicious（伪造交付） | `2` | `Refunded` | 48000 → 49000（+1_000） | 0 / 0（不变） | **+1**（见 §4） |
| Fulfilled（合规交付，对照） | `0` | `Settled` | 48000 → 48000（**0**，`Payout::settle` 的 `refund_to_buyer=0`） | bob +980 / broker +20 | 不变（见 §4） |
| NotFulfilled（伪造交付） | `1` | `Refunded` | 47000 → 48000（+1_000） | 980 / 20（不变） | **不变**（见 §4） |

状态阶梯三单均含 **Disputed 读回**（`open_dispute` 生效的直接证据；每步经 5×0.4s
读回重试，避免读到上一块旧态）。`fee = 1_000 × 200 / 10_000 = 20`，与 `bob +980 /
broker +20` 勾稽。

## §4 misconduct 取证（println 累计视图，P5 console 通道）

`timeout 25 docker exec multi-tools shaker console Lyquid-tldda6zq…` 回放（`console_rc=124`
= 回放完成后被 timeout 杀，与 R1 同）：

```
apply_verdict: deal=deal-5 verdict=2 misconduct=[0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC=1]   # attempt2 Malicious：0→1
apply_verdict: deal=deal-6 verdict=2 misconduct=[0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC=2]   # attempt3 Malicious：1→2
apply_verdict: deal=deal-7 verdict=0 misconduct=[0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC=2]   # Fulfilled：不变
apply_verdict: deal=deal-8 verdict=1 misconduct=[0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC=2]   # NotFulfilled：不变
```

**对照点**（方案 §5 T6-B）：NotFulfilled 的证据不是「无行」，而是**每行都打、计数不增**
——deal-8 行与 deal-7 行计数同值（2），deal-6 行相对 deal-5 行 +1。行内含 deal id 与
verdict code，计数为**累计视图**。misconduct 无 getter（方法清单冻结），println 是既有
观测缝（先例 `fund:deal_view`、`deal_info`），非共识状态、语义零影响。

## §5 编码器缺陷（本轮由 attempt 1 暴露并修复）

首跑（`_r2-adversarial-attempt1-raw.txt`）症状：`apply_committee_verdict` 交易
`status 0x1` 但 deal-4 停留 `Disputed`（平台吞 Err）。定位到 `rpc.py` 的 ABI 编码器：
`_enc_value("string[]")` 把长度字也算进 `head_size`，元素偏移比标准多 `0x20`，链上解出
的 `signers`/`members` 为垃圾串 → 成员/签名守卫拒绝。与 `cast calldata` 逐字节对比：

```
mine: …000000a0 000000…a0   (偏移 0x60/0xa0)
cast: …00000040 000000…80   (偏移 0x40/0x80)
```

**修复**：`head_size = 32 * len(items)`（偏移相对长度字之后的 tail）；`_decode_ret` 的
`string[]` 做了同源对偶修正（见 `w1b2-r2-keeper-timeout.md` §3）。修复后交叉校验：

```
MATCH apply_committee_verdict(string,uint8,string[]) args=('deal-x', 2, ['n1','n2'])
MATCH apply_committee_verdict(string,uint8,string[]) args=('deal-y', 0, [])
MATCH apply_committee_verdict(string,uint8,string[]) args=('deal-z', 1, [3 个地址/占位串])
MATCH committee_config(string[],uint32)              args=(['n1','n2','n3'], 3)
MATCH fund(string) / create_deal(8 params)
ENCODER VERDICT: ALL MATCH cast calldata
```

**连带事实修正（R1 口径）**：R1 在 node 模式每次运行都调 `committee_config(string[],uint32)`，
但受同一编码器缺陷影响，链上委员会**从未真正按意图配置**（成员为垃圾串）。R1 的正常/
超时流不依赖委员会，故未被发现；R2 对抗流首次依赖才暴露。修正后本实例的委员会由
main() 以地址制名单配置：`[0xf39F…92266, "node-1", "node-2", "node-3"]`、threshold 3，
证书 signers = 前 3 个（含 broker 地址），满足 `caller ∈ members ∧ caller ∈ signers ∧
len ≥ threshold`。

## §6 余额勾稽（实例终态）

```
balances: alice=77000 bob=3920 broker=80  (sum=81000)
deal-1..3 Refunded（超时/keeper） deal-4 Refunded（补偿 NotFulfilled）
deal-5/6 Refunded（Malicious） deal-7 Settled（Fulfilled） deal-8 Refunded（NotFulfilled）
deal-9 Settled（T6-C 正常流） deal-10 Settled / deal-11 Refunded / deal-12 Refunded /
deal-13 Settled / deal-14 Refunded（node --flow all 一次连跑，见 §6.1）
```

总注资 `81_000`（faucet 历史：draft 10_000 + T6-A 10_000 + attempt1/2/3 各 10_000 +
T6-C 10_000 + `--flow all` 的 normal 10_000 / timeout 1_000 / adversarial 10_000）——
托管 14 × 1_000、回流 10 × 1_000 ⇒ `81_000 − 14_000 + 10_000 = 77_000`；且
`77_000 + 3_920 + 80 = 81_000` 守恒。终态原文：`_r2-final-state-raw.txt`。

### 6.1 node `--flow all` 全序列（门控拆除的集成验证）

```
$ python scripts/demo.py --node http://127.0.0.1:10087 --contract 0xFD6F…c351 --flow all
FLOW 1 normal      → deal-10 state=Settled balances alice=67000 bob=2940 broker=60
FLOW 2 timeout     → deal-11 deadline_slot=288, nudge 287→288→289, due=['deal-11'], Refunded
FLOW 3 adversarial → deal-12 Refunded / deal-13 Settled / deal-14 Refunded (DEMO COMPLETE)
DEMO_EXIT=0
```

同一进程内 normal+timeout+adversarial 三流连跑成功 ⇒ 方案 §6-3 的门控拆除目标达成
（`--flow all` 的 node 序列已与 sim 对齐；原 `ADVERSARIAL_BANNER` / `exit 2` 已删除，
`grep -rn "sim-only\|ADVERSARIAL_BANNER" scripts/ agents/` 零命中，见 T7 日志）。
原文：`_r2-node-all-raw.txt`。

## §7 偏离登记

1. **编码器/解码器修正**（rpc.py，方案 §6-2 名义面之外）：见 §5 与 keeper md §3。属
   执行期发现并修复的潜伏缺陷，不改变任何 selector、调用形态或语义。
2. **attempt 1 / attempt 2 的失败留在档**（未删）：
   - attempt 1：编码器缺陷（deal-4 停留 Disputed）；
   - attempt 2：**链上已成功**（deal-5 → Refunded，malicious 生效），失败在 demo 的余额
     断言口径（拿 pre-fund 快照比 post-refund，正确应为 post-fund 基线 +1_000）。已改为
     `open_scenario` 同时返回 pre-fund / post-fund 两个快照。
   - 两笔遗留 deal（deal-4 Disputed、deal-5 Refunded）均已登记；deal-4 用 NotFulfilled(1)
     补偿裁决回收（`alice 48000->49000`，选 1 以不改变 misconduct 计数语义）。
3. **Fulfilled/NotFulfilled 仅 node 面**：sim 分支按方案逐字不动，故 FakeNode 侧仍只有
   Malicious 一条（sim transcript 与 T0 逐字一致，见 T7 日志）。
4. **node `--flow all` 全序列已在同一进程跑通**（§6.1，`_r2-node-all-raw.txt`）：三个流
   分别取证（T6-A/-B/-C）之外再补一次集成连跑，覆盖门控拆除后 main() 的新序列分支。
5. **misconduct 计数跨 attempt 累计**：console 取证的四行为 deal-5（attempt2）→ deal-6
   （attempt3）→ deal-7 → deal-8，计数 1→2→2→2；`--flow all` 的三次裁决在 console 采集
   **之后**执行（计数会继续变化，但本轮 console 原文已定格在上表）。计数本身属可复算的
   core 语义（core.rs:203-210），不是本轮新增状态面。
