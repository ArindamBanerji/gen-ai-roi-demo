import asyncio
from app.db.neo4j import neo4j_client

async def fix():
    await neo4j_client.connect()
    rows = await neo4j_client.run_query("MATCH (d:Decision) WHERE d.outcome IS NOT NULL RETURN count(*) AS cnt")
    print(f"Before: {rows[0]['cnt']} verified decisions")
    await neo4j_client.run_query("MATCH (d:Decision) WHERE d.category IS NULL OR d.category = 'unknown' DETACH DELETE d")
    rows = await neo4j_client.run_query("MATCH (d:Decision) WHERE d.outcome IS NOT NULL RETURN count(*) AS cnt")
    print(f"After cleanup: {rows[0]['cnt']} verified decisions")

asyncio.run(fix())
