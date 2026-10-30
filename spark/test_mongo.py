import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pyspark.sql import SparkSession
from config.settings import MONGO_URI, MONGO_DB

spark = (
    SparkSession.builder.appName("test_mongo")
    .config("spark.jars.packages", "org.mongodb.spark:mongo-spark-connector_2.12:10.3.0")
    .config("spark.mongodb.read.connection.uri", MONGO_URI)
    .config("spark.mongodb.write.connection.uri", MONGO_URI)
    .getOrCreate()
)
spark.sparkContext.setLogLevel("ERROR")

df = (
    spark.read.format("mongodb")
    .option("database", MONGO_DB)
    .option("collection", "ping")
    .load()
)
df.show()
spark.stop()
