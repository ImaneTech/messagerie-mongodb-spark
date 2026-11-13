import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from pymongo import DESCENDING

from config.settings import COLLECTIONS
from queries.utils import get_db, select_benchmark_ids


def get_query(user_id=None, limit=20):
    db = get_db()
    conversations = db[COLLECTIONS["conversations"]]

    if not user_id:
        user_id = select_benchmark_ids(db)[1]

    cursor = (
        conversations.find({"participants.user_id": user_id})
        .sort("last_message_at", DESCENDING)
        .limit(limit)
    )

    return conversations, cursor


def run(user_id=None, limit=20):
    """
    T06: Lister les conversations d'un utilisateur dans >= 5 conversations.
    Query sur conversations avec filter participants.user_id, sort last_message_at descendante.
    """
    _, cursor = get_query(user_id, limit)
    if not cursor:
        return []
    return list(cursor)


def explain_plan(user_id=None, limit=20):
    """Exécute et retourne le plan d'exécution explain()."""
    _, cursor = get_query(user_id, limit)
    if not cursor:
        return {}
    return cursor.explain()
