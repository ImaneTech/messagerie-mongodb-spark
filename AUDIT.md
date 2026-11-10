# AUDIT — Sujet 04 Messagerie (MongoDB + Spark)

Date : 2026-11-10 — Phase 1, lecture seule. Légende : ✅ OK · 🟡 partiel · ❌ manquant/faux · ⛔ bloquant (P0).

> ⚠️ Avertissement méthodologique : le cluster n'est pas joignable depuis cette machine (Docker Desktop arrêté, machine B injoignable). Les statuts « OK » ci-dessous signifient *implémenté dans le code* ; les mesures réelles restent à re-valider par Emma (commandes fournies en Phase 6).

---

## 1. Données (exigence 3.2)

| # | Exigence | Statut | Preuve | Correctif | Priorité |
|---|---|---|---|---|---|
| 1.1 | 10 000 utilisateurs : id, pseudo, téléphone, pays, date inscription, contacts, paramètres, dernière connexion | 🟡 | `generate_data.py` produit `_id, pseudo, phone, country, created_at, contacts[], settings{}, last_login` — **noms ≠ spec** (`registered_at`→`created_at`, `last_seen`→`last_login`). Champs tous présents | Renommer ou documenter le mapping dans le README/rapport (recommandé : aligner les noms sur la spec) | P1 |
| 1.2 | 8 000 conversations : type, nom, participants+rôles, date création | ✅ | `generate_conversations` : 7 800 privées + 200 groupes = 8 000 ; `participants[{user_id, role}]`, `created_at`, `type`, `name` | — | — |
| 1.3 | ≥80 000 messages : conv, ts, expéditeur, type, contenu, PJ (nom/taille/MIME), réactions (user→emoji), modifié, supprimé | 🟡 | ~85 000 + spam + back-and-forth ≈ 88k ✅ volumes ; `attachment{name,size,mime}` ✅ ; `edited`/`edited_at`, `deleted`/`deleted_at` ✅ ; **réactions = tableau `[{user_id, emoji}]`** (spec : « utilisateur vers emoji » — acceptable, mais un document `{user_id: emoji}` serait plus fidèle et simplifierait A23) | Trancher : garder le tableau (défendable) ou migrer vers map. Documenter le choix | P2 |
| 1.4 | Statuts de lecture : conv, user, dernier message lu | 🟡 | `read_status{conversation_id, user_id, last_read_ts}` — spec demande `last_read_msg_id` **ou** équivalent ; `last_read_ts` est défendable mais T13 ne l'exploite pas correctement (voir 4.13) | Ajouter `last_read_msg_id` ou justifier le timestamp | P1 |
| 1.5 | ≥1 000 signalements : message, rapporteur, motif, statut | ✅ | `generate_reports(total_reports=1200)` + `created_at` | — | — |
| 1.6 | ≥50 000 éléments au total | ✅ | ~10k+8k+~88k+~38k+1.4k ≈ **145k** (README annonce 105 420 messages — à revérifier par un `count` réel) | Re-mesurer et corriger le README | P1 |
| 1.7 | Générateur Python/Faker, reproductible | ✅ | `seed=42` partout, `Faker.seed` ; `generate_all()` existe mais `load_data.py` duplique la logique d'appel | Factoriser via `generate_all()` | P2 |

## 2. Types composites (exigence)

| Exigence | Statut | Preuve |
|---|---|---|
| Documents imbriqués | ✅ | `settings{}`, `attachment{}`, `participants[]` |
| Tableaux | ✅ | `contacts[]`, `participants[]`, `reactions[]` |
| Dates BSON | ✅ | `created_at`, `last_login`, `ts`, `expire_at`, `last_message_at`, `last_read_ts` = `datetime` Python → BSON Date (pas de strings) |

## 3. Infrastructure (exigence 3.3 + guide §4)

| # | Exigence | Statut | Preuve | Correctif | Priorité |
|---|---|---|---|---|---|
| 3.1 | Replica set de 3 nœuds | 🟡 | mongo1+mongo2 (A), mongo3 (B) — **mais aucun script `rs.initiate`** ; initiation non reproductible, priorités non versionnées | Créer `scripts/init_replica_set.js` (mongo1 priority 2, hostnames `IP:port` joignables depuis B) | **P0** |
| 3.2 | Compare write/read concerns + failover | ✅ | `consistency_test.py` (w=1/majority/3, local/majority) + `scripts/failover_test.py` | Ajouter test « 1 membre arrêté / 2 arrêtés » (guide §4.8) — partiel : failover_test couvre l'élection, pas la perte de quorum | P1 |
| 3.3 | Spark 1 master + 2 workers + connecteur MongoDB | 🟡 | **Les 2 workers sont sur machine A** ; la cible Emma est worker2 sur B | Déplacer `spark-worker2` dans `machine-b/docker-compose.yml` (worker distant : `spark://<IP_A>:7077`, `SPARK_PUBLIC_DNS=<IP_B>`) — **décision à confirmer** (voir §décisions) | P1 |
| 3.4 | Versions épinglées compatibles | ✅ | spark:3.5.3-python3 + connector `_2.12:10.3.0` ; attention pyspark pip=3.5.1 (local seulement) | Aligner `requirements.txt` pyspark==3.5.3 ou documenter | P2 |
| 3.5 | Docker Compose « recommandé » | 🟡 | Deux compose par machine, réseau **bridge** (guide impose **host network**) | ⚠️ Dilemme : host network casse le port-offset mongo2=27018/mongo3=27019 (conflit même machine pour mongo1/mongo2) et la résolution des noms. **Recommandation : garder bridge** (justifié : 2 mongod sur A) et documenter l'écart au guide, OU passer en host avec ports 27017/27018 sur A et 27017 sur B. Trancher avec Emma | **P0** (décision) |
| 3.6 | mongo3 joignable par tous (hostnames/IPs joignables inter-machines) | ❓ | URI = `mongo1:27017,mongo2:27018,mongo3:27019` — `mongo3` n'existe pas dans le réseau bridge de A **sauf si** les compose partagent un réseau externe. Aucun `external: true` / `docker network` dans les fichiers → mongo3 est probablement **injoignable** par les scripts de A et par les workers Spark | Déclarer un réseau Docker **external** partagé (`chat_net` créé une fois, `external: true` dans les 2 compose) OU utiliser les IPs `192.168.0.195:27019` | **P0** |
| 3.7 | Scripts start/stop/healthcheck ordre propre | ❌ | Aucun script de cycle de vie ; le guide §4.8/4.12 l'exige | `scripts/cluster_up.sh`, `cluster_down.sh`, `restart_after_powercut.sh`, `check_cluster.sh` | P1 |
| 3.8 | Config centralisée (master addr, driver host, connector) | 🟡 | `MONGO_URI` centralisé ✅ ; mais `--master spark://spark-master:7077`, `--packages ...:10.3.0`, driver host dupliqués dans `.sh` et `.ps1` | `.env` racine + variables dans les scripts | P2 |

## 4. Les 30 requêtes

### Transactionnelles

| ID | Statut | Note | Priorité |
|---|---|---|---|
| T1 envoyer message | 🟡 | `t01` insère mais **ne met PAS à jour `last_message_at`** (commentaire ligne 48) — sémantique incomplète vs spec (« envoyer un message » dans une vraie app met à jour la conv) ; à documenter ou corriger | P1 |
| T2 import 10 000 en lot | ✅ | `bulk_write` InsertOne ×10 000, unordered — OK (spec dit « en lot » ; `insert_many` par paquets aussi acceptable) | — |
| T3 profil utilisateur | ✅ | findOne par `_id` ou `pseudo` (index unique) | — |
| T4 50 derniers messages | ✅ | index `{conversation_id, ts:-1}` + `deleted:false` ; pagination OK | — |
| T5 page précédente | 🟡 | Keyset `$lt before_ts` ✅ **mais** le tri `ts` seul peut être ambigu (timestamps identiques) et `ts` n'a pas de tie-break `_id` ; spec suggère curseur complet. Aussi : fallback utilise `.skip(10)` (ironie) | P2 |
| T6 conversations d'un user triées | ✅ | index multikey `{participants.user_id, last_message_at:-1}` | — |
| T7 créer groupe | ✅ | insert avec rôles admin/member | — |
| T8 ajouter/retirer participant | ✅ | `$push`/`$pull` + `$inc participants_count` | — |
| T9 modifier message | ✅ | `$set content, edited, edited_at` | — |
| T10 suppression logique | ✅ | `deleted:true` + `deleted_at`, contenu masqué | — |
| T11 réaction | 🟡 | `$push {user_id, emoji}` — **permet les doublons** (un user peut réagir 2×) ; spec « utilisateur vers emoji » suggère unicité. `$addToSet` ou map serait plus correct | P1 |
| T12 marquer comme lu | ✅ | upsert sur `(conversation_id, user_id)` + index unique | — |
| T13 non lus | 🟡 | **N'exclut pas les messages de l'utilisateur lui-même** (spec : « non lus … dans une conversation » — implicitement les messages des autres) ; utilise `last_read_ts` et non `last_read_msg_id` ; le `run()` sans args fait une boucle de 200 read_status + count → **le temps mesuré inclut la recherche de la paire**, pas la requête pure | P1 |
| T14 éphémères 24 h | 🟡 | TTL index ✅ mais `run()` insère avec `ttl_seconds=3600` par défaut (1 h, pas 24 h) ; le TTL monitor ~60 s à expliquer | P2 |
| T15 signaler | ✅ | insert reports status=pending | — |

### Analytiques natives

| ID | Statut | Note |
|---|---|---|
| A16 msgs/jour 30 j | ✅ | `$match ts≥30j` + `$dateToString` — index `ts` exploitable |
| A17 top 10 actifs | ✅ | group+sort+limit+`$lookup` users |
| A18 par type | ✅ | |
| A19 taille moy PJ par MIME | ✅ | `$match attachment exists` — attention : `attachment: None` en Python → `null` en BSON, `$exists` matche null aussi ? Non : `{"attachment": {"$exists": true}}` inclut les `null` → le `$avg` sur `attachment.size` ignore null, mais `count` dans le `$group` compte les null comme un groupe `_id:null` possible. **Vérifier** : ajouter `"attachment": {"$ne": null}` | P2 |
| A20 groupes >50 | ✅ | `participants_count>50` + index `{type, participants_count}` |
| A21 inactifs 30 j | 🟡 | utilise `last_login` (≠ `last_seen` de la spec) ; index `last_login` ✅ |
| A22 par heure | ✅ | `$hour` — ATTENTION : `$hour` utilise le **timezone du serveur** (UTC en conteneur) ; documenter |
| A23 emoji top | ✅ | `$unwind reactions` + group emoji — fonctionne avec le format tableau ; `$limit(10)` alors que spec dit « le plus utilisé » (top 1) — limite à 1 pour coller à la spec ou justifier | P2 |
| A24 signalements motif/statut | ✅ | |
| A25 convs sans message 7 j | ✅ | `last_message_at < now-7j` + index dédié |

### Synthèse requêtes

- Toutes les 30 sont **implémentées** ; sémantiques globalement correctes.
- **Justifications par requête** : présentes dans le README sous forme de tableau (index + pipeline) — ✅ exigence 1 partiellement (pas de justification *rédigée* du choix embed/référence par requête, mais le README section 2 couvre le schéma).
- **Indexes** : 13 index, chacun rattachable à une requête — ✅ ; `idx_users_created_at` (S30) et `idx_conversations_last_message_at` (A25) OK. Index orphelin possible : aucun evident.
- **`explain()` evidence** : `explain_plan()` n'existe que pour T4/T5/T6 ; `index_test.py` produit les JSON explain — partiel pour les 30.

## 5. Natif vs Spark (exigence 4)

| Exigence | Statut | Preuve |
|---|---|---|
| Comparer ≥3 requêtes | ✅ | `spark/comparaison/cmp_a16/a17/a18.py` + `merge_native_spark.py` → `native_vs_spark.csv` ; vérification d'équivalence des résultats incluse |
| Jobs S26-S30 | ✅ | 5 jobs, écriture `stats_*`, `lag`/`explode+self-join`/`window`/`join`/`cohort` — conformes à la spec. S27 : self-join `a.user_id < b.user_id` ✅ ; S28 : fenêtre 1h/10min `countDistinct conv >20` ✅ ; S29 : join messages↔reports, seuil `sent_count>=20` documenté en code ✅ ; S30 : cohortes mois d'inscription, activité M+1 ✅ |
| Timing Spark | 🟡 | S26 : 3 runs sur `agg().collect()` ✅ ; S27/S29/S30 : **timing uniquement autour de l'écriture** (`time.time()` sur `write.save()`), pas autour de l'action de calcul → mesure non conforme §4.7 ; S28 : OK (collect ×3) | P1 |
| Exécution cluster (pas local) | ✅ | `spark-submit --master spark://spark-master:7077` via docker exec ; `--executor-memory 1g --total-executor-cores 4` conforme guide | — |

## 6. Expériences cohérence/index (exigence 5)

| Exigence | Statut | Preuve |
|---|---|---|
| ≥2 expériences | ✅ | (a) `index_test.py` : T4/T6 avec/sans index (`$natural` hint), explain executionStats, docs examinés ; (b) `consistency_test.py` : w=1/majority/3 + readConcern local/majority | — |
| Mesures réelles | ❓ | CSV attendus dans `benchmarks/results/` — **gitignorés et absents** ; aucune valeur vérifiable dans le repo. Le README cite des chiffres (2.4 ms vs 8.1 ms, failover 2.4 s) non traçables | P1 (régénérer + versionner un export) |
| Comportement avec nœud arrêté | 🟡 | `consistency_test.py` exige 3 membres UP ; **aucun script n'arrête un secondaire pour tester w:1/majority** ni le cas 2-nœuds-down (quorum perdu) | P1 |

## 7. Dashboard (exigence 6)

| Exigence | Statut | Preuve |
|---|---|---|
| Streamlit ≥3 charts | ✅ | ~10 graphiques Plotly (A16, A18, A22, A17, A24, S26, S28, S29, S30, benchmarks) |
| Données réelles | ✅ | lit MongoDB + `stats_*` + CSV results ; `@st.cache_data(ttl=60)` (guide suggère 30 — mineur) |
| UI compacte 1-2 écrans | 🟡 | 5 onglets, tableaux longs non contrains — à redesign (Phase 7) ; pas de `.streamlit/config.toml` | P1 |
| Connexion RS multi-hôtes | ✅ | `MONGO_URI` avec 3 membres + `primaryPreferred` | — |

## 8. Livrables

| Livrable | Statut | Note |
|---|---|---|
| Dépôt Git | ✅ | `main` propre hormis 6 fichiers modifiés non commités + 1 non suivi — **à committer sur la branche de fix** |
| README | ✅ | Très complet (reproduire, catalogue 30 requêtes, dépannage) |
| Rapport ≤15 p., template ENSA | ❌ | **Aucun `.tex` dans le repo** — normal si le rapport vit ailleurs, mais rien à vérifier ici ; `docs/` PDFs absents aussi |
| Démo 15 min | ❌ | Pas de `DEMO_SCRIPT.md` ; checklist §4.12 non formalisée | P1 |

## 9. Problèmes de qualité / sécurité

| Problème | Sévérité | Détail |
|---|---|---|
| Identifiants MongoDB commités | 🔴 | `MONGO_INITDB_ROOT_PASSWORD=admin123` en clair dans les 2 compose ; `.env` contient des IPs (OK) mais pas de secrets — le mot de passe DB est le vrai souci. Lab local → acceptable si documenté, à durcir si possible | P1 |
| `mongo3` probablement injoignable (voir 3.6) | 🔴 | Risque que tout le RS soit dégradé en prod actuelle — **à vérifier en premier** (`rs.status()`) | **P0** |
| Duplication de code | 🟡 | `get_db()`/`sys.path.insert` répété dans chaque requête ; connexion MongoClient recréée par appel (dashboard : 1 client par fonction) | P2 |
| `sys.path.insert` fragile | 🟡 | `os.path.join(dirname, "../..")` non résolu (`abspath` sur un chemin avec `..` fonctionne mais est fragile) ; pattern `python -m` depuis la racine marcherait | P2 |
| T13 mesure inclut la recherche de paire | 🟡 | voir 4.13 | P1 |
| README mélange bash/PowerShell | 🟡 | §5.2 en PowerShell, reste en bash — normal Windows, à clarifier | P2 |
| `check_data.py` non intégré au README | 🟡 | Excellent outil de validation absent de la doc | P2 |
| Numéros du README non vérifiables | 🟡 | 105 420 messages, latences, failover 2.4 s — aucun CSV versionné pour les justifier | P1 |
| `run_spark_job.ps1` utilise `Invoke-Expression` + chemin codé en dur `c:\Users\EMMA\...` | 🟡 | Fragile ; préférer la version `.sh` sous WSL ou un `.ps1` paramétré | P2 |
| `messages.bulk_write` T2 : 10 000 InsertOne en mémoire | 🟡 | Fonctionne mais `insert_many` par lots serait plus fidèle à « en lot » ; spec T2 = « importer 10 000 messages en lot » — bulk_write ordered=False est un bulk légitime | P2 |
| `datetime.utcnow()` dans a25 | 🟡 | Déprécié py3.12+ ; utiliser `datetime.now(timezone.utc)` comme ailleurs | P2 |
| `get_db()` ne ferme jamais le client | 🟡 | Chaque requête ouvre un MongoClient (pool de connexions implicite, OK pour un script ; à noter) | P2 |

## 10. Décisions ouvertes (à trancher avec Emma)

1. **Réseau Docker** : rester en bridge + réseau external partagé (recommandé, justifié par mongo1/mongo2 sur A) vs host network du guide. Le guide impose host, mais 2 mongod sur la même machine + workers distants rendent bridge plus sûr. **Ma reco : bridge + external network, documenté.**
2. **worker2 Spark** : le déplacer sur machine B (cible Emma) — le guide veut 2 machines utilisées ; sinon tout Spark sur A est moins impressionnant mais plus simple. **Ma reco : le déplacer sur B.**
3. **Schéma users** : renommer `created_at`→`registered_at`, `last_login`→`last_seen` pour coller à la spec (coût : régénérer les données + adapter requêtes/index) vs documenter le mapping. **Ma reco : renommer (le prof lit le schéma).**
4. **Réactions** : tableau `{user_id,emoji}` (actuel) vs document map `{user_id: emoji}` (spec « utilisateur vers emoji »). **Ma reco : map + `$set reactions.<uid>` atomique — plus fidèle à T11 « une réaction par utilisateur ».**
5. **read_status** : ajouter `last_read_msg_id` en plus de `last_read_ts` ? **Ma reco : oui, les deux (spec explicite).**

## Synthèse

- **P0 (bloquants)** : ① script `rs.initiate` + réseau inter-machines pour mongo3 (3.1/3.6) ; ② décision réseau/worker2 (3.5/3.3).
- **P0/P1 majeurs** : T13 sémantique, T11 unicité réactions, timings Spark S27/S29/S30, tests nœud arrêté, absence de tout résultat mesuré versionné, rapport/DEMO_SCRIPT absents.
- **✅ Déjà solide** : les 30 requêtes implémentées, index complets, jobs Spark conformes, benchmarks index+consistency, dashboard riche, README exemplaire, `check_data.py`.
