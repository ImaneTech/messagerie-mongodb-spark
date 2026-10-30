from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError
from config.settings import MONGO_URI, MONGO_DB

def create_indexes():
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        db = client[MONGO_DB]

        indexes = {
            "users": [
                ([("pseudo", ASCENDING)], {"unique": True, "name": "idx_users_pseudo_unique"}),
                ([("last_login", ASCENDING)], {"name": "idx_users_last_login"}),
                ([("created_at", ASCENDING)], {"name": "idx_users_created_at"})
            ],
            "conversations": [
                ([("participants.user_id", ASCENDING), ("last_message_at", DESCENDING)], {"name": "idx_conversations_user_last_msg"}),
                ([("type", ASCENDING), ("participants_count", DESCENDING)], {"name": "idx_conversations_type_count"}),
                ([("last_message_at", ASCENDING)], {"name": "idx_conversations_last_message_at"})
            ],
            "messages": [
                ([("conversation_id", ASCENDING), ("ts", DESCENDING)], {"name": "idx_messages_conv_ts"}),
                ([("sender_id", ASCENDING), ("ts", DESCENDING)], {"name": "idx_messages_sender_ts"}),
                ([("ts", ASCENDING)], {"name": "idx_messages_ts"}),
                ([("expire_at", ASCENDING)], {
                    "expireAfterSeconds": 0,
                    "partialFilterExpression": {"expire_at": {"$exists": True}},
                    "name": "idx_messages_expire_at_ttl"
                })
            ],
            "read_status": [
                ([("conversation_id", ASCENDING), ("user_id", ASCENDING)], {"unique": True, "name": "idx_read_status_conv_user_unique"})
            ],
            "reports": [
                ([("reason", ASCENDING), ("status", ASCENDING)], {"name": "idx_reports_reason_status"}),
                ([("message_id", ASCENDING)], {"name": "idx_reports_message_id"})
            ]
        }

        print(f"Connexion réussie à MongoDB ({MONGO_DB}). Création des index...")
        for coll_name, coll_indexes in indexes.items():
            coll = db[coll_name]
            for keys, kwargs in coll_indexes:
                coll.create_index(keys, **kwargs)
            current_indexes = [idx["name"] for idx in coll.list_indexes()]
            print(f"Collection '{coll_name}': {current_indexes}")

        return True

    except (ServerSelectionTimeoutError, PyMongoError) as e:
        print(f"Erreur de connexion / Réplica Set : {e}")
        return False

if __name__ == "__main__":
    create_indexes()
