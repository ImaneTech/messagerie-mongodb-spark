import os
import time
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

MONGO_URI = os.environ["MONGO_URI"]

spark = SparkSession.builder \
    .appName("S28_SpamDetection") \
    .config("spark.mongodb.read.connection.uri", MONGO_URI) \
    .config("spark.mongodb.write.connection.uri", MONGO_URI) \
    .config("spark.mongodb.read.database", "chatdb") \
    .config("spark.mongodb.write.database", "chatdb") \
    .getOrCreate()

# Lire messages de type text
msgs_df = spark.read.format("mongodb").option("collection", "messages").load()
msgs_df = msgs_df.filter(F.col("type") == "text") \
                 .select("sender_id", "content", "conversation_id", "ts")

# groupBy sender_id, content, window(ts, "1 hour"), countDistinct(conversation_id) > 20
windowed = msgs_df.groupBy(
    "sender_id",
    "content",
    F.window(F.col("ts"), "1 hour")
).agg(F.countDistinct("conversation_id").alias("nb_conversations"))

spam = windowed.filter(F.col("nb_conversations") > 20)

spam.show(20, truncate=50)

start_write = time.time()
spam.write.format("mongodb").option("collection", "stats_s28").mode("overwrite").save()
duration_ms = (time.time() - start_write) * 1000
print(f"DUREE_MS={duration_ms:.0f}")

rows = spam.count()
print(f"Lignes écrites dans stats_s28 (spammeurs) : {rows}")

spark.stop()
