# W1-B1 S2 委员会认证回合完整证据（T4 交付）

> 全部为 2026-10-24 实跑实录。实验实例：`Lyquid-rkkfz4d3tvxcp4aflxpqu26gxmhyxepvei3qa` @ `0xcbEAF3BDe82155F56486Fb5a1072cb8baAf547cc`（multi 4 节点 v0.8.1；部署命令与实例沿革见 `_w1b1-deploy-zz2jue.txt` 头注 + `w1b1-t2-deploy.txt`）。部署签名者与全部 cast send 同钥 anvil#0（`0xac0974…ff80` → 地址 `0xf39F…9266`），S2 守卫前提成立。

## 1. 委员会成员获取与编码（方案 T4 第 1 步，修订指令 1）

来源 = GetNodeInfo×4（T1 实测，见 w1b1-topology.md §3.1；GetPeers×4 并集交叉核对一致）。编码 = demo.sh:199-212 官方 Python 段逐行镜像执行（容器内 python3）：去 `Node-` 前缀 → upper → 补 `=` 至 8 倍数 → b32decode → 35 字节校验 → 取前 32 字节 → `"0x"+hex`。

| 节点 | nodeId（GetNodeInfo） | bytes32（实跑换算） |
|---|---|---|
| node1 | Node-ve3tav5jw5ico7or34gcb6ni7rtmd35uokriuijygabd3tsltd7fj6ia | `0xa9373057a9b750277dd1df0c20f9a8fc66c1efb472a28a213830023dce4b98fe` |
| node2 | Node-j3fcdy5twah7csa6pr4jhgxcvszycxdms2hsen5m7lrvtezqlv52cqaa | `0x4eca21e3b3b00ff1481e7c78939ae2acb3815c6c968f2237acfae35993305d7b` |
| node3 | Node-2folhfgf4kuyfdenaq3l4dnamv7yxrnqq3zbp64thfa5esqgxhv6wzqa | `0xd15cb394c5e2a9828c8d0436be0da0657f8bc5b086f217fb933941d24a06b9eb` |
| node4 | Node-oq2lcra5u4ksufzsv2ciqbl56dkp5c653ikzkx3lh62tai566d7dseia | `0x7434b1441da7152a1732ae8488057df0d4fe8bddda15955f6b3fb53023bef0fe` |

**示例数组（ABI 面 `bytes32[]`，官方 run.sh:257 `configure_committee(bytes32[])` 同形）**：

```
[0xa9373057a9b750277dd1df0c20f9a8fc66c1efb472a28a213830023dce4b98fe,0x4eca21e3b3b00ff1481e7c78939ae2acb3815c6c968f2237acfae35993305d7b,0xd15cb394c5e2a9828c8d0436be0da0657f8bc5b086f217fb933941d24a06b9eb,0x7434b1441da7152a1732ae8488057df0d4fe8bddda15955f6b3fb53023bef0fe]
```

（注：实际 configure 时的 4 元素顺序即上表 node1-4 顺序。）`shaker to-hex Lyquid-rkkfz4d3…` = `0x8a945cf07b9d6e27f0055ddf0A6Bc6BB0F8b91f5`（下称 TARGET，advance/finalize 的 address 参数）。

## 2. configure（仅入 staging）

```
cast send 0xcbEAF3BD…7cc "probe_configure(bytes32[],uint16)" "[<上表4元素>]" 1 \
  --private-key <anvil#0> --rpc-url http://node1:10087/api
→ blockNumber 63 / status 1 / tx 0xc397ea77c7257a883d810ba64fbf813270e2cb3f1218744d0fa32ffd70831306
console: probe_configure: staged committee of 4 nodes threshold=1 (dest epoch advance/finalize required to activate)
```

守卫 `eth_guard = creator` 通过（deploy 与 cast send 同钥 anvil#0）。`Vec<NodeID>` 的 ABI 面即 bytes32[] 实证。

## 3. 两阶段激活（advance → finalize）

**通道修正（SPIKE-3，重要）**：方案规定 advance/finalize 走 cast send＋观测驱动（依据"W1-A eth_call 已证不可用"）。本环境实测：

1. **cast send 通道失败**：`cast send __lyquor_oracle_advance_epoch(...) "cert_probe" $TARGET false` → status 1（×2 次，tx 0xf4c240d3…60fe1350 与重试），但 dest epoch 30s+ 恒 0，链上无内层 certified-call 交易（逐块 1 tx 均为我方 send；anvil 70 笔 sendRawTransaction 与 70 块一一对应，节点未追加提交）。
2. **cast call 通道成功**（官方 demo.sh:319-336 原形）：首次 `cast call … advance … returns (bool)` 即返回 **true**，5s 内 dest epoch **0→1**。
3. 根因定位：`__lyquor_oracle_advance_epoch` 内部 = validate_phase（UPC 向委员会同步收签）→ `submit_call` 异步上链。**cast call = 节点本地执行路径，内层提交能落地；cast send = 链序执行路径，内层提交静默丢失**（与 run_round 同症，见 §4；机制在节点侧，未深挖）。
4. W1-A 的"eth_call 不可用"是单节点 0.8.2-dev 环境/版本的实测，本 multi v0.8.1 不成立——读与执行均可用。**本偏离（cast send → cast call）即方案"观测不满足驱动"的自然结果，且与官方 demo 形态一致**，SPIKE 登记 implementation.md。

```
[advance]  cast call --rpc-url http://node1:10087/api $CTR \
             "__lyquor_oracle_advance_epoch(string,address,bool) returns (bool)" "cert_probe" 0x8a945cf07b9d6e27f0055ddf0A6Bc6BB0F8b91f5 false
           → true
[poll]     dest epoch（cast call __lyquor_oracle_dest_epoch_info）: poll1 = 1   （旧值 0）
[finalize] cast call … "__lyquor_oracle_finalize_epoch(string,address,bool) returns (bool)" "cert_probe" $TARGET false
           → true
```

**激活确认（get_epoch 语义对照 demo_wait_for_committee）**——dest 面（含 full config）：

```
cast call "__lyquor_oracle_dest_epoch_info(string,bool) returns (uint64,bytes32,uint32,bytes)" "cert_probe" true
→ 1                                          （dest epoch = 1）
→ 0x2ac7a61c1aad313cdc8b4099c307eb18f5b85edf7b25195059ef35f00f9e1bc3   （config_hash）
→ 5                                          （change_count = 4×AddNode + 1×SetThreshold）
→ 0x0400 20 <a93730…98fe> 01 20 <4eca21…5d7b> 02 20 <d15cb3…b9eb> 03 20 <7434b1…b0fe> 01
   （full config：4 委员会成员 signer id 0/1/2/3，逐字节可见上表 4 个 bytes32，末位 threshold=0x01）
```

跨节点可见性：node2/node3 通道 `__lyquor_oracle_dest_epoch_info … false` → 均 `1`。源侧 get_epoch（finalize 后才 >0，source.rs:289-291/409）由 bump 行为佐证（§5：epoch=0 时必 false 的语义在 epoch=1 下翻转）。

## 4. probe_run_round 认证回合（核心观测）

```
[cast send 版] status 1, tx 0x83d4c5acd0ae730d765211baa7644b748b1b735ea06460846d1337541726684b
               → 无 on_certified println、无内层交易（同 §3.1 症状，返回 Ok(false) 路径）
[cast call 版] run_round → true；console 全程实录：
  probe_run_round: node=Node-ve3tav5jw5ico7or34gcb6ni7rtmd35uokriuijygabd3tsltd7fj6ia starting propose_and_certify (avg_num=1)
  probe_propose: node=Node-ve3tav…6ia round=1 ts_ms=1792852758588 (avg_num=1 target.seq_id=HashBytes(Hash("b813e12d…3cbd")))
  probe_aggregate: aggregated round=1 node=Node-ve3tav…6ia from 1 input(s)
  probe_aggregate: aggregated round=1 node=Node-ve3tav…6ia from 1 input(s)
  probe_run_round: certified call submitted to the sequencing backend
  probe_on_certified: ctx.cert.signers RAW = [0] (type Vec<SignerID>=Vec<u32>, len=1)
  probe_on_certified: signer 0 -> Node-ve3tav5jw5ico7or34gcb6ni7rtmd35uokriuijygabd3tsltd7fj6ia
  probe_on_certified: payload(round=1 node=Node-ve3tav…6ia ts_ms=1792852758588) recorded; probe_rounds=1
```

内层 certified call 上链实证：call 前头部块 71-73 均 1 tx（我方历史 send）；call 后头部推进至 block 74 且**该块交易非我方 cast send**（cast call 不产交易）= `submit_certified_call!` 提交的 `probe_on_certified` 调用。

### ctx.cert.signers 形态结论

| 维度 | 实测 |
|---|---|
| 原始域 | `Vec<SignerID>`，SignerID = u32（primitives/src/oracle.rs:65；OracleCert.signers :130-136）——**数字 signer 序号列表，非 NodeID、非地址** |
| 本次值 | `[0]`（threshold=1 单签：唯一应答委员会成员的 signer id） |
| 映射 | `ctx.signer_node_id(signer_id as u64) -> Option<NodeID>`（runtime/mod.rs:560） |
| 映射结果 | `0 → Node-ve3tav…6ia`（node1，本轮唯一投票者/签名者 = 提案节点自身，吻合 threshold=1） |
| 落库 | network `probe_last_signers_raw=[0]`、`probe_last_signers_nodes=["Node-ve3tav…"]`、`probe_rounds=1` |

### 与 W1-A ctx 事实交叉核对表

| 项 | W1-A 实测（implementation.md §④/§⑤） | W1-B1 本轮实测 | 勾稽 |
|---|---|---|---|
| 普通 network 方法 ctx | CallContext：origin/caller/input/lyquid_id（+node_id）字段，无 cert | 普通 network 面（probe_mark_fire 等）行为一致 | 一致 |
| 认证回调 ctx | 未测（W1-A 无 oracle 路径） | `CertifiedContextImpl` 增加 `pub cert: OracleCert`（runtime/mod.rs:534）+ `signer_node_id` 访问器（:560），cert.signers=数字域 | **本轮钉死** |
| ctx.caller 字符串形 | EIP-55 `0xf39F…9266`（D4b 探针） | 部署/cast 全程同钥，creator 守卫命中 | 一致 |
| eth_call 读路径 | "Invalid contract address"（0.8.2-dev 单节点） | **可用**（v0.8.1 multi；读+执行） | 环境差异，SPIKE-2 |
| consensus 时间 | chain_pos().block() | propose ts_ms=lyquor_api::systime()（wall clock 域） | 互补观测面 |

## 5. set_threshold（epoch>0 后）

```
cast send "probe_bump_threshold(uint16)" 2   → status 1, tx 0x4f2ce7e3ad7bf272e05537a45013735a0a7d5ebe9a49a33992ac7aa6cf3918fa
console: probe_bump_threshold: set_threshold(2) -> true (false = epoch==0 or same-threshold)
重复同一调用（同值）:
console: probe_bump_threshold: set_threshold(2) -> false
```

- `true`：epoch=1（>0，source.rs:268-271 的 epoch-0 恒 false 不再命中）且 1→2 变更成功入 staging。
- 重复 `false`：same-threshold 短路（source.rs:272-274）——**间接证明 staging.threshold 已为 2**（若第一次未生效，第二次应为 true）。
- dest current 仍为 threshold=1（§4 full config）——staging→dest 需再走一轮 advance/finalize（未做，见 §7）。

## 6. 方案内可选加分项（threshold=2 双签聚合）：**未执行**（时间盒让位于 S1/T5；单签回合已达成 ctx.cert.signers 形态验证目标）。

## 7. 遗留项（如实登记）

1. bump 后的阈值 2 未做第二轮 advance/finalize 激活（平台流程同 §3，无新信息量）。
2. `probe_net_config` 的 cast send 通道 println 不可见（SPIKE-1/§0.1 of w1b1-s1-timer.md）；配置回显改由 `__lyquor_oracle_dest_epoch_info(full_config=true)` 结构化读承载（§3）。
3. 委员会成员换算的独立复核：官方 demo 代码逐行镜像 + 激活后 full config 中的 4 个 bytes32 与换算值逐字节一致（§3 十六进制段），双重印证。

## 8. 人工复现命令清单（容器内；KEY/CTR/TARGET/LY 见文首）

```bash
# 1) 换算（GetNodeInfo×4 → bytes32，demo.sh:199-212 Python 段）
# 2) configure（仅 staging）
cast send $CTR "probe_configure(bytes32[],uint16)" "[<4×bytes32>]" 1 --private-key $KEY --rpc-url http://node1:10087/api
# 3) advance（cast call，观测 true）→ poll dest epoch → finalize（cast call，观测 true）
cast call --rpc-url http://node1:10087/api $CTR "__lyquor_oracle_advance_epoch(string,address,bool) returns (bool)" "cert_probe" $TARGET false
cast call --rpc-url http://node1:10087/api $CTR "__lyquor_oracle_dest_epoch_info(string,bool) returns (uint64,bytes32,uint32,bytes)" "cert_probe" true
cast call --rpc-url http://node1:10087/api $CTR "__lyquor_oracle_finalize_epoch(string,address,bool) returns (bool)" "cert_probe" $TARGET false
# 4) run_round（cast call！）→ console 取 on_certified
cast call --rpc-timeout 30 --rpc-url http://node1:10087/api $CTR "probe_run_round() returns (bool)"
timeout 60 shaker console $LY --endpoint ws://node1:10087/ws
# 5) threshold
cast send $CTR "probe_bump_threshold(uint16)" 2 --private-key $KEY --rpc-url http://node1:10087/api
```
