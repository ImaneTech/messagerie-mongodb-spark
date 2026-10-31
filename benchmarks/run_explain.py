import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pymongo import DESCENDING
from config.settings import COLLECTIONS
from queries.utils import get_db

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def explain_command(db, collection_name, query_filter, sort=None, limit=None, hint=None,
                    verbosity="executionStats"):
    """
    Exécute un explain via la commande MongoDB pour obtenir executionStats.
    Retourne le résultat brut.
    """
    cmd = {
        "explain": {
            "find": collection_name,
            "filter": query_filter,
        },
        "verbosity": verbosity,
    }
    if sort:
        cmd["explain"]["sort"] = sort
    if limit:
        cmd["explain"]["limit"] = limit
    if hint:
        cmd["explain"]["hint"] = hint

    return db.command(cmd)


def extract_explain_summary(explain_result):
    """Extrait les champs pertinents d'un résultat explain executionStats."""
    stats = explain_result.get("executionStats", {})
    winning_plan = explain_result.get("queryPlanner", {}).get("winningPlan", {})

    def get_stage(plan):
        if not isinstance(plan, dict):
            return "UNKNOWN"
        stage = plan.get("stage", "")
        if stage:
            return stage
        for key in ["inputStage", "inputStages"]:
            sub = plan.get(key)
            if isinstance(sub, dict):
                return get_stage(sub)
            elif isinstance(sub, list) and sub:
                return get_stage(sub[0])
        return "UNKNOWN"

    return {
        "winningPlan_stage": get_stage(winning_plan),
        "totalDocsExamined": stats.get("totalDocsExamined"),
        "nReturned": stats.get("nReturned"),
        "executionTimeMillis": stats.get("executionTimeMillis"),
    }


def save_explain(filename, summary):
    path = os.path.join(RESULTS_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"  Écrit : {filename} — stage={summary['winningPlan_stage']}, "
          f"docsExamined={summary['totalDocsExamined']}, "
          f"nReturned={summary['nReturned']}, "
          f"timeMs={summary['executionTimeMillis']}")


def main():
    db = get_db()
    print("=== Explain plans T4, T5, T6 ===\n")

    # ── T4 normal ────────────────────────────────────────────────────────────
    print("T4 (avec index):")
    conv = db[COLLECTIONS["conversations"]].find_one()
    cid = conv["_id"] if conv else None
    raw = explain_command(
        db,
        collection_name=COLLECTIONS["messages"],
        query_filter={"conversation_id": cid, "deleted": False},
        sort={"ts": -1},
        limit=50,
    )
    save_explain("explain_T4.json", extract_explain_summary(raw))

    # ── T4 sans index (hint $natural) ────────────────────────────────────────
    print("\nT4 (sans index — $natural):")
    raw = explain_command(
        db,
        collection_name=COLLECTIONS["messages"],
        query_filter={"conversation_id": cid, "deleted": False},
        sort={"ts": -1},
        limit=50,
        hint={"$natural": 1},
    )
    save_explain("explain_T4_noindex.json", extract_explain_summary(raw))

    # ── T5 normal ────────────────────────────────────────────────────────────
    print("\nT5 (avec index):")
    sample = list(db[COLLECTIONS["messages"]].find(
        {"conversation_id": cid, "deleted": False}
    ).sort("ts", DESCENDING).skip(10).limit(1))
    before_ts = sample[0]["ts"] if sample else None

    q5 = {"conversation_id": cid, "deleted": False}
    if before_ts:
        q5["ts"] = {"$lt": before_ts}

    raw = explain_command(
        db,
        collection_name=COLLECTIONS["messages"],
        query_filter=q5,
        sort={"ts": -1},
        limit=50,
    )
    save_explain("explain_T5.json", extract_explain_summary(raw))

    # ── T6 normal ────────────────────────────────────────────────────────────
    print("\nT6 (avec index):")
    u = db[COLLECTIONS["users"]].find_one()
    uid = u["_id"] if u else None

    raw = explain_command(
        db,
        collection_name=COLLECTIONS["conversations"],
        query_filter={"participants.user_id": uid},
        sort={"last_message_at": -1},
        limit=20,
    )
    save_explain("explain_T6.json", extract_explain_summary(raw))

    # ── T6 sans index (hint $natural) ────────────────────────────────────────
    print("\nT6 (sans index — $natural):")
    raw = explain_command(
        db,
        collection_name=COLLECTIONS["conversations"],
        query_filter={"participants.user_id": uid},
        sort={"last_message_at": -1},
        limit=20,
        hint={"$natural": 1},
    )
    save_explain("explain_T6_noindex.json", extract_explain_summary(raw))

    print("\n=== Terminé ===")


if __name__ == "__main__":
    main()
