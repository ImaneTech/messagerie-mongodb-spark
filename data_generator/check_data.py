import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timedelta, timezone
from pymongo import MongoClient, ASCENDING
from config.settings import MONGO_URI, MONGO_DB


def check_data():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[MONGO_DB]

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    one_day_ago = now - timedelta(days=1)
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    checks = []

    # 1. Collection counts
    users_count = db.users.count_documents({})
    convs_count = db.conversations.count_documents({})
    msgs_count = db.messages.count_documents({})
    reports_count = db.reports.count_documents({})

    checks.append(("users == 10000", users_count == 10000, users_count))
    checks.append(("conversations == 8000", convs_count == 8000, convs_count))
    checks.append(("messages >= 80000", msgs_count >= 80000, msgs_count))
    checks.append(("reports >= 1000", reports_count >= 1000, reports_count))

    # 2. read_status count == total participants
    total_participants = sum(
        c["participants_count"]
        for c in db.conversations.find({}, {"participants_count": 1})
    )
    read_status_count = db.read_status.count_documents({})
    checks.append((
        "read_status == participants",
        read_status_count == total_participants,
        f"{read_status_count} vs {total_participants}"
    ))

    # 3. Messages in time windows
    msgs_24h = db.messages.count_documents({"ts": {"$gte": one_day_ago}})
    msgs_7d = db.messages.count_documents({"ts": {"$gte": seven_days_ago}})
    msgs_30d = db.messages.count_documents({"ts": {"$gte": thirty_days_ago}})

    checks.append(("messages 24h >= 300", msgs_24h >= 300, msgs_24h))
    checks.append(("messages 7d (info)", True, msgs_7d))
    checks.append(("messages 30d (info)", True, msgs_30d))

    # 4. Ephemeral messages: must have some and none in the past
    ephemeral_count = db.messages.count_documents({"expire_at": {"$exists": True, "$ne": None}})
    ephemeral_past = db.messages.count_documents({"expire_at": {"$exists": True, "$ne": None, "$lt": now}})
    checks.append(("ephemeral messages > 0", ephemeral_count > 0, ephemeral_count))
    checks.append(("no expired ephemeral (expire_at < now == 0)", ephemeral_past == 0, ephemeral_past))

    # 5. S28: spam — same content, same sender, in >20 distinct conversations within 1 hour
    # Group by (sender_id, content) and check span of ts <= 1 hour and distinct conv_count > 20
    spam_pipeline = [
        {"$match": {"type": "text"}},
        {"$group": {
            "_id": {"sender_id": "$sender_id", "content": "$content"},
            "convs": {"$addToSet": "$conversation_id"},
            "min_ts": {"$min": "$ts"},
            "max_ts": {"$max": "$ts"}
        }},
        {"$project": {
            "sender_id": "$_id.sender_id",
            "content": "$_id.content",
            "conv_count": {"$size": "$convs"},
            "span_ms": {"$subtract": ["$max_ts", "$min_ts"]}
        }},
        # span <= 3 600 000 ms (1 hour) and conv_count > 20
        {"$match": {"conv_count": {"$gt": 20}, "span_ms": {"$lte": 3600000}}},
        {"$group": {
            "_id": "$content",
            "senders": {"$addToSet": "$sender_id"},
            "max_convs": {"$max": "$conv_count"}
        }},
        {"$match": {"$expr": {"$gte": [{"$size": "$senders"}, 3]}}}
    ]
    spam_results = list(db.messages.aggregate(spam_pipeline))
    spam_contents_with_3senders = len(spam_results)
    checks.append(("S28 spam >= 3 senders >20 convs/1h", spam_contents_with_3senders >= 1, spam_contents_with_3senders))

    # 6. S26: private conversations with alternating senders within 5 minutes (>= 100 such convs)
    quick_count = 0
    for conv in db.conversations.find({"type": "private"}, {"_id": 1}):
        conv_id = conv["_id"]
        msgs = list(db.messages.find(
            {"conversation_id": conv_id},
            {"sender_id": 1, "ts": 1}
        ).sort("ts", ASCENDING))
        if len(msgs) >= 4:
            alt_within_5min = 0
            for i in range(len(msgs) - 1):
                if msgs[i]["sender_id"] != msgs[i + 1]["sender_id"]:
                    diff = (msgs[i + 1]["ts"] - msgs[i]["ts"]).total_seconds()
                    if diff <= 300:
                        alt_within_5min += 1
            if alt_within_5min >= 3:
                quick_count += 1
    checks.append(("S26 quick back-forth >= 100", quick_count >= 100, quick_count))

    # 7. S27: pairs of users with >= 3 common contacts (>= 10 such pairs)
    # Use aggregation: explode contacts, self-join on contact, count by pair
    s27_pipeline = [
        {"$project": {"user_id": "$_id", "contact": "$contacts"}},
        {"$unwind": "$contact"},
        {"$group": {
            "_id": "$contact",
            "users": {"$addToSet": "$user_id"}
        }},
        {"$project": {
            "pairs": {
                "$reduce": {
                    "input": "$users",
                    "initialValue": [],
                    "in": {
                        "$concatArrays": [
                            "$$value",
                            {"$map": {
                                "input": {"$filter": {
                                    "input": "$users",
                                    "as": "u",
                                    "cond": {"$gt": ["$$u", "$$this"]}
                                }},
                                "as": "u2",
                                "in": {"a": "$$this", "b": "$$u2"}
                            }}
                        ]
                    }
                }
            }
        }},
        {"$unwind": "$pairs"},
        {"$group": {"_id": "$pairs", "common": {"$sum": 1}}},
        {"$match": {"common": {"$gte": 3}}},
        {"$count": "pair_count"}
    ]
    s27_result = list(db.users.aggregate(s27_pipeline))
    common_pairs = s27_result[0]["pair_count"] if s27_result else 0
    checks.append(("S27 common contacts >= 10 pairs", common_pairs >= 10, common_pairs))

    # 8. A21: users inactive for > 30 days
    inactive_users = db.users.count_documents({"last_login": {"$lt": thirty_days_ago}})
    checks.append(("A21 inactive >= 100", inactive_users >= 100, inactive_users))

    # 9. A25: conversations with last_message_at > 7 days ago
    idle_convs = db.conversations.count_documents({"last_message_at": {"$lt": seven_days_ago}})
    checks.append(("A25 idle convs >= 100", idle_convs >= 100, idle_convs))

    # 10. A20: groups with participants_count > 50
    large_groups = db.conversations.count_documents({"type": "group", "participants_count": {"$gt": 50}})
    checks.append(("A20 groups > 50 >= 5", large_groups >= 5, large_groups))

    # 11. TTL index: exactly 1 on messages.expire_at
    print("\n=== INDEXES ===")
    for coll in ["users", "conversations", "messages", "read_status", "reports"]:
        index_names = [idx["name"] for idx in db[coll].list_indexes()]
        print(f"  {coll}: {index_names}")

    ttl_count = 0
    for idx in db.messages.list_indexes():
        if "expireAfterSeconds" in idx:
            ttl_count += 1
            print(f"  TTL index: {idx['name']}, expireAfterSeconds={idx.get('expireAfterSeconds')}, "
                  f"partialFilter={idx.get('partialFilterExpression')}")
    checks.append(("Exactly 1 TTL index (messages.expire_at)", ttl_count == 1, ttl_count))

    # 12. S30 consistency: messages ts >= sender created_at
    s30_bad_pipeline = [
        {"$lookup": {
            "from": "users",
            "localField": "sender_id",
            "foreignField": "_id",
            "as": "sender"
        }},
        {"$unwind": "$sender"},
        {"$match": {"$expr": {"$lt": ["$ts", "$sender.created_at"]}}},
        {"$count": "bad_count"}
    ]
    bad_result = list(db.messages.aggregate(s30_bad_pipeline))
    bad_ts_count = bad_result[0]["bad_count"] if bad_result else 0
    checks.append(("S30 ts < created_at == 0", bad_ts_count == 0, bad_ts_count))

    # 13. S30: distinct registration months (>= 6 for retention cohorts)
    reg_months_agg = list(db.users.aggregate([
        {"$project": {"month": {"$dateToString": {"format": "%Y-%m", "date": {"$toDate": "$created_at"}}}}},
        {"$group": {"_id": "$month"}},
        {"$count": "month_count"}
    ]))
    reg_months_count = reg_months_agg[0]["month_count"] if reg_months_agg else 0
    checks.append(("S30 registration months >= 6", reg_months_count >= 6, reg_months_count))

    # 14. S30: distinct message months
    msg_months_agg = list(db.messages.aggregate([
        {"$project": {"month": {"$dateToString": {"format": "%Y-%m", "date": {"$toDate": "$ts"}}}}},
        {"$group": {"_id": "$month"}},
        {"$count": "month_count"}
    ]))
    msg_months_count = msg_months_agg[0]["month_count"] if msg_months_agg else 0
    checks.append(("S30 message months >= 6 (info)", msg_months_count >= 6, msg_months_count))

    # ── Print table ──────────────────────────────────────────────────────────
    print("\n=== CHECKS ===")
    header = f"{'STATUS':<8} {'CHECK':<50} {'VALUE'}"
    print(header)
    print("-" * 80)
    for name, passed, value in checks:
        status = "PASS" if passed else "FAIL"
        print(f"{status:<8} {name:<50} {value}")

    all_passed = all(c[1] for c in checks)
    print()
    print(f"Overall: {'ALL PASS' if all_passed else 'SOME FAIL'}")
    return all_passed


if __name__ == "__main__":
    check_data()
