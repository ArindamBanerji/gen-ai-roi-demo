import asyncio
import json
from ci_platform.graph.age_client import AGEClient

QUERIES = {
    "conservation_state_full": """
        MATCH (cs:L5ConservationState)
        RETURN cs.domain AS domain, cs.status AS status, cs.alpha AS alpha, cs.q AS q,
               cs.V AS V, cs.theta_min AS theta_min, cs.product AS product,
               cs.categories_total AS categories_total, cs.categories_with_data AS categories_with_data,
               cs.baseline_product AS baseline_product, cs.relative_threshold AS relative_threshold,
               cs.complacency_flag AS complacency_flag
        LIMIT 5
    """,
    "verified_decisions_soc": """
        MATCH (d:Decision)
        WHERE d.domain = 'soc' AND d.correct IS NOT NULL
        RETURN count(d) AS total
    """,
    "correct_decisions_soc": """
        MATCH (d:Decision)
        WHERE d.domain = 'soc' AND d.correct = true
        RETURN count(d) AS total
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
