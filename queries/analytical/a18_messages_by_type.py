import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config.settings import COLLECTIONS
from queries.utils import get_db


def run():
    """
    A18: Répartition des messages par type (text, image, voice, file).
    Aggregation sur messages avec $group par type, $sum.
    """
    db = get_db()
    messages = db[COLLECTIONS["messages"]]

    pipeline = [
        {"$group": {"_id": "$type", "count": {"$sum": 1}}},
        {"$project": {"type": "$_id", "count": 1, "_id": 0}},
        {"$sort": {"count": -1}}
    ]

    return list(messages.aggregate(pipeline))



