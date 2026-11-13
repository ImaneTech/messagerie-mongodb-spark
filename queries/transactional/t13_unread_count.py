import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config.settings import COLLECTIONS
from queries.utils import get_db

# Cache de la paire de test pour éviter de répéter la recherche dans les benchmarks
_cached_pair = None


def get_test_pair(db):
    global _cached_pair
    if _cached_pair:
        return _cached_pair

    read_status = db[COLLECTIONS["read_status"]]
    messages = db[COLLECTIONS["messages"]]

    # Trouver une paire avec des messages non lus
    for st in read_status.find({"last_read_ts": {"$ne": None}}, limit=50):
        cid = st.get("conversation_id")
        uid = st.get("user_id")
        last_read = st.get("last_read_ts")
        if cid and uid and last_read:
            cnt = messages.count_documents({
                "conversation_id": cid,
                "deleted": False,
                "sender_id": {"$ne": uid},
                "ts": {"$gt": last_read},
            })
            if cnt > 0:
                _cached_pair = (cid, uid)
                return _cached_pair

    # Fallback sur la première entrée disponible
    first = read_status.find_one()
    if first:
        _cached_pair = (first["conversation_id"], first["user_id"])
        return _cached_pair
    return None, None


def run(conversation_id=None, user_id=None):
    """
    T13: Compter les messages non lus d'un utilisateur dans une conversation.
    Exclut les messages supprimés et les messages émis par l'utilisateur lui-même.
    Utilise l'index composé {conversation_id: 1, ts: -1}.
    """
    db = get_db()
    read_status = db[COLLECTIONS["read_status"]]
    messages = db[COLLECTIONS["messages"]]

    if not conversation_id or not user_id:
        conversation_id, user_id = get_test_pair(db)
        if not conversation_id:
            return 0

    st = read_status.find_one({"conversation_id": conversation_id, "user_id": user_id})
    last_read = st.get("last_read_ts") if st else None

    query = {
        "conversation_id": conversation_id,
        "deleted": False,
        "sender_id": {"$ne": user_id},
    }
    if last_read:
        query["ts"] = {"$gt": last_read}

    return messages.count_documents(query)
