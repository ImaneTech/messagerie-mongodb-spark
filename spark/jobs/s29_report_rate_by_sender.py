"""Calcul du ratio de messages signalés par utilisateur pour la modération."""

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from pyspark.sql import functions as F

from spark.spark_session import get_spark_session

spark = get_spark_session("S29_ReportRateBySender")

# 1. Chargement de la collection messages
msgs_df = spark.read.format("mongodb").option("collection", "messages").load()
msgs_df = msgs_df.select(F.col("_id").alias("message_id"), "sender_id")

# 2. Chargement de la collection reports
reports_df = spark.read.format("mongodb").option("collection", "reports").load()
reports_df = reports_df.select("message_id").withColumnRenamed("message_id", "rep_message_id")

# 3. Calcul du nombre de messages envoyés par émetteur
sent_count = msgs_df.groupBy("sender_id").agg(F.count("message_id").alias("sent_count"))

# 4. Jointure avec reports pour isoler les messages ayant fait l'objet d'un signalement
reported_msgs = msgs_df.join(reports_df, msgs_df.message_id == reports_df.rep_message_id, "inner")
reported_count = reported_msgs.groupBy("sender_id").agg(
    F.count("message_id").alias("reported_count")
)

# 5. Jointure globale, imputation des zéros, calcul du ratio et filtre seuil
result = (
    sent_count.join(reported_count, "sender_id", "left")
    .fillna(0, subset=["reported_count"])
    .withColumn("report_rate", F.col("reported_count") / F.col("sent_count"))
    .filter(F.col("sent_count") >= 20)
    .orderBy(F.col("report_rate").desc())
    .limit(20)
)

# 6. Mesure de l'action de calcul distribué (3 runs)
spark_times = []
for _ in range(3):
    t0 = time.time()
    res = result.collect()
    spark_times.append((time.time() - t0) * 1000)

avg_ms = sum(spark_times) / len(spark_times)
print(f"SPARK_AVG_MS={avg_ms:.0f}")
print(f"DUREE_MS={avg_ms:.0f}")
result.show()

# 7. Sauvegarde des résultats d'audit dans stats_s29
start_write = time.time()
result.write.format("mongodb").option("collection", "stats_s29").mode("overwrite").save()
duration_ms = (time.time() - start_write) * 1000
print(f"WRITE_MS={duration_ms:.0f}")

rows = result.count()
print(f"Lignes écrites dans stats_s29 : {rows}")

spark.stop()