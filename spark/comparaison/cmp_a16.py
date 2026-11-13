"""Version Spark de A16 pour comparaison de performances avec MongoDB natif."""

import os
import sys
import time
from datetime import datetime, timedelta, timezone
UTC = timezone.utc

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from pyspark.sql import functions as F

from spark.comparaison.timing import record_spark_timing
from spark.spark_session import get_spark_session

# --- Initialisation de la Session Spark ---
t_session_start = time.time()
spark = get_spark_session("CMP_A16_MessagesPerDay")
t_session_ms = (time.time() - t_session_start) * 1000
print(f"SPARK_SESSION_MS={t_session_ms:.0f}")

now = datetime.now(UTC).replace(tzinfo=None)
start_30d = now - timedelta(days=30)

# --- Exécution de 3 runs Spark pour calcul de moyenne ---
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
record_spark_timing("A16", spark_avg_ms, t_session_ms)
print(f"DUREE_MS={spark_avg_ms:.0f}")
print(
    f"Spark : {len(spark_rows)} jours, total messages : {sum(r['total_messages'] for r in spark_rows)}"
)

print("SAME_RESULT=SPARK_ONLY")
result_df.show(35, truncate=False)

# --- Écriture résultat dans MongoDB ---
t0 = time.time()
result_df.write.format("mongodb").option("collection", "stats_cmp_a16").mode("overwrite").save()
write_ms = (time.time() - t0) * 1000
print(f"Lignes écrites dans stats_cmp_a16 : {len(spark_rows)}")
print(f"Durée écriture : {write_ms:.0f} ms")

spark.stop()