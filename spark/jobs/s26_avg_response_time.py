import os
import time
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

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

# Une réponse = message dont sender diffère du précédent
responses = msgs_w.filter(
    F.col("prev_sender").isNotNull() &
    (F.col("sender_id") != F.col("prev_sender"))
)

# Delta en secondes
responses = responses.withColumn(
    "delta_sec",
    (F.col("ts").cast("long") - F.col("prev_ts").cast("long"))
)

# Moyenne globale
global_avg = responses.agg(F.avg("delta_sec").alias("global_avg_sec")).collect()[0]["global_avg_sec"]
print(f"Moyenne globale de réponse : {global_avg:.2f} secondes")

# Moyenne par conversation
per_conv = responses.groupBy("conversation_id").agg(F.avg("delta_sec").alias("avg_sec"))

print("Top 20 conversations les plus LENTES :")
per_conv.orderBy(F.col("avg_sec").desc()).limit(20).show()

print("Top 20 conversations les plus RAPIDES :")
per_conv.orderBy(F.col("avg_sec").asc()).limit(20).show()

start_write = time.time()
per_conv.write.format("mongodb").option("collection", "stats_s26").mode("overwrite").save()
duration_ms = (time.time() - start_write) * 1000
print(f"DUREE_MS={duration_ms:.0f}")

rows = per_conv.count()
print(f"Lignes écrites dans stats_s26 : {rows}")

spark.stop()
