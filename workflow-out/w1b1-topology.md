# W1-B1 多节点拓扑文档（T1 交付）

> 本文全部输出为 2026-10-24 实跑存档，非转录。执行环境：Windows + Git Bash（MSYS）+ Docker Compose v2。
> 执行基线：trustbridge HEAD = f83ab52（W1-A 完成态），ldk = 官方克隆只读使用。

## 1. 实际起法（从零复现）

```bash
# ① 停单节点 devnet（保留卷；host 10087 端口互斥，必须先停）
cd <workspace>/ldk
docker compose -p ldk -f docker-compose.yaml down

# ② 起 4 节点 multi 栈（anvil + registry:3 + node1-4 + setup-devnet bootstrap）
docker compose -f docker/multi/docker-compose.yaml up -d

# ③ 观察 bootstrap 三步（等 node1 → 幂等部署 bartender → 等 GetPeers≥3 → availability activate）
docker compose -f docker/multi/docker-compose.yaml logs -f setup-devnet
```

本轮 bootstrap 日志全文存档：`workflow-out/_w1b1-setupdevnet-bootstrap.log`。要点：

- bartender 幂等部署：`Lyquid-f7vljmg2ymknxo6ox4lwdblt6ldygrc2kf6aa` → contract `0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0`
- availability activate：`Committee Size: 4, Threshold: 1`，Source/Destination Epoch = 1

## 2. 节点实测身份与端口映射

| 容器 | host API | 容器内 API | GetNodeInfo 实测 nodeId | 版本 |
|---|---|---|---|---|
| multi-node1-1 | 127.0.0.1:10087 | node1:10087 | `Node-ve3tav5jw5ico7or34gcb6ni7rtmd35uokriuijygabd3tsltd7fj6ia` | 0.8.1+9e5108a |
| multi-node2-1 | 127.0.0.1:11087 | node2:10087 | `Node-j3fcdy5twah7csa6pr4jhgxcvszycxdms2hsen5m7lrvtezqlv52cqaa` | 0.8.1+9e5108a |
| multi-node3-1 | 127.0.0.1:12087 | node3:10087 | `Node-2folhfgf4kuyfdenaq3l4dnamv7yxrnqq3zbp64thfa5esqgxhv6wzqa` | 0.8.1+9e5108a |
| multi-node4-1 | 127.0.0.1:13087 | node4:10087 | `Node-oq2lcra5u4ksufzsv2ciqbl56dkp5c653ikzkx3lh62tai566d7dseia` | 0.8.1+9e5108a |

四节点与 SDK 锁定 rev fd575e8（v0.8.1）同版本。**容器内端口恒为 10087**（11087/12087/13087 仅宿主侧映射，compose :57/:66/:75）——容器内 cast send/shaker 一律用 `nodeX:10087`。

## 3. 节点间通信验证（原始输出）

### 3.1 GetNodeInfo ×4【宿主】

```
=== GetNodeInfo host:10087 ===
{"nodeId":{"value":"Node-ve3tav5jw5ico7or34gcb6ni7rtmd35uokriuijygabd3tsltd7fj6ia"},"version":"0.8.1+9e5108a"}
=== GetNodeInfo host:11087 ===
{"nodeId":{"value":"Node-j3fcdy5twah7csa6pr4jhgxcvszycxdms2hsen5m7lrvtezqlv52cqaa"},"version":"0.8.1+9e5108a"}
=== GetNodeInfo host:12087 ===
{"nodeId":{"value":"Node-2folhfgf4kuyfdenaq3l4dnamv7yxrnqq3zbp64thfa5esqgxhv6wzqa"},"version":"0.8.1+9e5108a"}
=== GetNodeInfo host:13087 ===
{"nodeId":{"value":"Node-oq2lcra5u4ksufzsv2ciqbl56dkp5c653ikzkx3lh62tai566d7dseia"},"version":"0.8.1+9e5108a"}
```

### 3.2 GetPeers ×4（mesh 验证，每节点恰 3 peers）【宿主】

```
=== GetPeers host:10087 (node1) ===
{"peers":[{"id":{"value":"Node-oq2lcra5u4ksufzsv2ciqbl56dkp5c653ikzkx3lh62tai566d7dseia"}},{"id":{"value":"Node-j3fcdy5twah7csa6pr4jhgxcvszycxdms2hsen5m7lrvtezqlv52cqaa"}},{"id":{"value":"Node-2folhfgf4kuyfdenaq3l4dnamv7yxrnqq3zbp64thfa5esqgxhv6wzqa"}}]}
=== GetPeers host:11087 (node2) ===
{"peers":[{"id":{"value":"Node-ve3tav5jw5ico7or34gcb6ni7rtmd35uokriuijygabd3tsltd7fj6ia"}},{"id":{"value":"Node-oq2lcra5u4ksufzsv2ciqbl56dkp5c653ikzkx3lh62tai566d7dseia"}},{"id":{"value":"Node-2folhfgf4kuyfdenaq3l4dnamv7yxrnqq3zbp64thfa5esqgxhv6wzqa"}}]}
=== GetPeers host:12087 (node3) ===
{"peers":[{"id":{"value":"Node-ve3tav5jw5ico7or34gcb6ni7rtmd35uokriuijygabd3tsltd7fj6ia"}},{"id":{"value":"Node-j3fcdy5twah7csa6pr4jhgxcvszycxdms2hsen5m7lrvtezqlv52cqaa"}},{"id":{"value":"Node-oq2lcra5u4ksufzsv2ciqbl56dkp5c653ikzkx3lh62tai566d7dseia"}}]}
=== GetPeers host:13087 (node4) ===
{"peers":[{"id":{"value":"Node-ve3tav5jw5ico7or34gcb6ni7rtmd35uokriuijygabd3tsltd7fj6ia"}},{"id":{"value":"Node-2folhfgf4kuyfdenaq3l4dnamv7yxrnqq3zbp64thfa5esqgxhv6wzqa"}},{"id":{"value":"Node-j3fcdy5twah7csa6pr4jhgxcvszycxdms2hsen5m7lrvtezqlv52cqaa"}}]}
```

交叉核对：4 节点 peers 并集 = 4 个互异 ID，逐一与 `node1-4.toml` 预置 peer ID 一致（node1.toml 列 {j3fcdy=node2, 2folhf=node3, oq2lcr=node4}；单次 GetPeers 自排除、只得 3 个，**并集才得全 4**——S2 委员会成员获取以此为准）。

### 3.3 GetLyquidInfo ×4（同一 bartender contract 全网可见 = 跨节点状态同步证据）【宿主】

四节点输出逐字节一致（lyquidId `Lyquid-f7vljmg2ymknxo6ox4lwdblt6ldygrc2kf6aa`，contract `0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0`，imageDigest `0xcd33f78d…75c9`，`lyquidNumber:{image:1,var:4}`）：

```
{"lyquidInfo":{"lyquidId":{"value":"Lyquid-f7vljmg2ymknxo6ox4lwdblt6ldygrc2kf6aa"},"contract":{"value":"0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0"},"sequenceBackend":"0xb813e12d322b9312d099fba2da69b8f7edc8656fdc673f5e454b894471ca3cbd","imageDigest":"0xcd33f78d230119026c297ee314024c8ac026f27886e7e99c5b9f991859c175c9","lyquidNumber":{"image":1,"var":4}}}
```

### 3.4 availability gate 状态【setup-devnet 容器】

```
$ docker compose -f docker/multi/docker-compose.yaml run --rm setup-devnet /usr/local/bin/shaker availability status
Source Epoch: 1
Destination Epoch: 1
Committee Size: 4
Threshold: 1
Deadline Blocks: 50
Admitted Images: 1
Pending Deployments: 0
Committee: Node-j3fcdy5twah7csa6pr4jhgxcvszycxdms2hsen5m7lrvtezqlv52cqaa, Node-oq2lcra5u4ksufzsv2ciqbl56dkp5c653ikzkx3lh62tai566d7dseia, Node-ve3tav5jw5ico7or34gcb6ni7rtmd35uokriuijygabd3tsltd7fj6ia, Node-2folhfgf4kuyfdenaq3l4dnamv7yxrnqq3zbp64thfa5esqgxhv6wzqa
```

## 4. 与单节点通道差异表

| 维度 | 单节点（W1-A） | multi（W1-B1） |
|---|---|---|
| compose | `ldk/docker-compose.yaml`（项目名 `ldk`） | `ldk/docker/multi/docker-compose.yaml`（项目名 `multi`） |
| 节点 | 1 × lyquor-node:main-latest（0.8.2-dev） | 4 × lyquor-node:v0.8.1（与 SDK rev fd575e8 对齐） |
| host 端口 | 10087 | 10087/11087/12087/13087（容器内均 10087） |
| 常驻 tools 容器 | `ldk-tools-1`（compose 常驻） | **无常驻 tools**（setup-devnet 为 one-shot）→ 探针部署用临时 `multi-tools` 容器（§6） |
| shaker 部署参数 | `scripts/deploy.sh`（docker cp + 容器内 deploy，无 -r） | 需 `-r http://registry:8000/lyquids --endpoint ws://node1:10087/ws` + `--private-key <anvil#0>` |
| sequencer | anvil 容器（单） | 共享 anvil（`ws://anvil:8545`，state 落卷 anvil-state） |
| 镜像分发 | 本地构建推送 | 本地 OCI `registry:3`（host :8000）+ ghcr fallback |
| 委员会 | 无 availability gate 多节点语义 | bootstrap 即 `availability activate --committee auto --threshold 1`（4 节点入会） |
| 部署签名者 | ldk-tools-1 内默认钥 | **必须显式 `--private-key`（anvil#0）**——与后续 cast send 同钥，S2 `eth_guard = creator` 守卫依赖 |

## 5. ldk_cargo-cache 卷复用登记（R4 缓解，实测）

- `docker volume ls` 本轮实测：`ldk_cargo-cache`、`ldk_node-data` 存在（单节点项目 `down` 未清卷）；multi 自建卷 `multi_anvil-state`、`multi_node1-4-data`、`multi_registry-data`。
- fd575e8 依赖 git db 在 `ldk_cargo-cache` 卷内；`down` 不清卷 → 临时工具容器（multi-tools）挂 `ldk_cargo-cache:/usr/local/cargo` 即免重拉全部依赖，**无需"down 前拷贝 db"步骤**。实测：multi-tools 内 `shaker deploy` 全量 release 构建 28.55s（含全部依赖编译），git/registry 缓存全部命中卷。
- 复用挂载命令（T2 第 6 步实际执行）：`docker run -d --name multi-tools --network multi_default -e LYQUOR_ENDPOINT=ws://node1:10087/ws -v ldk_cargo-cache:/usr/local/cargo ghcr.io/lyquor-labs/lyquor-tools:v0.8.1 sleep infinity`
- setup-devnet `run --rm -v ldk_cargo-cache:/usr/local/cargo …` 为同效退路（同镜像同网络）。
- **边界登记**：rustup 工具链目录（RUSTUP_HOME=/usr/local/rustup）不在此卷内——shaker 按需下载的 rust-std sysroot 缓存随容器层丢失。单节点切回后 ldk-tools-1（新容器）部署被该下载阻断（容器/宿主均不可达 github；详见 w1b1-s1-timer.md §5-1），跨栈部署时注意。

## 5b. W1-B1 lyquid 实例沿革（multi 链上）

| # | Lyquid ID | Contract | 说明 |
|---|---|---|---|
| 1 | Lyquid-ahjg4huwvban3bvhxue7rcbaw4mnltwyolhqa | 0x0165878A594ca255338adfa4d48449f69242Eb8F | 首次部署（deploy 复跑归档前），弃用 |
| 2 | Lyquid-wsd6v4xjliqgjrcaiikuafrjmaho4q4hqiwqa | 0x2279B7A0a67DB372996a5FaB50D91eAA73d2eBe6 | deploy 全日志归档件（w1b1-t2-deploy.txt）；console 通道发现 |
| 3 | Lyquid-zz2juejwa3xj5cx6jqespjhlzzr7bjchoi7aa | 0x9A676e781A523b5d0C0e43731313A708CB607508 | **S1 实验实例**（加 probe_net_report） |
| 4 | Lyquid-rkkfz4d3tvxcp4aflxpqu26gxmhyxepvei3qa | 0xcbEAF3BDe82155F56486Fb5a1072cb8baAf547cc | **S2 实验实例**（probe_net_config + network 化 bump_threshold） |

（shaker deploy 每次创建新实例；Lyquid ID 由部署者+内容确定性派生——#4 与 W1-A 单节点主实例同 ID，异链无冲突。）

## 6. Git Bash（MSYS）宿主侧注意事项（本轮实测）

- Git Bash 会把容器内绝对路径改写为 Windows 路径（`/usr/local/bin/shaker` → `F:/Git/usr/local/bin/shaker`，导致 `exec` 失败一次，已存档）。**宿主 docker exec / compose run 带容器内路径时须加 `MSYS_NO_PATHCONV=1` 前缀**。
- 宿主 curl 探活用 `127.0.0.1:10087|11087|12087|13087`；容器内命令（cast send / shaker）用 `nodeX:10087`。

## 7. 起停 / 回退命令

```bash
# multi 停止（保留全部卷）
docker compose -f docker/multi/docker-compose.yaml down

# multi 重置（含 anvil 链状态与节点数据）
docker compose -f docker/multi/docker-compose.yaml down -v

# 切回单节点（W1-A 通道）
cd <workspace>/ldk
docker compose -p ldk -f docker-compose.yaml up -d      # 或 scripts/devnet-up.sh
```

## 8. 信任模型差异（如实登记为 W1-B 后续边界条件）

multi devnet ≠ 生产拜占庭环境：

1. **单一共享 anvil sequencer**：排序权威单点，无分片/多 sequencer 抗审查假设；链状态持久化仅靠 anvil 退出时落盘（无 --state-interval，SIGKILL 可能回退——S1 实验 b 因此只杀节点服务、保留 anvil）。
2. **registry 分发信任**：lyquid 镜像经本地 registry:3 分发，无镜像内容审计。
3. **availability gate 委员会 ≠ oracle 委员会**：bootstrap 的 `availability activate --committee auto` 是平台级准入门（4 节点、threshold 1）；S2 实验的认证委员会是 lyquid 内 oracle 状态机独立配置，二者不可混同。
4. 四节点均由确定性 seed 生成身份（node1 seed=0x0），密钥/身份非安全生成域，仅供拓扑/语义实验。

## 9. 人工验证命令清单（宿主 Git Bash；容器内命令在 T2/T3/T4 文档另有全量清单）

```bash
# 0) 切换到 multi
cd <workspace>/ldk && docker compose -p ldk -f docker-compose.yaml down
docker compose -f docker/multi/docker-compose.yaml up -d
docker compose -f docker/multi/docker-compose.yaml logs -f setup-devnet   # 等三步完成

# 1) 节点身份
for p in 10087 11087 12087 13087; do curl -s --data '{}' -H 'content-type: application/json' \
  http://127.0.0.1:$p/lyquor.node.v1.NodeService/GetNodeInfo; echo; done

# 2) mesh
for p in 10087 11087 12087 13087; do curl -s --data '{}' -H 'content-type: application/json' \
  http://127.0.0.1:$p/lyquor.node.v1.NodeService/GetPeers; echo; done

# 3) 跨节点状态同步
for p in 10087 11087 12087 13087; do curl -s --data '{}' -H 'content-type: application/json' \
  http://127.0.0.1:$p/lyquor.lyquid.v1.LyquidService/GetLyquidInfo; echo; done

# 4) availability gate
MSYS_NO_PATHCONV=1 docker compose -f docker/multi/docker-compose.yaml run --rm \
  setup-devnet /usr/local/bin/shaker availability status
```

## 10. W1-B1 收尾时环境状态与处置命令（T5 实录）

- 收尾时执行了切回：multi 栈保留运行（plan T5-4；W1-B2 可复用），单节点以 `docker compose -p ldk -f docker-compose.yaml up -d` 随时可恢复（本轮 S1 单节点交叉验证曾切至单节点，因 sysroot 下载阻断未完成部署，切回详见 implementation.md）。
- 临时容器处置：`docker rm -f multi-tools`（已完成——注意其容器层内缓存随之丢失，见 §5 边界登记）。
- 重置类命令（勿随意）：`docker compose -f docker/multi/docker-compose.yaml down -v` 会清空 anvil 链与 4 节点数据（W1-B1 实验现场即销毁）。
