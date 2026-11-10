#!/usr/bin/env bash
# scripts/cluster_up.sh
# Démarrage ordonné de l'infrastructure multi-machines (Guide §4.8)

echo "=== 1. Démarrage des nœuds de données MongoDB ==="
cd "$(dirname "$0")/../machine-a" || exit 1
docker compose up -d mongo1 mongo2

echo "Attente de la disponibilité de mongo1 et mongo2..."
sleep 5

echo "=== 2. Démarrage de Spark Master et Worker 1 sur Machine A ==="
docker compose up -d spark-master spark-worker1

# Optionnel : si le worker 2 est configuré sur Machine A (mode standalone complet)
if docker compose config | grep -q "spark-worker2"; then
  docker compose up -d spark-worker2
fi

echo "=== 3. Vérification de l'état du cluster ==="
cd ..
python3 scripts/check_cluster.py

