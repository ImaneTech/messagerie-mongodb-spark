"""Version Spark de A18 pour comparaison de performances avec MongoDB natif."""

import os
import sys
import time
import csv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from pyspark.sql import functions as F
from spark.spark_session import get_spark_session

# --- Initialisation de la Session Spark ---
t_session_start = time.time()
spark = get_spark_session("CMP_A18_MessagesByType")
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
        msgs_df.groupBy("type").agg(F.count("*").alias("count")).orderBy(F.col("count").desc())
    )
    spark_rows = result_df.collect()
    spark_times.append((time.time() - t0) * 1000)

spark_avg_ms = sum(spark_times) / len(spark_times)
print(f"SPARK_AVG_MS={spark_avg_ms:.0f}")
print(f"DUREE_MS={spark_avg_ms:.0f}")

spark_types = sorted([(r["type"], r["count"]) for r in spark_rows])
print(f"Types Spark : {spark_types}")

print("SAME_RESULT=SPARK_ONLY")
result_df.show()

# --- Écriture résultat dans MongoDB ---
t0 = time.time()
result_df.write.format("mongodb").option("collection", "stats_cmp_a18").mode("overwrite").save()
write_ms = (time.time() - t0) * 1000
print(f"Lignes écrites dans stats_cmp_a18 : {len(spark_rows)}")
print(f"Durée écriture : {write_ms:.0f} ms")

# --- Export direct en CSV pour le dashboard Streamlit ---
csv_path = "/tmp/native_vs_spark.csv"
rows_to_write = [
    {"benchmark": "A18", "type": r["type"], "count": r["count"], "duration_ms": spark_avg_ms}
    for r in spark_rows
]

with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["benchmark", "type", "count", "duration_ms"])
    writer.writeheader()
    writer.writerows(rows_to_write)

print(f"Fichier CSV généré avec succès : {csv_path}")

spark.stop()