# scripts/cluster_up.ps1
# Démarrage des services locaux d'une VM du cluster 3 machines.
# Usage : .\scripts\cluster_up.ps1 -Role <a|b|c>

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
    $services = @("mongo1", "spark-master")
} elseif ($normalizedRole -in @("b", "vm2", "machine-b")) {
    $composeDir = "machine-b"
    $services = @("mongo2", "spark-worker1")
} elseif ($normalizedRole -in @("c", "vm3", "machine-c")) {
    $composeDir = "machine-c"
    $services = @("mongo3", "spark-worker2")
} else {
    Write-Error "Usage: $PSCommandPath -Role <a|b|c>"
    exit 1
}

Write-Host "=== Démarrage des services $($services -join ', ') sur $composeDir ===" -ForegroundColor Cyan
docker compose -f "$composeDir/docker-compose.yml" up -d @services

Write-Host "[OK] Services démarrés. Après le démarrage des 3 VMs :" -ForegroundColor Green
Write-Host "  1. Sur VM1 : python scripts/init_replica_set.py"
Write-Host "  2. Partout : python scripts/check_cluster.py"
