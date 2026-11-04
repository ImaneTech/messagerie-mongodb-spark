import os
import time

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

MONGO_URI = os.environ["MONGO_URI"]

spark = (
    SparkSession.builder.appName("S30_RetentionCohorts")
    .config("spark.mongodb.read.connection.uri", MONGO_URI)
    .config("spark.mongodb.write.connection.uri", MONGO_URI)
    .config("spark.mongodb.read.database", "chatdb")
    .config("spark.mongodb.write.database", "chatdb")
    .getOrCreate()
)

# Lire users
users_df = spark.read.format("mongodb").option("collection", "users").load()
users_df = users_df.select(F.col("_id").alias("user_id"), "created_at")

# Cohort = mois de created_at ("YYYY-MM")
users_df = users_df.withColumn("cohort", F.date_format(F.col("created_at"), "yyyy-MM"))

# Taille de chaque cohorte
cohort_sizes = users_df.groupBy("cohort").agg(F.count("user_id").alias("cohort_size"))

# Lire messages
msgs_df = spark.read.format("mongodb").option("collection", "messages").load()
msgs_df = msgs_df.select(F.col("sender_id").alias("user_id"), "ts")

# Joindre users (cohort) avec messages (ts)
joined = users_df.join(msgs_df, "user_id", "inner")

# Mois du message
joined = joined.withColumn("msg_month", F.date_format(F.col("ts"), "yyyy-MM"))

# Mois suivant la cohorte (add_months)
joined = joined.withColumn(
    "next_month",
    F.date_format(F.add_months(F.to_date(F.concat(F.col("cohort"), F.lit("-01"))), 1), "yyyy-MM"),
)

# Active = sender qui a au moins 1 message dans le mois suivant la cohorte
active_users = (
    joined.filter(F.col("msg_month") == F.col("next_month"))
    .groupBy("cohort", "user_id")
    .agg(F.count("ts").alias("msg_count"))
    .filter(F.col("msg_count") >= 1)
    .groupBy("cohort")
    .agg(F.countDistinct("user_id").alias("active_users"))
)

# Joindre cohort_sizes et active_users
result = (
    cohort_sizes.join(active_users, "cohort", "left")
    .fillna(0, subset=["active_users"])
    .withColumn("retention_pct", F.round(F.col("active_users") / F.col("cohort_size") * 100, 2))
    .orderBy("cohort")
)

result.show()

start_write = time.time()
result.write.format("mongodb").option("collection", "stats_s30").mode("overwrite").save()
duration_ms = (time.time() - start_write) * 1000
print(f"DUREE_MS={duration_ms:.0f}")

rows = result.count()
print(f"Lignes écrites dans stats_s30 : {rows} cohortes")

spark.stop()
