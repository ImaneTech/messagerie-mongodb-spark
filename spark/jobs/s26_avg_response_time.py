from pyspark.sql import SparkSession
from config.settings import MONGO_URI, MONGO_DB

def run():
    """
    S26: Temps de réponse moyen entre messages dans une conversation
    Spark job pour calculer la différence moyenne entre created_at de messages consécutifs par conversation
    """
    pass
