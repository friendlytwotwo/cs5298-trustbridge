# W1-B1 S1 timer 实验记录与结论（T3 交付）

> 本文全部命令与输出为 2026-10-24 实跑实录（会话内逐字转写；multi-tools 容器 /tmp 原始捕获文件已随容器删除，正文即存档）。实验实例：`Lyquid-zz2juejwa3xj5cx6jqespjhlzzr7bjchoi7aa` @ `0x9A676e781A523b5d0C0e43731313A708CB607508`（multi 4 节点 v0.8.1，T1 拓扑见 w1b1-topology.md）。

## 0. 通道先行证明（前置硬门，方案 §③-T3 第 0 步）

### 0.1 发现 A：console 可见性按执行通道区分（SPIKE-1，修订登记）

按方案先做"cast send probe_arm + console 取回 arm println"。实测序列：

```
# ① attach console 后 cast send probe_arm(5000)（node1 通道）
cast send 0x9A676e…7508 "probe_arm(uint64)" 5000 --private-key <anvil#0> --rpc-url http://node1:10087/api
→ blockNumber 17 / status 1 / tx 0xa53fccb008f3a196e8a08bd59d199e2adb1de123510f930ec8f88aab7df17671
# 26s 后 console /tmp/console-t0.log：仅 "received SIGTERM"，无任何 probe 行
```

对照定位（同一实例 #3 上）：

| 方法 | 类别 | 调用通道 | console |
|---|---|---|---|
| `probe_arm` (instance) | instance | cast send | **静默** |
| `probe_get_report` (instance) | instance | cast send | **静默** |
| `probe_reset_net` (network) | network | cast send | **可见**：`probe_reset_net: cleared (old net_fires=0)` |
| `probe_net_report` (network) | network | cast send | **可见**：`probe_net_report: {"probe_net_fires":0,"net_last_fire_ms":0}` |
| `probe_arm`/`probe_propose`/`probe_aggregate` (instance) | instance | **cast call** | **可见**（S2 阶段实录，见 w1b1-s2-oracle.md §4） |

**结论（SPIKE-1 登记，implementation.md 同步）**：node v0.8.1 的 console 转发区分**执行通道**而非方法类别——cast send（链序执行）仅 network 方法 println 可达 console；cast call（节点本地执行）则 instance/network 均可达。回执 LyteLog 仍可证 cast send 侧真实执行（如 `probe_net_config` 的 LyteLog 含方法名、status 0x1，但其 println 不可见，机制在节点侧、本窗口未深挖）。
**适配**：探针新增 network 域 `probe_net_report()`（S1 观测原语）与 S2 `probe_net_config`/`probe_bump_threshold`（network 化），arm 成功分母改用 cast send 回执 status=1（方案 R11"实测失败输出存档；必要时收敛签名形态"款）。

### 0.2 发现 B：cast call 在本环境可用（SPIKE-2，对方案前提的修正）

方案 §② 写"eth_call 已证不可用"（W1-A 单节点 0.8.2-dev 实测）。本环境（multi v0.8.1）实测 `cast call` 对探针合约**读与执行均可用**（S2 激活即靠它，见 w1b1-s2-oracle.md §3）：

```
cast call --rpc-url http://node1:10087/api <CTR> "__lyquor_oracle_dest_epoch_info(string,bool) returns (uint64,bytes32,uint32,bytes)" "cert_probe" false
→ 0 / 0x000…0 / 0 / 0x     （ws://node1:10087/ws 同样可用）
```

`()` 返回不可读调用与 W1-A 登记一致：`cast call "probe_net_config() returns (bool)"` → `Error: … FuncNotFound`（send 可达）。

## 1. 实验 a —— 触发次数（判定域 = 共识 network 计数 delta）

协议：reset→baseline→双节点 arm→轮询。全部命令容器内（multi-tools），node2 容器内端口 10087。

```
[a.1] cast send "probe_reset_net()"  --rpc-url http://node1:10087/api
      → status 1, tx 0xa680653eb0c40bee6edfeaf2aeaed794655d72b987dd77af6c57f01d5a7eed47
[a.2] baseline: cast send "probe_net_report()" ×2（node1 + node2 通道，均 status 1）
[a.3] arm: cast send "probe_arm(uint64)" 5000 ×2
      node1 → status 1, tx 0xdbd23c9fb9d229da75d28762728f536eb5be433d03a8281b935fda9f839362ae
      node2 → status 1, tx 0x4190aac5fc5d9fed9bc153abb2c5cce93fd450765fed01f04ba15a9686039e83
[a.4] poll ×4（间隔 8s，触发窗后 ≥3 周期）+ node2 终读：均 status 1
      console（node1 全程 attach）20 行 probe_net_report 全部为
      {"probe_net_fires":0,"net_last_fire_ms":0}
```

**判定：delta = (0 − 0) = 0 ≠ 成功 arm 数 2 → exactly-once 不满足（欠触发：0 次触发而非 1 次/节点）。** instance 域无对照数据（println 通道限制，见 §0.1；NET FIRE 即 instance timer 成功的唯一链上痕迹，为 0）。

## 2. 实验 b —— kill/重启节点服务（anvil/registry 保持运行）

```
[b.1] 前置读数: block-number=42; probe_net_report → status 1（console: net_fires=0）
[b.2] docker compose -f docker/multi/docker-compose.yaml kill node1 node2 node3 node4
      → 4 × "Killed"；up -d → 4 × Started + setup-devnet Started
[b.3] bootstrap 幂等重跑实录（setup-devnet 日志尾部）：
      Committee Size: 4 / Threshold: 1 / Admitted Images: 3 / Pending Deployments: 0
      （无重复部署、委员会不变）
[b.4] 链连续性: block-number 42 → 46（anvil 未重启、链前进未回退）；
      GetLyquidInfo 同一 bartender contract 0x9fE4…a6e0
[b.5] 重启后读数: node1+node2 通道 probe_net_report 均 status 1
      console: net_fires=0（与重启前逐项一致）
```

**判定（判定域 = network 计数）：重启前后 probe_net_fires 0→0，无重复触发（也不存在"重启重放"——实验 a 的 arm 在重启后仍未补发）。** instance 计数（probe_fires）是否复位：**不可观测**（console 通道限制，§0.1）——方案本将"节点数据卷持久"降级为待观测项，如实登记为该项未取得观测。节点卷（multi_node1-4-data）在 kill/up 间保留，up 后 lyquid 直接可调用（无重新部署）。

## 3. 实验 c —— 触发延迟与周期比

三组 delay ∈ {2000, 5000, 10000}，每组完整 reset→baseline→arm(node1)→poll（等待 = delay+10s）：

```
group 2000 : reset/tx + arm/tx 0x34156604acf48418e7f69c3a44df5b1bb4c5cb9236e8d474bcae74da43f551a2 → poll: net_fires=0
group 5000 : arm/tx 0x21de01dedf4835385b5736bebccf94333ee0a5c34e84e641b291f14f4770174f          → poll: net_fires=0
group 10000: arm/tx 0x26d661af9eeb65374428f29e92e519cdcc4b6c480c976b29e3beebecab1e55e9          → poll: net_fires=0
（三组 console 尾部实录：probe_reset_net: cleared ×3 + probe_net_report net_fires=0 全部轮询）
```

**延迟 = 从未触发（比值无定义）。** Recurrent 对照组：`probe_arm_recurrent(2000)`（tx 0x5d83918cc99577a245f2fdb144e8db6b480b6b9fe1a51a9398519dc438a096cd）后**主动产块** 12 个（block 0x15→0x20，排除"slot 边界才检查"假设）持续 60s+，console 13 行 probe_net_report 全为 0——Recurrent 同样不触发。

## 4. 结论表（判定域 = 共识 network 计数；对齐 timeout.rs:75-77 SPIKE_1 口径）

| 实验 | 观测 | 结论 | 对主方案影响 |
|---|---|---|---|
| (a) exactly-once | 双节点 arm（status 1×2）后 delta=0 | **不满足**（欠触发 0/2；非 double-fire 形态） | native trigger 不可依赖 |
| (b) kill/重启 | 节点服务重启（anvil 保持），network 计数 0→0，链连续 | 无重复触发——但前提（有触发）不成立，结论仅登记不背书 | keeper 模式下 claim_timeout 幂等守卫仍是去重权威（W1-A 已证） |
| (c) 延迟/周期 | 3 组 delay + Recurrent(2000) 产块 60s | **从未触发，延迟无定义**（验收 (c) latency < 2x period 无从满足） | 同上 |
| Recurrent 对照 | 主动产块 12 块/60s | 不触发 → 排除"slot 对齐"假设 | — |

**native trigger 判定（二选一）：不可用**（本 multi v0.8.1 devnet：`TriggerMode::Once` 与 `Recurrent` 的 instance trigger 注册成功（arm status 1、无节点侧报错）但调度器从未触发；四节点日志均无 trigger/fire 活动）。**主方案转 keeper 模式，不算失败**——"off-chain trigger; on-chain guard"的 on-chain 守卫（claim_timeout 幂等）W1-A 已实现并测试；watcher 落 keeper.py 轮询（W1-B2 范围）。

## 5. 未竟项与遗留（如实登记）

1. **单节点（0.8.2-dev）交叉验证未完成**：切栈后 shaker deploy 被 rust-std sysroot 下载阻断（`https://github.com/lyquor-labs/rust-toolchain/releases/...rust-std-1.99.0-wasm32-unknown-unknown.tar.xz`，容器 TLS 被掐/宿主直连亦不通；W1-A 曾登记同类瞬断后恢复）。故"trigger 不触发"结论的**版本维度未标定**（0.8.1 multi 环境实测不触发；0.8.2-dev 是否同病未知）。遗留至 W1-B2：网络可达时补部署复测。
2. instance 域计数重启前后对照：未取得（§2）。
3. cast-send 通道下 instance println 不可达 console 的节点侧机制：未深挖（LyteLog 证执行、无输出，SPIKE-1 登记）。

## 6. 人工复现命令清单（多节点，容器内 multi-tools；KEY/CTR/LY 见文首）

```bash
# 0) 通道
cast send $CTR "probe_reset_net()" --private-key $KEY --rpc-url http://node1:10087/api
cast send $CTR "probe_net_report()" --private-key $KEY --rpc-url http://node1:10087/api   # 观测原语
timeout 30 shaker console $LY --endpoint ws://node1:10087/ws                              # 观测面
# 1) 实验 a：reset → baseline(net_report ×2 通道) → arm(5000) ×node1+node2 → 轮询 net_report
# 2) 实验 b：docker compose kill node1..4 && up -d → 前后 block-number + net_report 比对
# 3) 实验 c：对 delay ∈ {2000,5000,10000} 重复 reset→baseline→arm→poll
#    对照：cast send "probe_arm_recurrent(uint64)" 2000 + 周期性产块（cast send 任意方法）
```
