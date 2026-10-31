import os
import time
from datetime import datetime, timedelta, timezone
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pymongo import MongoClient

# URI injectée par docker exec -e MONGO_URI
MONGO_URI = os.environ["MONGO_URI"]


def native_run(mongo_uri):
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    db = client["chatdb"]
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start_30d = now - timedelta(days=30)
    pipeline = [
        {"$match": {"ts": {"$gte": start_30d}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$ts"}},
            "total_messages": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    result = list(db.messages.aggregate(pipeline))
    client.close()
    return result


# --- 3 runs natifs ---
native_times = []
native_result = None
for _ in range(3):
    t0 = time.time()
    native_result = native_run(MONGO_URI)
    native_times.append((time.time() - t0) * 1000)
native_avg_ms = sum(native_times) / len(native_times)
print(f"NATIVE_AVG_MS={native_avg_ms:.0f}")
native_days = sorted([(r["_id"], r["total_messages"]) for r in native_result])

# --- Session Spark ---
t_session_start = time.time()
spark = SparkSession.builder \
    .appName("CMP_A16_MessagesPerDay") \
    .config("spark.mongodb.read.connection.uri", MONGO_URI) \
    .config("spark.mongodb.write.connection.uri", MONGO_URI) \
    .config("spark.mongodb.read.database", "chatdb") \
    .config("spark.mongodb.write.database", "chatdb") \
    .getOrCreate()
t_session_ms = (time.time() - t_session_start) * 1000
print(f"SPARK_SESSION_MS={t_session_ms:.0f}")

now = datetime.now(timezone.utc).replace(tzinfo=None)
start_30d = now - timedelta(days=30)

# --- 3 runs Spark ---
spark_times = []
spark_rows = None
result_df = None
for _ in range(3):
    t0 = time.time()
    msgs_df = spark.read.format("mongodb").option("collection", "messages").load()
    result_df = (
        msgs_df
        .filter(F.col("ts") >= F.lit(start_30d).cast("timestamp"))
        .groupBy(F.date_format("ts", "yyyy-MM-dd").alias("day"))
        .agg(F.count("*").alias("total_messages"))
        .orderBy("day")
    )
    spark_rows = result_df.collect()
    spark_times.append((time.time() - t0) * 1000)
spark_avg_ms = sum(spark_times) / len(spark_times)
print(f"DUREE_MS={spark_avg_ms:.0f}")

spark_days = sorted([(r["day"], r["total_messages"]) for r in spark_rows])

# --- Comparaison ---
same = set(native_days) == set(spark_days)
print(f"SAME_RESULT: {'OK' if same else 'DIFFERENT'}")
print(f"Native : {len(native_days)} jours, Spark : {len(spark_days)} jours")

# --- Écriture résultat ---
t0 = time.time()
result_df.write.format("mongodb").option("collection", "stats_cmp_a16").mode("overwrite").save()
write_ms = (time.time() - t0) * 1000
print(f"Lignes écrites dans stats_cmp_a16 : {len(spark_rows)}")
print(f"Durée écriture : {write_ms:.0f} ms")

spark.stop()
