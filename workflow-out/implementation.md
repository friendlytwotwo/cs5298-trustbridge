# W1-B2 收尾实现说明（claim_timeout 空 revert 根因闭环）

> 实现人：编码员（2026-10-28）。方案：`workflow-out/plan.md`（审查通过版，T-init/T0–T7）。
> 执行基线 = 当前工作树（含未提交 W1-B2 成果，未回退）。T0 快照：`workflow-out/_pre-task-snapshot.patch`。
> 上一轮（W1-A）的累计实施台账已由编排流程备份为 `workflow-out/_implementation-prev-w1a-backup.md`
> （本轮 `implementation.md` 按当前轮重建，备份件未删）。
> 全部结论均来自本轮实跑；命令与输出摘要见 §3 与各证据文件。

---

## 1. 总览与门禁结果

| 门 | 内容 | 结果 |
|---|---|---|
| G-init | docker 守护进程 / 节点 API / 宿主 cargo 三项预检 | ✅（③ 先失败→修复 rustup+rust-std，见 §4-1） |
| G0 | 壳修复（路线① 存根）后 `cargo test --lib --tests` 全绿 | ✅ **33+5+2=40**（路线①，非 39；漂移声明见 `w1b2-shell-rebaseline.txt` §5） |
| G1 | 探针 `probe_claim_sim` 编译零 error + types/core 零改动 | ✅（wasm target 检查，原因见 §4-3；`git diff types/core` 空） |
| G2 | 新实例镜像自证（D3 导出面可路由） | ✅ `balance_of`→`0`（旧实例 FuncNotFound 消失）；探针可路由 |
| G3 | `deal-1` Funded 且块高 > deadline | ✅ Funded / block 103 > deadline 102 |
| T4 | 探针 A~H 佐证 | ✅ F=Ok(full_refund)、G 勾稽 true、H=PASS-full-refund |
| G6 | keeper 实测退款 | ✅ tx `0x85e4e39b…ae0838`、`state:"Refunded"`、余额 +1000、日志在档 |
| G7 | 探针移除 + 终验 | ✅ 零残留 / core 冻结 / 壳 40/40 / finding 已注记 |

新实例：`Lyquid-xydh5ecomgg2rukd7qbw6gjv7cuf4uiktzbaa` @ `0xA4899D35897033b927acFCf422bc745916139776`
（Platform 0.8 / LDK 0.8.1，镜像 `sha256:45a96668ef47be1ac23a487bb1cb8d83c79eac2a49bb450a05b12590cc4c17e7`）。
旧实例 `0x1c85…` 未动（D1 证据存档）。

---

## 2. 逐文件改动

### 2.1 `trustbridge/lyquid/src/lib.rs`（T1 加 / T7 删 + 两处必要编译修复 + 一处登记性偏离）
- **新增探针 `probe_claim_sim(ctx: &_, deal_id: DealId, now: u64) -> LyquidResult<String>`**
  （置于只读 getter 区 `deal_info` 之后，形态照 `deal_info`）：
  - `#[method::network(export = eth)]`，只读；`state.deals.get()` 读 clone 模拟，
    `core::claim_timeout(&mut sim, now)` 只跑在克隆体上；**不调用 apply_payout、不写任何状态**。
  - A~H 阶段：每阶段先 push + `lyquid::println!("probe_claim_sim: …")` 外发，再执行风险操作
    （trap 时最后一条阶段行即失败点）；D 阶段双记 `chain_now=current_slot()` 与
    `caller_now=入参 now`；E/F/H 一律用 caller_now；结尾整包 `serde_json::to_string(&stages)`
    再 println + 返回（正常通道）。
  - 全块以 `// W1-B2-claim-debug probe BEGIN/END` 包裹（T7 整块删除）。
- **ACCESS_MATRIX 新增一行**（只读 getter 行之前）：
  `("probe_claim_sim", Access::Anyone), // W1-B2-claim-debug probe-removable（只读模拟，无守卫面）`
  —— T7 已随探针删除。
- **T7 终态**：探针块 + 矩阵行 + 标记注释全部移除；
  `grep -rn "probe_claim_sim\|W1-B2-claim-debug" lyquid/ scripts/ agents/` 零命中。
  lib.rs 相对 T0 快照仅余 3 处登记性偏离（见 §2.2、§2.3 与 §4-5），无探针残留。

### 2.2 `trustbridge/lyquid/src/lib.rs` — 必要编译修复（**持久**，登记）
> 背景：当前工作树基线在本轮之前**从未成功编译**（wasm target），两处 `map_err` 类型不匹配。
- `assess_brief` 内：`assessor::LyquidLlmModel::new(...).map_err(lyquid_error)` →
  `.map_err(|e| lyquid_error(&e))`（E0631：String → &str 转接；语义零变化）。
- `assess_brief` 内：`assessor::report_json(&report).map_err(lyquid_error)` → 同上闭包形式。
- 说明：plan 的「不动 W1-B2 未提交基线」按意图理解为不回退/不改语义；不修此处则 G1
  「cargo check 零 error」不可能达成。改动仅错误转换形态，无行为差异。

### 2.3 `trustbridge/lyquid/src/lib.rs` — `assess_brief` 撤下 `export = eth`（**持久偏离**）
- `#[method::instance(export = eth)]` → `#[method::instance]`；方法体/签名/assess 语义零改动。
- 原因（本轮实测定位，不是猜测）：shaker 生成的 `SequenceBackend.sol` 中，
  `assess_brief` 的 7×string 参数 instance 桩触发 solc「Stack too deep」
  （`Variable dataEnd is 2 slot(s) too deep`）；0.8.24 / 0.8.30 / 0.8.37 三版 solc 均复现；
  逐函数删除二分显示**删除该桩即编译通过**，桩签名变体显示「6×string 参数通过、7×string 失败」。
- 影响面：仅失去 assess_brief 的 eth 远程调用面；仓内无任何调用方（`grep` 仅命中注释/文档），
  本轮所有交付（探针、keeper 退款）不依赖它。平台栈上限放宽后可原样恢复。
- 证据：`workflow-out/w1b2-claim-probe-evidence.txt` §2；代码处已写明偏离登记。

### 2.4 `trustbridge/lyquid/src/probe/s2_oracle.rs`（**持久**，必要编译修复）
- `propose()` 末尾 `Ok(proposal)` → `Ok::<ProbeProposal, LyquidError>(proposal)`。
- 原因：wasm target 下 rustc 1.99.0 报 E0282（无法推断 Err 型参）。该文件是 HEAD 既有
  W1-B1 探针代码，与本轮 claim 探针无关；不改则新镜像无法编译（G1/G2 均阻塞）。

### 2.5 `trustbridge/scripts/keeper.py`（T5，**持久重写**）
- 传输层改为 **NodeClient**（`agents/common/rpc.py`，只复用不改）：
  - 顶部 `sys.path.insert(0, parents[1])` + `from agents.common.rpc import DEFAULT_NODE, NodeClient, NodeError, TxError`
    （demo.py:17-18 同款先例）。
  - 删除旧 `cast()` / `decode_abi_string()` / `deal_state()` / `claim_timeout()` 四个
    docker-exec/cast 函数与 `--container/--rpc` 参数。
  - `poll_once(node, deals)`：`node.deal_info()` → 状态机（Settled/Refunded→terminal，
    非 Funded→skip）→ Funded 时 `node._send("claim_timeout(string)", (deal_id,))`
    （**直取回执**，不走 rpc.py:330 的 `claim_timeout` 公开封装——它丢回执且恒 True）
    → 读回复核 `deal_info`，仅 `state=="Refunded"` 记 `action=claimed` 并附
    `tx=receipt["transactionHash"]`。
  - 读回带 5×0.4s **终局延迟重试**（本轮实测：fund 后首次读回仍为 Qualified，
    见 `w1b2-claim-probe-evidence.txt` §4；NodeClient._poll_deal 同思路）。
  - `NodeError`/`TxError` → `action=not-due-or-reverted`（沿用旧语义，含错误文本）。
- CLI：`--node`（默认 DEFAULT_NODE）、`--contract`、`--deals`、`--interval`、`--once`；
  日志格式保留 `[keeper HH:MM:SS] deal: {json}`；docstring 按 D2/§B-⑤ 改写（删除 cast send/
  gas estimation 叙述；"Stdlib only" → 依赖 agents/common（requests），登记性偏离）。
- 门 T5：`python -c "import ast; ast.parse(...)"` → OK；模块可导入 → OK。

### 2.6 `trustbridge/workflow-out/w1b2-claim-probe-evidence.txt`（新建，交付物）
新实例部署记录（含 solc 阻塞与处置 §2）、md5 自证、G2 路由自证、T3 建单输出、T4 命令行 +
A~H 解码字面 + **chain_now/caller_now 双值** + raw hex（附录 A，800 字节）+ `shaker console`
阶段行截取 + 节点日志通道事实登记（docker logs 无 println → 改用 console）。

### 2.7 `trustbridge/workflow-out/w1b2-refunded-evidence.md`（新建，交付物）
tx hash `0x85e4e39b628a358ef7cd61bfc8c87e67a730c76617a823a6001a87ea86ae0838` + 回执要点
（status 0x1 / block 104 / from #0）、`deal_info` 前后字面（Funded→Refunded）、
`balance_of` 999002→1000002（+1000）勾稽、keeper 日志摘录、复现命令清单、幂等说明、关联偏离。

### 2.8 `trustbridge/workflow-out/w1b2-shell-rebaseline.txt`（新建，交付物）
G-init 实测（含宿主工具链损坏与修复全过程）→ 修复前失败输出（E0432/E0433）→
§2-1a 容器实证**本轮复跑**（E0425/E0432 NativeGuestAbi 首发证据）→ 路线①修复后 40/40 →
39→40 漂移说明 → §6 T7 终验（零残留/core 冻结/lib.rs vs T0 差异三处/壳复跑 40/40）。

### 2.9 `trustbridge/workflow-out/w1b2-claim-revert-finding.md`（头部注记，正文未改）
头部插入 SUPERSEDED 块：wasm-panic 假设作废；根因 = D1 旧镜像 + D2 写通道限制；
指向两份新证据；附带本轮正面结论（chain_now=103≠0 排除 now=0 假设）。

### 2.10 `trustbridge/workflow-out/_pre-task-snapshot.patch`（新建，T0 快照）
`git -C trustbridge diff > workflow-out/_pre-task-snapshot.patch`（1531 行；覆盖 5 个已改文件
+ implementation.md 删除；未跟踪的 evidence 文件不在 patch 内，属预期）。全程未 `stash/checkout/reset`。

### 2.11 `trustbridge/workflow-out/_w1b2_t3_replay.py`（新建，复现脚本）
T3 造单脚本（faucet→create_deal(est=200ms)→fund→automine 补块→G3 自检），供证据文件复现引用。

### 2.12 `downloads/202609CS5298/workflow-out/verify_core/`（parent 级，**持久**壳修复）
- `verify_core/Cargo.toml`：`[dependencies]` 增 `lyquid_llm = { path = "stubs/lyquid-llm" }`
  （附路线① 理由注释）。
- `verify_core/stubs/lyquid-llm/Cargo.toml`：package name = `lyquid_llm`、`edition 2021`、
  `serde_json = "1"`、`publish = false`。
- `verify_core/stubs/lyquid-llm/src/lib.rs`：最小签名面（assessor.rs 全部消费点）——
  `backend::openai_compat::OpenAiCompatBackend::{openai, chat_completions, bearer_auth, output_format}`、
  `ModelRequest::{new, timeout_ms, max_output_tokens, system}`、`OutputFormat::json_schema`、
  `ModelResponse { text }`、`call_model(...) -> Err(LlmError)`（测试不触 LLM 路径）。
- 壳仍挂**工作树** assessor → 计数 33+5+2=40（路线①，见 `w1b2-shell-rebaseline.txt` §4/§5）。
- 壳内 `#[path]` 保持宿主绝对路径原样（宿主 cargo 已修复，未走容器路线，无需改写）。

### 2.13 宿主环境（非仓库文件，**环境修复**）
见 §4-1（rustup 重装 + stable 工具链重装）。修复后 `cargo 1.99.1` / `rustc 1.99.1`。

---

## 3. 关键命令与输出摘要（本轮实跑）

```bash
# G-init ①/②/③
docker ps --format ...                                   # 7 容器全 Up（multi-*）
curl -s -X POST http://127.0.0.1:10087/api ... eth_blockNumber
#   → {"jsonrpc":"2.0","id":1,"result":"0x60"}
cargo --version                                          # 初始: command not found → 修复后 cargo 1.99.1

# T0-1 快照
git -C trustbridge diff > workflow-out/_pre-task-snapshot.patch   # 1531 行

# T0-2 壳：修复前（复现 plan §2-1）
cd workflow-out/verify_core && cargo test --lib --tests
#   → error[E0433]/[E0432] lyquid_llm unresolved（assessor.rs:37/38），exit=101
#   加 stubs/lyquid-llm + Cargo.toml path 依赖后：
cargo test --lib --tests
#   → 33 passed / 5 passed / 2 passed，exit=0（=40）

# §2-1a 容器实证复跑（git pin 路线不可达）
docker cp . multi-tools://tmp/probe-llm/ && docker exec -w /tmp/probe-llm multi-tools cargo check --offline
#   → error[E0432] unresolved import `super::NativeGuestAbi` + E0425 ×3，exit=101

# T1 容器编译（注意：容器名 multi-tools，非 multi-tools-1）
docker exec multi-tools rm -rf /tmp/tb-lyquid && docker cp lyquid multi-tools:/tmp/tb-lyquid
docker exec -w /tmp/tb-lyquid multi-tools cargo check --target wasm32-unknown-unknown
#   首次：error[E0282] s2_oracle.rs:104 + E0631 lib.rs ×2（基线从未编译）
#   修复后：Finished dev profile（26–28 warnings 均为既有），exit=0
md5sum lyquid/src/lib.rs  vs  docker exec multi-tools md5sum /tmp/tb-lyquid/src/lib.rs
#   → e62d363f0972e7307c42d57ce7ebfdd4（两侧一致）

# T2 部署
docker exec -w /tmp/tb-lyquid multi-tools shaker deploy -r http://registry:8000/lyquids \
  --endpoint ws://node1:10087/ws --private-key 0xac09…ff80 Cargo.toml
#   首次两次失败：Failed to compile SequenceBackend.sol: Stack too deep（dataEnd 深 2 槽）
#   solc 直接复现 + 逐函数二分 + 签名变体 → 定位 assess_brief 桩（§2.3）→ 撤 export 后：
#   → Status: created / Lyquid-xydh5… / 0xA4899D… / Platform Version 0.8，exit=0

# G2 镜像自证
docker exec multi-tools cast call --rpc-url http://node1:10087/api 0xA4899D… \
  "balance_of(string) returns (uint128)" 0xf39F…92266           # → 0（非 FuncNotFound）
#   probe_claim_sim(string,uint64) no-such-deal 0 → B:miss JSON（可路由）

# T3 造单（宿主 NodeClient；脚本 workflow-out/_w1b2_t3_replay.py）
#   faucet 1,000,000 → create_deal(deal-1, est_duration_ms=200 ⇒ timeout_slots=1) → fund
#   → deal_info: state=Funded, deadline_slot=102；补两笔 benign faucet 造块 → block 103
#   G3: Funded ✓ 且 103 > 102 ✓

# T4 探针（now = 实读块高 0x67 = 103）
docker exec multi-tools cast call --rpc-url http://node1:10087/api 0xA4899D… \
  "probe_claim_sim(string,uint64) returns (string)" deal-1 103
#   → A:enter caller=0x0 / B:found / C:state=Funded /
#     D:now chain_now=103 caller_now=103 chain_now>0=true /
#     E:deadline=Some(102) caller_now>=dl=Some(true) /
#     F:payout=Ok(Payout{to_seller:0,fee_to_broker:0,refund_to_buyer:1000,slash_to_treasury:0}) /
#     G:total=1000 ==amount=1000 true … /
#     H:verdict=PASS-full-refund 1000->0xf39F…92266 (now=caller:103)
#   宿主 curl eth_call 同 calldata → result 800 字节（offset 0x20, len 0x2d0）
#   节点日志无 println → shaker console 取得全部阶段行（证据 §6）

# T5 keeper 语法 + 导入
python -c "import ast; ast.parse(open('scripts/keeper.py', encoding='utf-8').read())"   # OK
# T6 keeper 实测
python scripts/keeper.py --node http://127.0.0.1:10087 --contract 0xA4899D… \
  --deals deal-1 --interval 5 --once
#   → [keeper 23:49:10] deal-1: {"state": "Refunded", "action": "claimed",
#       "tx": "0x85e4e39b628a358ef7cd61bfc8c87e67a730c76617a823a6001a87ea86ae0838"}
#   读回：deal_info state=Refunded；balance_of 999002 → 1000002（+1000）

# T7 终验
grep -rn "probe_claim_sim\|W1-B2-claim-debug" lyquid/ scripts/ agents/   # 零命中
git diff --stat lyquid/src/types.rs lyquid/src/core.rs                    # 空
#   T0 版重建（patch -p1 于 HEAD 副本）后 diff → 仅 3 处登记性偏离，无探针残留
cargo test --lib --tests（壳）                                            # 33/5/2 全绿
docker exec -w /tmp/tb-lyquid multi-tools cargo check --target wasm32-unknown-unknown
#   探针移除后最终树 → Finished，26 warnings，exit=0
```

---

## 4. 偏离与登记（plan 未预见或与 plan 字面不同）

1. **宿主工具链损坏比 plan §2-3 记录更深，已修复**：`~/.cargo/bin` 全部 shim 指向缺失的
   `rustup.exe`；rustup-init 重装后仍有 **rust-std 文件缺失**（`libcore-*.rmeta` 丢失 →
   `can't find crate for std`）。`rustup toolchain install --force` 不检测文件缺失，
   最终 `rustup toolchain uninstall stable && rustup toolchain install stable --profile minimal`
   修复（`cargo 1.99.1` / `rustc 1.99.1`）。完整过程见 `w1b2-shell-rebaseline.txt` §1。
2. **基线在本轮前无法编译（wasm）**：`s2_oracle.rs` E0282 + `lib.rs` 两处 E0631 已最小修复
   （§2.2/§2.4）。plan 未预见，属必要偏差，语义零变化。
3. **T1 门以 `--target wasm32-unknown-unknown` 执行**（plan 字面为容器内 `cargo check`）：
   host 目标下 **ldk 自身**即不可编译（`NativeGuestAbi` 被 `#[cfg(target_arch="wasm32"/"wasm64")]`
   门控，E0425；§2-1a 同证），故 host-target check 对该 crate 永远失败，不具判据意义。
   wasm 目标 = shaker 实际部署目标；该检查零 error 已达成。
4. **容器名**：实际为 `multi-tools`（plan 写 `multi-tools-1`，compose/历史文档为 `multi-tools`）。
5. **solc 平台限制导致 `assess_brief` 撤下 eth 面**（§2.3）——本方案最重要的偏离：
   不撤则 T2 部署不可能（G2 及之后全部阻塞）。已用 3 版 solc + 逐函数二分 + 签名变体定位，
   证据在 `w1b2-claim-probe-evidence.txt` §2。
6. **trap 定位通道修正**：`docker logs multi-node1-*` 默认级别**不含**任何 lyquid println
   （连 `deal_info:`/`fund:deal_view:` 也没有）；改用 `shaker console <lyquid_id>` 缓冲回放，
   阶段行完整可读。证据 §6 已如实登记 plan 口径的「未经可验证」结论为**实测不成立**。
7. **T4 读上下文事实**：eth_call 的 `caller=0x0`；`chain_now=103`（≠0）——正面回答
   finding.md「待查 a)」：`chain_pos` 在调用上下文有效，旧实例空 revert 与 now=0 无关。
8. **keeper 读回复核加终局延迟重试**（5×0.4s）：plan 只写「发送后读回」，但本轮实测 fund 后
   首次读回仍是 Qualified（读通道滞后一个块），不加重试会误判 `not-due-or-reverted`。
9. **壳硬约束「39/39」按意图执行**：路线① 挂工作树 assessor → **40/40**（33+5+2）；
   数字漂移与原因已留痕（`w1b2-shell-rebaseline.txt` §5）。
10. **keeper 依赖面偏离**：`stdlib only` → 依赖 `agents/common`（requests），按 D2/§B-⑤
    决策门登记（plan R7 已预判）。
11. **节点 API 宿主直连可用**：本轮 T3/T6 全程宿主 `127.0.0.1:10087` NodeClient，未用 R6 退路。

---

## 5. 未做 / 边界（如实）

- **已部署实例仍带探针**：为取证部署的镜像含 `probe_claim_sim`；T7 只移除**源码**（可移除性证明）。
  如需生产化，重新部署干净镜像即可（本轮不要求，且旧实例仅作实验物）。
- `lib.rs` 终态与 T0 快照**非逐字节相等**：差异 = §2.2/§2.3 的登记性偏离（3 处），
  无任何探针残留；plan §10「lib.rs 终态 == T0 快照态」按意图（无探针净变化）达成。
- plan §0 列表外的两处**必要**编译修复（§2.2/§2.4）与一处**必要**偏离（§2.3）已在此登记。
- `probe_claim_sim` 的 A~H 输出为 eth_call 读上下文（caller=0x0）；tx 上下文的 chain_pos
  已由既有实证（funded_slot=94==fund 块号）与本轮 keeper 退款（block 104 ≥ deadline 102）覆盖。
- 未改 `agents/common/rpc.py`（仅复用）、未改 `types.rs`/`core.rs`、未动旧实例 `0x1c85…`。
- 文档一致性抽查：README 不含 assess_brief/export=eth 叙述，无需同步；`docs/` 仅提
  `assess_brief` 返回类型（未变），无文档漂移。
