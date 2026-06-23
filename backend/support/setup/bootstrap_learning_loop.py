"""
support/setup/bootstrap_learning_loop.py -- Set outcome/correct on Decision nodes.

The 9,796 Decision nodes migrated from Aura lack outcome and correct fields.
This script reads the synthetic pilot decision data to determine the correct
ratio per category/action pair, then bulk-updates Decision nodes in AGE.

Usage:
    python support/setup/bootstrap_learning_loop.py --dry-run   # print plan
    python support/setup/bootstrap_learning_loop.py --live       # update AGE

REQUIRES:
    GRAPH_BACKEND=age
    DATABASE_URL=postgresql://user:pass@host:5432/dbname
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from collections import Counter, defaultdict
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
LIVE = "--live" in _args

if not DRY_RUN and not LIVE:
    print(
        "Usage:\n"
        "  python support/setup/bootstrap_learning_loop.py --dry-run\n"
        "  python support/setup/bootstrap_learning_loop.py --live\n"
    )
    sys.exit(1)

# ── load synthetic pilot decisions ────────────────────────────────────────────

_SYNTHETIC_PATH = (
    Path(__file__).resolve().parents[4]
    / "cross-graph-experiments"
    / "experiments"
    / "v_synthetic_pilot_analysts"
    / "synthetic_pilot_decisions.json"
)

if not _SYNTHETIC_PATH.exists():
    print(f"[ERROR] Synthetic pilot data not found at:\n  {_SYNTHETIC_PATH}")
    sys.exit(1)

with open(_SYNTHETIC_PATH, "r", encoding="utf-8") as fh:
    _raw = json.load(fh)

DECISIONS = _raw["decisions"]
print(f"[INFO] Loaded {len(DECISIONS)} synthetic pilot decisions from {_SYNTHETIC_PATH.name}")

# ── compute per-category/action correct rates ─────────────────────────────────

_pair_total: dict[tuple[str, str], int] = Counter()
_pair_correct: dict[tuple[str, str], int] = Counter()

for d in DECISIONS:
    cat = d["category"]
    act = d["correct_action"]
    _pair_total[(cat, act)] += 1
    if d["analyst_correct"]:
        _pair_correct[(cat, act)] += 1

# Global correct rate as fallback
_global_correct = sum(1 for d in DECISIONS if d["analyst_correct"])
_global_rate = _global_correct / len(DECISIONS) if DECISIONS else 0.85

print(f"[INFO] Global correct rate: {_global_rate:.1%} ({_global_correct}/{len(DECISIONS)})")
print(f"[INFO] Category/action pairs: {len(_pair_total)}")
for pair, total in sorted(_pair_total.items(), key=lambda x: -x[1]):
    correct = _pair_correct[pair]
    print(f"  {pair[0]}/{pair[1]}: {correct}/{total} ({correct/total:.0%})")


# ── dry-run plan ──────────────────────────────────────────────────────────────

def print_plan():
    print("\n[DRY-RUN] Plan:")
    print(f"  1. Query Decision nodes grouped by (category, action)")
    print(f"  2. For each group, mark ~{_global_rate:.0%} as correct based on synthetic data")
    print(f"  3. SET d.outcome = 'correct', d.correct = true on correct nodes")
    print(f"  4. SET d.outcome = 'incorrect', d.correct = false on remaining nodes")
    print(f"  5. Verify via /api/soc/analytics and /api/soc/executive-narrative")
    print("\n  No changes made. Run with --live to execute.")


# ── live execution ────────────────────────────────────────────────────────────

async def run_live():
    # Import AGE client
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from ci_platform.graph.age_client import AGEClient

    client = AGEClient()
    try:
        await client.ensure_graph()
        print("[STEP 0] AGE graph connected.\n")
    except Exception as e:
        print(f"[ERROR] Cannot connect to AGE: {e}")
        sys.exit(1)

    # Step 1 — Count Decision nodes without outcome
    rows = await client.run_query(
        "MATCH (d:Decision)-[:DECIDED_ON]->() WHERE d.outcome IS NULL RETURN count(d) AS cnt"
    )
    null_count = int(rows[0]["cnt"]) if rows else 0
    print(f"[STEP 1] Decision nodes with outcome=NULL: {null_count}")

    if null_count == 0:
        print("[INFO] All Decision nodes already have outcomes. Nothing to do.")
        return

    # Step 2 — Get all Decision nodes grouped by category+action, with IDs
    # AGE doesn't support collect(), so we fetch individual nodes
    rows = await client.run_query(
        "MATCH (d:Decision)-[:DECIDED_ON]->() WHERE d.outcome IS NULL "
        "RETURN d.decision_id AS decision_id, "
        "       d.category AS category, "
        "       d.action AS action"
    )
    print(f"[STEP 2] Fetched {len(rows)} Decision nodes to update.")

    # Step 3 — Determine correct/incorrect for each node
    # Group by (category, action) and apply the synthetic correct rate
    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for r in rows:
        cat = r.get("category") or "unknown"
        act = r.get("action") or "unknown"
        did = r.get("decision_id") or ""
        groups[(cat, act)].append(did)

    correct_ids: set[str] = set()
    incorrect_ids: set[str] = set()

    import hashlib

    for (cat, act), ids in groups.items():
        # Look up correct rate from synthetic data
        rate = _global_rate  # fallback
        if (cat, act) in _pair_total:
            rate = _pair_correct[(cat, act)] / _pair_total[(cat, act)]
        elif any(k[0] == cat for k in _pair_total):
            # Category match but different action — use category-level rate
            cat_total = sum(v for k, v in _pair_total.items() if k[0] == cat)
            cat_correct = sum(v for k, v in _pair_correct.items() if k[0] == cat)
            rate = cat_correct / cat_total if cat_total > 0 else _global_rate

        # Deterministic assignment: hash each decision_id, mark top N% as correct
        sorted_ids = sorted(ids, key=lambda x: hashlib.sha256(x.encode()).hexdigest())
        n_correct = int(len(sorted_ids) * rate)
        for i, did in enumerate(sorted_ids):
            if i < n_correct:
                correct_ids.add(did)
            else:
                incorrect_ids.add(did)

    print(f"[STEP 3] Marking {len(correct_ids)} correct, {len(incorrect_ids)} incorrect.")

    # Step 4 — Batch update Decision nodes
    # Process in batches of 200
    BATCH = 200
    updated = 0

    # Update correct decisions
    correct_list = list(correct_ids)
    for i in range(0, len(correct_list), BATCH):
        batch = correct_list[i:i + BATCH]
        # AGE doesn't support IN with list params — build inline literal
        id_literal = ", ".join(f"'{did}'" for did in batch)
        await client.run_query(
            f"MATCH (d:Decision) "
            f"WHERE d.decision_id IN [{id_literal}] "
            f"SET d.outcome = 'correct', d.correct = true"
        )
        updated += len(batch)
        if updated % 1000 < BATCH:
            print(f"  Updated {updated}/{null_count}...")

    # Update incorrect decisions
    incorrect_list = list(incorrect_ids)
    for i in range(0, len(incorrect_list), BATCH):
        batch = incorrect_list[i:i + BATCH]
        id_literal = ", ".join(f"'{did}'" for did in batch)
        await client.run_query(
            f"MATCH (d:Decision) "
            f"WHERE d.decision_id IN [{id_literal}] "
            f"SET d.outcome = 'incorrect', d.correct = false"
        )
        updated += len(batch)
        if updated % 1000 < BATCH:
            print(f"  Updated {updated}/{null_count}...")

    print(f"[STEP 4] Updated {updated} Decision nodes.\n")

    # Step 5 — Verification
    rows = await client.run_query(
        "MATCH (d:Decision) WHERE d.correct = true RETURN count(d) AS cnt"
    )
    correct_count = int(rows[0]["cnt"]) if rows else 0

    rows = await client.run_query(
        "MATCH (d:Decision) WHERE d.outcome = 'correct' RETURN count(d) AS cnt"
    )
    outcome_count = int(rows[0]["cnt"]) if rows else 0

    rows = await client.run_query(
        "MATCH (d:Decision) WHERE d.correct = true "
        "RETURN d.category AS category, d.action AS action, count(d) AS n "
        "ORDER BY n DESC LIMIT 5"
    )
    print("[STEP 5] Verification:")
    print(f"  correct=true:      {correct_count}")
    print(f"  outcome='correct': {outcome_count}")
    print(f"  Top category/action pairs:")
    for r in rows:
        print(f"    {r['category']}/{r['action']}: {r['n']}")

    print("\n[OK] Bootstrap complete. Restart uvicorn to refresh endpoints.")


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if DRY_RUN:
        print_plan()
    else:
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(run_live())
