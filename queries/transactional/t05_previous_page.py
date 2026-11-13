import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from pymongo import DESCENDING

from config.settings import COLLECTIONS
from queries.utils import get_db


def get_query(conversation_id=None, before_ts=None, before_id=None, limit=50):
    db = get_db()
    messages = db[COLLECTIONS["messages"]]
    conversations = db[COLLECTIONS["conversations"]]

    if not conversation_id:
        conv = conversations.find_one()
        if not conv:
            return None, None
        conversation_id = conv["_id"]

    query = {"conversation_id": conversation_id, "deleted": False}
    if before_ts is not None:
        query["$or"] = [{"ts": {"$lt": before_ts}}]
        if before_id is not None:
            query["$or"].append({"ts": before_ts, "_id": {"$lt": before_id}})
    else:
        sample = list(messages.find(query).sort([("ts", DESCENDING), ("_id", DESCENDING)]).limit(1))
        if sample:
            query["$or"] = [
                {"ts": {"$lt": sample[0]["ts"]}},
                {"ts": sample[0]["ts"], "_id": {"$lt": sample[0]["_id"]}},
            ]

    cursor = messages.find(query).sort([("ts", DESCENDING), ("_id", DESCENDING)]).limit(limit)
    return messages, cursor


def run(conversation_id=None, before_ts=None, before_id=None, limit=50):
    """
    T05: Pagination vers l'arrière (page précédente).
    Query sur messages avec keyset pagination: filter conversation_id et ts < before_ts, sort ts descendante, limit 50.
    """
    _, cursor = get_query(conversation_id, before_ts, before_id, limit)
    if not cursor:
        return []
    return list(cursor)


def explain_plan(conversation_id=None, before_ts=None, before_id=None, limit=50):
    """Exécute et retourne le plan d'exécution explain()."""
    _, cursor = get_query(conversation_id, before_ts, before_id, limit)
    if not cursor:
        return {}
    return cursor.explain()
