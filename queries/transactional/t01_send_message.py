import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import uuid
from datetime import UTC, datetime

from config.settings import COLLECTIONS
from queries.utils import get_db


def run(conversation_id=None, sender_id=None, content="Hello !", msg_type="text", attachment=None):
    """
    T01: Envoyer un message instantané (texte, pièce jointe, réaction).
    Insert un document dans la collection messages et met à jour last_message_at dans conversations.
    Le document est tagué _benchmark=True et supprimé après le timing.
    """
    db = get_db()
    messages = db[COLLECTIONS["messages"]]
    conversations = db[COLLECTIONS["conversations"]]

    if not conversation_id or not sender_id:
        conv = conversations.find_one()
        if not conv:
            raise ValueError("Aucune conversation trouvée en base.")
        conversation_id = conv["_id"]
        sender_id = conv["participants"][0]["user_id"]

    now = datetime.now(UTC).replace(tzinfo=None)
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
        "expire_at": None,
        "_benchmark": True,
    }

    messages.insert_one(doc)
    conversations.update_one({"_id": conversation_id}, {"$set": {"last_message_at": now}})
    return doc


def cleanup():
    """Supprime tous les messages insérés par le benchmark."""
    db = get_db()
    messages = db[COLLECTIONS["messages"]]
    messages.delete_many({"_benchmark": True})
