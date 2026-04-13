import asyncio, os, sys
sys.path.insert(0, ".")
os.environ["GRAPH_BACKEND"] = "age"
from ci_platform.graph import get_graph_client

async def ck():
    c = get_graph_client()
    r = await c.run_query(
        "MATCH (d:Decision {origin: 'zero_day_synthetic'}) "
        "RETURN d.correct AS val, count(d) AS cnt"
    )
    for row in r:
        print(f"  d.correct={row['val']!r}  count={row['cnt']}")

    r2 = await c.run_query(
        "MATCH (d:Decision) WHERE d.correct = true RETURN count(d) AS n"
    )
    print(f"  WHERE d.correct = true: {r2[0]['n']}")

    r3 = await c.run_query(
        "MATCH (d:Decision) WHERE d.correct = 'true' RETURN count(d) AS n"
    )
    print(f"  WHERE d.correct = 'true': {r3[0]['n']}")

    r4 = await c.run_query(
        "MATCH (d:Decision) WHERE d.outcome = 'correct' RETURN count(d) AS n"
    )
    print(f"  WHERE d.outcome = 'correct': {r4[0]['n']}")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(ck())
