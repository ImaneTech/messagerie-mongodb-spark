from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed

def run(conversation_id=None, user_id=None):
    """
    T13: Compter les messages non lus d'un utilisateur.
    Récupère last_read_ts dans read_status puis count sur messages avec ts > last_read_ts.
    """
    db = get_db()
    read_status = db[COLLECTIONS["read_status"]]
    messages = db[COLLECTIONS["messages"]]
    conversations = db[COLLECTIONS["conversations"]]

    if not conversation_id or not user_id:
        st = read_status.find_one()
        if not st:
            return 0
        conversation_id = st["conversation_id"]
        user_id = st["user_id"]
        last_read = st["last_read_ts"]
    else:
        st = read_status.find_one({"conversation_id": conversation_id, "user_id": user_id})
        last_read = st["last_read_ts"] if st else None

    query = {
        "conversation_id": conversation_id,
        "deleted": False
    }
    if last_read:
        query["ts"] = {"$gt": last_read}

    unread = messages.count_documents(query)
    return unread

if __name__ == "__main__":
    count = run()
    avg_ms = timed(run, runs=5)
    print(f"T13 exécuté : {count} messages non lus trouvés. Temps moyen : {avg_ms:.2f} ms")
