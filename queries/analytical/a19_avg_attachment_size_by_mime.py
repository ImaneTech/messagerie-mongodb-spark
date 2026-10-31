import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed, record_benchmark


def run():
    """
    A19: Taille moyenne des pièces jointes par type MIME.
    Aggregation sur messages avec $match attachment exists, $group par attachment.mime, $avg attachment.size.
    """
    db = get_db()
    messages = db[COLLECTIONS["messages"]]

    pipeline = [
        {"$match": {"attachment": {"$exists": True}}},
        {"$group": {
            "_id": "$attachment.mime",
            "avg_size": {"$avg": "$attachment.size"},
            "count": {"$sum": 1}
        }},
        {"$project": {"mime": "$_id", "avg_size": {"$round": ["$avg_size", 2]}, "count": 1, "_id": 0}},
        {"$sort": {"count": -1}}
    ]

    return list(messages.aggregate(pipeline))


if __name__ == "__main__":
    res = run()
    avg_ms = timed(run, runs=5)
    record_benchmark("A19", avg_ms, {
        "description": "Taille moyenne des pièces jointes par MIME",
        "mime_types": len(res)
    })
    for r in res:
        print(f"  {r['mime']}: avg={r['avg_size']} octets, n={r['count']}")
    print(f"A19 exécuté : {len(res)} types MIME. Temps moyen : {avg_ms:.2f} ms")
