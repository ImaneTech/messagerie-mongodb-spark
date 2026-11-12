"""Détection de campagnes de spam via fenêtrage temporel glissant (sliding window)."""

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

MAX_GAP_SECONDS = 3600
HOSTS = "192.168.0.100:27017,192.168.0.101:27017,192.168.0.102:27017"
URI_MSGS = f"mongodb://{HOSTS}/chatdb.messages?replicaSet=rs0"
URI_STATS = f"mongodb://{HOSTS}/chatdb.stats_s28?replicaSet=rs0"

spark = (
    SparkSession.builder
    .appName("S28_SpamDetection")
    .config("spark.mongodb.input.uri", URI_MSGS)
    .config("spark.mongodb.output.uri", URI_STATS)
    .getOrCreate()
)
spark.sparkContext.setLogLevel("ERROR")

# Lire messages de type text (format "mongo" et URI explicite)
msgs_df = spark.read.format("mongo").option("uri", URI_MSGS).load()
msgs_df = msgs_df.filter(F.col("type") == "text").select(
    "sender_id", "content", "conversation_id", "ts"
)

# Fenêtre glissante : 1 heure, pas de 10 minutes (évite les coupures aux bords)
windowed = msgs_df.groupBy(
    "sender_id", "content", F.window(F.col("ts"), "1 hour", "10 minutes")
).agg(F.countDistinct("conversation_id").alias("nb_conversations"))

# Filtrer les spammeurs potentiels (> 20 conversations distinctes dans la fenêtre)
spam_raw = windowed.filter(F.col("nb_conversations") > 20)

# Dédupliquer par (sender_id, content) : garder la fenêtre avec le max de nb_conversations
dedup_window = Window.partitionBy("sender_id", "content").orderBy(F.col("nb_conversations").desc())
spam = (
    spam_raw.withColumn("rn", F.row_number().over(dedup_window)).filter(F.col("rn") == 1).drop("rn")
)

spam.show(20, truncate=50)

# --- Timing autour du collect ---
run_times = []
spark_rows = None
for _ in range(3):
    t0 = time.time()
    spark_rows = spam.collect()
    run_times.append((time.time() - t0) * 1000)
avg_ms = sum(run_times) / len(run_times)

print(f"DUREE_MS={avg_ms:.0f}")

# Afficher les sender_ids trouvés par Spark
spark_sender_ids = sorted(set(str(r["sender_id"]) for r in spark_rows))
print(f"SPARK_SENDER_IDS={spark_sender_ids}")
print(f"SPARK_ROWS={len(spark_rows)}")

# Écriture dans stats_s28 (avec URI d'écriture explicite)
spam.write.format("mongo").option("uri", URI_STATS).mode("overwrite").save()
print(f"Lignes écrites dans stats_s28 (spammeurs dédupliqués) : {len(spark_rows)}")

spark.stop()