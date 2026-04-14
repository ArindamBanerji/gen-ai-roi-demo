import asyncio, os, sys, time
sys.path.insert(0, ".")
os.environ["GRAPH_BACKEND"] = "age"
from ci_platform.graph import get_graph_client

async def ck():
    c = get_graph_client()
    now = int(time.time() * 1000)
    week_ms = 7 * 24 * 60 * 60 * 1000
    for w in range(4):
        end = now - (w * week_ms)
        start = end - week_ms
        r = await c.run_query(
            f"MATCH (d:Decision)-[:DECIDED_ON]->() "
            f"WHERE d.timestamp_epoch > {start} AND d.timestamp_epoch <= {end} "
            f"RETURN count(d) AS n"
        )
        print(f"  Week -{w}: {r[0]['n']} decisions")

asyncio.run(ck())
