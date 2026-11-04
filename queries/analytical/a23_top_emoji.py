import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config.settings import COLLECTIONS
from queries.utils import get_db


def run(limit=10):
    """
    A23: Top emojis les plus utilisés dans les réactions.
    Aggregation sur messages avec $unwind reactions, $group par emoji, $sort desc.
    """
    db = get_db()
    messages = db[COLLECTIONS["messages"]]

    pipeline = [
        {"$unwind": "$reactions"},
        {"$group": {"_id": "$reactions.emoji", "count": {"$sum": 1}}},
        {"$project": {"emoji": "$_id", "count": 1, "_id": 0}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
    ]

    return list(messages.aggregate(pipeline))
