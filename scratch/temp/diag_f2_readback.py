from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROJECTS = REPO.parent
for path in (REPO / "backend", PROJECTS / "ci-platform"):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)

from ci_platform.graph.age_client import AGEClient  # noqa: E402


async def main() -> None:
    client = AGEClient()
    queries = {
        "alerts": "MATCH (a:Alert) WHERE a.alert_id STARTS WITH 'DIAG-F2-CRED' RETURN count(a) AS cnt",
        "decisions": "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) WHERE d.domain='soc' AND a.alert_id STARTS WITH 'DIAG-F2-CRED' RETURN count(d) AS cnt",
        "verified_correct": "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) WHERE d.domain='soc' AND a.alert_id STARTS WITH 'DIAG-F2-CRED' AND d.outcome='correct' AND d.correct=true RETURN count(d) AS cnt",
        "by_category": "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) WHERE d.domain='soc' AND a.alert_id STARTS WITH 'DIAG-F2-CRED' RETURN d.category AS category, count(d) AS cnt ORDER BY category",
        "correct_by_category": "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) WHERE d.domain='soc' AND a.alert_id STARTS WITH 'DIAG-F2-CRED' AND d.outcome='correct' AND d.correct=true RETURN d.category AS category, count(d) AS cnt ORDER BY category",
        "l5_centroid": "MATCH (c:L5Centroid) WHERE c.domain='soc' RETURN count(c) AS cnt",
        "shaped_by": "MATCH ()-[r:SHAPED_BY]->() RETURN count(r) AS cnt",
        "l5_dk_weight": "MATCH (w:L5DKWeight) WHERE w.domain='soc' RETURN count(w) AS cnt",
        "dk_fields": "MATCH (w:L5DKWeight) WHERE w.domain='soc' RETURN w.n_decisions_used AS n_decisions_used, w.confirmed_mean_json IS NOT NULL AS confirmed_mean_json, w.confirmed_m2_json IS NOT NULL AS confirmed_m2_json, w.overridden_mean_json IS NOT NULL AS overridden_mean_json, w.overridden_m2_json IS NOT NULL AS overridden_m2_json, w.all_mean_json IS NOT NULL AS all_mean_json, w.all_m2_json IS NOT NULL AS all_m2_json LIMIT 10",
        "conservation": "MATCH (cs:L5ConservationState) WHERE cs.domain='soc' RETURN cs.status AS status, cs.alpha AS alpha, cs.q AS q, cs.V AS V, cs.theta_min AS theta_min, cs.categories_with_data AS categories_with_data LIMIT 10",
    }
    out = {}
    for key, query in queries.items():
        out[key] = await client.run_query(query)
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
