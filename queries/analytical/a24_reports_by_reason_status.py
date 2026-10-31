import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed, record_benchmark


def run():
    """
    A24: Signalements par raison et statut.
    Aggregation sur reports avec $group par {reason, status}, $sum.
    """
    db = get_db()
    reports = db[COLLECTIONS["reports"]]

    pipeline = [
        {"$group": {
            "_id": {"reason": "$reason", "status": "$status"},
            "count": {"$sum": 1}
        }},
        {"$project": {
            "reason": "$_id.reason",
            "status": "$_id.status",
            "count": 1,
            "_id": 0
        }},
        {"$sort": {"count": -1}}
    ]

    return list(reports.aggregate(pipeline))


if __name__ == "__main__":
    res = run()
    avg_ms = timed(run, runs=5)
    record_benchmark("A24", avg_ms, {
        "description": "Signalements par raison et statut",
        "combinations": len(res)
    })
    for r in res:
        print(f"  {r['reason']} / {r['status']}: {r['count']}")
    print(f"A24 exécuté : {len(res)} combinaisons. Temps moyen : {avg_ms:.2f} ms")
