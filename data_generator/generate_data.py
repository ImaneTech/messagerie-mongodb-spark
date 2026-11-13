"""Génération du jeu de données de test (utilisateurs, conversations, messages, statuts, reports)."""

import random
import uuid
from datetime import UTC, datetime, timedelta

from faker import Faker

fake = Faker()


def generate_users(num_users=10000, seed=42):
    """
    Génère num_users utilisateurs avec pseudo unique, contacts, réglages et dates de connexion.
    Les inscriptions sont étalées sur les 6 derniers mois (180 jours).
    """
    if seed:
        random.seed(seed)
        Faker.seed(seed)

    users = []
    user_ids = [f"usr_{uuid.uuid4().hex[:12]}" for _ in range(num_users)]
    used_pseudos = set()

    now = datetime.now(UTC).replace(tzinfo=None)

    for i, uid in enumerate(user_ids):
        # Pseudo unique
        base_pseudo = fake.user_name()
        pseudo = base_pseudo
        suffix = 1
        while pseudo in used_pseudos:
            pseudo = f"{base_pseudo}_{suffix}"
            suffix += 1
        used_pseudos.add(pseudo)

        # created_at étalé sur 6 mois (entre -180 jours et -30 jours)
        days_ago_created = random.randint(30, 180)
        created_at = now - timedelta(days=days_ago_created, seconds=random.randint(0, 86400))

        # last_login : 15 % inactifs depuis > 30 jours (pour A21)
        if random.random() < 0.15:
            inactive_days = random.randint(31, max(32, days_ago_created - 1))
            last_login = now - timedelta(days=inactive_days)
        else:
            last_login = now - timedelta(
                days=random.randint(0, 20), seconds=random.randint(0, 86400)
            )

        users.append(
            {
                "_id": uid,
                "pseudo": pseudo,
                "phone": fake.phone_number()[:15],
                "country": fake.country_code(),
                "created_at": created_at,
                "contacts": [],  # rempli ci-dessous
                "settings": {
                    "notifications": random.choice([True, False]),
                    "theme": random.choice(["light", "dark", "system"]),
                    "read_receipts": random.choice([True, True, False]),
                },
                "last_login": last_login,
            }
        )

    # Carnet de contacts (orienté)
    for u in users:
        num_contacts = random.randint(3, min(25, num_users - 1))
        possible = [other["_id"] for other in users if other["_id"] != u["_id"]]
        u["contacts"] = random.sample(possible, num_contacts)

    # S27 : clique de 200 utilisateurs avec beaucoup de contacts communs
    clique_users = random.sample(users, min(200, len(users)))
    clique_ids = [u["_id"] for u in clique_users]
    for u in clique_users:
        for other_id in clique_ids:
            if other_id != u["_id"] and other_id not in u["contacts"]:
                u["contacts"].append(other_id)

    return users


def generate_conversations(users, num_groups=200, num_direct=7800, seed=42):
    """
    Génère conversations privées (1-to-1) et de groupe.
    """
    if seed:
        random.seed(seed)

    user_ids = [u["_id"] for u in users]
    conversations = []
    now = datetime.now(UTC).replace(tzinfo=None)

    # 1. Conversations privées
    direct_pairs = set()
    while len(conversations) < num_direct:
        u1, u2 = random.sample(user_ids, 2)
        pair_key = tuple(sorted([u1, u2]))
        if pair_key in direct_pairs:
            continue
        direct_pairs.add(pair_key)

        conv_id = f"conv_p_{uuid.uuid4().hex[:10]}"
        created_at = now - timedelta(days=random.randint(10, 180))
        conversations.append(
            {
                "_id": conv_id,
                "type": "private",
                "name": "",
                "participants": [
                    {"user_id": u1, "role": "member"},
                    {"user_id": u2, "role": "member"},
                ],
                "participants_count": 2,
                "created_at": created_at,
                "last_message_at": created_at,
            }
        )

    # 2. Groupes
    for i in range(num_groups):
        conv_id = f"conv_g_{uuid.uuid4().hex[:10]}"
        # Au moins 7 groupes de > 50 participants (pour A20)
        if i < 7 and len(user_ids) >= 52:
            count = random.randint(52, min(75, len(user_ids)))
        else:
            count = random.randint(1, min(40, len(user_ids)))
        group_members = random.sample(user_ids, count)
        participants = [{"user_id": group_members[0], "role": "admin"}]
        for m in group_members[1:]:
            role = "admin" if random.random() < 0.05 else "member"
            participants.append({"user_id": m, "role": role})

        created_at = now - timedelta(days=random.randint(15, 180))
        group_name = random.choice(
            [
                f"Projet {fake.word().capitalize()}",
                f"Groupe {fake.city()}",
                f"Club {fake.bs().title()}",
                f"Famille {fake.last_name()}",
                f"Gaming {fake.first_name()}",
            ]
        )
        conversations.append(
            {
                "_id": conv_id,
                "type": "group",
                "name": group_name,
                "participants": participants,
                "participants_count": count,
                "created_at": created_at,
                "last_message_at": created_at,
            }
        )

    return conversations


def generate_messages(conversations, users, target_count=85000, seed=42):
    """
    Génère des messages cohérents avec distribution chronologique, pièces jointes, réactions,
    soft delete et messages éphémères (TTL).
    Contrainte : ts >= created_at de l'expéditeur.
    """
    if seed:
        random.seed(seed)
        Faker.seed(seed)

    messages = []
    now = datetime.now(UTC).replace(tzinfo=None)

    # Index created_at par user_id pour vérification rapide
    user_created = {u["_id"]: u["created_at"] for u in users}

    # Types MIME et extensions
    mime_types = {
        "image": [("image/jpeg", "jpg"), ("image/png", "png"), ("image/webp", "webp")],
        "file": [("application/pdf", "pdf"), ("application/zip", "zip"), ("text/plain", "txt")],
        "voice": [("audio/ogg", "ogg"), ("audio/mp4", "m4a")],
    }
    emojis = ["👍", "❤️", "😂", "🔥", "🎉", "👏", "😢", "😮", "🙏", "🚀"]

    msg_types = ["text", "image", "file", "voice"]
    type_weights = [0.70, 0.15, 0.09, 0.06]

    # Répartir les messages entre les conversations (pondéré par taille du groupe)
    weights = [max(2, c["participants_count"]) for c in conversations]
    total_weights = sum(weights)
    msgs_per_conv = [max(3, int(target_count * (w / total_weights))) for w in weights]

    # A25 : 15 % des conversations inactives depuis > 7 jours
    idle_conv_indices = set(
        random.sample(range(len(conversations)), int(len(conversations) * 0.15))
    )
    # 10 % des conversations ont des messages dans les dernières 24 h
    active_pool = [i for i in range(len(conversations)) if i not in idle_conv_indices]
    recent_conv_indices = set(random.sample(active_pool, int(len(conversations) * 0.10)))

    for idx, conv in enumerate(conversations):
        n_msgs = msgs_per_conv[idx]
        conv_participants = [p["user_id"] for p in conv["participants"]]
        conv_created = conv["created_at"]

        is_idle = idx in idle_conv_indices
        is_recent = idx in recent_conv_indices

        if is_idle:
            max_ts = now - timedelta(days=random.randint(8, 25))
        elif is_recent:
            max_ts = now - timedelta(minutes=random.randint(1, 60))
        else:
            max_ts = now - timedelta(days=random.randint(1, 6))

        if max_ts <= conv_created:
            max_ts = conv_created + timedelta(hours=2)

        span_seconds = max(10, int((max_ts - conv_created).total_seconds()))
        step_seconds = span_seconds // max(1, n_msgs)

        current_ts = conv_created

        for m_idx in range(n_msgs):
            current_ts += timedelta(seconds=random.randint(1, max(2, step_seconds * 2)))
            current_ts = min(current_ts, max_ts)

            sender_id = random.choice(conv_participants)

            # Contrainte S30 : ts >= created_at de l'expéditeur
            sender_min_ts = user_created.get(sender_id, conv_created)
            if current_ts < sender_min_ts:
                current_ts = sender_min_ts + timedelta(seconds=random.randint(1, 3600))

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
                attachment = {"name": f"{fake.word()}_{m_idx}.{ext}", "size": size, "mime": mime}

            reactions = []
            if random.random() < 0.25:
                other_members = [uid for uid in conv_participants if uid != sender_id]
                if other_members:
                    num_reacts = random.randint(1, min(4, len(other_members)))
                    reactors = random.sample(other_members, num_reacts)
                    for r_uid in reactors:
                        reactions.append({"user_id": r_uid, "emoji": random.choice(emojis)})

            # Messages éphémères (TTL) : 3 % des messages, expire dans le futur
            expire_at = None
            if random.random() < 0.03:
                expire_at = now + timedelta(days=random.randint(1, 7))

            is_deleted = random.random() < 0.02
            is_edited = random.random() < 0.05

            content = (
                fake.sentence(nb_words=random.randint(3, 15))
                if not is_deleted
                else "Ce message a été supprimé."
            )

            messages.append(
                {
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
                    "expire_at": expire_at,
                }
            )

        # Mettre à jour last_message_at de la conversation
        conv["last_message_at"] = current_ts

    # ── S28 : spam ─────────────────────────────────────────────────────────
    # Même contenu, mêmes expéditeurs, >20 conversations distinctes en 1 heure
    spam_contents = [
        "OFFRE SPÉCIALE ! Cliquez ici pour gagner !",
        "Promotion exclusive réservée aux membres VIP !",
        "Gagnez 500€ maintenant, inscrivez-vous vite !",
    ]
    spam_senders = random.sample([u["_id"] for u in users], min(10, len(users)))
    spam_hour_start = now - timedelta(hours=12)

    for spam_content in spam_contents:
        for sender in spam_senders:
            # Chaque spam_sender envoie le même contenu dans 25 conversations différentes
            spam_convs = random.sample(conversations, min(25, len(conversations)))
            for conv in spam_convs:
                spam_ts = spam_hour_start + timedelta(minutes=random.randint(0, 55))
                sender_min_ts = user_created.get(sender, spam_hour_start)
                if spam_ts < sender_min_ts:
                    spam_ts = sender_min_ts + timedelta(minutes=1)
                messages.append(
                    {
                        "_id": f"msg_{uuid.uuid4().hex[:12]}",
                        "conversation_id": conv["_id"],
                        "sender_id": sender,
                        "ts": spam_ts,
                        "type": "text",
                        "content": spam_content,
                        "attachment": None,
                        "reactions": [],
                        "edited": False,
                        "deleted": False,
                        "expire_at": None,
                    }
                )

    # ── S26 : réponses rapides (back-and-forth) dans conversations privées ──
    # Pour chaque conversation cible, insérer 12 messages alternés espacés de 5 s
    private_convs = [c for c in conversations if c["type"] == "private"]
    quick_conv_ids = random.sample([c["_id"] for c in private_convs], min(200, len(private_convs)))

    for conv_id in quick_conv_ids:
        conv = next(c for c in conversations if c["_id"] == conv_id)
        participants = [p["user_id"] for p in conv["participants"]]
        # base_ts doit être >= created_at des deux participants pour éviter gap=0
        p0_min = user_created.get(participants[0], now - timedelta(days=180))
        p1_min = user_created.get(participants[1], now - timedelta(days=180))
        base_min = max(p0_min, p1_min) + timedelta(seconds=1)
        raw_base = now - timedelta(hours=random.randint(1, 6))
        base_ts = max(raw_base, base_min)

        for i in range(12):
            sender = participants[i % 2]
            # Pas strictement croissant de 5s — aucune collision possible
            quick_ts = base_ts + timedelta(seconds=i * 5)
            sender_min_ts = user_created.get(sender, base_ts)
            if quick_ts < sender_min_ts:
                # Décaler toute la séquence
                base_ts = sender_min_ts + timedelta(seconds=1)
                quick_ts = base_ts + timedelta(seconds=i * 5)
            messages.append(
                {
                    "_id": f"msg_{uuid.uuid4().hex[:12]}",
                    "conversation_id": conv_id,
                    "sender_id": sender,
                    "ts": quick_ts,
                    "type": "text",
                    "content": fake.sentence(nb_words=random.randint(2, 8)),
                    "attachment": None,
                    "reactions": [],
                    "edited": False,
                    "deleted": False,
                    "expire_at": None,
                }
            )

    return messages


def generate_read_status(conversations, messages, seed=42):
    """
    Génère l'état de lecture par utilisateur et conversation (read_status).
    """
    if seed:
        random.seed(seed)

    conv_last_ts = {}
    conv_messages = {}
    for m in messages:
        cid = m["conversation_id"]
        if cid not in conv_last_ts or m["ts"] > conv_last_ts[cid]:
            conv_last_ts[cid] = m["ts"]
        if cid not in conv_messages:
            conv_messages[cid] = []
        conv_messages[cid].append(m)

    read_statuses = []
    for conv in conversations:
        cid = conv["_id"]
        c_msgs = conv_messages.get(cid, [])
        latest_ts = conv_last_ts.get(cid, conv["last_message_at"])
        for p in conv["participants"]:
            uid = p["user_id"]
            if random.random() < 0.80 or not c_msgs:
                last_read_ts = latest_ts
                last_msg_id = c_msgs[-1]["_id"] if c_msgs else None
            else:
                last_read_ts = latest_ts - timedelta(hours=random.randint(1, 48))
                read_subset = [m["_id"] for m in c_msgs if m["ts"] <= last_read_ts]
                last_msg_id = read_subset[-1] if read_subset else (c_msgs[0]["_id"] if c_msgs else None)

            read_statuses.append(
                {
                    "conversation_id": cid,
                    "user_id": uid,
                    "last_read_ts": last_read_ts,
                    "last_read_msg_id": last_msg_id,  # Conforme spécification ENSAJ §3.2
                }
            )

    return read_statuses


def generate_reports(messages, total_reports=1200, seed=42):
    """
    Génère des signalements sur des messages aléatoires.
    """
    if seed:
        random.seed(seed)

    reports = []
    reasons = ["spam", "harassment", "inappropriate", "offensive", "scam"]
    statuses = ["pending", "resolved", "dismissed"]

    all_senders = list({m["sender_id"] for m in messages})

    sampled_messages = random.sample(messages, min(total_reports, len(messages)))

    for m in sampled_messages:
        reporter_id = random.choice([u for u in all_senders if u != m["sender_id"]])
        reports.append(
            {
                "_id": f"rep_{uuid.uuid4().hex[:10]}",
                "message_id": m["_id"],
                "reporter_id": reporter_id,
                "reason": random.choice(reasons),
                "status": random.choices(statuses, weights=[0.45, 0.40, 0.15])[0],
                "created_at": m["ts"] + timedelta(minutes=random.randint(1, 180)),
            }
        )

    return reports


def generate_all(num_users=10000, num_groups=200, num_direct=7800, target_messages=85000, seed=42):
    """
    Génère le dataset complet interconnecté pour chatdb.
    """
    users = generate_users(num_users=num_users, seed=seed)
    conversations = generate_conversations(
        users, num_groups=num_groups, num_direct=num_direct, seed=seed
    )
    messages = generate_messages(conversations, users, target_count=target_messages, seed=seed)
    read_statuses = generate_read_status(conversations, messages, seed=seed)
    reports = generate_reports(messages, total_reports=1200, seed=seed)

    return {
        "users": users,
        "conversations": conversations,
        "messages": messages,
        "read_status": read_statuses,
        "reports": reports,
    }


def main():
    data = generate_all()
    print("Génération réussie :")
    for k, v in data.items():
        print(f" - {k}: {len(v)} documents")


if __name__ == "__main__":
    main()
