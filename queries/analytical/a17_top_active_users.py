from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed

def run():
    """
    A17: Top utilisés les plus actifs (nombre de messages envoyés)
    Aggregation sur messages avec $group par sender_id, $count, $sort descendante, limit 10
    """
    pass
