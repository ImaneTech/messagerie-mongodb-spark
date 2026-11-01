import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from pymongo import DESCENDING
from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed, record_benchmark, extract_index_name

def get_query(user_id=None, limit=20):
    db = get_db()
    conversations = db[COLLECTIONS["conversations"]]
    users = db[COLLECTIONS["users"]]

    if not user_id:
        # Chercher l'utilisateur participant au plus de conversations (>= 5)
        pipeline = [
            {"$unwind": "$participants"},
            {"$group": {"_id": "$participants.user_id", "count": {"$sum": 1}}},
            {"$match": {"count": {"$gte": 5}}},
            {"$sort": {"count": -1}},
            {"$limit": 1}
        ]
        top = list(db[COLLECTIONS["conversations"]].aggregate(pipeline))
        user_id = top[0]["_id"] if top else None
        if top:
            print(f"USER_CHOISI={user_id} NB_CONVERSATIONS={top[0]['count']}")

    cursor = conversations.find(
        {"participants.user_id": user_id}
    ).sort("last_message_at", DESCENDING).limit(limit)

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

if __name__ == "__main__":
    convs = run()
    timing = timed(run, runs=3)
    plan = explain_plan()
    index_name = extract_index_name(plan)

    record_benchmark("T06", timing["avg"], {
        "description": "Lister les conversations d'un utilisateur",
        "index_used": index_name,
        "user_id": str(convs[0]["_id"]) if convs else None
    })
    print(f"T06 exécuté : {len(convs)} conversations trouvées (Index: {index_name}). "
          f"Temps moyen : {timing['avg']:.2f} ms")
