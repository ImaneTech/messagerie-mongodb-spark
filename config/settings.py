"""Configuration fixe du Replica Set MongoDB du cluster à trois VMs."""

MONGO_DB = "chatdb"
IP_A = "192.168.0.100"
IP_B = "192.168.0.101"
IP_C = "192.168.0.102"
MONGO_URI = (
    f"mongodb://{IP_A}:27017,{IP_B}:27017,{IP_C}:27017/"
    f"{MONGO_DB}?replicaSet=rs0&readPreference=primaryPreferred"
)

# Dictionnaire de référence des 5 collections principales
COLLECTIONS = {
    "users": "users",                  # Profils utilisateurs, contacts et réglages
    "conversations": "conversations",  # Métadonnées des conversations privées et groupes
    "messages": "messages",            # Messages textuels et médias avec horodatage
    "read_status": "read_status",      # Statuts et pointeurs de dernier message lu
    "reports": "reports",              # Signalements d'abus pour modération
}
