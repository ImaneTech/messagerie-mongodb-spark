#!/bin/bash
# run_spark_job.sh — Lance un job Spark dans le conteneur spark-master (VM1)
#
# Utilisation :
#   ./benchmarks/run_spark_job.sh s26_avg_response_time
#
# Le script lit MONGO_URI et IP_A depuis config.settings si nécessaire.

set -euo pipefail

JOB_NAME="${1:-}"

if [ -z "$JOB_NAME" ]; then
    echo "Erreur: Nom du job requis"
    echo "Usage: $0 <job_name>"
    echo "Exemple: $0 s26_avg_response_time"
    exit 1
fi

if [[ ! "$JOB_NAME" =~ ^[A-Za-z0-9_-]+$ ]]; then
    echo "Erreur: Nom de job invalide (caractères autorisés : lettres, chiffres, _ et -)"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

CONFIG_OUTPUT="$(PROJECT_ROOT="$PROJECT_ROOT" python3 - <<'PY'
import os
import sys

sys.path.insert(0, os.environ["PROJECT_ROOT"])
from config.settings import IP_A, MONGO_URI

print(IP_A)
print(MONGO_URI)
PY
)"

SPARK_MASTER_HOST="$(printf '%s\n' "$CONFIG_OUTPUT" | sed -n '1p')"
MONGO_URI="$(printf '%s\n' "$CONFIG_OUTPUT" | sed -n '2p')"

if [ -z "$SPARK_MASTER_HOST" ] || [ -z "$MONGO_URI" ]; then
    echo "Erreur: Impossible de lire la configuration depuis config.settings"
    exit 1
fi

echo "==> Job: $JOB_NAME"
echo "==> Spark master: $SPARK_MASTER_HOST:7077"
echo "==> MONGO_URI: $MONGO_URI"
echo ""

# À exécuter sur VM1, là où le conteneur spark-master est hébergé.
docker exec -e MONGO_URI="$MONGO_URI" spark-master \
    /opt/spark/bin/spark-submit \
    --master "spark://$SPARK_MASTER_HOST:7077" \
    --packages org.mongodb.spark:mongo-spark-connector_2.12:10.3.0 \
    --conf spark.jars.ivy=/tmp/.ivy2 \
    --conf "spark.driver.host=$SPARK_MASTER_HOST" \
    --conf spark.driver.bindAddress=0.0.0.0 \
    --executor-memory 1g --total-executor-cores 4 \
    "/workspace/spark/jobs/${JOB_NAME}.py"
