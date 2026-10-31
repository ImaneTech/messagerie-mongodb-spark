import os
import time
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pymongo import MongoClient

# URI injectée par docker exec -e MONGO_URI
MONGO_URI = os.environ["MONGO_URI"]


def native_run(mongo_uri):
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    db = client["chatdb"]
    pipeline = [
        {"$group": {"_id": "$type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
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
native_types = sorted([(r["_id"], r["count"]) for r in native_result])

# --- Session Spark ---
t_session_start = time.time()
spark = SparkSession.builder \
    .appName("CMP_A18_MessagesByType") \
    .config("spark.mongodb.read.connection.uri", MONGO_URI) \
    .config("spark.mongodb.write.connection.uri", MONGO_URI) \
    .config("spark.mongodb.read.database", "chatdb") \
    .config("spark.mongodb.write.database", "chatdb") \
    .getOrCreate()
t_session_ms = (time.time() - t_session_start) * 1000
print(f"SPARK_SESSION_MS={t_session_ms:.0f}")

# --- 3 runs Spark ---
spark_times = []
spark_rows = None
result_df = None
for _ in range(3):
    t0 = time.time()
    msgs_df = spark.read.format("mongodb").option("collection", "messages").load()
    result_df = (
        msgs_df
        .groupBy("type")
        .agg(F.count("*").alias("count"))
        .orderBy(F.col("count").desc())
    )
    spark_rows = result_df.collect()
    spark_times.append((time.time() - t0) * 1000)
spark_avg_ms = sum(spark_times) / len(spark_times)
print(f"DUREE_MS={spark_avg_ms:.0f}")

spark_types = sorted([(r["type"], r["count"]) for r in spark_rows])

# --- Comparaison ---
same = native_types == spark_types
print(f"SAME_RESULT: {'OK' if same else 'DIFFERENT'}")
print(f"Types natif : {native_types}")
print(f"Types Spark : {spark_types}")

result_df.show()

# --- Écriture résultat ---
t0 = time.time()
result_df.write.format("mongodb").option("collection", "stats_cmp_a18").mode("overwrite").save()
write_ms = (time.time() - t0) * 1000
print(f"Lignes écrites dans stats_cmp_a18 : {len(spark_rows)}")
print(f"Durée écriture : {write_ms:.0f} ms")

spark.stop()
