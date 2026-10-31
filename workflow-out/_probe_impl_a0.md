# R6 实现说明（编码员，2026-11-01）

方案：`workflow-out/plan.md`（R6 后端全面审查——安全与正确性深审轮，2026-11-01）。
仓库定格 `HEAD=d4600474515ef2973899cc9754f854628288a878`（编码期实跑 `git rev-parse HEAD` 复核一致）。
改写注记：本文件为 R6 覆盖写（方案 §0-#15）；上一版 R5 实现说明已于编码期覆写前
备份至 `_implementation-prev-r5-backup.md`（两侧 md5 `a92ac14061798943f5f3be9d066c8af2`
逐字一致，编码期实跑复核）。下文「§x」指该方案文件。

## 0. 总结论

**本轮为审计轮，审计结论 = P0=0、达准入条件的 P1=0、P2 新增 6 项 + R5 残量实查登记 2 组——零代码改动。**

- 13 个候选文件（§0 清单 #1–#13）与本轮开工前逐字节一致：`git diff --stat -- lyquid/src scripts agents` 为空；开工前快照 `workflow-out/_pre-task-snapshot-r6.patch` 为 **0 字节**（开工前工作树本就干净），13 份原件已 cp 留档 `workflow-out/_r6-orig-*`（回退通道，未动用）。
- 零改动是**方案预期内的合法产出**：§4「P2 只登记（不改代码）」+ §0「改动面为候选面：findings 落在哪，修复落哪」+ 风险 R5「P2 只登记 + P1 择优天然限面」。六焦点审计未发现资金语义/守恒破坏、越权可达、误报漏报或 fail-closed 失效；R5 残留 3 项 P1 经安全视角重评后维持登记理由仍然成立（§3/§6）。
- 门禁 G1–G5 全部实跑通过（§5）；sim 冻结基线逐字一致（零改动下逐字保持的强验证）。

## 1. T0 定格实录（§1 九项预置事实复核）

| # | 预置事实 | 编码期实跑命令 | 结果 |
|---|---|---|---|
| 1 | HEAD=d460047…、工作树无代码改动 | `git rev-parse HEAD`；`git status --short` 过滤 workflow-out | 一致；仅 workflow-out 下 plan.md（规划师覆写）与 _probe_gate_a0.md 有改动 |
| 2 | selftest rc=0 | `python scripts/demo.py --selftest` | `SELFTEST OK`，rc=0；尾 3 项 PASS（deterministic/order-divergent、官方 FNV 向量 ×2）实见 |
| 3 | sim 基线零差异 | `python scripts/demo.py --sim --flow all` → `diff -u workflow-out/_r2-t0-sim-baseline-raw.txt <out>` | rc=0，`BASELINE-DIFF-IDENTICAL`；输出存 `workflow-out/_r6-baseline-sim-out.txt`（#A4） |
| 4 | py_compile 8 文件 | `python -m py_compile rpc.py protocol.py llm.py alice.py broker.py bob.py demo.py keeper.py` | `PY_COMPILE-ALL-OK` |
| 5 | 容器 cargo check 可用 | `MSYS_NO_PATHCONV=1 docker exec -w /tmp/tb-lyquid multi-tools cargo check --target wasm32-unknown-unknown` | rc=0，`Finished dev profile … 0.17s`，**33 条 warning**（与规划期记录同量级）；零源码改动故未 touch |
| 6 | 容器副本=改动前源 | `docker exec multi-tools md5sum /tmp/tb-lyquid/src/lib.rs` vs 仓库 md5sum | 两侧均 `03e3d08b9b41e00d4eb782d58b4de4ac` |
| 7 | 行数实测 | `wc -l` | Rust 7 文件 2945 行（types 197/core 909/lib 862/committee 185/committee_certified 433/assessor 273/timeout 86）+ 测试 2 文件 365 行 + Python 9 文件 2434 行，与 §1-7 一致 |
| 8 | verify_core 40 测试 | `grep -c '#\[test\]'` 5 个挂载文件 | core 23 + committee 4 + assessor 6 + escrow_lifecycle 5 + modelcheck_refund 2 = **40**（壳 crate `#[path]` 绝对路径挂载仓库内文件，测的即当前仓库态） |
| 9 | R5 方案备份在案 | `md5sum workflow-out/_plan-prev-r6-backup.md` | `d8381a05788422c01a4496a205ce9fd7`，与 §0 #A1 一致 |

## 2. 六焦点审计判定（T1–T6）

### 2.1 焦点① 访问控制与攻击面

**矩阵核对表（声明=执行，逐行实读 lib.rs）**：

| 方法（lib.rs 行） | 矩阵声明 | require 执行点 | 判定 |
|---|---|---|---|
| faucet :281 | Anyone（:213，TODO(W2) DEMO flag） | 无 require（Anyone 等价） | ✓ |
| create_deal :296 | Broker（:214） | :308 `require(Access::Broker,…)` | ✓ |
| fund :357 | Buyer（:215） | :361 `require(Access::Buyer,…,Some(deal))` | ✓ |
| notarize :398 | Anyone+自署名（:216） | :406–409 `from != caller → Err`（caller 取自 `ctx.caller`） | ✓ |
| submit_deliverable :419 | Seller（:217） | :423 | ✓ |
| complete :433 | Buyer（:218） | :437 | ✓ |
| claim_timeout :454 | Anyone permissionless（:219） | 无 require；守卫在 core::claim_timeout 重推导（core.rs:170–178） | ✓ |
| cancel :468 | Buyer（:220） | :472 | ✓ |
| open_dispute :487 | BuyerOrSeller（:221） | :493 | ✓ |
| apply_committee_verdict :520 | Committee+caller∈signers（:222） | :530 `require(Access::Committee)` + :531–533 `caller ∈ cert.signers` | ✓ |
| committee_config :545 | Broker（:223） | :547 + R5 threshold>0 门 ：554 | ✓ |
| getters :566/:583/:594/:605 | Anyone 只读（:224） | 无资金效应（due_deals(now) 调用方时钟已文档化为 advisory，:599–604） | ✓ |

require 单点（:230–246）：caller 经 `ctx.caller: Address` 字符串化（EIP-55，T4.5 探针钉死）；Committee 臂查 `state.committee_members` **空集即拒=fail-closed**（:243）。certified 回调面不入矩阵的口径与 committee_certified.rs 模块头 E2 门禁台账一致（origin=ZERO 使地址门必 fail-closed，台账承担审计面）——两处互相印证，无漂移。

**攻击者视角滥用路径 5 类判定**：

1. **签名/证书重放与跨单复用 —— 不可达**。路线① wire 证书无 evidence_root 参数，`into_domain`（committee.rs:44–56）从**当前全量证据日志**折叠根 → 无「旧根」可供重放；跨单复用面 = apply_verdict 仅 Disputed（core.rs:199）+ 终态封死；`validate_cert`（core.rs:235–253）四查（成员/去重/阈值/根匹配）。路线② signers 来自平台证书 `ctx.cert.signers`（committee_certified.rs:356–380），映射失败即剔除（:373–379 不猜测身份）。**诚实边界照录**：路线① 无签名为已文档化 demo 占位（lib.rs:511–513，TODO(W4)），非新缺陷。
2. **阈值绕过 —— 不可达**。成员域阈值唯一写点 committee_config=Broker 门（:547）；e2 域阈值唯一写点 e2_configure=`eth_guard = creator`（committee_certified.rs:112 + 阈值 0 已拒 ：119–123）。两域阈值源均不可被非授权方改写。demo 路线① broker 位居成员集首位即单方可出证——README/report 信任表的已文档化 demo 信任模型（demo.py:68–72 自述），路线② 已给出真实替代。
3. **重复结算 —— 不可达**。终态封死（types.rs:51–53 + core.rs require_states :29–37）；complete×2 / complete 后 verdict / verdict 后 claim 全被 Terminal/WrongState 拒；verify_core 实跑 modelcheck_refund 2/2（all_orderings 两测试）本轮复核仍覆盖当前代码（G5 全过）。
4. **伪造署名 —— 不可达（自署名内）**。notarize from==caller 强制在共识入口（lib.rs:407）；`check_evidence_shape`（committee.rs:66–74）只认卖家→买家方向条目 + deliverable 匹配。payload 冒充仍属「digest 即身份、无签名」的已文档化信任洞（committee.rs:53 注记 + 报告信任表），判定在洞范围内，不判新缺陷。
5. **未注资取款 —— 不可达**。claim_timeout 仅 Funded 且过 deadline（core.rs:170–178，未到→DeadlineNotReached）；cancel 无证据才可（core.rs:82–92；Qualified 取消=全零 payout，F2 测试 core.rs:524–544 钉死）；apply_payout 全零 no-op（lib.rs:726–737 三个 `>0` 门实读复核）；faucet 无上限 + BROKER=anvil#0 硬编码（lib.rs:208）作为已文档化 demo 信任洞（:277–279 TODO(W2)）重申。

### 2.2 焦点② 经济不变量

可达转移 × 守恒核对（每转移后 `Payout::total() == deal.amount`，或 Qualified 取消=0）：

| 转移 | Payout | 守恒证据 |
|---|---|---|
| fund（lib.rs:357–397） | —（入账） | 预检（:371–374）→ core::fund → debit 顺序契约实读在案（:366–372 注记）；重复 fund 被 require_states 拒 |
| complete BuyerConsent（:433–449） | settle | fee=saturating_mul/10_000 min-clamp（types.rs:165–172），to_seller=amount−fee 恒不 underflow；core 测试 fee_rounding_edges_conservation:476 / split_never_underflows:499 钉死 |
| complete Committee（core.rs:138–161） | settle 或 full_refund | F1/F4 终态映射测试 :549–590/:593–615 |
| claim_timeout（core.rs:170–178） | full_refund | 仅 Funded+过 deadline |
| cancel（core.rs:82–92） | full_refund 或全零 | Qualified=全零（F2）、Funded=全额；core.rs:432 测试 |
| apply_verdict（core.rs:191–218） | 三裁决映射 | Fulfilled→settle / NotFulfilled→full_refund / Malicious→full_refund+misconduct+1（:205–208）；Malicious 不罚没（slash 分支=登记死代码，P2-3） |

- **记账单点复核**：`credit`（lib.rs:693–703，A2 checked_add 实读在案；5 个调用点 ：288/:727/:730/:733/:736 全部带 `?`）；`debit` 预检（:684–690）。credit 失败路径 = checked_add 失败在**余额写回之前**返回 Err → 无半写副作用（A2 复核通过）。
- **fee/溢出边界**：fee_bps 上限 core::create（core.rs:54–56，lib.rs:317–319 注记不重复检查的分工在案）；fee_bps=10_000 → Fulfilled 仍 Settled（F4 测试在案）。
- **P2-11 重评**：`Payout::total()`（types.rs:174–176）裸加。实查构造面：Payout 仅由 settle（to_seller+fee=amount，余 0）/full_refund（refund=amount）/全零三形构造，total() ≤ amount 恒成立、不依赖入账侧；且 total() 消费点仅 debug_assert（lib.rs:725）与测试，**不在任何资金决策路径**。回绕不可达 → **维持登记**（types.rs 冻结约束不变）。
- **新边界发现 N3**（§3）：apply_cert_and_payout 的 misconduct 写回（lib.rs:788–791）先于 apply_payout（:792）——仅在「平台 Err 无原子回滚」+ credit 溢出（需 faucet 级荒谬余额）同时成立时产生「deal 已终态、payout 未落地」的资金滞留（fail-stuck 非 fail-open），faucet 信任洞边界内，P2。

### 2.3 焦点③ R5 修复正确性复核（结论：四项全部「未引入新问题」）

| 修复 | 复核证据 | 结论 |
|---|---|---|
| A1（committee_config threshold==0 拒，lib.rs:554） | 门的位置在 require（:547）之后、状态清写（:555–559）**之前**——顺序正确；误伤面 grep 实跑：全部调用点非 0（demo.py:610 E2_THRESHOLD=4、demo.py:792 THRESHOLD=3、broker.py:59 默认 3） | ✓ 无误伤 |
| A2（credit checked_add，lib.rs:700） | 失败在写回前返回 Err（无半写）；5 调用点带 `?` 实读在案；wasm release 无溢出检查的前提由 checked_add 覆盖 | ✓ 无回归 |
| B1a/B1b（demo.py:369–373 timeout 断言、:322–325 normal 断言） | 断言均只落在 `if node_mode(node):` 分支内；sim 分支零改动——G3 实跑 `BASELINE-DIFF-IDENTICAL` 为行为证据 | ✓ sim 逐字保持 |
| C1/C2（keeper.py:151–152 interval 门、:156–158 deals 门） | fail-closed 退出（p.error）而非静默空转；discover 默认路径（:161）不受影响（实读） | ✓ 无回归 |

### 2.4 焦点⑤ Python 编码层深审

- **_ABI × lib.rs 签名逐行对齐**（实读两侧）：faucet(string,uint128)=lib.rs:281 U128 边界转换 :286；create_deal 8 参（string×2,uint128,uint16,string×2,uint64,uint8）=lib.rs:296–306；fund/notarize/submit_deliverable/complete/cancel/open_dispute 参数面一致；apply_committee_verdict(string,uint8,string[])=lib.rs:520 扁平 wire；committee_config(string[],uint32)=lib.rs:545；claim_timeout→bool=lib.rs:454 返回 bool；balance_of→uint128=lib.rs:594 U128；due_deals(uint64)→string[]=lib.rs:605；assess_brief(string×4)→string=lib.rs:640–646；e2_arm(string)→bool=lib.rs committee_certified.rs:161；e2_run_verdict_round()→bool=:401；e2_net_config()→string=:192。**未发现漂移**。notarize 链上返回 u64 而 NodeClient 回执无返回值——已文档化不对称（rpc.py:566–569）。
- **编码器支持集**：_enc_value（string/string[]/uint*/bool，集外 ValueError :227）+ _is_dynamic（string/string[]）；R2 修正（偏移相对 tail 起点）实读在案（:207–222 编码、:254–267 解码）；**仍无 bytes32/bytes32[]** = 终裁冻结条款 1（e2_configure 走 cast send，:158–162 注记 + :685–697 实现）——零扩展合规。
- **错误路径**：NodeError 携带原始错误不折叠（:165–178）；TxError status≠0x1（:181–182 + :483–485）；_rpc 对非 JSON 响应 `r.json()` 裸抛、HTTP 错误 raise_for_status、连接异常裸抛（:441–450）= **P1-R1 维持登记**（重评见 §6）；NodeClient 写路径无 assert 依赖（全 raise），`python -O` 消失面仅限 FakeNode（P2-6 既有）。
- **protocol.py × core.rs 逐字节同规复核**：canonical 串 `"{seq}|{from}|{to}|{payload_digest}|{slot}\n"` 字段序/分隔符/UTF-8/空表=`cbf29ce484222325`/顺序敏感不重排两侧一致（protocol.py:65–90 vs core.rs:287–298）；G2 selftest 七向量（含官方 FNV ×2）实跑通过为行为证据。
- **P2-5 载荷域实查**：demo/broker/dashboard 全部 envelope/payload 字段域实读为 ASCII（terms/reason 字面串 + hex digest + 整数）；dashboard ops-reason 为用户输入可含非 ASCII，但其 digest 页内自算自用、与 demo/broker 规范化结果**无任何交叉比较点** → 分叉不可达，维持登记。
- **调用方交叉**：keeper 直用 `_send`（:116）+ 读回纪律（:123–131）在案；demo B1a/B1b 断言在案；agents CLI 新发现 N5（alice/bob 无 sender 选择，§3）。

### 2.5 焦点⑥ dashboard 只读交互面复核（三项纪律）

1. **选择器冻结一致** ✓：页内 SEL 表（dashboard.html:601）与 OPS 表（:848–890）共 16 个 selector 与 rpc.py `_ABI` 逐一比对全一致（ec78f86e/3e6b4459/16417010/4704839a/2b5d6a4a/b540def8/bd827024/b1fecd5a/73451f65/7ecc9d46/ad932b5c/a48ab911/786cfc8f/15df3c73/8b7acf91/a32974e3）；e2_configure/e2_run_verdict_round 无页内调用（组标注指回 demo.py --flow committee，:884）——cast 通道纪律一致。
2. **status 0x1 ≠ 方法 Ok 读回纪律** ✓：sendTx 回执行明示「已排序≠方法成功，读回见下」（:814–818）；手动操作台 runOp 每笔后强制 opsReadback()（:916–917）；LIVE 预设 liveStepTx 按期望终态 liveWaitState（:985–1001，超时抛错不静默）。与 keeper/demo 同口径。
3. **e2_arm 单次纪律**：LIVE 三预设零调用 e2_arm（8b7acf91 仅存在于手动按钮 op-arm，:888–889，带 ⚠ 单次标注）；**纪律为文档级标注、无硬锁**（重复手动点击可重发，但 armed_deal 重写的影响被 propose 的 Disputed 门 + aggregate 拒证 fail-closed 兜底）。判定：与 demo.py「绝不重复 e2_arm」读回纪律相比属轻微漂移，登记不修（只读件；若构成 P0 修复也只能落 rpc.py/文档侧——本轮判定不构成，见 N6 同类竞态面）。
- 附记：页内 LIVE 对抗预设的 committee_config([broker,node-1..3]) 会**覆盖**实例 NodeID 制配置——页面已自带 ⚠ 覆盖警示（:1134），知情面，登记不修。

## 3. findings 清单（分级全表）

判定口径 = §4：P0（资金语义/守恒、越权可达、误报漏报、fail-closed 失效）必修；P1 加固择优（三准入）；P2 只登记。**本轮 P0=0、P1 达准入=0。**

| ID | 级别 | 位置 | 问题一句话 | 证据 | 处置 |
|---|---|---|---|---|---|
| N1 | P2 | lyquid/src/lib.rs:412 | notarize 对不存在的 deal_id 也建条目（`evidence_log.entry(..).or_default()` 无 deals 存在性检查） | 实读；FakeNode 刻意收紧为「no such deal」（rpc.py:840–844 并自注「real node appends regardless」） | 登记（P2-6 同类非镜像面；零资金效应——裁决前有 deal 存在+Disputed 门） |
| N2 | P2 | lyquid/src/lib.rs:398–416 | notarize 无状态守卫，终态后仍可追加证据条目 | 实读（无 require_states/deal 查询）；影响面 = 无（后续裁决被 Terminal/Disputed 门拒，committee_cert 存证为历史记录） | 登记 |
| N3 | P2 | lyquid/src/lib.rs:788–792 | apply_cert_and_payout 中 misconduct 写回先于 apply_payout；若 apply_payout Err 且平台无原子回滚，则 deal 已终态而 payout 未落地（资金滞留托管） | 实读顺序（:784 deal 变更 → :788–791 misconduct → :792 payout）；触发需 credit 溢出 = 接收方余额近 u128::MAX，仅 faucet 级荒谬输入可达（lib.rs:698–699 同类登记）；fail-stuck 非 fail-open（不多发一分钱） | 登记（与 P2-11/A2 同信任洞类；W2 DEMO flag 处置时一并收敛） |
| N4 | P2 | scripts/keeper.py:94–96/:116–121 | poll_once 只捕 (NodeError, TxError)；requests 层 ConnectionError/Timeout/非 JSON 响应裸抛将终止 keeper 主循环 | 实读 except 子句；rpc.py:441–450 裸抛路径在案 | 登记（= P1-R1 在 keeper 落点的重申；安全视角无资金风险：claim permissionless+幂等、买方可自行 claim、keeper 重启即恢复） |
| N5 | P2 | agents/alice.py:33/:41、agents/bob.py:25/:33 | alice/bob CLI 无 sender 选择，node 模式写通道默认 anvil#0，与角色门（Buyer/Seller/自署名 from）不匹配 → 链上 Err 被吞（status 仍 0x1） | 实读（两文件无 sender= 参数；rpc.py:437 默认 DEFAULT_SENDER）；失败可见非隐蔽——后续 deal_info 读回打印显示真实状态（如 fund 后 state=Qualified） | 登记（独立 CLI 辅助面，编排主路径=demo.py 已显式传 sender；P2-7 同类 agent CLI 独立入口） |
| N6 | P2 | scripts/keeper.py:115–126 | 重复 claim 竞态下 action 归因失真：deal 已被他人 claim 后，本 keeper 的 _send 仍 status 0x1、读回 Refunded → report 记 action="claimed" 附本次 tx | 实读；permissionless 幂等竞态的既文档化面（keeper docstring「rejections are free」）；状态本身正确，仅 tx 归因不精确 | 登记 |
| P2-1残 | P2 | agents/common/rpc.py:56；agents/alice.py:16 | 死 import 残量：rpc.py `field`（dataclass 未用 field()）；alice.py `Acceptance`/`Deliverable`（未构造） | grep 实跑（rpc.py 全文 `field` 仅 import 行命中定义外用法；alice.py 两类型零使用） | 登记（P2 不修） |
| P2-2残 | P2 | agents/common/rpc.py:426/:500/:648/:809/:895–897/:911–915；agents/common/protocol.py:19；scripts/demo.py:16 | 行号注释漂移残量（指向旧版行号）：lib.rs:624→require 现 :230–246；lib.rs:241→faucet 现 :281；lib.rs:625-635→assess_brief 现 :639–676；lib.rs:189→现 :320；lib.rs:365-368→现 :530–533；lib.rs:369-371→现 :768–770；rpc.py:49→notarize wrapper 现 :564–569；lib.rs:367-369→自署名检查现 :406–409 | `grep -n "lib.rs:[0-9]"` 实跑 + 逐处与当前行号对照 | 登记（惯例：不改写） |

**P1 择优池结论**：P1-R1/R2/R3（R5 残留）经本轮安全视角重评**均不升级**（§6），亦无新增达三准入的 P1——零改动即择优结果（改动面最小=0）。

## 4. 修复 diff 摘要

**无修复实施——零 diff。** 证据链：

1. `git diff -- lyquid/src scripts agents` 在开工前即存为 0 字节 patch（`workflow-out/_pre-task-snapshot-r6.patch`，#A3），收尾时 `git diff --stat` 仍为空；
2. 13 份开工前原件 cp 留档 `workflow-out/_r6-orig-*`（回退通道未动用）；
3. G3 sim 输出与冻结基线 `diff -u` 零差异（逐字保持的强验证）；
4. 只读件 md5 前后一致：`scripts/dashboard.html` = `a2206ffcca6cbe2fddb632071bf76709`（开工前实取 = 收尾实取）。

## 5. 门禁复跑实录（G1–G5）

| # | 门禁 | 命令（实跑） | 结果 |
|---|---|---|---|
| G1 | 语法 | `python -m py_compile agents/common/rpc.py agents/common/protocol.py agents/common/llm.py agents/alice.py agents/broker.py agents/bob.py scripts/demo.py scripts/keeper.py` | `PY_COMPILE-ALL-OK`，rc=0（零改动 py，按方案对全部在范围文件复跑留记录） |
| G2 | 自检 | `python scripts/demo.py --selftest` | rc=0，`SELFTEST OK`（尾 3 项 PASS：deterministic/order-divergent、官方 FNV 向量 ×2） |
| G3 | sim 基线 | `python scripts/demo.py --sim --flow all` → `diff -u workflow-out/_r2-t0-sim-baseline-raw.txt <输出>` | rc=0，`BASELINE-DIFF-IDENTICAL`（零差异） |
| G4 | Rust 编译（只读） | `MSYS_NO_PATHCONV=1 docker exec -w /tmp/tb-lyquid multi-tools cargo check --target wasm32-unknown-unknown` | rc=0，`Finished dev profile … 0.17s`，**33 条 warning**（与规划期 §1-5 同量级；零源码改动故未 touch、未重编） |
| G5 | 模型检查壳 | 仓库外 `workflow-out/verify_core`：`cargo test --lib --tests` | **40/40**：lib 33（core 23+committee 4+assessor 6）+ escrow_lifecycle 5 + modelcheck_refund 2，0 failed（types/core 零语义改动，按 §5-G5「未改也建议复跑一次留记录」执行） |

## 6. 与 R5 台账的差异说明（15 项逐条）

R5 台账原文 = `workflow-out/_plan-prev-r6-backup.md` §2.2/§5。逐项按**当前代码**实查后的处置：

| ID | R6 处置 | 理由（本轮证据） |
|---|---|---|
| P1-R1（rpc.py:441–450 裸抛） | **维持登记** | R5 理由（控制改动面）仍成立；R6 安全重评：无资金风险——claim permissionless+幂等、失败可见、keeper 重启即恢复（N4 已登记 keeper 落点）。无钉死测试护航，不达 P1 准入第三条 |
| P1-R2（broker.py:31、llm.py:62 畸形 LLM 响应） | **维持登记** | 仅真实后端路径（默认 ScriptedLLM/HeuristicModel 回放）；R6 复核 assess_brief 链侧面有 parse_report 先行把错（assessor.rs:184–198），暴露面进一步收窄至 agent CLI 的 live 模式 |
| P1-R3（timeout.rs:61 `.ok?` 整轮中断） | **维持登记** | §3.4 预判成立：DoS 型延迟非资金错误；watcher 无许可且幂等、keeper 每轮重试自愈；T1 复核守卫面不依赖 watcher 及时性（claim_timeout 任何方可提交）；修复须重编 wasm，收益近零（watcher_step 当前无驱动方，keeper 为已定稿主路径） |
| P2-1（死 import） | **维持登记 + 残量实查** | R5 已顺带修 demo.py SLOT_MS（现 :59–65 实查无）；本轮残量 = rpc.py:56 `field` + alice.py:16 Acceptance/Deliverable（grep 实证） |
| P2-2（行号注释漂移） | **维持登记 + 残量实查** | R5 已修 6 处；本轮实查残量 8 处（P2-2残 行，含方案 4 处之外新实查的 rpc.py:648/:809、demo.py:16） |
| P2-3（shim/常量/slash 死代码） | **维持登记** | committee.rs:78–90 shim（apply_cert_and_payout :766 直读 network 状态，不调 members()——实读复核）；timeout.rs:86 已裁决常量；lib.rs slash 分支现 :735–737（core 无任何 slash>0 构造点——全库实读）；lyquid 面删除须重编 wasm |
| P2-4（`_ => Malicious` + sim KeyError） | **维持登记（红线内）** | 判级行为红线④；W4 oracle 签名认证处置。rpc.py:919 sim KeyError 仅 demo 侧固定 0/1/2 可达 |
| P2-5（双规范化） | **维持登记** | 载荷域全 ASCII 实查（§2.4）；dashboard 用户输入无交叉比较点，分叉不可达 |
| P2-6（FakeNode 非镜像 + assert -O） | **维持登记** | sim=编排冒烟定位不变；N1 是本轮对该类的补充登记（notarize 不存在 deal 收紧面） |
| P2-7（broker.py:57–59 硬编码成员） | **维持登记** | agent CLI 独立入口；与 rpc.py get_node_ids「禁硬编码」口径相悖仍在案（W4 一并） |
| P2-8（due 扫描 3× deal_info） | **维持登记** | node-only 效率面，demo.py:358–361 实读确认仍在 |
| P2-9（wait_for node 形参未用） | **维持登记** | demo.py:147 签名稳定性优先；predicate 闭包捕获 |
| P2-10（threshold>成员数可配置） | **维持登记** | fail-closed 方向（恒 InsufficientCommittee，core.rs:245–247 实读）；非安全洞，建议 W4 与 EvidenceMismatch 一并 |
| P2-11（Payout::total 裸加） | **维持登记** | T2 重评：构造面三形均使 total()≤amount 恒成立，且 total() 不在资金决策路径（仅 debug_assert+测试）；types.rs 冻结约束不变 |
| P2-12（文档行号漂移） | **维持登记（只读件）** | demo-script.md、docs/演示与运行指南.md 未改写；本轮代码零改动故漂移面零新增 |

**映射总结**：15 项 = 15 维持登记、0 升级必修、0 本轮顺带修。本轮新 findings N1–N6 全为 P2（N4 与 P1-R1 同根、N5 与 P2-7 同类、N1 与 P2-6 同类；无 R5 分级冲突）。

## 7. 伴随产物与工作树终态

- #A2 备份：`workflow-out/_implementation-prev-r5-backup.md`（覆写前 cp，md5 双侧一致 `a92ac14061798943f5f3be9d066c8af2`）；
- #A3 快照：`workflow-out/_pre-task-snapshot-r6.patch`（0 字节 = 开工前代码目录零改动）+ `workflow-out/_r6-orig-*` 13 件；
- #A4 本轮基线 sim 输出：`workflow-out/_r6-baseline-sim-out.txt`；
- 只读件核验：`scripts/dashboard.html`、`docs/b3-user-test/`、`workflow-out/report/`、`workflow-out/slides/`、`_submission-plan.md` 零改动（git status 未出现 + dashboard md5 前后一致）；
- 零 git 写（未 commit/add/push/branch/tag/restore/stash）；devnet 零链写零部署零重启（全部验证只读：selftest/sim/py_compile/容器 cargo check/壳 crate cargo test）；
- 本文件为 workflow-out/implementation.md 的 R6 覆写（本轮唯一实质写入件）。
