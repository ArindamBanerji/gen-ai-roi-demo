import asyncio, os, sys
sys.path.insert(0, ".")
os.environ["GRAPH_BACKEND"] = "age"
from ci_platform.graph import get_graph_client

async def ck():
    c = get_graph_client()
    r = await c.run_query(
        "MATCH (d:Decision {origin: 'zero_day_synthetic'}) "
        "RETURN d LIMIT 3"
    )
    for row in r:
        d = list(row.values())[0]
        if isinstance(d, dict):
            print(f"  Keys: {sorted(d.keys())}")
            print(f"  correct={d.get('correct')!r} outcome={d.get('outcome')!r}")
            print(f"  action={d.get('action')!r} confidence={d.get('confidence')!r}")
            print()

asyncio.run(ck())
