import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from datetime import datetime, timedelta

from config.settings import COLLECTIONS
from queries.utils import get_db


def run():
    """
    A21: Utilisateurs inactifs depuis plus de 30 jours.
    Filtre sur users.last_login < now - 30 jours.
    """
    db = get_db()
    users = db[COLLECTIONS["users"]]
    cutoff = datetime.utcnow() - timedelta(days=30)

    pipeline = [
        {"$match": {"last_login": {"$lt": cutoff}}},
        {"$project": {"_id": 0, "user_id": "$_id", "pseudo": 1, "last_login": 1}},
        {"$sort": {"last_login": 1}},
    ]

    return list(users.aggregate(pipeline))
