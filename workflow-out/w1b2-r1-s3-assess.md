# W1-B2 R1 · S3 证据：`assess_brief` 4×string 导出恢复 + 链上取证

执行日期：2026-10-29（R1 窗口）。执行基线：trustbridge 工作树（W1-B2 已提交 `dc78d2f`）。
本文件是本轮 S3 的唯一证据面；命令与输出的原文摘录如下（原始日志：`_r1-g2-raw.txt`、
`_r1-console-raw.txt`、`_r1-deploy-final-raw.txt`、`_r1-rpc-smoke-raw.txt`）。

**结论速览**

| 面 | 结果 |
|---|---|
| 部署（4×string 签名 + `export = eth`） | ✅ 通过（无 Stack too deep；Route A 成立，Route B 未触发） |
| 回放通道（eth_call，空 base_url/api_key/model → HeuristicModel） | ✅ 双通道取证（cast call 返回 + `shaker console` 回放） |
| 真实 LLM 通道（本地 mock base_url 探 egress） | ❌ 被平台 egress 策略拦截（私网地址），NodeError 原文入档（§3） |
| 真实凭据复跑 | 未执行（宿主无 `TB_LLM_*`，G-init ④ 缺口，合法路径） |

---

## §1 部署记录（G2 门）

### 1.1 源码同步与三方勾稽

```
$ md5sum lyquid/src/lib.rs lyquid/src/assessor.rs            # 宿主
70182fa9082a49fd4cd4ce8d24a46a6f *lyquid/src/lib.rs
4df7cda64e7e9eb4483c0b8be64068aa *lyquid/src/assessor.rs

$ docker exec multi-tools md5sum /tmp/tb-lyquid/src/lib.rs /tmp/tb-lyquid/src/assessor.rs   # 容器
70182fa9082a49fd4cd4ce8d24a46a6f  /tmp/tb-lyquid/src/lib.rs
4df7cda64e7e9eb4483c0b8be64068aa  /tmp/tb-lyquid/src/assessor.rs
```

容器内编译预检（T1 门）：`docker exec -w /tmp/tb-lyquid multi-tools cargo check
--target wasm32-unknown-unknown` → `Finished dev profile … in 26.79s`，**零 error**（仅
既有 warning）。

> D1 型旧镜像风险实测复现一次并已处置：首轮 `docker cp` 在 Git Bash 的 MSYS 路径转换下
> 目标路径被改写，容器内仍是旧源码（md5 不符），而随后的 `cargo check` 复用了旧 target
> 目录 0.67s 即"通过"。改为 `MSYS_NO_PATHCONV=1` 重做 `rm -rf` + `docker cp` + 删 `target`
> 后 md5 与宿主一致、check 实耗 26.79s。**教训：每次 cp 后必须 md5 勾稽再采信编译结果。**

### 1.2 部署

```
$ docker exec -w /tmp/tb-lyquid multi-tools shaker deploy \
    -r http://registry:8000/lyquids \
    --endpoint ws://node1:10087/ws \
    --private-key 0xac0974…ff80 Cargo.toml
…
INFO shaker::build: Built trustbridge with LDK 0.8.1
INFO shaker: Pushed image hash sha256:e352451bf69598d88d3d52a89eb87b2a87f7308850f6f911f2cb38358c721f39 to http://registry:8000/lyquids:latest
INFO shaker::deploy: trustbridge.address = 0x40918Ba7f132E0aCba2CE4de4c4baF9BD2D7D849
INFO shaker::deploy: trustbridge.lyquid_id = Lyquid-5h2kjsj3cbx2haipw6dzpd7cbe52z3seyfkaa
Status: created
Contract: 0x40918Ba7f132E0aCba2CE4de4c4baF9BD2D7D849
Platform Version: 0.8
```

- **实例**：`Lyquid-5h2kjsj3cbx2haipw6dzpd7cbe52z3seyfkaa`
- **地址**：`0x40918Ba7f132E0aCba2CE4de4c4baF9BD2D7D849`
- **镜像**：`sha256:e352451b…58c721f39`
- 本轮共 deploy 三次（13:54 / 13:57 / 13:58）：前两次镜像 `sha256:fb1930f6…`，第三次
  `sha256:e352451b…`；三次的源码 md5 完全一致（见 1.1 与 13:57 复测）。⇒ **平台镜像
  digest 至少包含非源码输入**（构建环境/时间类），不能作为"源码同一"的判据；判据以
  md5（源码）+ G2 行为自证（部署产物）为准。三实例的 G2 探针返回完全一致。

### 1.3 G2(a) 读面可路由

```
$ docker exec multi-tools cast call --rpc-url http://node1:10087/api 0x40918Ba7f132E0aCba2CE4de4c4baF9BD2D7D849 \
    "balance_of(string) returns (uint128)" 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
0
```

### 1.4 G2(b) `assess_brief` 回放（P1 探针，一次通过）

```
$ cast sig "assess_brief(string,string,string,string)"
0x3297eeb6

$ docker exec multi-tools cast call --rpc-url http://node1:10087/api 0x40918Ba7…D7D849 \
    "assess_brief(string,string,string,string) returns (string)" \
    '{"buyer_profile_digest":"b","seller_profile_digest":"s","terms_digest":"t","license_scope":"online-video,12mo,EU"}' '' '' ''
"{\"qualification_score\":75,\"risks\":[\"heuristic-mode\"],\"est_duration_ms\":60000,\"est_confidence\":40}"
```

- 返回与 `assessor.rs:89` HeuristicModel 定值逐字一致（`75 / ["heuristic-mode"] / 60000 / 40`）。
- selector `0x3297eeb6` 已冻结进 `agents/common/rpc.py` 的 `_ABI` 表。
- Python 封装同面复验（`_r1-rpc-smoke-raw.txt`）：
  `NodeClient.assess_brief(...)` → `{'qualification_score': 75, 'risks': ['heuristic-mode'],
  'est_duration_ms': 60000, 'est_confidence': 40}`。

**⇒ Route A 成立：4×string 的 instance 桩在 SequenceBackend.sol 中编译通过、可部署、
eth_call 可路由并返回报告 JSON。Route B 未触发。**

---

## §2 回放通道双证（G3 门之一）

通道 A —— cast call 原始返回：见 1.4。

通道 B —— `shaker console` 缓冲回放（D4 通道，`lyquid::println!`）：

```
$ timeout 20 docker exec multi-tools shaker console Lyquid-5h2kjsj3cbx2haipw6dzpd7cbe52z3seyfkaa
assess_brief: mode=heuristic report={"qualification_score":75,"risks":["heuristic-mode"],"est_duration_ms":60000,"est_confidence":40}
```

（`timeout` 退出码 124 是本地截断流量所致，行内容已完整取得。）

两通道同源互证：cast call 的返回面与节点本地 println 行给出同一 mode=heuristic + 同一报告
JSON。**G3 门（回放证据双通道在档）满足。**

---

## §3 真实 LLM 通道（cast call 探 egress；不可达，如实登记）

### 3.1 探针布置

- mock 服务：`multi-tools` 容器内 `python3 /tmp/r1_mock_llm.py`（0.0.0.0:9111，POST
  任意路径均返回合法 chat_completions 形状：`choices[0].message.content` = 报告 JSON
  `{"qualification_score":88,"risks":["mock-egress-mode"],"est_duration_ms":1234,"est_confidence":55}`；
  请求（路径 + authorization + body）落 `/tmp/mock_llm_requests.log`）。自测与请求日志见
  `_r1-mock-selftest-raw.txt`：自测（`Bearer probe`）返回上述 mock 报告；**日志中仅有
  自测条目——两次节点探针均未到达 mock**。
- 通道：**cast call**（eth_call，节点本地执行），`base_url` 指向 mock，`api_key` 为明显
  假值（**不是真实凭据**），`model=mock-model`。**未使用 cast send**（SPIKE-1 已证 send
  通道 console 静默、Err 被平台吞掉、status 恒 0x1，原始错误不可得）。

### 3.2 探针 1：主机名形式

```
$ docker exec multi-tools cast call --rpc-url http://node1:10087/api 0x40918Ba7…D7D849 \
    "assess_brief(string,string,string,string) returns (string)" '<brief_json>' \
    'http://multi-tools:9111/v1/chat/completions' '<redacted>' 'mock-model'
Error: server returned an error response: error code -1: Execution error:
Barrel(Lyquid(LyquidRuntime("assess(llm): llm call: openai-compat: HTTP transport error:
Host runtime: http request failed: error sending request for url
(http://multi-tools:9111/v1/chat/completions)"))).
```

mock 日志在该次探针后**无新增请求**（日志中仅自测那一行）。

### 3.3 探针 2：容器 IP 形式（策略原文浮出）

```
$ docker exec multi-tools cast call --rpc-url http://node1:10087/api 0x40918Ba7…D7D849 \
    "assess_brief(string,string,string,string) returns (string)" '<brief_json>' \
    'http://172.18.0.2:9111/v1/chat/completions' '<redacted>' 'mock-model'
Error: server returned an error response: error code -1: Execution error:
Barrel(Lyquid(LyquidRuntime("assess(llm): llm call: openai-compat: HTTP transport error:
Host runtime: http_request rejected by egress policy: blocked private/internal address `172.18.0.2`"))).
```

### 3.4 结论（如实登记）

1. **R1 平台的 eth_call 上下文确实发起 http egress**（错误来自 Host runtime 的
   `http_request`，而非"instance 方法不可调用"）；失败原因是**节点 egress 策略拒绝私网/
   内部地址**（SSRF 防护），主机名形式在策略/解析层就失败、IP 形式给出显式拒绝文案。
2. 因此**"本地 mock base_url"这一取证路线在本 devnet 上不可用**；真实 LLM 通道需要
   **公网可达的 HTTPS 端点 + 真实凭据**。
3. G-init ④ 复核：宿主 `env | grep -i "TB_\|LLM"` 为空（执行时），**不存在真实凭据**，
   故按方案"任一缺失 → 不复跑 + 如实登记缺项"处理，**未做真实凭据复跑**。
4. 影响面：**回放通道证据独立成立**（§2），S3 交付面 = 回放模式链上驱动 + 真实通道
   阻塞原因登记；这是任务明示的合法路径（"或回放兜底+如实记录"）。

### 3.5 api_key 脱敏

探针 `api_key` 为假值，按纪律仍脱敏登记：

```
sha256(api_key)[:8] = 57b9ec47
api_key 末 4 位      = 7f3a
api_key 长度         = 34
```

（值本身不是任何真实服务凭据；mock 日志中的 authorization 头亦仅此假值。）

---

## §4 偏离登记

| # | 项 | 处置 | 状态 |
|---|---|---|---|
| S3-1 | `assess_brief` 签名 7×string → 4×string（`brief_json` + `base_url`/`api_key`/`model`） | 依 D3：7×string instance 桩触发 solc Stack too deep，6×string 通过；4 参留余量 | **持久**（wire 形态变更登记） |
| S3-2 | 7×string 签名 | 不恢复；Stack too deep 记录保留为平台限制存档（`w1b2-claim-probe-evidence.txt §2`） | 存档 |
| S3-3 | `assessment_cache` 写在 eth_call 下 | 节点本地临时态，**不落链**；本轮无消费方，不构成缺口 | 登记 |
| S3-4 | 真实 LLM 通道 | 未取证：egress 策略拒私网 + 无凭据（§3） | 登记（非失败） |
| S3-5 | Route B | 未触发（G2 一次通过） | 不适用 |
