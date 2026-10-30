from pymongo import DESCENDING
from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed

def run(conversation_id=None, limit=50):
    """
    T04: Afficher les 50 derniers messages d'une conversation.
    Query sur messages avec filter conversation_id, sort ts descendante, limit 50.
    """
    db = get_db()
    messages = db[COLLECTIONS["messages"]]
    conversations = db[COLLECTIONS["conversations"]]

    if not conversation_id:
        conv = conversations.find_one()
        if not conv:
            return []
        conversation_id = conv["_id"]

    cursor = messages.find(
        {"conversation_id": conversation_id, "deleted": False}
    ).sort("ts", DESCENDING).limit(limit)

    return list(cursor)

if __name__ == "__main__":
    msgs = run()
    avg_ms = timed(run, runs=5)
    print(f"T04 exécuté : {len(msgs)} messages récupérés. Temps moyen : {avg_ms:.2f} ms")
