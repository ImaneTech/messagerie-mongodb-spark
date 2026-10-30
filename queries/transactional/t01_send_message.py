import uuid
from datetime import datetime, timezone
from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed

def run(conversation_id=None, sender_id=None, content="Hello !", msg_type="text", attachment=None):
    """
    T01: Envoyer un message instantané (texte, pièce jointe, réaction).
    Insert un document dans la collection messages et met à jour last_message_at dans conversations.
    """
    db = get_db()
    messages = db[COLLECTIONS["messages"]]
    conversations = db[COLLECTIONS["conversations"]]

    # Sélection dynamique si non fourni
    if not conversation_id or not sender_id:
        conv = conversations.find_one()
        if not conv:
            raise ValueError("Aucune conversation trouvée en base.")
        conversation_id = conv["_id"]
        sender_id = conv["participants"][0]["user_id"]

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    msg_id = f"msg_{uuid.uuid4().hex[:12]}"

    doc = {
        "_id": msg_id,
        "conversation_id": conversation_id,
        "sender_id": sender_id,
        "ts": now,
        "type": msg_type,
        "content": content,
        "attachment": attachment,
        "reactions": [],
        "edited": False,
        "deleted": False,
        "expire_at": None
    }

    messages.insert_one(doc)
    conversations.update_one(
        {"_id": conversation_id},
        {"$set": {"last_message_at": now}}
    )
    return doc

if __name__ == "__main__":
    res = run()
    avg_ms = timed(run, runs=5)
    print(f"T01 exécuté : Message envoyé ({res['_id']}). Temps moyen : {avg_ms:.2f} ms")
