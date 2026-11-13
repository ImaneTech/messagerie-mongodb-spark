#!/usr/bin/env bash
# scripts/cluster_up.sh
# Démarrage des services locaux d'une VM du cluster 3 machines.
# Usage : ./scripts/cluster_up.sh <a|b|c>   (a=VM1, b=VM2, c=VM3)

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROLE="${1:-}"

usage() {
    echo "Usage: $0 <a|b|c>"
    echo "  a / vm1   -> deploy/vm1 : mongo1 + spark-master"
    echo "  b / vm2   -> deploy/vm2 : mongo2 + spark-worker1"
    echo "  c / vm3   -> deploy/vm3 : mongo3 + spark-worker2"
}

case "$ROLE" in
    a|vm1)
        COMPOSE_DIR="deploy/vm1"
        SERVICES=(mongo1 spark-master)
        ;;
    b|vm2)
        COMPOSE_DIR="deploy/vm2"
        SERVICES=(mongo2 spark-worker1)
        ;;
    c|vm3)
        COMPOSE_DIR="deploy/vm3"
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
