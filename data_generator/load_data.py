import time
import argparse
from queries.utils import get_db
from data_generator.generate_data import generate_users, generate_conversations, generate_messages, generate_read_status, generate_reports
from schema.create_indexes import create_indexes

def load_data(num_users=10000, num_groups=200, num_direct=7800, target_messages=85000, drop=True, batch_size=5000):
    """
    Génère et insère en masse les données synthétiques dans MongoDB.
    """
    db = get_db()
    print(f"Connexion établie avec la base : '{db.name}'")

    if drop:
        print("Nettoyage des collections existantes...")
        for coll_name in ["users", "conversations", "messages", "read_status", "reports"]:
            db[coll_name].delete_many({})
        print("Collections nettoyées.")

    print(f"Génération des données ({num_users} users, {num_groups + num_direct} convs, ~{target_messages} msgs)...")
    start_time = time.time()
    users = generate_users(num_users=num_users, seed=42)
    conversations = generate_conversations(users, num_groups=num_groups, num_direct=num_direct, seed=42)
    messages = generate_messages(conversations, users, target_count=target_messages, seed=42)
    read_statuses = generate_read_status(conversations, messages, seed=42)
    reports = generate_reports(messages, total_reports=1200, seed=42)
    data = {
        "users": users,
        "conversations": conversations,
        "messages": messages,
        "read_status": read_statuses,
        "reports": reports
    }
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
            batch = docs[i:i + batch_size]
            coll.insert_many(batch, ordered=False)

        count = coll.count_documents({})
        print(f" - Collection '{coll_name}': {count} documents en base.")

    insert_duration = time.time() - insert_start
    total_duration = time.time() - start_time

    print(f"Insertion terminée en {insert_duration:.2f}s (Durée totale : {total_duration:.2f}s).")

    # S'assurer que les index sont créés et actifs
    print("Vérification des index...")
    create_indexes()

    print("Chargement des données terminé avec succès !")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chargement des données synthétiques dans MongoDB.")
    parser.add_argument("--users", type=int, default=10000, help="Nombre d'utilisateurs")
    parser.add_argument("--groups", type=int, default=200, help="Nombre de groupes")
    parser.add_argument("--direct", type=int, default=7800, help="Nombre de conversations privées")
    parser.add_argument("--messages", type=int, default=85000, help="Nombre cible de messages")
    parser.add_argument("--no-drop", action="store_true", help="Ne pas vider les collections avant insertion")

    args = parser.parse_args()
    load_data(
        num_users=args.users,
        num_groups=args.groups,
        num_direct=args.direct,
        target_messages=args.messages,
        drop=not args.no_drop
    )
