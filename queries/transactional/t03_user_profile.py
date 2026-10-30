from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed

def run(user_id=None, pseudo=None):
    """
    T03: Consulter le profil utilisateur.
    Récupère un document utilisateur par son user_id ou pseudo depuis la collection users.
    """
    db = get_db()
    users = db[COLLECTIONS["users"]]

    if user_id:
        query = {"_id": user_id}
    elif pseudo:
        query = {"pseudo": pseudo}
    else:
        first = users.find_one({}, {"_id": 1})
        if not first:
            return None
        query = {"_id": first["_id"]}

    profile = users.find_one(query)
    return profile

if __name__ == "__main__":
    prof = run()
    avg_ms = timed(run, runs=5)
    print(f"T03 exécuté : Profil récupéré ({prof.get('pseudo') if prof else 'None'}). Temps moyen : {avg_ms:.2f} ms")
