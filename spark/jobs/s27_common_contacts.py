"""Identification des contacts communs par auto-jointure distribuée (self-join)."""

import os
import time

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

MONGO_URI = os.environ["MONGO_URI"]

# Initialisation de la session Spark avec le connecteur MongoDB
spark = (
    SparkSession.builder.appName("S27_CommonContacts")
    .config("spark.mongodb.read.connection.uri", MONGO_URI)
    .config("spark.mongodb.write.connection.uri", MONGO_URI)
    .config("spark.mongodb.read.database", "chatdb")
    .config("spark.mongodb.write.database", "chatdb")
    .getOrCreate()
)

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
top20.show()

# 5. Persistance du résultat dans MongoDB (collection stats_s27)
start_write = time.time()
top20.write.format("mongodb").option("collection", "stats_s27").mode("overwrite").save()
duration_ms = (time.time() - start_write) * 1000
print(f"DUREE_MS={duration_ms:.0f}")

rows = top20.count()
print(f"Lignes écrites dans stats_s27 : {rows}")

spark.stop()
