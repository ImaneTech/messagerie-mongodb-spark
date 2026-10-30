import uuid
from datetime import datetime, timezone, timedelta
from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed

def run(conversation_id=None, sender_id=None, content="Message éphémère", ttl_seconds=3600):
    """
    T14: Messages éphémères avec TTL (auto-suppression).
    Insert un message avec le champ expire_at (index TTL configuré avec expireAfterSeconds=0).
    """
    db = get_db()
    messages = db[COLLECTIONS["messages"]]
    conversations = db[COLLECTIONS["conversations"]]

    if not conversation_id or not sender_id:
        conv = conversations.find_one()
        if not conv:
            return None
        conversation_id = conv["_id"]
        sender_id = conv["participants"][0]["user_id"]

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    expire_at = now + timedelta(seconds=ttl_seconds)

    doc = {
        "_id": f"msg_eph_{uuid.uuid4().hex[:10]}",
        "conversation_id": conversation_id,
        "sender_id": sender_id,
        "ts": now,
        "type": "text",
        "content": content,
        "attachment": None,
        "reactions": [],
        "edited": False,
        "deleted": False,
        "expire_at": expire_at
    }

    messages.insert_one(doc)
    return doc

if __name__ == "__main__":
    msg = run()
    avg_ms = timed(run, runs=5)
    print(f"T14 exécuté : Message éphémère inséré ({msg['_id']}, expire à {msg['expire_at']}). Temps moyen : {avg_ms:.2f} ms")
