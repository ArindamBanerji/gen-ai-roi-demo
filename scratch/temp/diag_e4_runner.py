from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REPO = Path(__file__).resolve().parents[2]
PROJECTS = REPO.parent
BACKEND = REPO / "backend"
CI_PLATFORM = PROJECTS / "ci-platform"
for p in (str(BACKEND), str(CI_PLATFORM), str(REPO)):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.graph_schema import _S  # noqa: E402
from ci_platform.graph.age_client import AGEClient  # noqa: E402


BASE_URL = "http://127.0.0.1:8001"
GRAPH_DSN = "host=localhost port=5433 dbname=soc_copilot user=postgres password=postgres"
GRAPH_NAME = "soc_graph_diag_e4"
ALERT_IDS = [f"DIAG-E4-CRED-{i:03d}" for i in range(1, 6)]
SCORER_ACTIONS = {"escalate", "investigate", "suppress", "monitor"}


def post_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = Request(
        BASE_URL + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return {
                "status": resp.status,
                "body": json.loads(body) if body else {},
                "raw": body,
            }
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        parsed: Any
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = body
        return {"status": exc.code, "body": parsed, "raw": body}
    except URLError as exc:
        return {"status": None, "body": {"error": str(exc)}, "raw": str(exc)}


async def scalar(client: AGEClient, query: str, key: str = "cnt") -> int:
    rows = await client.run_query(query)
    if not rows:
        return 0
    return int(rows[0].get(key) or 0)


async def seed_alerts(client: AGEClient) -> dict[str, Any]:
    created = 0
    existing = 0
    seeded: list[dict[str, Any]] = []
    for idx, alert_id in enumerate(ALERT_IDS, start=1):
        user_id = f"{alert_id}-USER"
        asset_id = f"{alert_id}-ASSET"
        exists = await scalar(
            client,
            f"MATCH (a:Alert {{alert_id: {_S(alert_id)}}}) RETURN count(a) AS cnt",
        )
        if exists:
            existing += 1
        else:
            await client.run_query(
                "CREATE (u:User {"
                + ", ".join(
                    [
                        f"user_id: {_S(user_id)}",
                        f"id: {_S(user_id)}",
                        f"name: {_S('C9B Proof User ' + str(idx))}",
                        "origin: 'c9b_seed'",
                        "department: 'SOC'",
                        "risk_level: 'critical'",
                        "risk_score: 0.92",
                        "c9b_proof: true",
                    ]
                )
                + "})"
            )
            await client.run_query(
                "CREATE (asset:Asset {"
                + ", ".join(
                    [
                        f"asset_id: {_S(asset_id)}",
                        f"id: {_S(asset_id)}",
                        f"hostname: {_S('c9b-proof-e4-' + str(idx))}",
                        "criticality: 'critical'",
                        "origin: 'c9b_seed'",
                        "asset_type: 'workload'",
                        "business_unit: 'security'",
                        "c9b_proof: true",
                    ]
                )
                + "})"
            )
            await client.run_query(
                "CREATE (a:Alert {"
                + ", ".join(
                    [
                        f"alert_id: {_S(alert_id)}",
                        f"id: {_S(alert_id)}",
                        "category: 'credential_access'",
                        "severity: 'critical'",
                        "alert_type: 'anomalous_login'",
                        "status: 'pending'",
                        "origin: 'c9b_seed'",
                        "source: 'c9b_seed'",
                        "c9b_proof: true",
                        f"timestamp_epoch: {1725000000000 + idx}",
                        f"source_location: {_S('c9b-seed-zone-e4-' + str(idx))}",
                        f"user_id: {_S(user_id)}",
                        f"asset_id: {_S(asset_id)}",
                        "attack_pattern_id: ''",
                        "mfa_completed: false",
                        "device_fingerprint_match: false",
                        "vpn_provider: 'c9b_seed'",
                    ]
                )
                + "})"
            )
            created += 1
        await client.run_query(
            f"MATCH (a:Alert {{alert_id: {_S(alert_id)}}}), "
            f"(u:User {{user_id: {_S(user_id)}}}) "
            "CREATE (a)-[:INVOLVES]->(u)"
        )
        await client.run_query(
            f"MATCH (a:Alert {{alert_id: {_S(alert_id)}}}), "
            f"(asset:Asset {{asset_id: {_S(asset_id)}}}) "
            "CREATE (a)-[:DETECTED_ON]->(asset)"
        )
        seeded.append(
            {
                "alert_id": alert_id,
                "user_id": user_id,
                "asset_id": asset_id,
                "alert_type": "anomalous_login",
                "category": "credential_access",
                "severity": "critical",
                "risk_score": 0.92,
                "asset_criticality": "critical",
                "mfa_completed": False,
                "device_fingerprint_match": False,
            }
        )
    return {"created": created, "existing": existing, "seeded": seeded}


def extract_decision_id(body: dict[str, Any]) -> str | None:
    return (
        body.get("decision_id")
        or body.get("id")
        or body.get("recommendation", {}).get("decision_id")
        or body.get("gae_scoring", {}).get("decision_id")
    )


def extract_action(body: dict[str, Any]) -> str | None:
    return body.get("action") or body.get("recommendation", {}).get("action")


def extract_confidence(body: dict[str, Any]) -> Any:
    return body.get("confidence") or body.get("recommendation", {}).get("confidence")


def compact_analyze(body: dict[str, Any]) -> dict[str, Any]:
    fv = body.get("factor_vector") or body.get("gae_scoring", {}).get("factor_vector")
    return {
        "category": body.get("category")
        or body.get("alert", {}).get("category")
        or body.get("situation_analysis", {}).get("category"),
        "action": extract_action(body),
        "confidence": extract_confidence(body),
        "decision_id": extract_decision_id(body),
        "factor_vector": fv,
        "factor_vector_len": len(fv) if isinstance(fv, list) else None,
        "routing_zone": body.get("routing_zone")
        or body.get("recommendation", {}).get("routing_zone")
        or body.get("gae_scoring", {}).get("routing_zone"),
        "referral": body.get("referral"),
        "decision_method": body.get("decision_method"),
    }


def compact_outcome(body: dict[str, Any]) -> dict[str, Any]:
    return {
        "outcome_id": body.get("outcome_id") or body.get("id"),
        "outcome": body.get("outcome"),
        "correct": body.get("correct"),
        "verification": body.get("verification"),
        "centroid_update": body.get("centroid_update"),
        "l5_centroid_persisted": body.get("l5_centroid_persisted"),
        "l5_persistence_skipped_reason": body.get("l5_persistence_skipped_reason"),
        "l5_persistence": body.get("l5_persistence"),
    }


async def readback(client: AGEClient, decision_ids: list[str]) -> dict[str, Any]:
    ids_json = json.dumps(decision_ids)
    prefix = "DIAG-E4-CRED"
    queries = {
        "decisions_domain": f"""
            MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)
            WHERE d.domain = 'soc' AND a.alert_id STARTS WITH {_S(prefix)}
            RETURN count(d) AS cnt
        """,
        "non_referral": f"""
            MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)
            WHERE d.domain = 'soc' AND a.alert_id STARTS WITH {_S(prefix)}
              AND d.action <> 'refer_to_analyst'
            RETURN count(d) AS cnt
        """,
        "outcomes_posted": f"""
            MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)
            WHERE d.domain = 'soc' AND a.alert_id STARTS WITH {_S(prefix)}
              AND d.outcome IS NOT NULL AND d.correct IS NOT NULL
            RETURN count(d) AS cnt
        """,
        "l5_centroid": "MATCH (c:L5Centroid) WHERE c.domain = 'soc' RETURN count(c) AS cnt",
        "diag_caused_l5_centroid": f"""
            MATCH (c:L5Centroid)
            WHERE c.domain = 'soc' AND c.caused_by_decision_id IN {ids_json}
            RETURN count(c) AS cnt
        """,
        "shaped_by": "MATCH (c:L5Centroid)-[:SHAPED_BY]->(d:Decision) WHERE c.domain = 'soc' RETURN count(*) AS cnt",
        "diag_shaped_by": f"""
            MATCH (c:L5Centroid)-[:SHAPED_BY]->(d:Decision)-[:DECIDED_ON]->(a:Alert)
            WHERE c.domain = 'soc' AND a.alert_id STARTS WITH {_S(prefix)}
            RETURN count(*) AS cnt
        """,
        "l5_dk_weight": "MATCH (w:L5DKWeight) WHERE w.domain = 'soc' RETURN count(w) AS cnt",
        "l5_conservation": "MATCH (cs:L5ConservationState) WHERE cs.domain = 'soc' RETURN count(cs) AS cnt",
    }
    counts: dict[str, int] = {}
    raw: dict[str, Any] = {}
    for name, query in queries.items():
        rows = await client.run_query(query)
        raw[name] = rows
        counts[name] = int(rows[0].get("cnt") or 0) if rows else 0
    raw["decision_rows"] = await client.run_query(
        f"""
        MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)
        WHERE d.domain = 'soc' AND a.alert_id STARTS WITH {_S(prefix)}
        RETURN a.alert_id AS alert_id, d.decision_id AS decision_id,
               d.category AS category, d.action AS action,
               d.confidence AS confidence, d.outcome AS outcome,
               d.correct AS correct, d.factor_vector AS factor_vector,
               d.verified_at_epoch AS verified_at_epoch
        ORDER BY a.alert_id, d.timestamp_epoch
        """
    )
    raw["diag_l5_rows"] = await client.run_query(
        f"""
        MATCH (c:L5Centroid)
        WHERE c.domain = 'soc' AND c.caused_by_decision_id IN {ids_json}
        RETURN c.domain AS domain, c.category AS category, c.action AS action,
               c.caused_by_decision_id AS caused_by_decision_id,
               c.delta_norm AS delta_norm
        """
    )
    raw["diag_shaped_rows"] = await client.run_query(
        f"""
        MATCH (c:L5Centroid)-[:SHAPED_BY]->(d:Decision)-[:DECIDED_ON]->(a:Alert)
        WHERE c.domain = 'soc' AND a.alert_id STARTS WITH {_S(prefix)}
        RETURN a.alert_id AS alert_id, d.decision_id AS decision_id,
               c.category AS category, c.action AS action,
               c.caused_by_decision_id AS caused_by_decision_id
        """
    )
    return {"counts": counts, "raw": raw}


async def main() -> int:
    client = AGEClient(dsn=GRAPH_DSN, graph_name=GRAPH_NAME)
    await client.ensure_graph()
    seed = await seed_alerts(client)
    loops = []
    decision_ids: list[str] = []
    for alert_id in ALERT_IDS:
        analyze = post_json("/api/alert/analyze", {"alert_id": alert_id})
        analyze_compact = compact_analyze(analyze["body"]) if isinstance(analyze["body"], dict) else {}
        decision_id = analyze_compact.get("decision_id")
        action = analyze_compact.get("action")
        outcome = None
        outcome_compact = None
        if analyze["status"] == 200 and decision_id and action in SCORER_ACTIONS:
            decision_ids.append(str(decision_id))
            outcome = post_json(
                "/api/alert/outcome",
                {
                    "alert_id": alert_id,
                    "decision_id": decision_id,
                    "outcome": "correct",
                    "analyst_action": action,
                },
            )
            outcome_compact = compact_outcome(outcome["body"]) if isinstance(outcome["body"], dict) else {}
        loops.append(
            {
                "alert_id": alert_id,
                "analyze_status": analyze["status"],
                "analyze": analyze_compact,
                "outcome_status": outcome["status"] if outcome else None,
                "outcome": outcome_compact,
                "raw_analyze_body": analyze["body"],
                "raw_outcome_body": outcome["body"] if outcome else None,
            }
        )
    rb = await readback(client, decision_ids)
    output = {
        "graph": GRAPH_NAME,
        "base_url": BASE_URL,
        "alert_ids": ALERT_IDS,
        "seed": seed,
        "loops": loops,
        "decision_ids": decision_ids,
        "readback": rb,
    }
    out_path = Path(__file__).with_name("diag_e4_results.json")
    out_path.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

