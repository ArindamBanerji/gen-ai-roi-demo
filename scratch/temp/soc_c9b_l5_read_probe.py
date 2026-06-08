import asyncio
import json
from ci_platform.graph.age_client import AGEClient

DECISION_IDS = [
    '4f3bce21-e490-44f3-b25b-2a4723c9d772',
    'd3331ac4-4357-497b-8c64-0741de2379a2',
    'b211b9d3-fa13-488e-9ba4-577dcb6c2daa',
    '4765c909-d4d3-46d5-af61-3cb053f1fc40',
    'a646eeaf-954f-48d0-9bbd-580c3deac638',
]
ids = '[' + ', '.join("'" + x + "'" for x in DECISION_IDS) + ']'
QUERIES = {
    "health_counts": """
        MATCH (d:Decision) WHERE d.domain = 'soc' RETURN count(d) AS total
    """,
    "diag_e2_decisions_by_ids": f"""
        MATCH (d:Decision)
        WHERE d.decision_id IN {ids}
        OPTIONAL MATCH (d)-[:DECIDED_ON]->(a:Alert)
        RETURN d.decision_id AS decision_id, d.domain AS domain, a.alert_id AS alert_id,
               d.action AS action, d.outcome AS outcome, d.correct AS correct,
               d.category AS category, d.centroid_delta_norm AS centroid_delta_norm,
               d.factor_vector AS factor_vector, d.verified_at_epoch AS verified_at_epoch
        ORDER BY decision_id
    """,
    "diag_e2_decisions_by_alert": """
        MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)
        WHERE a.alert_id IN ['DIAG-E2-001','DIAG-E2-002','DIAG-E2-003','DIAG-E2-004','DIAG-E2-005']
        RETURN d.decision_id AS decision_id, d.domain AS domain, a.alert_id AS alert_id,
               d.action AS action, d.outcome AS outcome, d.correct AS correct,
               d.category AS category, d.centroid_delta_norm AS centroid_delta_norm,
               d.factor_vector AS factor_vector, d.verified_at_epoch AS verified_at_epoch
        ORDER BY a.alert_id
    """,
    "l5_centroids_total": """
        MATCH (c:L5Centroid) RETURN count(c) AS total
    """,
    "l5_centroids_soc": """
        MATCH (c:L5Centroid) WHERE c.domain = 'soc' RETURN count(c) AS total
    """,
    "l5_centroids_sample": """
        MATCH (c:L5Centroid)
        RETURN c.domain AS domain, c.category AS category, c.action AS action,
               c.caused_by_decision_id AS caused_by_decision_id, c.delta_norm AS delta_norm
        LIMIT 10
    """,
    "shaped_by_total": """
        MATCH ()-[r:SHAPED_BY]->() RETURN count(r) AS total
    """,
    "l5_conservation": """
        MATCH (cs:L5ConservationState)
        RETURN cs.domain AS domain, cs.status AS status, cs.alpha AS alpha, cs.q AS q,
               cs.categories_total AS categories_total, cs.categories_with_data AS categories_with_data
        LIMIT 5
    """,
    "l5dk_total": """
        MATCH (w:L5DKWeight) RETURN count(w) AS total
    """,
}

async def main():
    c = AGEClient()
    out = {}
    for name, q in QUERIES.items():
        try:
            out[name] = await c.run_query(q)
        except Exception as exc:
            out[name] = {"error": type(exc).__name__, "message": str(exc)}
    print(json.dumps(out, indent=2, default=str))

asyncio.run(main())
