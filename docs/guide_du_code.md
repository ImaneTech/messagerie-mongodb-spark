# Guide du code

Ce document décrit la structure du projet et les points d'entrée pour chaque dossier.

## Structure par dossier

### config/
Contient la configuration centralisée. Commencer par `settings.py` pour comprendre les connexions MongoDB.

### data_generator/
Génération et chargement des données synthétiques. Ouvrir `generate_data.py` pour voir la logique de génération des utilisateurs, conversations et messages avec les cas particuliers (spam, réponses rapides, etc.). Ouvrir `load_data.py` pour le chargement en base.

### schema/
Définition du schéma et des index. Commencer par `schema_design.md` pour la documentation complète, puis `create_indexes.py` pour la création des index.

### queries/
Implémentation des 30 requêtes (15 transactionnelles T01-T15 dans `transactional/`, 10 analytiques A16-A25 dans `analytical/`). Chaque fichier contient une fonction `run()` qui exécute la requête.

### spark/jobs/
Jobs PySpark S26-S30 pour les analyses distribuées. Ouvrir `spark_session.py` pour comprendre la configuration Spark, puis chaque job individuel.

### benchmarks/
Scripts de test et benchmark. Ouvrir `run_all.py` pour lancer tous les tests, `run_native_queries.py` pour les requêtes natives, `index_test.py` pour les tests d'index, `consistency_test.py` pour les tests de cohérence du replica set.

### dashboard/
Application Streamlit. Ouvrir `app.py` pour voir le code du tableau de bord.

## Questions possibles

1. Où est définie l'URI MongoDB ? Réponse : `config/settings.py`, variable `MONGO_URI`
2. Comment générer les données de test ? Réponse : `python -m data_generator.load_data`
3. Quels index existent sur la collection messages ? Réponse : `schema/create_indexes.py` ou `schema/schema_design.md`
4. Comment exécuter une requête transactionnelle ? Réponse : importer le module depuis `queries/transactional/` et appeler `run()`
5. Où est la logique de détection de spam ? Réponse : `spark/jobs/s28_spam_detection.py`
6. Comment lancer tous les benchmarks ? Réponse : `python benchmarks/run_all.py --with-spark`
7. Où trouver les résultats des tests ? Réponse : `benchmarks/results/*.csv`
8. Comment accéder au tableau de bord ? Réponse : `python -m streamlit run dashboard/app.py`
9. Quel est le seuil pour détecter le spam ? Réponse : 20 conversations distinctes en 1 heure, voir `spark/jobs/s28_spam_detection.py` ligne 30
10. Comment fonctionne le TTL des messages éphémères ? Réponse : Index TTL sur `expire_at` avec `expireAfterSeconds=0`, voir `schema/create_indexes.py` lignes 26-30
