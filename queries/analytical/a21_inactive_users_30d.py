import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from datetime import datetime, timedelta
from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed, record_benchmark


def run():
    """
    A21: Utilisateurs inactifs depuis plus de 30 jours.
    Filtre sur users.last_login < now - 30 jours.
    """
    db = get_db()
    users = db[COLLECTIONS["users"]]
    cutoff = datetime.utcnow() - timedelta(days=30)

    pipeline = [
        {"$match": {"last_login": {"$lt": cutoff}}},
        {"$project": {"_id": 0, "user_id": "$_id", "pseudo": 1, "last_login": 1}},
        {"$sort": {"last_login": 1}}
    ]

    return list(users.aggregate(pipeline))


if __name__ == "__main__":
    res = run()
    avg_ms = timed(run, runs=5)
    record_benchmark("A21", avg_ms, {
        "description": "Utilisateurs inactifs depuis 30 jours",
        "inactive_count": len(res)
    })
    print(f"A21 exécuté : {len(res)} utilisateurs inactifs. Temps moyen : {avg_ms:.2f} ms")
