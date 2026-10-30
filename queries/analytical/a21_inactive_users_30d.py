from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed

def run():
    """
    A21: Utilisateurs inactifs depuis 30 jours
    Aggregation sur messages avec $group par sender_id, $max created_at, $match $lt vs 30 jours
    """
    pass
