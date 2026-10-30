from pymongo import DESCENDING
from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed

def run(user_id=None, limit=20):
    """
    T06: Lister les conversations d'un utilisateur.
    Query sur conversations avec filter participants.user_id, sort last_message_at descendante.
    """
    db = get_db()
    conversations = db[COLLECTIONS["conversations"]]
    users = db[COLLECTIONS["users"]]

    if not user_id:
        u = users.find_one()
        if not u:
            return []
        user_id = u["_id"]

    cursor = conversations.find(
        {"participants.user_id": user_id}
    ).sort("last_message_at", DESCENDING).limit(limit)

    return list(cursor)

if __name__ == "__main__":
    convs = run()
    avg_ms = timed(run, runs=5)
    print(f"T06 exécuté : {len(convs)} conversations trouvées. Temps moyen : {avg_ms:.2f} ms")
