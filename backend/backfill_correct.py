import asyncio, os, sys
sys.path.insert(0, ".")
os.environ["GRAPH_BACKEND"] = "age"
from ci_platform.graph import get_graph_client

async def fix():
    c = get_graph_client()

    # Backfill from outcome field (which DID get stored)
    r1 = await c.run_query(
        "MATCH (d:Decision {origin: 'zero_day_synthetic'}) "
        "WHERE d.outcome = 'correct' "
        "SET d.correct = true "
        "RETURN count(d) AS n"
    )
    print(f"Set correct=true:  {r1[0]['n']}")

    r2 = await c.run_query(
        "MATCH (d:Decision {origin: 'zero_day_synthetic'}) "
        "WHERE d.outcome = 'incorrect' "
        "SET d.correct = false "
        "RETURN count(d) AS n"
    )
    print(f"Set correct=false: {r2[0]['n']}")

    # Verify
    r3 = await c.run_query(
        "MATCH (d:Decision) WHERE d.correct = true RETURN count(d) AS n"
    )
    print(f"Total correct=true: {r3[0]['n']}  (expect ~3972)")

    r4 = await c.run_query(
        "MATCH (d:Decision) WHERE d.correct IS NULL RETURN count(d) AS n"
    )
    print(f"correct IS NULL:    {r4[0]['n']}  (expect 0 or near-0)")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(fix())
