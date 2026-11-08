"""Configuration des connexions MongoDB (Replica Set rs0) et de l'environnement."""

import os
from dotenv import load_dotenv

# Chargement du fichier .env à la racine
load_dotenv()

# Adresses IP des deux machines physiques
IP_A = os.getenv("IP_A", "127.0.0.1")
IP_B = os.getenv("IP_B", "127.0.0.1")

# Nom de la base de données
MONGO_DB = os.getenv("MONGO_DB", "chatdb")

# Chaîne de connexion MongoDB Replica Set multi-hôtes
# Permet au driver PyMongo de basculer automatiquement en cas de panne du primaire
MONGO_URI = os.getenv(
    "MONGO_URI",
    f"mongodb://{IP_A}:27017,{IP_A}:27018,{IP_B}:27017/?replicaSet=rs0",
)

# Dictionnaire de référence des 5 collections principales
COLLECTIONS = {
    "users": "users",                  # Profils utilisateurs, contacts et réglages
    "conversations": "conversations",  # Métadonnées des conversations privées et groupes
    "messages": "messages",            # Messages textuels et médias avec horodatage
    "read_status": "read_status",      # Statuts et pointeurs de dernier message lu
    "reports": "reports",              # Signalements d'abus pour modération
}
