# run_spark_job.ps1 — Lance un job Spark dans le conteneur spark-master
#
# Utilisation :
#   1. Définir l'URI MongoDB dans la variable d'environnement :
#        $env:MONGO_URI = (python -c "import sys; sys.path.insert(0, 'c:\Users\EMMA\messagerie-mongodb-spark'); from config.settings import MONGO_URI; print(MONGO_URI)")
#   2. Appeler ce script avec le nom du job (sans .py) :
#        .\benchmarks\run_spark_job.ps1 s26_avg_response_time
#
# Exemple complet depuis la racine du projet :
#   $env:MONGO_URI = (python -c "import sys; sys.path.insert(0, 'c:\Users\EMMA\messagerie-mongodb-spark'); from config.settings import MONGO_URI; print(MONGO_URI)")
#   .\benchmarks\run_spark_job.ps1 s26_avg_response_time

param(
    [Parameter(Mandatory=$true)]
    [string]$JobName
)

if (-not $env:MONGO_URI) {
    $projectRoot = (Resolve-Path "$PSScriptRoot\..").Path
    $env:MONGO_URI = python -c "import sys; sys.path.insert(0, r'$projectRoot'); from config.settings import MONGO_URI; print(MONGO_URI)"
    if (-not $env:MONGO_URI) {
        Write-Error "Impossible de lire MONGO_URI depuis config.settings"
        exit 1
    }
}

$cmd = "docker exec -e MONGO_URI=`"$env:MONGO_URI`" spark-master /opt/spark/bin/spark-submit " +
       "--master spark://spark-master:7077 " +
       "--packages org.mongodb.spark:mongo-spark-connector_2.12:10.3.0 " +
       "--conf spark.jars.ivy=/tmp/.ivy2 " +
       "--conf spark.driver.host=spark-master " +
       "--conf spark.driver.bindAddress=0.0.0.0 " +
       "--executor-memory 1g --total-executor-cores 4 " +
       "/opt/spark-jobs/jobs/$JobName.py"

Write-Host "==> Commande executee :"
Write-Host $cmd
Write-Host ""

Invoke-Expression $cmd
