# W1 Spike 执行计划（2026-10-19 制定）

> 前置文档：[计划书](FinalProject_计划书_TrustBridge_2026-10-12.md)（§6 里程碑/§8 风险册）、[可行性调研](FinalProject_可行性调研_现有方法_2026-10-11.md)（§4 平台验证）、仓库 README（W1 spike 清单）
> 代码基线：`a8ca9fb`（四阶段加固完成，壳 39/39，lib.rs 对真实 ldk 尚有 73 个编译错——这正是本计划要消除的）

---

## 0. 今日硬节点与日程重压缩

- **Canvas 分组注册截止 = 今天（10/19）**。无论本计划其余部分如何安排，先确认注册已完成；未完成则立即办理。
- 计划书原排期 W1 止于 10/19；这一周实际投入了四阶段代码加固（值得：避免了带缺陷上 devnet）。剩余 31 天，日程压缩如下（吸收掉原 W5 报告周的冗余）：

| 窗口 | 内容 | 对应原计划 |
|---|---|---|
| **10/20–10/23（W1'）** | 五项 spike + lib.rs 编译清零 | 原 W1 后移 |
| 10/24–10/30（W2'） | 正常流上 devnet（报价→评估→托管→存证→交付→结算） | 原 W2+W3 前半 |
| 10/31–11/6（W3'） | 对抗流（超时退款、伪造→委员会裁决）+ LLM 真实接线 | 原 W3 后半+W4 |
| 11/7–11/13（W4'） | 4 节点委员会演示（E2）、对照实验、组外用户测试（B3） | 原 W5 |
| 11/14–11/18（W5'） | 报告 PDF、幻灯片、预录 demo、AI 使用声明 | 原 W6 |
| **11/19 12:00** | 提交；当天 8 分钟展示 + 2 分钟问答 | 不变 |

---

## 1. 五项 Spike（按执行顺序；每项含通过判据与止损）

### S0 环境预检（10/20 上午，半小时）

Docker Desktop 运行、`gh auth status` 通过（拉 GitHub Packages 需要）、磁盘 ≥10GB。
**通过**：`docker compose up -d` 起 4 节点 devnet，`curl 127.0.0.1:10087/lyquor/api` 有响应。
**止损**：devnet 起不来 = 全计划阻塞，当天必须解决（读 docs.lyquor.dev 的 Prerequisites 逐项核对版本）。

### S5 宏漂移审计（10/20，与 S0 并行启动）——一切的前提

把 `lyquid/src/` 里全部 `SPIKE(W1)` 标记逐个落地：`state!` 字段语法、`#[method::network/instance]` 属性真实形态、caller 身份访问器、slot 时钟访问器、`LyquidError` 构造、`call!`/`trigger!` 签名。
**通过**：`cargo check` 错误数 73 → **0**（或 ≤5 且逐条注明属上游模板必需项）；`cargo test`（主 crate）全绿。
**止损**：若某宏形态与假设差异过大（如 caller 身份模型完全不同），记录实际形态并重写对应封装层——壳测试保护核心语义不变。

### S1 Timer 语义（10/21，风险 R1，双人协作）

4 节点 devnet 部署最小 escrow Lyquid；造一笔过期的 Funded 交易；注册 `TriggerMode::Once` watcher 提交 `claim_timeout`；**kill/重启全部节点**重复观察。
**通过**：a) 恰好一次退款（守卫去重）；b) 重启后无重复触发；c) 触发延迟 < 2× 周期。
**止损**：任一不满足 → 放弃 native trigger，转 keeper 模式（`scripts/keeper.py` 轮询 `due_deals`→提交退款），主方案本就不依赖 trigger 正确性——半天内完成转换并记录到 spike 报告。

### S2 委员会回合（10/22 上午）

移植 `price-feed` oracle 骨架：`propose_and_certify` / `set_threshold` 跑通一次认证调用；读取 `ctx.cert.signers` 真实形态。
**通过**：4 节点 localnet 上拿到 ≥阈值签名者的认证结果并能在 network 函数中读取。
**止损**：oracle 流过于复杂 → demo 路径维持现有"成员集+阈值+签名者集合校验"（已实现），oracle 留 W4 演示加分项，报告中如实说明信任模型差异。

### S3 lyquid-llm 两步提交（10/22 下午）

instance 函数内 `call_model`（JsonSchema 输出）→ 结果经网络调用提交；确认 `http_request` 出口限制与超时行为。
**通过**：broker 流程在 devnet 上完成一次真实 LLM 资格评估+估时并入库（`assessment_cache`→`create_deal`）。
**止损**：API key/网络受限 → MockLLM 回放模式（已实现）撑起 W2 开发，真实调用仅用于最终 demo 录制。

### S4 RPC 包格式（10/23）

抓包/读源码确定 `/lyquor/api` 的确切 JSON 形状（方法名 mangling、Vec/struct 参数编码、错误形状）。
**通过**：`python scripts/demo.py --node http://127.0.0.1:10087` 三流程在真实 devnet 上全绿。
**止损**：直接 RPC 形状过于怪异 → 用 `shaker console`/SDK 脚本桥接一层，保持 `NodeClient` 接口不变。

### W1' 收尾（10/23 晚）

spike 报告五节（每节：结论/证据/决策/对 README 的更新）；**更新 README 的 Verified-API 状态表**；git tag `w1-spikes-done`。

---

## 2. 分工（3 人）

| 人 | 主责 |
|---|---|
| P1 | S5 宏审计 + lib.rs 编译清零 + 部署脚本（deploy.sh 校正） |
| P2 | S1 timer + S2 委员会（平台侧最险两项） |
| P3 | S4 RPC + keeper.py + demo.py 接 devnet + spike 报告汇总 |
| 共同 | S3 结对（LLM 接线涉密钥管理）；每日晚 10 分钟同步结论 |

---

## 3. W1' 完成定义（Definition of Done）

1. 五项 spike 各有报告节（结论/证据/决策），README API 状态表更新；
2. `cargo check` = 0 错（或 ≤5 项有逐条说明），壳 39/39 保持全绿；
3. `demo.py --node` 至少跑通流程 1（正常流）到 Settled；
4. Canvas 注册完成（今天就办）；
5. git tag `w1-spikes-done` 并推送。

W2' 起按压缩日程表执行；所有里程碑验收标准沿用计划书 §6 不变。
