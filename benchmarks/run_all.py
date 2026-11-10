"""Script principal pour exécuter l'ensemble des benchmarks (natif, index, cohérence, spark)."""

import argparse
import csv
import os
import subprocess
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

SPARK_JOBS = [
    "s26_avg_response_time",
    "s27_common_contacts",
    "s28_spam_detection",
    "s29_report_rate_by_sender",
    "s30_retention_cohorts",
]

SPARK_JOB_DESCRIPTIONS = {
    "s26_avg_response_time": "Temps de réponse moyen",
    "s27_common_contacts": "Contacts communs top 20",
    "s28_spam_detection": "Détection spam",
    "s29_report_rate_by_sender": "Taux de signalement top 20",
    "s30_retention_cohorts": "Rétention par cohorte",
}

NATIVE_FAMILIES = {
    "T01": "transactional",
    "T02": "transactional",
    "T03": "transactional",
    "T04": "transactional",
    "T05": "transactional",
    "T06": "transactional",
    "T07": "transactional",
    "T08": "transactional",
    "T09": "transactional",
    "T10": "transactional",
    "T11": "transactional",
    "T12": "transactional",
    "T13": "transactional",
    "T14": "transactional",
    "T15": "transactional",
    "A16": "analytical",
    "A17": "analytical",
    "A18": "analytical",
    "A19": "analytical",
    "A20": "analytical",
    "A21": "analytical",
    "A22": "analytical",
    "A23": "analytical",
    "A24": "analytical",
    "A25": "analytical",
}


def run_native_queries():
    print("=== (a) Requêtes natives ===")
    result = subprocess.run(
        [sys.executable, os.path.join(os.path.dirname(__file__), "run_native_queries.py")],
        capture_output=False,
        text=True,
    )
    return result.returncode == 0


def run_index_test():
    print("\n=== (b) Test des index ===")
    result = subprocess.run(
        [sys.executable, os.path.join(os.path.dirname(__file__), "index_test.py")],
        capture_output=False,
        text=True,
    )
    return result.returncode == 0


def run_consistency_test():
    print("\n=== (c) Test de cohérence ===")
    result = subprocess.run(
        [sys.executable, os.path.join(os.path.dirname(__file__), "consistency_test.py")],
        capture_output=False,
        text=True,
    )
    return result.returncode == 0


def run_spark_jobs():
    print("\n=== Spark jobs ===")
    script = os.path.abspath(os.path.join(os.path.dirname(__file__), "run_spark_job.sh"))
    for job in SPARK_JOBS:
        print(f"  Lancement {job}...")
        result = subprocess.run(
            ["bash", script, job], capture_output=False, text=True
        )
        if result.returncode != 0:
            print(f"  ATTENTION: {job} a échoué (code {result.returncode})")


def merge_all_queries():
    native_path = os.path.join(RESULTS_DIR, "queries_native.csv")
    spark_path = os.path.join(RESULTS_DIR, "spark_jobs.csv")
    out_path = os.path.join(RESULTS_DIR, "all_queries.csv")

    rows = []

    if os.path.exists(native_path):
        with open(native_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(
                    {
                        "query_id": row["query_id"],
                        "family": row.get(
                            "family", NATIVE_FAMILIES.get(row["query_id"], "unknown")
                        ),
                        "description": row["description"],
                        "engine": "mongodb",
                        "avg_ms": row["avg_ms"],
                        "min_ms": row["min_ms"],
                        "max_ms": row["max_ms"],
                        "runs": row["runs"],
                    }
                )

    if os.path.exists(spark_path):
        with open(spark_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                job_id = row["job_id"]
                rows.append(
                    {
                        "query_id": job_id.upper() if job_id else row.get("query_id", ""),
                        "family": "spark",
                        "description": row.get(
                            "description", SPARK_JOB_DESCRIPTIONS.get(job_id, job_id)
                        ),
                        "engine": "spark",
                        "avg_ms": row.get("avg_ms", 0),
                        "min_ms": row.get("min_ms", 0),
                        "max_ms": row.get("max_ms", 0),
                        "runs": row.get("runs", 3),
                    }
                )

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "query_id",
                "family",
                "description",
                "engine",
                "avg_ms",
                "min_ms",
                "max_ms",
                "runs",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nall_queries.csv : {len(rows)} lignes écrites dans {out_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-spark", action="store_true", help="Lance aussi les jobs Spark")
    args = parser.parse_args()

    run_native_queries()
    run_index_test()
    run_consistency_test()

    if args.with_spark:
        run_spark_jobs()

    merge_all_queries()
    print("\nrun_all.py terminé.")


if __name__ == "__main__":
    main()
