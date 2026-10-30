from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed

def run(conversation_id=None, user_id=None, action="add"):
    """
    T08: Ajouter ou retirer un participant d'un groupe.
    Update sur conversations avec $push ou $pull sur participants et mise à jour de participants_count.
    """
    db = get_db()
    conversations = db[COLLECTIONS["conversations"]]
    users = db[COLLECTIONS["users"]]

    if not conversation_id or not user_id:
        group_conv = conversations.find_one({"type": "group"})
        if not group_conv:
            return None
        conversation_id = group_conv["_id"]
        # Trouver un utilisateur qui n'est pas déjà dans le groupe
        member_ids = {p["user_id"] for p in group_conv["participants"]}
        candidate = users.find_one({"_id": {"$nin": list(member_ids)}})
        if not candidate:
            candidate = users.find_one()
        user_id = candidate["_id"]

    if action == "add":
        res = conversations.update_one(
            {"_id": conversation_id, "participants.user_id": {"$ne": user_id}},
            {
                "$push": {"participants": {"user_id": user_id, "role": "member"}},
                "$inc": {"participants_count": 1}
            }
        )
    else:
        res = conversations.update_one(
            {"_id": conversation_id, "participants.user_id": user_id},
            {
                "$pull": {"participants": {"user_id": user_id}},
                "$inc": {"participants_count": -1}
            }
        )
    return res.modified_count

if __name__ == "__main__":
    added = run(action="add")
    removed = run(action="remove")
    avg_ms = timed(lambda: run(action="add"), runs=3)
    print(f"T08 exécuté : Add={added}, Remove={removed}. Temps moyen : {avg_ms:.2f} ms")
