from pyspark.sql import SparkSession

uri = "mongodb://192.168.0.178:27017,192.168.0.178:27018,192.168.0.195:27017/?replicaSet=rs0"

spark = (SparkSession.builder.appName("test_mongo")
         .config("spark.mongodb.read.connection.uri", uri)
         .config("spark.mongodb.write.connection.uri", uri)
         .getOrCreate())
spark.sparkContext.setLogLevel("ERROR")

df = (spark.read.format("mongodb")
      .option("database", "test")
      .option("collection", "ping")
      .load())
df.show()
spark.stop()