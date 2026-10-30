from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed

def run():
    """
    A23: Top emojis les plus utilisés dans les réactions
    Aggregation sur messages avec $unwind réactions, $group par réactions.emoji, $count, $sort descendante
    """
    pass
