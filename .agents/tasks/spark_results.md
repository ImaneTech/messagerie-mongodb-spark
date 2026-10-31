# Résultats — Stage 4B — Jobs Spark S26 à S30

Date d'exécution : 2026-10-31

---

## Tableau des 5 jobs Spark

| job_id | Statut   | rows_out | Résultat (1 ligne)                                         | avg_ms |
|--------|----------|----------|------------------------------------------------------------|--------|
| S26    | RUN-OK   | 7 743    | Moyenne globale 724 444 s (données sur 6 mois) — top 20 convs écrits dans stats_s26 | 4 568 |
| S27    | RUN-OK   | 20       | 179 192 lignes après explode, 5,4M intermédiaires — top 20 paires dans stats_s27 | 14 301 |
| S28    | RUN-OK   | 1        | 1 combinaison sender/content/fenêtre >20 convs en 1h détectée dans stats_s28 | 5 356 |
| S29    | RUN-OK   | 20       | Top 20 expéditeurs par taux de signalement (sent >= 20 msgs) dans stats_s29 | 4 726 |
| S30    | RUN-OK   | 6        | 6 cohortes mensuelles (mai–octobre 2026) avec rétention dans stats_s30 | 5 696 |

---

## Détail des timings (3 runs, DUREE_MS mesurée autour du write)

| job_id | run1_ms | run2_ms | run3_ms | avg_ms | min_ms | max_ms |
|--------|---------|---------|---------|--------|--------|--------|
| S26    | 5 097   | 4 065   | 4 541   | 4 568  | 4 065  | 5 097  |
| S27    | 13 452  | 14 854  | 14 598  | 14 301 | 13 452 | 14 854 |
| S28    | 4 482   | 3 884   | 7 701   | 5 356  | 3 884  | 7 701  |
| S29    | 4 432   | 4 576   | 5 169   | 4 726  | 4 432  | 5 169  |
| S30    | 6 925   | 5 098   | 5 064   | 5 696  | 5 064  | 6 925  |

---

## Notes

- **mongo3 (192.168.0.195:27017)** inaccessible : toléré, SocketTimeoutException en fin de job, sans impact sur les résultats.
- **S27** : self-join coûteux (5,4M lignes intermédiaires) — 14 s de write, attendu vu la taille.
- **S28** : 1 seul résultat car les 3 contenus spam du générateur partagent la même fenêtre horaire et le même expéditeur pour certains cas. Donnée cohérente avec le check_data (3 contenus détectés nativement sur critère différent).
- **Transient Ivy failure** pour S29 runs 2/3 : résolu en passant `--jars` avec les jars déjà en cache. Jobs S26/S27/S28/S30 utilisent `--packages` car le cache était chaud.
- Tous les résultats écrits dans `stats_s26` … `stats_s30` dans chatdb (mode overwrite).
- CSV : `benchmarks/results/spark_jobs.csv`
- Script helper : `benchmarks/run_spark_job.ps1`

## Commits réalisés

- `Job Spark S26` — f4555e8
- `Job Spark S27` — e15b0d4
- `Job Spark S28` — 42ce039
- `Job Spark S29` — 6b98b6a
- `Job Spark S30` — ff6ea4a
- `Mesures des jobs Spark` — 486ed0e (CSV + helper script)
