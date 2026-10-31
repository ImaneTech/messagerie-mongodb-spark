# Rapport final — Stage 4A / 4B / 4C

Date : 2026-10-31

## 1. Vérifications 4A (check_data.py) — ALL PASS 20/20

| Statut | Vérification                         | Valeur mesurée     |
|--------|--------------------------------------|--------------------|
| PASS   | users == 10000                       | 10000              |
| PASS   | conversations == 8000                | 8000               |
| PASS   | messages >= 80000                    | 84697              |
| PASS   | reports >= 1000                      | 1200               |
| PASS   | read_status == participants          | 20166              |
| PASS   | messages 24h >= 300                  | 5672               |
| PASS   | messages 7j                          | 26869              |
| PASS   | messages 30j                         | 55935              |
| PASS   | aucun éphémère expire_at < now       | 0                  |
| PASS   | S28 spam >= 3 contenu >20 convs/1h   | 3 contenus         |
| PASS   | S26 back-and-forth rapide >= 100     | 584 conversations  |
| PASS   | S27 paires contacts communs >= 10    | 28895 paires       |
| PASS   | A21 inactifs > 30j >= 100            | 1545               |
| PASS   | A25 convs inactives >= 100           | 2650               |
| PASS   | A20 groupes > 50 participants >= 5   | 7 groupes          |
| PASS   | 1 seul index TTL                     | 1                  |
| PASS   | S30 ts < created_at == 0             | 0                  |
| PASS   | S30 mois inscription distincts >= 6  | 6 (mai–oct 2026)   |

## 2. Counts avant/après requêtes natives

| Collection    | Avant  | Après  |
|---------------|--------|--------|
| users         | 10000  | 10000  |
| conversations | 8000   | 8000   |
| messages      | 84697  | 84697  |
| read_status   | 20166  | 20166  |
| reports       | 1200   | 1200   |

## 3. Requêtes natives — 25/25 RUN-OK

| ID  | Statut | avg_ms | Résumé                                          |
|-----|--------|--------|-------------------------------------------------|
| T01 | RUN-OK | 23     | 1 message inséré puis supprimé                  |
| T02 | RUN-OK | 519    | 10000 messages bulk puis supprimés              |
| T03 | RUN-OK | 14     | profil récupéré (johnsonjoshua)                 |
| T04 | RUN-OK | 21     | 3 messages retournés                            |
| T05 | RUN-OK | 34     | 3 messages, pagination keyset                   |
| T06 | RUN-OK | 16     | 5 conversations utilisateur                     |
| T07 | RUN-OK | 19     | groupe créé puis supprimé                       |
| T08 | RUN-OK | 21     | 1 participant ajouté puis retiré                |
| T09 | RUN-OK | 39     | 1 message modifié puis restauré                 |
| T10 | RUN-OK | 20     | 1 message soft-deleted puis restauré            |
| T11 | RUN-OK | 22     | 1 réaction ajoutée puis restaurée               |
| T12 | RUN-OK | 17     | last_read_ts mis à jour puis restauré           |
| T13 | RUN-OK | 34     | 0 messages non lus                              |
| T14 | RUN-OK | 22     | message éphémère inséré puis supprimé           |
| T15 | RUN-OK | 21     | rapport inséré puis supprimé                    |
| A16 | RUN-OK | 105    | messages/jour sur ~170 jours                    |
| A17 | RUN-OK | 103    | top user: wujorge — 92 messages                 |
| A18 | RUN-OK | 113    | text=60323, image=12116, file=7411              |
| A19 | RUN-OK | 116    | taille moy. pièces jointes par MIME             |
| A20 | RUN-OK | 11     | groupes > 50 participants trouvés               |
| A21 | RUN-OK | 29     | 1545 utilisateurs inactifs > 30j                |
| A22 | RUN-OK | 127    | ~2350 messages/heure                            |
| A23 | RUN-OK | 95     | top emoji: 🚀 (2850), 😢 (2813)                 |
| A24 | RUN-OK | 18     | signalements par motif/statut                   |
| A25 | RUN-OK | 32     | 2650 conversations inactives > 7j               |

## 4. Explain T4 et T6 (avec/sans index)

| Requête | Scénario    | winningPlan | totalDocsExamined | nReturned | ms |
|---------|-------------|-------------|-------------------|-----------|----|
| T4      | avec index  | LIMIT       | 8                 | 3         | 1  |
| T4      | sans index  | SORT        | 84697             | 3         | 46 |
| T6      | avec index  | LIMIT       | 5                 | 5         | 0  |
| T6      | sans index  | SORT        | 8000              | 5         | 7  |

## 5. Jobs Spark S26–S30 — 5/5 RUN-OK

| job_id | Statut | rows_out | Résultat (1 ligne)                                | avg_ms |
|--------|--------|----------|---------------------------------------------------|--------|
| S26    | RUN-OK | 7743     | Moyenne globale 724444 s — top 20 dans stats_s26  | 4568   |
| S27    | RUN-OK | 20       | 179192 lignes explode, 5,4M interméd.             | 14301  |
| S28    | RUN-OK | 1        | 1 combinaison sender/content/fenêtre >20 convs    | 5356   |
| S29    | RUN-OK | 20       | top 20 senders par taux signalement               | 4726   |
| S30    | RUN-OK | 6        | 6 cohortes mai–oct 2026 avec rétention            | 5696   |

## 6. Comparaison natif vs Spark

| query_id | native_avg_ms | spark_avg_ms | spark_session_ms | same_result |
|----------|---------------|--------------|------------------|-------------|
| A16      | 106           | 6038         | 1826             | OK          |
| A17      | 107           | 5648         | 1879             | OK          |
| A18      | 95            | 5596         | 1822             | OK          |

Spark ~55–57× plus lent que natif (overhead JVM + lecture complète de la collection).

## 7. Commits

- `Vérification des données` (Stage 4A-1/2)
- `Mesures des requêtes natives` (Stage 4A-3/4)
- `Job Spark S26` — f4555e8
- `Job Spark S27` — e15b0d4
- `Job Spark S28` — 42ce039
- `Job Spark S29` — 6b98b6a
- `Job Spark S30` — ff6ea4a
- `Mesures des jobs Spark` — 486ed0e
- `Comparaison natif et Spark` (Stage 4C — ce commit)

## 8. Problèmes ouverts

- mongo3 (192.168.0.195:27017) inaccessible (machine B éteinte) — SocketTimeoutException attendue, sans impact.
- pymongo absent du conteneur spark-master à l'installation initiale — résolu par `pip install` root éphémère.

## 9. Prochaine action

Stage 4C terminé. Aucune suite demandée (arrêt après 4C). Remettre le rapport au superviseur.
