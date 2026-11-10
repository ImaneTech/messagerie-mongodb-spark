# Scénario de Démonstration (15 minutes)
## Sujet 04 — Messagerie Distribuée Haute Performance (MongoDB & Apache Spark)
**Étudiante :** Emma — 2e année cycle ingénieur Cyberdéfense et Confiance Numérique (CCN3-ENSAJ)

---

## Chronogramme de la Soutenance (15 min chrono)

```
[00:00 - 02:00] Architecture & Infrastructure physique multi-machines
[02:00 - 05:00] Modèle de données NoSQL, choix Embed vs Reference & Index
[05:00 - 08:00] Démonstration des requêtes transactionnelles (T) & analytiques (A)
[08:00 - 11:00] Traitements distribués Big Data avec Apache Spark & UI Master
[11:00 - 14:00] Tests de résilience : Cohérence (Write/Read Concern) & Bascule (Failover HA)
[14:00 - 15:00] Tableau de bord Streamlit & Conclusion
```

---

## 1. Architecture Système (2 min)

### Ce qu'il faut dire :
> "Notre système repose sur une architecture distribuée déployée sur deux machines physiques interconnectées sur un réseau local dédié :
> - **Machine A (Hôte principal)** : héberge les nœuds MongoDB `mongo1` (Primaire avec priorité 2) et `mongo2` (Secondaire), ainsi que le `spark-master` et le premier exécuteur `spark-worker1`.
> - **Machine B (Nœud distant)** : héberge `mongo3` (Secondaire) pour former un Replica Set à 3 membres (`rs0`), garantissant le quorum de vote, ainsi que `spark-worker2` pour la distribution des calculs.
> Cette topologie respecte le théorème CAP : tolérance aux partitions réseau et consistance forte."

### Ce qu'il faut montrer à l'écran :
1. **Terminal Machine A** :
   ```bash
   python scripts/check_cluster.py
   ```
   *Montrer les 3 membres MongoDB `[OK]` et les 2 Workers Spark `ALIVE`.*
2. **Navigateur** : ouvrir `http://localhost:18080` (Spark Master Web UI) montrant `Alive Workers: 2`, `Cores: 4 Total`, `Memory: 4.0 GiB`.

---

## 2. Modèle de Données & Stratégie d'Indexation (3 min)

### Ce qu'il faut dire :
> "Notre conception est guidée par les patterns d'accès du workload applicatif :
> - **Imbrication (Embedding)** : appliquée aux données de taille bornée lues systématiquement avec le parent : réglages utilisateur (`settings`), pièces jointes (`attachment`), participants de groupe (`participants`), réactions emoji.
> - **Référence (Referencing)** : appliquée aux relations non bornées (1-to-N) pour éviter la saturation du document BSON (limite 16 Mo) et les contentions en écriture : les messages, les statuts de lecture (`read_status`) et les signalements (`reports`).
> - **Indexation ciblée** : nous avons créé 13 index composés et spécialisés, notamment l'index composé `{conversation_id: 1, ts: -1}` sur les messages (T04/T05) et l'index TTL `{expire_at: 1}` pour les messages éphémères (T14)."

### Ce qu'il faut montrer à l'écran :
Afficher la comparaison d'exécution avec et sans index (T04) :
```bash
python -m benchmarks.index_test
```
*Souligner le passage d'un `COLLSCAN` (84 697 documents examinés, ~51 ms) à un `IXSCAN` (50 documents examinés, 2.49 ms) : **gain d'accélération x20.5**.*

---

## 3. Requêtes Natives MongoDB (3 min)

### Ce qu'il faut dire :
> "Nous avons implémenté et validé l'intégralité des 30 requêtes requises :
> - 15 requêtes transactionnelles (T01 à T15) : envoi de message avec mise à jour du salon, pagination par curseur temporel (T05 sans `skip`), soft-delete (T10), réaction atomique sans doublon (T11), TTL automatique (T14).
> - 10 pipelines d'agrégation analytiques (A16 à A25) : activité par jour, distribution horaire, détection de spam et inactivité."

### Ce qu'il faut montrer à l'écran :
```bash
python -m benchmarks.run_native_queries
```
*Montrer l'exécution chronométrée en direct (3 runs par requête, écart-type, médiane et p95).*

---

## 4. Traitements Distribués avec Apache Spark (3 min)

### Ce qu'il faut dire :
> "Les calculs lourds multi-collections et sur graphe sont délégués au cluster Spark via le connecteur officiel MongoDB :
> - **S26** : Calcul du temps de réponse moyen par fonction de fenêtrage glissante (`Window lag`).
> - **S27** : Découverte des contacts en commun par auto-jointure (`self-join` asymétrique `user_a < user_b`).
> - **S28** : Détection d'attaques de spam (messages identiques sur >20 conversations en <1h).
> - **S29 & S30** : Ratios de signalement par jointure et rétention mensuelle par cohortes."

### Ce qu'il faut montrer à l'écran :
Lancer le job Spark S28 (Spam Detection) :
```bash
powershell -File benchmarks/run_spark_job.ps1 s28_spam_detection
# ou sous Linux : ./benchmarks/run_spark_job.sh s28_spam_detection
```
1. Montrer l'exécution sur le cluster (4 cœurs mobilisés).
2. Basculer sur `http://localhost:18080` pour montrer l'application active sous `Running Applications`.
3. Montrer la collection `stats_s28` alimentée dans MongoDB.

---

## 5. Résilience & Haute Disponibilité (Failover) (3 min)

### Ce qu'il faut dire :
> "Nous avons expérimenté les garanties de réplication et la tolérance aux pannes :
> 1. **Write Concern & Read Concern** : avec `w:1`, l'écriture est acquittée dès le Primaire (latence <1ms) ; avec `w:majority`, elle attend la réplication sur au moins 2 nœuds (~2.5ms), protégeant contre le rollback en cas de crash.
> 2. **Bascule automatique (Failover)** : lors de l'arrêt brutal de `mongo1`, le Replica Set détecte la panne et élit automatiquement un nouveau Primaire en **3.62 secondes**, maintenant la continuité d'écriture."

### Ce qu'il faut montrer à l'écran :
Lancer le test de bascule en direct :
```bash
python scripts/failover_test.py --mode stop
```
*Observer : arrêt de mongo1 -> élection de mongo2 ou mongo3 -> écriture réussie avec `w=majority` -> redémarrage de mongo1 qui réintègre le cluster comme Secondaire sans perte de données.*

---

## 6. Dashboard & Conclusion (1 min)

### Ce qu'il faut montrer :
1. Lancer le tableau de bord Streamlit :
   ```bash
   streamlit run dashboard/app.py
   ```
2. Ouvrir `http://localhost:8501`.
3. Présenter la vue exécutive compacte :
   - 6 KPIs temps réel (Volume, Santé Replica Set, Accélération Index x20.5).
   - Graphiques A16 (courbe d'activité), A18 (formats de message), A24 (modération), et comparatif de performance natif vs Spark.

---

## Questions Fréquentes du Jury & Réponses Types

### Q1 : Pourquoi avoir choisi d'imbriquer les participants plutôt que d'utiliser une table d'association ?
**Réponse :** "Dans une messagerie, une conversation a un nombre fini et modéré de participants (généralement < 100). L'imbrication permet de récupérer la métadonnée complète de la conversation et de ses membres en une seule lecture sans jointure (`$lookup`), optimisant la requête critique T06 grâce à l'index multikey `{participants.user_id: 1, last_message_at: -1}`."

### Q2 : Pourquoi Spark est-il plus lent que MongoDB natif sur les requêtes A16 à A18 ?
**Réponse :** "Spark introduit un coût fixe d'initialisation de session, de sérialisation et de transfert réseau (~1.5s à 2s). Sur un volume de 85 000 documents qui tient en mémoire cache RAM de MongoDB, le moteur en C++ de MongoDB avec indexation est imbattable. En revanche, Spark devient nettement supérieur dès qu'il s'agit de jointures massives entre collections (S29), d'auto-jointures combinatoires de graphe (S27) ou de fenêtrages complexes (S26)."

### Q3 : Que se passe-t-il si la Machine A tombe en panne complètement ?
**Réponse :** "La Machine A héberge 2 nœuds (`mongo1` et `mongo2`). Si Machine A tombe, il ne reste que `mongo3` sur Machine B (1 nœud sur 3). Selon le protocole de consensus Raft/Paxos de MongoDB, une majorité absolue est obligatoire pour élire un Primaire (soit $\lfloor 3/2 \rfloor + 1 = 2$ votes). Avec 1 seul vote, `mongo3` ne peut pas s'élire Primaire et bascule en mode Secondaire en lecture seule. Les écritures sont bloquées pour préserver l'intégrité et éviter le syndrome de Split-Brain."

### Q4 : Quelle est la différence entre `w:1` et `w:majority` ?
**Réponse :** "`w:1` acquitte l'écriture dès qu'elle est validée dans le journal du Primaire local. Si le Primaire subit un crash avant de propager l'oplog aux Secondaires, l'écriture est perdue (rollback). `w:majority` n'acquitte l'écriture qu'après confirmation par la majorité des nœuds votants (au moins 2 sur 3), garantissant que l'écriture survivra à toute élection future."

### Q5 : Pourquoi utiliser une pagination par curseur temporel (T05) plutôt que `.skip()` ?
**Réponse :** "`.skip(N)` a une complexité temporelle linéaire $\mathcal{O}(N)$ car MongoDB doit scanner et rejeter $N$ documents en mémoire avant de renvoyer le résultat. Le curseur temporel (`ts < last_seen_ts`) utilise l'arbre B-Tree de l'index pour sauter instantanément au point souhaité en $\mathcal{O}(\log N)$, garantissant un temps de réponse constant quelle que soit la profondeur de défilement dans l'historique."
