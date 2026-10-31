import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed, record_benchmark, extract_index_name


def run():
    """
    A18: Répartition des messages par type (text, image, voice, file).
    Aggregation sur messages avec $group par type, $sum.
    """
    db = get_db()
    messages = db[COLLECTIONS["messages"]]

    pipeline = [
        {"$group": {"_id": "$type", "count": {"$sum": 1}}},
        {"$project": {"type": "$_id", "count": 1, "_id": 0}},
        {"$sort": {"count": -1}}
    ]

    return list(messages.aggregate(pipeline))


if __name__ == "__main__":
    res = run()
    avg_ms = timed(run, runs=5)
    record_benchmark("A18", avg_ms, {
        "description": "Répartition des messages par type",
        "types_count": len(res)
    })
    for r in res:
        print(f"  {r['type']}: {r['count']}")
    print(f"A18 exécuté : {len(res)} types. Temps moyen : {avg_ms:.2f} ms")
