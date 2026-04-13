import asyncio, os, sys
sys.path.insert(0, ".")
os.environ["GRAPH_BACKEND"] = "age"
from ci_platform.graph import get_graph_client

async def run():
    c = get_graph_client()
    before = await c.run_query("MATCH (d:Decision) RETURN count(d) AS cnt")
    orphans = await c.run_query(
        "MATCH (d:Decision) WHERE NOT EXISTS((d)-[:DECIDED_ON]->()) RETURN count(d) AS cnt"
    )
    connected = await c.run_query(
        "MATCH (d:Decision)-[:DECIDED_ON]->() RETURN count(d) AS cnt"
    )
    print(f"BEFORE: total={before[0]['cnt']}, orphans={orphans[0]['cnt']}, connected={connected[0]['cnt']}")

    await c.run_query(
        "MATCH (d:Decision) WHERE NOT EXISTS((d)-[:DECIDED_ON]->()) DETACH DELETE d"
    )

    after = await c.run_query("MATCH (d:Decision) RETURN count(d) AS cnt")
    remaining = await c.run_query(
        "MATCH (d:Decision) WHERE NOT EXISTS((d)-[:DECIDED_ON]->()) RETURN count(d) AS cnt"
    )
    print(f"AFTER:  total={after[0]['cnt']}, orphans={remaining[0]['cnt']}")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(run())
