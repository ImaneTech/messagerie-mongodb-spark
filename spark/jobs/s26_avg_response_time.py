"""Calcul du temps de réponse moyen en conversation privée avec fonction de fenêtrage (lag)."""

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from pyspark.sql import functions as F
from pyspark.sql.window import Window

from spark.spark_session import get_spark_session

MAX_GAP_SECONDS = 3600

spark = get_spark_session("S26_AvgResponseTime")

# Lire conversations privées (format "mongo" pour le connecteur 3.0.1)
convs_df = spark.read.format("mongo").option("collection", "conversations").load()
private_ids = (
    convs_df.filter(F.col("type") == "private").select("_id").withColumnRenamed("_id", "conv_id")
)

# Lire messages (format "mongo" pour le connecteur 3.0.1)
msgs_df = spark.read.format("mongo").option("collection", "messages").load()
msgs_df = msgs_df.select("_id", "conversation_id", "sender_id", "ts")

# Joindre pour ne garder que les messages de conversations privées
msgs_private = msgs_df.join(private_ids, msgs_df.conversation_id == private_ids.conv_id, "inner")

# Window partitionBy conversation_id orderBy ts
w = Window.partitionBy("conversation_id").orderBy("ts")

# Lag de sender_id et ts
msgs_w = msgs_private.withColumn("prev_sender", F.lag("sender_id").over(w)).withColumn(
    "prev_ts", F.lag("ts").over(w)
)

# Une réponse valide : sender diffère du précédent ET 0 < gap <= MAX_GAP_SECONDS
# gap=0 (messages simultanés) = pas une réponse mesurable
responses = (
    msgs_w.filter(F.col("prev_sender").isNotNull() & (F.col("sender_id") != F.col("prev_sender")))
    .withColumn(
        "delta_sec",
        (F.unix_timestamp(F.col("ts")) - F.unix_timestamp(F.col("prev_ts"))).cast("double"),
    )
    .filter((F.col("delta_sec") > 0.0) & (F.col("delta_sec") <= MAX_GAP_SECONDS))
)

# --- 3 runs pour le timing ---
run_times = []
global_avg = None
global_median = None
response_count = None
per_conv = None
dist = None

for i in range(3):
    t0 = time.time()
    # Calculs globaux avec distribution complète
    agg_row = responses.agg(
        F.count("*").alias("nb"),
        F.avg("delta_sec").alias("avg_sec"),
        F.min("delta_sec").alias("min_sec"),
        F.max("delta_sec").alias("max_sec"),
        F.percentile_approx("delta_sec", 0.25).alias("p25_sec"),
        F.percentile_approx("delta_sec", 0.50).alias("p50_sec"),
        F.percentile_approx("delta_sec", 0.75).alias("p75_sec"),
        F.percentile_approx("delta_sec", 0.95).alias("p95_sec"),
    ).collect()[0]
    run_times.append((time.time() - t0) * 1000)
    if i == 0:
        global_avg = agg_row["avg_sec"]
        global_median = agg_row["p50_sec"]
        response_count = agg_row["nb"]
        dist = agg_row

avg_ms = sum(run_times) / len(run_times)
print(f"MAX_GAP_SECONDS={MAX_GAP_SECONDS}")
print(f"REPONSES_COMPTEES={response_count}")
print("DISTRIBUTION (secondes, gap>0 uniquement):")
print(f"  min    = {dist['min_sec']:.3f}")
print(f"  p25    = {dist['p25_sec']:.3f}")
print(f"  median = {dist['p50_sec']:.3f}")
print(f"  p75    = {dist['p75_sec']:.3f}")
print(f"  p95    = {dist['p95_sec']:.3f}")
print(f"  max    = {dist['max_sec']:.3f}")
print(f"  mean   = {dist['avg_sec']:.3f}")
print(f"MOYENNE_SEC={global_avg:.3f}" if global_avg is not None else "MOYENNE_SEC=None")
print(f"MEDIANE_SEC={global_median:.3f}" if global_median is not None else "MEDIANE_SEC=None")
print(f"DUREE_MS={avg_ms:.0f}")

# Moyenne par conversation
per_conv = responses.groupBy("conversation_id").agg(
    F.avg("delta_sec").alias("avg_sec"), F.count("*").alias("response_count")
)

print("Top 20 conversations les plus RAPIDES (avg_sec ASC) :")
per_conv.orderBy(F.col("avg_sec").asc()).limit(20).show()

# Écriture dans stats_s26 (format "mongo" pour le connecteur 3.0.1)
per_conv.write.format("mongo").option("collection", "stats_s26").mode("overwrite").save()

rows = per_conv.count()
print(f"Lignes écrites dans stats_s26 : {rows}")

spark.stop()