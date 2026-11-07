# Rapport Technique & Résultats Expérimentaux
## Système de Messagerie Distribuée Haute Performance (MongoDB & Apache Spark)

---

### Résumé Exécutif

Ce projet met en œuvre et évalue une architecture de messagerie distribuée complète, conçue pour concilier des exigences transactionnelles strictes à faible latence (envoi et lecture de messages, pagination, statuts de lecture) et des capacités d'analyse Big Data à large échelle.

L'infrastructure s'articule autour de deux piliers technologiques :
1. **Un Replica Set MongoDB (`rs0`) à 3 nœuds**, déployé sur deux machines physiques distinctes (Machine A et Machine B) garantissant la tolérance aux pannes avec bascule automatique (failover).
2. **Un cluster Apache Spark en mode standalone**, assurant l'extraction, le partitionnement et le traitement analytique distribué sur le volume de messages et le graphe social.

---

### 1. Architecture Système & Déploiement Physique

Le déploiement multi-machines répartit la charge et assure la résilience du quorum en cas d'indisponibilité matérielle :

![Architecture Système](../figures/architecture_systeme.png)

- **Machine A (`192.168.1.50`) :**
  - `mongo1` (port 27017) : Nœud Primaire initial, gestionnaire des écritures.
  - `mongo2` (port 27018) : Nœud Secondaire.
  - `spark-master` & `spark-worker-1` : Coordination et exécution des jobs distribués.
  - `dashboard` (Streamlit, port 8501) : Interface d'observabilité exécutive.
- **Machine B (`192.168.1.51`) :**
  - `mongo3` (port 27017) : Nœud Secondaire garantissant le quorum (3 membres, 2 nécessaires pour la majorité).
  - `spark-worker-2` : Nœud de calcul distribué additionnel (4 cœurs, 4 Go RAM).

---

### 2. Modèle de Données & Stratégie d'Indexation

La conception NoSQL repose sur 5 collections normalisées selon les modèles d'accès applicatifs :

![Modèle Relationnel NoSQL](../figures/modele.png)

#### Collections Principales
- **`users`** : Documents d'utilisateurs, contacts (`Array[String]`), paramètres et statut de connexion.
- **`conversations`** : Conversations 1-to-1 et groupes (`participants[user_id, role]`, `last_message_at`).
- **`messages`** : Événements de messagerie, pièces jointes, réactions, marqueur de suppression douce (`deleted`) et timestamp d'expiration TTL (`expire_at`).
- **`read_status`** : Suivi fin de lecture par paire `(conversation_id, user_id)`.
- **`reports`** : Signalements de modération (`message_id`, `reason`, `status`).

#### Évaluation de l'Indexation (IXSCAN vs COLLSCAN)
L'optimisation des requêtes transactionnelles critiques (T04, T05, T06) a été mesurée rigoureusement par 30 exécutions avec et sans index :

![Accélération par Indexation](../figures/index_test.png)

| Requête | Opération Métier | Sans Index (COLLSCAN) | Avec Index (IXSCAN) | Facteur d'Accélération |
| :--- | :--- | :---: | :---: | :---: |
| **T04** | 50 derniers messages d'un salon | 53.4 ms | 2.6 ms | **x 20.5** |
| **T05** | Pagination temporelle précédente | 54.1 ms | 2.8 ms | **x 19.3** |
| **T06** | Liste des conversations actives | 12.8 ms | 1.1 ms | **x 11.6** |

L'inspection des explain plans (`executionStats`) démontre le passage d'un scan complet de collection (`totalDocsExamined = 85 000`) à une consultation ciblée de l'index B-Tree composé (`totalDocsExamined = 50`), éliminant l'étape mémoire de tri (`SORT stage`).

---

### 3. Pipeline de Données & Traitements Analytiques

L'ingestion et l'exploitation des données suivent un flux bidirectionnel entre le stockage opérationnel et le moteur analytique :

![Pipeline de Données](../figures/pipeline_donnees.png)

#### Traitements Analytiques Spark (S26 à S30)
1. **S26 - Temps de réponse moyen :** Calcul par fenêtre temporelle (`Window.partitionBy().orderBy()`) du délai de réponse moyen entre interlocuteurs privés (médiane : 1.74s).
2. **S27 - Identification des contacts communs :** Auto-jointure asymétrique (`self-join`) sur le graphe social bipartite après explosion des listes de contacts.
3. **S28 - Détection d'attaques de spam :** Détection de fenêtres glissantes de 1h identifiant les utilisateurs diffusant un message textuel identique sur plus de 20 conversations distinctes.
4. **S29 - Taux de signalement abusif :** Jointure entre flux de messages et signalements pour calculer le ratio de toxicité par expéditeur (seuil >= 20 messages).
5. **S30 - Analyse de rétention par cohortes :** Suivi mensuel d'activité à M+1 des utilisateurs selon leur mois d'inscription.

---

### 4. Benchmark Comparatif : MongoDB Natif vs Apache Spark

Une comparaison directe a été effectuée sur les agrégations A16, A17 et A18 pour évaluer la rentabilité du passage à Spark :

![MongoDB Natif vs Spark](../figures/native_vs_spark.png)

| Requête | Description | MongoDB Natif (ms) | Spark Exécution (ms) | Spark Session Init (ms) | Cohérence des Résultats |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **A16** | Messages par jour (30j) | 12.4 ms | 185.0 ms | 1 780 ms | Identique (100%) |
| **A17** | Top 10 utilisateurs actifs | 18.2 ms | 162.0 ms | 1 740 ms | Identique (100%) |
| **A18** | Répartition par type de message | 14.1 ms | 148.0 ms | 1 750 ms | Identique (100%) |

**Enseignements d'ingénierie :**
- Pour des agrégations légères sur des volumétries tenant en cache RAM (< 100k documents), le moteur natif MongoDB en C++ surpasse Spark grâce à l'absence d'overhead réseau et de sérialisation.
- Apache Spark devient indispensable dès que les opérations nécessitent des calculs de graphe (S27), des jointures inter-collections massives (S29) ou des fenêtrages temporels non pris en charge nativement en streaming.

---

### 5. Haute Disponibilité & Résilience (Failover)

Le Replica Set MongoDB a été soumis à des tests d'arrêt brutal du Primaire (`docker stop mongo1`) pour mesurer la réactivité du protocole d'élection Raft/Paxos sous quorum :

![Chronologie de Bascule](../figures/bascule.png)

- **Temps de détection du nœud défaillant :** ~1.20s
- **Phase d'élection du nouveau Primaire :** ~2.42s
- **Durée totale d'interruption d'écriture :** **3.62s** (conforme à l'objectif de SLA < 5s)
- **Succès d'écriture post-élection :** 100% avec `WriteConcern(w="majority")`
- **Réintégration de l'ancien Primaire :** Synchronisation automatique sans perte en 4.10s en tant que Secondaire.

---

### 6. Interface d'Observabilité Exécutive (Dashboard)

Une application Streamlit interactive et compacte (`dashboard/app.py`) a été développée selon une charte graphique épurée (Clean Light Corporate Theme) :

![Dashboard Synthétique](../figures/dashboard.png)

L'ensemble des indicateurs clés (KPIs Replica Set, métriques de latence IXSCAN, distribution des types de messages, ratio de modération) s'affiche sur un écran unique optimisé sans défilement (< 850px), prêt pour l'intégration dans des revues de direction.

