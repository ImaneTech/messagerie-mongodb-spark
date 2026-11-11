"""Chargement par lots des données synthétiques dans MongoDB et création des index."""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pymongo import MongoClient

from config.settings import MONGO_DB, MONGO_URI
from data_generator.generate_data import generate_all
from schema.create_indexes import create_indexes


def load_data(
    num_users=10000,
    num_groups=200,
    num_direct=7800,
    target_messages=85000,
    drop=True,
    batch_size=5000,
):
    """
    Génère et insère en masse les données synthétiques dans MongoDB.
    """
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[MONGO_DB]
    print(f"Connexion établie avec la base : '{db.name}'")

    if drop:
        print("Nettoyage des collections existantes...")
        for coll_name in ["users", "conversations", "messages", "read_status", "reports"]:
            db[coll_name].delete_many({})
        print("Collections nettoyées.")

    print(
        f"Génération des données ({num_users} users, {num_groups + num_direct} convs, ~{target_messages} msgs)..."
    )
    start_time = time.time()
    data = generate_all(
        num_users=num_users,
        num_groups=num_groups,
        num_direct=num_direct,
        target_messages=target_messages,
        seed=42,
    )
    gen_duration = time.time() - start_time
    print(f"Données générées en mémoire en {gen_duration:.2f}s.")

    print("Insertion en masse dans MongoDB...")
    insert_start = time.time()

    for coll_name, docs in data.items():
        coll = db[coll_name]
        if not docs:
            continue

        # Ingestion par lots (batching) pour optimiser les performances réseau et mémoire
        total_docs = len(docs)
        for i in range(0, total_docs, batch_size):
            batch = docs[i : i + batch_size]
            coll.insert_many(batch, ordered=False)

        count = coll.count_documents({})
        print(f" - Collection '{coll_name}': {count} documents en base.")

    insert_duration = time.time() - insert_start
    total_duration = time.time() - start_time

    print(f"Insertion terminée en {insert_duration:.2f}s (Durée totale : {total_duration:.2f}s).")

    # S'assurer que les index sont créés et actifs
    print("Vérification des index...")
    create_indexes()

    client.close()
    print("Chargement des données terminé avec succès !")


def main():
    parser = argparse.ArgumentParser(
        description="Chargement des données synthétiques dans MongoDB."
    )
    parser.add_argument("--users", type=int, default=10000, help="Nombre d'utilisateurs")
    parser.add_argument("--groups", type=int, default=200, help="Nombre de groupes")
    parser.add_argument("--direct", type=int, default=7800, help="Nombre de conversations privées")
    parser.add_argument("--messages", type=int, default=85000, help="Nombre cible de messages")
    parser.add_argument(
        "--no-drop", action="store_true", help="Ne pas vider les collections avant insertion"
    )

    args = parser.parse_args()
    load_data(
        num_users=args.users,
        num_groups=args.groups,
        num_direct=args.direct,
        target_messages=args.messages,
        drop=not args.no_drop,
    )


if __name__ == "__main__":
    main()
