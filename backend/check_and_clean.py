import asyncio, os, sys
sys.path.insert(0, ".")
os.environ["GRAPH_BACKEND"] = "age"
from ci_platform.graph import get_graph_client

async def run():
    c = get_graph_client()

    # Sanity check: pick one orphan, verify no edges via alternative query
    r = await c.run_query(
        "MATCH (d:Decision) WHERE NOT EXISTS((d)-[:DECIDED_ON]->()) "
        "RETURN d.decision_id AS did LIMIT 1"
    )
    if r:
        did = r[0]["did"]
        r2 = await c.run_query(
            f"MATCH (d:Decision)-[r]->() WHERE d.decision_id = '{did}' "
            "RETURN type(r) AS rel_type, count(r) AS cnt"
        )
        print(f"Sanity check: orphan {did} relationships: {r2}")
        print(f"Expected: empty list (no relationships)")
        if r2:
            print("ABORT — NOT EXISTS may be unreliable in AGE")
            return

    # Counts before
    orphans = await c.run_query(
        "MATCH (d:Decision) WHERE NOT EXISTS((d)-[:DECIDED_ON]->()) RETURN count(d) AS cnt"
    )
    connected = await c.run_query(
        "MATCH (d:Decision)-[:DECIDED_ON]->() RETURN count(d) AS cnt"
    )
    total = await c.run_query("MATCH (d:Decision) RETURN count(d) AS cnt")
    print(f"\nBEFORE: total={total[0]['cnt']}, orphans={orphans[0]['cnt']}, connected={connected[0]['cnt']}")

    # Delete
    await c.run_query(
        "MATCH (d:Decision) WHERE NOT EXISTS((d)-[:DECIDED_ON]->()) DETACH DELETE d"
    )

    # Counts after
    remaining = await c.run_query("MATCH (d:Decision) RETURN count(d) AS cnt")
    orphans_after = await c.run_query(
        "MATCH (d:Decision) WHERE NOT EXISTS((d)-[:DECIDED_ON]->()) RETURN count(d) AS cnt"
    )
    print(f"AFTER:  total={remaining[0]['cnt']}, orphans={orphans_after[0]['cnt']}")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(run())
