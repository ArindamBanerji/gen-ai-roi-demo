import asyncio, os, sys
sys.path.insert(0, 'backend')
os.environ['GRAPH_BACKEND'] = 'age'
from ci_platform.graph import get_graph_client
async def ck():
    c = get_graph_client()
    r1 = await c.run_query('MATCH (d:Decision) RETURN count(d) AS total')
    r2 = await c.run_query('MATCH (d:Decision) RETURN count(DISTINCT d.decision_id) AS unique_ids')
    r3 = await c.run_query('MATCH (a:Alert) RETURN count(a) AS alerts')
    r4 = await c.run_query('MATCH (a:Alert) RETURN count(DISTINCT a.alert_id) AS unique_alerts')
    r5 = await c.run_query('MATCH (d:Decision) WHERE d.origin IS NOT NULL RETURN d.origin AS o, count(d) AS n ORDER BY n DESC')
    r6 = await c.run_query('MATCH (d:Decision) WITH d.decision_id AS did, count(d) AS cnt WHERE cnt > 1 RETURN count(did) AS duped_ids, sum(cnt) AS total_duped_nodes')
    print('Decisions total:', r1[0]['total'])
    print('Decisions unique IDs:', r2[0]['unique_ids'])
    print('Duplicated IDs:', r6[0]['duped_ids'], '(', r6[0]['total_duped_nodes'], 'nodes)')
    print('Alerts total:', r3[0]['alerts'])
    print('Alerts unique IDs:', r4[0]['unique_alerts'])
    print('Origin breakdown:')
    for r in r5:
        print(' ', r['o'], ':', r['n'])
asyncio.run(ck())
