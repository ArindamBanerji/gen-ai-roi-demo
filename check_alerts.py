import asyncio, os, sys
sys.path.insert(0, "backend")
os.environ["GRAPH_BACKEND"] = "age"
from ci_platform.graph import get_graph_client

async def ck():
    c = get_graph_client()
    r1 = await c.run_query("MATCH (a:Alert) RETURN count(a) AS n")
    print("Total alerts:", r1[0]["n"])

    r3 = await c.run_query(
        "MATCH (a:Alert) RETURN a.status AS s, count(a) AS n ORDER BY n DESC"
    )
    print("Status breakdown:")
    for r in r3:
        print("  ", r["s"], ":", r["n"])

    r4 = await c.run_query(
        "MATCH (a:Alert) RETURN a.alert_id AS id, a.status AS s LIMIT 5"
    )
    print("Sample alerts:")
    for r in r4:
        print("  ", r["id"], ":", r["s"])

    # What does the queue query actually look like?
    r5 = await c.run_query(
        "MATCH (a:Alert) WHERE a.status = 'pending' RETURN count(a) AS n"
    )
    print("Pending (direct query):", r5[0]["n"])

    # Check if queue uses a different filter
    r6 = await c.run_query(
        "MATCH (a:Alert) WHERE NOT EXISTS((a)<-[:DECIDED_ON]-()) RETURN count(a) AS n"
    )
    print("Without DECIDED_ON edge:", r6[0]["n"])

asyncio.run(ck())
