import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from datetime import datetime, timezone
from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed, record_benchmark

# Cache pour restaurer l'état original
_original_state = {}

def run(conversation_id=None, user_id=None, last_read_ts=None):
    """
    T12: Marquer une conversation comme lue.
    Upsert sur read_status avec conversation_id, user_id, last_read_ts.
    Stocke l'état original pour restauration après timing.
    """
    db = get_db()
    read_status = db[COLLECTIONS["read_status"]]
    conversations = db[COLLECTIONS["conversations"]]

    if not conversation_id or not user_id:
        # Utiliser un document read_status existant
        st = read_status.find_one()
        if not st:
            conv = conversations.find_one()
            if not conv:
                return 0
            conversation_id = conv["_id"]
            user_id = conv["participants"][0]["user_id"]
            _original_state["existed"] = False
            _original_state["conversation_id"] = conversation_id
            _original_state["user_id"] = user_id
        else:
            conversation_id = st["conversation_id"]
            user_id = st["user_id"]
            _original_state["existed"] = True
            _original_state["conversation_id"] = conversation_id
            _original_state["user_id"] = user_id
            _original_state["last_read_ts"] = st.get("last_read_ts")

    if not last_read_ts:
        last_read_ts = datetime.now(timezone.utc).replace(tzinfo=None)

    res = read_status.update_one(
        {"conversation_id": conversation_id, "user_id": user_id},
        {"$set": {"last_read_ts": last_read_ts}},
        upsert=True
    )
    return res.modified_count or (1 if res.upserted_id else 0)

def cleanup():
    """Restaure le document read_status à son état original."""
    cid = _original_state.get("conversation_id")
    uid = _original_state.get("user_id")
    if cid and uid:
        db = get_db()
        read_status = db[COLLECTIONS["read_status"]]
        if _original_state.get("existed"):
            original_ts = _original_state.get("last_read_ts")
            if original_ts:
                read_status.update_one(
                    {"conversation_id": cid, "user_id": uid},
                    {"$set": {"last_read_ts": original_ts}}
                )
        else:
            # Le document a été créé par upsert, le supprimer
            read_status.delete_one({"conversation_id": cid, "user_id": uid})

if __name__ == "__main__":
    count = run()
    cleanup()
    avg_ms = timed(run, runs=5)
    cleanup()
    record_benchmark("T12", avg_ms, {"description": "Marquer une conversation comme lue"})
    print(f"T12 exécuté : Curseur de lecture mis à jour. Temps moyen : {avg_ms:.2f} ms")
