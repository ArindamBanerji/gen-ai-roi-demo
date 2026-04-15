"""Test AGE Cypher syntax for pre-deletion safety check.

Tests three approaches:
1. CASE WHEN inside count() — what Claude Code implemented
2. WITH d WHERE chaining — what the roadmap session recommends
3. Double WHERE — known invalid, should fail

Run from repo root: python test_age_precheck.py
"""
import asyncio
import os
import sys

sys.path.insert(0, "backend")
os.environ["GRAPH_BACKEND"] = "age"

from ci_platform.graph import get_graph_client


async def test():
    c = get_graph_client()
    
    # The filter that StateManager uses
    FILTER = "WHERE d.origin IS NULL OR d.origin <> 'zero_day_synthetic'"
    ORIGIN = "zero_day_synthetic"

    print("=" * 60)
    print("Testing AGE Cypher syntax for pre-deletion safety check")
    print("=" * 60)

    # --- Approach 1: CASE WHEN (what Claude Code implemented) ---
    print("\n1. CASE WHEN inside count():")
    try:
        r = await c.run_query(
            f"MATCH (d:Decision) {FILTER} "
            f"RETURN count(CASE WHEN d.origin = '{ORIGIN}' "
            f"THEN 1 ELSE NULL END) AS n_persistent, "
            f"count(d) AS n_total"
        )
        print(f"   WORKS: n_persistent={r[0]['n_persistent']}, n_total={r[0]['n_total']}")
    except Exception as e:
        print(f"   FAILS: {e}")

    # --- Approach 2: WITH d WHERE chaining (roadmap recommendation) ---
    print("\n2. WITH d WHERE chaining:")
    try:
        r = await c.run_query(
            f"MATCH (d:Decision) {FILTER} "
            f"WITH d WHERE d.origin = '{ORIGIN}' "
            f"RETURN count(d) AS n"
        )
        print(f"   WORKS: n={r[0]['n']}")
    except Exception as e:
        print(f"   FAILS: {e}")

    # --- Approach 3: Double WHERE (known invalid) ---
    print("\n3. Double WHERE (should fail):")
    try:
        r = await c.run_query(
            f"MATCH (d:Decision) {FILTER} "
            f"WHERE d.origin = '{ORIGIN}' "
            f"RETURN count(d) AS n"
        )
        print(f"   WORKS (unexpected!): n={r[0]['n']}")
    except Exception as e:
        print(f"   FAILS (expected): {type(e).__name__}")

    # --- Approach 4: Simple count for comparison ---
    print("\n4. Baseline counts (no filter chaining):")
    try:
        r1 = await c.run_query(
            "MATCH (d:Decision) RETURN count(d) AS n"
        )
        r2 = await c.run_query(
            f"MATCH (d:Decision) WHERE d.origin = '{ORIGIN}' "
            "RETURN count(d) AS n"
        )
        r3 = await c.run_query(
            f"MATCH (d:Decision) {FILTER} RETURN count(d) AS n"
        )
        print(f"   Total decisions: {r1[0]['n']}")
        print(f"   Persistent (origin=zero_day_synthetic): {r2[0]['n']}")
        print(f"   Session (SESSION_FILTER): {r3[0]['n']}")
    except Exception as e:
        print(f"   FAILS: {e}")

    # --- Summary ---
    print("\n" + "=" * 60)
    print("RECOMMENDATION:")
    print("  If approach 1 works: current code is safe")
    print("  If approach 1 fails: CRITICAL — pre-check is broken,")
    print("    switch to approach 2 (WITH d WHERE)")
    print("=" * 60)


asyncio.run(test())
