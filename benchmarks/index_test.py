# benchmarks/index_test.py
# Test d'index pour T4 et T6 : 30 runs avec index, 30 runs avec hint($natural:1), alternés.
import sys, os, csv, statistics, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config.settings import COLLECTIONS
from queries.utils import get_db

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

def get_heavy_conv(db):
    """Retourne la conversation_id avec le plus de messages."""
    pipeline = [
        {"$group": {"_id": "$conversation_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 1}
    ]
    top = list(db[COLLECTIONS["messages"]].aggregate(pipeline))
    return top[0]["_id"] if top else None

def get_heavy_user(db):
    """Retourne le user_id participant au plus de conversations."""
    pipeline = [
        {"$unwind": "$participants"},
        {"$group": {"_id": "$participants.user_id", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gte": 5}}},
        {"$sort": {"count": -1}},
        {"$limit": 1}
    ]
    top = list(db[COLLECTIONS["conversations"]].aggregate(pipeline))
    return top[0]["_id"] if top else None

def explain_query(db, collection_name, query_filter, sort=None, limit=None, hint=None):
    cmd = {"explain": {"find": collection_name, "filter": query_filter}, "verbosity": "executionStats"}
    if sort: cmd["explain"]["sort"] = sort
    if limit: cmd["explain"]["limit"] = limit
    if hint: cmd["explain"]["hint"] = hint
    return db.command(cmd)

def build_stage_chain(plan):
    if not isinstance(plan, dict): return ""
    stage = plan.get("stage", "")
    parts = [stage] if stage else []
    sub = plan.get("inputStage")
    if isinstance(sub, dict):
        child = build_stage_chain(sub)
        if child: parts.append(child)
    subs = plan.get("inputStages")
    if isinstance(subs, list) and subs:
        child = build_stage_chain(subs[0])
        if child: parts.append(child)
    return " > ".join(parts)

def run_timed_query(db, collection_name, query_filter, sort_spec, limit, hint=None):
    """Exécute la requête et retourne (elapsed_ms, nReturned)."""
    coll = db[collection_name]
    cursor = coll.find(query_filter).sort(list(sort_spec.items())).limit(limit)
    if hint:
        cursor = cursor.hint(hint)
    t0 = time.time()
    docs = list(cursor)
    elapsed = (time.time() - t0) * 1000
    return elapsed, len(docs)

def bench(query_id, db, collection_name, query_filter, sort_spec, limit, n_runs=30):
    results = []
    for i in range(n_runs):
        mode = "index" if i % 2 == 0 else "no_index"
        hint = None if mode == "index" else {"$natural": 1}
        elapsed, n_ret = run_timed_query(db, collection_name, query_filter, sort_spec, limit, hint)
        results.append({"mode": mode, "elapsed_ms": elapsed, "n_returned": n_ret})

    # Récupérer explain pour chaque mode
    explain_rows = []
    for mode, hint in [("index", None), ("no_index", {"$natural": 1})]:
        raw = explain_query(db, collection_name, query_filter, sort=sort_spec, limit=limit, hint=hint)
        stats = raw.get("executionStats", {})
        wp = raw.get("queryPlanner", {}).get("winningPlan", {})
        index_times = [r["elapsed_ms"] for r in results if r["mode"] == mode]
        n_returned = results[0]["n_returned"] if results else 0
        explain_rows.append({
            "query_id": query_id,
            "mode": mode,
            "runs": n_runs // 2,
            "avg_ms": round(statistics.mean(index_times), 2),
            "median_ms": round(statistics.median(index_times), 2),
            "p95_ms": round(sorted(index_times)[int(len(index_times) * 0.95)], 2),
            "docs_examined": stats.get("totalDocsExamined", 0),
            "keys_examined": stats.get("totalKeysExamined", 0),
            "n_returned": stats.get("nReturned", n_returned),
            "stage_chain": build_stage_chain(wp)
        })
    return explain_rows

def main():
    db = get_db()

    conv_id = get_heavy_conv(db)
    user_id = get_heavy_user(db)
    print(f"T4 conv_id: {conv_id}")
    print(f"T6 user_id: {user_id}")

    all_rows = []

    # T4 : 50 derniers messages d'une conversation
    print("\nT4 index test (30+30 runs)...")
    rows_t4 = bench(
        "T4", db, COLLECTIONS["messages"],
        {"conversation_id": conv_id, "deleted": False},
        {"ts": -1}, 50
    )
    all_rows.extend(rows_t4)

    # T6 : conversations d'un utilisateur
    print("T6 index test (30+30 runs)...")
    rows_t6 = bench(
        "T6", db, COLLECTIONS["conversations"],
        {"participants.user_id": user_id},
        {"last_message_at": -1}, 20
    )
    all_rows.extend(rows_t6)

    out_path = os.path.join(RESULTS_DIR, "index_test.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["query_id","mode","runs","avg_ms","median_ms","p95_ms","docs_examined","keys_examined","n_returned","stage_chain"])
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nRésultats écrits dans {out_path}")
    for row in all_rows:
        print(f"  {row['query_id']} {row['mode']}: avg={row['avg_ms']}ms, docs={row['docs_examined']}, chain={row['stage_chain']}")

if __name__ == "__main__":
    main()
