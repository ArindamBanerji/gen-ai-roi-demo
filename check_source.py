import asyncio, os, sys
sys.path.insert(0, "backend")
os.environ["GRAPH_BACKEND"] = "age"
from ci_platform.graph import get_graph_client

async def ck():
    c = get_graph_client()
    
    # How many Decision nodes have source set?
    r1 = await c.run_query("MATCH (d:Decision) WHERE d.source IS NOT NULL RETURN count(d) AS n")
    print(f"Decisions with source field: {r1[0]['n']}")
    
    # How many have source starting with zero_day?
    r2 = await c.run_query("MATCH (d:Decision) WHERE d.source STARTS WITH 'zero_day_' RETURN count(d) AS n")
    print(f"Decisions with zero_day source: {r2[0]['n']}")
    
    # How many total?
    r3 = await c.run_query("MATCH (d:Decision) RETURN count(d) AS n")
    print(f"Total decisions: {r3[0]['n']}")
    
    # Sample a few to see what source looks like
    r4 = await c.run_query("MATCH (d:Decision) WHERE d.source IS NOT NULL RETURN d.source AS src LIMIT 5")
    print(f"Sample sources: {[r['src'] for r in r4]}")
    
    # Sample zero-day nodes specifically
    r5 = await c.run_query("MATCH (d:Decision) WHERE d.decision_id STARTS WITH 'zd-' RETURN d.decision_id AS id, d.source AS src, d.correct AS correct LIMIT 5")
    print(f"Zero-day nodes: {r5}")

asyncio.run(ck())
