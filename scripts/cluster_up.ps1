# scripts/cluster_up.ps1
# Démarrage ordonné de l'infrastructure multi-machines (PowerShell)

Write-Host "=== 1. Démarrage des nœuds MongoDB (Machine A) ===" -ForegroundColor Cyan
Set-Location "$PSScriptRoot\..\machine-a"
docker compose up -d mongo1 mongo2

Write-Host "Attente de la disponibilité de mongo1 et mongo2 (5s)..."
Start-Sleep -Seconds 5

Write-Host "=== 2. Démarrage de Spark Master et Workers ===" -ForegroundColor Cyan
docker compose up -d spark-master spark-worker1 spark-worker2

Write-Host "=== 3. Vérification de l'état du cluster ===" -ForegroundColor Cyan
Set-Location "$PSScriptRoot\.."
python scripts\check_cluster.py

