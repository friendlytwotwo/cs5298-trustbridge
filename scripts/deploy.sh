#!/usr/bin/env bash
# Deploy the TrustBridge Lyquid with shaker.
# NOTE: `shaker deploy --update` RESETS all state when the code digest changes
# (state-preserving migration is "planned" upstream) — the demo scripts are
# idempotent and re-create their world from scratch on every run by design.
set -euo pipefail
cd "$(dirname "$0")/../lyquid"

echo "[deploy] building + deploying trustbridge Lyquid..."
# SPIKE(W1): confirm the exact shaker invocation from the lyquid-template
# README (deploy input hex, target selection, multi-node registration).
shaker deploy ./Cargo.toml --input 0x00
echo "[deploy] done. Verify with: shaker console"
