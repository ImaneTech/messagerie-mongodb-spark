import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from datetime import datetime, timedelta
from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed, record_benchmark


def run():
    """
    A25: Conversations inactives depuis plus de 7 jours.
    Filtre sur conversations.last_message_at < now - 7 jours.
    """
    db = get_db()
    conversations = db[COLLECTIONS["conversations"]]
    cutoff = datetime.utcnow() - timedelta(days=7)

    pipeline = [
        {"$match": {"last_message_at": {"$lt": cutoff}}},
        {"$project": {
            "_id": 0,
            "conversation_id": "$_id",
            "name": 1,
            "type": 1,
            "last_message_at": 1
        }},
        {"$sort": {"last_message_at": 1}}
    ]

    return list(conversations.aggregate(pipeline))


if __name__ == "__main__":
    res = run()
    avg_ms = timed(run, runs=5)
    record_benchmark("A25", avg_ms, {
        "description": "Conversations inactives depuis 7 jours",
        "idle_count": len(res)
    })
    print(f"A25 exécuté : {len(res)} conversations inactives. Temps moyen : {avg_ms:.2f} ms")
