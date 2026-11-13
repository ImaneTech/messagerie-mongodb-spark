import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from pymongo import DESCENDING

from config.settings import COLLECTIONS
from queries.utils import get_db, select_benchmark_ids


def get_query(conversation_id=None, limit=50):
    db = get_db()
    messages = db[COLLECTIONS["messages"]]

    if not conversation_id:
        conversation_id = select_benchmark_ids(db)[0]

    cursor = (
        messages.find({"conversation_id": conversation_id, "deleted": False})
        .sort("ts", DESCENDING)
        .limit(limit)
    )

    return messages, cursor


def run(conversation_id=None, limit=50):
    """
    T04: Afficher les 50 derniers messages de la conversation la plus chargée.
    Query sur messages avec filter conversation_id, sort ts descendante, limit 50.
    """
    _, cursor = get_query(conversation_id, limit)
    if not cursor:
        return []
    return list(cursor)


def explain_plan(conversation_id=None, limit=50):
    """Exécute et retourne le plan d'exécution explain()."""
    _, cursor = get_query(conversation_id, limit)
    if not cursor:
        return {}
    return cursor.explain()
