# scripts/restart_after_powercut.ps1
# Reprise locale après coupure : données MongoDB d'abord, puis Spark.
# Usage : .\scripts\restart_after_powercut.ps1 -Role <a|b|c>

param(
    [Parameter(Mandatory=$true)]
    [string]$Role
)

$ErrorActionPreference = "Stop"
$RootDir = Resolve-Path "$PSScriptRoot\.."
Set-Location $RootDir
$normalizedRole = $Role.ToLower()

if ($normalizedRole -in @("a", "vm1", "machine-a")) {
    $composeDir = "machine-a"
    $mongoService = "mongo1"
    $sparkService = "spark-master"
} elseif ($normalizedRole -in @("b", "vm2", "machine-b")) {
    $composeDir = "machine-b"
    $mongoService = "mongo2"
    $sparkService = "spark-worker1"
} elseif ($normalizedRole -in @("c", "vm3", "machine-c")) {
    $composeDir = "machine-c"
    $mongoService = "mongo3"
    $sparkService = "spark-worker2"
} else {
    Write-Error "Usage: $PSCommandPath -Role <a|b|c>"
    exit 1
}

$composeFile = "$composeDir/docker-compose.yml"

Write-Host "=================================================================" -ForegroundColor Yellow
Write-Host "REPRISE APRÈS COUPURE — $composeDir" -ForegroundColor Yellow
Write-Host "=================================================================" -ForegroundColor Yellow

Write-Host "Étape 1 : démarrage du nœud MongoDB local ($mongoService)..." -ForegroundColor Cyan
docker compose -f $composeFile up -d $mongoService

Write-Host "Étape 2 : attente de stabilisation (15s)..." -ForegroundColor Cyan
Start-Sleep -Seconds 15

if ($composeDir -eq "machine-a") {
    Write-Host "Étape 3 : vérification du Replica Set depuis mongo1..." -ForegroundColor Cyan
    docker exec mongo1 mongosh --quiet --eval "rs.status().members.map(m => m.name + ': ' + m.stateStr)"
}

Write-Host "Étape 4 : démarrage du service Spark local ($sparkService)..." -ForegroundColor Cyan
docker compose -f $composeFile up -d $sparkService

Write-Host "[OK] $composeDir redémarré. Lancez scripts/check_cluster.py après coup sur les 3 VMs." -ForegroundColor Green
