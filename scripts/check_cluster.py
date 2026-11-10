"""
scripts/check_cluster.py
Vérification d'état complet de l'infrastructure multi-machines :
1. Santé des 3 membres du Replica Set MongoDB (rs0), détection du Primaire et des Secondaires.
2. État du cluster Apache Spark (Master ALIVE, nombre de Workers connectés, cœurs et RAM).
"""

import sys
import urllib.request
import json
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from config.settings import MONGO_URI, MONGO_DB


def check_mongodb():
    print("=" * 60)
    print("1. VÉRIFICATION DU REPLICA SET MONGODB (rs0)")
    print("=" * 60)
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=4000)
        status = client.admin.command("replSetGetStatus")
        set_name = status.get("set", "inconnu")
        print(f"Replica Set : {set_name}")
        
        primary_found = False
        healthy_count = 0
        for m in status.get("members", []):
            name = m.get("name")
            state = m.get("stateStr")
            health = m.get("health")
            uptime = m.get("uptime", 0)
            if state == "PRIMARY":
                primary_found = True
            if health == 1:
                healthy_count += 1
            print(f"  • {name:<18} État: {state:<12} Santé: {health} (uptime: {uptime}s)")

        if healthy_count == 3 and primary_found:
            print(f"[OK] Replica Set optimal : 3/3 membres en ligne avec un Primaire actif.")
            return True
        else:
            print(f"[ATTENTION] État dégradé : {healthy_count}/3 membres en ligne. Primaire trouvé: {primary_found}")
            return False
    except PyMongoError as e:
        print(f"[ERREUR] Connexion MongoDB impossible via {MONGO_URI} : {e}")
        return False


def check_spark():
    print("\n" + "=" * 60)
    print("2. VÉRIFICATION DU CLUSTER APACHE SPARK")
    print("=" * 60)
    url = "http://localhost:18080/json/"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            status = data.get("status", "INCONNU")
            workers = data.get("workers", [])
            alive_workers = [w for w in workers if w.get("state") == "ALIVE"]
            total_cores = sum(w.get("cores", 0) for w in alive_workers)
            total_memory = sum(w.get("memory", 0) for w in alive_workers)

            print(f"Statut Master : {status}")
            print(f"Workers actifs : {len(alive_workers)} (Total cœurs: {total_cores}, RAM: {total_memory} MB)")
            for w in alive_workers:
                wid = w.get("id", "")
                waddr = w.get("address", "")
                wcores = w.get("cores", 0)
                wmem = w.get("memory", 0)
                print(f"  • Worker {waddr:<22} Cœurs: {wcores}  RAM: {wmem} MB  (id: {wid[:20]}...)")

            if len(alive_workers) >= 2:
                print(f"[OK] Cluster Spark prêt : {len(alive_workers)} workers ALIVE connectés.")
                return True
            else:
                print(f"[ATTENTION] Nombre de workers insuffisant : {len(alive_workers)}/2 attendus.")
                return False
    except Exception as e:
        print(f"[INFO] Master Spark Web UI non joignable à {url} : {e}")
        print("Vérifiez que le conteneur spark-master est démarré sur la machine A.")
        return False


if __name__ == "__main__":
    mongo_ok = check_mongodb()
    spark_ok = check_spark()
    print("\n" + "=" * 60)
    print(f"RÉSUMÉ : MongoDB={'OK' if mongo_ok else 'KO'} | Spark={'OK' if spark_ok else 'KO'}")
    print("=" * 60)
    sys.exit(0 if (mongo_ok and spark_ok) else 1)
