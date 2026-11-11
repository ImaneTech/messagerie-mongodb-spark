"""Configuration des connexions MongoDB (Replica Set rs0) et de l'environnement."""

import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Target Database Name
MONGO_DB = os.getenv("MONGO_DB", "chatdb")

# IP Configurations
IP_A = os.getenv("IP_A", "192.168.0.100")
IP_B = os.getenv("IP_B", "192.168.0.101")
IP_C = os.getenv("IP_C", "192.168.0.102")

# Default Replica Set Connection String
DEFAULT_URI = f"mongodb://{IP_A}:27017,{IP_B}:27017,{IP_C}:27017/{MONGO_DB}?replicaSet=rs0&readPreference=primaryPreferred"

MONGO_URI = os.getenv("MONGO_URI", DEFAULT_URI)

# Dictionnaire de référence des 5 collections principales
COLLECTIONS = {
    "users": "users",                  # Profils utilisateurs, contacts et réglages
    "conversations": "conversations",  # Métadonnées des conversations privées et groupes
    "messages": "messages",            # Messages textuels et médias avec horodatage
    "read_status": "read_status",      # Statuts et pointeurs de dernier message lu
    "reports": "reports",              # Signalements d'abus pour modération
}
