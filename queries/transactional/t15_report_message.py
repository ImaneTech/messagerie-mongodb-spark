import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import uuid
from datetime import datetime, timezone

from config.settings import COLLECTIONS
from queries.utils import get_db


def run(message_id=None, reporter_id=None, reason="spam"):
    """
    T15: Signaler un message (abus, spam).
    Insert dans reports avec: _id, message_id, reporter_id, reason, status='pending', created_at.
    Le document est tagué _benchmark=True et supprimé après le timing.
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
        "created_at": now,
        "_benchmark": True,
    }

    reports.insert_one(report_doc)
    return report_doc


def cleanup():
    """Supprime tous les rapports insérés par le benchmark."""
    db = get_db()
    reports = db[COLLECTIONS["reports"]]
    reports.delete_many({"_benchmark": True})
