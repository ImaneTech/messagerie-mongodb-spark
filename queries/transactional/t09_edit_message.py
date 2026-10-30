from datetime import datetime, timezone
from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed

def run(message_id=None, new_content="Texte mis à jour après édition."):
    """
    T09: Modifier un message existant.
    Update sur messages avec filter _id, $set content, edited=True et ts de modification.
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
            "content": new_content,
            "edited": True,
            "edited_at": datetime.now(timezone.utc).replace(tzinfo=None)
        }}
    )
    return res.modified_count

if __name__ == "__main__":
    mod = run()
    avg_ms = timed(run, runs=5)
    print(f"T09 exécuté : {mod} message modifié. Temps moyen : {avg_ms:.2f} ms")
