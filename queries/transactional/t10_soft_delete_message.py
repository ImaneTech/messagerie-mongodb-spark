import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from datetime import datetime, timezone
from config.settings import COLLECTIONS
from queries.utils import get_db

# Cache pour restaurer l'état original
_original_state = {}

def run(message_id=None):
    """
    T10: Suppression douce d'un message (marquer comme supprimé).
    Update sur messages avec filter _id, $set deleted=True, content remplacé et timestamp deleted_at.
    Stocke l'état original pour restauration après timing.
    """
    db = get_db()
    messages = db[COLLECTIONS["messages"]]

    if not message_id:
        msg = messages.find_one({"deleted": False, "_benchmark": {"$exists": False}})
        if not msg:
            return 0
        message_id = msg["_id"]
        # Stocker l'état original
        _original_state["message_id"] = message_id
        _original_state["deleted"] = msg.get("deleted", False)
        _original_state["content"] = msg.get("content", "")
        _original_state["deleted_at"] = msg.get("deleted_at", None)

    res = messages.update_one(
        {"_id": message_id},
        {"$set": {
            "deleted": True,
            "content": "Ce message a été supprimé.",
            "deleted_at": datetime.now(timezone.utc).replace(tzinfo=None)
        }}
    )
    return res.modified_count

def cleanup():
    """Restaure le message à son état original (non supprimé)."""
    mid = _original_state.get("message_id")
    if mid:
        db = get_db()
        messages = db[COLLECTIONS["messages"]]
        restore = {
            "deleted": _original_state.get("deleted", False),
            "content": _original_state.get("content", ""),
        }
        if _original_state.get("deleted_at") is not None:
            restore["deleted_at"] = _original_state["deleted_at"]
            messages.update_one({"_id": mid}, {"$set": restore})
        else:
            messages.update_one({"_id": mid}, {"$set": restore, "$unset": {"deleted_at": ""}})


