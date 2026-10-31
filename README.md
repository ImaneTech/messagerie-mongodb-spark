# Messagerie instantanée : MongoDB + Spark

Plateforme de données d'une application de messagerie (10 000 utilisateurs, conversations privées et de groupe, statuts de lecture, signalements) : **MongoDB** en replica set de 3 nœuds pour le stockage, **Apache Spark** (1 master, 2 workers) pour les analyses distribuées, **Streamlit** pour le tableau de bord.

> Détails techniques du projet : commandes, justification de chaque requête, tests, dépannage.

## Sommaire

1. [Architecture](#1-architecture)
2. [Structure du dépôt](#2-structure-du-dépôt)
3. [Prérequis](#3-prérequis)
4. [Installation et lancement](#4-installation-et-lancement)
5. [Données](#5-données)
6. [Les 30 requêtes](#6-les-30-requêtes)
7. [Jobs Spark](#7-jobs-spark)
8. [Benchmarks et tests](#8-benchmarks-et-tests)
9. [Tableau de bord](#9-tableau-de-bord)
10. [Dépannage](#10-dépannage)
11. [Checklist de démonstration](#11-checklist-de-démonstration)

## 1. Architecture

| Machine | Conteneurs / rôle |
|---|---|
| Machine A (principale) | `mongo1` (PRIMARY, priorité 2), `mongo2`, `spark-master`, 2 workers Spark, scripts Python, Streamlit |
| Machine B (secondaire) | `mongo3` |

Chaîne de traitement : **générateur Python/Faker → MongoDB → PySpark → collections `stats_...` de MongoDB → Streamlit**.

Versions : MongoDB `<version>`, Spark `apache/spark:3.5.3-python3`, connecteur `mongo-spark-connector_2.12:<version>`, Python `<version>`.

Choix de déploiement :
- Le master et les workers Spark restent sur la machine A : les clusters multi-PC sous Windows posent problème avec le réseau WSL2 (NAT).
- Le Wi-Fi est déconseillé (l'adresse IP change et le cluster perd ses nœuds) : utiliser Ethernet ou des IP réservées dans le routeur.

## 2. Structure du dépôt

```
<racine>/
├── machine-a/                # machine A : mongo1, mongo2, spark-master, workers
│   └── docker-compose.yml
├── machine-b/                # machine B : mongo3
│   └── docker-compose.yml
├── schema/
│   └── create_indexes.py     # création des index
├── data_generator/           # générateur Faker et chargement
├── queries/                  # un script par requête (T1..T15, A16..A25)
├── spark/jobs/               # jobs PySpark S26..S30 (montés dans /opt/spark-jobs)
├── benchmarks/
│   ├── run_all.py            # exécute les 30 requêtes, écrit un CSV
│   └── results/              # CSV des temps
├── dashboard/                # application Streamlit
└── README.md
```

## 3. Prérequis

- Docker et Docker Compose sur les deux machines.
- Python 3.10+ avec un environnement virtuel : `pip install -r requirements.txt` (pymongo, faker, pandas, streamlit).
- Réseau local fiable entre A et B (Ethernet de préférence) et port **27017** ouvert dans le pare-feu des deux machines.

## 4. Installation et lancement

### 4.1 Machine A

```bash
git clone <url-du-depot>
cd <racine>
python -m venv venv && source venv/bin/activate      # Windows : venv\Scripts\activate
pip install -r requirements.txt
cd machine-a
docker compose up -d
```

### 4.2 Machine B (mongo3)

```powershell
git pull
# créer machine-b/.env avec les adresses IP de A et B
cd machine-b
docker compose up -d
# ouvrir le port 27017 dans le pare-feu Windows
```

Test réseau dans les deux sens (PowerShell) :

```powershell
Test-NetConnection <ip-machine-A> -Port 27017
Test-NetConnection <ip-machine-B> -Port 27017
```

### 4.3 Vérifications

```bash
docker exec -it mongo1 mongosh --eval "rs.status().members.map(m => [m.name, m.stateStr])"
```

Résultat attendu : **1 PRIMARY et 2 SECONDARY**. Interface du master Spark : `http://<ip-machine-A>:8080` (2 workers `ALIVE`).

## 5. Données

Volumes cibles : 10 000 utilisateurs, 8 000 conversations, au moins 80 000 messages, un statut de lecture par participant, au moins 1 000 signalements.

```bash
python -m schema.create_indexes          # index de chaque collection
python -m data_generator.generate_data  # génération des données
python -m data_generator.load_data      # chargement dans MongoDB
```

Cas particuliers injectés pour que les requêtes donnent des résultats :

| Cas | Requête concernée |
|---|---|
| même texte envoyé dans plus de 20 conversations en 1 h | S28 |
| réponses rapprochées en conversation privée | S26 |
| inscriptions réparties sur plusieurs mois | S30 |
| utilisateurs inactifs depuis 30 jours, conversations sans message depuis 7 jours | A21, A25 |
| groupes de plus de 50 participants | A20 |
| messages éphémères avec `expire_at` | T14 |

Vérification des volumes : `db.<collection>.countDocuments({})` pour chaque collection.

## 6. Les 30 requêtes

### Transactionnelles (T1 à T15)

| ID | Requête | Technique et index |
|---|---|---|
| T1 | Envoyer un message | `insertOne` dans `messages` |
| T2 | Importer 10 000 messages | `insertMany` (`ordered: false`) |
| T3 | Profil d'un utilisateur | `findOne` sur `_id` (indexé par défaut) |
| T4 | 50 derniers messages d'une conversation | `find` + `sort` + `limit(50)` ; index composé (conversation, date décroissante) |
| T5 | 50 messages antérieurs à un message donné | `find` avec filtre `$lt` sur la date + `sort` + `limit` ; même index, pagination par curseur (pas de `skip`) |
| T6 | Conversations d'un utilisateur par dernier message | `find` sur l'identifiant du participant + `sort` sur la date du dernier message ; index sur ces champs |
| T7 | Créer un groupe | `insertOne` ; participants et rôles imbriqués dans la conversation |
| T8 | Ajouter puis retirer un participant | `$push` puis `$pull` sur le tableau des participants |
| T9 | Modifier un message | `updateOne` avec `$set` (contenu, indicateur « modifié ») |
| T10 | Supprimer un message pour tous | suppression logique : `updateOne` avec `$set` sur l'indicateur « supprimé » |
| T11 | Ajouter une réaction | `updateOne` avec `$set` sur la réaction de l'utilisateur (utilisateur vers emoji) |
| T12 | Marquer une conversation comme lue | `updateOne` avec `upsert` sur le statut de lecture (dernier message lu) |
| T13 | Messages non lus dans une conversation | `countDocuments` des messages postérieurs au dernier message lu |
| T14 | Messages éphémères (24 h) | index TTL sur `expire_at` (`expireAfterSeconds`) |
| T15 | Signaler un message | `insertOne` dans `signalements` (référence vers le message) |

### Analytiques natives (A16 à A25)

| ID | Requête | Pipeline d'agrégation |
|---|---|---|
| A16 | Messages par jour sur 30 jours | `$match` (dates), `$group` sur `$dateToString`, `$sort` |
| A17 | Top 10 des utilisateurs actifs | `$group` par expéditeur (`$sum`), `$sort`, `$limit` |
| A18 | Répartition par type de message | `$group` par type |
| A19 | Taille moyenne des pièces jointes par type MIME | `$match` (pièce jointe présente), `$group` (`$avg`) |
| A20 | Groupes de plus de 50 participants | `$match` (type groupe), `$addFields` avec `$size`, `$match` |
| A21 | Utilisateurs inactifs depuis 30 jours | `find` sur la dernière connexion ; index sur ce champ |
| A22 | Messages par heure de la journée | `$group` sur `$hour` |
| A23 | Emoji le plus utilisé | transformation de la map de réactions en tableau, `$unwind`, `$group`, `$sort`, `$limit(1)` |
| A24 | Signalements par motif et statut | `$group` sur (motif, statut) |
| A25 | Conversations sans message depuis 7 jours | `$group` par conversation (`$max` sur la date), `$match` |

### Distribuées avec Spark (S26 à S30)

| ID | Requête | Technique Spark |
|---|---|---|
| S26 | Temps de réponse moyen en privé | `Window.partitionBy(conversation).orderBy(date)` et `F.lag` |
| S27 | Contacts communs entre paires, top 20 | `explode` des contacts, auto-jointure, `groupBy` + `count`, `orderBy`, `limit(20)` |
| S28 | Spam : même contenu dans plus de 20 conversations en 1 h | `groupBy` (expéditeur, contenu, fenêtre d'1 h), `countDistinct` des conversations |
| S29 | Taux de signalement par expéditeur, top 20 | `join` messages et signalements, `groupBy` + `agg`, `orderBy`, `limit(20)` |
| S30 | Rétention par cohorte mensuelle | cohorte = mois d'inscription ; part des utilisateurs actifs le mois suivant |

## 7. Jobs Spark

Les jobs sont dans `spark/jobs/` (monté dans `/opt/spark-jobs` du conteneur `spark-master`) et écrivent leurs résultats dans des collections `stats_...`.

```bash
docker exec -it spark-master /opt/spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  --conf spark.jars.ivy=/tmp/.ivy2 \
  --packages org.mongodb.spark:mongo-spark-connector_2.12:<version> \
  --executor-memory 1g --total-executor-cores 4 \
  /apps/<job>.py
```

Suivi : master `http://<ip-machine-A>:8080`, application en cours `http://<ip-machine-A>:4040`.

Squelette d'un job :

```python
from pyspark.sql import SparkSession, functions as F

spark = (SparkSession.builder.appName("<job>")
         .config("spark.mongodb.read.connection.uri", "<uri>")
         .config("spark.mongodb.write.connection.uri", "<uri>")
         .getOrCreate())
df = spark.read.format("mongodb").option("collection", "messages").load()
# ... transformations ...
res.write.format("mongodb").mode("append").option("collection", "stats_<nom>").save()
spark.stop()
```

## 8. Benchmarks et tests

Chaque mesure est répétée **3 fois** et on retient la moyenne. Pour Spark, le chronomètre entoure une action (`count`, `show`, `write`), car le calcul est paresseux.

```bash
python benchmarks/run_all.py             # 30 requêtes, résultats dans benchmarks/results/*.csv
```

### 8.1 Cohérence (write concern et read concern)
- T1 et T2 avec `w: 1` puis `w: "majority"`.
- Lecture avec `readConcern("local")` puis `readConcern("majority")`.

### 8.2 Index
- T4 et T6 sans puis avec index, avec `explain("executionStats")` : `COLLSCAN` contre `IXSCAN`, documents examinés, temps.

### 8.3 Bascule du primaire

```bash
docker stop mongo1                        # le primaire s'arrête
# mesurer le temps avant qu'un nouveau PRIMARY apparaisse, vérifier que les écritures reprennent
docker start mongo1                       # mongo1 revient comme secondaire, puis redevient primaire (priorité 2)
```

### 8.4 Comparaison natif et Spark
A16, A17 et A18 contre leur équivalent Spark (3 mesures, moyenne).

### Résultats

Les temps moyens des 30 requêtes sont dans `benchmarks/results/`. `<tableau ou lien vers le CSV>`

## 9. Tableau de bord

```bash
streamlit run dashboard/app.py --server.address 0.0.0.0 --server.port 8501
```

Ouvrir `http://<ip-machine-A>:8501`. Il lit les collections `stats_...` écrites par Spark et affiche au moins 3 graphiques : `<messages par jour, répartition par type, messages par heure, top utilisateurs>`, plus une page des temps d'exécution.

## 10. Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| `Address already in use` / port refusé sous Windows | port dans une plage exclue par Windows | `netsh interface ipv4 show excludedportrange protocol=tcp`, choisir un autre port |
| `mongo3` n'apparaît pas dans `rs.status()` | pare-feu ou IP incorrecte | ouvrir le port 27017, vérifier `.env` et `Test-NetConnection` |
| `All masters are unresponsive` | IP du master changée ou port 7077 fermé | IP fixe, vérifier le pare-feu |
| `Initial job has not accepted any resources` | workers absents ou ressources demandées trop grandes | vérifier le port 8080, réduire `--executor-memory` et `--total-executor-cores` |
| `NoSuchMethodError` / `ClassNotFound` | connecteur en `_2.13` avec Spark Scala 2.12 | utiliser `mongo-spark-connector_2.12` |
| Erreur Ivy (`.ivy2 ... FileNotFound`) | cache non accessible en écriture | ajouter `--conf spark.jars.ivy=/tmp/.ivy2` |
| Le cluster perd ses nœuds | Wi-Fi, adresse IP changée | Ethernet ou IP réservées dans le routeur |

## 11. Checklist avant une démonstration

- [ ] Les deux machines répondent au ping et gardent leur adresse IP.
- [ ] `rs.status()` : 1 PRIMARY et 2 SECONDARY.
- [ ] Interface 8080 : 2 workers `ALIVE`.
- [ ] Les données sont chargées et un script PySpark s'exécute sur le cluster.
- [ ] Le test de panne (`docker stop mongo1`) a été essayé et le temps d'élection noté.
- [ ] Le tableau de bord affiche au moins 3 graphiques.
- [ ] Les temps natif et Spark sont mesurés 3 fois et notés.

## Références

- Documentation MongoDB : [write concern](https://www.mongodb.com/docs/manual/reference/write-concern/), [read concern](https://www.mongodb.com/docs/manual/reference/read-concern/), [index TTL](https://www.mongodb.com/docs/manual/core/index-ttl/), [connecteur Spark](https://www.mongodb.com/docs/spark-connector/current/).