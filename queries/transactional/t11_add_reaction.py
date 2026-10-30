from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed

def run():
    """
    T11: Ajouter une réaction à un message
    Update sur messages avec filter message_id, $push sur réactions array avec {user_id, emoji, timestamp}
    """
    pass
