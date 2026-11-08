"""Session PySpark centralisée pour les jobs analytiques."""

import os
import tempfile

from pyspark.sql import SparkSession

from config.settings import MONGO_DB, MONGO_URI


def _ivy_home():
    """Retourne un chemin absolu pour le cache Ivy, compatible Windows et Linux."""
    return os.environ.get("SPARK_IVY_HOME") or os.path.join(tempfile.gettempdir(), ".ivy2")


def get_spark_session(app_name="MessagingAnalytics"):
    """Crée et retourne une SparkSession configurée avec le connecteur MongoDB."""
    spark = (
        SparkSession.builder.appName(app_name)
        .config("spark.jars.packages", "org.mongodb.spark:mongo-spark-connector_2.12:10.3.0")
        .config("spark.jars.ivy", _ivy_home())
        .config("spark.mongodb.read.connection.uri", MONGO_URI)
        .config("spark.mongodb.read.database", MONGO_DB)
        .config("spark.mongodb.write.connection.uri", MONGO_URI)
        .config("spark.mongodb.write.database", MONGO_DB)
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    return spark
