import random
import uuid
from datetime import datetime, timedelta, timezone
from faker import Faker

fake = Faker()

def generate_users(num_users=500, seed=42):
    """
    Génère num_users utilisateurs avec pseudo unique, contacts, réglages et dates de connexion.
    """
    if seed:
        random.seed(seed)
        Faker.seed(seed)

    users = []
    user_ids = [f"usr_{uuid.uuid4().hex[:12]}" for _ in range(num_users)]
    used_pseudos = set()

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    for i, uid in enumerate(user_ids):
        # Pseudo unique
        base_pseudo = fake.user_name()
        pseudo = base_pseudo
        suffix = 1
        while pseudo in used_pseudos:
            pseudo = f"{base_pseudo}_{suffix}"
            suffix += 1
        used_pseudos.add(pseudo)

        # Date de création étalée sur les 6 derniers mois
        days_ago_created = random.randint(30, 180)
        created_at = now - timedelta(days=days_ago_created, seconds=random.randint(0, 86400))

        # Date de dernière connexion (15% inactifs depuis plus de 30 jours pour la requête A21)
        if random.random() < 0.15:
            last_login = created_at + timedelta(days=random.randint(1, max(1, days_ago_created - 31)))
        else:
            last_login = now - timedelta(days=random.randint(0, 20), seconds=random.randint(0, 86400))

        users.append({
            "_id": uid,
            "pseudo": pseudo,
            "phone": fake.phone_number()[:15],
            "country": fake.country_code(),
            "created_at": created_at,
            "contacts": [],  # Rempli après génération de tous les users
            "settings": {
                "notifications": random.choice([True, False]),
                "theme": random.choice(["light", "dark", "system"]),
                "read_receipts": random.choice([True, True, False])
            },
            "last_login": last_login
        })

    # Générer le carnet de contacts (relation réciproque ou orientée)
    for u in users:
        num_contacts = random.randint(3, min(25, num_users - 1))
        possible_contacts = [other["_id"] for other in users if other["_id"] != u["_id"]]
        u["contacts"] = random.sample(possible_contacts, num_contacts)

    return users


def generate_conversations(users, num_groups=50, num_direct=150, seed=42):
    """
    Génère conversations privées (1-to-1) et de groupes (dont certains > 50 membres pour A20).
    """
    if seed:
        random.seed(seed)

    user_ids = [u["_id"] for u in users]
    conversations = []
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # 1. Conversations privées (1-to-1)
    direct_pairs = set()
    while len(conversations) < num_direct:
        u1, u2 = random.sample(user_ids, 2)
        pair_key = tuple(sorted([u1, u2]))
        if pair_key in direct_pairs:
            continue
        direct_pairs.add(pair_key)

        conv_id = f"conv_p_{uuid.uuid4().hex[:10]}"
        created_at = now - timedelta(days=random.randint(10, 150))
        conversations.append({
            "_id": conv_id,
            "type": "private",
            "name": "",
            "participants": [
                {"user_id": u1, "role": "member"},
                {"user_id": u2, "role": "member"}
            ],
            "participants_count": 2,
            "created_at": created_at,
            "last_message_at": created_at  # Sera mis à jour avec les messages
        })

    # 2. Conversations de groupe
    for i in range(num_groups):
        conv_id = f"conv_g_{uuid.uuid4().hex[:10]}"
        # Forcer au moins 6 groupes de plus de 50 participants pour A20
        if i < 7:
            count = random.randint(52, min(75, len(users)))
        else:
            count = random.randint(3, 40)

        group_members = random.sample(user_ids, count)
        participants = [{"user_id": group_members[0], "role": "admin"}]
        for m in group_members[1:]:
            role = "admin" if random.random() < 0.05 else "member"
            participants.append({"user_id": m, "role": role})

        created_at = now - timedelta(days=random.randint(15, 120))
        group_names = [
            f"Projet {fake.word().capitalize()}",
            f"Groupe {fake.city()}",
            f"Club {fake.bs().title()}",
            f"Famille {fake.last_name()}",
            f"Gaming {fake.first_name()}"
        ]

        conversations.append({
            "_id": conv_id,
            "type": "group",
            "name": random.choice(group_names),
            "participants": participants,
            "participants_count": count,
            "created_at": created_at,
            "last_message_at": created_at
        })

    return conversations


def generate_messages(conversations, target_count=10000, seed=42):
    """
    Génère des messages cohérents avec distribution chronologique, pièces jointes, réactions,
    soft delete et messages éphémères (TTL).
    """
    if seed:
        random.seed(seed)
        Faker.seed(seed)

    messages = []
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Types MIME et extensions
    mime_types = {
        "image": [("image/jpeg", "jpg"), ("image/png", "png"), ("image/webp", "webp")],
        "file": [("application/pdf", "pdf"), ("application/zip", "zip"), ("text/plain", "txt")],
        "voice": [("audio/ogg", "ogg"), ("audio/mp4", "m4a")]
    }
    emojis = ["👍", "❤️", "😂", "🔥", "🎉", "👏", "😢", "😮", "🙏", "🚀"]

    msg_types = ["text", "image", "file", "voice"]
    type_weights = [0.70, 0.15, 0.09, 0.06]

    # Répartir les messages entre les conversations (pondéré par taille du groupe)
    weights = [max(2, c["participants_count"]) for c in conversations]
    total_weights = sum(weights)
    msgs_per_conv = [max(3, int(target_count * (w / total_weights))) for w in weights]

    # Pour satisfaire A25 (conversations inactives depuis 7 jours), 15% des conversations s'arrêtent il y a > 7 jours
    idle_conv_indices = set(random.sample(range(len(conversations)), int(len(conversations) * 0.15)))

    for idx, conv in enumerate(conversations):
        n_msgs = msgs_per_conv[idx]
        conv_participants = [p["user_id"] for p in conv["participants"]]

        is_idle = idx in idle_conv_indices
        conv_created = conv["created_at"]

        if is_idle:
            max_ts = now - timedelta(days=random.randint(8, 25))
        else:
            max_ts = now - timedelta(minutes=random.randint(1, 120))

        if max_ts <= conv_created:
            max_ts = conv_created + timedelta(hours=2)

        span_seconds = max(10, int((max_ts - conv_created).total_seconds()))
        step_seconds = span_seconds // max(1, n_msgs)

        current_ts = conv_created

        for m_idx in range(n_msgs):
            current_ts += timedelta(seconds=random.randint(1, max(2, step_seconds * 2)))
            if current_ts > max_ts:
                current_ts = max_ts

            sender_id = random.choice(conv_participants)
            m_type = random.choices(msg_types, weights=type_weights)[0]

            attachment = None
            if m_type != "text":
                mime, ext = random.choice(mime_types[m_type])
                if m_type == "image":
                    size = random.randint(150_000, 3_500_000)
                elif m_type == "voice":
                    size = random.randint(50_000, 800_000)
                else:
                    size = random.randint(200_000, 15_000_000)

                attachment = {
                    "name": f"{fake.word()}_{m_idx}.{ext}",
                    "size": size,
                    "mime": mime
                }

            # Réactions (0 à 4 réactions par message)
            reactions = []
            if random.random() < 0.25:
                other_members = [uid for uid in conv_participants if uid != sender_id]
                if other_members:
                    num_reacts = random.randint(1, min(4, len(other_members)))
                    reactors = random.sample(other_members, num_reacts)
                    for r_uid in reactors:
                        reactions.append({
                            "user_id": r_uid,
                            "emoji": random.choice(emojis)
                        })

            # Messages éphémères (TTL) : 3% des messages
            expire_at = None
            if random.random() < 0.03:
                expire_at = current_ts + timedelta(days=random.randint(1, 7))

            is_deleted = random.random() < 0.02
            is_edited = random.random() < 0.05

            content = fake.sentence(nb_words=random.randint(3, 15)) if not is_deleted else "Ce message a été supprimé."

            msg = {
                "_id": f"msg_{uuid.uuid4().hex[:12]}",
                "conversation_id": conv["_id"],
                "sender_id": sender_id,
                "ts": current_ts,
                "type": m_type,
                "content": content,
                "attachment": attachment,
                "reactions": reactions,
                "edited": is_edited,
                "deleted": is_deleted,
                "expire_at": expire_at
            }
            messages.append(msg)

        # Mettre à jour last_message_at de la conversation
        conv["last_message_at"] = current_ts

    return messages


def generate_read_status(conversations, messages, seed=42):
    """
    Génère l'état de lecture par utilisateur et conversation (read_status).
    """
    if seed:
        random.seed(seed)

    # Indexer le timestamp du dernier message par conversation
    conv_last_ts = {}
    for m in messages:
        cid = m["conversation_id"]
        if cid not in conv_last_ts or m["ts"] > conv_last_ts[cid]:
            conv_last_ts[cid] = m["ts"]

    read_statuses = []
    for conv in conversations:
        cid = conv["_id"]
        latest_ts = conv_last_ts.get(cid, conv["last_message_at"])

        for p in conv["participants"]:
            uid = p["user_id"]
            # 80% des utilisateurs sont à jour sur la conversation, 20% ont du retard (messages non lus pour T13)
            if random.random() < 0.80:
                last_read_ts = latest_ts
            else:
                last_read_ts = latest_ts - timedelta(hours=random.randint(1, 48))

            read_statuses.append({
                "conversation_id": cid,
                "user_id": uid,
                "last_read_ts": last_read_ts
            })

    return read_statuses


def generate_reports(messages, total_reports=120, seed=42):
    """
    Génère des signalements (reports) sur des messages aléatoires pour la modération.
    """
    if seed:
        random.seed(seed)

    reports = []
    reasons = ["spam", "harassment", "inappropriate", "offensive", "scam"]
    statuses = ["pending", "resolved", "dismissed"]

    sampled_messages = random.sample(messages, min(total_reports, len(messages)))

    for m in sampled_messages:
        reports.append({
            "_id": f"rep_{uuid.uuid4().hex[:10]}",
            "message_id": m["_id"],
            "reporter_id": f"usr_mod_{uuid.uuid4().hex[:8]}",
            "reason": random.choice(reasons),
            "status": random.choices(statuses, weights=[0.45, 0.40, 0.15])[0],
            "created_at": m["ts"] + timedelta(minutes=random.randint(1, 180))
        })

    return reports


def generate_all(num_users=500, num_groups=50, num_direct=150, target_messages=10000, seed=42):
    """
    Génère le dataset complet interconnecté pour chatdb.
    """
    users = generate_users(num_users=num_users, seed=seed)
    conversations = generate_conversations(users, num_groups=num_groups, num_direct=num_direct, seed=seed)
    messages = generate_messages(conversations, target_count=target_messages, seed=seed)
    read_statuses = generate_read_status(conversations, messages, seed=seed)
    reports = generate_reports(messages, total_reports=150, seed=seed)

    return {
        "users": users,
        "conversations": conversations,
        "messages": messages,
        "read_status": read_statuses,
        "reports": reports
    }

if __name__ == "__main__":
    data = generate_all()
    print("Génération réussie :")
    for k, v in data.items():
        print(f" - {k}: {len(v)} documents")
