from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed

def run():
    """
    A25: Conversations inactives depuis 7 jours (sans nouveaux messages)
    Aggregation sur conversations avec $lookup last message, $match $lt last_message.created_at vs 7 jours
    """
    pass
