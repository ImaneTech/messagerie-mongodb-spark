import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config.settings import COLLECTIONS
from queries.utils import get_db

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


