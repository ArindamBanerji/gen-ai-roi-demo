"""
Seed 50 verified Decision nodes + 3 Campaign nodes into Neo4j.

Simulates 7 days of live analyst feedback for the Executive Narrative (Tab 5).
Idempotent — MERGE on id so re-running is safe.

Usage (from backend/):
    python scripts/seed_verified_decisions.py
"""

import asyncio
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Path / .env setup — mirrors ingest_shadow_decisions.py pattern
# ---------------------------------------------------------------------------
_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

try:
    from dotenv import load_dotenv
    _env = _BACKEND_DIR.parent / ".env"
    if _env.exists():
        load_dotenv(_env)
        print(f"  Loaded .env from {_env}")
    else:
        print(f"  WARNING: .env not found at {_env}")
except ImportError:
    print("  WARNING: python-dotenv not installed")

from app.db.neo4j import neo4j_client  # noqa: E402 (must follow sys.path insert)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CATEGORIES = [
    "credential_access",
    "threat_intel_match",
    "lateral_movement",
    "data_exfiltration",
    "insider_threat",
    "cloud_infrastructure",
]

ACTIONS = ["escalate", "investigate", "suppress", "monitor"]

N_DECISIONS  = 50
N_CORRECT    = 40   # first 40 correct, last 10 incorrect
RANDOM_SEED  = 42

# ---------------------------------------------------------------------------
# Cypher — decisions (MERGE = idempotent)
# ---------------------------------------------------------------------------

UPSERT_DECISION = """
UNWIND $batch AS d
MERGE (n:Decision {id: d.id})
SET n.category    = d.category,
    n.action      = d.action,
    n.outcome     = d.outcome,
    n.correct     = d.correct,
    n.confidence  = d.confidence,
    n.verified_at = d.verified_at,
    n.timestamp   = d.timestamp,
    n.source      = d.source,
    n.shadow_mode = false,
    n.factor_vector = []
"""

# ---------------------------------------------------------------------------
# Cypher — campaigns (only seed if none exist)
# ---------------------------------------------------------------------------

CHECK_CAMPAIGNS = "MATCH (c:Campaign) RETURN count(c) AS cnt"

UPSERT_CAMPAIGN = """
UNWIND $batch AS c
MERGE (n:Campaign {id: c.id})
SET n.alert_count   = c.alert_count,
    n.confidence    = c.confidence,
    n.first_seen    = c.first_seen,
    n.last_seen     = c.last_seen,
    n.severity      = c.severity,
    n.source        = c.source,
    n.nl_summary    = c.nl_summary,
    n.trigger_rule  = c.trigger_rule,
    n.category_sequence  = c.category_sequence,
    n.shared_entities    = c.shared_entities,
    n.technique_sequence = c.technique_sequence,
    n.correlation_window_hours = c.correlation_window_hours,
    n.updated_at    = c.updated_at
"""

# ---------------------------------------------------------------------------
# Build payloads
# ---------------------------------------------------------------------------

def _iso(dt: datetime) -> str:
    return dt.isoformat()


def build_decisions() -> list[dict]:
    rng  = random.Random(RANDOM_SEED)
    now  = datetime.now(timezone.utc)
    rows = []

    for i in range(1, N_DECISIONS + 1):
        correct    = i <= N_CORRECT
        outcome    = "correct" if correct else "incorrect"
        confidence = round(rng.uniform(0.72, 0.95), 4)
        # spread evenly across the last 7 days
        days_ago   = i // 7            # 0..7
        hours_ago  = (i % 7) * 3      # spread within day
        ts         = now - timedelta(days=days_ago, hours=hours_ago)

        rows.append({
            "id":         f"VERIFIED-{i:04d}",
            "category":   CATEGORIES[(i - 1) % len(CATEGORIES)],
            "action":     ACTIONS[(i - 1) % len(ACTIONS)],
            "outcome":    outcome,
            "correct":    correct,
            "confidence": confidence,
            "verified_at": _iso(ts),
            "timestamp":   _iso(ts),
            "source":      "seed_verified",
        })

    return rows


def build_campaigns() -> list[dict]:
    now = datetime.now(timezone.utc)
    specs = [
        {
            "id":          "CAMP-SEED-001",
            "alert_count": 3,
            "confidence":  0.72,
            "first_seen":  _iso(now - timedelta(days=6)),
            "last_seen":   _iso(now - timedelta(days=5)),
            "severity":    "medium",
            "nl_summary":  "Credential access cluster — 3 alerts over 24h",
            "category_sequence":   ["credential_access", "lateral_movement", "data_exfiltration"],
            "technique_sequence":  ["T1078", "T1021", "T1048"],
            "shared_entities":     ["user:alice", "asset:srv-db-01"],
        },
        {
            "id":          "CAMP-SEED-002",
            "alert_count": 5,
            "confidence":  0.85,
            "first_seen":  _iso(now - timedelta(days=4)),
            "last_seen":   _iso(now - timedelta(days=2)),
            "severity":    "high",
            "nl_summary":  "Threat intel + lateral movement — 5 alerts, 48h window",
            "category_sequence":   ["threat_intel_match", "lateral_movement",
                                    "credential_access", "lateral_movement", "data_exfiltration"],
            "technique_sequence":  ["T1588", "T1021", "T1078", "T1021", "T1048"],
            "shared_entities":     ["asset:workstation-07", "user:bob", "ip:10.0.1.45"],
        },
        {
            "id":          "CAMP-SEED-003",
            "alert_count": 4,
            "confidence":  0.68,
            "first_seen":  _iso(now - timedelta(days=2)),
            "last_seen":   _iso(now - timedelta(hours=6)),
            "severity":    "medium",
            "nl_summary":  "Insider threat pattern — 4 alerts, cloud + data exfil",
            "category_sequence":   ["insider_threat", "cloud_infrastructure",
                                    "insider_threat", "data_exfiltration"],
            "technique_sequence":  ["T1048", "T1578", "T1048", "T1048"],
            "shared_entities":     ["user:charlie", "asset:s3-bucket-prod"],
        },
    ]

    for s in specs:
        s.update({
            "source":      "seed_verified",
            "trigger_rule": "manual_seed",
            "correlation_window_hours": 48,
            "updated_at":  _iso(now),
        })

    return specs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    print("\n[seed_verified_decisions] Connecting to Neo4j …")
    await neo4j_client.connect()

    try:
        # ── 1. Verified decisions ────────────────────────────────────────────
        decisions = build_decisions()
        await neo4j_client.run_query(UPSERT_DECISION, {"batch": decisions})
        n_decisions = len(decisions)
        print(f"  Decisions  : {n_decisions} upserted "
              f"({N_CORRECT} correct, {n_decisions - N_CORRECT} incorrect)")

        # ── 2. Campaigns — skip if any already exist ─────────────────────────
        rows = await neo4j_client.run_query(CHECK_CAMPAIGNS, {})
        existing = int((rows[0].get("cnt") or 0) if rows else 0)

        if existing > 0:
            print(f"  Campaigns  : {existing} already exist — skipping seed")
            n_campaigns = 0
        else:
            campaigns = build_campaigns()
            await neo4j_client.run_query(UPSERT_CAMPAIGN, {"batch": campaigns})
            n_campaigns = len(campaigns)
            print(f"  Campaigns  : {n_campaigns} seeded "
                  f"(CAMP-SEED-001/002/003)")

        print(f"\nSeeded {n_decisions} verified decisions, {n_campaigns} campaigns")

    finally:
        await neo4j_client.close()


if __name__ == "__main__":
    asyncio.run(main())
