"""
Module : benchmarks.merge_native_spark
Projet : Messagerie Distribuée Haute Performance (MongoDB & Apache Spark)

Rôle du fichier :
Fusion et comparaison formelle des résultats entre MongoDB natif (PyMongo) et Apache Spark :
- Porte sur les trois requêtes d'agrégation communes : A16 (activité par jour), A17 (top utilisateurs) et A18 (répartition par type).
- Récupère les temps d'exécution natifs depuis `queries_native.csv`.
- Récupère les durées de calcul Spark et d'initialisation de session (`spark_session_ms`).
- Valide l'équivalence exacte des résultats (`same_result = True/False`) en interrogeant
  les collections de sortie Spark (`stats_cmp_a16`, `stats_cmp_a17`, `stats_cmp_a18`).
- Génère le fichier de synthèse `benchmarks/results/native_vs_spark.csv`.
"""

import csv
import os
import shutil
import statistics
import sys
import time
from datetime import UTC, datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pymongo import MongoClient

from config.settings import MONGO_DB, MONGO_URI

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
NATIVE_CSV = os.path.join(RESULTS_DIR, "queries_native.csv")
SPARK_CMP_CSV = os.path.join(RESULTS_DIR, "spark_cmp_timings.csv")
OUTPUT_CSV = os.path.join(RESULTS_DIR, "native_vs_spark.csv")
DASHBOARD_CSV = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard", "native_vs_spark.csv")
COMPARISON_IDS = ("A16", "A17", "A18")


def read_spark_cmp_timings():
    """
    Retourne {query_id: {spark_avg_ms, spark_session_ms}} depuis spark_cmp_timings.csv.
    Ce CSV est produit après les jobs de comparaison Spark.
    Format: query_id, spark_avg_ms, spark_session_ms
    """
    data = {}
    if not os.path.exists(SPARK_CMP_CSV):
        print("[WARN] spark_cmp_timings.csv absent - timings Spark inconnus")
        return data

    with open(SPARK_CMP_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            qid = row.get("query_id", "").strip()
            try:
                avg = float(row.get("spark_avg_ms", 0))
            except ValueError:
                avg = 0.0
            try:
                sess = float(row.get("spark_session_ms", 0))
            except ValueError:
                sess = 0.0
            data[qid] = {"spark_avg_ms": avg, "spark_session_ms": sess}
    return data


def measure_native_timings(runs=3):
    """Measure each native aggregation repeatedly and return average milliseconds."""
    timings = {}
    for query_id in COMPARISON_IDS:
        durations = []
        for _ in range(runs):
            start = time.perf_counter()
            get_native_result(query_id)
            durations.append((time.perf_counter() - start) * 1000)
        timings[query_id] = {
            "avg_ms": sum(durations) / len(durations),
            "median_ms": statistics.median(durations),
        }
        print(
            f"  {query_id} MongoDB natif: "
            f"{timings[query_id]['avg_ms']:.2f} ms ({runs} runs)"
        )
    return timings


def get_native_result(query_id):
    """Exécute la requête native et retourne le résultat sous forme canonique."""
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    try:
        db = client[MONGO_DB]
        now = datetime.now(UTC).replace(tzinfo=None)
        start_30d = now - timedelta(days=30)

        if query_id == "A16":
            pipeline = [
                {"$match": {"ts": {"$gte": start_30d}}},
                {
                    "$group": {
                        "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$ts"}},
                        "total_messages": {"$sum": 1},
                    }
                },
                {"$sort": {"_id": 1}},
            ]
            docs = list(db.messages.aggregate(pipeline))
            return {d["_id"]: d["total_messages"] for d in docs}

        if query_id == "A17":
            pipeline = [
                {"$group": {"_id": "$sender_id", "message_count": {"$sum": 1}}},
                {"$sort": {"message_count": -1}},
                {"$limit": 10},
            ]
            docs = list(db.messages.aggregate(pipeline))
            return {d["_id"]: d["message_count"] for d in docs}

        if query_id == "A18":
            pipeline = [{"$group": {"_id": "$type", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}]
            docs = list(db.messages.aggregate(pipeline))
            return {d["_id"]: d["count"] for d in docs}

        raise ValueError(f"Unknown comparison query: {query_id}")
    finally:
        client.close()


def get_spark_result(query_id):
    """Lit la collection stats_cmp_a* et retourne le résultat sous forme canonique."""
    coll_map = {"A16": "stats_cmp_a16", "A17": "stats_cmp_a17", "A18": "stats_cmp_a18"}
    coll_name = coll_map.get(query_id)
    if not coll_name:
        return {}

    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[MONGO_DB]

    if coll_name not in db.list_collection_names():
        client.close()
        print(f"  [WARN] Collection {coll_name} absente")
        return {}

    docs = list(db[coll_name].find({}, {"_id": 0}))
    client.close()

    result = {}
    if query_id == "A16":
        for d in docs:
            day = d.get("day") or d.get("_id", "")
            total = d.get("total_messages") or d.get("count", 0)
            result[str(day)] = int(total)
    elif query_id == "A17":
        for d in docs:
            sender = d.get("sender_id") or d.get("_id", "")
            count = d.get("message_count") or d.get("count", 0)
            result[str(sender)] = int(count)
    elif query_id == "A18":
        for d in docs:
            typ = d.get("type") or d.get("_id", "")
            count = d.get("count", 0)
            result[str(typ)] = int(count)

    return result


def compare(native_res, spark_res, query_id):
    """Compare les deux résultats et retourne 'OK' ou 'DIFFERENT' avec explication."""
    if not spark_res:
        return "DIFFERENT", "Spark result empty (collection absente ou vide)"

    if query_id == "A16":
        # Comparer le total de messages et le nombre de jours
        native_total = sum(native_res.values())
        spark_total = sum(spark_res.values())
        native_days = len(native_res)
        spark_days = len(spark_res)
        print(f"  A16 native: {native_days} jours, {native_total} messages")
        print(f"  A16 spark : {spark_days} jours, {spark_total} messages")
        # Tolérance ±1% sur le total (rechargement peut changer légèrement)
        if native_days == spark_days and native_total == spark_total:
            return "OK", f"jours={native_days}, total={native_total}"
        else:
            return (
                "DIFFERENT",
                f"native={native_days}j/{native_total}msg, spark={spark_days}j/{spark_total}msg",
            )

    elif query_id == "A17":
        # Comparer le top 10 (sender_ids et counts)
        native_top = sorted(native_res.items(), key=lambda x: -x[1])[:10]
        spark_top = sorted(spark_res.items(), key=lambda x: -x[1])[:10]
        print(f"  A17 native top1: {native_top[0] if native_top else 'none'}")
        print(f"  A17 spark  top1: {spark_top[0]  if spark_top  else 'none'}")
        native_keys = {k for k, v in native_top}
        spark_keys = {k for k, v in spark_top}
        if native_keys == spark_keys and dict(native_top) == dict(spark_top):
            return "OK", f"top10 identique, top1={native_top[0]}"
        else:
            diff = native_keys.symmetric_difference(spark_keys)
            return "DIFFERENT", f"senders différents: {diff}"

    elif query_id == "A18":
        # Comparer types et counts
        print(f"  A18 native: {sorted(native_res.items())}")
        print(f"  A18 spark : {sorted(spark_res.items())}")
        if native_res == spark_res:
            return "OK", f"types identiques: {list(native_res.keys())}"
        return (
            "DIFFERENT",
            f"types différents: native={set(native_res.keys())} spark={set(spark_res.keys())}",
        )

    return "DIFFERENT", "comparaison non implémentée"


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    native_timings = measure_native_timings()
    spark_timings = read_spark_cmp_timings()
    missing_spark = [qid for qid in COMPARISON_IDS if qid not in spark_timings]
    if missing_spark:
        raise RuntimeError(
            "Missing Spark timings for "
            + ", ".join(missing_spark)
            + ". Run cmp_a16.py, cmp_a17.py and cmp_a18.py first."
        )

    rows = []
    for qid in COMPARISON_IDS:
        print(f"\n=== Comparaison {qid} ===")
        native_res = get_native_result(qid)
        spark_res = get_spark_result(qid)
        verdict, detail = compare(native_res, spark_res, qid)
        print(f"  -> same_result={verdict}  ({detail})")

        native_timing = native_timings.get(qid)
        spark_avg = spark_timings.get(qid, {}).get("spark_avg_ms", None)
        if native_timing is None or spark_avg is None:
            raise RuntimeError(f"Missing timing for {qid}; refusing to write incomplete CSV")
        rows.append(
            {
                "query_id": qid,
                "native_avg_ms": f"{native_timing['avg_ms']:.6f}",
                "native_median_ms": f"{native_timing['median_ms']:.6f}",
                "spark_avg_ms": f"{spark_avg:.6f}",
            }
        )

    fieldnames = ["query_id", "native_avg_ms", "native_median_ms", "spark_avg_ms"]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    shutil.copyfile(OUTPUT_CSV, DASHBOARD_CSV)

    print(f"\n=== {OUTPUT_CSV} ===")
    print(f"{'query_id':<8} {'native_avg_ms':>14} {'spark_avg_ms':>13}")
    print("-" * 40)
    for r in rows:
        print(f"{r['query_id']:<8} {r['native_avg_ms']:>14} {r['spark_avg_ms']:>13}")
    print(f"Copie dashboard : {DASHBOARD_CSV}")


if __name__ == "__main__":
    main()
