import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed, record_benchmark

# Cache pour restaurer l'état original
_original_state = {}

def run(message_id=None, user_id=None, emoji="🔥"):
    """
    T11: Ajouter une réaction à un message.
    Update sur messages avec filter _id, $push sur reactions array avec {user_id, emoji}.
    Stocke l'état original pour restauration après timing.
    """
    db = get_db()
    messages = db[COLLECTIONS["messages"]]
    users = db[COLLECTIONS["users"]]

    if not message_id or not user_id:
        msg = messages.find_one({"deleted": False, "_benchmark": {"$exists": False}})
        u = users.find_one()
        if not msg or not u:
            return 0
        message_id = msg["_id"]
        user_id = u["_id"]
        # Stocker l'état original des reactions
        _original_state["message_id"] = message_id
        _original_state["user_id"] = user_id
        _original_state["reactions"] = list(msg.get("reactions", []))

    res = messages.update_one(
        {"_id": message_id},
        {"$push": {"reactions": {"user_id": user_id, "emoji": emoji}}}
    )
    return res.modified_count

def cleanup():
    """Restaure le tableau reactions à son état original."""
    mid = _original_state.get("message_id")
    if mid:
        db = get_db()
        messages = db[COLLECTIONS["messages"]]
        messages.update_one(
            {"_id": mid},
            {"$set": {"reactions": _original_state.get("reactions", [])}}
        )

if __name__ == "__main__":
    count = run()
    cleanup()
    avg_ms = timed(run, runs=5)
    cleanup()
    record_benchmark("T11", avg_ms, {"description": "Ajout d'une réaction emoji"})
    print(f"T11 exécuté : {count} réaction ajoutée. Temps moyen : {avg_ms:.2f} ms")
