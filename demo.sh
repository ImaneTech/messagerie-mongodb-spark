#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "=============================================================="
echo "      DÉMONSTRATION COMPLÈTE MONGODB + SPARK (TOUTES COMMANDES)"
echo "=============================================================="

echo
echo "[1/9] Vérification de Docker et des conteneurs"
if ! command -v docker >/dev/null 2>&1; then
    echo "[ERREUR] Docker n'est pas installé."
    exit 1
fi
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

echo
echo "[2/9] Vérification du Replica Set MongoDB et du cluster Spark"
python3 scripts/check_cluster.py

echo
echo "[3/9] Génération et chargement complet des données (si nécessaire)"
python3 -m schema.create_indexes
python3 data_generator/generate_data.py
python3 data_generator/load_data.py
python3 data_generator/check_data.py

echo
echo "[4/9] Exécution des benchmarks natifs (T1 à T15 et A16 à A25)"
python3 benchmarks/run_all.py

echo
echo "[5/9] Exécution de la comparaison MongoDB natif vs PySpark (A16 à A18)"
export COMPARISON_CUTOFF="$(date -u -d '31 days ago' '+%Y-%m-%dT%H:%M:%S.000Z')"
python3 benchmarks/run_all.py --with-spark
python3 benchmarks/merge_native_spark.py

echo
echo "[6/9] Exécution du job Spark S28 (Détection de spam)"
python3 spark/jobs/s28_spam_detection.py

echo
echo "[7/9] Exécution des tests de performance et cohérence"
python3 benchmarks/index_test.py
python3 benchmarks/consistency_test.py

echo
echo "[8/9] Test de tolérance aux pannes (Failover du primaire)"
python3 scripts/failover_test.py

echo
echo "[9/9] Démarrage du dashboard Streamlit"
if command -v curl >/dev/null 2>&1 && curl -fsS http://127.0.0.1:8501/_stcore/health >/dev/null 2>&1; then
    echo "OK      Streamlit est déjà actif sur le port 8501"
else
    nohup python3 -m streamlit run dashboard/app.py \
        --server.address 0.0.0.0 \
        --server.port 8501 \
        > /tmp/messagerie-streamlit.log 2>&1 &
    echo "Streamlit démarré en arrière-plan."
    sleep 3
fi

echo
echo "=============================================================="
echo "       TOUTES LES COMMANDES ONT ÉTÉ EXÉCUTÉES AVEC SUCCÈS !"
echo "=============================================================="
echo "Ouvrir le dashboard : http://192.168.0.100:8501"
echo "Interface Spark Master : http://192.168.0.100:8080"