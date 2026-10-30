import uuid
from datetime import datetime, timezone
from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed

def run(message_id=None, reporter_id=None, reason="spam"):
    """
    T15: Signaler un message (abus, spam).
    Insert dans reports avec: _id, message_id, reporter_id, reason, status='pending', created_at.
    """
    db = get_db()
    reports = db[COLLECTIONS["reports"]]
    messages = db[COLLECTIONS["messages"]]
    users = db[COLLECTIONS["users"]]

    if not message_id:
        msg = messages.find_one({"deleted": False})
        if not msg:
            return None
        message_id = msg["_id"]

    if not reporter_id:
        u = users.find_one()
        reporter_id = u["_id"] if u else "usr_anonymous"

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    report_doc = {
        "_id": f"rep_{uuid.uuid4().hex[:10]}",
        "message_id": message_id,
        "reporter_id": reporter_id,
        "reason": reason,
        "status": "pending",
        "created_at": now
    }

    reports.insert_one(report_doc)
    return report_doc

if __name__ == "__main__":
    rep = run()
    avg_ms = timed(run, runs=5)
    print(f"T15 exécuté : Signalement enregistré ({rep['_id']}). Temps moyen : {avg_ms:.2f} ms")
