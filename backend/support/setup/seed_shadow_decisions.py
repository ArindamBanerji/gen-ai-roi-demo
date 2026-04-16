"""
Seed 1,500 ShadowDecision nodes into AGE from V-SHADOW-SYNTHETIC-v3.

Source: cross-graph-experiments/experiments/v_shadow_synthetic_v3/
        v_shadow_synthetic_results.json

Usage:
    cd backend
    python support/setup/seed_shadow_decisions.py
"""

import asyncio
import json
import math
import os
import sys
import pathlib

# ── resolve paths ────────────────────────────────────────────────────────────

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent          # support/setup/
BACKEND_DIR = SCRIPT_DIR.parent.parent                        # backend/
REPO_DIR = BACKEND_DIR.parent                                 # gen-ai-roi-demo-v4-v50/
PROJECT_DIR = REPO_DIR.parent                                 # claude_projects/

SOURCE_JSON = (
    PROJECT_DIR
    / "cross-graph-experiments"
    / "experiments"
    / "v_shadow_synthetic_v3"
    / "v_shadow_synthetic_results.json"
)

SOURCE_TAG = "v_shadow_synthetic_v3"
PROGRESS_EVERY = 100


# ── serializer (same as graph_schema.py) ─────────────────────────────────────

def _S(val):
    """Serialize a Python value for inline use in AGE Cypher."""
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            raise ValueError("AGE cannot store NaN/Inf: " + repr(val))
        return str(val)
    if isinstance(val, (list, tuple)):
        return "'" + json.dumps(val).replace("'", "\\'") + "'"
    s = str(val).replace("\\", "\\\\").replace("'", "\\'")
    return "'" + s + "'"


# ── main ─────────────────────────────────────────────────────────────────────

async def main() -> None:
    # 1. Load JSON
    if not SOURCE_JSON.exists():
        print("[ERROR] Source file not found: " + str(SOURCE_JSON))
        sys.exit(1)

    with open(SOURCE_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    decisions = data.get("decisions", [])
    if not decisions:
        print("[ERROR] No 'decisions' array in source file.")
        sys.exit(1)

    print("Loaded " + str(len(decisions)) + " records from " + SOURCE_JSON.name)

    # 2. Connect to AGE
    os.environ.setdefault("GRAPH_BACKEND", "age")
    sys.path.insert(0, str(BACKEND_DIR))
    from ci_platform.graph import get_graph_client

    client = get_graph_client()
    await client.ensure_graph()
    print("Connected to AGE: " + type(client).__name__)

    # 3. Check existing count
    try:
        rows = await client.run_query(
            "MATCH (sd:ShadowDecision {source: " + _S(SOURCE_TAG) +
            "}) RETURN count(sd) AS cnt"
        )
        existing = int(rows[0]["cnt"]) if rows else 0
    except Exception as exc:
        print("[WARN] Count query failed: " + str(exc))
        existing = 0

    print("Current ShadowDecision count: " + str(existing))

    if existing >= len(decisions):
        print("Already have " + str(existing) + " nodes (>= " +
              str(len(decisions)) + "). Nothing to load.")
        return

    if existing > 0:
        print("[WARN] " + str(existing) + " nodes already exist. Deleting first...")
        await client.run_query(
            "MATCH (sd:ShadowDecision {source: " + _S(SOURCE_TAG) +
            "}) DETACH DELETE sd"
        )
        print("  Deleted.")

    # 4. Load records one at a time (AGE has no batch CREATE)
    print("Loading " + str(len(decisions)) + " records...")
    loaded = 0
    errors = []

    for i, record in enumerate(decisions):
        decision_id = "shadow-" + str(i).zfill(4)

        try:
            await client.run_query(
                "CREATE (s:ShadowDecision {"
                "decision_id: " + _S(decision_id) + ", "
                "source: " + _S(SOURCE_TAG) + ", "
                "category: " + _S(record["category"]) + ", "
                "agreed: " + _S(record["agreed"]) + ", "
                "analyst_correct: " + _S(record["analyst_correct"]) + ", "
                "analyst: " + _S(record["analyst"]) + ", "
                "day: " + _S(record["day"]) + ", "
                "ai_action: " + _S(record["ai_action"]) + ", "
                "ai_confidence: " + _S(record["ai_confidence"]) + ", "
                "analyst_action: " + _S(record["analyst_action"]) + ", "
                "ai_correct: " + _S(record["ai_correct"]) + ", "
                "reasoning: " + _S(record.get("reasoning", "")) +
                "})"
            )
            loaded += 1
        except Exception as exc:
            errors.append((i, decision_id, str(exc)))

        if (i + 1) % PROGRESS_EVERY == 0:
            print("  " + str(i + 1) + "/" + str(len(decisions)) + "...")

    # 5. Report errors
    if errors:
        print("\n[WARN] " + str(len(errors)) + " records failed:")
        for idx, did, err in errors[:10]:
            print("  Record " + str(idx) + " (" + did + "): " + err)
        if len(errors) > 10:
            print("  ... and " + str(len(errors) - 10) + " more")

    # 6. Verify final count
    try:
        rows = await client.run_query(
            "MATCH (sd:ShadowDecision {source: " + _S(SOURCE_TAG) +
            "}) RETURN count(sd) AS cnt"
        )
        final_count = int(rows[0]["cnt"]) if rows else 0
    except Exception as exc:
        print("[WARN] Final count query failed: " + str(exc))
        final_count = -1

    print("\nRecords attempted: " + str(len(decisions)))
    print("Records loaded:    " + str(loaded))
    print("Records failed:    " + str(len(errors)))
    print("Final AGE count:   " + str(final_count) + " ShadowDecision nodes")

    if errors:
        print("[ERROR] " + str(len(errors)) + " failures")
        sys.exit(1)
    else:
        print("[OK] Done.")


# ── entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
