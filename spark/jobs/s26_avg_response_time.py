import os
import time
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

MAX_GAP_SECONDS = 3600

MONGO_URI = os.environ["MONGO_URI"]

spark = SparkSession.builder \
    .appName("S26_AvgResponseTime") \
    .config("spark.mongodb.read.connection.uri", MONGO_URI) \
    .config("spark.mongodb.write.connection.uri", MONGO_URI) \
    .config("spark.mongodb.read.database", "chatdb") \
    .config("spark.mongodb.write.database", "chatdb") \
    .getOrCreate()

# Lire conversations privées
convs_df = spark.read.format("mongodb").option("collection", "conversations").load()
private_ids = convs_df.filter(F.col("type") == "private").select("_id").withColumnRenamed("_id", "conv_id")

# Lire messages
msgs_df = spark.read.format("mongodb").option("collection", "messages").load()
msgs_df = msgs_df.select("_id", "conversation_id", "sender_id", "ts")

# Joindre pour ne garder que les messages de conversations privées
msgs_private = msgs_df.join(private_ids, msgs_df.conversation_id == private_ids.conv_id, "inner")

# Window partitionBy conversation_id orderBy ts
w = Window.partitionBy("conversation_id").orderBy("ts")

# Lag de sender_id et ts
msgs_w = msgs_private.withColumn("prev_sender", F.lag("sender_id").over(w)) \
                     .withColumn("prev_ts", F.lag("ts").over(w))

# Une réponse valide : sender diffère du précédent ET gap <= MAX_GAP_SECONDS
responses = msgs_w.filter(
    F.col("prev_sender").isNotNull() &
    (F.col("sender_id") != F.col("prev_sender"))
).withColumn(
    "delta_sec",
    (F.col("ts").cast("long") - F.col("prev_ts").cast("long"))
).filter(F.col("delta_sec") <= MAX_GAP_SECONDS)

# --- 3 runs pour le timing ---
run_times = []
global_avg = None
global_median = None
response_count = None
per_conv = None

for i in range(3):
    t0 = time.time()
    # Calculs globaux
    agg_row = responses.agg(
        F.count("*").alias("nb"),
        F.avg("delta_sec").alias("avg_sec"),
        F.percentile_approx("delta_sec", 0.5).alias("median_sec")
    ).collect()[0]
    run_times.append((time.time() - t0) * 1000)
    if i == 0:
        global_avg = agg_row["avg_sec"]
        global_median = agg_row["median_sec"]
        response_count = agg_row["nb"]

avg_ms = sum(run_times) / len(run_times)
print(f"MAX_GAP_SECONDS={MAX_GAP_SECONDS}")
print(f"REPONSES_COMPTEES={response_count}")
print(f"MOYENNE_SEC={global_avg:.2f}" if global_avg is not None else "MOYENNE_SEC=None")
print(f"MEDIANE_SEC={global_median}")
print(f"DUREE_MS={avg_ms:.0f}")

# Moyenne par conversation
per_conv = responses.groupBy("conversation_id").agg(
    F.avg("delta_sec").alias("avg_sec"),
    F.count("*").alias("response_count")
)

print("Top 20 conversations les plus RAPIDES (avg_sec ASC) :")
per_conv.orderBy(F.col("avg_sec").asc()).limit(20).show()

# Écriture dans stats_s26
per_conv.write.format("mongodb").option("collection", "stats_s26").mode("overwrite").save()

rows = per_conv.count()
print(f"Lignes écrites dans stats_s26 : {rows}")

spark.stop()
