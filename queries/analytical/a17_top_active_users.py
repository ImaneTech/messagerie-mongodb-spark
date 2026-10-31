import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed, record_benchmark

def run(limit=10):
    """
    A17: Top utilisateurs les plus actifs (nombre de messages envoyés).
    Aggregation sur messages avec $group par sender_id, $sort descendante, limit 10, $lookup sur users.
    """
    db = get_db()
    messages = db[COLLECTIONS["messages"]]

    pipeline = [
        {
            "$group": {
                "_id": "$sender_id",
                "message_count": {"$sum": 1}
            }
        },
        {"$sort": {"message_count": -1}},
        {"$limit": limit},
        {
            "$lookup": {
                "from": COLLECTIONS["users"],
                "localField": "_id",
                "foreignField": "_id",
                "as": "user_info"
            }
        },
        {
            "$project": {
                "user_id": "$_id",
                "pseudo": {"$arrayElemAt": ["$user_info.pseudo", 0]},
                "message_count": 1,
                "_id": 0
            }
        }
    ]

    return list(messages.aggregate(pipeline))

if __name__ == "__main__":
    res = run()
    avg_ms = timed(run, runs=5)
    record_benchmark("A17", avg_ms, {
        "description": "Top 10 utilisateurs actifs",
        "top_users_count": len(res)
    })
    print(f"A17 exécuté : Top {len(res)} utilisateurs actifs récupérés. Temps moyen : {avg_ms:.2f} ms")
