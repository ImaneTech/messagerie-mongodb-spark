import time
from pymongo import MongoClient
from config.settings import MONGO_URI, MONGO_DB

def get_db():
    """Retourne la connexion MongoDB et la base de données"""
    client = MongoClient(MONGO_URI)
    return client[MONGO_DB]

def timed(fn, runs=5):
    """Exécute une fonction plusieurs fois et retourne le temps moyen en ms"""
    times = []
    for _ in range(runs):
        start = time.time()
        fn()
        end = time.time()
        times.append((end - start) * 1000)
    return sum(times) / len(times)
