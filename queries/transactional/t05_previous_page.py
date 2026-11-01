import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from pymongo import DESCENDING
from config.settings import COLLECTIONS
from queries.utils import get_db

def get_query(conversation_id=None, before_ts=None, limit=50):
    db = get_db()
    messages = db[COLLECTIONS["messages"]]
    conversations = db[COLLECTIONS["conversations"]]

    if not conversation_id:
        conv = conversations.find_one()
        if not conv:
            return None, None
        conversation_id = conv["_id"]

    query = {"conversation_id": conversation_id, "deleted": False}
    if before_ts:
        query["ts"] = {"$lt": before_ts}
    else:
        sample = list(messages.find(query).sort("ts", DESCENDING).skip(10).limit(1))
        if sample:
            query["ts"] = {"$lt": sample[0]["ts"]}

    cursor = messages.find(query).sort("ts", DESCENDING).limit(limit)
    return messages, cursor

def run(conversation_id=None, before_ts=None, limit=50):
    """
    T05: Pagination vers l'arrière (page précédente).
    Query sur messages avec keyset pagination: filter conversation_id et ts < before_ts, sort ts descendante, limit 50.
    """
    _, cursor = get_query(conversation_id, before_ts, limit)
    if not cursor:
        return []
    return list(cursor)

def explain_plan(conversation_id=None, before_ts=None, limit=50):
    """Exécute et retourne le plan d'exécution explain()."""
    _, cursor = get_query(conversation_id, before_ts, limit)
    if not cursor:
        return {}
    return cursor.explain()


