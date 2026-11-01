# R6-R2 独立重审轮 实现说明（编码员，2026-11-01）

方案：`workflow-out/plan.md`（R6-R2 独立重审，HEAD 定格
`f40ce773021640c9ea7e2b87b163a39843067a74`，编码期 `git rev-parse HEAD` 实跑一致）。
改写注记：本文件为 R6-R2 覆盖写（方案 §0 #15）；上一版（上一轮 R6）实现说明已于
编码期覆写前备份至 `_implementation-prev-r6-backup.md`（#A2，覆写前再复核 md5
`782299b5120ea355d0655c33e19e8457` 逐字一致，编码期实跑）。下文「§x」指 R6-R2
方案文件；本表行号均为**当前代码**实读行号（零改动轮 = 开工前行号）。

## 0. 总结论

**本轮为独立重审轮：21 项先验台账逐条按当前代码重新取证，六焦点全部重开，
门禁 G1–G5 全部重跑。结论 = P0=0、达准入 P1=0、零代码改动；台账 21 项全部
「维持登记」+ 本轮新登记 P2×1（R2-N1）；G1/G2/G3/G5 通过，G4 容器不可用如实
登记未跑。**

- 13 个候选文件与本轮开工前逐字节一致：开工前快照
  `workflow-out/_pre-task-snapshot-r6r2.patch` 为 **0 字节**（工作树本就干净），
  13 份原件 cp 留档 `workflow-out/_r6r2-orig-*`（回退通道，未动用）；收尾
  `cmp -s` 13/13 逐字节一致（§5）。
- 零改动是**方案预期内的合法产出**：§0「上一轮同面审计结论为零改动，本轮预期
  亦为零至极少改动」+ §4「P2 只登记」+「P1 择优」三条件。六焦点新眼扫描未发现
  资金语义/守恒破坏、越权可达、误报漏报或 fail-closed 失效；三项 P1 候选逐一
  给出不取准入的本轮理由（§2 处置列），未照抄上一轮措辞（红线⑦）。
- sim 冻结基线逐字一致（md5 同 `a7cd1bdcd09fb44bff2002cb49e8694c`）是零改动
  轮的强行为验证；verify_core 40/40 本轮重跑为 types/core 当前态的新鲜基线。

## 1. 备份与快照（T0）与 §1 预置事实复跑实录（全部实跑）

**T0 件**：

| 件 | 实跑结果 |
|---|---|
| #A1 `_plan-prev-r6-run2-backup.md` | 规划期已落盘；本轮复核 md5 `4e8053581971daf5ede1e6a22c1840f0` = 方案 §0 #A1 值 |
| #A2 `_implementation-prev-r6-backup.md` | 规划期已落盘；**覆写本文件前**复核 md5 `782299b5120ea355d0655c33e19e8457` = 方案 §0 #A2 值 |
| 原点名两件 `_plan-prev-r6-backup.md` / `_implementation-prev-r5-backup.md` | 保持原样零改动；实跑 md5 `d8381a05788422c01a4496a205ce9fd7` / `a92ac14061798943f5f3be9d066c8af2` = 方案 §1-8 值 |
| #A3 `_pre-task-snapshot-r6r2.patch` + `_r6r2-orig-*` | **编码期开工前落盘**：`git diff -- lyquid/src scripts agents` → patch 0 字节；逐文件 cp 原件 13 份（lib/core/types/committee/committee_certified/timeout/assessor + rpc/protocol/llm/broker/demo/keeper），`ls | wc -l` = 13 |
| #A4 `_r6-run2-sim-out.txt` | 规划期已落盘，md5 `a7cd1bdcd09fb44bff2002cb49e8694c` = 冻结基线同值（本轮复核） |

**§1 十一项预置事实复跑**：

| # | 项 | 本轮实录 |
|---|---|---|
| 1 | HEAD / 提交前移 / 工作树 | `git rev-parse HEAD` = `f40ce77…`；`git diff --stat d460047..HEAD -- lyquid/src agents scripts` **空**；`git status --short lyquid scripts agents` **空** |
| 2 | 自检 | `python scripts/demo.py --selftest` → rc=0，尾 3 项 PASS 实见（deterministic/order-divergent、官方 FNV 向量 ×2），`SELFTEST OK` |
| 3 | 语法 | `python -m py_compile` 8 件（rpc/protocol/llm/alice/broker/bob/demo/keeper）→ `PY_COMPILE-ALL-OK` |
| 4 | sim 基线 | `python scripts/demo.py --sim --flow all` → rc=0；输出另存 `_r6r2-sim-out.txt`；`diff -u _r2-t0-sim-baseline-raw.txt _r6r2-sim-out.txt` **零差异**（diff_rc=0），两侧 md5 同 `a7cd1bdcd09fb44bff2002cb49e8694c` |
| 5 | 容器 | **编码期重试仍不可用**：`MSYS_NO_PATHCONV=1 docker exec -w /tmp/tb-lyquid multi-tools cargo check --target wasm32-unknown-unknown` → `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine … daemon 不在运行`。按方案 R3 如实登记 G4 未跑+原因；零改动前提下缺席不掩盖行为面（上一轮 7514c71 曾实证容器 md5 `03e3d08b…` = 仓库 lib.rs） |
| 6 | verify_core 挂载 | 壳 `src/lib.rs`/`tests/*.rs` 以 `#[path]` **绝对路径**挂载仓库内 types/core/committee/assessor + lyquid/tests 两文件（grep 实见 5 处 `#[path = …trustbridge\lyquid\...]`）；挂载面 `grep -c '#\[test\]'`：core 23 / committee 4 / assessor 6 / escrow_lifecycle 5 / modelcheck_refund 2 = **40** |
| 7 | 模型检查 | 父级 `workflow-out/verify_core`：`cargo test --lib --tests` → **33+5+2 = 40 passed, 0 failed**，rc=0（编码期复跑，基线新鲜） |
| 8 | 上一轮备份件 | 见 T0 表（md5 双侧一致） |
| 9 | 范围实测 | `wc -l` 实跑：Rust 7 文件 = 273+185+433+909+862+86+197 = **2945**；Rust 测试 2 文件 = 181+184 = **365**；Python 9 文件 = 962+810+179+161+98+93+68+56+7 = **2434**；dashboard.html = **1170**。与方案 §1-9 逐项同值（审计面逐字节一致的再次实证） |
| 10 | 负载锚点 | 全部实读命中（行号表见 §3 各焦点引用） |
| 11 | #A1/#A2 | 见 T0 表 |

## 2. 分级 findings 清单（本轮全表）

分级规则沿方案 §4：P0 必修 / P1 择优（准入三条件：不触红线、改动面小、有钉死
测试或门禁护航）/ P2 只登记。

| ID | 级别 | 位置 | 问题一句话 | 本轮证据 | 处置 |
|---|---|---|---|---|---|
| P1-R1 | P1（择优未取） | rpc.py:441-450 | `_rpc` 对非 JSON 响应/连接异常/HTTP 错误裸抛（`r.raise_for_status()` :446、`r.json()` :447，无折叠） | 实读 rpc.py:441-450；调用方面实测：`_deal_exists`（:542-547）只捕 NodeError——若把传输异常折进 NodeError，`discover_deals` 会把瞬时网络错误**静默截断**为「无更多 deal」，属引入新危害 | **维持登记不修**：修复须区分错误类并波及 discovery 语义，不满足「改动面小」；无钉死测试 |
| P1-R2 | P1（择优未取） | broker.py:29-31、llm.py:61-62 | live 模式畸形 LLM 响应裸 traceback（broker `json.loads(raw)` :30、`rep[k]` :31 KeyError；llm.py `r.json()["choices"][0]` :62 KeyError/IndexError） | 实读 broker.py:27-34、llm.py:47-62；live = `TB_LLM=openai` 显式 opt-in（llm.py:65-69），录制演示专用 | **维持登记不修**：不触红线但无门禁护航（live 面无测试），非本轮准入池优先项 |
| P1-R3 | P1（择优未取） | timeout.rs:61 | `watcher_step` 单笔 claim 失败 `.ok?` 中断整轮 | 实读 timeout.rs:57-63；本轮再证：native trigger 已判 unusable（timeout.rs:67-86 三栏记录），**生产驱动方 = keeper.py**（:115-122 逐单捕 `(NodeError, TxError)` continue，无此面），watcher_step 现无驱动方 | **维持登记不修**：DoS 型延迟非资金错误、幂等自愈；lyquid 改动须容器 cargo check 护航而 G4 不可用（§1-5），收益近零风险实存 |
| P2-1 | P2 | rpc.py:56、alice.py:16 | 死 import：rpc.py `field` 导入后零引用；alice.py `Acceptance`/`Deliverable` 导入后零引用 | `grep -n "field" agents/common/rpc.py`：仅 :56 为 import，余为 doc 文本；alice.py 全文实读无使用点 | 登记不修 |
| P2-2 | P2 | rpc.py:426/:500/:648/:809/:895-897/:911-915、protocol.py:19、demo.py:15 | 行号注释漂移残量 8 处（实例：rpc.py:426 `lib.rs:624`→require 实为 :230-246；:500 `lib.rs:241`→faucet 实为 :281；:648 `lib.rs:625-635`→模式契约实为 :649-661；:809 `lib.rs:189`→输入校验实为 :320-326；:895-897 `lib.rs:365-368`→caller∈signers 实为 :530-533；:911-915 `lib.rs:369-371`→读算校同源实为 :768-770；protocol.py:19 `rpc.py:49`→notarize 包装实为 :564；demo.py:15 `lib.rs:367-369`→自署名实为 :406-409） | 逐点实读比对当前行号（左列即本轮证据） | 登记不修（惯例：行号漂移只登记） |
| P2-3 | P2 | committee.rs:78-90、timeout.rs:86、lib.rs:735-737 | 死代码：`set_members`/`members` shim 零调用方；`SPIKE_1_TRIGGER_REGISTRATION` 仅声明无读取；`slash_to_treasury > 0` 分支 core 恒不产出 | `grep -rn "committee::members\|set_members\|SPIKE_1_TRIGGER" lyquid/src`（除自身/注释外零命中）；core.rs:87/:494/:533 三处 slash 字面量全零；apply_payout doc（lib.rs:713-717）自我声明 W4 扩展单点 | 登记不修 |
| P2-4 | P2 | committee.rs:45-49、rpc.py:919 | 未知 verdict_code 判定面：链上 `_ => Malicious`（红线④内零变化）；sim 字典越界 KeyError（仅 FakeNode 面） | 实读 committee.rs:44-56、rpc.py:919 | 登记不修（红线④） |
| P2-5 | P2 | protocol.py:30 vs broker.py:38-40 | 双规范化 ensure_ascii 差异 | 实读两处；本轮再证分叉不可达：terms 只经 broker 自产自用（broker.py:38→:41 同一 hash 面），alice/bob 不重算 terms_digest；dashboard `canon`（:775-781）用 `JSON.stringify`（不转义非 ASCII）= 与 protocol.py 同向；ops-reason 非 ASCII 的 reason_digest 页内**自算自用**（open_dispute :880/:1130 与 notarize DISPUTE :870/:1126 两 digest 各自独立上链，无交叉比较点） | 登记不修 |
| P2-6 | P2 | rpc.py:809-813 等 | FakeNode 非镜像面（notarize 拒 pre-deal :839-844 刻意收紧）+ `python -O` 下 assert 消失 | 本轮重证：**NodeClient 写路径零 assert**（`sed -n '420,750p' rpc.py \| grep assert` 空）——`_send` :483-484、`create_deal` 读回 :537-539 全 if+raise；assert 仅 FakeNode（sim 冒烟面） | 登记不修 |
| P2-7 | P2 | broker.py:57-59 | 默认成员硬编码 node-1..4 | 实读 broker.py:57-59；对照 rpc.py:392-412 `get_node_ids` 动态面（demo committee 流用之，demo.py:603-605 实读） | 登记不修 |
| P2-8 | P2 | demo.py:358-361 | due 扫描每 deal 3× `deal_info`（node-only 效率） | 实读 demo.py:356-361 | 登记不修 |
| P2-9 | P2 | demo.py:147 | `wait_for` 的 `node` 形参未用 | 实读 demo.py:147-176：函数体仅用 time/predicate/last，`node` 零引用 | 登记不修 |
| P2-10 | P2 | core.rs:245-247 | `threshold > 成员数` 可配置（committee_config :545-561 只拒 0 不拒超员；e2_configure 同 :119-123）——fail-closed 方向恒拒（InsufficientCommittee），非安全洞 | 实读两处配置门 + core.rs:245-247 | 登记不修（W4 处置） |
| P2-11 | P2 | types.rs:174-176 | `Payout::total` 裸加 | 本轮重证消费面：`grep -rn "\.total()"` = lib.rs:725 debug_assert + core.rs 测试断言（:350/:375/:484/:508/:536/:565/:588/:614/:814），**不在资金决策路径**（apply_payout 逐字段 `>0` 门 :726-736）；构造面三形 total≤amount 恒成立（types.rs:155-177 实读） | 登记不修 |
| P2-12 | P2 | workflow-out/demo-script.md、docs/演示与运行指南.md | 文档行号漂移 | 惯例：只读件只登记不改写 | 登记不修 |
| N1 | P2（维持） | lib.rs:412 | notarize 对不存在 deal_id 也建条目（`entry(..).or_default()` 无存在性检查） | 本轮重证**裁决门不可绕**：apply_cert_and_payout 读 entries（:769-770）后，deal 查找 :783 `ok_or_else("no such deal")` 在 core::apply_verdict 之前 `?` 早退——幻影 deal 的证据永远进不了裁决；影响 = 日志噪声/内存面 | 维持登记 |
| N2 | P2（维持） | lib.rs:398-416 | notarize 无状态守卫，终态后仍可追加证据 | 本轮重证：终态后追加不可生效——apply_verdict 仅 Disputed（core.rs:199）+ 终态封死（core.rs:30-31 + `terminal_states_reject_everything` :756-788 实读）；Disputed 窗口内追加 = 设计内证据窗，append 后旧根必败 validate_cert（core.rs:249-251）fail-closed，活性可经重 arm + 重认证回合恢复 | 维持登记 |
| N3 | P2（维持） | lib.rs:788-792 | misconduct 写回先于 apply_payout（fail-stuck 面） | 本轮重证双前提缺一不可：①credit 溢出需先经 faucet（Anyone，已文档化信任洞 lib.rs:277-279）铸至 u128::MAX 邻域；②平台 Err 无原子回滚语义（fund 注记 :366-370 同款口径）。影响 = 资金滞留（deal 已终态、贷记未落地）——**非盗取、非守恒破坏**（credit checked_add 只会少记不会多记） | 维持登记 |
| N4 | P2（维持） | keeper.py:94-96/:116-121 | poll_once 只捕 `(NodeError, TxError)`，requests 层异常裸抛终止主循环 | 实读 keeper.py:92-132 + 主循环 :165-173（仅捕 KeyboardInterrupt） | 维持登记（单轮崩溃 = 人工重启，无资金风险） |
| N5 | P2（维持） | alice.py:33/:40-41、bob.py:25/:32-33 | CLI 无 sender 选择，node 写通道默认 anvil#0（DEFAULT_SENDER rpc.py:70、:437）与角色门不匹配 | 本轮 grep 实证：`node.fund/notarize/complete/submit_deliverable` 六处调用零 `sender=`；链上 Buyer/Seller 门 fail-closed 拒（tx 落地但 Err 被吞；alice.py:34 读回仍见旧态可见） | 维持登记 |
| N6 | P2（维持） | keeper.py:115-131 | 重复 claim 竞态下 action 归因失真 | 实读 keeper.py:115-131：读回 Refunded 即记 `action=claimed` + 本笔 tx hash；他方先落时本笔 Err 被吞仍 0x1 → 归因失真；终态守卫使双付款不可达（core.rs:30-31） | 维持登记 |
| **R2-N1** | **P2（本轮新登记）** | keeper.py:19-20 | 文档措辞失准：docstring 称 `_send`「already asserts status=='0x1'」——实为 `if + raise TxError`（rpc.py:483-484），非 Python assert；行为描述正确（非 0x1 必报错）但术语失真，且 if-raise 在 `python -O` 下仍生效、比 assert 更强 | 本轮新眼扫描实读 keeper.py:17-20 × rpc.py:464-485 对照；P2-6 重证（NodeClient 段 grep assert = 空）佐证 | 登记不修（doc 文案面，沿 P2-2 同类惯例） |

**P0 = 0**：六焦点（§3）全部重开，未发现可达资金/越权/fail-closed 失效类缺陷。

## 3. 六焦点核对表（本轮新证据）

### 3.1 焦点① 访问控制与攻击面

**矩阵 12 行逐行实读**（声明 lib.rs:212-225 / 执行 require :230-246）：

| 方法 | 声明（实读行） | 执行点（实读行） | 判定 |
|---|---|---|---|
| faucet | :213 Anyone | :281-291 无 require | ✓ |
| create_deal | :214 Broker | :308 | ✓ |
| fund | :215 Buyer | :361 | ✓ |
| notarize | :216 Anyone+自署名 | :406-409 `from != caller → Err` | ✓ |
| submit_deliverable | :217 Seller | :423 | ✓ |
| complete | :218 Buyer | :437 | ✓ |
| claim_timeout | :219 Anyone permissionless | 无 require；core 重推导（:459 → core.rs:170-178） | ✓ |
| cancel | :220 Buyer | :472 | ✓（任务书未列 cancel，语义核对 = Buyer 与 fund/complete 同侧） |
| open_dispute | :221 BuyerOrSeller | :493 | ✓ |
| apply_committee_verdict | :222 Committee+caller∈signers | :530 + :531-533 | ✓ |
| committee_config | :223 Broker | :547 + R5 阈值门 :554 | ✓ |
| getters ×4 | :224 Anyone 只读 | :566/:583/:594/:605 无资金效应 | ✓ |

require 的 Committee 臂（:243）查 `state.committee_members`，未配置 = 空集即拒
（fail-closed 实读确认）。

**完备性反向扫描（本轮增量）**：`grep -n "pub fn" lyquid/src/lib.rs` = 16 个；
其中 15 个 network 方法（faucet…due_deals，行号 :281/:296/:357/:398/:419/:433/
:454/:468/:487/:520/:545/:566/:583/:594/:605）全部被矩阵 12 行覆盖（getters 4 个
合一行）；`assess_brief`（:640）为 `#[method::instance]` 不属 network 矩阵口径
（:611-613 分节注释 + 方法属性实读）。**无方法漏登记矩阵行**。
certified 回调面不入矩阵口径：committee_certified.rs 模块头 E2 门禁台账（:28-48）
明示 origin=ZERO（:331 `origin: Address::ZERO` 实读）使地址门必 fail-closed，
与 lib.rs:193-194 注记互证一致。

**滥用路径 5 类重判定**（本轮实读）：
1. **签名/证书重放与跨单复用**：不可达。路线① into_domain（committee.rs:44-56）
   从当前全量证据折叠根，validate_cert 四查（core.rs:235-253：成员 :237-240 /
   去重 :241-243 / 阈值 :245-247 / 根匹配 :249-251）；路线② signers =
   `ctx.cert.signers` 逐节点映射（committee_certified.rs:356-380，映射失败剔除
   :373-379）。
2. **阈值绕过**：不可达。成员域唯一写点 committee_config=Broker（:547）+ 阈值
   0 拒（:554）；e2 域唯一写点 e2_configure=creator（committee_certified.rs:112）
   + 阈值 0 拒（:119-123）。
3. **重复结算**：不可达。终态封死（types.rs:51-53 + require_states core.rs:29-37）；
   apply_verdict 仅 Disputed（core.rs:199）、claim_timeout 仅 Funded+过 deadline
   （core.rs:170-178）、complete 仅 Submitted（core.rs:139）；720 排序模型检查
   本轮 G5 重跑 40/40 为新鲜背书。
4. **伪造署名**：不可达（洞内）。notarize 自署名（:406-409）使 check_evidence_shape
   的 `e.from == deal.seller`（committee.rs:69-71）成为可信归属；「digest 即身份、
   无签名」为已文档化 demo 信任洞（committee.rs:53 注记实读），洞内不判新缺陷。
5. **未注资取款**：不可达。claim_timeout 仅 Funded（core.rs:171）；cancel 无证据
   才可 + Qualified=全零 payout（core.rs:84-88，F2 钉死 :524-544）；apply_payout
   全零 no-op（lib.rs:726-736 四个 `>0` 门实读）；faucet 无上限 + BROKER=anvil#0
   （lib.rs:208）为已文档化信任洞（:277-279 TODO(W2) 实读）。

**advisory 时钟增量检查**：`grep due_deals|dueDeals` 三面实跑——demo.py:381 仅
sim 分支（node 路径 :357-361 用 discover_deals+deal_info）；keeper.py **零命中**
（走 discover_deals :161）；dashboard.html 只读显示（:660/:1087）+ 文档注记
（:209/:599）。timeout.rs:55 watcher_step 的 due 列表进 claim_timeout 由守卫重
推导（core.rs:171-175）。**无新增把 advisory 当权威的调用方**。

### 3.2 焦点② 经济不变量

可达转移全集守恒重证（全部实读）：
- `fund` lib.rs:357-392：余额预检 :371-374 → core::fund :375 → debit :378（顺序
  契约注记 :366-370；重复 fund 被 require_states 拒 core.rs:62）。
- `complete` lib.rs:433-448：BuyerConsent → `Payout::settle`（types.rs:165-172，
  fee = saturating_mul/10_000 + min-clamp，to_seller = amount-fee 恒不 underflow）；
  Committee 分支（core.rs:142-150）Fulfilled→settle、NotFulfilled/Malicious→
  full_refund；fee_bps 上限 core::create :54-56（InvalidFeeBps）。
- `claim_timeout` core.rs:170-178：仅 Funded + `now >= deadline`（:171-175）→
  full_refund。
- `cancel` core.rs:82-92：funded_slot 分流——Funded 全额退（:85）/ Qualified 全零
  （:87）。
- `apply_verdict` core.rs:191-218：三裁决映射 + Malicious misconduct+1（:205-208）
  + Malicious 不罚没（full_refund :207）。
- 记账单点：credit（lib.rs:693-703，checked_add :700；5 调用点 :288/:727/:730/
  :733/:736 全带 `?`）+ debit 预检（:684-691）。
- fee/溢出边界：`Deal::split`（types.rs:140-143）与 settle 同式；饱和角由
  `fee_rounding_edges_conservation`（core.rs:476-496）/`split_never_underflows`
  （:499-519，含 u128::MAX × u16::MAX 饱和角）/`verdict_fulfilled_full_fee_still_settled`
  （:593-615）钉死——本轮 G5 重跑 40/40 全含。
- N3 / P2-11 重验：见 §2 两行。

### 3.3 焦点③ R5 修复正确性复核（逐项「未引入新问题」）

| 项 | 本轮证据 | 结论 |
|---|---|---|
| A1 阈值 0 拒 | lib.rs:554 门位实读：require（:547）后、状态清写（:555-559）前；误伤面 grep 实跑：broker.py:57 `threshold=3`、demo.py:73 `THRESHOLD=3`、demo.py:81 `E2_THRESHOLD=4`（传参点 :610/:613）——**无一传 0** | 未引入新问题 |
| A2 credit checked_add | lib.rs:700 实读；失败 `ok_or_else?` 在写回 :701 前返回 Err 无半写；5 调用点全带 `?` | 未引入新问题 |
| B1a/B1b 终态断言 | demo.py:322-325（Settled）/:369-373（Refunded）实读：均在 `if node_mode(node):` 分支内；sim 分支零改动——本轮 G3 基线 md5 同值（§1-4）为行为证据 | 未引入新问题 |
| C1/C2 keeper 入参门 | keeper.py:151-152 `--interval<=0 → p.error`、:155-158 `--deals` 空表 → `p.error` 实读；discover 默认路径 :161 不受影响 | 未引入新问题 |

### 3.4 焦点④ 台账 21 项重评

§2 全表即产出：21 项逐条本轮证据 + 全部「维持登记」。升级候选专项重验：
- N1/N2 升 P0 可达链：**不存在**（:783 早退链 + core.rs:199/:30-31 门，§2 两行）；
- N3 fail-stuck：双前提缺一不可且影响为滞留非盗取（§2）；
- P1-R3：生产驱动方 keeper 逐单捕获（keeper.py:115-122），watcher_step 无驱动方；
- P2-4：红线④内；P2-5/P2-10/P2-11：§2 各行本轮证据。

### 3.5 焦点⑤ Python 编码层深审

**编码器支持集**（实读 rpc.py:202-278）：`_enc_value` string :203-205 / string[]
:206-222（head_size=32×len、偏移相对长度字后，R2 修正注记在位）/ uint* :223-224 /
bool :225-226 / 集外 ValueError :227；`_is_dynamic` :230-231 仅 string/string[]；
`_encode_args` :234-244 动态偏移=head_size+len(tail)；`_decode_ret` :247-273
（string[] tail=base+32 :262）；`_sig_types` :276-278。**无 bytes32/bytes32[]** =
终裁冻结条款 1 合规（e2_configure 走 cast send：注记 :158-162 + `e2_configure_cast`
:685-697 实读）。

**_ABI × lib.rs 签名对齐全表**（16 wire 面，逐一比对，零漂移）：
faucet(string,uint128)=lib.rs:281 U128 边界 :286 ✓；create_deal 8 参 =:296-306 ✓；
fund(string) :357 ✓；notarize(string×4) :398 ✓；submit_deliverable(string,string)
:419 ✓；complete(string) :433 ✓；claim_timeout(string)→bool :454 ✓；
cancel(string) :468 ✓；open_dispute(string,string) :487 ✓；
apply_committee_verdict(string,uint8,string[]) =:520 扁平 wire ✓；
committee_config(string[],uint32) :545 ✓；deal_info(string)→string :566 ✓；
evidence_entries_json(string)→string :583 ✓；balance_of(string)→uint128 :594
U128 返回 ✓；due_deals(uint64)→string[] :605 ✓；assess_brief(string×4)→string
:640-646 ✓；e2_arm(string)→bool = committee_certified.rs:161 ✓；
e2_run_verdict_round()→bool（cast call 通道 rpc.py:699-710）✓；
e2_net_config()→string :192 ✓。

**错误路径全查**：NodeError :165-178（raw verbatim 不折叠）；TxError :181-182 +
`_send` :483-484（if+raise，无 assert）；`_rpc` :441-450（P1-R1 面）；`_view`
:455-462；`_send` 回执 60s 超时 :474-482。`python -O` 面：NodeClient 写路径全
raise（§2 P2-6 grep 空）。已证对齐面复核不推翻：五视图 + 写面（faucet/notarize/
create_deal/fund/claim_timeout）本轮同表全过。

**protocol.py × core.rs 逐字节同规**：canonical 串
`"{seq}|{from}|{to}|{payload_digest}|{slot}\n"`——protocol.py:88 vs core.rs:290
字段序/分隔符一致；UTF-8（protocol.py:89 `.encode("utf-8")` vs core.rs:291
`.bytes()`）；空表 = `cbf29ce484222325` 两侧同（protocol.py:45/:86、core.rs:272-274
注记 + :288 fold）；顺序敏感不重排（两侧无 sort 实读）。G2 selftest 七向量 PASS
（§1-2）为行为证据。

**调用方交叉**：agents CLI（alice/bob 无 sender = N5；broker 双规范化 = P2-5、
默认成员 = P2-7）+ keeper 直用 `_send`（keeper.py:116；读回纪律 :123-131；
:19-20 文案 = 本轮新登记 R2-N1）。dashboard → 焦点⑥。

### 3.6 焦点⑥ dashboard 只读交互面复核

只读件零改动：md5 `a2206ffcca6cbe2fddb632071bf76709`（开工与收尾两次实测同值
= 上一轮登记值）。

1. **选择器冻结一致**：页内 SEL 表（:601）5 个 + OPS 表/LIVE 预设的
   b540def8/bd827024/b1fecd5a/73451f65/7ecc9d46/ad932b5c/a48ab911/786cfc8f/
   15df3c73/8b7acf91/a32974e3 = **合计 16 个 distinct selector** × rpc.py `_ABI`
   （:104-151）逐一比对：selector 与参数/返回类型**全数一致**（含 R2 修正后的
   string[] 偏移语义，页内 `encStrArr` :788-792 / `decStringArr` :626-627 与
   rpc.py :206-222/:253-268 同规实读）。`e2_configure`/`e2_run_verdict_round`
   **页内零调用**（全文实读 + 组标注 :884 明示 cast 通道指向 demo.py
   --flow committee）。
2. **status 0x1 ≠ 方法 Ok 读回纪律**两调用方成立：页内 sendTx 说明（:814-818
   「已排序≠方法成功，读回见下」实读）+ runOp 每笔强制 opsReadback（:916-917）+
   LIVE 预设 liveStepTx 按期望终态 liveWaitState（:985-1001；:964-975 超时抛错
   不静默实读）；agents 侧 keeper `_read_back`（:123-131）+ demo B1a/B1b
   （:322-325/:369-373）。
3. **e2_arm 单次纪律**：LIVE 三预设零调用 e2_arm（仅手动按钮 op-arm :888-889
   带「⚠ 单次」标注实读）；纪律为文档级无硬锁——本轮重证兜底链三层全部实读在位：
   armed_deal 重写被 propose 的 Disputed 门挡（committee_certified.rs:249-253）+
   aggregate 不一致拒证 None（:316-320）+ validate_cert 根匹配 fail-closed
   （core.rs:249-251）；页内 LIVE 对抗预设 committee_config([broker,node-1..3])
   覆盖实例 NodeID 制配置的 ⚠ 警示（:1134）实读在位。

**结论**：三纪律全部一致，零漂移；无 P0，dashboard 保持只读零改动。

## 4. 已实施修复

**零**。本轮无 P0；P1 择优三项均不满足准入（§2 各行处置列给出本轮理由）；
P2 全部登记不修。改动面 = workflow-out 产物（本文件 + `_pre-task-snapshot-r6r2.patch`
+ `_r6r2-orig-*` ×13 + `_r6r2-sim-out.txt`），**代码文件零字节改动**。

## 5. 门禁复跑实录（G1–G5，本轮全部重跑留档）

| # | 门禁 | 命令（照方案 §5 照抄执行） | 结果 |
|---|---|---|---|
| G1 | 语法 | `python -m py_compile agents/common/rpc.py agents/common/protocol.py agents/common/llm.py agents/alice.py agents/broker.py agents/bob.py scripts/demo.py scripts/keeper.py`（零改动 → 全 8 件复跑留记录） | **PASS**，`PY_COMPILE-ALL-OK`，rc=0 |
| G2 | 自检 | `python scripts/demo.py --selftest` | **PASS**，rc=0，`SELFTEST OK`（尾 3 项 PASS 实见） |
| G3 | sim 基线 | `python scripts/demo.py --sim --flow all`（输出另存 `workflow-out/_r6r2-sim-out.txt`）→ `diff -u workflow-out/_r2-t0-sim-baseline-raw.txt workflow-out/_r6r2-sim-out.txt` | **PASS**，diff_rc=0 零差异；两侧 md5 同 `a7cd1bdcd09fb44bff2002cb49e8694c` |
| G4 | Rust 编译（只读） | `MSYS_NO_PATHCONV=1 docker exec -w /tmp/tb-lyquid multi-tools cargo check --target wasm32-unknown-unknown`（零源码改动故未 touch） | **未跑（如实登记）**：`failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine … daemon 不在运行`（编码期重试实录）；零改动前提下缺席不掩盖行为面（7514c71 曾实证容器副本 md5 = 仓库 lib.rs） |
| G5 | 模型检查壳 | 父级 `workflow-out/verify_core`：`cargo test --lib --tests` | **PASS**，40/40（33 lib + 5 escrow_lifecycle + 2 modelcheck_refund，0 failed，rc=0）；挂载面 = 仓库当前态（`#[path]` 绝对路径 grep 实证，测试数 23+4+6+5+2=40） |

**快照比对（T7 收尾）**：13/13 `_r6r2-orig-*` 与工作区文件 `cmp -s` 逐字节一致
（`SNAPSHOT-IDENTICAL`）；`git status --short lyquid scripts agents` 空；
`git diff --stat -- lyquid/src scripts agents` 空；`scripts/dashboard.html`
收尾 md5 `a2206ffcca6cbe2fddb632071bf76709` = 开工值；`docs/b3-user-test/` 三件
与 `_submission-plan.md` 未触（只读）。

## 6. 与上一轮 R6（N1–N6）/ R5 台账（15 项）差异说明

| 来源 | 项 | 上一轮处置 | 本轮处置 | 差异 |
|---|---|---|---|---|
| R5 | P1-R1/R2/R3 | 登记不修 | 登记不修（逐项给出**本轮**不取准入理由，§2 处置列） | 无分级变化；P1-R3 增补「生产驱动方 = keeper 逐单捕获」新证据 |
| R5 | P2-1..P2-11（11 项代码面） | 登记不修 | 全部维持登记；P2-2 本轮把 demo.py:16 精确到 :15 并补全 8 处实读对照；P2-11 补 grep 消费面全表；P2-3 补零调用 grep | 无升级无降级 |
| R5 | P2-12 | 只读件只登记 | 同 | 无 |
| R6 | N1 | P2 登记 | **维持 P2**（新增裁决门不可绕实证：lib.rs:783 早退链） | 无 |
| R6 | N2 | P2 登记 | **维持 P2**（新增 Disputed 窗口 fail-closed + 活性可恢复论证） | 无 |
| R6 | N3 | P2 登记 | **维持 P2**（双前提逐条重证） | 无 |
| R6 | N4 | P2 登记 | 维持 P2 | 无 |
| R6 | N5 | P2 登记 | 维持 P2（本轮 grep 六处调用点为新增证据） | 无 |
| R6 | N6 | P2 登记 | 维持 P2 | 无 |
| R6-R2 | **R2-N1** | — | **本轮新登记 P2**（keeper.py:19-20 文档措辞「asserts」vs 实为 if+raise） | 台账 21 → 22 项 |

**台账总量**：R5 15 项 + 上一轮 R6 6 项 = 21 项全部维持；本轮新登记 1 项
（R2-N1）；升级 0；顺带修 0；代码改动 0。

## 7. 逐文件改动摘要

| 路径 | 改动 |
|---|---|
| `workflow-out/implementation.md` | 覆写为本文件（R6-R2 实现说明；覆写前 #A2 md5 复核一致） |
| `workflow-out/_pre-task-snapshot-r6r2.patch` | 新增（0 字节，开工时工作树实证） |
| `workflow-out/_r6r2-orig-*` ×13 | 新增（原件拷贝，回退通道，未动用） |
| `workflow-out/_r6r2-sim-out.txt` | 新增（本轮 G3 sim 输出，md5 = 冻结基线） |
| 其余全部（lyquid/src ×7、agents ×7、scripts/{demo,keeper}.py、dashboard.html、docs、_submission-plan.md） | **零改动**（§5 快照比对实录） |

零 git 写（未 commit/add/push/branch/tag/restore/stash）；devnet 零链写零部署
零重启（全部验证 = selftest / sim / py_compile / verify_core 只读面 + 一次失败
的 docker exec 探测，无任何链上效果）。
