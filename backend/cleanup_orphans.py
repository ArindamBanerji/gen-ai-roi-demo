import asyncio, os, sys
sys.path.insert(0, ".")
os.environ["GRAPH_BACKEND"] = "age"
from ci_platform.graph import get_graph_client

async def clean():
    c = get_graph_client()
    r = await c.run_query(
        "MATCH (d:Decision) WHERE NOT EXISTS((d)-[:DECIDED_ON]->()) "
        "RETURN count(d) AS n"
    )
    print(f"Orphans before: {r[0]['n']}")
    await c.run_query(
        "MATCH (d:Decision) WHERE NOT EXISTS((d)-[:DECIDED_ON]->()) "
        "DETACH DELETE d"
    )
    r2 = await c.run_query(
        "MATCH (d:Decision) WHERE NOT EXISTS((d)-[:DECIDED_ON]->()) "
        "RETURN count(d) AS n"
    )
    print(f"Orphans after:  {r2[0]['n']}")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(clean())
