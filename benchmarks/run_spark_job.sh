#!/bin/bash
# run_spark_job.sh — Lance un job Spark dans le conteneur spark-master
#
# Utilisation :
#   ./benchmarks/run_spark_job.sh s26_avg_response_time
#
# Le script lit automatiquement MONGO_URI depuis config.settings si non définie

set -e

JOB_NAME="$1"

if [ -z "$JOB_NAME" ]; then
    echo "Erreur: Nom du job requis"
    echo "Usage: $0 <job_name>"
    echo "Exemple: $0 s26_avg_response_time"
    exit 1
fi

# Lire MONGO_URI depuis config.settings si non définie
if [ -z "$MONGO_URI" ]; then
    MONGO_URI=$(python3 -c "import sys; sys.path.insert(0, '..'); from config.settings import MONGO_URI; print(MONGO_URI)")
    if [ -z "$MONGO_URI" ]; then
        echo "Erreur: Impossible de lire MONGO_URI depuis config.settings"
        exit 1
    fi
fi

echo "==> Job: $JOB_NAME"
echo "==> MONGO_URI: $MONGO_URI"
echo ""

# Exécuter le job Spark dans le conteneur spark-master
docker exec -e MONGO_URI="$MONGO_URI" spark-master \
    /opt/spark/bin/spark-submit \
    --master spark://spark-master:7077 \
    --packages org.mongodb.spark:mongo-spark-connector_2.12:10.3.0 \
    --conf spark.jars.ivy=/tmp/.ivy2 \
    --conf spark.driver.host=spark-master \
    --conf spark.driver.bindAddress=0.0.0.0 \
    --executor-memory 1g --total-executor-cores 4 \
    /opt/spark-jobs/jobs/"$JOB_NAME".py
