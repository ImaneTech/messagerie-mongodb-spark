import os
import time

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

# URI injectée par docker exec -e MONGO_URI
MONGO_URI = os.environ["MONGO_URI"]

# --- Session Spark ---
t_session_start = time.time()
spark = (
    SparkSession.builder.appName("CMP_A17_TopActiveUsers")
    .config("spark.mongodb.read.connection.uri", MONGO_URI)
    .config("spark.mongodb.write.connection.uri", MONGO_URI)
    .config("spark.mongodb.read.database", "chatdb")
    .config("spark.mongodb.write.database", "chatdb")
    .getOrCreate()
)
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
        msgs_df.groupBy("sender_id")
        .agg(F.count("*").alias("message_count"))
        .orderBy(F.col("message_count").desc())
        .limit(10)
    )
    spark_rows = result_df.collect()
    spark_times.append((time.time() - t0) * 1000)
spark_avg_ms = sum(spark_times) / len(spark_times)
print(f"SPARK_AVG_MS={spark_avg_ms:.0f}")
print(f"DUREE_MS={spark_avg_ms:.0f}")

spark_top = sorted(
    [(str(r["sender_id"]), r["message_count"]) for r in spark_rows], key=lambda x: -x[1]
)
print(f"Spark top1 : {spark_top[0] if spark_top else 'none'}")

# La comparaison native/Spark est réalisée dans merge_native_spark.py
print("SAME_RESULT=SPARK_ONLY")

result_df.show(10)

# --- Écriture résultat ---
t0 = time.time()
result_df.write.format("mongodb").option("collection", "stats_cmp_a17").mode("overwrite").save()
write_ms = (time.time() - t0) * 1000
print(f"Lignes écrites dans stats_cmp_a17 : {len(spark_rows)}")
print(f"Durée écriture : {write_ms:.0f} ms")

spark.stop()
