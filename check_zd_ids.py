import asyncio, os, sys
sys.path.insert(0, "backend")
os.environ["GRAPH_BACKEND"] = "age"
from ci_platform.graph import get_graph_client

async def ck():
    c = get_graph_client()
    # Sample decision IDs to see the pattern
    r = await c.run_query(
        "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) "
        "WHERE a.alert_id STARTS WITH 'ZD-' OR a.alert_id STARTS WITH 'zd-' "
        "RETURN d.decision_id AS did, a.alert_id AS aid LIMIT 5"
    )
    print(f"Zero-day linked decisions: {r}")
    
    # What alert_id patterns exist?
    r2 = await c.run_query(
        "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) "
        "RETURN substring(a.alert_id, 0, 6) AS prefix, count(d) AS n "
        "ORDER BY n DESC LIMIT 10"
    )
    print(f"Alert ID prefixes: {r2}")
    
    # Do any Decision nodes have a generator field?
    r3 = await c.run_query(
        "MATCH (d:Decision) WHERE d.generator IS NOT NULL RETURN d.generator AS g LIMIT 5"
    )
    print(f"Generator field: {r3}")

asyncio.run(ck())
