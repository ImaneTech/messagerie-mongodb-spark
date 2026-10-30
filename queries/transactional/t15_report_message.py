from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed

def run():
    """
    T15: Signaler un message (abus, spam)
    Insert dans reports avec: reporter_id, message_id, reason, status='pending', created_at
    """
    pass
