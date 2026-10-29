# W1-B2 S4：RPC 信封探针 + deal_info 字面补验证据

> 全部输出为 2026-10-25 实跑存档。执行基线 HEAD = `1c0e45f`（W1-B1 完成态）。
> 环境：multi v0.8.1 四节点栈（拓扑 §2），宿主 Git Bash + multi-tools 容器（ghcr.io/lyquor-labs/lyquor-tools:v0.8.1，挂 ldk_cargo-cache 卷）。
> 基线实例：`Lyquid-rkkfz4d3…` @ `0xcbEAF3BDe82155F56486Fb5a1072cb8baAf547cc`（拓扑 §5b #4，与部署同源代码）。

## A. deal_info 字面补验（T1，零代码改动）

### A-0 账户实测（R1 口径：地址以 eth_accounts 实测为准）

```
$ curl -s -X POST -H 'content-type: application/json' \
    --data '{"jsonrpc":"2.0","id":1,"method":"eth_accounts","params":[]}' http://127.0.0.1:10087/api
{"jsonrpc":"2.0","id":1,"result":["0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266","0x70997970c51812dc3a010c7d01b50e0d17dc79c8","0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc", ...共 10 账户]}
$ curl -s --data '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}' http://127.0.0.1:10087/api
{"jsonrpc":"2.0","id":1,"result":"0x7a69"}
```

anvil 确定性 dev 账户 #0/#1/#2（EIP-55 串）：
- #0 `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266` = BROKER（lib.rs:155 一致）
- #1 `0x70997970C51812dc3A010C7d01b50e0d17dc79C8` = ALICE
- #2 `0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC` = BOB
- 私钥 ↔ 地址对应关系以 A-1/A-2 的 `from` 回执字段实证（#0 私钥发 tx → from=#0；#1 私钥发 tx → from=#1，见 B-①/②）。

### A-1 造状态（容器内 cast send，`--rpc-url http://node1:10087/api --private-key <anvil#0>`）

| 笔 | 命令（ABI 裸函数名） | 回执要点 |
|---|---|---|
| 1 | `cast send 0xcbEAF3… "faucet(string,uint128)" 0x70997970C51812dc3A010C7d01b50e0d17dc79C8 1000000000000000000` | status=1, block 80, tx `0x073e8f2f8f59d94f024fe26b0114965c033b60f9b84e6d473d7c55c1f37286b4`, from `0xf39F…92266` |
| 2 | `cast send 0xcbEAF3… "create_deal(string,string,uint128,uint16,string,string,uint64,uint8)" 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 agent-bob 1000000000000000000 200 terms-digest-w1b2-t1 accept-digest-w1b2-t1 60000 40` | status=1, block 81, tx `0xc0d2615be6bb6c36c0432fbc4d31f4d17b6b1c16db935a0dbb0b370f8b472640`（buyer=anvil#0 地址串，与 W1-A T5 同构，规避单密钥 Buyer 守卫） |
| 3 | `cast send 0xcbEAF3… "fund(string)" deal-1`（第一次，#0 余额为 0） | status=1, block 82, tx `0x571c33fa…`——**但 deal_info 仍读出 Qualified**：fund 内 `Err("insufficient balance")` 被平台吞掉、status 仍 1（lib.rs network Err 非回滚语义，implementation.md §③ 既登记）。教训登记：**eth 通道 status=1 ≠ 方法成功，读回执后须以 deal_info/balance_of 复核**（已写进 rpc.py `_send` 与 keeper 断言口径） |
| 4 | `cast send 0xcbEAF3… "faucet(string,uint128)" 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 1000000000000000000` | status=1, block 83, tx `0x2c49428533afe7774cdc34387342362b51cd22e7cfa70d9b526e7111014eee1e` |
| 5 | `cast send 0xcbEAF3… "fund(string)" deal-1`（重试） | status=1, block 84, tx `0x4bafe410ac060aa342aacf911e6eb9482e20045ba673b146d62710fe8f5de42c` |

### A-2 字面读（W1-A 豁免条件 (b) 遗留项补验——**通过**）

```
$ cast call --rpc-url http://node1:10087/api 0xcbEAF3BDe82155F56486Fb5a1072cb8baAf547cc \
    "deal_info(string) returns (string)" deal-1
"{\"id\":\"deal-1\",\"buyer\":\"0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266\",\"seller\":\"agent-bob\",\"amount\":1000000000000000000,\"state\":\"Funded\",\"timeout_slots\":300,\"deadline_slot\":384}"

$ cast call --rpc-url http://node3:10087/api … 同命令
"{\"id\":\"deal-1\",\"buyer\":\"0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266\",\"seller\":\"agent-bob\",\"amount\":1000000000000000000,\"state\":\"Funded\",\"timeout_slots\":300,\"deadline_slot\":384}"
```

- `state:"Funded"` 字面 + `deadline_slot=384 = funded_block 84 + timeout_slots 300` 勾稽一致（fund 在 block 84，lib.rs `funded_slot + timeout_slots`）。
- 首轮读（fund 实败期间）`state:"Qualified"`、`deadline_slot:null`——**读通道反映的是真实链上状态**，非缓存假象（node1/node3 两通道一致）。
- network 方法（`export = eth`）的 eth_call 读在 multi v0.8.1 **可用**——W1-A 单节点 0.8.2-dev 的 "Invalid contract address" 限制在 multi 不成立（与 w1b1-s2-oracle.md:40-42 结论同向，本轮在 escrow 主合约上坐实）。

### A-3 错误形状（逐字）

```
$ cast call --rpc-url http://node1:10087/api 0xcbEAF3… "deal_info(string) returns (string)" no-such-deal
Error: server returned an error response: error code -1: Execution error: Barrel(Lyquid(LyquidRuntime("no such deal"))).
```

### A-4 结论

任务 1 前半（deal_info 字面补验）**通过**：multi 链上 network+export=eth 方法的字面读通道开放，DealView JSON 与 fund 控制台输出同构（id/buyer/seller/amount/state/timeout_slots/deadline_slot 七字段逐一对应）。W1-A R3 豁免的遗留验证项就此销项。

## B. S4 信封探针矩阵（T2，宿主 curl → http://127.0.0.1:10087/api）

### B-⓪ selector 固化（容器内 `cast sig`，落 rpc.py 常量表；与 A-1 回执 log 内嵌 selector 交叉印证）

```
faucet(string,uint128)                                            => 0xb540def8   （A-1 log data 内同值）
create_deal(string,string,uint128,uint16,string,string,uint64,uint8) => 0xbd827024（A-1 log data 内同值）
fund(string)                                                      => 0x73451f65   （A-1 log data 内同值）
notarize(string,string,string,string)                             => 0xb1fecd5a
submit_deliverable(string,string)                                 => 0x7ecc9d46
complete(string)                                                  => 0xad932b5c
claim_timeout(string)                                             => 0x786cfc8f
cancel(string)                                                    => 0x0b4f3f3d
open_dispute(string,string)                                       => 0xa48ab911
committee_config(string[],uint32)                                 => 0x15df3c73
deal_info(string)                                                 => 0xec78f86e
evidence_entries_json(string)                                     => 0x16417010
balance_of(string)                                                => 0x3e6b4459
due_deals(uint64)                                                 => 0x4704839a
```

探针 calldata（`cast calldata` 生成）：faucet(#1,5) = `0xb540def8…79433800…00`；deal_info(deal-1) = `0xec78f86e…64653100…00`（全文见本节命令现场，宿主历史可复跑）。

### B-① 写通道决策门（R2#3 双 sender）：**通过 → eth_sendTransaction 为主通道**

```
=== ① eth_sendTransaction from=#0 ===
{"jsonrpc":"2.0","id":1,"result":"0xde2ddf9eff4df974915bddb92dc9f45fa2ee253de26e52f00596abc7a10a974e"}
=== ② eth_sendTransaction from=#1（非默认 sender）===
{"jsonrpc":"2.0","id":2,"result":"0xdb5f69626664c6ced6ef5eb4e6e08a3ec363a3fad5f920850e432df5411cb7e0"}
```

### B-② 回执轮询（anvil 兼容形状）

```
=== ③a eth_getTransactionReceipt（#1 tx，automine 下立即终态）===（节选，全文为 anvil 标准形状）
{"jsonrpc":"2.0","id":3,"result":{"type":"0x2","status":"0x1",…,"logs":[{…faucet LyteLog…}],
 "transactionHash":"0xdb5f6962…1cb7e0","blockNumber":"0x56","from":"0x70997970c51812dc3a010c7d01b50e0d17dc79c8",
 "to":"0xcbeaf3bde82155f56486fb5a1072cb8baaf547cc","contractAddress":null,…}}
=== ③b #0 tx ===
{"jsonrpc":"2.0","id":4,"result":{…,"status":"0x1","blockNumber":"0x55",
 "from":"0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266",…}}
```

- 回执字段：`status`(hex)/`blockNumber`/`transactionHash`/`logs[]`/`from`/`to`/`gasUsed`——`from` 字段实证 #0/#1 私钥↔地址对应（R1 退路密钥表地址实测核）。
- automine 下立即轮询即终态，无 pending 窗口观测（如实登记；客户端仍按「pending→null 重试」实现）。

### B-③ 读通道透传

```
=== ④a eth_getTransactionCount(#0,latest) ===
{"jsonrpc":"2.0","id":5,"result":"0x55"}
=== ④b eth_estimateGas（deal_info data）——不可用 ===
{"jsonrpc":"2.0","id":6,"error":{"code":-1,"message":"Call(ErrorObject { code: ServerError(3), message: \"execution reverted\", data: Some(RawValue(\"0x\")) })"}}
=== ④c eth_call（deal_info deal-1）===
{"jsonrpc":"2.0","id":7,"result":"0x…20|af|{\"id\":\"deal-1\",\"buyer\":\"0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266\",\"seller\":\"agent-bob\",\"amount\":1000000000000000000,\"state\":\"Funded\",\"timeout_slots\":300,\"deadline_slot\":384}|padding"}
=== ④d eth_blockNumber ===
{"jsonrpc":"2.0","id":8,"result":"0x56"}
```

- **eth_estimateGas 对 lyquid 合约调用不可用**（ServerError(3) execution reverted）——`eth_sendTransaction` 不带 gas 字段即可（①②实证自动注气），客户端不依赖 estimateGas。
- eth_call 返回 ABI 编码 string（offset/len/utf8/pad），解码即 DealView JSON。

### B-④ 错误形状（逐字）

```
=== ④e 未知 JSON-RPC 方法 ===
{"jsonrpc":"2.0","id":9,"error":{"code":-32601,"message":"Method not found"}}
=== ④f eth_call 方法级 Err（no such deal）===
{"jsonrpc":"2.0","id":10,"error":{"code":-1,"message":"Execution error: Barrel(Lyquid(LyquidRuntime(\"no such deal\")))."}}
=== ④g eth_sendTransaction 非账户 from ===
{"jsonrpc":"2.0","id":11,"error":{"code":-1,"message":"Call(ErrorObject { code: InvalidParams, message: \"No Signer available\", data: None })"}}
=== ④h 未导出方法（submit_deliverable @基线实例）===
{"jsonrpc":"2.0","id":12,"error":{"code":-1,"message":"Execution error: Barrel(FuncNotFound)."}}
```

④h = D3 export=eth 增补必要性的直接证据：未导出的 network 方法在 ETH API 一律 `FuncNotFound`。

### B-⑤ 决策登记（R2#3 门）

| 项 | 结论 |
|---|---|
| 主通道 | `eth_sendTransaction`（#0 与 #1 双 sender 均成功，门条件满足）——`from` 每调用可选 |
| 读通道 | `eth_call`（params `[{to,data},"latest"]`） |
| 回执 | `eth_getTransactionReceipt` 轮询，`status=="0x1"` 为成功 |
| 计数/块高 | `eth_getTransactionCount` / `eth_blockNumber` 透传可用 |
| estimateGas | **不可用且不需要**（B-③④b） |
| R1 退路（subprocess cast send） | 不触发（门通过）；密钥表仍按方案落 rpc.py 常量（地址经 B-② from 实测核） |

## C. NodeClient 冒烟（T2-4，重写后 python 直连 T1 实例）

```
$ python -（NodeClient("http://127.0.0.1:10087", contract="0xcbEAF3…")）
[0] calldata bytes match cast: True                     # _encode_args 输出与 cast calldata 字节级一致（首版 string 编码漏长度字，LyquorInput 错误暴露后修复）
[1] deal_info(deal-1) = {'id': 'deal-1', 'buyer': '0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266', 'seller': 'agent-bob', 'amount': 1000000000000000000, 'state': 'Funded', 'timeout_slots': 300, 'deadline_slot': 384}
[2] NodeError as expected: eth_call: rpc error -1: Execution error: Barrel(Lyquid(LyquidRuntime("no such deal"))).
[3] block_number = 86
[4] balance_of(#1)  -> NodeError -1: Barrel(FuncNotFound)   # 预期：基线实例先于 D3 增补（与 §B-④h 同证），T3 新实例复测
[5] due_deals()     -> NodeError -1: Barrel(FuncNotFound)   # 同上
```

读/错/块高三通道全通；写通道由 T5/T6 实测覆盖（keeper/demo）。
