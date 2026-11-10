"""Identification des contacts communs par auto-jointure distribuée (self-join)."""

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from config.settings import MONGO_DB, MONGO_URI
from spark.spark_session import get_spark_session

spark = get_spark_session("S27_CommonContacts")

# 1. Chargement des utilisateurs (identifiant et liste de contacts)
users_df = spark.read.format("mongodb").option("collection", "users").load()
users_df = users_df.select("_id", "contacts").withColumnRenamed("_id", "user_id")

# 2. Dénormalisation du tableau de contacts (une ligne par relation user -> contact)
exploded = users_df.select("user_id", F.explode("contacts").alias("contact_id"))
print(f"Lignes après explode : {exploded.count()}")

# 3. Auto-jointure sur contact_id avec condition asymétrique a.user_id < b.user_id
# Cela élimine les doublons (A, B) vs (B, A) ainsi que les auto-relations (A, A)
a = exploded.alias("a")
b = exploded.alias("b")

joined = a.join(
    b, (F.col("a.contact_id") == F.col("b.contact_id")) & (F.col("a.user_id") < F.col("b.user_id"))
).select(
    F.col("a.user_id").alias("user_a"), F.col("b.user_id").alias("user_b"), F.col("a.contact_id")
)
print(f"Lignes intermédiaires après self-join : {joined.count()}")

# 4. Regroupement par paire et calcul du nombre de contacts communs distincts
pairs = joined.groupBy("user_a", "user_b").agg(F.countDistinct("contact_id").alias("common_count"))

# Top 20 des paires les plus connectées
top20 = pairs.orderBy(F.col("common_count").desc()).limit(20)

# 5. Mesure de l'action de calcul distribué (3 runs, moyenne conforme guide §4.7)
spark_times = []
for _ in range(3):
    t0 = time.time()
    res = top20.collect()
    spark_times.append((time.time() - t0) * 1000)

avg_ms = sum(spark_times) / len(spark_times)
print(f"SPARK_AVG_MS={avg_ms:.0f}")
print(f"DUREE_MS={avg_ms:.0f}")
top20.show()

# 6. Persistance du résultat dans MongoDB (collection stats_s27)
start_write = time.time()
top20.write.format("mongodb").option("collection", "stats_s27").mode("overwrite").save()
duration_ms = (time.time() - start_write) * 1000
print(f"WRITE_MS={duration_ms:.0f}")

rows = top20.count()
print(f"Lignes écrites dans stats_s27 : {rows}")

spark.stop()
