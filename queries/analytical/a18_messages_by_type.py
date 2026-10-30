from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed

def run():
    """
    A18: Répartition des messages par type (texte, image, vidéo, document)
    Aggregation sur messages avec $group par type, $count
    """
    pass
