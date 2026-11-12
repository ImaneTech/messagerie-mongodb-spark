# run_spark_job.ps1 — Lance un job Spark dans le conteneur spark-master (VM1)
#
# Usage :
#   .\benchmarks\run_spark_job.ps1 s26_avg_response_time
#
# Le script lit MONGO_URI et IP_A depuis config.settings automatiquement.

param(
    [Parameter(Mandatory=$true)]
    [string]$JobName
)

$ErrorActionPreference = "Stop"

if ($JobName -notmatch '^[A-Za-z0-9_-]+$') {
    Write-Error "Nom de job invalide (caractères autorisés : lettres, chiffres, _ et -)"
    exit 1
}

$projectRoot = (Resolve-Path "$PSScriptRoot\..").Path
$configLines = @(python -c "import sys; sys.path.insert(0, r'$projectRoot'); from config.settings import IP_A, MONGO_URI; print(IP_A); print(MONGO_URI)")

if ($configLines.Count -lt 2) {
    Write-Error "Impossible de lire la configuration depuis config.settings"
    exit 1
}

$sparkHost = $configLines[0].Trim()
$env:MONGO_URI = $configLines[1].Trim()

Write-Host "==> Job: $JobName"
Write-Host "==> Spark master: ${sparkHost}:7077"
Write-Host "==> MONGO_URI: $env:MONGO_URI"
Write-Host ""

# À exécuter sur VM1, là où le conteneur spark-master est hébergé.
if ($JobName -match '^cmp_a(16|17|18)$') {
    $jobPath = "/workspace/spark/comparaison/$JobName.py"
} else {
    $jobPath = "/workspace/spark/jobs/$JobName.py"
}

$cmdArgs = @(
    "exec",
    "-e", "MONGO_URI=$env:MONGO_URI",
    "spark-master",
    "/opt/spark/bin/spark-submit",
    "--master", "spark://${sparkHost}:7077",
    "--packages", "org.mongodb.spark:mongo-spark-connector_2.12:10.3.0",
    "--conf", "spark.jars.ivy=/tmp/.ivy2",
    "--conf", "spark.driver.host=$sparkHost",
    "--conf", "spark.driver.bindAddress=0.0.0.0",
    "--executor-memory", "1g",
    "--total-executor-cores", "4",
    $jobPath
)

& docker @cmdArgs
