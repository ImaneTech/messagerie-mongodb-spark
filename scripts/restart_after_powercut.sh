#!/usr/bin/env bash
# scripts/restart_after_powercut.sh
# Procédure de reprise après coupure de courant (Guide §4.8)
# Ordre strict : Nœuds de données d'abord -> Attente quorum sain -> Spark Master -> Workers

echo "================================================================="
echo "PROCÉDURE DE REPRISE APRÈS COUPURE ÉLECTRIQUE (Guide §4.8)"
echo "================================================================="

echo "Étape 1 : Démarrage des conteneurs de stockage MongoDB..."
docker start mongo1 mongo2 2>/dev/null
# Si exécuté sur Machine B : docker start mongo3

echo "Étape 2 : Attente de stabilisation du quorum Replica Set (15s)..."
sleep 15

echo "Étape 3 : Vérification de la santé du Replica Set..."
docker exec mongo1 mongosh --quiet --eval "rs.status().members.map(m => m.name + ': ' + m.stateStr)"

echo "Étape 4 : Démarrage de Spark Master..."
docker start spark-master 2>/dev/null
sleep 5

echo "Étape 5 : Démarrage des Spark Workers..."
docker start spark-worker1 spark-worker2 2>/dev/null
# Si worker 2 sur Machine B : docker start spark-worker2 sur machine B

echo "Étape 6 : Contrôle final..."
python3 scripts/check_cluster.py
