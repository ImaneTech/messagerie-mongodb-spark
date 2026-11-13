#!/usr/bin/env bash
# scripts/cluster_down.sh
# Arrêt des services locaux d'une VM du cluster 3 machines.
# Usage : ./scripts/cluster_down.sh <a|b|c>

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROLE="${1:-}"

usage() {
    echo "Usage: $0 <a|b|c>"
    echo "  a / vm1   -> deploy/vm1 : spark-master puis mongo1"
    echo "  b / vm2   -> deploy/vm2 : spark-worker1 puis mongo2"
    echo "  c / vm3   -> deploy/vm3 : spark-worker2 puis mongo3"
}

case "$ROLE" in
    a|vm1)
        COMPOSE_DIR="deploy/vm1"
        SERVICES=(spark-master mongo1)
        ;;
    b|vm2)
        COMPOSE_DIR="deploy/vm2"
        SERVICES=(spark-worker1 mongo2)
        ;;
    c|vm3)
        COMPOSE_DIR="deploy/vm3"
        SERVICES=(spark-worker2 mongo3)
        ;;
    *)
        usage
        exit 1
        ;;
esac

cd "$ROOT_DIR"
echo "=== Arrêt des services ${SERVICES[*]} sur ${COMPOSE_DIR} ==="
docker compose -f "$COMPOSE_DIR/docker-compose.yml" stop "${SERVICES[@]}"
echo "[OK] Services arrêtés sur ${COMPOSE_DIR}."
