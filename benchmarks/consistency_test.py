"""
Module : benchmarks.consistency_test
Projet : Messagerie Distribuée Haute Performance (MongoDB & Apache Spark)

Rôle du fichier :
Benchmark des niveaux de garantie de réplication et de cohérence distribuée (CAP Theorem / PACELC) :
1. Niveaux de Write Concern sur écriture unitaire T01 et import par lot T02 :
   - `w=1`        : Accusé de réception dès écriture sur le nœud Primaire (faible latence, risque de rollback).
   - `w=majority` : Accusé de réception après réplication sur la majorité des nœuds (2/3 du Replica Set).
2. Niveaux de Read Concern sur lecture T04 :
   - `local`    : Données lues localement sur le nœud sollicité.
   - `majority` : Lecture exclusive des données confirmées par quorum, protégeant contre la lecture sale (dirty read).
3. Sauvegarde des mesures comparatives (temps moyen, min, max, p95) dans `benchmarks/results/consistency_test.csv`.
"""

import csv
import os
import statistics
import sys
import time
from datetime import UTC, datetime

from bson import ObjectId

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pymongo import DESCENDING, MongoClient, WriteConcern
from pymongo.errors import PyMongoError
from pymongo.read_concern import ReadConcern

from config.settings import COLLECTIONS, MONGO_DB, MONGO_URI

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def get_members_up():
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        status = client.admin.command("replSetGetStatus")
        members_up = sum(
            1 for m in status.get("members", []) if m.get("stateStr") in ["PRIMARY", "SECONDARY"]
        )
        client.close()
        return members_up
    except PyMongoError as exc:
        raise RuntimeError(
            f"Impossible de vérifier les membres MongoDB ({type(exc).__name__})."
        ) from exc


def get_heavy_conv(db):
    pipeline = [
        {"$group": {"_id": "$conversation_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 1},
    ]
    top = list(db[COLLECTIONS["messages"]].aggregate(pipeline))
    return top[0]["_id"] if top else None


def make_message(conv_id, user_id=None):
    return {
        "_id": ObjectId(),
        "conversation_id": conv_id,
        "sender_id": user_id or ObjectId(),
        "content": "benchmark test",
        "type": "text",
        "ts": datetime.now(UTC).replace(tzinfo=None),
        "deleted": False,
        "_benchmark": True,
    }


def bench_t1_write_concern(db, conv_id, wc_value, runs=50):
    """Insère 1 message avec write concern w=wc_value, runs fois."""
    times = []
    coll = db[COLLECTIONS["messages"]].with_options(
        write_concern=WriteConcern(w=wc_value, wtimeout=10000)
    )
    for _ in range(runs):
        doc = make_message(conv_id)
        t0 = time.time()
        result = coll.insert_one(doc)
        elapsed = (time.time() - t0) * 1000
        times.append(elapsed)
        coll.delete_one({"_id": result.inserted_id, "_benchmark": True})
    return times


def bench_t2_write_concern(db, conv_id, wc_value, runs=5):
    """Insère 10 000 messages avec write concern w=wc_value, runs fois."""
    times = []
    coll = db[COLLECTIONS["messages"]].with_options(
        write_concern=WriteConcern(w=wc_value, wtimeout=10000)
    )
    for _ in range(runs):
        docs = [make_message(conv_id) for _ in range(10000)]
        t0 = time.time()
        coll.insert_many(docs, ordered=False)
        elapsed = (time.time() - t0) * 1000
        times.append(elapsed)
        coll.delete_many({"_benchmark": True})
    return times


def bench_t4_read_concern(db, conv_id, rc_level, runs=30):
    """Requête T4 (50 derniers messages) avec read concern rc_level, runs fois."""
    times = []
    coll = db[COLLECTIONS["messages"]].with_options(read_concern=ReadConcern(level=rc_level))
    for _ in range(runs):
        t0 = time.time()
        list(
            coll.find({"conversation_id": conv_id, "deleted": False})
            .sort("ts", DESCENDING)
            .limit(50)
        )
        elapsed = (time.time() - t0) * 1000
        times.append(elapsed)
    return times


def calc_stats(times, n_runs=None):
    n = n_runs or len(times)
    return {
        "runs": n,
        "avg_ms": round(statistics.mean(times), 2),
        "median_ms": round(statistics.median(times), 2),
        "p95_ms": round(sorted(times)[int(len(times) * 0.95)], 2),
    }


def main():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[MONGO_DB]
    
    members_up = get_members_up()
    if members_up != 3:
        client.close()
        raise SystemExit(
            f"Erreur : 3 membres sont nécessaires, mais seulement {members_up} sont disponibles."
        )
        
    conv_id = get_heavy_conv(db)
    print(f"members_up={members_up}, conv_id={conv_id}")

    rows = []

    # T1 write concern w=1
    print("T1 write concern w=1 (50 runs)...")
    t1_w1 = bench_t1_write_concern(db, conv_id, 1, runs=50)
    s = calc_stats(t1_w1)
    rows.append({"test_id": "T1", "setting": "w=1", **s, "members_up": members_up})
    print(f"  w=1: avg={s['avg_ms']}ms")

    # T1 write concern w=majority
    print("T1 write concern w=majority (50 runs)...")
    t1_wmaj = bench_t1_write_concern(db, conv_id, "majority", runs=50)
    s = calc_stats(t1_wmaj)
    rows.append({"test_id": "T1", "setting": "w=majority", **s, "members_up": members_up})
    print(f"  w=majority: avg={s['avg_ms']}ms")

    # T1 write concern w=3
    print("T1 write concern w=3 (50 runs)...")
    t1_w3 = bench_t1_write_concern(db, conv_id, 3, runs=50)
    s = calc_stats(t1_w3)
    rows.append({"test_id": "T1", "setting": "w=3", **s, "members_up": members_up})
    print(f"  w=3: avg={s['avg_ms']}ms")

    # T2 write concern w=1
    print("T2 write concern w=1 (5 runs, 10000 docs)...")
    t2_w1 = bench_t2_write_concern(db, conv_id, 1, runs=5)
    s = calc_stats(t2_w1)
    rows.append({"test_id": "T2", "setting": "w=1", **s, "members_up": members_up})
    print(f"  w=1: avg={s['avg_ms']}ms")

    # T2 write concern w=majority
    print("T2 write concern w=majority (5 runs, 10000 docs)...")
    t2_wmaj = bench_t2_write_concern(db, conv_id, "majority", runs=5)
    s = calc_stats(t2_wmaj)
    rows.append({"test_id": "T2", "setting": "w=majority", **s, "members_up": members_up})
    print(f"  w=majority: avg={s['avg_ms']}ms")

    # T2 write concern w=3
    print("T2 write concern w=3 (5 runs, 10000 docs)...")
    t2_w3 = bench_t2_write_concern(db, conv_id, 3, runs=5)
    s = calc_stats(t2_w3)
    rows.append({"test_id": "T2", "setting": "w=3", **s, "members_up": members_up})
    print(f"  w=3: avg={s['avg_ms']}ms")

    # T4 read concern local
    print("T4 read concern local (30 runs)...")
    t4_local = bench_t4_read_concern(db, conv_id, "local", runs=30)
    s = calc_stats(t4_local)
    rows.append({"test_id": "T4", "setting": "readConcern=local", **s, "members_up": members_up})
    print(f"  local: avg={s['avg_ms']}ms")

    # T4 read concern majority
    print("T4 read concern majority (30 runs)...")
    t4_maj = bench_t4_read_concern(db, conv_id, "majority", runs=30)
    s = calc_stats(t4_maj)
    rows.append({"test_id": "T4", "setting": "readConcern=majority", **s, "members_up": members_up})
    print(f"  majority: avg={s['avg_ms']}ms")

    out_path = os.path.join(RESULTS_DIR, "consistency_test.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "test_id",
                "setting",
                "runs",
                "avg_ms",
                "median_ms",
                "p95_ms",
                "members_up",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    # Calculer les ratios depuis les médianes
    t1_w1_median = next(r["median_ms"] for r in rows if r["test_id"] == "T1" and r["setting"] == "w=1")
    t1_wmaj_median = next(r["median_ms"] for r in rows if r["test_id"] == "T1" and r["setting"] == "w=majority")
    t1_w3_median = next(r["median_ms"] for r in rows if r["test_id"] == "T1" and r["setting"] == "w=3")
    t2_w1_median = next(r["median_ms"] for r in rows if r["test_id"] == "T2" and r["setting"] == "w=1")
    t2_wmaj_median = next(r["median_ms"] for r in rows if r["test_id"] == "T2" and r["setting"] == "w=majority")
    t2_w3_median = next(r["median_ms"] for r in rows if r["test_id"] == "T2" and r["setting"] == "w=3")
    t4_local_median = next(r["median_ms"] for r in rows if r["test_id"] == "T4" and r["setting"] == "readConcern=local")
    t4_maj_median = next(r["median_ms"] for r in rows if r["test_id"] == "T4" and r["setting"] == "readConcern=majority")

    print("\nRatios (basés sur médianes):")
    print(f"  T1 w=majority/w=1: {t1_wmaj_median / t1_w1_median:.2f}x")
    print(f"  T1 w=3/w=1: {t1_w3_median / t1_w1_median:.2f}x")
    print(f"  T2 w=majority/w=1: {t2_wmaj_median / t2_w1_median:.2f}x")
    print(f"  T2 w=3/w=1: {t2_w3_median / t2_w1_median:.2f}x")
    print(f"  T4 majority/local: {t4_maj_median / t4_local_median:.2f}x")

    print(f"\nRésultats écrits dans {out_path}")
    print("Benchmark terminé : replica set à 3 membres.")
    client.close()


if __name__ == "__main__":
    main()