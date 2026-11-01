"""
merge_native_spark.py
Fusionne queries_native.csv et les timings Spark (spark_jobs.csv ou spark_cmp_raw.txt)
en benchmarks/results/native_vs_spark.csv.

Colonnes : query_id, native_avg_ms, spark_avg_ms, spark_session_ms, same_result
"""
import sys
import os
import csv
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")

NATIVE_CSV  = os.path.join(RESULTS_DIR, "queries_native.csv")
SPARK_CSV   = os.path.join(RESULTS_DIR, "spark_jobs.csv")
RAW_TXT     = os.path.join(RESULTS_DIR, "spark_cmp_raw.txt")
OUTPUT_CSV  = os.path.join(RESULTS_DIR, "native_vs_spark.csv")

# ID correspondances : query_id natif -> query_id Spark cmp
CMP_PAIRS = {
    "A16": "CMP_A16",
    "A17": "CMP_A17",
    "A18": "CMP_A18",
}


def read_native_csv(path):
    """Retourne {query_id: {"avg_ms": float, "result_summary": str}}."""
    data = {}
    if not os.path.exists(path):
        print(f"[WARN] Fichier absent : {path}")
        return data
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            qid = row.get("query_id", "").strip()
            if qid in CMP_PAIRS:
                try:
                    avg_ms = float(row.get("avg_ms", 0) or 0)
                except ValueError:
                    avg_ms = 0.0
                data[qid] = {
                    "avg_ms": avg_ms,
                    "result_summary": row.get("result_summary", ""),
                }
    return data


def read_spark_raw_txt(path):
    """
    Lit spark_cmp_raw.txt.
    Format attendu (une ligne par job) :
        CMP_A16 SPARK_AVG_MS=1234 SPARK_SESSION_MS=5678
    Retourne {cmp_id: {"spark_avg_ms": float, "spark_session_ms": float}}.
    """
    data = {}
    if not os.path.exists(path):
        return data
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if not parts:
                continue
            cmp_id = parts[0]
            spark_avg = 0.0
            spark_sess = 0.0
            for p in parts[1:]:
                m = re.match(r"SPARK_AVG_MS=(\d+\.?\d*)", p)
                if m:
                    spark_avg = float(m.group(1))
                m2 = re.match(r"SPARK_SESSION_MS=(\d+\.?\d*)", p)
                if m2:
                    spark_sess = float(m2.group(1))
            data[cmp_id] = {"spark_avg_ms": spark_avg, "spark_session_ms": spark_sess}
    return data


def read_spark_jobs_csv(path):
    """
    Lit spark_jobs.csv.
    Retourne {query_id: {"avg_ms": float, "session_ms": float}}.
    """
    data = {}
    if not os.path.exists(path):
        print(f"[WARN] Fichier absent : {path}")
        return data
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            qid = row.get("query_id", "").strip()
            try:
                avg_ms = float(row.get("avg_ms", 0) or 0)
            except ValueError:
                avg_ms = 0.0
            try:
                session_ms = float(row.get("session_ms", 0) or 0)
            except ValueError:
                session_ms = 0.0
            data[qid] = {"avg_ms": avg_ms, "session_ms": session_ms}
    return data


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    native_data = read_native_csv(NATIVE_CSV)
    raw_data = read_spark_raw_txt(RAW_TXT)          # prioritaire si présent
    spark_csv_data = read_spark_jobs_csv(SPARK_CSV)

    rows = []
    for native_id, cmp_id in CMP_PAIRS.items():
        native_avg = native_data.get(native_id, {}).get("avg_ms", None)

        # Résolution des timings Spark : raw_txt > spark_csv
        if cmp_id in raw_data:
            spark_avg  = raw_data[cmp_id]["spark_avg_ms"]
            spark_sess = raw_data[cmp_id]["spark_session_ms"]
        elif cmp_id in spark_csv_data:
            spark_avg  = spark_csv_data[cmp_id]["avg_ms"]
            spark_sess = spark_csv_data[cmp_id]["session_ms"]
        else:
            spark_avg  = None
            spark_sess = None

        # Comparaison des résultats : basée sur spark_jobs.csv (rows) et native result_summary
        # On ne peut comparer les valeurs exactes sans réexécuter ; on indique SPARK_ONLY
        # pour montrer que la comparaison se fait côté scripts cmp_*.py.
        same_result = "SPARK_ONLY"

        rows.append({
            "query_id":       native_id,
            "native_avg_ms":  f"{native_avg:.2f}" if native_avg is not None else "N/A",
            "spark_avg_ms":   f"{spark_avg:.2f}"  if spark_avg  is not None else "N/A",
            "spark_session_ms": f"{spark_sess:.2f}" if spark_sess is not None else "N/A",
            "same_result":    same_result,
        })

    # Écriture CSV
    fieldnames = ["query_id", "native_avg_ms", "spark_avg_ms", "spark_session_ms", "same_result"]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Écrit : {OUTPUT_CSV}")
    print()
    # Affichage console
    header = f"{'query_id':<10} {'native_avg_ms':>14} {'spark_avg_ms':>13} {'spark_session_ms':>16} {'same_result':>12}"
    print(header)
    print("-" * len(header))
    for r in rows:
        print(f"{r['query_id']:<10} {r['native_avg_ms']:>14} {r['spark_avg_ms']:>13} "
              f"{r['spark_session_ms']:>16} {r['same_result']:>12}")


if __name__ == "__main__":
    main()
