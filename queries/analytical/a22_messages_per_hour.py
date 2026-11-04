import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config.settings import COLLECTIONS
from queries.utils import get_db


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
        {"$sort": {"hour": 1}},
    ]

    return list(messages.aggregate(pipeline))
