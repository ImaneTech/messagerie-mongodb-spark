import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed, record_benchmark


def run():
    """
    A22: Distribution des messages par heure de la journée.
    Aggregation sur messages avec $hour de ts, $group, $sort.
    """
    db = get_db()
    messages = db[COLLECTIONS["messages"]]

    pipeline = [
        {"$project": {"hour": {"$hour": "$ts"}}},
        {"$group": {"_id": "$hour", "count": {"$sum": 1}}},
        {"$project": {"hour": "$_id", "count": 1, "_id": 0}},
        {"$sort": {"hour": 1}}
    ]

    return list(messages.aggregate(pipeline))


if __name__ == "__main__":
    res = run()
    avg_ms = timed(run, runs=5)
    record_benchmark("A22", avg_ms, {
        "description": "Messages par heure de la journée",
        "hours_count": len(res)
    })
    for r in res:
        print(f"  {r['hour']:02d}h : {r['count']} messages")
    print(f"A22 exécuté : {len(res)} tranches horaires. Temps moyen : {avg_ms:.2f} ms")
