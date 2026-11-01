import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from datetime import datetime, timedelta, timezone
from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed, record_benchmark

def run(start_date=None, end_date=None):
    """
    A16: Nombre de messages par jour sur les 30 derniers jours.
    Toujours filtrer sur ts >= now - 30 jours avant le $group.
    """
    db = get_db()
    messages = db[COLLECTIONS["messages"]]

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start_30d = now - timedelta(days=30)

    # Le filtre 30 jours est toujours appliqué, start_date/end_date peuvent
    # restreindre davantage mais pas au-delà de 30 jours.
    match_filter = {"ts": {"$gte": start_30d}}
    if start_date and start_date > start_30d:
        match_filter["ts"]["$gte"] = start_date
    if end_date:
        match_filter["ts"]["$lte"] = end_date

    pipeline = [
        {"$match": match_filter},
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$ts"
                    }
                },
                "total_messages": {"$sum": 1}
            }
        },
        {"$sort": {"_id": 1}}
    ]

    return list(messages.aggregate(pipeline))

if __name__ == "__main__":
    res = run()
    total_msgs = sum(r["total_messages"] for r in res)
    print(f"A16 buckets={len(res)} total_messages={total_msgs}")
    timing = timed(run, runs=3)
    record_benchmark("A16", timing["avg"], {
        "description": "Nombre de messages par jour (30 derniers jours)",
        "buckets": len(res),
        "total_messages": total_msgs
    })
    print(f"A16 exécuté : {len(res)} buckets, {total_msgs} messages au total. "
          f"Temps moyen : {timing['avg']:.2f} ms")
