import os
import json
import time
from pymongo import MongoClient
from config.settings import MONGO_URI, MONGO_DB

def get_db():
    """Retourne la connexion MongoDB et la base de données."""
    client = MongoClient(MONGO_URI)
    return client[MONGO_DB]

def timed(fn, runs=5):
    """Exécute une fonction plusieurs fois et retourne le temps moyen en ms."""
    times = []
    for _ in range(runs):
        start = time.time()
        fn()
        end = time.time()
        times.append((end - start) * 1000)
    return sum(times) / len(times)

def extract_index_name(explain_dict):
    """Extrait récursivement le nom de l'index utilisé dans le winningPlan d'explain()."""
    def find_index(stage):
        if not isinstance(stage, dict):
            return None
        if "indexName" in stage:
            return stage["indexName"]
        for k in ["inputStage", "inputStages"]:
            sub = stage.get(k)
            if isinstance(sub, dict):
                res = find_index(sub)
                if res:
                    return res
            elif isinstance(sub, list):
                for s in sub:
                    res = find_index(s)
                    if res:
                        return res
        return None

    winning = explain_dict.get("queryPlanner", {}).get("winningPlan", {})
    return find_index(winning) or "COLLSCAN"

def record_benchmark(query_id, time_ms, details=None):
    """Enregistre le résultat de benchmark dans benchmarks/results/benchmarks.json."""
    results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "benchmarks", "results"))
    os.makedirs(results_dir, exist_ok=True)
    file_path = os.path.join(results_dir, "benchmarks.json")

    data = {}
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

    data[query_id] = {
        "time_ms": round(time_ms, 3),
        "details": details or {}
    }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
