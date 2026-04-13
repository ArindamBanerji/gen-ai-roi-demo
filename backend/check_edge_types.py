import asyncio, os, sys
sys.path.insert(0, ".")
os.environ["GRAPH_BACKEND"] = "age"
from ci_platform.graph import get_graph_client

async def run():
    c = get_graph_client()

    # What relationship types do Decision nodes have?
    r = await c.run_query(
        "MATCH (d:Decision)-[r]->() "
        "RETURN type(r) AS rel_type, count(r) AS cnt ORDER BY cnt DESC"
    )
    print("Decision outgoing relationships:")
    for row in r: print(f"  {row}")

    # How many Decisions have DECIDED_ON vs FOR_ALERT vs both vs neither?
    r2 = await c.run_query(
        "MATCH (d:Decision) "
        "RETURN "
        "sum(CASE WHEN EXISTS((d)-[:DECIDED_ON]->()) THEN 1 ELSE 0 END) AS has_decided_on, "
        "sum(CASE WHEN EXISTS((d)-[:FOR_ALERT]->()) THEN 1 ELSE 0 END) AS has_for_alert, "
        "sum(CASE WHEN NOT EXISTS((d)-[:DECIDED_ON]->()) AND NOT EXISTS((d)-[:FOR_ALERT]->()) THEN 1 ELSE 0 END) AS truly_orphaned, "
        "count(d) AS total"
    )
    print(f"\nDecision edge coverage: {r2}")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(run())
