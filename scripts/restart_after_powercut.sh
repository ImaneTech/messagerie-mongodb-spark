#!/usr/bin/env bash
# scripts/restart_after_powercut.sh
# Reprise locale après coupure : données MongoDB d'abord, puis Spark.
# Usage : ./scripts/restart_after_powercut.sh <a|b|c>

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROLE="${1:-}"

usage() {
    echo "Usage: $0 <a|b|c>"
    echo "  a / vm1   -> deploy/vm1 : mongo1 puis spark-master"
    echo "  b / vm2   -> deploy/vm2 : mongo2 puis spark-worker1"
    echo "  c / vm3   -> deploy/vm3 : mongo3 puis spark-worker2"
}

case "$ROLE" in
    a|vm1)
        COMPOSE_DIR="deploy/vm1"
        MONGO_SERVICE="mongo1"
        SPARK_SERVICE="spark-master"
        ;;
    b|vm2)
        COMPOSE_DIR="deploy/vm2"
        MONGO_SERVICE="mongo2"
        SPARK_SERVICE="spark-worker1"
        ;;
    c|vm3)
        COMPOSE_DIR="deploy/vm3"
        MONGO_SERVICE="mongo3"
        SPARK_SERVICE="spark-worker2"
        ;;
    *)
        usage
        exit 1
        ;;
esac

cd "$ROOT_DIR"
COMPOSE_FILE="$COMPOSE_DIR/docker-compose.yml"

echo "================================================================="
echo "REPRISE APRÈS COUPURE — ${COMPOSE_DIR}"
echo "================================================================="

echo "Étape 1 : démarrage du nœud MongoDB local (${MONGO_SERVICE})..."
docker compose -f "$COMPOSE_FILE" up -d "$MONGO_SERVICE"

echo "Étape 2 : attente de stabilisation (15s)..."
sleep 15

if [ "$COMPOSE_DIR" = "deploy/vm1" ]; then
    echo "Étape 3 : vérification du Replica Set depuis mongo1..."
    docker exec mongo1 mongosh --quiet --eval "rs.status().members.map(m => m.name + ': ' + m.stateStr)" || true
fi

echo "Étape 4 : démarrage du service Spark local (${SPARK_SERVICE})..."
docker compose -f "$COMPOSE_FILE" up -d "$SPARK_SERVICE"

echo "[OK] ${COMPOSE_DIR} redémarré. Lancez scripts/check_cluster.py après coup sur les 3 VMs."
