# scripts/restart_after_powercut.ps1
# Procédure de reprise après coupure de courant (Guide §4.8)
# Ordre strict : Nœuds de données d'abord -> Attente quorum sain -> Spark Master -> Workers

Write-Host "=================================================================" -ForegroundColor Yellow
Write-Host "PROCÉDURE DE REPRISE APRÈS COUPURE ÉLECTRIQUE (Guide §4.8)" -ForegroundColor Yellow
Write-Host "=================================================================" -ForegroundColor Yellow

Write-Host "Étape 1 : Démarrage des conteneurs de stockage MongoDB..." -ForegroundColor Cyan
docker start mongo1 mongo2
# Sur Machine B : docker start mongo3

Write-Host "Étape 2 : Attente de stabilisation du quorum Replica Set (15s)..."
Start-Sleep -Seconds 15

Write-Host "Étape 3 : Vérification de la santé du Replica Set..." -ForegroundColor Cyan
docker exec mongo1 mongosh --quiet --eval "rs.status().members.map(m => m.name + ': ' + m.stateStr)"

Write-Host "Étape 4 : Démarrage de Spark Master..." -ForegroundColor Cyan
docker start spark-master
Start-Sleep -Seconds 5

Write-Host "Étape 5 : Démarrage des Spark Workers..." -ForegroundColor Cyan
docker start spark-worker1 spark-worker2

Write-Host "Étape 6 : Contrôle final..." -ForegroundColor Cyan
python scripts\check_cluster.py

