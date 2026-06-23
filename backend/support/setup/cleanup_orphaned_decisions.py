"""
support/setup/cleanup_orphaned_decisions.py -- Remove pre-WS-4 refer_to_analyst Decision nodes.

648 Decision nodes exist with action='refer_to_analyst' -- simulation artifacts created
before the dual representation fix (BACKLOG-050 / WS-4).  refer_to_analyst is a routing
decision handled by the confidence gate in triage.py, not a ProfileScorer action.
These nodes pollute bootstrap counts and analytics.

Also reports (but does NOT delete) Decision nodes where category IS NULL -- those may need
the category property set from their linked Alert node rather than deleted.

Usage:
    python support/setup/cleanup_orphaned_decisions.py --dry-run   # count only, no writes
    python support/setup/cleanup_orphaned_decisions.py --live       # delete + verify

REQUIRES:
    GRAPH_BACKEND=age
    DATABASE_URL=postgresql://user:pass@host:5432/dbname
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# ── pre-flight ────────────────────────────────────────────────────────────────

GRAPH_BACKEND = os.getenv("GRAPH_BACKEND", "neo4j")
if GRAPH_BACKEND != "age":
    print(
        f"[ERROR] GRAPH_BACKEND={GRAPH_BACKEND!r}. This script only runs against AGE.\n"
        "        Set GRAPH_BACKEND=age and DATABASE_URL=postgresql://... then retry."
    )
    sys.exit(1)

_args = set(sys.argv[1:])
DRY_RUN = "--dry-run" in _args
LIVE    = "--live"    in _args

if not DRY_RUN and not LIVE:
    print(
        "Usage:\n"
        "  python support/setup/cleanup_orphaned_decisions.py --dry-run\n"
        "  python support/setup/cleanup_orphaned_decisions.py --live\n"
    )
    sys.exit(1)

# ── constants ─────────────────────────────────────────────────────────────────

BATCH = 200   # decision_ids per DELETE batch (mirrors bootstrap_learning_loop.py)


# ── helper ────────────────────────────────────────────────────────────────────

def _int(rows: list, key: str) -> int:
    """Extract an integer from an AGEClient query result row (handles agtype wrapping)."""
    if not rows:
        return 0
    v = rows[0].get(key, 0)
    return int(v) if v is not None else 0


# ── main ──────────────────────────────────────────────────────────────────────

async def run() -> None:
    # Add backend/ to sys.path so ci_platform is importable (same as bootstrap script)
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from ci_platform.graph.age_client import AGEClient

    client = AGEClient()
    try:
        await client.ensure_graph()
        print("[STEP 0] AGE graph connected.\n")
    except Exception as exc:
        print(f"[ERROR] Cannot connect to AGE: {exc}")
        sys.exit(1)

    # ── Step 1: Total Decision count (context) ────────────────────────────────
    rows = await client.run_query(
        "MATCH (d:Decision) RETURN count(d) AS cnt"
    )
    total_count = _int(rows, "cnt")
    print(f"[STEP 1] Total Decision nodes in graph:                  {total_count}")

    # ── Step 2: Count refer_to_analyst Decision nodes ─────────────────────────
    rows = await client.run_query(
        "MATCH (d:Decision) WHERE d.action = 'refer_to_analyst' "
        "RETURN count(d) AS cnt"
    )
    rta_count = _int(rows, "cnt")
    print(f"[STEP 2] Decision nodes with action='refer_to_analyst':  {rta_count}")

    # ── Step 3: Count null-category Decision nodes (report only, not deleted) ─
    rows = await client.run_query(
        "MATCH (d:Decision) WHERE d.category IS NULL "
        "RETURN count(d) AS cnt"
    )
    null_cat_count = _int(rows, "cnt")
    print(f"[STEP 3] Decision nodes with category=NULL:              {null_cat_count}")
    if null_cat_count > 0:
        print(
            "         NOTE: null-category nodes are NOT deleted by this script.\n"
            "               They may need d.category set from their linked Alert node."
        )

    print()

    # ── Dry-run exit ──────────────────────────────────────────────────────────
    if DRY_RUN:
        if rta_count == 0:
            print("[DRY-RUN] No refer_to_analyst Decision nodes found -- nothing to delete.")
        else:
            print(
                f"[DRY-RUN] Would delete {rta_count} Decision node(s) with "
                f"action='refer_to_analyst' and all their relationships.\n"
                f"          Re-run with --live to execute."
            )
        return

    # ── Live: delete ──────────────────────────────────────────────────────────
    if rta_count == 0:
        print("[OK] No refer_to_analyst Decision nodes found -- nothing to delete.")
        return

    # Step 4: Fetch all decision_ids to delete
    rows = await client.run_query(
        "MATCH (d:Decision) WHERE d.action = 'refer_to_analyst' "
        "RETURN d.decision_id AS decision_id"
    )
    ids_to_delete = [r["decision_id"] for r in rows if r.get("decision_id")]
    print(f"[STEP 4] Fetched {len(ids_to_delete)} decision_id(s) to delete.")

    if not ids_to_delete:
        # AGE agtype wrapping edge case: count was non-zero but IDs came back empty
        print("[WARN] Count was non-zero but no decision_ids returned -- aborting.")
        return

    # Step 5: Batch-delete Decision nodes and their HAD_CONTEXT children
    # DETACH DELETE removes the node and all its relationships (DECIDED_ON, etc.)
    deleted = 0
    for i in range(0, len(ids_to_delete), BATCH):
        batch     = ids_to_delete[i : i + BATCH]
        id_literal = ", ".join(f"'{did}'" for did in batch)
        await client.run_query(
            f"MATCH (d:Decision) "
            f"WHERE d.decision_id IN [{id_literal}] "
            f"OPTIONAL MATCH (d)-[:HAD_CONTEXT]->(ctx:DecisionContext) "
            f"DETACH DELETE d, ctx"
        )
        deleted += len(batch)
        print(f"  Deleted {deleted}/{len(ids_to_delete)}...")

    print(f"[STEP 5] Deleted {deleted} Decision node(s) and their relationships.\n")

    # Step 6: Verify
    rows = await client.run_query(
        "MATCH (d:Decision) WHERE d.action = 'refer_to_analyst' "
        "RETURN count(d) AS cnt"
    )
    remaining = _int(rows, "cnt")
    print(f"[STEP 6] Verification -- refer_to_analyst Decision nodes remaining: {remaining}")

    rows = await client.run_query(
        "MATCH (d:Decision) RETURN count(d) AS cnt"
    )
    new_total = _int(rows, "cnt")
    print(f"         Total Decision nodes after cleanup:                       {new_total}")
    print(f"         Removed:                                                  {total_count - new_total}")

    if remaining == 0:
        print(
            "\n[OK] Cleanup complete.\n"
            "     Next: python support/setup/bootstrap_learning_loop.py --live\n"
            "     Then: restart uvicorn to refresh bootstrap counts and analytics."
        )
    else:
        print(f"\n[WARN] {remaining} refer_to_analyst Decision node(s) still present -- check for errors above.")


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run())
