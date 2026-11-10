"""Configuration des connexions MongoDB (Replica Set rs0) et de l'environnement."""

import os
from dotenv import load_dotenv

# Chargement du fichier .env à la racine
load_dotenv()

# Nom de la base de données
MONGO_DB = os.getenv("MONGO_DB", "chatdb")

# Chaîne de connexion MongoDB Replica Set multi-hôtes (Docker services internes)
# Utilise les noms de services Docker pour la communication inter-conteneurs
# Permet au driver PyMongo de basculer automatiquement en cas de panne du primaire
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://mongo1:27017,mongo2:27018,mongo3:27019/?replicaSet=rs0&readPreference=primaryPreferred",
)

# Dictionnaire de référence des 5 collections principales
COLLECTIONS = {
    "users": "users",                  # Profils utilisateurs, contacts et réglages
    "conversations": "conversations",  # Métadonnées des conversations privées et groupes
    "messages": "messages",            # Messages textuels et médias avec horodatage
    "read_status": "read_status",      # Statuts et pointeurs de dernier message lu
    "reports": "reports",              # Signalements d'abus pour modération
}
