import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from datetime import datetime, timezone
from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed, record_benchmark

def run(message_id=None):
    """
    T10: Suppression douce d'un message (marquer comme supprimé).
    Update sur messages avec filter _id, $set deleted=True, content remplacé et timestamp deleted_at.
    """
    db = get_db()
    messages = db[COLLECTIONS["messages"]]

    if not message_id:
        msg = messages.find_one({"deleted": False})
        if not msg:
            return 0
        message_id = msg["_id"]

    res = messages.update_one(
        {"_id": message_id},
        {"$set": {
            "deleted": True,
            "content": "Ce message a été supprimé.",
            "deleted_at": datetime.now(timezone.utc).replace(tzinfo=None)
        }}
    )
    return res.modified_count

if __name__ == "__main__":
    count = run()
    avg_ms = timed(run, runs=5)
    record_benchmark("T10", avg_ms, {"description": "Suppression douce (soft delete)"})
    print(f"T10 exécuté : {count} message supprimé logiquement. Temps moyen : {avg_ms:.2f} ms")
