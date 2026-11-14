# Messagerie MongoDB et Spark

Application de messagerie distribuée construite avec MongoDB Replica Set,
Apache Spark et Streamlit.

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
2. [Organisation du dépôt](#organisation-du-dépôt)
3. [Installation](#installation)
4. [Données et schéma](#données-et-schéma)
5. [Requêtes et jobs Spark](#requêtes-et-jobs-spark)
6. [Benchmarks](#benchmarks)
7. [Tableau de bord](#tableau-de-bord)
8. [Preuves d'exécution](#preuves-dexécution)

## Architecture

**Architecture du système**
Ce schéma présente les VM, le Replica Set MongoDB, le cluster Spark et le
tableau de bord Streamlit.
<p align="center"><img src="./screenshots/preuve_architecture.png" width="700" alt="Architecture du système"></p>

Le déploiement est décrit dans les trois fichiers Compose :

- `deploy/vm1/docker-compose.yml` : MongoDB 1 et Spark Master ;
- `deploy/vm2/docker-compose.yml` : MongoDB 2 et Spark Worker 1 ;
- `deploy/vm3/docker-compose.yml` : MongoDB 3 et Spark Worker 2.

## Organisation du dépôt

```text
messagerie-mongodb-spark/
├── benchmarks/             # Mesures natives, index et cohérence
│   └── results/            # CSV produits par les mesures
├── config/                 # Configuration MongoDB et Spark
├── dashboard/              # Application Streamlit
├── data_generator/         # Génération, chargement et contrôle des données
├── deploy/
│   ├── vm1/                # Mongo1 et Spark Master
│   ├── vm2/                # Mongo2 et Spark Worker 1
│   └── vm3/                # Mongo3 et Spark Worker 2
├── queries/
│   ├── transactional/      # Requêtes T01 à T15
│   └── analytical/         # Requêtes A16 à A25
├── schema/                 # Création des index MongoDB
├── scripts/                # Démarrage, contrôle et failover
├── screenshots/            # Preuves visuelles de la version actuelle
├── spark/
│   ├── jobs/               # Jobs S26 à S30
│   └── comparaison/        # Comparaisons natives et Spark
├── .gitignore
├── README.md
└── requirements.txt
```

## Installation

### Prérequis

- Trois VM Ubuntu sur le même réseau local ;
- Docker Engine et Docker Compose ;
- Python 3.10 ou plus récent ;
- ports `27017`, `7077`, `8080`, `8081`, `8082` et `8501` accessibles selon le rôle.

### Préparer le projet

```bash
git clone <url-du-depot>
cd messagerie-mongodb-spark
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Démarrer les VM

Sur chaque VM, lancer la commande correspondant à son rôle :

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

Le contrôle doit confirmer un PRIMARY, deux SECONDARY et deux workers Spark
actifs.

## Données et schéma

Créer les index, générer les données puis les charger :

```bash
python3 -m schema.create_indexes
python3 -m data_generator.generate_data
python3 -m data_generator.load_data
python3 data_generator/check_data.py
```

Les champs principaux utilisés par le projet sont `created_at`, `last_login`,
`attachment.size` et le type de message `voice`.

## Requêtes et jobs Spark

Les requêtes natives sont organisées en deux familles :

- T01 à T15 : opérations transactionnelles ;
- A16 à A25 : agrégations analytiques.

Les jobs distribués sont :

| Job | Fonction |
|---|---|
| S26 | Temps moyen de réponse |
| S27 | Contacts communs |
| S28 | Détection du spam |
| S29 | Taux de signalement |
| S30 | Rétention par cohorte |

Lancer un job depuis VM1 :

```bash
./benchmarks/run_spark_job.sh s27_common_contacts
```

## Benchmarks

Les mesures sont écrites dans `benchmarks/results/` :

```bash
python3 benchmarks/run_all.py
python3 benchmarks/index_test.py
python3 benchmarks/consistency_test.py
python3 benchmarks/run_all.py --with-spark
```

Les fichiers `native_vs_spark.csv`, `index_test.csv`,
`consistency_test.csv` et `all_queries.csv` contiennent les résultats
produits par les mesures. Les anciennes valeurs ne doivent pas être
interprétées comme une nouvelle mesure du cluster.

### Résultats des benchmarks et de la tolérance aux pannes

**Test de tolérance aux pannes**
Cette capture confirme les trois essais de coupure de `mongo1`, ainsi que la
moyenne et la médiane de l'interruption des écritures.
<p align="center"><img src="./screenshots/preuve_failover_resultats_vm.png" width="420" alt="Résultats du failover"></p>

**Comparaison MongoDB natif et Spark**
Cette capture confirme l'équivalence des résultats A16, A17 et A18 entre les
requêtes natives et les jobs Spark.
<p align="center"><img src="./screenshots/preuve_comparaison_csv_vm.png" width="420" alt="Comparaison MongoDB natif et Spark"></p>

**Exécution détaillée du job A16**
Cette capture montre les volumes journaliers traités par Spark et l'écriture
des statistiques.
<p align="center"><img src="./screenshots/preuve_spark_s26_vm.png" width="420" alt="Exécution du job A16 sur Spark"></p>

### Mesure de la bascule

Le test mesure la reprise des écritures après le changement de primaire. Il
utilise une collection dédiée, réalise trois essais par défaut et écrit les
résultats dans `benchmarks/results/failover_test.csv`.

```bash
python3 scripts/failover_test.py --mode stop
```

La durée mesurée correspond au temps entre la dernière écriture réussie avant
la panne et la première écriture réussie après la reprise.

## Tableau de bord

Lancer Streamlit depuis la racine :

```bash
streamlit run dashboard/app.py
```

Le tableau de bord présente cinq espaces : vue d'ensemble, usage, abus et
modération, engagement et performance, avec des graphiques et des indicateurs.

## Preuves d'exécution

Les preuves sont regroupées dans `screenshots/`, avec des titres et
des descriptions courtes.

### Cluster et données

**tat du cluster MongoDB**
Cette capture confirme les membres disponibles et leurs rôles dans le Replica Set.
<p align="center"><img src="./screenshots/preuve_cluster_etat.png" width="420" alt="tat du cluster MongoDB"></p>

**Initialisation du Replica Set**
Cette capture montre l'initialisation de `rs0` et l'élection du primaire.
<p align="center"><img src="./screenshots/preuve_initialisation_replica.png" width="420" alt="Initialisation du Replica Set"></p>

**Comptage des collections**
Cette capture présente les volumes obtenus dans les collections principales.
<p align="center"><img src="./screenshots/preuve_comptage_donnees.png" width="420" alt="Comptage des collections"></p>

**Tests des index T4 et T6**
Cette capture compare les plans et les temps avec et sans index.
<p align="center"><img src="./screenshots/preuve_tests_index.png" width="420" alt="Tests des index T4 et T6"></p>

### Spark et mesures

**Interface initiale de Spark**
Cette capture confirme que le Master Spark est actif et que les workers sont connectés.
<p align="center"><img src="./screenshots/preuve_spark_initial.png" width="420" alt="Interface initiale de Spark"></p>

**Jobs Spark exécutés**
Cette capture présente les applications Spark terminées et en cours d'exécution.
<p align="center"><img src="./screenshots/preuve_spark_jobs.png" width="420" alt="Jobs Spark exécutés"></p>

**Job S27 terminé**
Cette capture montre la fin du job Spark et son statut d'exécution.
<p align="center"><img src="./screenshots/preuve_spark_s27_termine.png" width="420" alt="Job S27 terminé"></p>

**Résultats des contacts communs S27**
Cette capture présente les paires d'utilisateurs ayant des contacts communs.
<p align="center"><img src="./screenshots/preuve_spark_s27_contacts.png" width="420" alt="Résultats S27"></p>

**Temps de réponse S26**
Cette capture présente les mesures du temps moyen de réponse.
<p align="center"><img src="./screenshots/preuve_spark_s26_reponse.png" width="420" alt="Résultats S26"></p>

**Taux de signalement S29**
Cette capture présente les expéditeurs et leurs taux de signalement.
<p align="center"><img src="./screenshots/preuve_spark_s29_signalements.png" width="420" alt="Résultats S29"></p>

**Cohortes de rétention S30**
Cette capture montre les cohortes mensuelles et leur rétention.
<p align="center"><img src="./screenshots/preuve_spark_s30_cohortes.png" width="420" alt="Résultats S30"></p>

**Comparaison Spark A16**
Cette capture présente la mesure Spark de l'analyse A16.
<p align="center"><img src="./screenshots/preuve_spark_a16.png" width="420" alt="Comparaison Spark A16"></p>

**Comparaison Spark A17**
Cette capture présente la mesure Spark de l'analyse A17.
<p align="center"><img src="./screenshots/preuve_spark_a17.png" width="420" alt="Comparaison Spark A17"></p>

**Comparaison Spark A18**
Cette capture présente la mesure Spark de l'analyse A18.
<p align="center"><img src="./screenshots/preuve_spark_a18.png" width="420" alt="Comparaison Spark A18"></p>

**Comparaison MongoDB natif et Spark**
Cette capture résume les temps et la cohérence des résultats A16 à A18.
<p align="center"><img src="./screenshots/preuve_comparaison_native_spark.png" width="420" alt="Comparaison native et Spark"></p>

**Comparaison finale sur la VM**
Cette capture confirme que les résultats A16, A17 et A18 sont cohérents entre MongoDB et Spark.
<p align="center"><img src="./screenshots/preuve_comparaison_vm.png" width="420" alt="Comparaison finale sur la VM"></p>

**Test de cohérence des écritures**
Cette capture compare les niveaux de Write Concern et Read Concern.
<p align="center"><img src="./screenshots/preuve_coherence_write_concern.png" width="420" alt="Test de cohérence"></p>

**lection après failover**
Cette capture montre l'état du Replica Set après l'indisponibilité d'un nud.
<p align="center"><img src="./screenshots/preuve_election_failover.png" width="420" alt="lection après failover"></p>

**Écritures pendant le failover**
Cette capture montre les écritures réussies pendant le test de bascule.
<p align="center"><img src="./screenshots/preuve_failover_ecritures_vm.png" width="420" alt="Écritures pendant le failover"></p>

**Fichier de résultats du failover**
Cette capture montre le fichier CSV généré après le test.
<p align="center"><img src="./screenshots/preuve_failover_csv_vm.png" width="420" alt="Fichier de résultats du failover"></p>

### Tableau de bord

**Lancement de Streamlit**
Cette capture confirme le démarrage du serveur du tableau de bord.
<p align="center"><img src="./screenshots/preuve_lancement_streamlit.png" width="420" alt="Lancement de Streamlit"></p>

**Vue d'ensemble**
Cette page présente les indicateurs généraux et les messages par jour.
<p align="center"><img src="./screenshots/preuve_dashboard_vue_ensemble.png" width="420" alt="Vue d'ensemble"></p>

**Types de messages**
Cette page présente la répartition des messages par type.
<p align="center"><img src="./screenshots/preuve_dashboard_types.png" width="420" alt="Types de messages"></p>

**Messages par heure**
Cette page montre la distribution horaire des messages.
<p align="center"><img src="./screenshots/preuve_dashboard_heures.png" width="420" alt="Messages par heure"></p>

**Utilisateurs actifs**
Cette page présente le classement des utilisateurs les plus actifs.
<p align="center"><img src="./screenshots/preuve_dashboard_utilisateurs.png" width="420" alt="Utilisateurs actifs"></p>

**Modération des signalements**
Cette page présente les signalements par motif et par statut.
<p align="center"><img src="./screenshots/preuve_dashboard_moderation.png" width="420" alt="Modération"></p>

**Taux de signalement**
Cette page présente les taux de signalement par expéditeur.
<p align="center"><img src="./screenshots/preuve_dashboard_signalements.png" width="420" alt="Taux de signalement"></p>

**Détection du spam**
Cette page présente les expéditeurs détectés comme spammeurs.
<p align="center"><img src="./screenshots/preuve_dashboard_spam.png" width="420" alt="Détection du spam"></p>

**Rétention par cohorte**
Cette page présente la rétention mensuelle des utilisateurs.
<p align="center"><img src="./screenshots/preuve_dashboard_retention.png" width="420" alt="Rétention"></p>

**Temps de réponse S26**
Cette page présente les temps de réponse moyens par conversation.
<p align="center"><img src="./screenshots/preuve_dashboard_reponse.png" width="420" alt="Temps de réponse"></p>

**Temps moyen des requêtes**
Cette page compare le temps moyen des requêtes natives.
<p align="center"><img src="./screenshots/preuve_dashboard_requetes.png" width="420" alt="Temps des requêtes"></p>

**Performance des index**
Cette page compare les performances avec et sans index pour T4 et T6.
<p align="center"><img src="./screenshots/preuve_dashboard_indexes.png" width="420" alt="Performance des index"></p>

**Cohérence du cluster**
Cette page présente les résultats des tests de cohérence.
<p align="center"><img src="./screenshots/preuve_dashboard_coherence.png" width="420" alt="Cohérence"></p>

**Performance native et Spark**
Cette page compare les temps MongoDB natifs et Spark.
<p align="center"><img src="./screenshots/preuve_dashboard_native_spark.png" width="420" alt="Performance native et Spark"></p>
