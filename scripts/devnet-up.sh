#!/usr/bin/env bash
# Bring up the Lyquor devnet (node + Anvil + tools) per the official quickstart.
# 4 nodes land on 10087 / 11087 / 12087 / 13087.
# SPIKE(W1): run inside the environment where `gh` is authenticated for
# GitHub Packages pulls, then verify `docker compose ps` shows all services.
set -euo pipefail

echo "[devnet] starting Lyquor docker-compose stack..."
docker compose up -d
sleep 5
docker compose ps

NODE=http://127.0.0.1:10087
echo "[devnet] probing node at ${NODE} ..."
curl -sf "${NODE}/lyquor/api" -o /dev/null \
  && echo "[devnet] node API reachable" \
  || echo "[devnet] WARNING: node API not reachable yet (check 'docker compose logs')"
