import os

from dotenv import load_dotenv

load_dotenv()

IP_A = os.getenv("IP_A")
IP_B = os.getenv("IP_B")
MONGO_DB = os.getenv("MONGO_DB", "chatdb")

MONGO_URI = f"mongodb://{IP_A}:27017,{IP_A}:27018,{IP_B}:27017/?replicaSet=rs0"

COLLECTIONS = {
    "users": "users",
    "conversations": "conversations",
    "messages": "messages",
    "read_status": "read_status",
    "reports": "reports",
}
