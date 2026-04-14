"""EXP 7: Does AGE support SET n += {props} (merge, not replace)?"""
import asyncio, os, sys
sys.path.insert(0, ".")
os.environ["GRAPH_BACKEND"] = "age"
from ci_platform.graph import get_graph_client

async def exp7():
    c = get_graph_client()

    print("EXP 7: SET n += {props} (merge syntax)")
    await c.run_query(
        "CREATE (t:TestIntegrity {test_id: 'exp7', a: 1, b: 2, c: 3})"
    )

    r0 = await c.run_query(
        "MATCH (t:TestIntegrity {test_id: 'exp7'}) "
        "RETURN t.a AS a, t.b AS b, t.c AS c"
    )
    print(f"  Before: a={r0[0]['a']}, b={r0[0]['b']}, c={r0[0]['c']}")

    try:
        await c.run_query(
            "MATCH (t:TestIntegrity {test_id: 'exp7'}) SET t += {a: 99, d: 4}"
        )
        r = await c.run_query(
            "MATCH (t:TestIntegrity {test_id: 'exp7'}) "
            "RETURN t.a AS a, t.b AS b, t.c AS c, t.d AS d"
        )
        if r:
            row = r[0]
            print(f"  After:  a={row['a']}, b={row.get('b', 'WIPED')}, c={row.get('c', 'WIPED')}, d={row.get('d', 'MISSING')}")
            if row.get("b") == 2 and row.get("d") == 4:
                print("  >>> += MERGES: preserves existing, adds new. SAFE for bulk updates.")
            elif row.get("b") is None:
                print("  >>> += WIPES like =. NOT safe.")
            else:
                print(f"  >>> Unexpected result")
        else:
            print("  >>> Node not found after +=")
    except Exception as e:
        print(f"  >>> AGE does not support +=: {e}")

    await c.run_query("MATCH (t:TestIntegrity {test_id: 'exp7'}) DETACH DELETE t")
    print("Cleanup done.")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(exp7())
