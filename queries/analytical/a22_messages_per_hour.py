from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed

def run():
    """
    A22: Distribution des messages par heure de la journée
    Aggregation sur messages avec $group par $hour created_at, $count
    """
    pass
