# scripts/cluster_down.ps1
# Arrêt des services locaux d'une VM du cluster 3 machines.
# Usage : .\scripts\cluster_down.ps1 -Role <a|b|c>

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
    $services = @("spark-master", "mongo1")
} elseif ($normalizedRole -in @("b", "vm2", "machine-b")) {
    $composeDir = "machine-b"
    $services = @("spark-worker1", "mongo2")
} elseif ($normalizedRole -in @("c", "vm3", "machine-c")) {
    $composeDir = "machine-c"
    $services = @("spark-worker2", "mongo3")
} else {
    Write-Error "Usage: $PSCommandPath -Role <a|b|c>"
    exit 1
}

Write-Host "=== Arrêt des services $($services -join ', ') sur $composeDir ===" -ForegroundColor Cyan
docker compose -f "$composeDir/docker-compose.yml" stop @services
Write-Host "[OK] Services arrêtés sur $composeDir." -ForegroundColor Green
