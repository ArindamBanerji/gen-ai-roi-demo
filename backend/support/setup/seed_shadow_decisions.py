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
BATCH_SIZE = 50
PROGRESS_EVERY = 100


# ── main ─────────────────────────────────────────────────────────────────────

async def main() -> None:
    # 1. Load JSON
    if not SOURCE_JSON.exists():
        print(f"[ERROR] Source file not found: {SOURCE_JSON}")
        sys.exit(1)

    with open(SOURCE_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    decisions = data.get("decisions", [])
    if not decisions:
        print("[ERROR] No 'decisions' array in source file.")
        sys.exit(1)

    print(f"Loaded {len(decisions)} records from {SOURCE_JSON.name}")

    # 2. Connect to AGE
    from ci_platform.graph import get_graph_client

    client = get_graph_client()
    print(f"Connected to AGE: {type(client).__name__}")

    # 3. Check existing count
    try:
        rows = await client.run_query(
            "MATCH (sd:ShadowDecision {source: $source}) RETURN count(sd) AS cnt",
            {"source": SOURCE_TAG},
        )
        existing = int(rows[0]["cnt"]) if rows else 0
    except Exception as exc:
        print(f"[WARN] Count query failed: {exc}")
        existing = 0

    print(f"Current ShadowDecision count: {existing}")

    if existing >= len(decisions):
        print(f"Already have {existing} nodes (>= {len(decisions)}). Nothing to load.")
        return

    if existing > 0:
        print(f"[WARN] {existing} nodes already exist. Skipping load to avoid duplicates.")
        print("       Delete existing ShadowDecision nodes first if you want to reload.")
        return

    # 4. Load records in batches
    print(f"Loading {len(decisions)} records in batches of {BATCH_SIZE}...")
    loaded = 0
    errors = []

    for i, record in enumerate(decisions):
        decision_id = f"shadow-{i:04d}"

        try:
            await client.run_query(
                """
                CREATE (s:ShadowDecision {
                    decision_id:      $decision_id,
                    source:           $source,
                    category:         $category,
                    agreed:           $agreed,
                    analyst_correct:  $analyst_correct,
                    analyst:          $analyst,
                    day:              $day,
                    ai_action:        $ai_action,
                    ai_confidence:    $ai_confidence,
                    analyst_action:   $analyst_action,
                    ai_correct:       $ai_correct,
                    reasoning:        $reasoning
                })
                """,
                {
                    "decision_id":     decision_id,
                    "source":          SOURCE_TAG,
                    "category":        record["category"],
                    "agreed":          record["agreed"],
                    "analyst_correct": record["analyst_correct"],
                    "analyst":         record["analyst"],
                    "day":             record["day"],
                    "ai_action":       record["ai_action"],
                    "ai_confidence":   record["ai_confidence"],
                    "analyst_action":  record["analyst_action"],
                    "ai_correct":      record["ai_correct"],
                    "reasoning":       record.get("reasoning", ""),
                },
            )
            loaded += 1
        except Exception as exc:
            errors.append((i, decision_id, str(exc)))

        if (i + 1) % PROGRESS_EVERY == 0:
            print(f"Loaded {i + 1}/{len(decisions)}...")

    print(f"Loaded {len(decisions)}/{len(decisions)}...")

    # 5. Report errors
    if errors:
        print(f"\n[WARN] {len(errors)} records failed:")
        for idx, did, err in errors[:10]:
            print(f"  Record {idx} ({did}): {err}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")

    # 6. Verify final count
    try:
        rows = await client.run_query(
            "MATCH (sd:ShadowDecision {source: $source}) RETURN count(sd) AS cnt",
            {"source": SOURCE_TAG},
        )
        final_count = int(rows[0]["cnt"]) if rows else 0
    except Exception as exc:
        print(f"[WARN] Final count query failed: {exc}")
        final_count = -1

    print(f"\nRecords attempted: {len(decisions)}")
    print(f"Records loaded:    {loaded}")
    print(f"Records failed:    {len(errors)}")
    print(f"Final AGE count:   {final_count} ShadowDecision nodes")
    print("Done.")


# ── entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
