"""Flip ~15% of zero-day synthetic decisions to incorrect. One-time fix."""
import asyncio, os, sys, random
sys.path.insert(0, ".")
os.environ["GRAPH_BACKEND"] = "age"
from ci_platform.graph import get_graph_client

ERROR_RATE = 0.15
random.seed(42)

async def run():
    c = get_graph_client()
    r = await c.run_query(
        "MATCH (d:Decision {origin: 'zero_day_synthetic'}) "
        "RETURN d.decision_id AS did, d.category AS cat"
    )
    print(f"Total synthetic decisions: {len(r)}")
    to_flip = [row for row in r if random.random() < ERROR_RATE]
    print(f"Flipping {len(to_flip)} to incorrect ({len(to_flip)/len(r):.1%})")

    for row in to_flip:
        await c.run_query(
            f"MATCH (d:Decision {{decision_id: '{row['did']}'}}) "
            f"SET d.correct = false, d.outcome = 'incorrect'"
        )

    verify = await c.run_query(
        "MATCH (d:Decision {origin: 'zero_day_synthetic'}) "
        "RETURN sum(CASE WHEN d.correct = true THEN 1 ELSE 0 END) AS correct, "
        "count(d) AS total"
    )
    v = verify[0]
    print(f"After: {v['correct']}/{v['total']} correct = {int(v['correct'])/int(v['total']):.1%}")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(run())
