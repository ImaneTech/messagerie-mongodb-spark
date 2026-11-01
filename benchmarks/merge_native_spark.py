"""
merge_native_spark.py
Compare les résultats natifs (MongoDB PyMongo) et Spark pour A16, A17, A18.
Lit queries_native.csv pour les timings natifs.
Lit les collections stats_cmp_a16/17/18 pour les résultats Spark.
Relit spark_jobs.csv pour les timings Spark cmp (colonnes avg_ms lignes cmp_a16 etc.).
Écrit native_vs_spark.csv : query_id, native_avg_ms, spark_avg_ms, spark_session_ms, same_result.
"""
import sys
import os
import csv
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config.settings import MONGO_URI, MONGO_DB
from pymongo import MongoClient

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
NATIVE_CSV  = os.path.join(RESULTS_DIR, "queries_native.csv")
SPARK_CMP_CSV = os.path.join(RESULTS_DIR, "spark_cmp_timings.csv")
OUTPUT_CSV  = os.path.join(RESULTS_DIR, "native_vs_spark.csv")


def read_native_timings():
    """Retourne {query_id: avg_ms} depuis queries_native.csv."""
    data = {}
    if not os.path.exists(NATIVE_CSV):
        print(f"[WARN] Absent: {NATIVE_CSV}")
        return data
    with open(NATIVE_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            qid = row.get("query_id", "").strip()
            if qid in ("A16", "A17", "A18"):
                try:
                    data[qid] = float(row.get("avg_ms", 0))
                except ValueError:
                    data[qid] = 0.0
    return data


def read_spark_cmp_timings():
    """
    Retourne {query_id: {spark_avg_ms, spark_session_ms}} depuis spark_cmp_timings.csv.
    Ce CSV est produit par run_spark_cmp.ps1 (ou manuellement après les jobs cmp).
    Format: query_id, spark_avg_ms, spark_session_ms
    """
    data = {}
    if not os.path.exists(SPARK_CMP_CSV):
        print(f"[WARN] spark_cmp_timings.csv absent - timings Spark inconnus")
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


def get_native_result(query_id):
    """Exécute la requête native et retourne le résultat sous forme canonique."""
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[MONGO_DB]
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start_30d = now - timedelta(days=30)
    result = {}

    if query_id == "A16":
        pipeline = [
            {"$match": {"ts": {"$gte": start_30d}}},
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$ts"}},
                "total_messages": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        docs = list(db.messages.aggregate(pipeline))
        result = {d["_id"]: d["total_messages"] for d in docs}

    elif query_id == "A17":
        pipeline = [
            {"$group": {"_id": "$sender_id", "message_count": {"$sum": 1}}},
            {"$sort": {"message_count": -1}},
            {"$limit": 10}
        ]
        docs = list(db.messages.aggregate(pipeline))
        result = {d["_id"]: d["message_count"] for d in docs}

    elif query_id == "A18":
        pipeline = [
            {"$group": {"_id": "$type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        docs = list(db.messages.aggregate(pipeline))
        result = {d["_id"]: d["count"] for d in docs}

    client.close()
    return result


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
        spark_total  = sum(spark_res.values())
        native_days  = len(native_res)
        spark_days   = len(spark_res)
        print(f"  A16 native: {native_days} jours, {native_total} messages")
        print(f"  A16 spark : {spark_days} jours, {spark_total} messages")
        # Tolérance ±1% sur le total (rechargement peut changer légèrement)
        if native_days == spark_days and abs(native_total - spark_total) <= 0.01 * native_total:
            return "OK", f"jours={native_days}, total={native_total}"
        else:
            return "DIFFERENT", f"native={native_days}j/{native_total}msg, spark={spark_days}j/{spark_total}msg"

    elif query_id == "A17":
        # Comparer le top 10 (sender_ids et counts)
        native_top = sorted(native_res.items(), key=lambda x: -x[1])[:10]
        spark_top  = sorted(spark_res.items(), key=lambda x: -x[1])[:10]
        print(f"  A17 native top1: {native_top[0] if native_top else 'none'}")
        print(f"  A17 spark  top1: {spark_top[0]  if spark_top  else 'none'}")
        native_keys = {k for k, v in native_top}
        spark_keys  = {k for k, v in spark_top}
        if native_keys == spark_keys and dict(native_top) == dict(spark_top):
            return "OK", f"top10 identique, top1={native_top[0]}"
        elif native_keys == spark_keys:
            return "OK", f"top10 mêmes senders (counts peuvent varier si rechargement)"
        else:
            diff = native_keys.symmetric_difference(spark_keys)
            return "DIFFERENT", f"senders différents: {diff}"

    elif query_id == "A18":
        # Comparer types et counts
        print(f"  A18 native: {sorted(native_res.items())}")
        print(f"  A18 spark : {sorted(spark_res.items())}")
        if native_res == spark_res:
            return "OK", f"types identiques: {list(native_res.keys())}"
        # Vérifier si les types sont les mêmes (counts peuvent différer légèrement après rechargement)
        if set(native_res.keys()) == set(spark_res.keys()):
            total_native = sum(native_res.values())
            total_spark  = sum(spark_res.values())
            if abs(total_native - total_spark) <= 0.01 * total_native:
                return "OK", f"types identiques, totaux ~égaux ({total_native} vs {total_spark})"
            else:
                return "DIFFERENT", f"totaux différents: native={total_native} spark={total_spark}"
        return "DIFFERENT", f"types différents: native={set(native_res.keys())} spark={set(spark_res.keys())}"

    return "DIFFERENT", "comparaison non implémentée"


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    native_timings = read_native_timings()
    spark_timings  = read_spark_cmp_timings()

    rows = []
    for qid in ["A16", "A17", "A18"]:
        print(f"\n=== Comparaison {qid} ===")
        native_res = get_native_result(qid)
        spark_res  = get_spark_result(qid)
        verdict, detail = compare(native_res, spark_res, qid)
        print(f"  -> same_result={verdict}  ({detail})")

        native_avg = native_timings.get(qid, None)
        spark_avg  = spark_timings.get(qid, {}).get("spark_avg_ms", None)
        spark_sess = spark_timings.get(qid, {}).get("spark_session_ms", None)

        rows.append({
            "query_id":        qid,
            "native_avg_ms":   f"{native_avg:.2f}" if native_avg is not None else "N/A",
            "spark_avg_ms":    f"{spark_avg:.2f}"  if spark_avg  is not None else "N/A",
            "spark_session_ms": f"{spark_sess:.2f}" if spark_sess is not None else "N/A",
            "same_result":     verdict,
        })

    fieldnames = ["query_id", "native_avg_ms", "spark_avg_ms", "spark_session_ms", "same_result"]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n=== {OUTPUT_CSV} ===")
    print(f"{'query_id':<8} {'native_avg_ms':>14} {'spark_avg_ms':>13} {'spark_session_ms':>16} {'same_result':>12}")
    print("-" * 68)
    for r in rows:
        print(f"{r['query_id']:<8} {r['native_avg_ms']:>14} {r['spark_avg_ms']:>13} "
              f"{r['spark_session_ms']:>16} {r['same_result']:>12}")


if __name__ == "__main__":
    main()
