import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed, record_benchmark


def run():
    """
    A20: Groupes de plus de 50 participants.
    Filtre sur conversations type='group' et participants_count > 50.
    """
    db = get_db()
    conversations = db[COLLECTIONS["conversations"]]

    pipeline = [
        {"$match": {"type": "group", "participants_count": {"$gt": 50}}},
        {"$project": {
            "name": 1,
            "participants_count": 1,
            "created_at": 1
        }},
        {"$sort": {"participants_count": -1}}
    ]

    return list(conversations.aggregate(pipeline))


if __name__ == "__main__":
    res = run()
    avg_ms = timed(run, runs=5)
    record_benchmark("A20", avg_ms, {
        "description": "Groupes de plus de 50 participants",
        "groups_found": len(res)
    })
    for r in res:
        print(f"  {r.get('name', '?')}: {r['participants_count']} participants")
    print(f"A20 exécuté : {len(res)} groupes trouvés. Temps moyen : {avg_ms:.2f} ms")
