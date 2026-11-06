"""Test de bascule du primaire : arrêt de mongo1, élection, écriture, retour."""
import argparse
import csv
import subprocess
import time
from datetime import datetime
from pathlib import Path

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from config.settings import IP_A, IP_B, MONGO_DB, MONGO_URI

MEMBERS = {"mongo1": (IP_A, 27017), "mongo2": (IP_A, 27018), "mongo3": (IP_B, 27017)}
RESULTS = Path("benchmarks/results/failover_test.csv")


def hello(name):
    host, port = MEMBERS[name]
    client = MongoClient(
        host, port, directConnection=True,
        serverSelectionTimeoutMS=500, connectTimeoutMS=500,
    )
    try:
        return client.admin.command("hello")
    except PyMongoError:
        return None
    finally:
        client.close()


def find_primary(candidates):
    for name in candidates:
        info = hello(name)
        if info and info.get("isWritablePrimary"):
            return name
    return None


def wait_for(predicate, timeout):
    """Retourne la durée en secondes avant que predicate() soit vrai, ou None."""
    start = time.perf_counter()
    while time.perf_counter() - start < timeout:
        if predicate():
            return time.perf_counter() - start
        time.sleep(0.1)
    return None


def run(mode):
    if find_primary(MEMBERS) != "mongo1":
        raise SystemExit("mongo1 doit être le primaire au départ.")

    survivors = ["mongo2", "mongo3"]
    t0 = time.perf_counter()
    subprocess.run(["docker", mode, "mongo1"], check=True, capture_output=True)

    election = wait_for(lambda: find_primary(survivors) is not None, 60)
    new_primary = find_primary(survivors)
    elapsed_election = (time.perf_counter() - t0) if election is not None else None

    client = MongoClient(MONGO_URI, w="majority", serverSelectionTimeoutMS=30000)
    coll = client[MONGO_DB]["failover_test"]
    w0 = time.perf_counter()
    coll.insert_one({"ts": datetime.utcnow(), "mode": mode})
    write_time = time.perf_counter() - w0

    subprocess.run(["docker", "start", "mongo1"], check=True, capture_output=True)
    s0 = time.perf_counter()
    rejoin = wait_for(lambda: hello("mongo1") is not None, 120)
    back = wait_for(lambda: find_primary(["mongo1"]) is not None, 120)
    back_total = (time.perf_counter() - s0) if back is not None else None

    coll.drop()
    client.close()
    return {
        "date": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "new_primary": new_primary,
        "election_s": round(elapsed_election, 2) if elapsed_election else "",
        "write_after_failover_s": round(write_time, 2),
        "mongo1_reachable_s": round(rejoin, 2) if rejoin else "",
        "mongo1_primary_again_s": round(back_total, 2) if back_total else "",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["stop", "kill"], default="kill")
    row = run(parser.parse_args().mode)
    print(row)
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    new_file = not RESULTS.exists()
    with RESULTS.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if new_file:
            writer.writeheader()
        writer.writerow(row)