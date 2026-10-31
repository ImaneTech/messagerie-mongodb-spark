import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed, record_benchmark

def run(start_date=None, end_date=None):
    """
    A16: Nombre de messages par jour sur une période.
    Aggregation sur messages avec $group par $dateToString de ts, $count.
    """
    db = get_db()
    messages = db[COLLECTIONS["messages"]]

    pipeline = []
    if start_date or end_date:
        match_filter = {}
        if start_date:
            match_filter["$gte"] = start_date
        if end_date:
            match_filter["$lte"] = end_date
        pipeline.append({"$match": {"ts": match_filter}})

    pipeline.extend([
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
    ])

    return list(messages.aggregate(pipeline))

if __name__ == "__main__":
    res = run()
    avg_ms = timed(run, runs=5)
    record_benchmark("A16", avg_ms, {
        "description": "Nombre de messages par jour",
        "days_aggregated": len(res)
    })
    print(f"A16 exécuté : {len(res)} jours agrégés. Temps moyen : {avg_ms:.2f} ms")
