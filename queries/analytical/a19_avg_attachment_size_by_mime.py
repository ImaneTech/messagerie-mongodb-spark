import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config.settings import COLLECTIONS
from queries.utils import get_db


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



