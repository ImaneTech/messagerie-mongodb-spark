# scripts/cluster_down.ps1
# Arrêt ordonné et propre de l'infrastructure (PowerShell)

Write-Host "=== 1. Arrêt des Workers et Master Spark ===" -ForegroundColor Cyan
Set-Location "$PSScriptRoot\..\machine-a"
docker stop spark-worker2 spark-worker1 spark-master

Write-Host "=== 2. Arrêt propre des nœuds MongoDB ===" -ForegroundColor Cyan
docker stop mongo2 mongo1

Write-Host "[OK] Conteneurs de la machine A arrêtés proprement." -ForegroundColor Green
Set-Location "$PSScriptRoot\.."
