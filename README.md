# Messagerie Instantanée : MongoDB Replica Set + Apache Spark

Plateforme de données distribuée pour une application de messagerie instantanée (10 000 utilisateurs, conversations privées et de groupe, statuts de lecture, signalements).

Le stockage hautement disponible est géré par **MongoDB** (Replica Set à 3 nœuds), les analyses et la détection d'abus sont exécutées de façon distribuée via **Apache Spark** (1 Master, 2 Workers), et le suivi opérationnel est rendu visuel via un tableau de bord **Streamlit**.

---

## Sommaire

1. [Architecture & Infrastructure](#1-architecture--infrastructure)
2. [Modélisation & Schémas du Système](#2-modélisation--schémas-du-système)
3. [Structure du Dépôt](#3-structure-du-dépôt)
4. [Prérequis System](#4-prérequis-system)
5. [Installation et Lancement](#5-installation-et-lancement)
6. [Données & Volumétrie](#6-données--volumétrie)
7. [Catalogue des 30 Requêtes](#7-catalogue-des-30-requêtes)
8. [Traitements Distribués PySpark](#8-traitements-distribués-pyspark)
9. [Benchmarks, Sécurité & Failover](#9-benchmarks-sécurité--failover)
10. [Tableau de Bord Streamlit](#10-tableau-de-bord-streamlit)
11. [Guide de Dépannage](#11-guide-de-dépannage)

---

## 1. Architecture & Infrastructure

| Machine | Services / Conteneurs Docker | Rôle & Ports |
|---|---|---|
| **VM1** `192.168.0.100` (Master) | `mongo1`<br>`spark-master`<br>Scripts Python & Streamlit | **PRIMARY** (Port 27017, Priorité 2)<br>Master Spark (Ports 7077, 18080 UI)<br>Dashboard (Port 8501) |
| **VM2** `192.168.0.101` (Worker 1) | `mongo2`<br>`spark-worker1` | **SECONDARY** (Port 27017, Priorité 1)<br>Worker 1 (2 cœurs, 2 Go, Port 18081) |
| **VM3** `192.168.0.102` (Worker 2) | `mongo3`<br>`spark-worker2` | **SECONDARY** (Port 27017, Priorité 1)<br>Worker 2 (2 cœurs, 2 Go, Port 18082) |

- **Chaîne d'exécution :** Générateur Python (Faker) ➔ MongoDB (`chatdb`) ➔ Connecteur Spark-MongoDB ➔ Pipeline PySpark ➔ Collections `stats_...` ➔ Dashboard Streamlit.
- **Versions :** MongoDB 7.0, Spark `3.5.3-python3`, Connecteur `mongo-spark-connector_2.12:10.3.0`, Python 3.10+.

### 1.1 Architecture Système Globale

<p align="center">
  <img src="./screenshots/arch_systeme_global.png" width="100%" alt="Architecture système globale" />
</p>

### 1.2 Flux des Données

<p align="center">
  <img src="./screenshots/arch_flux_donnees.png" width="100%" alt="Flux des données" />
</p>

---

## 2. Modélisation & Schémas du Système

### 2.1 Séquence de Bascule Automatique (Failover — Élection)

<p align="center">
  <img src="./screenshots/failover_sequence.png" width="100%" alt="Diagramme de séquence failover" />
</p>

### 2.2 Timeline du Failover (États de mongo1)

<p align="center">
  <img src="./screenshots/failover_timeline.png" width="100%" alt="Timeline failover" />
</p>

---

## 3. Structure du Dépôt

```text
messagerie-mongodb-spark/
├── benchmarks/              # Scripts de mesures de temps, Write Concern et index
│   └── run_all.py           # Exécution automatisée des 30 requêtes
│   # results/ est gitignored (généré à l'exécution)
├── config/                  # Fichiers de configuration MongoDB & Spark
│   └── settings.py
├── dashboard/               # Interface Web Streamlit
│   └── app.py
├── data_generator/          # Génération par lots (Faker) et injection BSON
│   ├── generate_data.py
│   └── load_data.py
├── machine-a/               # Orchestration Docker Compose VM1 (mongo1 + spark-master)
│   ├── docker-compose.yml
│   └── .env.example
├── machine-b/               # Orchestration Docker Compose VM2 (mongo2 + spark-worker1)
│   ├── docker-compose.yml
│   └── .env.example
├── machine-c/               # Orchestration Docker Compose VM3 (mongo3 + spark-worker2)
│   ├── docker-compose.yml
│   └── .env.example
├── queries/                 # Implémentation PyMongo des requêtes T01-T15 et A16-A25
│   ├── transactional/
│   └── analytical/
├── schema/                  # Initialisation et création des 13 index BSON
│   └── create_indexes.py
├── screenshots/             # Captures d'écran et schémas du système
├── scripts/                 # Scripts système (Failover, simulation de crash)
│   └── failover_test.py
├── spark/                   # Jobs PySpark S26-S30 montés dans /opt/spark-jobs
│   ├── spark_session.py
│   ├── jobs/
│   └── comparaison/
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

---

## 4. Prérequis Système

- **3 Machines Virtuelles Ubuntu** (22.04 ou 24.04 LTS) configurées avec les adresses IP fixes `192.168.0.100`, `192.168.0.101` et `192.168.0.102` sur le même sous-réseau local (cartes réseau configurées en mode **Pont / Bridged**).
- **Docker Engine officiel Linux** avec le plugin Docker Compose v2 (`docker-ce`, `docker-compose-plugin`).
- Utilisateur membre du groupe docker (`sudo usermod -aG docker $USER`).
- **Python 3.10+** avec environnement virtuel (`python3-venv`).
- Pare-feu configuré pour autoriser le trafic inter-machines : `sudo ufw allow from 192.168.0.0/24` (ou désactivé en labo).

---

## 5. Installation et Lancement

### 5.1 Déploiement VM1 `192.168.0.100` (Master)

```bash
git clone https://github.com/votre-repo/messagerie-mongodb-spark.git
cd messagerie-mongodb-spark

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Aucun fichier .env n'est requis : config/settings.py utilise les IPs fixes par défaut.
./scripts/cluster_up.sh a
# ou : cd machine-a && docker compose up -d
```

<p align="center">
  <img src="./screenshots/docker_compose_machine_a.png" width="100%" alt="Docker Compose Machine A — conteneurs démarrés" />
</p>

### 5.2 Déploiement VM2 `192.168.0.101` (Worker 1)

```bash
cd messagerie-mongodb-spark
./scripts/cluster_up.sh b
# ou : cd machine-b && docker compose up -d
```

### 5.3 Déploiement VM3 `192.168.0.102` (Worker 2)

```bash
cd messagerie-mongodb-spark
./scripts/cluster_up.sh c
# ou : cd machine-c && docker compose up -d
```

Vérification de la connectivité réseau inter-machines (depuis VM1) :

```bash
nc -zv 192.168.0.100 27017   # mongo1
nc -zv 192.168.0.101 27017   # mongo2
nc -zv 192.168.0.102 27017   # mongo3
nc -zv 192.168.0.100 7077    # spark-master
```

### 5.4 Initialisation & Validation du Cluster

Une fois les 3 VMs démarrées, initialiser le Replica Set avec les priorités spécifiées (`mongo1` en priorité 2) :

```bash
python scripts/init_replica_set.py
# Ou via mongosh direct sur VM1 :
# docker exec -i mongo1 mongosh --quiet < scripts/init_replica_set.js
```

Vérification de l'ensemble du cluster (MongoDB + Spark) en une seule commande :

```bash
python scripts/check_cluster.py
```

Résultat attendu : **3/3 membres MongoDB en ligne (1 PRIMARY et 2 SECONDARY)** et **2 workers Spark ALIVE**.

Vérification directe via `mongosh` :

```bash
docker exec -it mongo1 mongosh --eval "rs.status().members.map(m => [m.name, m.stateStr])"
```

Résultat attendu : **1 PRIMARY et 2 SECONDARY**.

<p align="center">
  <img src="./screenshots/replica_set_status.png" width="100%" alt="Statut Replica Set — 1 PRIMARY + 2 SECONDARY" />
</p>

- **Spark Master UI :** `http://192.168.0.100:18080` — les 2 workers doivent être `ALIVE`.

<p align="center">
  <img src="./screenshots/spark_master_ui.png" width="100%" alt="Spark Master UI — 2 workers ALIVE" />
</p>

---

## 6. Données & Volumétrie

### Commandes d'initialisation

```bash
python -m schema.create_indexes
python -m data_generator.generate_data
python -m data_generator.load_data
```

### Volumétrie Générée

| Collection | Stratégie | Documents | Description |
|---|---|---|---|
| `users` | Imbriqué | **10 000** | Profils, tableau `contacts[]`, sous-document `settings{}` |
| `conversations` | Imbriqué | **8 000** | Métadonnées, tableau `participants[]` |
| `messages` | Référence | **105 420** | Référence `conversation_id` & `sender_id`, imbrique `attachment{}` et `reactions[]` |
| `read_status` | Séparée | **38 450** | Horodatage `last_read_ts` par participant |
| `reports` | Séparée | **1 420** | Signalements référençant `message_id` |

<p align="center">
  <img src="./screenshots/mongodb_compass_collections.png" width="100%" alt="MongoDB Compass — collections chatdb et volumes" />
</p>

---

## 7. Catalogue des 30 Requêtes

### Transactionnelles (T01 à T15) — Driver PyMongo

| ID | Requête | Implémentation & Indexation |
|---|---|---|
| **T01** | Envoyer un message | `insertOne` dans `messages` + update `$set` sur la conversation |
| **T02** | Importation massive | `insertMany(ordered=False)` par paquets de 5 000 |
| **T03** | Recherche profil utilisateur | `findOne` via index unique `pseudo` |
| **T04** | 50 derniers messages d'un chat | `find` + `sort` + `limit(50)` via index composé `(conversation_id, ts: -1)` |
| **T05** | Pagination des messages antérieurs | Filtre `$lt` par curseur sur l'index de T04 |
| **T06** | Lister les chats d'un membre | Index composé `(participants.user_id, last_message_at: -1)` |
| **T07** | Créer un groupe de discussion | `insertOne` dans `conversations` avec tableau de participants |
| **T08** | Gérer les membres d'un groupe | `$push`, `$pull` et `$inc` |
| **T09** | Édition de texte d'un message | `updateOne` atomique avec `$set` sur le contenu et `is_edited` |
| **T10** | Masquage (Suppression douce) | Update atomique de `is_deleted` |
| **T11** | Réagir avec un emoji | `$push` sur le tableau `reactions` |
| **T12** | Marquer une discussion comme lue | `updateOne` avec `upsert=True` sur `read_status` |
| **T13** | Compter les messages non lus | `countDocuments` avec filtre `$gt` sur `last_read_ts` |
| **T14** | Purge des messages éphémères | Index TTL sur `expire_at` |
| **T15** | Soumettre un signalement | `insertOne` dans `reports` |

### Analytiques Natives (A16 à A25) — Aggregation Pipelines

| ID | Requête | Étapes du Pipeline |
|---|---|---|
| **A16** | Volume de messages par jour | `$match` ➔ `$group` (`$dateToString`) ➔ `$sort` |
| **A17** | Top 10 utilisateurs actifs | `$group` ➔ `$sort` ➔ `$limit(10)` ➔ `$lookup` |
| **A18** | Répartition par type de contenu | `$group` par `type` (text, image, audio) |
| **A19** | Taille moyenne des pièces jointes | `$match` + `$group` (`$avg` sur `size_bytes`) |
| **A20** | Groupes de plus de 50 membres | Filtre sur `type=group` et `participants_count` |
| **A21** | Utilisateurs inactifs depuis 30 jours | Range query indexée sur `last_login` |
| **A22** | Distribution horaire des envois | `$group` sur `$hour` |
| **A23** | Emoji le plus populaire | `$unwind` ➔ `$group` ➔ `$sort` ➔ `$limit(1)` |
| **A24** | Synthèse des motifs de signalement | `$group` sur `(reason, status)` |
| **A25** | Discussions abandonnées | Filtre sur `last_message_at` (≥ 7 jours) |

---

## 8. Traitements Distribués PySpark

Les jobs se trouvent dans `spark/jobs/` et écrivent leurs résultats dans des collections `stats_...` de MongoDB.

### Soumission d'un Job

Depuis VM1 (là où `spark-master` est hébergé) :

```bash
./benchmarks/run_spark_job.sh s28_spam_detection
# ou sous Windows/PowerShell :
# .\benchmarks\run_spark_job.ps1 s28_spam_detection
```

Le script utilise `spark://192.168.0.100:7077` comme master et `192.168.0.100` comme `spark.driver.host`, puis exécute `/workspace/spark/jobs/<job>.py` dans le conteneur `spark-master`.

| ID | Job Spark | Algorithme |
|---|---|---|
| **S26** | Temps de réponse moyen | `Window.partitionBy("conversation_id").orderBy("ts")` + `lag()` |
| **S27** | Contacts communs (Top 20) | `explode()` + Self-Join distribué |
| **S28** | Détection de spammers | Fenêtre 1h, `countDistinct(conversation_id) > 20` |
| **S29** | Taux de messages signalés | Jointure `messages`/`reports` + agrégation |
| **S30** | Rétention par cohorte | Groupement par mois d'inscription + activité M+1 |

---

## 9. Benchmarks, Sécurité & Failover

### 9.1 Exécution

```bash
python benchmarks/run_all.py
python benchmarks/index_test.py
python benchmarks/consistency_test.py
```

### 9.2 Impact du Write Concern

| Mode | Latence T01 | Garantie |
|---|---|---|
| `w: 1` | **2.4 ms** | Acquittement primaire uniquement |
| `w: majority` | **8.1 ms** | Acquittement par ≥ 2 nœuds sur 3 |

### 9.3 Gain apporté par l'Indexation (T04)

| Stratégie | Temps | Documents scannés |
|---|---|---|
| Sans index (`COLLSCAN`) | 68.4 ms | 105 420 |
| Avec index (`IXSCAN`) | **1.2 ms** | 50 |

### 9.4 Test de Bascule Automatique (Failover)

```bash
docker stop mongo1   # arrêt brutal du Primary
docker start mongo1  # réintègre le cluster en tant que SECONDARY
```

**Résultat observé :** élection et promotion de `mongo2` en PRIMARY en **2.4 secondes**.

<p align="center">
  <img src="./screenshots/failover_test_terminal.png" width="100%" alt="Terminal — test de bascule failover" />
</p>

<p align="center">
  <img src="./screenshots/failover_sequence.png" width="100%" alt="Séquence d'élection failover" />
</p>

<p align="center">
  <img src="./screenshots/failover_timeline.png" width="100%" alt="Timeline des états mongo1" />
</p>

---

## 10. Tableau de Bord Streamlit

```bash
streamlit run dashboard/app.py
```

Accessible à `http://localhost:8501` ou `http://192.168.0.100:8501`

### Vue d'ensemble — KPIs et messages par jour (A16)

<p align="center">
  <img src="./screenshots/dashboard_vue_ensemble.png" width="100%" alt="Vue d'ensemble — KPIs et messages par jour" />
</p>

### Usage — Répartition par type de message (A18)

<p align="center">
  <img src="./screenshots/dashboard_usage_type_messages.png" width="100%" alt="Répartition par type de message" />
</p>

### Usage — Messages par heure de la journée (A22)

<p align="center">
  <img src="./screenshots/dashboard_usage_messages_heure.png" width="100%" alt="Messages par heure de la journée" />
</p>

### Usage — Top 10 utilisateurs actifs (A17)

<p align="center">
  <img src="./screenshots/dashboard_usage_top_utilisateurs.png" width="100%" alt="Top 10 utilisateurs actifs" />
</p>

### Abus et modération — Signalements par motif et statut (A24)

<p align="center">
  <img src="./screenshots/dashboard_abus_signalements.png" width="100%" alt="Signalements par motif et statut" />
</p>

### Abus et modération — Taux de signalement par expéditeur (S29)

<p align="center">
  <img src="./screenshots/dashboard_abus_taux_s29.png" width="100%" alt="Taux de signalement S29" />
</p>

### Abus et modération — Expéditeurs de spam détectés (S28)

<p align="center">
  <img src="./screenshots/dashboard_abus_spam_s28.png" width="100%" alt="Expéditeurs de spam S28" />
</p>

### Engagement — Rétention par cohorte mensuelle (S30)

<p align="center">
  <img src="./screenshots/dashboard_engagement_retention_s30.png" width="100%" alt="Rétention par cohorte mensuelle S30" />
</p>

### Engagement — Temps de réponse moyen (S26)

<p align="center">
  <img src="./screenshots/dashboard_engagement_response_s26.png" width="100%" alt="Temps de réponse moyen S26" />
</p>

### Performance — Temps moyen toutes requêtes

<p align="center">
  <img src="./screenshots/dashboard_performance_all_queries.png" width="100%" alt="Temps moyen par requête" />
</p>

### Performance — Comparaison MongoDB natif vs Spark + Tests d'index

<p align="center">
  <img src="./screenshots/dashboard_performance_benchmark.png" width="100%" alt="Benchmark natif vs Spark et tests d'index" />
</p>

---

## 11. Guide de Dépannage

| Problème | Cause Possible | Solution |
|---|---|---|
| `permission denied while trying to connect to the Docker daemon socket` | L'utilisateur n'est pas dans le groupe `docker` sous Ubuntu | Exécuter `sudo usermod -aG docker $USER` puis recharger la session avec `newgrp docker` ou se reconnecter |
| `Spark Master UI : Alive Workers: 0` | Master Spark redémarré ou workers déconnectés après inactivité | Exécuter `docker restart spark-worker1` sur VM2 et `docker restart spark-worker2` sur VM3 pour forcer le ré-enregistrement immédiat auprès du Master |
| `Address already in use` sous Linux | Un service `mongod` ou autre processus tourne déjà sur le port local | Identifier le processus avec `sudo ss -tulpn \| grep :27017` et l'arrêter (`sudo systemctl stop mongod`) |
| `mongo3` absent ou `Host unreachable` | Pare-feu UFW bloquant ou VM non accessible en mode Pont | Vérifier les règles UFW (`sudo ufw allow 27017/tcp` sur VM3) et tester via `nc -zv 192.168.0.102 27017` |
| `Initial job has not accepted any resources` | Workers Spark sans ressources disponibles ou occupés | Vérifier dans `http://192.168.0.100:18080` que les workers sont `ALIVE` et ajuster `--executor-memory 1g` |
| `ClassNotFoundException: MongoTableProvider` | Incompatibilité de version Scala avec Spark 3.5 | Utiliser impérativement le connecteur Scala 2.12 : `org.mongodb.spark:mongo-spark-connector_2.12:10.3.0` |
| Reprise après coupure de courant / arrêt brutal | Inversion de l'ordre de démarrage (Guide §4.8) | Exécuter `./scripts/restart_after_powercut.sh` pour démarrer les bases d'abord, attendre le quorum, puis Spark |
| Dashboard sans données Spark | Jobs S26-S30 non exécutés | Lancer les jobs via `python benchmarks/run_all.py --with-spark` ou vérifier les collections `stats_*` dans MongoDB |
