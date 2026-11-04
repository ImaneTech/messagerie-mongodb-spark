import os
import time
from datetime import datetime, timedelta, timezone

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

# URI injectée par docker exec -e MONGO_URI
MONGO_URI = os.environ["MONGO_URI"]

# --- Session Spark ---
t_session_start = time.time()
spark = (
    SparkSession.builder.appName("CMP_A16_MessagesPerDay")
    .config("spark.mongodb.read.connection.uri", MONGO_URI)
    .config("spark.mongodb.write.connection.uri", MONGO_URI)
    .config("spark.mongodb.read.database", "chatdb")
    .config("spark.mongodb.write.database", "chatdb")
    .getOrCreate()
)
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
        msgs_df.filter(F.col("ts") >= F.lit(start_30d).cast("timestamp"))
        .groupBy(F.date_format("ts", "yyyy-MM-dd").alias("day"))
        .agg(F.count("*").alias("total_messages"))
        .orderBy("day")
    )
    spark_rows = result_df.collect()
    spark_times.append((time.time() - t0) * 1000)
spark_avg_ms = sum(spark_times) / len(spark_times)
print(f"SPARK_AVG_MS={spark_avg_ms:.0f}")
print(f"DUREE_MS={spark_avg_ms:.0f}")
print(
    f"Spark : {len(spark_rows)} jours, total messages : {sum(r['total_messages'] for r in spark_rows)}"
)

# La comparaison native/Spark est réalisée dans merge_native_spark.py
print("SAME_RESULT=SPARK_ONLY")

result_df.show(35, truncate=False)

# --- Écriture résultat ---
t0 = time.time()
result_df.write.format("mongodb").option("collection", "stats_cmp_a16").mode("overwrite").save()
write_ms = (time.time() - t0) * 1000
print(f"Lignes écrites dans stats_cmp_a16 : {len(spark_rows)}")
print(f"Durée écriture : {write_ms:.0f} ms")

spark.stop()
