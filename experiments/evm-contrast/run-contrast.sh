#!/usr/bin/env bash
# TrustBridge — 纯 EVM 对照实验（R3 目标 B）：容器内一键执行
#   build → deploy → 三流（normal / timeout / adversarial）→ gas/代码量采集
#
# 宿主引导（Git Bash；MSYS 路径改写纪律同 lyquid 通道，w1b1-topology.md §6）：
#   MSYS_NO_PATHCONV=1 docker exec multi-tools rm -rf /tmp/tb-evm
#   MSYS_NO_PATHCONV=1 docker cp experiments/evm-contrast/. multi-tools:/tmp/tb-evm
#   MSYS_NO_PATHCONV=1 docker exec -w /tmp/tb-evm multi-tools bash run-contrast.sh
#   MSYS_NO_PATHCONV=1 docker cp multi-tools:/tmp/tb-evm/gas-raw.txt workflow-out/_r3-t4-gas-raw.txt
#   MSYS_NO_PATHCONV=1 docker cp multi-tools:/tmp/tb-evm/report.txt  workflow-out/_r3-t4-flows-raw.txt
#
# 固定事实（plan §2 规划期实证）：forge 1.7.1 + 自动 solc 容器内可用；anvil 从
# 容器内可达 http://anvil:8545（宿主无端口映射）——本合约与 Lyquid 实例共享同一
# sequencer，双方链上证据同链可比。
#
# 角色（与 rpc.py 角色表同源；anvil 确定性开发账户）：
#   #0 = broker/deployer（committeeConfig 的 deployer 门 + broker 费收方）
#   #1 = buyer   #2 = seller   #3 = 额外委员会成员
#
# 诚实边界（报告须引用）：委员会由 deployer 管理的地址表承载（无平台认证机制）；
# k-of-n 签名聚合为自建 ECRECOVER；超时域 = block.timestamp（Lyquid = slot）。
set -euo pipefail

RPC="${RPC:-http://anvil:8545}"
DEPLOY_KEY="${DEPLOY_KEY:-0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80}"
BUYER_KEY="${BUYER_KEY:-0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d}"
SELLER_KEY="${SELLER_KEY:-0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a}"
COMM_KEY="${COMM_KEY:-0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6}"

OUT_DIR="${OUT_DIR:-$PWD}"
GAS_LOG="$OUT_DIR/gas-raw.txt"
REPORT="$OUT_DIR/report.txt"
: > "$GAS_LOG"
: > "$REPORT"

log() { echo "$@" | tee -a "$REPORT"; }
sec() { echo; echo "===== $* =====" | tee -a "$REPORT"; }

# send <label> <key> <cast send args...>：发交易并把 tx/status/gasUsed 记入 gas-raw
send() {
    local label="$1" key="$2"
    shift 2
    local out tx st gas
    out=$(cast send --rpc-url "$RPC" --private-key "$key" "$@" --json)
    tx=$(echo "$out" | jq -r '.transactionHash // empty')
    st=$(echo "$out" | jq -r '.status // empty')
    gas=$(echo "$out" | jq -r '.gasUsed // empty')
    if [ -z "$gas" ] && [ -n "$tx" ]; then
        gas=$(cast receipt "$tx" --rpc-url "$RPC" --json | jq -r '.gasUsed // empty')
    fi
    printf '%s\ttx=%s\tstatus=%s\tgasUsed=%s\n' "$label" "$tx" "$st" "$gas" | tee -a "$GAS_LOG"
    if [ "$st" != "0x1" ]; then
        echo "[T4] FAIL: $label status=$st" >&2
        exit 1
    fi
}

# ---------------------------------------------------------------- addresses --
DEP0=$(cast wallet address --private-key "$DEPLOY_KEY")
BUYER=$(cast wallet address --private-key "$BUYER_KEY")
SELLER=$(cast wallet address --private-key "$SELLER_KEY")
COMM3=$(cast wallet address --private-key "$COMM_KEY")

AMOUNT=1000000000000000000              # 1 ether
AMOUNT_HUMAN="1 ether"
TERMS=$(cast keccak "terms:license:song:midnight-motors:online-video,12mo,EU")
ACCEPT=$(cast keccak "acceptance:deliverable matches license terms")
DOC=$(cast keccak "LICENSE-DOC: grant of song 'midnight-motors' to buyer, online-video,12mo,EU")
FORGED=$(cast keccak "FORGED-LICENSE-DOC: copied template, wrong scope")
REASON=$(cast keccak "dispute: deliverable does not match agreed terms")

sec "[T4] build"
forge build 2>&1 | tee -a "$REPORT"

sec "[T4] deploy"
DEPLOY_JSON=$(forge create Escrow.sol:Escrow --rpc-url "$RPC" --private-key "$DEPLOY_KEY" --broadcast --json)
ADDR=$(echo "$DEPLOY_JSON" | jq -r '.deployedTo')
DEPTX=$(echo "$DEPLOY_JSON" | jq -r '.transactionHash')
DEPGAS=$(cast receipt "$DEPTX" --rpc-url "$RPC" --json | jq -r '.gasUsed')
CODESIZE=$(cast codesize "$ADDR" --rpc-url "$RPC")
SOL_LINES=$(wc -l < Escrow.sol)
log "contract=$ADDR deployTx=$DEPTX deployGasUsed=$DEPGAS runtimeBytecodeBytes=$CODESIZE escrow_sol_lines=$SOL_LINES"
log "roles: deployer/broker=$DEP0 buyer=$BUYER seller=$SELLER committee4=$COMM3"
printf 'deploy\tEscrow\t%s\t%s\t%s\t%s\n' "$DEPTX" "deployGasUsed=$DEPGAS" "codeSize=$CODESIZE" "srcLines=$SOL_LINES" | tee -a "$GAS_LOG"

sec "[T4] committeeConfig(4 members, threshold=3)"
send "committee:committeeConfig" "$DEPLOY_KEY" "$ADDR" \
    "committeeConfig(address[],uint256)" "[$DEP0,$BUYER,$SELLER,$COMM3]" 3
log "committeeSize=$(cast call "$ADDR" "committeeSize()(uint256)" --rpc-url "$RPC") threshold=$(cast call "$ADDR" "threshold()(uint256)" --rpc-url "$RPC")"

balance() { cast balance "$1" --rpc-url "$RPC"; }

# ---------------------------------------------------------------- flow 1 ----
sec "[T4] flow 1 normal: create -> fund -> notarize -> deliver -> complete"
send "normal:createDeal" "$BUYER_KEY" "$ADDR" \
    "createDeal(address,address,uint256,uint16,bytes32,bytes32,uint64,uint8)" \
    "$SELLER" "$DEP0" "$AMOUNT" 200 "$TERMS" "$ACCEPT" 2000 90
ID1=$(cast call "$ADDR" "dealCounter()(uint256)" --rpc-url "$RPC")
log "normal deal=$ID1 state=$(cast call "$ADDR" "stateOf(uint256)(uint8)" "$ID1" --rpc-url "$RPC") (Qualified=1)"
B_BEFORE=$(balance "$BUYER")
send "normal:fund" "$BUYER_KEY" "$ADDR" "fund(uint256)" "$ID1" --value "$AMOUNT"
send "normal:notarize(acceptance)" "$SELLER_KEY" "$ADDR" \
    "notarize(uint256,address,bytes32)" "$ID1" "$BUYER" "$ACCEPT"
send "normal:submitDeliverable" "$SELLER_KEY" "$ADDR" "submitDeliverable(uint256,bytes32)" "$ID1" "$DOC"
send "normal:complete" "$BUYER_KEY" "$ADDR" "complete(uint256)" "$ID1"
log "normal final state=$(cast call "$ADDR" "stateOf(uint256)(uint8)" "$ID1" --rpc-url "$RPC") (Settled=5) buyer=$B_BEFORE->$(balance "$BUYER") seller=$(balance "$SELLER") broker=$(balance "$DEP0")"

# ---------------------------------------------------------------- flow 2 ----
sec "[T4] flow 2 timeout: create -> fund -> warp -> claimTimeout"
send "timeout:createDeal" "$BUYER_KEY" "$ADDR" \
    "createDeal(address,address,uint256,uint16,bytes32,bytes32,uint64,uint8)" \
    "$SELLER" "$DEP0" "$AMOUNT" 200 "$TERMS" "$ACCEPT" 2000 90
ID2=$(cast call "$ADDR" "dealCounter()(uint256)" --rpc-url "$RPC")
T_BEFORE=$(balance "$BUYER")
send "timeout:fund" "$BUYER_KEY" "$ADDR" "fund(uint256)" "$ID2" --value "$AMOUNT"
DL=$(cast call "$ADDR" "deadline(uint256)(uint64)" "$ID2" --rpc-url "$RPC")
log "timeout deal=$ID2 deadline=$DL now=$(cast block latest --field timestamp --rpc-url "$RPC")"
cast rpc evm_increaseTime 30 --rpc-url "$RPC" > /dev/null
cast rpc evm_mine --rpc-url "$RPC" > /dev/null
log "timeout warp: now=$(cast block latest --field timestamp --rpc-url "$RPC") (deadline=$DL)"
send "timeout:claimTimeout" "$COMM_KEY" "$ADDR" "claimTimeout(uint256)" "$ID2"
log "timeout final state=$(cast call "$ADDR" "stateOf(uint256)(uint8)" "$ID2" --rpc-url "$RPC") (Refunded=6) buyer=$T_BEFORE->$(balance "$BUYER")"

# ---------------------------------------------------------------- flow 3 ----
sec "[T4] flow 3 adversarial: forged deliverable -> dispute -> k-of-n verdict(NotFulfilled)"
send "adv:createDeal" "$BUYER_KEY" "$ADDR" \
    "createDeal(address,address,uint256,uint16,bytes32,bytes32,uint64,uint8)" \
    "$SELLER" "$DEP0" "$AMOUNT" 200 "$TERMS" "$ACCEPT" 60000 90
ID3=$(cast call "$ADDR" "dealCounter()(uint256)" --rpc-url "$RPC")
A_BEFORE=$(balance "$BUYER")
send "adv:fund" "$BUYER_KEY" "$ADDR" "fund(uint256)" "$ID3" --value "$AMOUNT"
send "adv:notarize(acceptance)" "$SELLER_KEY" "$ADDR" \
    "notarize(uint256,address,bytes32)" "$ID3" "$BUYER" "$ACCEPT"
send "adv:submitDeliverable(forged)" "$SELLER_KEY" "$ADDR" "submitDeliverable(uint256,bytes32)" "$ID3" "$FORGED"
send "adv:notarize(dispute)" "$BUYER_KEY" "$ADDR" \
    "notarize(uint256,address,bytes32)" "$ID3" "$SELLER" "$REASON"
send "adv:openDispute" "$BUYER_KEY" "$ADDR" "openDispute(uint256,bytes32)" "$ID3" "$REASON"
DIGEST=$(cast call "$ADDR" "verdictDigest(uint256,uint8)(bytes32)" "$ID3" 1 --rpc-url "$RPC")
ROOT=$(cast call "$ADDR" "evidenceRoot(uint256)(bytes32)" "$ID3" --rpc-url "$RPC")
log "adv deal=$ID3 state=$(cast call "$ADDR" "stateOf(uint256)(uint8)" "$ID3" --rpc-url "$RPC") (Disputed=4)"
log "adv evidenceRoot=$ROOT verdictDigest(NotFulfilled)=$DIGEST evidenceCount=$(cast call "$ADDR" "evidenceCount(uint256)(uint256)" "$ID3" --rpc-url "$RPC")"
SIG1=$(cast wallet sign --no-hash --private-key "$BUYER_KEY" "$DIGEST")
SIG2=$(cast wallet sign --no-hash --private-key "$SELLER_KEY" "$DIGEST")
SIG3=$(cast wallet sign --no-hash --private-key "$COMM_KEY" "$DIGEST")
log "adv sigs: buyer=$SIG1 seller=$SIG2 committee4=$SIG3 (3-of-4, raw digest sign)"
send "adv:applyVerdict(3-of-4)" "$COMM_KEY" "$ADDR" \
    "applyVerdict(uint256,uint8,bytes[])" "$ID3" 1 "[$SIG1,$SIG2,$SIG3]"
log "adv final state=$(cast call "$ADDR" "stateOf(uint256)(uint8)" "$ID3" --rpc-url "$RPC") (Refunded=6) buyer=$A_BEFORE->$(balance "$BUYER")"
log "adv misconduct(seller)=$(cast call "$ADDR" "misconduct(address)(uint256)" "$SELLER" --rpc-url "$RPC") (NotFulfilled must NOT bump; Malicious would)"

# 负向对照：把同一签名集（对 deal ID3 的 digest 签名）重放到另一个争议单——
# ecrecover 出的地址对该 deal 的 digest 不再 ∈ 成员（root/deal 绑定），必须失败。
sec "[T4] negative control: replay the same signature set on a different deal"
send "adv2:createDeal" "$BUYER_KEY" "$ADDR" \
    "createDeal(address,address,uint256,uint16,bytes32,bytes32,uint64,uint8)" \
    "$SELLER" "$DEP0" "$AMOUNT" 200 "$TERMS" "$ACCEPT" 60000 90
ID4=$(cast call "$ADDR" "dealCounter()(uint256)" --rpc-url "$RPC")
send "adv2:fund" "$BUYER_KEY" "$ADDR" "fund(uint256)" "$ID4" --value "$AMOUNT"
send "adv2:openDispute" "$BUYER_KEY" "$ADDR" "openDispute(uint256,bytes32)" "$ID4" "$REASON"
set +e
REPLAY_OUT=$(cast send --rpc-url "$RPC" --private-key "$COMM_KEY" "$ADDR" \
    "applyVerdict(uint256,uint8,bytes[])" "$ID4" 1 "[$SIG1,$SIG2,$SIG3]" 2>&1)
REPLAY_RC=$?
set -e
log "negative-control replay rc=$REPLAY_RC (non-zero = signature set is bound to deal/root; expected)"
log "$REPLAY_OUT"

sec "[T4] summary"
log "sol_source_lines=$SOL_LINES runtime_bytecode_bytes=$CODESIZE deploy_gasUsed=$DEPGAS"
log "gas-raw.txt: $(wc -l < "$GAS_LOG") lines (per-op gasUsed)"
log "DONE"
