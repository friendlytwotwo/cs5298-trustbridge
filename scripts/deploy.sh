#!/usr/bin/env bash
# Deploy the TrustBridge Lyquid with shaker.
#
# S5/W1-A 实测通道固化（T4.0/D8 三选一结论）：
#   宿主无 shaker；ldk-tools-1 容器只挂载 ../ldk（trustbridge 不可见）；
#   故通道 = docker cp 源码入容器 + 容器内 shaker deploy。
#   部署默认连接 ws://node:10087/ws（容器内服务名解析）。constructor 输入
#   由 shaker 自动合成（含 bartender 地址/镜像 digest），无需 --input。
#
# 平台 pin：Cargo.toml 现锁 ldk rev=fd575e8（v0.8.1）。D7 触发证据：
#   devnet 节点（main-latest, LDK "0.8.2-dev"）托管层拒绝 v0.7.3 构建
#   （IncompatibleLdk，docker logs ldk-node-1 实测）；全新 0.8.1 部署即
#   "Lyquid discovered and hosted"。详见 workflow-out/implementation.md。
#
# NOTE: `shaker deploy --update` RESETS all state when the code digest changes
# (state-preserving migration is "planned" upstream) — the demo scripts are
# idempotent and re-create their world from scratch on every run by design.
# W1-A 另测得：跨 LDK 大版本的 --update（0.7.3 时代历史 -> 0.8.1 镜像）会让
# 节点重放旧槽位时 pin 住 sequencing（旧 artifact 不兼容）；跨此边界请全新
# 部署（新 Lyquid，状态从零，demo 幂等设计可接受）。
#
# 调用通道（部署后验证）：容器内 cast send <CONTRACT> "faucet(string,uint128)" ...
# 经 http://node:10087/api（ETH API；devnet key 默认 anvil #0）。
# 读路径（eth_call）在本 devnet 构建上对非-bartender lyquid 不可用
# （"Invalid contract address"，节点侧限制，S4/W1-B 对齐）；状态证据走
# shaker console（fund 的 Ok 路径输出 DealView JSON，含 "state":"Funded"）。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONTAINER="${CONTAINER:-ldk-tools-1}"
GUEST_DIR="${GUEST_DIR:-/tmp/tb-lyquid}"

echo "[deploy] syncing crate into $CONTAINER:$GUEST_DIR ..."
docker exec "$CONTAINER" rm -rf "$GUEST_DIR"
docker cp "$REPO_ROOT/lyquid" "$CONTAINER:$GUEST_DIR"
docker exec "$CONTAINER" rm -rf "$GUEST_DIR/target"

echo "[deploy] building + deploying trustbridge Lyquid (in-container shaker)..."
docker exec "$CONTAINER" sh -c "cd $GUEST_DIR && shaker deploy Cargo.toml"
echo "[deploy] done. Verify with: docker exec $CONTAINER shaker console \$(docker exec $CONTAINER shaker list | tail -1)"
