from datetime import datetime, timezone
from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed

def run(conversation_id=None, user_id=None, last_read_ts=None):
    """
    T12: Marquer une conversation comme lue.
    Upsert sur read_status avec conversation_id, user_id, last_read_ts.
    """
    db = get_db()
    read_status = db[COLLECTIONS["read_status"]]
    conversations = db[COLLECTIONS["conversations"]]

    if not conversation_id or not user_id:
        conv = conversations.find_one()
        if not conv:
            return 0
        conversation_id = conv["_id"]
        user_id = conv["participants"][0]["user_id"]

    if not last_read_ts:
        last_read_ts = datetime.now(timezone.utc).replace(tzinfo=None)

    res = read_status.update_one(
        {"conversation_id": conversation_id, "user_id": user_id},
        {"$set": {"last_read_ts": last_read_ts}},
        upsert=True
    )
    return res.modified_count or (1 if res.upserted_id else 0)

if __name__ == "__main__":
    count = run()
    avg_ms = timed(run, runs=5)
    print(f"T12 exécuté : Curseur de lecture mis à jour. Temps moyen : {avg_ms:.2f} ms")
