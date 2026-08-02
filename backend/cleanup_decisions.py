import asyncio
from app.db.graph_client import graph_client

async def fix():
    await graph_client.connect()
    rows = await graph_client.run_query("MATCH (d:Decision) WHERE d.outcome IS NOT NULL RETURN count(*) AS cnt")
    print(f"Before: {rows[0]['cnt']} verified decisions")
    await graph_client.run_query("MATCH (d:Decision) WHERE d.category IS NULL OR d.category = 'unknown' DETACH DELETE d")
    rows = await graph_client.run_query("MATCH (d:Decision) WHERE d.outcome IS NOT NULL RETURN count(*) AS cnt")
    print(f"After cleanup: {rows[0]['cnt']} verified decisions")

asyncio.run(fix())
