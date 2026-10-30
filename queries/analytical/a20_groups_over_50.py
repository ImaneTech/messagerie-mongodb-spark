from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed

def run():
    """
    A20: Groupes de plus de 50 participants
    Query sur conversations avec filter type='group', $expr $size participant_ids > 50
    """
    pass
