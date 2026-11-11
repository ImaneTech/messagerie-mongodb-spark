# REPO_MAP — messagerie-mongodb-spark

> **Configuration cible actuelle** : la refactorisation 3-VM utilise
> `192.168.0.100`, `192.168.0.101` et `192.168.0.102`, avec un membre MongoDB
> et un service Spark dédiés par VM. Les notes historiques ci-dessous décrivent
> l'état observé avant cette refactorisation.

Audit Phase 0 (read-only). Date: 2026-11-10. Machine d'audit : Windows (poste de dev d'Emma) — Docker Desktop arrêté, cluster non joignable depuis cet environnement.

## Arborescence

| Chemin | Rôle | État |
|---|---|---|
| `config/settings.py` | `MONGO_URI`, `MONGO_DB`, `COLLECTIONS` | URI par défaut vers les 3 IPs fixes et `chatdb`; `.env` facultatif |
| `machine-a/docker-compose.yml` | mongo1 (27017), spark-master — réseau **bridge** `chat_net` | VM1 / master |
| `machine-b/docker-compose.yml` | mongo2 (27017), spark-worker1 — réseau **bridge** `chat_net` | VM2 / worker 1 |
| `machine-c/docker-compose.yml` | mongo3 (27017), spark-worker2 — réseau **bridge** `chat_net` | VM3 / worker 2 |
| `machine-a/.env`, `machine-b/.env`, `.env` | IPs `192.168.0.178` (A) / `192.168.0.195` (B) — **réseau 192.168.0.0/24, pas 192.168.1.x du guide** | OK (IP fixes supposées) |
| `data_generator/generate_data.py` | Générateur Faker, seed=42, users/conversations/messages/read_status/reports + injections S26/S27/S28/S30 | Complet, voir écarts de schéma dans AUDIT |
| `data_generator/load_data.py` | Orchestration génération + `insert_many` par lots de 5000 + `create_indexes()` | OK |
| `data_generator/check_data.py` | ~16 vérifications de cohérence (counts, TTL, spam, back-and-forth, cohorts) | Très bon outil, à conserver |
| `schema/create_indexes.py` | 13 index idempotents (unique pseudo, TTL expire_at, composés) | OK |
| `queries/transactional/t01..t15` | 15 requêtes PyMongo, chacune avec `run()`, la plupart avec `cleanup()` | Implémentées ; écarts listés dans AUDIT |
| `queries/analytical/a16..a25` | 10 pipelines d'agrégation | Implémentées |
| `queries/utils.py` | `get_db()`, `timed(runs=3)`, `extract_index_name()`, `save_query_results()` | OK |
| `spark/spark_session.py` | SparkSession + `mongo-spark-connector_2.12:10.3.0`, ivy `/tmp` | OK |
| `spark/jobs/s26..s30` | 5 jobs PySpark écrivant dans `stats_s26..s30` | Implémentés, timings partiels (voir AUDIT) |
| `spark/comparaison/cmp_a16/a17/a18` | Versions Spark de A16-A18 pour comparaison natif/Spark | OK (3 requêtes = exigence min.) |
| `benchmarks/run_native_queries.py` | Exécute les 25 requêtes natives, 3 runs chacun, counts avant/après, CSV | OK |
| `benchmarks/index_test.py` | T4/T5/T6 explain executionStats + benchmark index/no-index via hint `$natural` | OK — couvre l'exigence « effet d'un index » |
| `benchmarks/consistency_test.py` | w=1/majority/3 sur T1+T2, readConcern local/majority sur T4 | OK — couvre l'exigence « write/read concern » ; exige 3 membres UP |
| `benchmarks/run_all.py` | Orchestrateur : natif + index + consistency (+ spark optionnel) + merge CSV | OK |
| `benchmarks/run_spark_job.sh` / `.ps1` | `docker exec spark-master spark-submit --master spark://spark-master:7077 --packages ..._2.12:10.3.0` | OK ; master address = nom de service Docker (bridge) |
| `benchmarks/merge_native_spark.py` | Compare résultats natif vs Spark (A16-A18), produit `native_vs_spark.csv` | OK |
| `scripts/failover_test.py` | Test failover : stop/kill mongo1, mesure élection, écriture w=majority, réintégration → CSV | Bon script ; suppose mongo1 primaire et jointe les membres par noms Docker |
| `dashboard/app.py` | Streamlit 5 onglets, KPI + ~10 graphiques Plotly, cache 60 s, lit Mongo + CSV results | Fonctionnel ; à redesign (exigence « compact, 1-2 écrans ») partiellement |
| `README.md` | Documentation FR complète : archi, schéma, 30 requêtes, Spark, benchmarks, dashboard, dépannage | Très complet ; contient des chiffres non vérifiables ici |
| `screenshots/` | 20 captures (archi, RS, Spark UI, dashboard, failover) | Présentes |
| `.gitignore` | `.env`, `.venv`, `benchmarks/results/`, `data/` | OK ; `benchmarks/results/` ignoré → les CSV de preuves ne sont PAS versionnés |
| `requirements.txt` | pymongo 4.19, Faker 40.44, pyspark 3.5.1, streamlit 1.66.1, pandas 3.1, plotly | pyspark 3.5.1 vs Spark 3.5.3 du cluster — mineur |

## Topologie historique (avant la refactorisation)

- **Réseau Docker : bridge** (`chat_net`), PAS host network comme le guide (§4.1). Conséquence : les conteneurs sont joints par noms de service (`mongo1`, `spark-master`), pas par IP:port de l'hôte ; mongo3 écoute sur **27019** (mongo1=27017, mongo2=27018 pour éviter les collisions… sur la même machine seulement ; mongo3 aurait pu être 27017).
- **Spark : master + worker1 + worker2 tous sur machine A.** Machine B n'héberge que mongo3. Le layout visé par Emma (worker2 sur B) n'est PAS celui configuré.
- **MongoDB : mongo1+mongo2 sur A, mongo3 sur B** — conforme à la cible.
- IPs configurées : A=`192.168.0.178`, B=`192.168.0.195` (sous-réseau `192.168.0.0/24`, différent du `192.168.1.x` du guide — pas bloquant si les deux machines sont sur ce sous-réseau).
- Priorités RS : mongo1 priority 2 annoncé dans le README ; **aucun script `rs.initiate` dans le repo** — l'initiation du replica set n'est pas reproductible (P0).

## Versions épinglées

- Spark `apache/spark:3.5.3-python3` (Scala 2.12) ✓ conforme guide
- Connecteur `mongo-spark-connector_2.12:10.3.0` ✓ suffixe `_2.12` correct
- MongoDB `mongo:7` (le guide ne fixe pas de version Mongo ; 7.0 noté dans README)
- pyspark pip `3.5.1` ≠ image `3.5.3` (utilisé seulement pour scripts locaux ; jobs tournent dans le conteneur)

## ABSENTS du dépôt

1. **`docs/` — les deux PDF du professeur absents** (`guide_ensaj_mini_projets.pdf`, `miniProjetsEnsaj_1.pdf`). Le prompt les résume intégralement ; je n'ai pas pu les relire.
2. **Sources du rapport LaTeX** (template ENSA + `.tex`) — absents. Le README dit que le rapport est séparé ; rien à compiler ici.
3. **`results/`** — gitignoré et absent : aucune preuve chiffrée versionnée (normal si régénéré, mais `DEMO_SCRIPT.md` et un export versionné des résultats seraient utiles).
4. **Script d'initiation du replica set** (`rs.initiate` avec priorités + hostnames joignables depuis B).
5. **Scripts start/stop/restart ordonnés** (le guide §4.8 demande l'ordre de redémarrage après coupure).
6. **`DEMO_SCRIPT.md`**.
7. **Fichier `.streamlit/config.toml`** pour le thème dashboard.
8. `docker-compose` racine : deux compose séparés (A et B) — acceptable, mais aucun ne couvre le cas « tout sur une machine » pour démo.

## État git

- Branche `main`, **6 fichiers modifiés non commités** (README, run_all, settings, 2 compose, failover_test) + `run_spark_job.sh` non suivi. À intégrer dans la branche de travail.
- Tags existants : `avant-reecriture`, `avant-style-etudiant` (pas de tag `v-before-audit`).
