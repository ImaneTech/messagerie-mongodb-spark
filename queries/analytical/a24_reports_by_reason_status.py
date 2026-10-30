from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed

def run():
    """
    A24: Signalements par raison et statut
    Aggregation sur reports avec $group par reason, status, $count
    """
    pass
