"""Test: does AGE SET on one property wipe other properties?"""
import asyncio, os, sys
sys.path.insert(0, ".")
os.environ["GRAPH_BACKEND"] = "age"
from ci_platform.graph import get_graph_client

async def experiment():
    c = get_graph_client()

    # Step 1: Create a test node with 4 properties
    await c.run_query(
        "CREATE (t:TestSetBehavior {"
        "test_id: 'SET-TEST-001', "
        "prop_a: 'alpha', "
        "prop_b: true, "
        "prop_c: 42"
        "})"
    )
    print("Created: test_id, prop_a, prop_b, prop_c")

    # Step 2: Read back — all 4 should exist
    r = await c.run_query(
        "MATCH (t:TestSetBehavior {test_id: 'SET-TEST-001'}) RETURN t"
    )
    before = list(r[0].values())[0]
    print(f"Before SET: {sorted(before.keys())}")
    print(f"  prop_a={before.get('prop_a')!r} prop_b={before.get('prop_b')!r} prop_c={before.get('prop_c')!r}")

    # Step 3: SET only prop_a to a new value
    await c.run_query(
        "MATCH (t:TestSetBehavior {test_id: 'SET-TEST-001'}) "
        "SET t.prop_a = 'beta' "
        "RETURN t"
    )
    print("\nRan: SET t.prop_a = 'beta'")

    # Step 4: Read back — prop_b and prop_c should still exist
    r2 = await c.run_query(
        "MATCH (t:TestSetBehavior {test_id: 'SET-TEST-001'}) RETURN t"
    )
    after = list(r2[0].values())[0]
    print(f"After SET:  {sorted(after.keys())}")
    print(f"  prop_a={after.get('prop_a')!r} prop_b={after.get('prop_b')!r} prop_c={after.get('prop_c')!r}")

    # Step 5: Verdict
    lost = []
    if after.get("prop_b") is None: lost.append("prop_b")
    if after.get("prop_c") is None: lost.append("prop_c")
    if lost:
        print(f"\n*** AGE BUG CONFIRMED: SET wiped {lost} ***")
    else:
        print(f"\n*** AGE SET is safe -- properties preserved. Data loss came from elsewhere. ***")

    # Cleanup
    await c.run_query("MATCH (t:TestSetBehavior {test_id: 'SET-TEST-001'}) DELETE t")
    print("Cleaned up test node.")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(experiment())
