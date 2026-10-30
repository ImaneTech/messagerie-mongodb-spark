from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed

def run():
    """
    T14: Messages éphémères avec TTL (auto-suppression)
    Insert message avec expiresAt field, ou createIndex sur messages avec expireAfterSeconds
    """
    pass
