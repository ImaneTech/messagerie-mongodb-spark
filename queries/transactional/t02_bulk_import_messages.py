import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import uuid
from datetime import datetime, timezone, timedelta
from pymongo import InsertOne
from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed, record_benchmark

def run(conversation_id=None, sender_id=None, count=10000):
    """
    T02: Import en masse de messages (bulk insert).
    Insère 10 000 documents messages en une seule opération bulk_write.
    Chaque document est tagué _benchmark=True et supprimé après le timing.
    """
    db = get_db()
    messages = db[COLLECTIONS["messages"]]
    conversations = db[COLLECTIONS["conversations"]]

    if not conversation_id or not sender_id:
        conv = conversations.find_one()
        if not conv:
            raise ValueError("Aucune conversation trouvée.")
        conversation_id = conv["_id"]
        sender_id = conv["participants"][0]["user_id"]

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    operations = []

    for i in range(count):
        msg_id = f"msg_bulk_{uuid.uuid4().hex[:10]}"
        msg_doc = {
            "_id": msg_id,
            "conversation_id": conversation_id,
            "sender_id": sender_id,
            "ts": now + timedelta(seconds=i),
            "type": "text",
            "content": f"Bulk import message #{i}",
            "attachment": None,
            "reactions": [],
            "edited": False,
            "deleted": False,
            "expire_at": None,
            "_benchmark": True
        }
        operations.append(InsertOne(msg_doc))

    result = messages.bulk_write(operations, ordered=False)
    return result.inserted_count

def cleanup():
    """Supprime tous les messages insérés par le benchmark."""
    db = get_db()
    messages = db[COLLECTIONS["messages"]]
    messages.delete_many({"_benchmark": True})

if __name__ == "__main__":
    inserted = run(count=10000)
    cleanup()
    avg_ms = timed(lambda: run(count=10000), runs=3)
    cleanup()
    record_benchmark("T02", avg_ms, {"count": 10000, "description": "Import en masse de 10 000 messages"})
    print(f"T02 exécuté : {inserted} messages insérés via bulk_write. Temps moyen : {avg_ms:.2f} ms")
