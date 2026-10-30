# R3 目标 A 证据：E2 四节点委员会（T1 平台探针梯子 + T3 演示实录）

> T1 实跑：2026-10-30T02:04–02:08Z（接力看护触发）。实验台 = R2 实例
> `Lyquid-tldda6zqdhab2kdysepcqxx73uvm3sxz7wbaa` @ `0xFD6F7A6a5c21A3f503EBaE7a473639974379c351`
> （probe 方法已在位，**零改码零部署**，plan §3.4）。T3 段落由后续触发回填。

## §T1 平台探针梯子结论表

**S2 遗留问题的答案（P6）：多签聚合可达，且四节点全签实证。**

| # | 探针 | 结果 | 证据 |
|---|---|---|---|
| 1 | GetNodeInfo×4 当轮实测 + 宿主 {10087,11087,12087,13087} 连通性 | 4/4 通；NodeID 与 S2 表一致（节点身份跨重启稳定，bytes32 换算可复用，仍按当轮重算） | `_r3-t1-nodeinfo-raw.txt` |
| 2 | TARGET 推导 `shaker to-hex` | `0x9aC6307B3019C01d2878911E285efFDD2ACdcAf9`（非零 ≠ 合约 0xFD6F…c351，断言通过） | `_r3-t1-target-raw.txt` |
| 3 | **th=2 双签聚合** | configure(status=1, block 319) → advance=true → dest 0→1（change_count=5=4×AddNode+SetThreshold(2)）→ finalize=true → run_round=true → **cert.signers RAW=[0,2] len=2 → node1+node3 两异节点** | `_r3-t1-th2-raw.txt` + `_r3-t1-th2-console.txt` |
| 4 | **th=4 四签聚合** | bump(status=1, block 323) → advance=true → dest→2（尾部 `04`=threshold 4）→ finalize=true → run_round=true → **cert.signers RAW=[0,1,2,3] len=4 → 四节点全签** | `_r3-t1-th4-raw.txt` + `_r3-t1-th4-console.txt` |
| 5 | 通道面：容器内跨节点读 | node2/node3/node4 容器 cast call dest_epoch_info 全通，与 node1 读数一致（epoch=2 同 config） | `_r3-t1-node234-channel-raw.txt` |
| 6 | 通道面：**宿主 eth_call 直连 node2–4**（S2 未证项，本轮新证） | 11087/12087/13087 三端口 eth_call 全部返回完整 ABI 编码且一致 → **§3.6-5 的 docker_exec_cast 降级无需触发，宿主可直连全部 4 节点** | 同上 |

### T1 对后续任务的指令性结论

1. **多签聚合可达**（th2/th4 双档实证）→ L0「平台硬限制」分支排除。
2. **signers=4 实证**（T1 口径：probe_run_round avg_num=1 单提案四签）→ **L1 已达标**；
   **L2 的剩余待证项只有 inputs=4**（多提案聚合，probe 硬编码 avg_num=1 观察不到，
   plan §3.4 边界）——由 T3 首跑 `flow_committee`（avg_num=4 + arm 一次 + node1 单次触发）
   的 console 聚合行判定。
3. **宿主直连四端口可用** → T3 编排可直接用 NodeClient×4/宿主 curl，无需 docker_exec_cast。
4. fallback 预期：若 T3 首跑 inputs<4 → 按 plan §3.4 预登记降级 L1（avg_num=1 + 重新
   cp/deploy + 显式登记），不再经过 L0 三段式。

### 原始日志（7 件）

`_r3-t1-nodeinfo-raw.txt`、`_r3-t1-target-raw.txt`、`_r3-t1-th2-raw.txt`、
`_r3-t1-th2-console.txt`、`_r3-t1-th4-raw.txt`、`_r3-t1-th4-console.txt`、
`_r3-t1-node234-channel-raw.txt`

---

## §T3 E2 四节点委员会演示实录

> 实跑：2026-10-30T02:49–02:55Z。**新实例**（T3.1 `shaker deploy`，非 R2 实例）=
> `Lyquid-ybidj3krshf4gqcjk3m3px6mooi6tg74twwaa` @ `0x87006e75a5B6bE9D1bbF61AC8Cd84f05D9140589`
> （image `sha256:ccf7498b21638dff3a2d01b054c64d7dbb2c36922fa5072520590d2795974603`，LDK 0.8.1）。
> 部署前 md5 勾稽 9/9 MATCH（含首次上容器的 `committee_certified.rs` `83e358ee…`）、
> cargo check `Finished`、TARGET 断言通过。

### T3 结论

**判级 = L2（目标级达成）**：console 原文同时满足 `inputs=4` 与 `signers=4`，且四条
signer→Node 映射全部落在 e2_configure 配置的四个 NodeID 上。

| 项 | 值 |
|---|---|
| 判级 | **L2** — `e2_aggregate: agreed … from 4 input(s) (avg_num=4)` + `cert.signers RAW = [0, 1, 2, 3] (len=4)` + 四条 `signer N -> Node-…` |
| 实例 | `Lyquid-ybidj3krshf4gqcjk3m3px6mooi6tg74twwaa` |
| 合约 | `0x87006e75a5B6bE9D1bbF61AC8Cd84f05D9140589` |
| TARGET | `0xc05034ED5191cbc3404956D9b7dFcC7391e99bfc`（`shaker to-hex`；非零且 ≠ 合约） |
| deal | `deal-1`：Disputed → **Refunded**（NotFulfilled=1，全额退款 1000） |
| 降级 | **无 L1 fallback / 无 L0**：`E2_AVG_NUM` 保持 4，未改 lyquid 码、未重部署、未重触发 run_round |

### console 判级摘录（取证源 node1，原文；`_r3-t3-console-raw.txt`）

```
:5   e2_configure: staged committee of 4 nodes threshold=4 (dest epoch advance/finalize required to activate)
:15  e2_arm: armed_deal=deal-1 (network domain; single send visible to all nodes)
:19  e2_propose: node=Node-ve3tav5jw5ico7or34gcb6ni7rtmd35uokriuijygabd3tsltd7fj6ia deal=deal-1 verdict=1 (shape_ok=false, entries=3, avg_num=4, target.seq_id=…)
:20  e2_aggregate: input from Node-ve3tav5jw5ico7or34gcb6ni7rtmd35uokriuijygabd3tsltd7fj6ia -> deal=deal-1 verdict=1 (ts_ms=1793328719418)
:21  e2_aggregate: input from Node-j3fcdy5twah7csa6pr4jhgxcvszycxdms2hsen5m7lrvtezqlv52cqaa -> deal=deal-1 verdict=1 (ts_ms=1793328719458)
:22  e2_aggregate: input from Node-2folhfgf4kuyfdenaq3l4dnamv7yxrnqq3zbp64thfa5esqgxhv6wzqa -> deal=deal-1 verdict=1 (ts_ms=1793328719460)
:23  e2_aggregate: input from Node-oq2lcra5u4ksufzsv2ciqbl56dkp5c653ikzkx3lh62tai566d7dseia -> deal=deal-1 verdict=1 (ts_ms=1793328719460)
:24  e2_aggregate: agreed deal=deal-1 verdict=1 from 4 input(s) (avg_num=4)
:30  e2_run_verdict_round: certified call submitted to the sequencing backend
:31  committee_verdict_certified: cert.signers RAW = [0, 1, 2, 3] (Vec<SignerID>=Vec<u32>, len=4) deal=deal-1 verdict=1
:32  committee_verdict_certified: signer 0 -> Node-ve3tav5jw5ico7or34gcb6ni7rtmd35uokriuijygabd3tsltd7fj6ia
:33  committee_verdict_certified: signer 1 -> Node-j3fcdy5twah7csa6pr4jhgxcvszycxdms2hsen5m7lrvtezqlv52cqaa
:34  committee_verdict_certified: signer 2 -> Node-2folhfgf4kuyfdenaq3l4dnamv7yxrnqq3zbp64thfa5esqgxhv6wzqa
:35  committee_verdict_certified: signer 3 -> Node-oq2lcra5u4ksufzsv2ciqbl56dkp5c653ikzkx3lh62tai566d7dseia
:36  apply_verdict: deal=deal-1 verdict=1 misconduct=[]
:38  deal_info: {"id":"deal-1",…,"state":"Refunded","timeout_slots":300,"deadline_slot":637}
```

判级口径逐条对齐（plan §2）：`inputs=4`（:24，四个不同 `Node-…` 输入行 :20–:23 佐证）；
`signers=4`（:31）；四条映射行（:32–:35）映射出四个**互不相同**的 NodeID，且与 demo transcript
`[committee] nodeN port=… node_id=…` 四行（= T3.3 当轮 GetNodeInfo 重取、喂给 `e2_configure`
的成员集）逐个逐字一致 → signer 身份闭环。

**如实注记**：aggregate 在 console 中出现两次 `agreed`（:24 与 :29，同一 4 输入集的重复
回放），但 `certified call submitted` 仅一次（:30）、`committee_verdict_certified`
仅一次（:31）、`apply_verdict` 仅一次（:36）→ 无重复结算。

### 读回勾稽（P2：status≠effect，一切以读回为准）

| # | 勾稽项 | 证据 |
|---|---|---|
| 1 | arm **单次** + 读回断言 | `_r3-t3-committee-raw.txt:27` `arm read-back OK: armed_deal == deal-1 (pre-arm='')`；console :15–:17（`e2_arm` 一次，`armed_deal` 空 → `deal-1`）；未重 arm |
| 2 | run_round **单次**、cast call | transcript :28 `e2_run_verdict_round() -> True`；console :18 仅一次 `starting propose_and_certify`；未重触发 |
| 3 | 终态 Refunded | transcript :29 `final state=Refunded`；T3.5 独立读回 `deal_info(deal-1).state=Refunded`（block 341） |
| 4 | 余额勾稽（全额退款） | alice：faucet +10000 → fund −1000 = **9000**（transcript `after_fund`）→ 退款 +1000 = **10000**；bob/broker 恒 0（新实例起始 0）。**链上 faucet 单次实证**：blocks 0–341 全量扫描仅 1 笔 `faucet(string,uint128)`（block 333，from broker，agent=alice，amount=10000）→ alice 的 10000 基线唯一、无双重 faucet |
| 5 | misconduct 不增 | console :36 `apply_verdict: deal=deal-1 verdict=1 misconduct=[]`（新实例首个裁决；NotFulfilled 不 +1，Malicious 才 +1） |

> ⚠️ 第 4 项在 **demo transcript 内建断言处**以 RuntimeError 收尾（见 D-T3-1），其实质由 T3.5
> 独立读回 + 链上扫描证明，**不是**链上资金失配。

### 偏离登记（2 项；均为取证/脚本面，链上语义无偏离）

**D-T3-1（demo 内建余额断言 stale baseline，代码缺陷，本阶段不修）**

- 现象：主跑在 demo.py:694 以
  `RuntimeError: refund accounting mismatch: before={'alice': 0, …} after_fund={'alice': 9000, …} after={'alice': 10000, …}` 退出（transcript :41）。
- 根因：`demo.py:622` `node.faucet(alice, 10_000)` 后**立即** `before = snapshot()`（:623），
  读路径滞后一块 → `before` 读到 faucet 落账前的 `0`；而 `after_fund=9000`（10000−1000）
  与 `after=10000`（+1000 退款）证明 faucet 已恰好落账一次、退款足额。断言
  `after[alice] == before[alice]`（:692）在 faucet 读回滞后时必然误报。
- 判定：**链上资金语义正确**（全额退款、bob/broker 不变），非链上失配；demo 自检按
  plan §5-RT8「异常即 abort 不绕过」正确中止。
- 本阶段处置：**不修码**（本阶段代码面授权仅 demo.py:87 一行，#3）、**不重跑**
  （plan §T3.3 执行纪律）。故 transcript 缺 `refund check OK` 行、内建 console 取证段
  （:700-713）未执行——这正是 T3.4 手工全量 console 成为唯一判级依据的原因。
- 遗留建议（下一阶段）：把 `before` 基线改为 faucet **落账后**读回（`read_back`/`wait_state`
  口径），或将断言改为 `after[alice] == after_fund[alice] + 1000`（`after_fund` 已在
  `wait_state(Funded)` 之后读，不受该竞态影响）。位置：demo.py:622-623 / 692-696。

**D-T3-2（deploy transcript 首写被截断，已重建；根因已复现）**

- 现象：`_r3-t3-deploy-raw.txt` 首写后只剩 TARGET 段起的 14 行（967 B）。
- 根因（自身命令模式，已在 /tmp 最小复现）：在 `{ … } >> $LOG 2>&1` 块内用
  `tee /dev/stderr` 取 TARGET；Git Bash/MSYS 下 `tee` 按**路径**打开 `/dev/stderr` 会截断
  重定向目标。复现：`{ printf a; x=$(echo hi | tee /dev/stderr); printf b; } >> t1.txt 2>&1`
  → t1.txt 只剩 `hi`/`b`。
- 处置：重建该日志（629 行：T3.0 预检 + md5/cargo check + deploy 段 + TARGET + T3.2 声明 + T3.6 收尾自检，头部注明规则）——T3.0/md5/cargo check 为 `[RE-RUN]`（只读；
  针对**同一容器副本** `/tmp/tb-lyquid`，md5 仍 9/9 MATCH）；deploy 段为 `[QUOTED]`
  （本次会话原始输出逐字引述，**刻意不重跑 deploy**：第二次部署会产生第二个实例、污染证据链）；
  丢失的约 460 行编译 warning 无决策内容，已在文件尾部「TRANSCRIPT SCOPE NOTE」如实声明。
- 影响：GT3-a 的 deploy 证据为**重建件**（关键行齐全：命令、image hash、实例名、地址、
  `created Lyquid-… => 0x…`、`[deploy exit=0]`）。

### 原始日志清单（4 件，全部在 workflow-out）

`_r3-t3-deploy-raw.txt`（T3.0 预检 + T3.1 部署 + TARGET + T3.2 回填声明）、
`_r3-t3-committee-raw.txt`（主跑全 transcript，单次运行，exit=1 由 D-T3-1 断言导致）、
`_r3-t3-console-raw.txt`（console 全量原始输出，判级唯一依据，rc=124 正常收尾）、
`_r3-t3-final-state-raw.txt`（终态读回 + faucet 单次链上扫描）。

### 收尾自检（GT3 a–f）

| 门 | 判据 | 状态 |
|---|---|---|
| GT3-a | deploy 日志：冻结面自证 + md5 9/9（含 committee_certified.rs）+ cargo check Finished + `created Lyquid-… => 0x…` + TARGET 断言 | ✅ 满足（deploy 段为重建件，见 D-T3-2） |
| GT3-b | transcript：arm 读回 OK + run_round 单次 + Refunded + 余额勾稽 OK | ⚠️ **部分满足**：前三项 ✅；「余额勾稽 OK」行缺失（D-T3-1 断言打断），实质由 T3.5 独立证明 |
| GT3-c | console 含判级行（signers RAW / aggregate inputs），判级可从原文直接读出 | ✅ 满足（L2） |
| GT3-d | §T3 回填（结论/摘录/勾稽/日志清单）；fallback 或 L0 时降级登记段 | ✅ 满足（无 fallback；偏离登记 D-T3-1/D-T3-2 在档） |
| GT3-e | 冻结面收尾复验同 T3.0；fallback 时另加 40/40 | ✅ 满足（`md5sum -c` 四 OK；无 fallback，40/40 不触发） |
| GT3-f | 未执行 git commit/add/push；主路径 lyquid 源零改动 | ✅ 满足（`git status --short lyquid/` = 与 T2 交付态逐字相同；`committee_certified.rs` md5 仍 `83e358ee…`，E2_AVG_NUM 未改） |

**未执行**：任何 `git commit` / `git add` / `git push`；任何 lyquid 源码改动；任何重跑/重部署/重触发 run_round。

---

## §T7 补记：D-T3-1 修复端到端重验（2026-10-30，主控直做，用户授权「继续 R3」）

> 上述 §T3/收尾自检均为 R3-T5+T6 轮时点记录，原文保留。本节为同日后续：T6.1 修复
> （`d1e6f5f`）当时因「无实跑部署/链写授权」未做端到端重验，本次在新实例上补齐。

- **部署**：新实例 `Lyquid-dpp6ird6knahaun6dokpi6ki2pdnbjxdfunqa` @
  `0x942ED2fa862887Dc698682cc6a86355324F0f01e`（容器源与提交后 `lyquid/` md5 9/9 一致，
  同 image `sha256:ccf7498b…4603`）；TARGET `0x1BDFe4447e53407051Be1B94F47948d3C6d0a6e3` ≠ 合约。
- **主跑**：`python scripts/demo.py --node http://127.0.0.1:10087 --contract 0x942E…f01e
  --instance Lyquid-dpp6…unqa --flow committee` → **`exit 0`，`DEMO COMPLETE`**
  （`_r3-t7-dt31-verify-raw.txt:69/:72`）。T3 时因 D-T3-1 中断的三段全部实际执行：
  `faucet read-back OK: alice 0 -> 10000 (+10000)`（:22）、
  `refund check OK: alice 10000 -> 9000 (after fund) -> 10000 (after verdict); bob/broker
  unchanged`（:31）、console 取证段 25 行完整回放（:32-:59）。
- **L2 判级复现**：`e2_aggregate: agreed deal=deal-1 verdict=1 from 4 input(s) (avg_num=4)`
  （:44）；`cert.signers RAW = [0, 1, 2, 3] (len=4)`（:51）+ 四条互异 signer→NodeID 映射
  （:52-:55），与当轮 GetNodeInfo 喂给 `e2_configure` 的四个 NodeID 逐字一致；
  `certified call submitted` 仅一次（:50）、`apply_verdict` 仅一次（:56）、终态
  `Refunded`（:30）。agreed 行重复回放两次（:44/:49）与 T3 同形态（§T3 如实注记），无重复结算。
- **资金勾稽**：alice 0 → faucet +10000 → fund −1000 = 9000 → 退款 +1000 = 10000；
  bob/broker 恒 0——与 T3.5 独立读回结论一致，且这次由 demo 内建断言自身证明（无 RuntimeError）。
- **联动更新**：`docs/b3-user-test/操作手册.md` §0-2/§3.2/§3.3 与 `通过判据.md` 附录中的
  「无已档实录」标注已改引本实录；T3 实录保留为修复前对照。
