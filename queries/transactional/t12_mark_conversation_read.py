from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed

def run():
    """
    T12: Marquer une conversation comme lue
    Upsert sur read_status avec user_id, conversation_id, last_read_message_id, last_read_at
    """
    pass
