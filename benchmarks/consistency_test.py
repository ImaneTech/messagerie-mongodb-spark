# benchmarks/consistency_test.py
# Test de cohérence : write concern T1/T2, read concern T4.
import sys, os, csv, statistics, time
from datetime import datetime, timezone
from bson import ObjectId
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pymongo import MongoClient, WriteConcern
from pymongo.read_concern import ReadConcern
from pymongo import DESCENDING
from config.settings import MONGO_URI, MONGO_DB, COLLECTIONS

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

def get_members_up():
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        status = client.admin.command("replSetGetStatus")
        members_up = sum(1 for m in status.get("members", []) if m.get("stateStr") in ["PRIMARY", "SECONDARY"])
        client.close()
        return members_up
    except Exception as e:
        print(f"replSetGetStatus error (toléré): {e}")
        return 1

def get_heavy_conv(db):
    pipeline = [
        {"$group": {"_id": "$conversation_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 1}
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
        "ts": datetime.now(timezone.utc).replace(tzinfo=None),
        "deleted": False,
        "_benchmark": True
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
    coll = db[COLLECTIONS["messages"]].with_options(
        read_concern=ReadConcern(level=rc_level)
    )
    for _ in range(runs):
        t0 = time.time()
        list(coll.find({"conversation_id": conv_id, "deleted": False}).sort("ts", DESCENDING).limit(50))
        elapsed = (time.time() - t0) * 1000
        times.append(elapsed)
    return times

def calc_stats(times, n_runs=None):
    n = n_runs or len(times)
    return {
        "runs": n,
        "avg_ms": round(statistics.mean(times), 2),
        "median_ms": round(statistics.median(times), 2),
        "p95_ms": round(sorted(times)[int(len(times) * 0.95)], 2)
    }

def main():
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    members_up = get_members_up()
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
        writer = csv.DictWriter(f, fieldnames=["test_id","setting","runs","avg_ms","median_ms","p95_ms","members_up"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nRésultats écrits dans {out_path}")
    print("IMPORTANT : résultats à relancer quand mongo3 (machine B) sera disponible.")
    client.close()

if __name__ == "__main__":
    main()
