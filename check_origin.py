import asyncio, os, sys
sys.path.insert(0, "backend")
os.environ["GRAPH_BACKEND"] = "age"
from ci_platform.graph import get_graph_client

async def ck():
    c = get_graph_client()
    r1 = await c.run_query("MATCH (d:Decision) WHERE d.origin IS NOT NULL RETURN count(d) AS n")
    print(f"Decisions with origin field: {r1[0]['n']}")
    
    r2 = await c.run_query("MATCH (d:Decision) WHERE d.origin = 'zero_day_synthetic' RETURN count(d) AS n")
    print(f"Zero-day synthetic decisions: {r2[0]['n']}")
    
    r3 = await c.run_query("MATCH (d:Decision) WHERE d.origin IS NULL RETURN count(d) AS n")
    print(f"Decisions WITHOUT origin: {r3[0]['n']}")
    
    r4 = await c.run_query("MATCH (d:Decision) RETURN count(d) AS n")
    print(f"Total decisions: {r4[0]['n']}")

asyncio.run(ck())
