#!/usr/bin/env bash
# scripts/cluster_down.sh
# Arrêt ordonné et propre de l'infrastructure (Guide §4.8)

echo "=== 1. Arrêt des Workers et Master Spark ==="
cd "$(dirname "$0")/../machine-a" || exit 1
docker stop spark-worker2 spark-worker1 spark-master 2>/dev/null

echo "=== 2. Arrêt propre des nœuds MongoDB ==="
docker stop mongo2 mongo1 2>/dev/null

echo "[OK] Nœuds de la machine A arrêtés proprement."
