# Résultats — Stage 4A-3 & 4A-4 — Requêtes natives + explain()

Date d'exécution : 2026-10-31

---

## Counts avant / après le run

| Collection    | Avant  | Après  | Statut |
|---------------|--------|--------|--------|
| users         | 10 000 | 10 000 | OK     |
| conversations | 8 000  | 8 000  | OK     |
| messages      | 84 697 | 84 697 | OK     |
| read_status   | 20 166 | 20 166 | OK     |
| reports       | 1 200  | 1 200  | OK     |

✓ Tous les counts sont identiques (nettoyage _benchmark correct).

---

## Tableau des 25 requêtes natives (runs=3)

| query_id | Statut   | avg_ms  | Résumé résultat                                          |
|----------|----------|---------|----------------------------------------------------------|
| T01      | RUN-OK   |   23.15 | 1 message inséré puis supprimé (_benchmark)              |
| T02      | RUN-OK   |  518.60 | 10 000 messages bulk_write puis supprimés (_benchmark)   |
| T03      | RUN-OK   |   14.44 | profil récupéré (pseudo: johnsonjoshua)                  |
| T04      | RUN-OK   |   21.36 | 3 messages retournés (conv de test avec peu de msgs)     |
| T05      | RUN-OK   |   33.72 | 3 messages, pagination keyset avant ts                   |
| T06      | RUN-OK   |   15.93 | 5 conversations pour l'utilisateur                       |
| T07      | RUN-OK   |   18.60 | groupe créé puis supprimé (_benchmark)                   |
| T08      | RUN-OK   |   21.39 | 1 participant ajouté puis retiré (réversible)            |
| T09      | RUN-OK   |   38.65 | 1 message modifié puis restauré                          |
| T10      | RUN-OK   |   20.22 | 1 message soft-deleted puis restauré                     |
| T11      | RUN-OK   |   22.27 | 1 réaction ajoutée puis restaurée                        |
| T12      | RUN-OK   |   17.42 | last_read_ts mis à jour puis restauré                    |
| T13      | RUN-OK   |   34.02 | 0 messages non lus (déjà lu)                             |
| T14      | RUN-OK   |   22.16 | message éphémère inséré puis supprimé (_benchmark)       |
| T15      | RUN-OK   |   20.81 | rapport inséré puis supprimé (_benchmark)                |
| A16      | RUN-OK   |  105.15 | messages par jour sur ~170 jours agrégés                 |
| A17      | RUN-OK   |  102.81 | top user: wujorge — 92 messages                          |
| A18      | RUN-OK   |  112.83 | text=60323, image=12116, file=7411                       |
| A19      | RUN-OK   |  115.50 | taille moy. pièces jointes par MIME type                 |
| A20      | RUN-OK   |   11.17 | groupes > 50 participants trouvés                        |
| A21      | RUN-OK   |   29.09 | 1545 utilisateurs inactifs > 30j                         |
| A22      | RUN-OK   |  126.82 | ~2350 messages/heure (distribution uniforme)             |
| A23      | RUN-OK   |   95.37 | top emoji: 🚀 (2850), 😢 (2813), ❤️ (2803)               |
| A24      | RUN-OK   |   17.84 | signalements par motif/statut (scam, harassment…)        |
| A25      | RUN-OK   |   31.93 | 2650 conversations inactives > 7j                        |

**25/25 RUN-OK**

---

## Explain T4 et T6 — avec / sans index

### T4 — 50 derniers messages d'une conversation

| Scénario      | winningPlan_stage | totalDocsExamined | nReturned | executionTimeMillis |
|---------------|-------------------|-------------------|-----------|---------------------|
| Avec index    | LIMIT             | 8                 | 3         | 1                   |
| Sans index    | SORT              | 84 697            | 3         | 46                  |

L'index réduit l'examen de **84 697 → 8 documents** (10 000× moins) et le temps de **46 → 1 ms**.

### T6 — Lister les conversations d'un utilisateur

| Scénario      | winningPlan_stage | totalDocsExamined | nReturned | executionTimeMillis |
|---------------|-------------------|-------------------|-----------|---------------------|
| Avec index    | LIMIT             | 5                 | 5         | 0                   |
| Sans index    | SORT              | 8 000             | 5         | 7                   |

L'index réduit l'examen de **8 000 → 5 documents**.

### T5 — Pagination précédente

| Scénario   | winningPlan_stage | totalDocsExamined | nReturned | executionTimeMillis |
|------------|-------------------|-------------------|-----------|---------------------|
| Avec index | LIMIT             | 8                 | 3         | 0                   |

---

## Fichiers produits

- `benchmarks/results/queries_native.csv` — source unique de vérité (25 requêtes, runs=3)
- `benchmarks/results/explain_T4.json`
- `benchmarks/results/explain_T4_noindex.json`
- `benchmarks/results/explain_T5.json`
- `benchmarks/results/explain_T6.json`
- `benchmarks/results/explain_T6_noindex.json`
- `benchmarks.json` supprimé (redondant)
