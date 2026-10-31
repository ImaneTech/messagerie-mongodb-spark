# Résultats de vérification des données — Stage 4A

Date d'exécution : 2026-10-31

## Tableau PASS/FAIL

| Statut | Vérification | Valeur mesurée |
|--------|-------------|----------------|
| PASS | users == 10000 | 10000 |
| PASS | conversations == 8000 | 8000 |
| PASS | messages >= 80000 | 84697 |
| PASS | reports >= 1000 | 1200 |
| PASS | read_status == participants | 20166 vs 20166 |
| PASS | messages 24h >= 300 | 5672 |
| PASS | messages 7j (info) | 26869 |
| PASS | messages 30j (info) | 55935 |
| PASS | messages éphémères > 0 | 2453 |
| PASS | aucun éphémère expire_at < now | 0 |
| PASS | S28 spam >= 3 expéditeurs >20 convs/1h | 3 contenus détectés |
| PASS | S26 back-and-forth rapide >= 100 convs | 584 conversations |
| PASS | S27 contacts communs >= 10 paires | 28895 paires |
| PASS | A21 utilisateurs inactifs >= 100 | 1545 |
| PASS | A25 conversations inactives >= 100 | 2650 |
| PASS | A20 groupes > 50 participants >= 5 | 7 groupes |
| PASS | Exactement 1 index TTL (messages.expire_at) | 1 |
| PASS | S30 ts < created_at == 0 | 0 |
| PASS | S30 mois d'inscription >= 6 | 6 mois |
| PASS | S30 mois de messages >= 6 (info) | 6 mois |

## Section S30 — Cohérence temporelle

| Vérification | Valeur |
|--------------|--------|
| Messages dont ts < created_at de l'expéditeur | **0** |
| Mois d'inscription distincts | **6** (mai–octobre 2026) |
| Mois de messages distincts | **6** (mai–octobre 2026) |

## Statut global

**ALL PASS** — 20/20 vérifications réussies.

## Corrections apportées

### check_data.py
- Correction du check S28 : ajout de la fenêtre 1 heure (span_ms <= 3 600 000) via agrégation MongoDB
- Correction du check S26 : vérification de toutes les conversations privées (pas seulement 200), critère >= 3 alternances dans 5 min
- Correction du check S27 : remplacement du loop Python par une agrégation MongoDB (explode contacts, self-join)
- Correction du check `ephemeral` : filtre `$ne: None` ajouté pour exclure les documents sans expire_at
- Ajout des vérifications S30 : ts < created_at, mois d'inscription, mois de messages

### generate_data.py
- Contrainte S30 appliquée : chaque message a désormais ts >= created_at de l'expéditeur
- S26 : 200 conversations privées cibles avec 12 messages alternés à 5 s d'intervalle
- S28 : 3 contenus spam distincts, 10 expéditeurs chacun, 25 conversations dans la fenêtre 1 h
- S27 : clique élargie à 200 utilisateurs (contacts mutuels garantis)
- Plage temporelle étendue : conversations créées entre -10 et -180 jours (6 mois couverts)
- Total messages : ~84 700 (> 80 000)
