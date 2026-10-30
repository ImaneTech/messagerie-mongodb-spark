from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed

def run(message_id=None, user_id=None, emoji="🔥"):
    """
    T11: Ajouter une réaction à un message.
    Update sur messages avec filter _id, $push sur reactions array avec {user_id, emoji}.
    """
    db = get_db()
    messages = db[COLLECTIONS["messages"]]
    users = db[COLLECTIONS["users"]]

    if not message_id or not user_id:
        msg = messages.find_one({"deleted": False})
        u = users.find_one()
        if not msg or not u:
            return 0
        message_id = msg["_id"]
        user_id = u["_id"]

    res = messages.update_one(
        {"_id": message_id},
        {"$push": {"reactions": {"user_id": user_id, "emoji": emoji}}}
    )
    return res.modified_count

if __name__ == "__main__":
    count = run()
    avg_ms = timed(run, runs=5)
    print(f"T11 exécuté : {count} réaction ajoutée. Temps moyen : {avg_ms:.2f} ms")
