"""Version Spark de A17 pour comparaison de performances avec MongoDB natif."""

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from pyspark.sql import functions as F
from spark.spark_session import get_spark_session
from spark.comparaison.timing import record_spark_timing

# --- Initialisation de la Session Spark ---
t_session_start = time.time()
spark = get_spark_session("CMP_A17_TopActiveUsers")
t_session_ms = (time.time() - t_session_start) * 1000
print(f"SPARK_SESSION_MS={t_session_ms:.0f}")

# --- Exécution de 3 runs Spark pour calcul de moyenne ---
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
record_spark_timing("A17", spark_avg_ms, t_session_ms)
print(f"DUREE_MS={spark_avg_ms:.0f}")

spark_top = sorted(
    [(str(r["sender_id"]), r["message_count"]) for r in spark_rows], key=lambda x: -x[1]
)
print(f"Spark top1 : {spark_top[0] if spark_top else 'none'}")

print("SAME_RESULT=SPARK_ONLY")
result_df.show(10)

# --- Écriture résultat dans MongoDB ---
t0 = time.time()
result_df.write.format("mongodb").option("collection", "stats_cmp_a17").mode("overwrite").save()
write_ms = (time.time() - t0) * 1000
print(f"Lignes écrites dans stats_cmp_a17 : {len(spark_rows)}")
print(f"Durée écriture : {write_ms:.0f} ms")

spark.stop()