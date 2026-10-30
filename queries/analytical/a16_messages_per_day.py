from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed

def run():
    """
    A16: Nombre de messages par jour sur une période
    Aggregation sur messages avec $group par $dateToString created_at, $count
    """
    pass
