import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from pymongo import DESCENDING
from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed, record_benchmark, extract_index_name

def get_query(conversation_id=None, limit=50):
    db = get_db()
    messages = db[COLLECTIONS["messages"]]
    conversations = db[COLLECTIONS["conversations"]]

    if not conversation_id:
        conv = conversations.find_one()
        if not conv:
            return None, None
        conversation_id = conv["_id"]

    cursor = messages.find(
        {"conversation_id": conversation_id, "deleted": False}
    ).sort("ts", DESCENDING).limit(limit)

    return messages, cursor

def run(conversation_id=None, limit=50):
    """
    T04: Afficher les 50 derniers messages d'une conversation.
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

if __name__ == "__main__":
    msgs = run()
    avg_ms = timed(run, runs=5)
    plan = explain_plan()
    index_name = extract_index_name(plan)

    record_benchmark("T04", avg_ms, {
        "description": "50 derniers messages d'une conversation",
        "index_used": index_name
    })
    print(f"T04 exécuté : {len(msgs)} messages récupérés (Index: {index_name}). Temps moyen : {avg_ms:.2f} ms")
