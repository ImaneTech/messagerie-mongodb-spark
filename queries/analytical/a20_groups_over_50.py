import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config.settings import COLLECTIONS
from queries.utils import get_db


def run():
    """
    A20: Groupes de plus de 50 participants.
    Filtre sur conversations type='group' et participants_count > 50.
    """
    db = get_db()
    conversations = db[COLLECTIONS["conversations"]]

    pipeline = [
        {"$match": {"type": "group", "participants_count": {"$gt": 50}}},
        {"$project": {"name": 1, "participants_count": 1, "created_at": 1}},
        {"$sort": {"participants_count": -1}},
    ]

    return list(conversations.aggregate(pipeline))
