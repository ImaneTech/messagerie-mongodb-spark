import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import uuid
from datetime import datetime, timedelta, timezone

from config.settings import COLLECTIONS
from queries.utils import get_db


def run(conversation_id=None, sender_id=None, content="Message éphémère", ttl_seconds=3600):
    """
    T14: Messages éphémères avec TTL (auto-suppression).
    Insert un message avec le champ expire_at (index TTL configuré avec expireAfterSeconds=0).
    Le document est tagué _benchmark=True et supprimé après le timing.
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
        "expire_at": expire_at,
        "_benchmark": True,
    }

    messages.insert_one(doc)
    return doc


def cleanup():
    """Supprime tous les messages éphémères insérés par le benchmark."""
    db = get_db()
    messages = db[COLLECTIONS["messages"]]
    messages.delete_many({"_benchmark": True})
