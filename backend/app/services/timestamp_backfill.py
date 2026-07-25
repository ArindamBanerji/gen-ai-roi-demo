"""Idempotent backfill: spread synthetic Decision timestamps across 90 days.

All 4860 zero_day_synthetic Decision nodes were seeded with the same
timestamp_epoch. This one-time migration assigns monotonically increasing
epochs so audit trail timestamps are distinct and CX3 passes.

Safe to call at every startup -- skips immediately once spread > 1 day.
"""
import logging
import time

log = logging.getLogger(__name__)

_90_DAYS_MS = 90 * 24 * 60 * 60 * 1000
_1_DAY_MS = 24 * 60 * 60 * 1000


async def backfill_decision_timestamps() -> dict:
    """Spread synthetic Decision timestamps if all nodes share the same epoch.

    Returns a dict with keys: updated (int), skipped (bool), reason (str).
    """
    from app.db.neo4j import neo4j_client, soc_decision_where  # noqa: PLC0415
    from app.graph_schema import _S         # noqa: PLC0415

    check = await neo4j_client.run_query(
        f"MATCH (d:Decision) WHERE {soc_decision_where()} "
        "AND d.origin = 'zero_day_synthetic' "
        "RETURN max(d.timestamp_epoch) AS max_ts, min(d.timestamp_epoch) AS min_ts, count(d) AS cnt"
    )
    if not check:
        return {"updated": 0, "skipped": True, "reason": "no rows"}

    row = check[0]
    cnt = int(row.get("cnt") or 0)
    if cnt == 0:
        return {"updated": 0, "skipped": True, "reason": "no synthetic decisions"}

    try:
        max_ts = float(row.get("max_ts") or 0)
        min_ts = float(row.get("min_ts") or 0)
        if max_ts - min_ts > _1_DAY_MS:
            return {"updated": 0, "skipped": True, "reason": "already spread"}
    except (TypeError, ValueError):
        pass

    id_rows = await neo4j_client.run_query(
        f"MATCH (d:Decision) WHERE {soc_decision_where()} "
        "AND d.origin = 'zero_day_synthetic' "
        "RETURN d.decision_id AS decision_id ORDER BY d.decision_id ASC"
    )
    if not id_rows:
        return {"updated": 0, "skipped": True, "reason": "no ids returned"}

    total = len(id_rows)
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - _90_DAYS_MS
    step_ms = _90_DAYS_MS // max(total - 1, 1)

    updated = 0
    for i, id_row in enumerate(id_rows):
        did = id_row.get("decision_id")
        if not did:
            continue
        new_ts = start_ms + i * step_ms
        await neo4j_client.run_query(
            f"MATCH (d:Decision) WHERE {soc_decision_where()} "
            f"AND d.decision_id = {_S(str(did))} "
            f"SET d.timestamp_epoch = {new_ts}"
        )
        updated += 1

    log.info("Timestamp backfill: %d nodes spread across 90-day window", updated)
    return {"updated": updated, "skipped": False, "reason": "backfilled"}
