import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config.settings import COLLECTIONS
from queries.utils import get_db

# Cache pour les IDs utilisés dans le bench (pour pouvoir restaurer)
_bench_state = {}


def run(conversation_id=None, user_id=None, action="add"):
    """
    T08: Ajouter ou retirer un participant d'un groupe.
    Update sur conversations avec $push ou $pull sur participants et mise à jour de participants_count.
    Le bench fait add puis remove pour rester réversible.
    """
    db = get_db()
    conversations = db[COLLECTIONS["conversations"]]
    users = db[COLLECTIONS["users"]]

    if not conversation_id or not user_id:
        group_conv = conversations.find_one({"type": "group"})
        if not group_conv:
            return None
        conversation_id = group_conv["_id"]
        member_ids = {p["user_id"] for p in group_conv["participants"]}
        candidate = users.find_one({"_id": {"$nin": list(member_ids)}})
        if not candidate:
            candidate = users.find_one()
        user_id = candidate["_id"]

    _bench_state["conversation_id"] = conversation_id
    _bench_state["user_id"] = user_id

    if action == "add":
        res = conversations.update_one(
            {"_id": conversation_id, "participants.user_id": {"$ne": user_id}},
            {
                "$push": {"participants": {"user_id": user_id, "role": "member"}},
                "$inc": {"participants_count": 1},
            },
        )
    else:
        res = conversations.update_one(
            {"_id": conversation_id, "participants.user_id": user_id},
            {"$pull": {"participants": {"user_id": user_id}}, "$inc": {"participants_count": -1}},
        )
    return res.modified_count


def cleanup():
    """Retire le participant ajouté par le benchmark (opération réversible)."""
    cid = _bench_state.get("conversation_id")
    uid = _bench_state.get("user_id")
    if cid and uid:
        db = get_db()
        conversations = db[COLLECTIONS["conversations"]]
        conversations.update_one(
            {"_id": cid, "participants.user_id": uid},
            {"$pull": {"participants": {"user_id": uid}}, "$inc": {"participants_count": -1}},
        )


def run_bench():
    """Benchmark : add seulement (cleanup retire ensuite)."""
    return run(action="add")
