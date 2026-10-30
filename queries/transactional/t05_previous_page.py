from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed

def run():
    """
    T05: Pagination vers l'arrière (page précédente)
    Query sur messages avec filter conversation_id, sort created_at descendante, skip 50, limit 50 pour la page précédente
    """
    pass
