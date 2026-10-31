import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed, record_benchmark


def run(limit=10):
    """
    A23: Top emojis les plus utilisés dans les réactions.
    Aggregation sur messages avec $unwind reactions, $group par emoji, $sort desc.
    """
    db = get_db()
    messages = db[COLLECTIONS["messages"]]

    pipeline = [
        {"$unwind": "$reactions"},
        {"$group": {"_id": "$reactions.emoji", "count": {"$sum": 1}}},
        {"$project": {"emoji": "$_id", "count": 1, "_id": 0}},
        {"$sort": {"count": -1}},
        {"$limit": limit}
    ]

    return list(messages.aggregate(pipeline))


if __name__ == "__main__":
    res = run()
    avg_ms = timed(run, runs=5)
    record_benchmark("A23", avg_ms, {
        "description": "Top 10 emojis dans les réactions",
        "emojis_count": len(res)
    })
    for r in res:
        print(f"  {r['emoji']}: {r['count']}")
    print(f"A23 exécuté : {len(res)} emojis. Temps moyen : {avg_ms:.2f} ms")
