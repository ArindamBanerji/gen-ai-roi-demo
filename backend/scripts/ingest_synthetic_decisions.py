"""
Ingest synthetic_pilot_decisions.json as verified Decision nodes in Neo4j.
Tab 5 executive narrative reads from these nodes.

Run from gen-ai-roi-demo-v4-v50/backend/:
    python scripts/ingest_synthetic_decisions.py <path_to_json>
"""
import asyncio, json, sys, os
from pathlib import Path

_here = Path(__file__).resolve().parent.parent   # backend/
sys.path.insert(0, str(_here))

try:
    from dotenv import load_dotenv
    _env = _here.parent / ".env"                 # repo root
    if _env.exists():
        load_dotenv(_env)
        print(f"  Loaded .env from {_env}")
    else:
        print(f"  WARNING: .env not found at {_env}")
except ImportError:
    print("  WARNING: python-dotenv not installed")

from app.db.neo4j import neo4j_client

SOURCE_TAG  = "synthetic_v1"
BATCH_SIZE  = 100

UPSERT_BATCH = """
UNWIND $batch AS row
MERGE (d:Decision {id: row.id})
SET d.category                 = row.category,
    d.action                   = row.action,
    d.correct                  = row.correct,
    d.outcome                  = row.outcome,
    d.verified_at              = row.verified_at,
    d.outcome_lead_time_hours  = row.outcome_lead_time_hours,
    d.analyst                  = row.analyst,
    d.day                      = row.day,
    d.source                   = row.source
"""

COUNT_QUERY = """
MATCH (d:Decision {source: $source})
RETURN count(d) AS total
"""


async def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/ingest_synthetic_decisions.py <path_to_json>")
        sys.exit(1)

    json_path = Path(sys.argv[1])
    if not json_path.exists():
        print(f"ERROR: file not found: {json_path}")
        sys.exit(1)

    print(f"\n[ingest_synthetic_decisions] Loading {json_path}")
    print(f"  NEO4J_URI: {os.getenv('NEO4J_URI', '(not set)')}")

    with open(json_path) as f:
        raw = json.load(f)

    decisions = raw if isinstance(raw, list) else raw.get("decisions", [])

    if not decisions:
        print("ERROR: no decisions found in file")
        sys.exit(1)

    # Peek — confirm field names before writing to graph
    first = decisions[0]
    print(f"\n  Field names : {list(first.keys())}")
    print(f"  Sample      : {first}")

    # Validate required fields are present
    required = {"decision_id", "category", "analyst_action", "analyst_correct",
                "outcome", "verified_at", "outcome_lead_time_hours", "analyst", "day"}
    missing = required - set(first.keys())
    if missing:
        print(f"\nERROR: missing expected fields: {missing}")
        print("  Aborting -- fix field mapping before ingesting.")
        sys.exit(1)

    print(f"\n  Loaded {len(decisions)} decisions -- field names confirmed.")

    await neo4j_client.connect()
    try:
        total = len(decisions)
        ingested = 0
        for start in range(0, total, BATCH_SIZE):
            chunk = decisions[start:start + BATCH_SIZE]
            batch = [
                {
                    "id":                        rec["decision_id"],
                    "category":                  rec["category"],
                    "action":                    rec["analyst_action"],
                    "correct":                   bool(rec["analyst_correct"]),
                    "outcome":                   rec["outcome"],
                    "verified_at":               rec["verified_at"],
                    "outcome_lead_time_hours":   rec["outcome_lead_time_hours"],
                    "analyst":                   rec["analyst"],
                    "day":                       rec["day"],
                    "source":                    SOURCE_TAG,
                }
                for rec in chunk
            ]
            await neo4j_client.run_query(UPSERT_BATCH, {"batch": batch})
            ingested += len(chunk)
            if ingested % 500 == 0 or ingested == total:
                print(f"  Progress: {ingested}/{total}")

        r = (await neo4j_client.run_query(COUNT_QUERY, {"source": SOURCE_TAG}))[0]
        print(f"\nIngested {r['total']} decisions")
    finally:
        await neo4j_client.close()


if __name__ == "__main__":
    asyncio.run(main())
