"""
scripts/init_replica_set.py
Initialisation et vérification du Replica Set rs0 depuis Python (PyMongo).
Applique la priorité 2 à mongo1 pour garantir son statut de Primaire.
"""

import sys
import time
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from config.settings import MONGO_URI, MONGO_DB


def init_replica_set():
    print("Connexion au cluster MongoDB...")
    try:
        # Connexion directe à mongo1 pour l'initialisation
        client = MongoClient("mongodb://127.0.0.1:27017/?directConnection=true", serverSelectionTimeoutMS=5000)
        admin = client.admin
    except Exception as e:
        print(f"[ERREUR] Impossible de joindre mongo1 en direct : {e}")
        return False

    config = {
        "_id": "rs0",
        "members": [
            {"_id": 0, "host": "mongo1:27017", "priority": 2},
            {"_id": 1, "host": "mongo2:27018", "priority": 1},
            {"_id": 2, "host": "mongo3:27019", "priority": 1},
        ],
    }

    try:
        status = admin.command("replSetGetStatus")
        print("[INFO] Replica Set déjà initialisé. Membres actuels :")
        for m in status.get("members", []):
            print(f"  - {m['name']} : {m['stateStr']} (health={m['health']})")
    except PyMongoError:
        print("[INFO] Initialisation initiale du Replica Set rs0...")
        try:
            admin.command("replSetInitiate", config)
            print("[OK] Commande replSetInitiate exécutée avec succès.")
        except Exception as e:
            print(f"[ERREUR] Échec de replSetInitiate : {e}")
            return False

    # Attente de la stabilisation du Primaire
    print("Vérification de l'élection du Primaire...")
    for _ in range(15):
        try:
            hello = admin.command("hello")
            if hello.get("isWritablePrimary"):
                print(f"[OK] Nœud primaire confirmé : {hello.get('primary', 'mongo1')}")
                return True
        except Exception:
            pass
        time.sleep(1)

    print("[WARN] Le primaire n'a pas été confirmé dans le délai imparti.")
    return True


if __name__ == "__main__":
    success = init_replica_set()
    sys.exit(0 if success else 1)
