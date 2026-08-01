import asyncio
import os
from ci_platform.graph.age_client import AGEClient

async def main():
    os.environ["GRAPH_BACKEND"] = "age"
    os.environ["GRAPH_DSN"] = "host=localhost port=5433 dbname=soc_copilot user=postgres password=postgres"
    os.environ["AGE_GRAPH_NAME"] = "soc_graph_diag_f6"
    c = AGEClient()
    queries = {
        "total_nodes": "MATCH (n) RETURN count(n) AS total",
        "f6_decisions": "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) WHERE a.alert_id STARTS WITH 'DIAG-F6-CRED' RETURN count(d) AS decisions",
        "f6_verified": "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) WHERE a.alert_id STARTS WITH 'DIAG-F6-CRED' RETURN sum(CASE WHEN coalesce(d.verified, false) = true THEN 1 ELSE 0 END) AS verified, sum(CASE WHEN coalesce(d.outcome, '') <> '' THEN 1 ELSE 0 END) AS outcome_present",
        "l5_centroid": "MATCH (n:L5Centroid) RETURN count(n) AS count",
        "l5_dk_weight": "MATCH (n:L5DKWeight) RETURN count(n) AS count, max(n.n_decisions_used) AS max_n_decisions_used",
        "l5_conservation": "MATCH (n:L5ConservationState) RETURN count(n) AS count",
        "shaped_by": "MATCH (:L5Centroid)-[r:SHAPED_BY]->(:Decision) RETURN count(r) AS count"
    }
    for name, q in queries.items():
        try:
            print(f"## {name}")
            print(await c.run_query(q))
        except Exception as e:
            print(f"## {name} ERROR")
            print(repr(e))

asyncio.run(main())
