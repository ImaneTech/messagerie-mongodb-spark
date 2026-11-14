"""Mesure la reprise des écritures après une bascule MongoDB."""

import argparse
import csv
import os
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pymongo import MongoClient
from pymongo.errors import PyMongoError
from pymongo.write_concern import WriteConcern

from config.settings import IP_A, IP_B, IP_C, MONGO_DB, MONGO_URI

MEMBERS = {
    "mongo1": (IP_A, 27017),
    "mongo2": (IP_B, 27017),
    "mongo3": (IP_C, 27017),
}
RESULTS = Path("benchmarks/results/failover_test.csv")
WRITE_INTERVAL_S = 0.2
ELECTION_TIMEOUT_S = 60
REJOIN_TIMEOUT_S = 120


def utc_now():
    return datetime.now(UTC)


def format_time(value):
    return value.isoformat(timespec="milliseconds") if value else ""


def hello(name):
    host, port = MEMBERS[name]
    client = MongoClient(
        host,
        port,
        directConnection=True,
        serverSelectionTimeoutMS=500,
        connectTimeoutMS=500,
    )
    try:
        return client.admin.command("hello")
    except PyMongoError:
        return None
    finally:
        client.close()


def replica_summary():
    members = []
    for name in MEMBERS:
        info = hello(name)
        if info is None:
            members.append({"name": name, "state": "UNREACHABLE"})
        elif info.get("isWritablePrimary"):
            members.append({"name": name, "state": "PRIMARY"})
        elif info.get("secondary"):
            members.append({"name": name, "state": "SECONDARY"})
        else:
            members.append({"name": name, "state": "OTHER"})
    return members


def find_primary(candidates):
    for name in candidates:
        info = hello(name)
        if info and info.get("isWritablePrimary"):
            return name
    return None


def wait_for(predicate, timeout):
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        result = predicate()
        if result:
            return result
        time.sleep(0.1)
    return None


def write_loop(collection, stop_event, attempts):
    write_number = 0
    while not stop_event.is_set():
        attempted_at = utc_now()
        try:
            collection.insert_one(
                {"write_number": write_number, "attempted_at": attempted_at},
            )
            attempts.append(
                {"at": utc_now(), "ok": True, "error": ""},
            )
            print(
                f"{format_time(attempts[-1]['at'])} "
                f"tentative={write_number} ok"
            )
        except PyMongoError as error:
            attempts.append(
                {"at": utc_now(), "ok": False, "error": type(error).__name__},
            )
            print(
                f"{format_time(attempts[-1]['at'])} "
                f"tentative={write_number} erreur={type(error).__name__}"
            )
        write_number += 1
        stop_event.wait(WRITE_INTERVAL_S)


def stop_container(mode):
    stopped_at = utc_now()
    subprocess.run(
        ["docker", mode, "mongo1"],
        check=True,
        capture_output=True,
        text=True,
    )
    return stopped_at


def run_trial(mode, trial_number):
    # S'assurer que mongo1 est démarré
    subprocess.run(["docker", "start", "mongo1"], capture_output=True, text=True)
    time.sleep(2)
    
    # Vérifier simplement s'il est primaire, sinon tenter un stepDown rapide
    if find_primary(MEMBERS) != "mongo1":
        try:
            for name, (ip, port) in MEMBERS.items():
                if name != "mongo1":
                    c = MongoClient(ip, port, serverSelectionTimeoutMS=1000)
                    if c.admin.command("hello").get("isWritablePrimary"):
                        c.admin.command("replSetStepDown", 10)
                    c.close()
        except Exception:
            pass
        time.sleep(3)

    if not wait_for(lambda: find_primary(MEMBERS) == "mongo1", 10):
        raise RuntimeError("mongo1 doit être le primaire au début de chaque essai.")



    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=1500,
        connectTimeoutMS=1000,
        socketTimeoutMS=1500,
    )
    collection = client[MONGO_DB]["failover_test"].with_options(
        write_concern=WriteConcern(w="majority", wtimeout=1000),
    )
    attempts = []
    stop_writer = threading.Event()
    writer = threading.Thread(
        target=write_loop,
        args=(collection, stop_writer, attempts),
        daemon=True,
    )
    container_stopped = False
    try:
        writer.start()
        if not wait_for(lambda: any(item["ok"] for item in attempts), 15):
            raise RuntimeError("Aucune écriture de préparation n'a réussi.")

        stopped_at = stop_container(mode)
        container_stopped = True
        new_primary = wait_for(
            lambda: find_primary(["mongo2", "mongo3"]),
            ELECTION_TIMEOUT_S,
        )
        first_after = wait_for(
            lambda: next(
                (
                    item["at"]
                    for item in attempts
                    if item["ok"] and item["at"] >= stopped_at
                ),
                None,
            ),
            ELECTION_TIMEOUT_S,
        )
        stop_writer.set()
        writer.join(timeout=5)

        before = [
            item["at"]
            for item in attempts
            if item["ok"] and item["at"] < stopped_at
        ]
        last_before = max(before) if before else None
        if last_before is None or first_after is None or new_primary is None:
            raise RuntimeError(
                "Mesure incomplète : primaire ou écritures manquants."
            )

        subprocess.run(
            ["docker", "start", "mongo1"],
            check=True,
            capture_output=True,
            text=True,
        )
        container_stopped = False
        rejoined = wait_for(lambda: hello("mongo1") is not None, REJOIN_TIMEOUT_S)
        if rejoined is None:
            raise RuntimeError("mongo1 ne rejoint pas le Replica Set.")
        final_primary = wait_for(
            lambda: find_primary(["mongo1", "mongo2", "mongo3"]),
            REJOIN_TIMEOUT_S,
        )
        if final_primary is None:
            raise RuntimeError("Aucun primaire détecté après le redémarrage.")

        interruption = (first_after - last_before).total_seconds()
        row = {
            "trial": trial_number,
            "mode": mode,
            "t_arret": format_time(stopped_at),
            "t_derniere_ok": format_time(last_before),
            "t_premiere_ok": format_time(first_after),
            "new_primary": new_primary,
            "interruption_s": round(interruption, 3),
            "final_primary": final_primary,
        }
        print(f"Essai {trial_number}: {row}")
        print(f"État final : {replica_summary()}")
        return row
    finally:
        stop_writer.set()
        if writer.is_alive():
            writer.join(timeout=5)
        if container_stopped:
            subprocess.run(
                ["docker", "start", "mongo1"],
                check=True,
                capture_output=True,
                text=True,
            )
        collection.drop()
        client.close()


def write_results(rows):
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0])
    with RESULTS.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["stop", "kill"], default="stop")
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs doit être supérieur ou égal à 1")

    print(f"État initial : {replica_summary()}")
    rows = [run_trial(args.mode, trial) for trial in range(1, args.runs + 1)]
    write_results(rows)
    values = [row["interruption_s"] for row in rows]
    values.sort()
    middle = len(values) // 2
    median = values[middle] if len(values) % 2 else (
        values[middle - 1] + values[middle]
    ) / 2
    average = sum(values) / len(values)
    print(f"Moyenne interruption : {average:.3f} s")
    print(f"Médiane interruption : {median:.3f} s")
    print(f"Résultats écrits dans {RESULTS}")
    with RESULTS.open(encoding="utf-8") as file:
        print(file.read(), end="")


if __name__ == "__main__":
    main()
