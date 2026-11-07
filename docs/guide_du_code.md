# Guide Technique & Architecture du Code

Ce document détaille l'organisation de l'espace de travail, le rôle technique de chaque répertoire et fichier, ainsi que le guide d'exécution pour la validation du projet.

---

## 1. Arborescence du Projet

```text
messagerie-mongodb-spark/
│
├── config/                  # Configuration centralisée et variables d'environnement
│   ├── __init__.py
│   └── settings.py          # URI Replica Set (rs0), IPs machines A/B, noms des collections
│
├── data_generator/          # Outils de génération et peuplement du dataset
│   ├── __init__.py
│   ├── generate_data.py     # Algorithmes de création (users, convs, messages, reports, statuts)
│   ├── load_data.py         # Ingestion par lots (batching) et indexation automatique
│   └── check_data.py        # Vérifications de cohérence volumétrique et temporelle
│
├── schema/                  # Modélisation et définitions des index
│   ├── __init__.py
│   ├── create_indexes.py    # Déclaration idempotente des index B-Tree, uniques et TTL
│   └── schema_design.md     # Spécification détaillée des schémas JSON et choix NoSQL
│
├── queries/                 # Implémentation des requêtes de messagerie
│   ├── __init__.py
│   ├── utils.py             # Gestionnaire de connexion, décorateur timed, helpers
│   ├── transactional/       # 15 requêtes CRUD et opérationnelles (T01 à T15)
│   └── analytical/          # 10 pipelines d'agrégation décisionnels (A16 à A25)
│
├── spark/                   # Traitements Big Data distribués (PySpark)
│   ├── __init__.py
│   ├── jobs/                # 5 analyses complexes (S26 à S30)
│   │   ├── s26_avg_response_time.py   # Temps de réponse (Window lag)
│   │   ├── s27_common_contacts.py     # Graphe social & contacts communs (self-join)
│   │   ├── s28_spam_detection.py      # Détection d'attaques de spam (fenêtre 1h)
│   │   ├── s29_report_rate_by_sender.py # Taux de signalement par utilisateur
│   │   └── s30_retention_cohorts.py   # Rétention mensuelle par cohortes
│   └── comparaison/         # Benchmarks comparatifs natif vs Spark
│       ├── cmp_a16.py       # Messages par jour (30j)
│       ├── cmp_a17.py       # Top 10 utilisateurs actifs
│       └── cmp_a18.py       # Répartition par type de message
│
├── benchmarks/              # Bancs de mesure de performance et résilience
│   ├── __init__.py
│   ├── run_all.py           # Orchestrateur global de benchmark
│   ├── run_native_queries.py # Mesures statistiques sur les 25 requêtes natives
│   ├── index_test.py        # Évaluation IXSCAN vs COLLSCAN avec export JSON explain
│   ├── consistency_test.py  # Tests Write Concern (w=1 vs majority) et Read Concern
│   ├── merge_native_spark.py # Fusion et comparaison des métriques Spark / MongoDB
│   └── results/             # Résultats certifiés au format CSV et plans JSON
│
├── dashboard/               # Interface d'observabilité exécutive
│   └── app.py               # Tableau de bord Streamlit (Clean Light Corporate Theme)
│
├── scripts/                 # Scripts d'infrastructure et de résilience
│   └── failover_test.py     # Mesure de bascule et élection en cas de panne du Primaire
│
├── figures/                 # Schémas d'architecture et graphiques haute résolution
│   ├── architecture_systeme.png # Topologie physique multi-machines et cluster
│   ├── modele.png               # Diagramme des entités et relations NoSQL
│   ├── pipeline_donnees.png     # Flux des données opérationnelles et analytiques
│   ├── bascule.png              # Chronologie de l'élection de haute disponibilité
│   ├── dashboard.png            # Vue de synthèse compacte du tableau de bord
│   ├── index_test.png / .pdf    # Histogrammes de gain d'accélération d'index
│   └── native_vs_spark.png/.pdf # Comparatif de latence d'exécution
│
├── report/                  # Documentation académique et livrables finaux
│   └── rapport_technique.md # Rapport d'ingénierie complet et résultats expérimentaux
│
├── generate_all_figures.py  # Générateur des diagrammes de synthèse
└── generate_report_plots.py # Script matplotlib générant les figures PDF/PNG
```

---

## 2. Guide d'Exécution & Commandes Clés

### A. Génération & Ingestion des Données
```bash
# Générer 10 000 utilisateurs, 8 000 conversations et ~85 000 messages
python -m data_generator.load_data

# Vérifier l'intégrité des données
python -m data_generator.check_data
```

### B. Lancement des Benchmarks
```bash
# Exécuter les requêtes natives, les tests d'index et de cohérence
python benchmarks/run_all.py

# Exécuter avec les jobs analytiques Spark (si cluster actif)
python benchmarks/run_all.py --with-spark
```

### C. Test de Haute Disponibilité (Failover)
```bash
# Simuler l'arrêt brutal du Primaire et chronométrer l'élection
python scripts/failover_test.py --mode stop
```

### D. Consultation du Tableau de Bord
```bash
# Démarrer le dashboard Streamlit
streamlit run dashboard/app.py
```
*(Le tableau de bord bascule automatiquement sur les données certifiées en cache CSV si la base de données n'est pas connectée).*
