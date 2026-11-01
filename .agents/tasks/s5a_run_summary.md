# Résumé Stage 5A-8 — Mesures corrigées

## Counts avant / après (identiques)

| Collection    | Avant  | Après  | Statut |
|---------------|--------|--------|--------|
| users         | 10000  | 10000  | OK     |
| conversations | 8000   | 8000   | OK     |
| messages      | 84373  | 84373  | OK     |
| read_status   | 20166  | 20166  | OK     |
| reports       | 1200   | 1200   | OK     |

## A16 — Messages par jour (30 derniers jours)
- **Buckets** : 30 (≤ 31 ✓)
- **Total messages** : 54754
- Spark cmp_a16 : 30 jours, 54760 messages (SPARK_AVG_MS=7988)

## S26 — Temps de réponse
- MAX_GAP_SECONDS=3600
- **REPONSES_COMPTEES** : 7033
- **MOYENNE_SEC** : 43.49
- **MEDIANE_SEC** : 0 (percentile_approx)
- DUREE_MS=6538, rows_out=3102

## S28 — Détection spam (sliding window)
- **SPARK_ROWS** : 30 (fenêtre glissante 1h/10min, dédupliqué par sender+content)
- **SPARK_SENDER_IDS** : ['usr_0b31c804048c', 'usr_1a103536133a', 'usr_3be6e14536d3', 'usr_8c85e77efde3', 'usr_9aae093d6bf6', 'usr_a92cd0b62310', 'usr_a9a5d35802eb', 'usr_b4ca3990904e', 'usr_bbd74caaa7c6', 'usr_d08e5c5b2750']
- DUREE_MS=1746

## T4 — Conversation choisie
- **CONV_CHOISIE** : conv_g_c5da42a4d5
- **NB_MESSAGES** : 304 (≥ 50 ✓)
- **nReturned** : 50 ✓

## T6 — Utilisateur choisi
- **USER_CHOISI** : usr_741de82fdfee
- **NB_CONVERSATIONS** : 10 (≥ 5 ✓)

## T13 — Messages non lus
- **T13_UNREAD_COUNT** : 1 (> 0 ✓)
- Méthode : 20e message le plus récent dans conv avec ≥ 20 messages, last_read_ts restauré après le test

## Explain T4 — Stage chain

| Mode         | stage_chain              | keysExamined | docsExamined | nReturned | timeMs |
|--------------|--------------------------|--------------|--------------|-----------|--------|
| Avec index   | LIMIT > FETCH > IXSCAN   | 51           | 51           | 50        | 1      |
| Sans index   | SORT > COLLSCAN          | 0            | 84373        | 50        | 33     |

## Statut des 25 requêtes natives

| query_id | status  | avg_ms  |
|----------|---------|---------|
| T01      | RUN-OK  | 17.78   |
| T02      | RUN-OK  | 607.05  |
| T03      | RUN-OK  | 10.97   |
| T04      | RUN-OK  | 107.11  |
| T05      | RUN-OK  | 35.07   |
| T06      | RUN-OK  | 34.49   |
| T07      | RUN-OK  | 21.57   |
| T08      | RUN-OK  | 19.98   |
| T09      | RUN-OK  | 29.54   |
| T10      | RUN-OK  | 19.05   |
| T11      | RUN-OK  | 20.01   |
| T12      | RUN-OK  | 18.20   |
| T13      | RUN-OK  | 41.00   |
| T14      | RUN-OK  | 17.90   |
| T15      | RUN-OK  | 20.61   |
| A16      | RUN-OK  | 83.84   |
| A17      | RUN-OK  | 103.60  |
| A18      | RUN-OK  | 86.67   |
| A19      | RUN-OK  | 119.00  |
| A20      | RUN-OK  | 9.95    |
| A21      | RUN-OK  | 20.11   |
| A22      | RUN-OK  | 115.85  |
| A23      | RUN-OK  | 95.56   |
| A24      | RUN-OK  | 12.24   |
| A25      | RUN-OK  | 27.90   |

## Statut des 5 jobs Spark

| job_id | status  | rows_out | avg_ms |
|--------|---------|----------|--------|
| s26    | RUN-OK  | 3102     | 6538   |
| s27    | RUN-OK  | 20       | 15596  |
| s28    | RUN-OK  | 30       | 1746   |
| s29    | RUN-OK  | 20       | 5793   |
| s30    | RUN-OK  | 6        | 6336   |

## Native vs Spark

| query_id | native_avg_ms | spark_avg_ms | spark_session_ms | same_result |
|----------|---------------|--------------|------------------|-------------|
| A16      | 83.84         | 7988         | 2009             | SPARK_ONLY  |
| A17      | 103.60        | 5383         | 1930             | SPARK_ONLY  |
| A18      | 86.67         | 7950         | 2346             | SPARK_ONLY  |

## Fichiers résultats générés
- benchmarks/results/queries_native.csv (25 lignes)
- benchmarks/results/spark_jobs.csv (5 lignes)
- benchmarks/results/native_vs_spark.csv (3 lignes)
- benchmarks/results/spark_cmp_raw.txt
- benchmarks/results/explain_T4.json (stage_chain non vide)
- benchmarks/results/explain_T4_noindex.json
- benchmarks/results/explain_T5.json
- benchmarks/results/explain_T6.json
- benchmarks/results/explain_T6_noindex.json
