# Journal des Modifications (CHANGES.md)
## Branche : `fix/prof-compliance`
**Contexte :** Mise en conformité stricte avec les spécifications du Sujet 04 et le Guide Plateforme ENSAJ.

---

### 1. Phase 0 & 1 — Orientation & Audit Initial
- **Fichiers créés :** [`REPO_MAP.md`](file:///c:/Users/EMMA/messagerie-mongodb-spark/REPO_MAP.md), [`AUDIT.md`](file:///c:/Users/EMMA/messagerie-mongodb-spark/AUDIT.md)
- **Tag de sauvegarde :** `v-before-audit`
- **Rôle :** Cartographie complète de l'existant, comparaison exigence par exigence avec la grille d'évaluation ENSAJ et identification des points bloquants (P0).

---

### 2. Phase 2 — Scripts d'Infrastructure & Cycle de Vie du Cluster
- **Commit :** `209accd` (`feat(infra): add cluster lifecycle scripts and machine-b worker2`)
- **Exigences satisfaites :** Guide §4.8, §4.12, Spécification 3.3.
- **Fichiers ajoutés / modifiés :**
  - [`scripts/init_replica_set.js`](file:///c:/Users/EMMA/messagerie-mongodb-spark/scripts/init_replica_set.js) & [`scripts/init_replica_set.py`](file:///c:/Users/EMMA/messagerie-mongodb-spark/scripts/init_replica_set.py) : Initialisation et reconfiguration idempotentes du Replica Set `rs0` avec 3 membres et priorité 2 sur `mongo1` (Primaire).
  - [`scripts/check_cluster.py`](file:///c:/Users/EMMA/messagerie-mongodb-spark/scripts/check_cluster.py) : Contrôle d'état complet (3 membres MongoDB sains + détection du Primaire, statut du Master Spark et 2 Workers `ALIVE`).
  - [`scripts/cluster_up.sh`](file:///c:/Users/EMMA/messagerie-mongodb-spark/scripts/cluster_up.sh) & [`scripts/cluster_up.ps1`](file:///c:/Users/EMMA/messagerie-mongodb-spark/scripts/cluster_up.ps1) : Démarrage ordonné de la plateforme.
  - [`scripts/cluster_down.sh`](file:///c:/Users/EMMA/messagerie-mongodb-spark/scripts/cluster_down.sh) & [`scripts/cluster_down.ps1`](file:///c:/Users/EMMA/messagerie-mongodb-spark/scripts/cluster_down.ps1) : Procédure d'arrêt propre (Spark d'abord, puis bases de données).
  - [`scripts/restart_after_powercut.sh`](file:///c:/Users/EMMA/messagerie-mongodb-spark/scripts/restart_after_powercut.sh) & [`scripts/restart_after_powercut.ps1`](file:///c:/Users/EMMA/messagerie-mongodb-spark/scripts/restart_after_powercut.ps1) : Implémentation stricte de la séquence de reprise après coupure (Guide §4.8 : Stockage d'abord -> Attente quorum -> Spark Master -> Workers).
  - [`machine-b/docker-compose.yml`](file:///c:/Users/EMMA/messagerie-mongodb-spark/machine-b/docker-compose.yml) : Ajout du service `spark-worker2` pour permettre le déploiement effectif sur la Machine B tout en conservant la possibilité du mode autonome sur Machine A.

---

### 3. Phase 3 — Générateur de Données & Conformité du Schéma
- **Commit :** `c07eabd` (`fix(data): add registered_at, last_seen and last_read_msg_id`)
- **Exigences satisfaites :** Spécification §3.2 (Collections et attributs requis).
- **Fichiers modifiés :**
  - [`data_generator/generate_data.py`](file:///c:/Users/EMMA/messagerie-mongodb-spark/data_generator/generate_data.py) :
    - Alignement de la collection `users` : injection simultanée des attributs spécifiés par le professeur (`registered_at` et `last_seen`) tout en conservant la rétro-compatibilité (`created_at` et `last_login`).
    - Alignement de la collection `read_status` : ajout du champ `last_read_msg_id` (identifiant BSON du dernier message lu) en cohérence avec `last_read_ts`.

---

### 4. Phase 4 — Requêtes Métier & Transactionnelles
- **Commit :** `6fedcb4` (`fix(queries): improve T01 last_message, T11 reactions, T13 unread count, T14 24h TTL`)
- **Exigences satisfaites :** Spécification §3.4 (T01, T11, T13, T14).
- **Fichiers modifiés :**
  - [`queries/transactional/t01_send_message.py`](file:///c:/Users/EMMA/messagerie-mongodb-spark/queries/transactional/t01_send_message.py) : Mise à jour automatique de l'attribut `last_message_at` de la conversation lors de l'envoi d'un message.
  - [`queries/transactional/t11_add_reaction.py`](file:///c:/Users/EMMA/messagerie-mongodb-spark/queries/transactional/t11_add_reaction.py) : Dédoublonnage atomique des réactions par utilisateur (`$pull` de l'ancienne réaction avant `$push`).
  - [`queries/transactional/t13_unread_count.py`](file:///c:/Users/EMMA/messagerie-mongodb-spark/queries/transactional/t13_unread_count.py) : Sélection d'une paire pré-déterminée pour mesurer fidèlement le temps de requête pur (sans boucle de recherche de 200 documents) et exclusion des messages émis par l'utilisateur lui-même (`sender_id != user_id`).
  - [`queries/transactional/t14_ephemeral_messages_ttl.py`](file:///c:/Users/EMMA/messagerie-mongodb-spark/queries/transactional/t14_ephemeral_messages_ttl.py) : Alignement de la durée de vie par défaut à 86 400 secondes (24 heures) conformément au libellé exact de la requête.

---

### 5. Phase 5 & 6 — Jobs Distribués Apache Spark & Benchmarks
- **Commit :** `f85ea04` (`fix(spark): measure 3 runs on distributed actions and improve runner scripts`)
- **Exigences satisfaites :** Spécification §3.5 (mesures des 30 requêtes), Guide §4.7 (mesures de temps Spark sur 3 itérations d'action).
- **Fichiers modifiés :**
  - [`spark/jobs/s27_common_contacts.py`](file:///c:/Users/EMMA/messagerie-mongodb-spark/spark/jobs/s27_common_contacts.py), [`spark/jobs/s29_report_rate_by_sender.py`](file:///c:/Users/EMMA/messagerie-mongodb-spark/spark/jobs/s29_report_rate_by_sender.py), [`spark/jobs/s30_retention_cohorts.py`](file:///c:/Users/EMMA/messagerie-mongodb-spark/spark/jobs/s30_retention_cohorts.py) : Intégration d'un chronométrage sur 3 exécutions de l'action (`collect()`) pour calculer la moyenne de calcul distribué `SPARK_AVG_MS`.
  - [`benchmarks/run_all.py`](file:///c:/Users/EMMA/messagerie-mongodb-spark/benchmarks/run_all.py) & [`benchmarks/run_spark_job.ps1`](file:///c:/Users/EMMA/messagerie-mongodb-spark/benchmarks/run_spark_job.ps1) : Support multiplateforme transparent (PowerShell sous Windows, Bash sous Linux) et résolution portable du répertoire racine.

---

### 6. Phase 10 — Support de Soutenance
- **Commit :** `e3890ed` (`docs: add 15-minute demo script and jury Q&A`)
- **Exigences satisfaites :** Guide §4.12, Préparation de la démonstration de 15 minutes.
- **Fichier ajouté :** [`DEMO_SCRIPT.md`](file:///c:/Users/EMMA/messagerie-mongodb-spark/DEMO_SCRIPT.md) (découpage minuté 0-15 min, commandes exactes à taper, questions pièges du jury avec réponses types).

