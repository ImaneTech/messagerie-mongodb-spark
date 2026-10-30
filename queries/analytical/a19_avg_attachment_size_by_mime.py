from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed

def run():
    """
    A19: Taille moyenne des pièces jointes par type MIME
    Aggregation sur messages avec $match type='attachment', $group par attachments.mime_type, $avg attachments.size
    """
    pass
