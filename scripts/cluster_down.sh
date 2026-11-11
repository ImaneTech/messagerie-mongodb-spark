#!/usr/bin/env bash
# scripts/cluster_down.sh
# Arrêt des services locaux d'une VM du cluster 3 machines.
# Usage : ./scripts/cluster_down.sh <a|b|c>

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROLE="${1:-}"

usage() {
    echo "Usage: $0 <a|b|c>"
    echo "  a / vm1   -> machine-a : spark-master puis mongo1"
    echo "  b / vm2   -> machine-b : spark-worker1 puis mongo2"
    echo "  c / vm3   -> machine-c : spark-worker2 puis mongo3"
}

case "$ROLE" in
    a|vm1|machine-a)
        COMPOSE_DIR="machine-a"
        SERVICES=(spark-master mongo1)
        ;;
    b|vm2|machine-b)
        COMPOSE_DIR="machine-b"
        SERVICES=(spark-worker1 mongo2)
        ;;
    c|vm3|machine-c)
        COMPOSE_DIR="machine-c"
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
