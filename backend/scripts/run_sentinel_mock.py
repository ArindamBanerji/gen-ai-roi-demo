"""
run_sentinel_mock.py -- CLI runner for SentinelMockConnector.

Loads synthetic_pilot_alerts.json, normalizes each alert, and MERGEs it into
Neo4j as an Alert node.  There is no /api/soc/import HTTP endpoint; the runner
writes directly to the graph (same pattern as seed scripts).

Run from gen-ai-roi-demo-v4-v50/backend/:
    python scripts/run_sentinel_mock.py <path_to_alerts_json>
    python scripts/run_sentinel_mock.py <path> --speed-ms 100
    python scripts/run_sentinel_mock.py <path> --day-filter 0 30
    python scripts/run_sentinel_mock.py <path> --dry-run
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BACKEND))

try:
    from dotenv import load_dotenv
    _env = _BACKEND.parent / ".env"
    if _env.exists():
        load_dotenv(_env)
        print(f"[env] Loaded .env from {_env}")
    else:
        print(f"[env] WARNING: .env not found at {_env}")
except ImportError:
    print("[env] WARNING: python-dotenv not installed")

from app.connectors.sentinel_mock import SentinelMockConnector  # noqa: E402
from app.db.graph_client import graph_client                           # noqa: E402

# ---------------------------------------------------------------------------
# Cypher — MERGE alert node; link to User/Asset if they already exist.
# Relationships are optional so the runner works even on a sparse graph.
# ---------------------------------------------------------------------------
MERGE_ALERT = """
UNWIND $batch AS a
MERGE (alert:Alert {id: a.id})
SET alert.alert_type       = a.alert_type,
    alert.severity         = a.severity,
    alert.category         = a.category,
    alert.source_location  = a.source_location,
    alert.asset_id         = a.asset_id,
    alert.user_id          = a.user_id,
    alert.timestamp_epoch  = a.timestamp_epoch,
    alert.day              = a.day,
    alert.shift            = a.shift,
    alert.status           = a.status,
    alert.source           = a.source
WITH alert, a
OPTIONAL MATCH (user:User {id: a.user_id})
FOREACH (_ IN CASE WHEN user IS NOT NULL THEN [1] ELSE [] END |
  MERGE (alert)-[:INVOLVES]->(user)
)
WITH alert, a
OPTIONAL MATCH (asset:Asset {id: a.asset_id})
FOREACH (_ IN CASE WHEN asset IS NOT NULL THEN [1] ELSE [] END |
  MERGE (alert)-[:DETECTED_ON]->(asset)
)
"""

BATCH_SIZE = 100


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Stream Sentinel mock alerts into Neo4j"
    )
    p.add_argument("alerts_json", help="Path to synthetic_pilot_alerts.json")
    p.add_argument(
        "--speed-ms", type=int, default=0,
        help="Delay between alerts in milliseconds (0 = as fast as possible)"
    )
    p.add_argument(
        "--day-filter", type=int, nargs=2, metavar=("MIN_DAY", "MAX_DAY"),
        default=None,
        help="Only stream alerts with day in [MIN_DAY, MAX_DAY] inclusive"
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Print normalized alerts; do not write to Neo4j"
    )
    return p.parse_args()


async def main() -> None:
    args = parse_args()

    connector = SentinelMockConnector()
    total_loaded = connector.load(args.alerts_json)
    day_filter = tuple(args.day_filter) if args.day_filter else None

    print(f"\n[sentinel-mock] Loaded {total_loaded} alerts from {args.alerts_json}")
    if day_filter:
        print(f"[sentinel-mock] Day filter: {day_filter[0]}-{day_filter[1]}")
    if args.dry_run:
        print("[sentinel-mock] Mode: DRY-RUN (no Neo4j writes)")
    print()

    alerts = list(connector.stream(day_filter=day_filter))
    print(f"[sentinel-mock] Streaming {len(alerts)} alerts after filter")

    if args.dry_run:
        for i, alert in enumerate(alerts):
            print(f"  [{i+1:>4}] {alert}")
            if args.speed_ms:
                time.sleep(args.speed_ms / 1000)
        print(f"\n[sentinel-mock] Dry-run complete -- {len(alerts)} alerts printed")
        return

    # Live mode — write to Neo4j in batches
    await graph_client.connect()
    try:
        ingested = 0
        for start in range(0, len(alerts), BATCH_SIZE):
            batch = alerts[start:start + BATCH_SIZE]
            await graph_client.run_query(MERGE_ALERT, {"batch": batch})
            ingested += len(batch)
            print(f"[sentinel-mock] Ingested {ingested}/{len(alerts)}")
            if args.speed_ms:
                time.sleep(args.speed_ms / 1000)

        print(f"\n[sentinel-mock] Done -- {ingested} alerts merged into Neo4j")
    finally:
        await graph_client.close()


if __name__ == "__main__":
    asyncio.run(main())
