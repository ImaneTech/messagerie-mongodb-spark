import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from queries.utils import get_db, timed, save_query_results
from queries.transactional import (
    t01_send_message, t02_bulk_import_messages, t03_user_profile,
    t04_last_50_messages, t05_previous_page, t06_user_conversations,
    t07_create_group, t08_add_remove_participant, t09_edit_message,
    t10_soft_delete_message, t11_add_reaction, t12_mark_conversation_read,
    t13_unread_count, t14_ephemeral_messages_ttl, t15_report_message
)
from queries.analytical import (
    a16_messages_per_day, a17_top_active_users, a18_messages_by_type,
    a19_avg_attachment_size_by_mime, a20_groups_over_50, a21_inactive_users_30d,
    a22_messages_per_hour, a23_top_emoji, a24_reports_by_reason_status,
    a25_conversations_idle_7d
)
from config.settings import COLLECTIONS

results = []

def collection_counts(db):
    """Retourne un dict avec le count de chacune des 5 collections."""
    return {
        "users":         db[COLLECTIONS["users"]].count_documents({}),
        "conversations": db[COLLECTIONS["conversations"]].count_documents({}),
        "messages":      db[COLLECTIONS["messages"]].count_documents({}),
        "read_status":   db[COLLECTIONS["read_status"]].count_documents({}),
        "reports":       db[COLLECTIONS["reports"]].count_documents({}),
    }

def print_counts(label, counts):
    print(f"\n=== {label} ===")
    for col, n in counts.items():
        print(f"  {col}: {n}")

db = get_db()

# ── Counts AVANT ────────────────────────────────────────────────────────────
counts_before = collection_counts(db)
print_counts("Counts AVANT le run", counts_before)

# ── Requêtes transactionnelles ───────────────────────────────────────────────
transactional_queries = [
    ("T01", t01_send_message,          "Envoyer un message"),
    ("T02", t02_bulk_import_messages,  "Import en masse de messages"),
    ("T03", t03_user_profile,          "Consulter profil utilisateur"),
    ("T04", t04_last_50_messages,      "50 derniers messages d'une conversation"),
    ("T05", t05_previous_page,         "Pagination precedente"),
    ("T06", t06_user_conversations,    "Lister conversations utilisateur"),
    ("T07", t07_create_group,          "Creer un groupe"),
    ("T08", t08_add_remove_participant,"Ajouter/retirer participant"),
    ("T09", t09_edit_message,          "Modifier un message"),
    ("T10", t10_soft_delete_message,   "Suppression douce"),
    ("T11", t11_add_reaction,          "Ajouter une reaction"),
    ("T12", t12_mark_conversation_read,"Marquer conversation comme lue"),
    ("T13", t13_unread_count,          "Compter messages non lus"),
    ("T14", t14_ephemeral_messages_ttl,"Messages ephemeres TTL"),
    ("T15", t15_report_message,        "Signaler un message"),
]

analytical_queries = [
    ("A16", a16_messages_per_day,              "Messages par jour"),
    ("A17", a17_top_active_users,              "Top utilisateurs actifs"),
    ("A18", a18_messages_by_type,              "Repartition par type"),
    ("A19", a19_avg_attachment_size_by_mime,   "Taille moyenne pieces jointes"),
    ("A20", a20_groups_over_50,                "Groupes de plus de 50"),
    ("A21", a21_inactive_users_30d,            "Utilisateurs inactifs 30j"),
    ("A22", a22_messages_per_hour,             "Messages par heure"),
    ("A23", a23_top_emoji,                     "Top emojis"),
    ("A24", a24_reports_by_reason_status,      "Signalements par motif/statut"),
    ("A25", a25_conversations_idle_7d,         "Conversations inactives 7j"),
]

# Modules avec cleanup a appeler apres timing
WRITE_MODULES = {
    "T01": t01_send_message,
    "T02": t02_bulk_import_messages,
    "T07": t07_create_group,
    "T08": t08_add_remove_participant,
    "T09": t09_edit_message,
    "T10": t10_soft_delete_message,
    "T11": t11_add_reaction,
    "T12": t12_mark_conversation_read,
    "T14": t14_ephemeral_messages_ttl,
    "T15": t15_report_message,
}

print("\n=== Execution des requetes transactionnelles ===")
for qid, module, desc in transactional_queries:
    try:
        result = module.run()
        timing = timed(module.run, runs=3)
        # Cleanup apres timing pour les modules write
        if qid in WRITE_MODULES and hasattr(module, "cleanup"):
            module.cleanup()
        result_str = str(result)[:100] if result is not None else "None"
        # Fix encoding issue for Windows console
        result_str = result_str.encode('utf-8', errors='replace').decode('utf-8')
        results.append({
            "query_id": qid,
            "family": "transactional",
            "description": desc,
            "avg_ms": timing["avg"],
            "min_ms": timing["min"],
            "max_ms": timing["max"],
            "runs": 3,
            "result_summary": result_str
        })
        print(f"{qid} RUN-OK: {desc} - {timing['avg']:.2f} ms | resultat: {result_str[:80]}")
    except Exception as e:
        # Toujours tenter le cleanup en cas d'erreur partielle
        if qid in WRITE_MODULES and hasattr(module, "cleanup"):
            try:
                module.cleanup()
            except Exception:
                pass
        results.append({
            "query_id": qid,
            "family": "transactional",
            "description": desc,
            "avg_ms": 0,
            "min_ms": 0,
            "max_ms": 0,
            "runs": 0,
            "result_summary": f"ERROR: {str(e)[:90]}"
        })
        print(f"{qid} RUN-FAILED: {desc} — {str(e)}")

print("\n=== Execution des requetes analytiques ===")
for qid, module, desc in analytical_queries:
    try:
        result = module.run()
        timing = timed(module.run, runs=3)
        result_str = str(result)[:100] if result is not None else "None"
        # Fix encoding issue for Windows console - replace problematic chars
        result_str = result_str.encode('ascii', errors='replace').decode('ascii')
        results.append({
            "query_id": qid,
            "family": "analytical",
            "description": desc,
            "avg_ms": timing["avg"],
            "min_ms": timing["min"],
            "max_ms": timing["max"],
            "runs": 3,
            "result_summary": result_str
        })
        print(f"{qid} RUN-OK: {desc} - {timing['avg']:.2f} ms | resultat: {result_str[:80]}")
    except Exception as e:
        results.append({
            "query_id": qid,
            "family": "analytical",
            "description": desc,
            "avg_ms": 0,
            "min_ms": 0,
            "max_ms": 0,
            "runs": 0,
            "result_summary": f"ERROR: {str(e)[:90]}"
        })
        print(f"{qid} RUN-FAILED: {desc} — {str(e)}")

# ── Counts APRÈS ─────────────────────────────────────────────────────────────
counts_after = collection_counts(db)
print_counts("Counts APRÈS le run", counts_after)

# Verification que les counts sont identiques
print("\n=== Verification counts avant/apres ===")
all_equal = True
for col in counts_before:
    before = counts_before[col]
    after  = counts_after[col]
    status = "OK" if before == after else "DIFF"
    if before != after:
        all_equal = False
    print(f"  {col}: {before} -> {after} [{status}]")

if all_equal:
    print("  [OK] Tous les counts sont identiques.")
else:
    print("  [!] ATTENTION : des counts ont change - verifier les modules write.")

# Sauvegarde CSV
save_query_results(results)
print("\nResultats sauvegardes dans benchmarks/results/queries_native.csv")

# Suppression de benchmarks.json si present
bj = os.path.join(os.path.dirname(__file__), "results", "benchmarks.json")
if os.path.exists(bj):
    os.remove(bj)
    print("benchmarks.json supprime (redondant).")
