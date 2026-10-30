import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import uuid
from datetime import datetime, timezone
from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed, record_benchmark

def run(name="Nouveau Groupe de Discussion", creator_id=None, member_ids=None):
    """
    T07: Créer une conversation de groupe.
    Insert un document dans conversations avec: name, type='group', participants, participants_count, created_at, last_message_at.
    """
    db = get_db()
    conversations = db[COLLECTIONS["conversations"]]
    users = db[COLLECTIONS["users"]]

    if not creator_id:
        sample_users = list(users.find({}, {"_id": 1}).limit(4))
        if len(sample_users) < 2:
            raise ValueError("Pas assez d'utilisateurs pour créer un groupe.")
        creator_id = sample_users[0]["_id"]
        member_ids = [u["_id"] for u in sample_users[1:]]

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    participants = [{"user_id": creator_id, "role": "admin"}]
    for m in (member_ids or []):
        participants.append({"user_id": m, "role": "member"})

    conv_doc = {
        "_id": f"conv_g_{uuid.uuid4().hex[:10]}",
        "type": "group",
        "name": name,
        "participants": participants,
        "participants_count": len(participants),
        "created_at": now,
        "last_message_at": now
    }

    conversations.insert_one(conv_doc)
    return conv_doc

if __name__ == "__main__":
    grp = run()
    avg_ms = timed(run, runs=5)
    record_benchmark("T07", avg_ms, {"description": "Création d'un groupe de discussion"})
    print(f"T07 exécuté : Groupe créé ({grp['_id']}, {grp['name']}). Temps moyen : {avg_ms:.2f} ms")
