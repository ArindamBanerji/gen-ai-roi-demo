import asyncio, os, sys
sys.path.insert(0, ".")
os.environ["GRAPH_BACKEND"] = "age"
from ci_platform.graph import get_graph_client

async def ck():
    c = get_graph_client()
    r = await c.run_query("MATCH (d:Decision) WHERE d.correct = true RETURN count(d) AS n")
    print(f"correct=true: {r[0]['n']}")
    r2 = await c.run_query("MATCH (d:Decision) WHERE d.correct IS NULL RETURN count(d) AS n")
    print(f"correct=NULL: {r2[0]['n']}")
    r3 = await c.run_query("MATCH (d:Decision) WHERE d.outcome IS NOT NULL RETURN count(d) AS n")
    print(f"outcome NOT NULL: {r3[0]['n']}")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(ck())
