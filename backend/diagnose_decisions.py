import asyncio
from app.db.graph_client import graph_client

async def diagnose():
    await graph_client.connect()
    
    # What categories actually exist on Decision nodes?
    rows = await graph_client.run_query(
        "MATCH (d:Decision) WHERE d.outcome IS NOT NULL "
        "RETURN d.category AS cat LIMIT 5"
    )
    for r in rows:
        print(f"  category = {repr(r.get('cat'))}")
    
    # Do they have category at all?
    rows2 = await graph_client.run_query(
        "MATCH (d:Decision) WHERE d.category IS NULL AND d.outcome IS NOT NULL "
        "RETURN count(*) AS cnt"
    )
    print(f"  Null category count: {rows2[0]['cnt'] if rows2 else '?'}")

asyncio.run(diagnose())
