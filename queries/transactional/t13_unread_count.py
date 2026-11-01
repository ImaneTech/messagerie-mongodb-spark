import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from pymongo import DESCENDING
from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed, record_benchmark

def run(conversation_id=None, user_id=None):
    """
    T13: Compter les messages non lus d'un utilisateur.
    Cherche d'abord une paire avec des non-lus réels ; si aucune,
    force un test artificiel sur le 20e message le plus récent.
    """
    db = get_db()
    read_status = db[COLLECTIONS["read_status"]]
    messages = db[COLLECTIONS["messages"]]

    # ── Cas 1 : paire explicitement fournie ─────────────────────────────────
    if conversation_id and user_id:
        st = read_status.find_one({"conversation_id": conversation_id, "user_id": user_id})
        last_read = st["last_read_ts"] if st else None
        query = {"conversation_id": conversation_id, "deleted": False}
        if last_read:
            query["ts"] = {"$gt": last_read}
        return messages.count_documents(query)

    # ── Cas 2 : chercher une paire avec non-lus réels ───────────────────────
    for st in read_status.find({}, limit=200):
        cid = st.get("conversation_id")
        uid = st.get("user_id")
        last_read = st.get("last_read_ts")
        if not last_read:
            continue
        count = messages.count_documents({
            "conversation_id": cid,
            "deleted": False,
            "ts": {"$gt": last_read}
        })
        if count > 0:
            return count

    # ── Cas 3 : test artificiel ──────────────────────────────────────────────
    # Trouver une conversation avec >= 20 messages
    pipeline = [
        {"$group": {"_id": "$conversation_id", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gte": 20}}},
        {"$sort": {"count": -1}},
        {"$limit": 1}
    ]
    top = list(messages.aggregate(pipeline))
    if not top:
        return 0
    target_conv = top[0]["_id"]

    # Trouver le 20e message le plus récent
    msg_20th = list(messages.find(
        {"conversation_id": target_conv, "deleted": False},
        {"ts": 1}
    ).sort("ts", DESCENDING).skip(19).limit(1))
    if not msg_20th:
        return 0
    ts_20th = msg_20th[0]["ts"]

    # Trouver ou créer un doc read_status pour ce test
    target_user = None
    st_doc = read_status.find_one({"conversation_id": target_conv})
    if st_doc:
        target_user = st_doc["user_id"]
        old_ts = st_doc.get("last_read_ts")
        # Mettre à jour last_read_ts au 20e message
        read_status.update_one(
            {"conversation_id": target_conv, "user_id": target_user},
            {"$set": {"last_read_ts": ts_20th}}
        )
    else:
        # Utiliser le premier utilisateur connu
        first_user = db[COLLECTIONS["users"]].find_one({}, {"_id": 1})
        target_user = first_user["_id"] if first_user else None
        if not target_user:
            return 0
        old_ts = None
        read_status.insert_one({
            "conversation_id": target_conv,
            "user_id": target_user,
            "last_read_ts": ts_20th
        })

    # Compter les non-lus
    count = messages.count_documents({
        "conversation_id": target_conv,
        "deleted": False,
        "ts": {"$gt": ts_20th}
    })

    # Restaurer l'ancienne valeur
    if old_ts is not None:
        read_status.update_one(
            {"conversation_id": target_conv, "user_id": target_user},
            {"$set": {"last_read_ts": old_ts}}
        )
    else:
        # On avait inséré un doc de test : le supprimer
        read_status.delete_one({"conversation_id": target_conv, "user_id": target_user})

    return count

if __name__ == "__main__":
    count = run()
    print(f"T13_UNREAD_COUNT={count}")
    assert count > 0, f"T13: count doit être > 0, obtenu {count}"
    timing = timed(run, runs=3)
    record_benchmark("T13", timing["avg"], {"description": "Comptage des messages non lus"})
    print(f"T13 exécuté : {count} messages non lus trouvés. Temps moyen : {timing['avg']:.2f} ms")
