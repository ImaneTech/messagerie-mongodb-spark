from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed

def run():
    """
    T10: Suppression douce d'un message (marquer comme supprimé
    Update sur messages avec filter message_id, $set deleted=True et deleted_at
    """
    pass
