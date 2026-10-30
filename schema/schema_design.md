# Conception du Schéma et Stratégie d'Indexation (chatdb)

Ce document présente la modélisation des données pour l'application de messagerie instantanée distribuée sous MongoDB (`chatdb`), ainsi que la justification des choix de modélisation (embarquement vs référence) et la cartographie complète des index et des 30 requêtes du sujet.

---

## 1. Schéma des Collections et Exemples de Documents

La base de données `chatdb` est structurée en 5 collections principales : `users`, `conversations`, `messages`, `read_status`, et `reports`.

### 1.1 Collection `users`
Stocke les profils utilisateurs, leur liste de contacts et leurs préférences.
```json
{
  "_id": "usr_7f8a9b1c2d",
  "pseudo": "alice_dev",
  "phone": "+33612345678",
  "country": "FR",
  "created_at": "2026-01-15T09:30:00Z",
  "contacts": [
    "usr_8a9b0c1d2e",
    "usr_9b0c1d2e3f"
  ],
  "settings": {
    "notifications": true,
    "theme": "dark",
    "read_receipts": true
  },
  "last_login": "2026-10-30T18:45:12Z"
}
```

### 1.2 Collection `conversations`
Gère les métadonnées des canaux privés (1-to-1) et des groupes.
```json
{
  "_id": "conv_99a88b77c6",
  "type": "group",
  "name": "Équipe Big Data",
  "participants": [
    {"user_id": "usr_7f8a9b1c2d", "role": "admin"},
    {"user_id": "usr_8a9b0c1d2e", "role": "member"},
    {"user_id": "usr_9b0c1d2e3f", "role": "member"}
  ],
  "participants_count": 3,
  "created_at": "2026-03-01T10:00:00Z",
  "last_message_at": "2026-10-30T20:15:30Z"
}
```

### 1.3 Collection `messages`
Enregistre les messages textuels et multimédias avec historique des réactions.
```json
{
  "_id": "msg_0011223344",
  "conversation_id": "conv_99a88b77c6",
  "sender_id": "usr_7f8a9b1c2d",
  "ts": "2026-10-30T20:15:30Z",
  "type": "image",
  "content": "Voici le diagramme d'architecture",
  "attachment": {
    "name": "architecture_mongodb_spark.png",
    "size": 1048576,
    "mime": "image/png"
  },
  "reactions": [
    {"user_id": "usr_8a9b0c1d2e", "emoji": "👍"},
    {"user_id": "usr_9b0c1d2e3f", "emoji": "🔥"}
  ],
  "edited": false,
  "deleted": false,
  "expire_at": null
}
```

### 1.4 Collection `read_status`
Suit l'état de lecture par utilisateur et conversation (curseur temporel).
```json
{
  "_id": "rs_5566778899",
  "conversation_id": "conv_99a88b77c6",
  "user_id": "usr_8a9b0c1d2e",
  "last_read_ts": "2026-10-30T20:15:30Z"
}
```

### 1.5 Collection `reports`
Trace les signalements de contenus abusifs ou de spams pour modération.
```json
{
  "_id": "rep_1234567890",
  "message_id": "msg_0011223344",
  "reporter_id": "usr_9b0c1d2e3f",
  "reason": "spam",
  "status": "pending",
  "created_at": "2026-10-30T20:20:00Z"
}
```

---

## 2. Choix de Modélisation : Embarquement (Embedding) vs Référence

| Élément | Choix | Justification technique |
| :--- | :--- | :--- |
| **`participants`** | Embarqué dans `conversations` | Cardinalité bornée par groupe, permet de vérifier les droits et afficher la liste en une seule lecture sans jointure. |
| **`reactions`** | Embarqué dans `messages` | Faible volume de réactions par message, lecture conjointe indispensable à l'affichage du flux de discussion. |
| **`attachment`** | Embarqué dans `messages` | Relation 1:1 stricte, métadonnées indissociables du message lors de son rendu à l'écran. |
| **`messages`** | Référence (`conversation_id`) | Relation 1:N non bornée (millions de messages possibles), évite le dépassement de la limite BSON de 16 Mo par document. |
| **`read_status`** | Collection séparée | Mises à jour à très haute fréquence à chaque message lu ; sépare les écritures pour éviter les locks et la contention sur les conversations. |

---

## 3. Stratégie d'Indexation

| Collection | Spécification de l'index | Options | Requêtes servies |
| :--- | :--- | :--- | :--- |
| **users** | `{pseudo: 1}` | `unique=True` | T03 (recherche profil), unicité à l'inscription |
| **users** | `{last_login: 1}` | | A21 (détection d'inactivité) |
| **users** | `{created_at: 1}` | | S30 (analyse des cohortes d'inscription) |
| **conversations** | `{participants.user_id: 1, last_message_at: -1}` | Compound | T06 (liste des conversations de l'utilisateur triées par récence) |
| **conversations** | `{type: 1, participants_count: -1}` | Compound | A20 (groupes volumineux avec plus de 50 membres) |
| **conversations** | `{last_message_at: 1}` | | A25 (détection des conversations dormantes/inactives) |
| **messages** | `{conversation_id: 1, ts: -1}` | Compound | T04, T05, T12, T13, S26 (chargement du fil, pagination inversée, non-lus) |
| **messages** | `{sender_id: 1, ts: -1}` | Compound | A17, S28, S29, S30 (top expéditeurs, spam, signalements) |
| **messages** | `{ts: 1}` | | A16, A18, A22 (agrégations temporelles par jour, type, heure) |
| **messages** | `{expire_at: 1}` | `expireAfterSeconds=0`, `partialFilterExpression={"expire_at": {"$exists": True}}` | T14 (nettoyage automatique en arrière-plan des messages éphémères) |
| **read_status** | `{conversation_id: 1, user_id: 1}` | `unique=True` | T12, T13 (upsert rapide du curseur de lecture et calcul des non lus) |
| **reports** | `{reason: 1, status: 1}` | Compound | A24 (rapports de modération par motif et état) |
| **reports** | `{message_id: 1}` | | T15, S29 (corrélation des messages signalés) |

---

## 4. Matrice Complète des 30 Requêtes (Sujet 04 - Messagerie Instantanée)

| ID | Intitulé de la requête | Collection | Filtre / Tri / Pipeline d'agrégation | Index utilisé | Justification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **T01** | Envoyer un message | `messages` | `insertOne({conversation_id, sender_id, ts, content, ...})` | Aucun (insertion) | Écriture directe et rapide en base. |
| **T02** | Import en masse de messages | `messages` | `bulkWrite([InsertOneModel(...)])` | Aucun (bulk insert) | Optimisation du débit d'ingestion réseau et disque. |
| **T03** | Consulter profil utilisateur | `users` | `find({_id: uid})` ou `find({pseudo: p})` | `_id` ou `{pseudo: 1}` | Recherche pointue O(1) sans scan de collection. |
| **T04** | 50 derniers messages d'un fil | `messages` | `find({conversation_id: cid}).sort({ts: -1}).limit(50)` | `{conversation_id: 1, ts: -1}` | Index composé couvrant filtrage et tri sans sort en mémoire. |
| **T05** | Pagination précédente | `messages` | `find({conversation_id: cid, ts: {$lt: last_ts}}).sort({ts: -1}).limit(50)` | `{conversation_id: 1, ts: -1}` | Keyset pagination optimale sans coût du skip élevé. |
| **T06** | Lister conversations utilisateur | `conversations` | `find({"participants.user_id": uid}).sort({last_message_at: -1})` | `{participants.user_id: 1, last_message_at: -1}` | Multikey index filtrant les membres avec tri direct par récence. |
| **T07** | Créer groupe de discussion | `conversations` | `insertOne({type: 'group', participants: [...], ...})` | Aucun (insertion) | Création atomique du canal de discussion. |
| **T08** | Ajouter/retirer participant | `conversations` | `updateOne({_id: cid}, {$push/pull: {participants: {...}}, $inc: {participants_count: ±1}})` | `_id_` | Mise à jour ciblée avec maintien du compteur dénormalisé. |
| **T09** | Modifier un message | `messages` | `updateOne({_id: mid}, {$set: {content: c, edited: true, edited_at: now}})` | `_id_` | Modification atomique sur clé primaire. |
| **T10** | Suppression douce (soft delete) | `messages` | `updateOne({_id: mid}, {$set: {deleted: true, content: 'Message supprimé'}})` | `_id_` | Préserve l'intégrité de l'historique sans rupture de séquence. |
| **T11** | Ajouter une réaction | `messages` | `updateOne({_id: mid}, {$push: {reactions: {user_id, emoji}}})` | `_id_` | Ajout dans le tableau embarqué sans locks externes. |
| **T12** | Marquer conversation comme lue | `read_status` | `updateOne({conversation_id, user_id}, {$set: {last_read_ts: ts}}, {upsert: true})` | `{conversation_id: 1, user_id: 1}` | Upsert idempotent ultra-rapide sur clé composée unique. |
| **T13** | Compter messages non lus | `messages` | `countDocuments({conversation_id: cid, ts: {$gt: last_read_ts}})` | `{conversation_id: 1, ts: -1}` | Scan index B-Tree borné par date de dernière lecture. |
| **T14** | Message éphémère (TTL) | `messages` | `insertOne({..., expire_at: ISODate(...)})` | `{expire_at: 1}` (TTL) | Suppression automatique par le thread TTL natif de MongoDB. |
| **T15** | Signaler un message | `reports` | `insertOne({message_id, reporter_id, reason, status: 'pending', created_at})` | Aucun (insertion) | Stockage isolé évitant de polluer le document message. |
| **A16** | Volume de messages par jour | `messages` | `$group: {_id: {$dateToString: {format: "%Y-%m-%d", date: "$ts"}}, count: {$sum: 1}}` | `{ts: 1}` | Scan d'index temporel pour agréger par date. |
| **A17** | Top 10 utilisateurs actifs | `messages` | `$group: {_id: "$sender_id", total: {$sum: 1}}, $sort: {total: -1}, $limit: 10` | `{sender_id: 1, ts: -1}` | Pré-regroupement facilité par l'index sur `sender_id`. |
| **A18** | Répartition par type de message | `messages` | `$group: {_id: "$type", count: {$sum: 1}}` | `{ts: 1}` (si filtré) | Répartition globale texte / image / audio / fichier. |
| **A19** | Taille moyenne des pièces jointes | `messages` | `$match: {"attachment.mime": {$exists: true}}, $group: {_id: "$attachment.mime", avgSize: {$avg: "$attachment.size"}}` | Scan partiel | Calcul analytique sur sous-documents embarqués. |
| **A20** | Groupes de plus de 50 membres | `conversations` | `find({type: 'group', participants_count: {$gt: 50}})` | `{type: 1, participants_count: -1}` | Filtre composite direct sur le compteur sans calcul `$size`. |
| **A21** | Inactifs depuis 30 jours | `users` | `find({last_login: {$lt: ISODate(now - 30j)}})` | `{last_login: 1}` | Range query O(log N) sur date de dernière connexion. |
| **A22** | Distribution messages par heure | `messages` | `$group: {_id: {$hour: "$ts"}, count: {$sum: 1}}, $sort: {_id: 1}` | `{ts: 1}` | Analyse horaire (0 à 23h) des pics de charge. |
| **A23** | Top emojis dans les réactions | `messages` | `$unwind: "$reactions", $group: {_id: "$reactions.emoji", count: {$sum: 1}}, $sort: {count: -1}, $limit: 10` | Scan reactions | Débobinage du tableau embarqué et comptage d'occurrences. |
| **A24** | Signalements par motif et état | `reports` | `$group: {_id: {reason: "$reason", status: "$status"}, total: {$sum: 1}}` | `{reason: 1, status: 1}` | Agrégation couverte par l'index composé. |
| **A25** | Conversations inactives (7j) | `conversations` | `find({last_message_at: {$lt: ISODate(now - 7j)}})` | `{last_message_at: 1}` | Scan sélectif des canaux abandonnés sans scan des messages. |
| **S26** | Temps moyen de réponse | `messages` | PySpark Window partitionBy `conversation_id` orderBy `ts`, `lead(ts) - ts` | `{conversation_id: 1, ts: -1}` | Partitionnement distribué Spark pour calculer le delta consécutif. |
| **S27** | Contacts en commun (Graphe) | `conversations` | PySpark self-join sur `participants.user_id` et groupement des paires | Multikey index | Calcul de graphe biparti utilisateurs-conversations distribué. |
| **S28** | Détection de spammeurs | `messages` | PySpark fenêtre 5 min par `sender_id`, détection de volume anormal | `{sender_id: 1, ts: -1}` | Agrégation par fenêtres glissantes (sliding windows). |
| **S29** | Taux de signalement expéditeur | `messages` & `reports` | PySpark join `messages.id == reports.message_id`, ratio signales/envoyés | `{sender_id: 1}` & `{message_id: 1}` | Jointure distribuée Spark entre flux de modération et messages. |
| **S30** | Rétention par cohorte | `users` & `messages` | PySpark cohorte par mois d'inscription `users.created_at`, activité dans `messages` | `users.created_at` & `messages.sender_id` | Analyse matricielle de churn et rétention à M+1, M+2, etc. |
