from config.settings import MONGO_DB, COLLECTIONS
from queries.utils import get_db, timed

def run():
    """
    T01: Envoyer un message instantané (texte, pièce jointe, réaction)
    Insert un document dans la collection messages avec les champs: sender_id, conversation_id, content, type, attachments, réactions, created_at
    """
    pass
