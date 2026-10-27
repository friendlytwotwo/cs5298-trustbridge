# W1-B2 R0 发现：claim_timeout 空 data revert（未解，调试记录）

时间：2026-10-27 23:0x | 实例：`Lyquid-ss7x5edzcxjszfykf3edlyl44etxn256htzqa` @ `0x1c85638e118b37167e9298c2268758e058DdfDA0`（multi 4 节点 v0.8.1，Platform 0.8）

## 已验证成功（R0 达成部分）
- escrow 部署上 multi（Platform 0.8）✅
- faucet / create_deal / fund 三笔 tx 全部 status=1（block 92/93/94），deal-1 进入 **Funded**（timeout_slots=1，deadline_slot=95）✅
- **deal_info 字面补验成功**：`cast call` 返回 DealView JSON 字面（W1-A 遗留项关闭）✅

## 未解：claim_timeout 发送稳定 revert，data=0x（空）
- 复现：`cast send --rpc-url http://node1:10087/api --private-key <anvil#0> <CTR> "claim_timeout(string)" deal-1` → gas estimation 阶段 `execution reverted`，data 0x；显式 `--gas 30000000` 同样失败
- 排除项：
  - 权限：ACCESS_MATRIX 中 claim_timeout = Access::Anyone（lib.rs:187），发送方 anvil#0 应通过
  - 导出缺失：源码 414 行已有 `#[method::network(export = eth)]`（W1-B2 编码员加），部署构建含此属性
  - deadline：块 96 > deadline_slot 95；funded_slot=94 证明 chain_pos().block() 在 multi 上与 anvil 块号一致（fund 时实证）
  - 状态：deal_info 确认 Funded
  - 对照：cast call fund 同样 FuncNotFound（call 路由对可变方法不开放，属已知机制）；claim_timeout 的 send 路由则给出空 revert 而非 FuncNotFound——两者不同
- 疑点：revert data 为空与错误桥（bridge_core_err 全变体生成消息）矛盾 → ① wasm panic（unreachable → 空 revert）或 ② 宿主对 LyquidError 的转换不携带消息（所有守卫错误都显示为空——无法用 data 区分是哪种失败）
- 待查：a) `lyquor_api::chain_pos()` 在 tx 执行上下文中的真实返回（若 Err→unwrap_or(0)→now=0→DeadlineNotReached→revert，但应带消息）；b) 错误→revert data 的宿主转换路径；c) shaker console 的节点侧执行跟踪；d) 构建一个最小对照（如 export=eth 的 probe_claim 复刻 claim 逻辑逐步 println）定位 panic 点

## 影响
keeper.py 代码就绪且解析/幂等逻辑已修（ABI hex 解码 bug 已修），但真实 claim 被此 revert 阻塞。超时退款路径在 multi v0.8.1 上**未验证**——W1 期收官声明中如实降级此项。
