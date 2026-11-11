#!/usr/bin/env bash
# scripts/cluster_up.sh
# Démarrage des services locaux d'une VM du cluster 3 machines.
# Usage : ./scripts/cluster_up.sh <a|b|c>   (a=VM1, b=VM2, c=VM3)

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROLE="${1:-}"

usage() {
    echo "Usage: $0 <a|b|c>"
    echo "  a / vm1   -> machine-a : mongo1 + spark-master"
    echo "  b / vm2   -> machine-b : mongo2 + spark-worker1"
    echo "  c / vm3   -> machine-c : mongo3 + spark-worker2"
}

case "$ROLE" in
    a|vm1|machine-a)
        COMPOSE_DIR="machine-a"
        SERVICES=(mongo1 spark-master)
        ;;
    b|vm2|machine-b)
        COMPOSE_DIR="machine-b"
        SERVICES=(mongo2 spark-worker1)
        ;;
    c|vm3|machine-c)
        COMPOSE_DIR="machine-c"
        SERVICES=(mongo3 spark-worker2)
        ;;
    *)
        usage
        exit 1
        ;;
esac

cd "$ROOT_DIR"
echo "=== Démarrage des services ${SERVICES[*]} sur ${COMPOSE_DIR} ==="
docker compose -f "$COMPOSE_DIR/docker-compose.yml" up -d "${SERVICES[@]}"

echo "[OK] Services démarrés. Après le démarrage des 3 VMs :"
echo "  1. Sur VM1 : python scripts/init_replica_set.py"
echo "  2. Partout : python scripts/check_cluster.py"
