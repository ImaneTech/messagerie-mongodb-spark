import os
import time

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

MONGO_URI = os.environ["MONGO_URI"]

spark = (
    SparkSession.builder.appName("S29_ReportRateBySender")
    .config("spark.mongodb.read.connection.uri", MONGO_URI)
    .config("spark.mongodb.write.connection.uri", MONGO_URI)
    .config("spark.mongodb.read.database", "chatdb")
    .config("spark.mongodb.write.database", "chatdb")
    .getOrCreate()
)

# Lire messages
msgs_df = spark.read.format("mongodb").option("collection", "messages").load()
msgs_df = msgs_df.select(F.col("_id").alias("message_id"), "sender_id")

# Lire reports
reports_df = spark.read.format("mongodb").option("collection", "reports").load()
reports_df = reports_df.select("message_id").withColumnRenamed("message_id", "rep_message_id")

# Count messages envoyés par sender
sent_count = msgs_df.groupBy("sender_id").agg(F.count("message_id").alias("sent_count"))

# Join messages avec reports pour trouver les messages signalés
reported_msgs = msgs_df.join(reports_df, msgs_df.message_id == reports_df.rep_message_id, "inner")
reported_count = reported_msgs.groupBy("sender_id").agg(
    F.count("message_id").alias("reported_count")
)

# Join sent_count avec reported_count
result = (
    sent_count.join(reported_count, "sender_id", "left")
    .fillna(0, subset=["reported_count"])
    .withColumn("report_rate", F.col("reported_count") / F.col("sent_count"))
    .filter(F.col("sent_count") >= 20)
    .orderBy(F.col("report_rate").desc())
    .limit(20)
)

result.show()

start_write = time.time()
result.write.format("mongodb").option("collection", "stats_s29").mode("overwrite").save()
duration_ms = (time.time() - start_write) * 1000
print(f"DUREE_MS={duration_ms:.0f}")

rows = result.count()
print(f"Lignes écrites dans stats_s29 : {rows}")

spark.stop()
