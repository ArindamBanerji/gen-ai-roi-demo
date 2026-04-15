import asyncio, os, sys
sys.path.insert(0, 'backend')
os.environ['GRAPH_BACKEND'] = 'age'
from ci_platform.graph import get_graph_client
async def ck():
    c = get_graph_client()
    for label in ['User','Asset','Alert','Decision','Campaign','ThreatIndicator','ShadowDecision']:
        r = await c.run_query('MATCH (n:' + label + ') RETURN count(n) AS n')
        print(label + ': ' + str(r[0]['n']))
    print()
    for edge in ['INVOLVES','DETECTED_ON','DECIDED_ON','HAS_INDICATOR']:
        r = await c.run_query('MATCH ()-[r:' + edge + ']->() RETURN count(r) AS n')
        print(edge + ': ' + str(r[0]['n']))
asyncio.run(ck())
