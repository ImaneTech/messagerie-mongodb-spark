#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "=============================================================="
echo "       DÉMONSTRATION COMPLÈTE MONGODB + SPARK"
echo "=============================================================="

echo
echo "[1/7] Vérification de Docker et des conteneurs sur VM1"
if ! command -v docker >/dev/null 2>&1; then
    echo "[ERREUR] Docker n'est pas installé."
    exit 1
fi
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

echo
echo "[2/7] Vérification du Replica Set MongoDB et du cluster Spark"
python3 scripts/check_cluster.py

echo
echo "[3/7] Vérification directe de l'état des membres du Replica Set"
if docker ps --format '{{.Names}}' | grep -qx 'mongo1'; then
    docker exec mongo1 mongosh \
        "mongodb://192.168.0.100:27017,192.168.0.101:27017,192.168.0.102:27017/chatdb?replicaSet=rs0" \
        --quiet \
        --eval 'printjson(rs.status().members.map(m => ({name:m.name, state:m.stateStr, health:m.health})))'
else
    echo "[ERREUR] Le conteneur mongo1 n'est pas démarré."
    exit 1
fi

echo
echo "[4/7] Vérification de la cohérence des données"
python3 data_generator/check_data.py

echo
echo "[5/7] Exécution du benchmark comparatif final (Natif vs PySpark)"
export COMPARISON_CUTOFF="$(date -u -d '31 days ago' '+%Y-%m-%dT%H:%M:%S.000Z')"
echo "Cutoff appliqué : $COMPARISON_CUTOFF"
python3 benchmarks/run_all.py --with-spark
python3 benchmarks/merge_native_spark.py

echo
echo "[6/7] Vérification des fichiers de résultats CSV"
for file in \
    benchmarks/results/native_vs_spark.csv \
    benchmarks/results/index_test.csv \
    benchmarks/results/consistency_test.csv \
    benchmarks/results/failover_test.csv
do
    if [ -f "$file" ]; then
        echo "OK      $file"
    else
        echo "MISSING $file"
        exit 1
    fi
done

echo
echo "[7/7] Démarrage du dashboard Streamlit"
if command -v curl >/dev/null 2>&1 && curl -fsS http://127.0.0.1:8501/_stcore/health >/dev/null 2>&1; then
    echo "OK      Streamlit est déjà actif sur le port 8501"
else
    nohup python3 -m streamlit run dashboard/app.py \
        --server.address 0.0.0.0 \
        --server.port 8501 \
        > /tmp/messagerie-streamlit.log 2>&1 &
    sleep 3
    echo "Streamlit démarré en arrière-plan."
fi

echo
echo "=============================================================="
echo "       DÉMONSTRATION PRÊTE ET VALIDÉE AVEC SUCCÈS !"
echo "=============================================================="
echo "-> Tableau comparatif affiché ci-dessus"
echo "-> Ouvrir le dashboard : http://192.168.0.100:8501"
echo "-> Interface Spark Master : http://192.168.0.100:8080"
echo "=============================================================="