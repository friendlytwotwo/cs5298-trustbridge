# 阶段重排计划（2026-10-27 制定）——取代 W1-B2 及原压缩日程后半段

> 背景：W1-B2 运行（dwfrun-9f1f20a9）经三轮方案审查（r1 REVISE→r2 APPROVE→冷读 REVISE）后被 GLM 周/月配额（code 1310）停止；重启过程遭遇编排会话不稳定。决定**整体作废该阶段运行**，按本计划重新安排。三轮审查的全部有价值发现已收入 §2 作为设计输入，不随运行作废而丢失。
> 代码基线：`ad8c850`（W1-A + W1-B1 + keeper.py 均已入库推送）。

---

## 1. 新阶段结构（10-28 → 11-19，23 天）

| 阶段 | 窗口 | 内容 | 执行方式 |
|---|---|---|---|
| **R0 devnet 实测** | 10-28 上午 | keeper 超时退款实测 + deal_info 字面补验 + 正常流手动跑通（全部组件已写好，纯执行） | 主控直做，不用工作流 |
| **R1 接线收尾** | 10-28 下午–10-29 | S3 LLM 真实接线（或回放兜底+如实记录）、S4 RPC 对齐进 NodeClient（移除 SPIKE W1-4）、`demo.py --node` 正常流到 Settled | 工作流（全角色 GLM-5.3-Flash） |
| **R2 对抗流+W2'** | 10-30–11/5 | 超时流（keeper 驱动）+ 伪造交付→委员会裁决在 devnet 跑通；W2' 正常流全 E2E 收尾 | 工作流 |
| **R3 演示与实验** | 11/6–11/12 | 4 节点委员会演示（E2）、纯 EVM 对照实验、组外用户测试（B3） | 工作流 + 人工 |
| **R4 报告冲刺** | 11/13–11/18 | 报告 PDF（≥6 页+AI 声明）、幻灯片、预录 demo | 主导写 |
| 提交 | **11/19 12:00** | 报告+demo ZIP；当天展示 | — |

## 2. W1-B2 三轮审查的已验证设计输入（R1 必须遵守）

1. **ABI 线型**：`u128`/`Vec<String>` 无 EthAbiType——`balance_of` 边界改 U128、`due_deals` 改 JSON 字符串 getter（keeper 相应适配，或 keeper 改为枚举 deal-N）；
2. **身份映射**：fund/submit_deliverable/complete/open_dispute 的发送方默认 anvil#0=BROKER，会被 Buyer/Seller 守卫拒绝——node 模式必须按角色用不同 anvil 私钥（`--from`）；
3. **assess_brief 返回类型**：`()` 不可读调——钉死为 `-> LyquidResult<String>` 返回报告 JSON（types.rs 冻结，用局部可序列化视图）；
4. **`--flow all` 门控**：node 模式下对抗流方法不在 eth 导出清单——node 模式过滤为 normal+timeout 并打出 "adversarial: sim-only" 横幅；
5. **keeper 产块助推**：timeout_slots=1 时 due_deals 在下一次产块前为空——demo/keeper 显式加 nudge 交易步骤；
6. **instance println 可见性**：仅 `cast call` 可见（cast send 静默）——S3 证据通道用 cast call。

## 3. 已作废与已保留

- 作废：dwfrun-9f1f20a9 运行及其 plan.md（未提交，随作废丢弃）；
- 保留：keeper.py（`ad8c850`）、W1-A/W1-B1 全部代码与证据、本文件 §2 设计输入；
- 环境：multi devnet 起法见 `workflow-out/w1b1-topology.md`；escrow 源码已 `docker cp` 至 multi-tools:/tmp/tb-lyquid（每次改码后需重新 cp）。

## 4. 启动规则

R0 由主控在下一次"继续"指令时直接执行；R1/R2/R3 各自由用户明确说"开始 R1/R2/R3"后以工作流启动（用户改版工作流，六角色 GLM-5.3-Flash）；任何阶段被配额中断即停，重置后从断点续跑。
