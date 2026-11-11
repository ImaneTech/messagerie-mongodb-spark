"""Configuration des connexions MongoDB (Replica Set rs0) et de l'environnement."""

import os

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

# Target Database Name
MONGO_DB = os.getenv("MONGO_DB") or "chatdb"

# Fixed IP addresses of the 3-VM cluster
IP_A = os.getenv("IP_A") or "192.168.0.100"
IP_B = os.getenv("IP_B") or "192.168.0.101"
IP_C = os.getenv("IP_C") or "192.168.0.102"

# Default Replica Set Connection String
DEFAULT_URI = f"mongodb://{IP_A}:27017,{IP_B}:27017,{IP_C}:27017/{MONGO_DB}?replicaSet=rs0&readPreference=primaryPreferred"

MONGO_URI = os.getenv("MONGO_URI") or DEFAULT_URI

# Dictionnaire de référence des 5 collections principales
COLLECTIONS = {
    "users": "users",                  # Profils utilisateurs, contacts et réglages
    "conversations": "conversations",  # Métadonnées des conversations privées et groupes
    "messages": "messages",            # Messages textuels et médias avec horodatage
    "read_status": "read_status",      # Statuts et pointeurs de dernier message lu
    "reports": "reports",              # Signalements d'abus pour modération
}
