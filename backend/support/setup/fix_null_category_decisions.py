"""
support/setup/fix_null_category_decisions.py — Repair null-category simulation Decision nodes.

2307 Decision nodes (source_id=None, i.e. simulation artifacts) have d.category IS NULL
and a [:DECIDED_ON] relationship to an Alert node.  This causes campaign recorrelation
to build temporal campaigns with category_sequence=[None, None, ...], which fails Pydantic
validation on GET /api/soc/campaigns (CampaignItem.category_sequence: list[str]).

Two-phase repair:
  Phase A: SET d.category = a.category for the ~1952 nodes whose Alert has a valid category.
  Phase B: DETACH DELETE the remaining ~355 nodes whose Alert also has null category
           (these are double-null artifacts with no recoverable category).

After this script, re-run recorrelation and the test suite.

Usage:
    python support/setup/fix_null_category_decisions.py --dry-run   # count + report only
    python support/setup/fix_null_category_decisions.py --live       # execute fix + verify

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
        "  python support/setup/fix_null_category_decisions.py --dry-run\n"
        "  python support/setup/fix_null_category_decisions.py --live\n"
    )
    sys.exit(1)

# ── constants ─────────────────────────────────────────────────────────────────

BATCH = 200   # node ids per write batch


# ── helper ────────────────────────────────────────────────────────────────────

def _int(rows: list, key: str) -> int:
    if not rows:
        return 0
    v = rows[0].get(key, 0)
    return int(v) if v is not None else 0


# ── main ──────────────────────────────────────────────────────────────────────

async def run() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from ci_platform.graph.age_client import AGEClient

    client = AGEClient()
    try:
        await client.ensure_graph()
        print("[STEP 0] AGE graph connected.\n")
    except Exception as exc:
        print(f"[ERROR] Cannot connect to AGE: {exc}")
        sys.exit(1)

    # ── Step 1: Count null-category Decision nodes with DECIDED_ON ────────────
    rows = await client.run_query(
        "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) "
        "WHERE d.category IS NULL "
        "RETURN count(d) AS cnt"
    )
    total_null = _int(rows, "cnt")
    print(f"[STEP 1] Null-category Decision nodes with DECIDED_ON relationship: {total_null}")

    # ── Step 2: Count Phase-A candidates (Alert has valid category) ───────────
    rows = await client.run_query(
        "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) "
        "WHERE d.category IS NULL AND a.category IS NOT NULL "
        "RETURN count(d) AS cnt"
    )
    phase_a_count = _int(rows, "cnt")
    print(f"[STEP 2] Phase A — fixable (Alert has category):                    {phase_a_count}")

    # ── Step 3: Count Phase-B candidates (Alert also null, delete) ───────────
    rows = await client.run_query(
        "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) "
        "WHERE d.category IS NULL AND a.category IS NULL "
        "RETURN count(d) AS cnt"
    )
    phase_b_count = _int(rows, "cnt")
    print(f"[STEP 3] Phase B — unfixable (Alert also null, will delete):        {phase_b_count}")
    print()

    # ── Dry-run exit ──────────────────────────────────────────────────────────
    if DRY_RUN:
        print("[DRY-RUN] No changes made.")
        print(f"          Phase A would SET d.category = a.category on {phase_a_count} nodes.")
        print(f"          Phase B would DETACH DELETE {phase_b_count} nodes (Alert also null).")
        print("          Re-run with --live to execute.")
        return

    # ── Phase A: Set d.category = a.category for fixable nodes ───────────────
    if phase_a_count == 0:
        print("[PHASE A] No fixable nodes — skipping.")
    else:
        print(f"[PHASE A] Fetching {phase_a_count} decision_id(s) to fix...")
        rows = await client.run_query(
            "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) "
            "WHERE d.category IS NULL AND a.category IS NOT NULL "
            "RETURN d.decision_id AS decision_id, a.category AS category"
        )

        # Build a map of decision_id → category
        id_cat_pairs = [
            (r["decision_id"], r["category"])
            for r in rows
            if r.get("decision_id") and r.get("category")
        ]
        print(f"         Fetched {len(id_cat_pairs)} pairs.")

        fixed = 0
        for i in range(0, len(id_cat_pairs), BATCH):
            batch = id_cat_pairs[i : i + BATCH]
            # Build individual SET statements in a single transaction via UNWIND
            # AGE doesn't support parameterized UNWIND maps, so we build a literal list.
            pairs_literal = ", ".join(
                f"{{decision_id: '{did}', category: '{cat}'}}"
                for did, cat in batch
            )
            await client.run_query(
                f"UNWIND [{pairs_literal}] AS pair "
                f"MATCH (d:Decision) WHERE d.decision_id = pair.decision_id "
                f"SET d.category = pair.category"
            )
            fixed += len(batch)
            print(f"  Fixed {fixed}/{len(id_cat_pairs)}...")

        print(f"[PHASE A] Set category on {fixed} Decision node(s).\n")

    # ── Phase B: Delete unfixable nodes (Alert also null) ────────────────────
    if phase_b_count == 0:
        print("[PHASE B] No unfixable nodes — skipping.")
    else:
        print(f"[PHASE B] Fetching {phase_b_count} decision_id(s) to delete...")
        rows = await client.run_query(
            "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) "
            "WHERE d.category IS NULL AND a.category IS NULL "
            "RETURN d.decision_id AS decision_id"
        )
        ids_to_delete = [r["decision_id"] for r in rows if r.get("decision_id")]
        print(f"         Fetched {len(ids_to_delete)} id(s).")

        deleted = 0
        for i in range(0, len(ids_to_delete), BATCH):
            batch = ids_to_delete[i : i + BATCH]
            id_literal = ", ".join(f"'{did}'" for did in batch)
            await client.run_query(
                f"MATCH (d:Decision) "
                f"WHERE d.decision_id IN [{id_literal}] "
                f"OPTIONAL MATCH (d)-[:HAD_CONTEXT]->(ctx:DecisionContext) "
                f"DETACH DELETE d, ctx"
            )
            deleted += len(batch)
            print(f"  Deleted {deleted}/{len(ids_to_delete)}...")

        print(f"[PHASE B] Deleted {deleted} Decision node(s).\n")

    # ── Verify ────────────────────────────────────────────────────────────────
    rows = await client.run_query(
        "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) "
        "WHERE d.category IS NULL "
        "RETURN count(d) AS cnt"
    )
    remaining = _int(rows, "cnt")
    print(f"[VERIFY] Null-category Decision nodes with DECIDED_ON remaining: {remaining}")

    if remaining == 0:
        print(
            "\n[OK] Fix complete — no null-category simulation Decision nodes remain.\n"
            "     Next steps:\n"
            "       1. POST /api/soc/campaigns/recorrelate  (or via test)\n"
            "       2. GET  /api/soc/campaigns              (verify 200, no None in category_sequence)\n"
            "       3. python -m pytest tests/ -q --timeout=60  (gate: 600 passed, 1 skipped)"
        )
    else:
        print(f"\n[WARN] {remaining} null-category Decision node(s) still present — check for errors above.")


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run())
