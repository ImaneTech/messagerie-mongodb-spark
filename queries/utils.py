"""Fonctions utilitaires pour l'accès MongoDB et le chronométrage des requêtes."""

import csv
import json
import os
import time

from pymongo import MongoClient

from config.settings import MONGO_DB, MONGO_URI


def get_db():
    """Retourne l'objet Database MongoDB connecté au Replica Set."""
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return client[MONGO_DB]


def timed(fn, runs=3):
    """
    Exécute une fonction `runs` fois consécutives et calcule le temps moyen, min et max en ms.
    Permet d'éliminer la gigue (jitter) réseau et d'obtenir des mesures stables.
    """
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        fn()
        end = time.perf_counter()
        times.append((end - start) * 1000.0)
    return {
        "avg": round(sum(times) / len(times), 2),
        "min": round(min(times), 2),
        "max": round(max(times), 2),
    }


def extract_index_name(explain_dict):
    """
    Extrait récursivement le nom de l'index utilisé dans le plan d'exécution optimal (winningPlan).
    Retourne 'COLLSCAN' si aucun index n'a été exploité (scan complet de collection).
    """
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


def save_query_results(filename, results_list):
    """
    Sauvegarde une liste de dictionnaires de résultats dans un fichier CSV.
    Crée automatiquement le dossier de destination si nécessaire.
    """
    if not results_list:
        return
    results_dir = os.path.dirname(filename)
    if results_dir:
        os.makedirs(results_dir, exist_ok=True)

    fieldnames = list(results_list[0].keys())
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results_list)
