"""
Step 3: Ingest V-SHADOW-SYNTHETIC-v3 into Neo4j as ShadowDecision nodes.

Usage (from gen-ai-roi-demo-v4-v50/backend/):
    python ../../scripts/ingest_shadow_decisions.py <path_to_json>

Expected result:
    - 1500 ShadowDecision nodes, source="v_shadow_synthetic_v3"
    - 6 AlertCategory nodes
    - 5 AnalystArchetype nodes
    - Relationships: [:IN_CATEGORY] and [:BY_ANALYST]
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# ── path setup ────────────────────────────────────────────────────────────────
# Run this from gen-ai-roi-demo-v4-v50/backend/ so app.db.neo4j resolves.
_backend_root = str(Path(__file__).resolve().parent.parent / "gen-ai-roi-demo-v4-v50" / "backend")
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from app.db.neo4j import neo4j_client

# ── constants ─────────────────────────────────────────────────────────────────
SOURCE_TAG = "v_shadow_synthetic_v3"
BATCH_SIZE = 100


# ── queries ───────────────────────────────────────────────────────────────────

ENSURE_CATEGORY = """
MERGE (:AlertCategory {name: $name})
"""

ENSURE_ARCHETYPE = """
MERGE (:AnalystArchetype {name: $name})
"""

UPSERT_BATCH = """
UNWIND $batch AS row
MERGE (sd:ShadowDecision {
    day: row.day,
    alert_idx: row.alert_idx,
    analyst: row.analyst,
    source: row.source
})
SET
    sd.category        = row.category,
    sd.ai_action       = row.ai_action,
    sd.ai_confidence   = row.ai_confidence,
    sd.analyst_action  = row.analyst_action,
    sd.agreed          = row.agreed,
    sd.analyst_correct = row.analyst_correct,
    sd.ai_correct      = row.ai_correct,
    sd.context         = row.context,
    sd.reasoning       = row.reasoning

WITH sd, row
MATCH (cat:AlertCategory    {name: row.category})
MATCH (arch:AnalystArchetype {name: row.analyst})
MERGE (sd)-[:IN_CATEGORY]->(cat)
MERGE (sd)-[:BY_ANALYST]->(arch)
"""

VERIFY = """
MATCH (sd:ShadowDecision {source: $source})
RETURN count(sd) AS total,
       count(DISTINCT sd.category) AS categories,
       count(DISTINCT sd.analyst)  AS archetypes
"""


# ── helpers ───────────────────────────────────────────────────────────────────

async def ensure_lookup_nodes(decisions: list[dict]) -> None:
    categories = {d["category"] for d in decisions}
    archetypes  = {d["analyst"]  for d in decisions}

    print(f"  Ensuring {len(categories)} AlertCategory nodes...")
    for cat in sorted(categories):
        await neo4j_client.run_query(ENSURE_CATEGORY, {"name": cat})

    print(f"  Ensuring {len(archetypes)} AnalystArchetype nodes...")
    for arch in sorted(archetypes):
        await neo4j_client.run_query(ENSURE_ARCHETYPE, {"name": arch})


async def ingest_batches(decisions: list[dict]) -> None:
    total = len(decisions)
    for start in range(0, total, BATCH_SIZE):
        batch_raw = decisions[start : start + BATCH_SIZE]
        batch = [
            {
                "day":            d["day"],
                "alert_idx":      d.get("alert_idx", 0),
                "category":       d["category"],
                "analyst":        d["analyst"],
                "ai_action":      d["ai_action"],
                "ai_confidence":  float(d["ai_confidence"]),
                "analyst_action": d["analyst_action"],
                "agreed":         bool(d["agreed"]),
                "analyst_correct":bool(d["analyst_correct"]),
                "ai_correct":     bool(d["ai_correct"]),
                "context":        d.get("context", ""),
                "reasoning":      d.get("reasoning", ""),
                "source":         SOURCE_TAG,
            }
            for d in batch_raw
        ]
        await neo4j_client.run_query(UPSERT_BATCH, {"batch": batch})
        end = min(start + BATCH_SIZE, total)
        print(f"  Ingested {end}/{total} decisions...")


async def verify(expected: int) -> bool:
    results = await neo4j_client.run_query(VERIFY, {"source": SOURCE_TAG})
    row = results[0] if results else {}
    total      = row.get("total", 0)
    categories = row.get("categories", 0)
    archetypes = row.get("archetypes", 0)

    print(f"\n  Verification:")
    print(f"    ShadowDecision nodes : {total}  (expected {expected})")
    print(f"    Distinct categories  : {categories}  (expected 6)")
    print(f"    Distinct archetypes  : {archetypes}  (expected 5)")

    ok = (total == expected and categories == 6 and archetypes == 5)
    print(f"  Status: {'✅ PASS' if ok else '❌ FAIL'}")
    return ok


# ── main ──────────────────────────────────────────────────────────────────────

async def main():
    if len(sys.argv) < 2:
        print("Usage: python ingest_shadow_decisions.py <path_to_v3_json>")
        sys.exit(1)

    json_path = Path(sys.argv[1])
    if not json_path.exists():
        print(f"ERROR: file not found: {json_path}")
        sys.exit(1)

    print(f"\n[Step 3] Ingesting V-SHADOW-SYNTHETIC-v3")
    print(f"  File : {json_path}")

    with open(json_path) as f:
        data = json.load(f)

    decisions = data.get("decisions", [])
    print(f"  Loaded {len(decisions)} decisions from JSON")

    await neo4j_client.connect()

    try:
        await ensure_lookup_nodes(decisions)
        await ingest_batches(decisions)
        ok = await verify(len(decisions))
        sys.exit(0 if ok else 1)
    finally:
        await neo4j_client.close()


if __name__ == "__main__":
    asyncio.run(main())
