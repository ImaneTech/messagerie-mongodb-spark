# Inventaire des fichiers Python — Étape A

> Généré le 2026-01-11. Aucune suppression n'a été effectuée dans cette étape.

## Tableau complet

| Fichier | Taille (octets) | Utilisé ailleurs | Action |
|---------|-----------------|------------------|--------|
| `benchmarks/__init__.py` | 0 | non (fichier vide) | garder (marqueur de package) |
| `benchmarks/consistency_test.py` | 6 319 | oui (lancé par `run_all.py`) | garder |
| `benchmarks/index_test.py` | 5 491 | oui (lancé par `run_all.py`) | garder |
| `benchmarks/merge_native_spark.py` | 9 717 | oui (mentionné dans README, utilisé pour `native_vs_spark.csv`) | garder |
| `benchmarks/run_all.py` | 5 132 | oui (point d'entrée principal des benchmarks) | garder |
| `benchmarks/run_explain.py` | 6 992 | oui (produit `explain_*.json`) | garder |
| `benchmarks/run_native_queries.py` | 8 232 | oui (lancé par `run_all.py`) | garder |
| `config/__init__.py` | 0 | non (fichier vide) | garder (marqueur de package) |
| `config/settings.py` | 415 | oui (importé par presque tous les fichiers) | garder |
| `dashboard/app.py` | 15 898 | oui (application Streamlit principale) | garder |
| `data_generator/__init__.py` | 0 | non (fichier vide) | garder (marqueur de package) |
| `data_generator/check_data.py` | 9 730 | non (script one-shot de vérification) | **garder** (protégé par règles absolues) |
| `data_generator/generate_data.py` | 16 753 | oui (importé par `load_data.py`) | garder |
| `data_generator/load_data.py` | 3 408 | oui (script de chargement principal) | garder |
| `queries/__init__.py` | 0 | non (fichier vide) | garder (marqueur de package) |
| `queries/analytical/__init__.py` | 0 | non (fichier vide) | garder (marqueur de package) |
| `queries/analytical/a16_messages_per_day.py` | 1 904 | oui (importé par `run_native_queries.py`) | garder |
| `queries/analytical/a17_top_active_users.py` | 1 532 | oui (importé par `run_native_queries.py`) | garder |
| `queries/analytical/a18_messages_by_type.py` | 1 038 | oui (importé par `run_native_queries.py`) | garder |
| `queries/analytical/a19_avg_attachment_size_by_mime.py` | 1 297 | oui (importé par `run_native_queries.py`) | garder |
| `queries/analytical/a20_groups_over_50.py` | 1 154 | oui (importé par `run_native_queries.py`) | garder |
| `queries/analytical/a21_inactive_users_30d.py` | 1 055 | oui (importé par `run_native_queries.py`) | garder |
| `queries/analytical/a22_messages_per_hour.py` | 1 086 | oui (importé par `run_native_queries.py`) | garder |
| `queries/analytical/a23_top_emoji.py` | 1 116 | oui (importé par `run_native_queries.py`) | garder |
| `queries/analytical/a24_reports_by_reason_status.py` | 1 184 | oui (importé par `run_native_queries.py`) | garder |
| `queries/analytical/a25_conversations_idle_7d.py` | 1 192 | oui (importé par `run_native_queries.py`) | garder |
| `queries/transactional/__init__.py` | 0 | non (fichier vide) | garder (marqueur de package) |
| `queries/transactional/t01_send_message.py` | 2 159 | oui (importé par `run_native_queries.py`) | garder |
| `queries/transactional/t02_bulk_import_messages.py` | 2 257 | oui (importé par `run_native_queries.py`) | garder |
| `queries/transactional/t03_user_profile.py` | 1 048 | oui (importé par `run_native_queries.py`) | garder |
| `queries/transactional/t04_last_50_messages.py` | 2 185 | oui (importé par `run_native_queries.py`) | garder |
| `queries/transactional/t05_previous_page.py` | 2 014 | oui (importé par `run_native_queries.py`) | garder |
| `queries/transactional/t06_user_conversations.py` | 2 199 | oui (importé par `run_native_queries.py`) | garder |
| `queries/transactional/t07_create_group.py` | 2 110 | oui (importé par `run_native_queries.py`) | garder |
| `queries/transactional/t08_add_remove_participant.py` | 2 783 | oui (importé par `run_native_queries.py`) | garder |
| `queries/transactional/t09_edit_message.py` | 2 549 | oui (importé par `run_native_queries.py`) | garder |
| `queries/transactional/t10_soft_delete_message.py` | 2 351 | oui (importé par `run_native_queries.py`) | garder |
| `queries/transactional/t11_add_reaction.py` | 1 911 | oui (importé par `run_native_queries.py`) | garder |
| `queries/transactional/t12_mark_conversation_read.py` | 2 896 | oui (importé par `run_native_queries.py`) | garder |
| `queries/transactional/t13_unread_count.py` | 4 308 | oui (importé par `run_native_queries.py`) | garder |
| `queries/transactional/t14_ephemeral_messages_ttl.py` | 2 020 | oui (importé par `run_native_queries.py`) | garder |
| `queries/transactional/t15_report_message.py` | 1 800 | oui (importé par `run_native_queries.py`) | garder |
| `queries/utils.py` | 3 164 | oui (importé par tous les fichiers de requêtes) | garder |
| `schema/__init__.py` | 0 | non (fichier vide) | garder (marqueur de package) |
| `schema/create_indexes.py` | 2 719 | oui (importé par `load_data.py`) | garder |
| `spark/__init__.py` | 0 | non (fichier vide) | garder (marqueur de package) |
| `spark/jobs/cmp_a16.py` | 2 025 | oui (lancé par `run_spark_job.ps1`) | garder |
| `spark/jobs/cmp_a17.py` | 1 878 | oui (lancé par `run_spark_job.ps1`) | garder |
| `spark/jobs/cmp_a18.py` | 1 764 | oui (lancé par `run_spark_job.ps1`) | garder |
| `spark/jobs/s26_avg_response_time.py` | 4 025 | oui (lancé par `run_spark_job.ps1`) | garder |
| `spark/jobs/s27_common_contacts.py` | 1 778 | oui (lancé par `run_spark_job.ps1`) | garder |
| `spark/jobs/s28_spam_detection.py` | 2 241 | oui (lancé par `run_spark_job.ps1`) | garder |
| `spark/jobs/s29_report_rate_by_sender.py` | 1 899 | oui (lancé par `run_spark_job.ps1`) | garder |
| `spark/jobs/s30_retention_cohorts.py` | 2 436 | oui (lancé par `run_spark_job.ps1`) | garder |
| `spark/spark_session.py` | 730 | non référencé directement (les jobs Spark créent leur propre session) | garder (utilitaire réutilisable) |
| `spark/test_mongo.py` | 690 | **non** — aucune référence dans le repo | **supprimer** |

---

## Fichiers spécifiques vérifiés

| Fichier | Verdict | Justification |
|---------|---------|---------------|
| `spark/test_mongo.py` | **SUPPRIMER** | Script one-shot de connectivité, non référencé dans aucun `.py`, `.ps1`, `.md`, `.txt` du repo |
| `benchmarks/run_spark_job.ps1` | garder (non-Python) | Référencé dans README et dans `run_all.py` via `subprocess` |
| `benchmarks/__init__.py` et autres `__init__.py` vides | garder | Tous dans des packages Python actifs (importés en production) |
| `benchmarks/results/benchmarks.json` | n'existe pas | Remplacé par CSV ; `run_native_queries.py` le supprime déjà si présent |
| `diag_*.py`, `check_a*.py` | n'existent pas | Aucun fichier de ce type trouvé dans le repo |

---

## Avertissements ruff / pyflakes

> `ruff` et `pyflakes` sont absents du venv. Analyse statique manuelle effectuée.

### Imports inutilisés confirmés

| Fichier | Import inutilisé | Détail |
|---------|-----------------|--------|
| `benchmarks/index_test.py` | `from pymongo import DESCENDING` | `DESCENDING` importé mais jamais utilisé dans le corps du fichier (les tris sont passés sous forme de dict `{"ts": -1}`) |
| `queries/analytical/a18_messages_by_type.py` | `extract_index_name` (depuis `queries.utils`) | Importé dans la ligne `from queries.utils import ..., extract_index_name` mais non appelé dans le corps |
| Tous les 25 fichiers T01–T15, A16–A25 | `MONGO_DB` (depuis `config.settings`) | Importé via `from config.settings import MONGO_DB, COLLECTIONS` mais jamais référencé dans le corps — `get_db()` l'encapsule |

### Imports potentiellement redondants (non confirmés comme bugs)

| Fichier | Observation |
|---------|-------------|
| `queries/utils.py` | `record_benchmark()` écrit encore dans `benchmarks.json` (format obsolète) mais la fonction reste appelée par les 25 fichiers de requêtes. À supprimer en même temps que la fonction si on nettoie |
| `spark/jobs/*.py` (tous) | `import time` utilisé pour le timing — OK |
| `dashboard/app.py` | `import sys` présent mais seul `sys.path.insert` en tête est utilisé (pattern standard) |

### Code mort identifié

| Fichier | Observation |
|---------|-------------|
| `queries/utils.py` — `record_benchmark()` | Écrit dans `benchmarks/results/benchmarks.json`, fichier déclaré obsolète (remplacé par CSV). La fonction reste appelée par les 25 fichiers de requêtes ; à supprimer dans une étape ultérieure si souhaité |
| `spark/spark_session.py` | Utilitaire non importé par les jobs Spark actuels (chaque job crée sa propre `SparkSession`). Non référencé — à évaluer lors du nettoyage |

---

## Résumé des actions proposées (étape suivante)

| Action | Fichiers concernés | Risque |
|--------|-------------------|--------|
| Supprimer | `spark/test_mongo.py` | nul (non référencé) |
| Supprimer import inutilisé | `benchmarks/index_test.py` : `DESCENDING` | faible |
| Supprimer import inutilisé | `queries/analytical/a18_messages_by_type.py` : `extract_index_name` | faible |
| Supprimer import inutilisé | 25 fichiers T01–T15 + A16–A25 : `MONGO_DB` | faible |
