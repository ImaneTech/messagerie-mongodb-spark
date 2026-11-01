# Rapport final Stage 5

## 1. Corrections Stage 5A (avant → après)

| Item | Avant | Après | Evidence |
|------|-------|-------|----------|
| A16 buckets | N non borné (tous les jours) | 30 buckets ≤ 31 ✓, total 54 754 msgs | RUN-OK — 30 printed |
| S26 | pas de médiane, gap illimité | MAX_GAP_SECONDS=3600 ; 7 033 réponses, moy=43.49s, médiane=0s (percentile_approx) | RUN-OK rows_out=3102 |
| S28 | fenêtre tumbling 1h → 1 row (scindé aux bornes) | fenêtre glissante 1h/10min, dédup sender+content → 30 rows, 10 senders | RUN-OK rows_out=30 |
| T4 nReturned | 3 (conv trop courte) | conv_g_c5da42a4d5 (304 msgs) → nReturned=50 | RUN-OK explain nReturned=50 |
| T4 plan index | — | LIMIT>FETCH>IXSCAN ; keys=51 docs=51 | RUN-OK |
| T4 plan sans index | — | SORT>COLLSCAN ; keys=0 docs=84 373 | RUN-OK |
| T6 utilisateur | non précisé | usr_741de82fdfee → 10 conversations (≥5 ✓) | RUN-OK nReturned=10 |
| T13 unread | count=0 (aucune conv avec non-lus) | last_read_ts = 20e msg récent → count=1 > 0, restauré | RUN-OK count=1 |
| S28 senders Spark vs check_data | désaccord | SPARK={usr_0b31c804048c,usr_1a103536133a,usr_3be6e14536d3,usr_8c85e77efde3,usr_9aae093d6bf6,usr_a92cd0b62310,usr_a9a5d35802eb,usr_b4ca3990904e,usr_bbd74caaa7c6,usr_d08e5c5b2750} diff=∅ | RUN-OK |

## 2. Counts 5 collections (avant = après)

| Collection    | Avant  | Après  |
|---------------|--------|--------|
| users         | 10 000 | 10 000 |
| conversations |  8 000 |  8 000 |
| messages      | 84 373 | 84 373 |
| read_status   | 20 166 | 20 166 |
| reports       |  1 200 |  1 200 |

## 3. 25 requêtes natives (3 runs)

| id  | statut  | avg_ms | | id  | statut  | avg_ms |
|-----|---------|--------|-|-----|---------|--------|
| T01 | RUN-OK  |  32.50 | | A16 | RUN-OK  |  80.36 |
| T02 | RUN-OK  | 557.85 | | A17 | RUN-OK  | 107.42 |
| T03 | RUN-OK  |  10.72 | | A18 | RUN-OK  |  86.17 |
| T04 | RUN-OK  | 123.87 | | A19 | RUN-OK  | 137.47 |
| T05 | RUN-OK  |  51.39 | | A20 | RUN-OK  |  11.79 |
| T06 | RUN-OK  |  32.64 | | A21 | RUN-OK  |  23.84 |
| T07 | RUN-OK  |  18.06 | | A22 | RUN-OK  | 132.85 |
| T08 | RUN-OK  |  19.42 | | A23 | RUN-OK  | 105.28 |
| T09 | RUN-OK  |  34.00 | | A24 | RUN-OK  |  11.61 |
| T10 | RUN-OK  |  33.70 | | A25 | RUN-OK  |  37.09 |
| T11 | RUN-OK  |  21.99 | | | | |
| T12 | RUN-OK  |  23.25 | | | | |
| T13 | RUN-OK  |  63.13 | | | | |
| T14 | RUN-OK  |  19.25 | | | | |
| T15 | RUN-OK  | 107.52 | | | | |

## 4. 5 jobs Spark (1 run)

| job_id | statut  | rows_out | avg_ms |
|--------|---------|----------|--------|
| s26    | RUN-OK  |    3 102 |  6 538 |
| s27    | RUN-OK  |       20 | 15 596 |
| s28    | RUN-OK  |       30 |  1 746 |
| s29    | RUN-OK  |       20 |  5 793 |
| s30    | RUN-OK  |        6 |  6 336 |

## 5. Native vs Spark

| query_id | native_avg_ms | spark_avg_ms | spark_session_ms | same_result |
|----------|---------------|--------------|------------------|-------------|
| A16      |         80.36 |        7 988 |            2 009 | SPARK_ONLY  |
| A17      |        107.42 |        5 383 |            1 930 | SPARK_ONLY  |
| A18      |         86.17 |        7 950 |            2 346 | SPARK_ONLY  |

Note : SPARK_ONLY = résultat Spark seul disponible (format agrégé différent, vérification sémantique non automatisable).

## 6. Index test

| query_id | mode     | runs | avg_ms | median_ms | p95_ms | docs_examined | keys_examined | n_returned | stage_chain              |
|----------|----------|------|--------|-----------|--------|---------------|---------------|------------|--------------------------|
| T4       | index    |   15 |  14.90 |      5.77 |  66.30 |            50 |            50 |         50 | LIMIT > FETCH > IXSCAN   |
| T4       | no_index |   15 | 122.78 |    132.57 | 194.56 |        93 525 |             0 |         50 | SORT > COLLSCAN          |
| T6       | index    |   15 |   4.63 |      3.49 |  13.28 |            10 |            10 |         10 | LIMIT > FETCH > IXSCAN   |
| T6       | no_index |   15 |  24.50 |     24.18 |  43.10 |         8 000 |             0 |         10 | SORT > COLLSCAN          |

## 7. Consistency test (members_up=2 ; mongo3 hors ligne attendu)

| test_id | setting         | runs | avg_ms  | median_ms | p95_ms   | members_up |
|---------|-----------------|------|---------|-----------|----------|------------|
| T1      | w=1             |   50 |    3.95 |      3.22 |     7.86 |          2 |
| T1      | w=majority      |   50 |   29.40 |     14.53 |    78.03 |          2 |
| T2      | w=1             |    5 |  688.24 |    667.23 | 1 148.45 |          2 |
| T2      | w=majority      |    5 |  620.55 |    441.80 | 1 262.62 |          2 |
| T4      | readConcern=local    | 30 | 14.52 |  14.32 |    16.46 |          2 |
| T4      | readConcern=majority | 30 | 13.34 |  13.17 |    14.58 |          2 |

Note : résultats à re-exécuter quand mongo3 sera de nouveau actif.

## 8. Dashboard

| Vérification       | Résultat |
|--------------------|----------|
| ast.parse app.py   | RUN-OK — "PARSE OK" |
| Smoke test AppTest | NOT-RUN (streamlit.testing.v1 non invoqué) |
| streamlit health   | NOT-RUN (serveur non démarré pendant ce rapport) |

## 9. git push

```
Commits en attente avant push :
0450702 Mise a jour README dashboard et port Spark
97e0035 Debut du dashboard
374744d Résultats consolidés
f87467c Test de cohérence
81802d3 Test des index
(origin/main = edde671 Mesures corrigees)
```

(git push sera exécuté après commit du présent rapport — voir ci-dessous)

## 10. Problèmes ouverts

- S26 médiane=0 s : percentile_approx(0.5) retourne 0 sur des valeurs entières basses ; la distribution réelle des temps de réponse < 1 s domine.
- native_vs_spark same_result=SPARK_ONLY pour A16/A17/A18 : comparaison automatique impossible car Spark renvoie un DataFrame structuré différent du curseur MongoDB.
- Smoke test AppTest et curl health NOT-RUN : aucune commande de démarrage Streamlit n'a été exécutée dans ce workflow.
- mongo3 hors ligne (1 membre unreachable) : consistency_test et replSetGetStatus ne reflètent que 2 membres.

## 11. Prochaine action unique

Démarrer `streamlit run dashboard/app.py --server.headless true`, exécuter le smoke test AppTest sur chaque page, vérifier `curl http://localhost:8501/_stcore/health` et corriger la médiane S26 (utiliser `percentile_approx(0.5)` sur les valeurs en secondes flottantes).
