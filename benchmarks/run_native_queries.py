"""Mesure les requêtes natives MongoDB T01-T15 et A16-A25."""

import argparse
import os
import sys

from pymongo.errors import PyMongoError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.settings import COLLECTIONS
from queries.analytical import (
    a16_messages_per_day,
    a17_top_active_users,
    a18_messages_by_type,
    a19_avg_attachment_size_by_mime,
    a20_groups_over_50,
    a21_inactive_users_30d,
    a22_messages_per_hour,
    a23_top_emoji,
    a24_reports_by_reason_status,
    a25_conversations_idle_7d,
)
from queries.transactional import (
    t01_send_message,
    t02_bulk_import_messages,
    t03_user_profile,
    t04_last_50_messages,
    t05_previous_page,
    t06_user_conversations,
    t07_create_group,
    t08_add_remove_participant,
    t09_edit_message,
    t10_soft_delete_message,
    t11_add_reaction,
    t12_mark_conversation_read,
    t13_unread_count,
    t14_ephemeral_messages_ttl,
    t15_report_message,
)
from queries.utils import get_db, save_query_results, timed

TRANSACTIONAL_QUERIES = [
    ("T01", t01_send_message, "Envoyer un message"),
    ("T02", t02_bulk_import_messages, "Import en masse de messages"),
    ("T03", t03_user_profile, "Consulter profil utilisateur"),
    ("T04", t04_last_50_messages, "50 derniers messages"),
    ("T05", t05_previous_page, "Pagination précédente"),
    ("T06", t06_user_conversations, "Lister conversations utilisateur"),
    ("T07", t07_create_group, "Créer un groupe"),
    ("T08", t08_add_remove_participant, "Ajouter/retirer participant"),
    ("T09", t09_edit_message, "Modifier un message"),
    ("T10", t10_soft_delete_message, "Suppression douce"),
    ("T11", t11_add_reaction, "Ajouter une réaction"),
    ("T12", t12_mark_conversation_read, "Marquer conversation comme lue"),
    ("T13", t13_unread_count, "Compter messages non lus"),
    ("T14", t14_ephemeral_messages_ttl, "Messages éphémères TTL"),
    ("T15", t15_report_message, "Signaler un message"),
]

ANALYTICAL_QUERIES = [
    ("A16", a16_messages_per_day, "Messages par jour"),
    ("A17", a17_top_active_users, "Top utilisateurs actifs"),
    ("A18", a18_messages_by_type, "Répartition par type"),
    ("A19", a19_avg_attachment_size_by_mime, "Taille moyenne pièces jointes"),
    ("A20", a20_groups_over_50, "Groupes de plus de 50"),
    ("A21", a21_inactive_users_30d, "Utilisateurs inactifs 30j"),
    ("A22", a22_messages_per_hour, "Messages par heure"),
    ("A23", a23_top_emoji, "Emoji le plus utilisé"),
    ("A24", a24_reports_by_reason_status, "Signalements par motif/statut"),
    ("A25", a25_conversations_idle_7d, "Conversations inactives 7j"),
]

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


def collection_counts(db):
    return {
        name: db[COLLECTIONS[name]].count_documents({})
        for name in COLLECTIONS
    }


def measure_query(query_id, module, description, results):
    try:
        warmup_result = module.run()
        timing = timed(module.run, runs=3)
        if query_id in WRITE_MODULES and hasattr(module, "cleanup"):
            module.cleanup()
        results.append(
            {
                "query_id": query_id,
                "family": "transactional" if query_id.startswith("T") else "analytical",
                "description": description,
                "avg_ms": timing["avg"],
                "median_ms": timing["median"],
                "min_ms": timing["min"],
                "max_ms": timing["max"],
                "runs": 3,
                "result_summary": str(warmup_result)[:100],
            }
        )
        print(f"{query_id} : {timing['avg']:.2f} ms")
    except (KeyError, PyMongoError, TypeError, ValueError) as exc:
        if query_id in WRITE_MODULES and hasattr(module, "cleanup"):
            module.cleanup()
        results.append(
            {
                "query_id": query_id,
                "family": "transactional" if query_id.startswith("T") else "analytical",
                "description": description,
                "avg_ms": 0,
                "median_ms": 0,
                "min_ms": 0,
                "max_ms": 0,
                "runs": 0,
                "result_summary": f"ERROR: {str(exc)[:90]}",
            }
        )
        print(f"{query_id} : erreur ({type(exc).__name__})")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    db = get_db()
    before = collection_counts(db)
    results = []

    for query in TRANSACTIONAL_QUERIES + ANALYTICAL_QUERIES:
        measure_query(*query, results)

    after = collection_counts(db)
    for name in before:
        print(f"{name}: {before[name]} -> {after[name]}")

    output = os.path.join(os.path.dirname(__file__), "results", "queries_native.csv")
    save_query_results(output, results)
    print(f"Résultats sauvegardés dans {output}")


if __name__ == "__main__":
    main()
