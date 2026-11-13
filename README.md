# Messagerie MongoDB et Spark

Projet Big Data du sujet 04 : une messagerie distribuÃ©e construite avec
MongoDB Replica Set, Apache Spark et Streamlit.

Le projet fonctionne sur trois VM Ubuntu :

| VM | Adresse | MongoDB | Spark |
|---|---|---|---|
| VM1 | `192.168.0.100` | `mongo1`, PRIMARY | Master |
| VM2 | `192.168.0.101` | `mongo2`, SECONDARY | Worker 1 |
| VM3 | `192.168.0.102` | `mongo3`, SECONDARY | Worker 2 |

MongoDB utilise la base `chatdb`, le Replica Set `rs0` et le port `27017`.
Spark utilise le port `7077` et son interface Web est disponible sur le port
`8080` de VM1. Le tableau de bord est disponible sur le port `8501`.

## Sommaire

1. [Architecture](#architecture)
2. [Organisation du dÃ©pÃ´t](#organisation-du-dÃ©pÃ´t)
3. [Installation](#installation)
4. [DonnÃ©es et schÃ©ma](#donnÃ©es-et-schÃ©ma)
5. [RequÃªtes et jobs Spark](#requÃªtes-et-jobs-spark)
6. [Benchmarks](#benchmarks)
7. [Tableau de bord](#tableau-de-bord)
8. [Preuves d'exÃ©cution](#preuves-dexÃ©cution)
9. [Preuves d'exÃ©cution](#preuves-dexÃ©cution)

## Architecture

Le flux principal est :

```text
GÃ©nÃ©rateur Python -> MongoDB chatdb -> Connecteur MongoDB-Spark
                  -> Jobs PySpark -> Collections stats_*
                  -> Tableau de bord Streamlit
```

Le dÃ©ploiement est dÃ©crit dans les trois fichiers Compose :

- `deploy/vm1/docker-compose.yml` : MongoDB 1 et Spark Master ;
- `deploy/vm2/docker-compose.yml` : MongoDB 2 et Spark Worker 1 ;
- `deploy/vm3/docker-compose.yml` : MongoDB 3 et Spark Worker 2.

## Organisation du dÃ©pÃ´t

```text
messagerie-mongodb-spark/
â”œâ”€â”€ benchmarks/                 # Mesures natives, index et cohÃ©rence
â”‚   â””â”€â”€ results/                # CSV produits par les mesures
â”œâ”€â”€ config/                     # Configuration MongoDB et Spark
â”œâ”€â”€ dashboard/                 # Application Streamlit
â”œâ”€â”€ data_generator/            # GÃ©nÃ©ration, chargement et contrÃ´le des donnÃ©es
â”œâ”€â”€ deploy/
â”‚   â”œâ”€â”€ vm1/                   # Mongo1 et Spark Master
â”‚   â”œâ”€â”€ vm2/                   # Mongo2 et Spark Worker 1
â”‚   â””â”€â”€ vm3/                   # Mongo3 et Spark Worker 2
â”œâ”€â”€ queries/
â”‚   â”œâ”€â”€ transactional/         # RequÃªtes T01 Ã  T15
â”‚   â””â”€â”€ analytical/            # RequÃªtes A16 Ã  A25
â”œâ”€â”€ schema/                    # CrÃ©ation des index MongoDB
â”œâ”€â”€ scripts/                   # DÃ©marrage, contrÃ´le et failover
â”œâ”€â”€ screenshots/               # Preuves visuelles de la version actuelle
â”œâ”€â”€ spark/
â”‚   â”œâ”€â”€ jobs/                  # Jobs S26 Ã  S30
â”‚   â””â”€â”€ comparaison/           # Comparaisons natives et Spark
â”œâ”€â”€ .gitignore
â”œâ”€â”€ README.md
â””â”€â”€ requirements.txt
```

## Installation

### PrÃ©requis

- Trois VM Ubuntu sur le mÃªme rÃ©seau local ;
- Docker Engine et Docker Compose ;
- Python 3.10 ou plus rÃ©cent ;
- ports `27017`, `7077`, `8080`, `8081`, `8082` et `8501` accessibles selon le rÃ´le.

Aucun fichier `.env` n'est nÃ©cessaire. La configuration fixe est centralisÃ©e
dans `config/settings.py`.

### PrÃ©parer le projet

```bash
git clone <url-du-depot>
cd messagerie-mongodb-spark
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### DÃ©marrer les VM

Sur chaque VM, lancer la commande correspondant Ã  son rÃ´le :

```bash
./scripts/cluster_up.sh vm1
./scripts/cluster_up.sh vm2
./scripts/cluster_up.sh vm3
```

Initialiser ensuite le Replica Set depuis VM1 :

```bash
python3 scripts/init_replica_set.py
python3 scripts/check_cluster.py
```

Le contrÃ´le doit confirmer un PRIMARY, deux SECONDARY et deux workers Spark
actifs.

## DonnÃ©es et schÃ©ma

CrÃ©er les index, gÃ©nÃ©rer les donnÃ©es puis les charger :

```bash
python3 -m schema.create_indexes
python3 -m data_generator.generate_data
python3 -m data_generator.load_data
python3 data_generator/check_data.py
```

Les champs principaux utilisÃ©s par le projet sont `created_at`, `last_login`,
`attachment.size` et le type de message `voice`.

## RequÃªtes et jobs Spark

Les requÃªtes natives sont organisÃ©es en deux familles :

- T01 Ã  T15 : opÃ©rations transactionnelles ;
- A16 Ã  A25 : agrÃ©gations analytiques.

Les jobs distribuÃ©s sont :

| Job | Fonction |
|---|---|
| S26 | Temps moyen de rÃ©ponse |
| S27 | Contacts communs |
| S28 | DÃ©tection du spam |
| S29 | Taux de signalement |
| S30 | RÃ©tention par cohorte |

Lancer un job depuis VM1 :

```bash
./benchmarks/run_spark_job.sh s27_common_contacts
```

## Benchmarks

Les mesures sont Ã©crites dans `benchmarks/results/` :

```bash
python3 benchmarks/run_all.py
python3 benchmarks/index_test.py
python3 benchmarks/consistency_test.py
python3 benchmarks/run_all.py --with-spark
```

Les fichiers `native_vs_spark.csv`, `index_test.csv`,
`consistency_test.csv` et `all_queries.csv` contiennent les rÃ©sultats
produits par les mesures. Les anciennes valeurs ne doivent pas Ãªtre
interprÃ©tÃ©es comme une nouvelle mesure du cluster.

## Tableau de bord

Lancer Streamlit depuis la racine :

```bash
streamlit run dashboard/app.py
```

Le tableau de bord prÃ©sente cinq espaces : vue d'ensemble, usage, abus et
modÃ©ration, engagement et performance. Il lit les collections `stats_*` et
les CSV prÃ©sents dans `benchmarks/results/`. Lorsqu'une donnÃ©e est absente,
la page affiche un message d'information.

## Preuves d'exÃ©cution

Les captures de la version actuelle sont regroupÃ©es dans `screenshots/`.
Elles sont nommÃ©es en franÃ§ais et classÃ©es par Ã©tape.

### Cluster et donnÃ©es

**Ã‰tat du cluster MongoDB**
Cette capture confirme les membres disponibles et leurs rÃ´les dans le Replica Set.
<p align="center"><img src="./screenshots/preuve_cluster_etat.png" width="420" alt="Ã‰tat du cluster MongoDB"></p>

**Initialisation du Replica Set**
Cette capture montre l'initialisation de `rs0` et l'Ã©lection du primaire.
<p align="center"><img src="./screenshots/preuve_initialisation_replica.png" width="420" alt="Initialisation du Replica Set"></p>

**Comptage des collections**
Cette capture prÃ©sente les volumes obtenus dans les collections principales.
<p align="center"><img src="./screenshots/preuve_comptage_donnees.png" width="420" alt="Comptage des collections"></p>

**Tests des index T4 et T6**
Cette capture compare les plans et les temps avec et sans index.
<p align="center"><img src="./screenshots/preuve_tests_index.png" width="420" alt="Tests des index T4 et T6"></p>

### Spark et mesures

**Interface initiale de Spark**
Cette capture confirme que le Master Spark est actif et que les workers sont connectÃ©s.
<p align="center"><img src="./screenshots/preuve_spark_initial.png" width="420" alt="Interface initiale de Spark"></p>

**Job S27 terminÃ©**
Cette capture montre la fin du job Spark et son statut d'exÃ©cution.
<p align="center"><img src="./screenshots/preuve_spark_s27_termine.png" width="420" alt="Job S27 terminÃ©"></p>

**RÃ©sultats des contacts communs S27**
Cette capture prÃ©sente les paires d'utilisateurs ayant des contacts communs.
<p align="center"><img src="./screenshots/preuve_spark_s27_contacts.png" width="420" alt="RÃ©sultats S27"></p>

**Temps de rÃ©ponse S26**
Cette capture prÃ©sente les mesures du temps moyen de rÃ©ponse.
<p align="center"><img src="./screenshots/preuve_spark_s26_reponse.png" width="420" alt="RÃ©sultats S26"></p>

**Taux de signalement S29**
Cette capture prÃ©sente les expÃ©diteurs et leurs taux de signalement.
<p align="center"><img src="./screenshots/preuve_spark_s29_signalements.png" width="420" alt="RÃ©sultats S29"></p>

**Cohortes de rÃ©tention S30**
Cette capture montre les cohortes mensuelles et leur rÃ©tention.
<p align="center"><img src="./screenshots/preuve_spark_s30_cohortes.png" width="420" alt="RÃ©sultats S30"></p>

**Comparaison Spark A16**
Cette capture prÃ©sente la mesure Spark de l'analyse A16.
<p align="center"><img src="./screenshots/preuve_spark_a16.png" width="420" alt="Comparaison Spark A16"></p>

**Comparaison Spark A17**
Cette capture prÃ©sente la mesure Spark de l'analyse A17.
<p align="center"><img src="./screenshots/preuve_spark_a17.png" width="420" alt="Comparaison Spark A17"></p>

**Comparaison Spark A18**
Cette capture prÃ©sente la mesure Spark de l'analyse A18.
<p align="center"><img src="./screenshots/preuve_spark_a18.png" width="420" alt="Comparaison Spark A18"></p>

**Comparaison MongoDB natif et Spark**
Cette capture rÃ©sume les temps et la cohÃ©rence des rÃ©sultats A16 Ã  A18.
<p align="center"><img src="./screenshots/preuve_comparaison_native_spark.png" width="420" alt="Comparaison native et Spark"></p>

**Test de cohÃ©rence des Ã©critures**
Cette capture compare les niveaux de Write Concern et Read Concern.
<p align="center"><img src="./screenshots/preuve_coherence_write_concern.png" width="420" alt="Test de cohÃ©rence"></p>

**Ã‰lection aprÃ¨s failover**
Cette capture montre l'Ã©tat du Replica Set aprÃ¨s l'indisponibilitÃ© d'un nÅ“ud.
<p align="center"><img src="./screenshots/preuve_election_failover.png" width="420" alt="Ã‰lection aprÃ¨s failover"></p>

### Tableau de bord

**Lancement de Streamlit**
Cette capture confirme le dÃ©marrage du serveur du tableau de bord.
<p align="center"><img src="./screenshots/preuve_lancement_streamlit.png" width="420" alt="Lancement de Streamlit"></p>

**Vue d'ensemble**
Cette page prÃ©sente les indicateurs gÃ©nÃ©raux et les messages par jour.
<p align="center"><img src="./screenshots/preuve_dashboard_vue_ensemble.png" width="420" alt="Vue d'ensemble"></p>

**Types de messages**
Cette page prÃ©sente la rÃ©partition des messages par type.
<p align="center"><img src="./screenshots/preuve_dashboard_types.png" width="420" alt="Types de messages"></p>

**Messages par heure**
Cette page montre la distribution horaire des messages.
<p align="center"><img src="./screenshots/preuve_dashboard_heures.png" width="420" alt="Messages par heure"></p>

**Utilisateurs actifs**
Cette page prÃ©sente le classement des utilisateurs les plus actifs.
<p align="center"><img src="./screenshots/preuve_dashboard_utilisateurs.png" width="420" alt="Utilisateurs actifs"></p>

**ModÃ©ration des signalements**
Cette page prÃ©sente les signalements par motif et par statut.
<p align="center"><img src="./screenshots/preuve_dashboard_moderation.png" width="420" alt="ModÃ©ration"></p>

**Taux de signalement**
Cette page prÃ©sente les taux de signalement par expÃ©diteur.
<p align="center"><img src="./screenshots/preuve_dashboard_signalements.png" width="420" alt="Taux de signalement"></p>

**DÃ©tection du spam**
Cette page prÃ©sente les expÃ©diteurs dÃ©tectÃ©s comme spammeurs.
<p align="center"><img src="./screenshots/preuve_dashboard_spam.png" width="420" alt="DÃ©tection du spam"></p>

**RÃ©tention par cohorte**
Cette page prÃ©sente la rÃ©tention mensuelle des utilisateurs.
<p align="center"><img src="./screenshots/preuve_dashboard_retention.png" width="420" alt="RÃ©tention"></p>

**Temps de rÃ©ponse S26**
Cette page prÃ©sente les temps de rÃ©ponse moyens par conversation.
<p align="center"><img src="./screenshots/preuve_dashboard_reponse.png" width="420" alt="Temps de rÃ©ponse"></p>

**Temps moyen des requÃªtes**
Cette page compare le temps moyen des requÃªtes natives.
<p align="center"><img src="./screenshots/preuve_dashboard_requetes.png" width="420" alt="Temps des requÃªtes"></p>

**Performance des index**
Cette page compare les performances avec et sans index pour T4 et T6.
<p align="center"><img src="./screenshots/preuve_dashboard_indexes.png" width="420" alt="Performance des index"></p>

**CohÃ©rence du cluster**
Cette page prÃ©sente les rÃ©sultats des tests de cohÃ©rence.
<p align="center"><img src="./screenshots/preuve_dashboard_coherence.png" width="420" alt="CohÃ©rence"></p>

**Performance native et Spark**
Cette page compare les temps MongoDB natifs et Spark.
<p align="center"><img src="./screenshots/preuve_dashboard_native_spark.png" width="420" alt="Performance native et Spark"></p>
