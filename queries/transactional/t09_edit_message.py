import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from datetime import UTC, datetime

from config.settings import COLLECTIONS
from queries.utils import get_db

# Cache pour restaurer l'état original
_original_state = {}


def _get_target():
    db = get_db()
    messages = db[COLLECTIONS["messages"]]
    msg = messages.find_one({"deleted": False, "_benchmark": {"$exists": False}})
    if not msg:
        return None, None
    return db, msg


def run(message_id=None, new_content="Texte mis à jour après édition."):
    """
    T09: Modifier un message existant.
    Update sur messages avec filter _id, $set content, edited=True et ts de modification.
    Stocke l'état original pour restauration après timing.
    """
    db = get_db()
    messages = db[COLLECTIONS["messages"]]

    if not message_id:
        _, msg = _get_target()
        if not msg:
            return 0
        message_id = msg["_id"]
        # Stocker l'état original pour cleanup
        _original_state["message_id"] = message_id
        _original_state["content"] = msg.get("content", "")
        _original_state["edited"] = msg.get("edited", False)
        _original_state["edited_at"] = msg.get("edited_at", None)

    res = messages.update_one(
        {"_id": message_id},
        {
            "$set": {
                "content": new_content,
                "edited": True,
                "edited_at": datetime.now(UTC).replace(tzinfo=None),
            }
        },
    )
    return res.modified_count


def cleanup():
    """Restaure le message à son état original."""
    mid = _original_state.get("message_id")
    if mid:
        db = get_db()
        messages = db[COLLECTIONS["messages"]]
        restore = {
            "content": _original_state.get("content", ""),
            "edited": _original_state.get("edited", False),
        }
        if _original_state.get("edited_at") is not None:
            restore["edited_at"] = _original_state["edited_at"]
        else:
            # Supprimer le champ edited_at s'il n'existait pas
            messages.update_one({"_id": mid}, {"$set": restore, "$unset": {"edited_at": ""}})
            return
        messages.update_one({"_id": mid}, {"$set": restore})
