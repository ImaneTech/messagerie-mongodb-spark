"""Persistence of Spark comparison timings for the dashboard benchmark."""

import csv
from pathlib import Path

FIELDNAMES = ["query_id", "spark_avg_ms", "spark_session_ms"]


def _results_dir():
    project_root = Path(__file__).resolve().parents[2]
    results_dir = project_root / "benchmarks" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir


def record_spark_timing(query_id, spark_avg_ms, spark_session_ms):
    """Write or replace one Spark comparison timing row."""
    path = _results_dir() / "spark_cmp_timings.csv"
    rows = {}
    if path.exists():
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if row.get("query_id"):
                    rows[row["query_id"]] = row

    rows[query_id] = {
        "query_id": query_id,
        "spark_avg_ms": f"{spark_avg_ms:.6f}",
        "spark_session_ms": f"{spark_session_ms:.6f}",
    }
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows[key] for key in sorted(rows))

    return str(path)
