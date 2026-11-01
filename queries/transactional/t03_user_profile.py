import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from config.settings import COLLECTIONS
from queries.utils import get_db

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


