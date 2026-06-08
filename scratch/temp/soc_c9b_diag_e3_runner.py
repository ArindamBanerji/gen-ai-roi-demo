from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import importlib.util

from ci_platform.graph.age_client import AGEClient


BASE_URL = os.getenv("SOC_BACKEND_URL", "http://127.0.0.1:8001").rstrip("/")
ALERT_IDS = [f"DIAG-E3-CRED-{i:03d}" for i in range(1, 6)]
GRAPH_NAME = "soc_graph_diag"


def _load_seed_module():
    path = REPO_ROOT / "scripts" / "soc_c9b_seed_alerts.py"
    spec = importlib.util.spec_from_file_location("soc_c9b_seed_alerts_diag_e3", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def post_json(path: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=30) as response:
            text = response.read().decode("utf-8")
            body = json.loads(text) if text else {}
            body["_http_status"] = response.status
            return body
    except HTTPError as exc:
        text = exc.read().decode("utf-8")
        try:
            body = json.loads(text) if text else {}
        except json.JSONDecodeError:
            body = {"raw": text}
        body["_http_status"] = exc.code
        return body


def first_present(obj: dict, paths: list[tuple[str, ...]]):
    for path in paths:
        cur = obj
        ok = True
        for key in path:
            if not isinstance(cur, dict) or key not in cur:
                ok = False
                break
            cur = cur[key]
        if ok:
            return cur
    return None


async def seed_exact_ids() -> dict:
    seed = _load_seed_module()
    client = AGEClient()
    created = 0
    existing = 0
    seed_details = []
    for index, alert_id in enumerate(ALERT_IDS, start=1):
        spec = seed.build_alert_spec("DIAG-E3-CRED", 1)
        spec = seed.AlertSpec(
            alert_id=alert_id,
            user_id=f"DIAG-E3-CRED-USER-{index:03d}",
            asset_id=f"DIAG-E3-CRED-ASSET-{index:03d}",
            category=spec.category,
            alert_type=spec.alert_type,
            severity=spec.severity,
            timestamp_epoch=1_725_100_000_000 + index,
            source_location=f"c9b-e3-proof-zone-{index}",
            risk_score=spec.risk_score,
            criticality=spec.criticality,
            mfa_completed=spec.mfa_completed,
            device_fingerprint_match=spec.device_fingerprint_match,
        )
        alert_exists = await seed._node_exists(client, "Alert", "alert_id", spec.alert_id)
        if alert_exists:
            existing += 1
        else:
            await seed._create_node_if_missing(
                client,
                "User",
                "user_id",
                spec.user_id,
                {
                    "user_id": spec.user_id,
                    "id": spec.user_id,
                    "name": f"C9B Proof User {spec.user_id[-3:]}",
                    "origin": "c9b_seed",
                    "department": "SOC",
                    "risk_level": spec.severity,
                    "risk_score": spec.risk_score,
                    "c9b_proof": True,
                },
            )
            await seed._create_node_if_missing(
                client,
                "Asset",
                "asset_id",
                spec.asset_id,
                {
                    "asset_id": spec.asset_id,
                    "id": spec.asset_id,
                    "hostname": f"c9b-proof-{spec.asset_id[-3:]}",
                    "criticality": spec.criticality,
                    "origin": "c9b_seed",
                    "asset_type": "workload",
                    "business_unit": "security",
                    "c9b_proof": True,
                },
            )
            await client.run_query(
                "CREATE (a:Alert {"
                + seed._props(
                    {
                        "alert_id": spec.alert_id,
                        "id": spec.alert_id,
                        "category": spec.category,
                        "severity": spec.severity,
                        "alert_type": spec.alert_type,
                        "status": "pending",
                        "origin": "c9b_seed",
                        "source": "c9b_seed",
                        "c9b_proof": True,
                        "timestamp_epoch": spec.timestamp_epoch,
                        "source_location": spec.source_location,
                        "user_id": spec.user_id,
                        "asset_id": spec.asset_id,
                        "attack_pattern_id": "",
                        "mfa_completed": spec.mfa_completed,
                        "device_fingerprint_match": spec.device_fingerprint_match,
                        "vpn_provider": "c9b_seed",
                    }
                )
                + "})"
            )
            created += 1
        await seed._create_edge_if_missing(
            client,
            "Alert",
            "alert_id",
            spec.alert_id,
            "INVOLVES",
            "User",
            "user_id",
            spec.user_id,
        )
        await seed._create_edge_if_missing(
            client,
            "Alert",
            "alert_id",
            spec.alert_id,
            "DETECTED_ON",
            "Asset",
            "asset_id",
            spec.asset_id,
        )
        seed_details.append(
            {
                "alert_id": spec.alert_id,
                "category": spec.category,
                "alert_type": spec.alert_type,
                "severity": spec.severity,
                "risk_score": spec.risk_score,
                "criticality": spec.criticality,
                "mfa_completed": spec.mfa_completed,
                "device_fingerprint_match": spec.device_fingerprint_match,
                "user_id": spec.user_id,
                "asset_id": spec.asset_id,
            }
        )
    return {"created": created, "existing": existing, "graph_name": GRAPH_NAME, "alerts": seed_details}


async def readback(decision_ids: list[str]) -> dict:
    client = AGEClient()
    decision_list = "[" + ", ".join(repr(d) for d in decision_ids) + "]"
    queries = {
        "decisions_diag_e3": "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) WHERE d.domain = 'soc' AND a.alert_id STARTS WITH 'DIAG-E3-CRED' RETURN count(d) AS total",
        "non_referral_diag_e3": "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) WHERE d.domain = 'soc' AND a.alert_id STARTS WITH 'DIAG-E3-CRED' AND d.action <> 'refer_to_analyst' RETURN count(d) AS total",
        "outcomes_diag_e3": "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) WHERE d.domain = 'soc' AND a.alert_id STARTS WITH 'DIAG-E3-CRED' AND (d.correct = true OR d.outcome = 'correct') RETURN count(d) AS total",
        "l5_centroid_total": "MATCH (c:L5Centroid) WHERE c.domain = 'soc' RETURN count(c) AS total",
        "l5_centroid_diag_e3_caused": f"MATCH (c:L5Centroid) WHERE c.domain = 'soc' AND c.caused_by_decision_id IN {decision_list} RETURN count(c) AS total",
        "shaped_by_total": "MATCH (c:L5Centroid)-[r:SHAPED_BY]->(d:Decision) WHERE c.domain = 'soc' RETURN count(r) AS total",
        "shaped_by_diag_e3": "MATCH (c:L5Centroid)-[r:SHAPED_BY]->(d:Decision)-[:DECIDED_ON]->(a:Alert) WHERE c.domain = 'soc' AND a.alert_id STARTS WITH 'DIAG-E3-CRED' RETURN count(r) AS total",
        "l5_dk_weight": "MATCH (w:L5DKWeight) WHERE w.domain = 'soc' RETURN count(w) AS total",
        "l5_conservation": "MATCH (cs:L5ConservationState) WHERE cs.domain = 'soc' RETURN count(cs) AS total",
        "decision_sample": "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) WHERE d.domain = 'soc' AND a.alert_id STARTS WITH 'DIAG-E3-CRED' RETURN a.alert_id AS alert_id, d.id AS decision_id, d.action AS action, d.outcome AS outcome, d.correct AS correct ORDER BY a.alert_id",
    }
    out = {}
    for name, query in queries.items():
        out[name] = await client.run_query(query)
    return out


async def main() -> dict:
    seed_summary = await seed_exact_ids()
    loops = []
    posted_outcomes = 0
    decision_ids = []
    for alert_id in ALERT_IDS:
        analyze = post_json("/api/alert/analyze", {"alert_id": alert_id})
        action = first_present(analyze, [("recommendation", "action"), ("action",), ("recommended_action",)])
        category = first_present(analyze, [("gae_scoring", "category"), ("category",), ("alert_category",)])
        confidence = first_present(analyze, [("recommendation", "confidence"), ("confidence",), ("gae_scoring", "confidence")])
        decision_id = first_present(analyze, [("decision_id",), ("recommendation", "decision_id"), ("gae_scoring", "decision_id")])
        factor_vector = first_present(analyze, [("factor_vector",), ("gae_scoring", "factor_vector")])
        outcome = None
        if decision_id:
            decision_ids.append(decision_id)
        if analyze.get("_http_status") == 200 and action and action != "refer_to_analyst" and decision_id:
            outcome = post_json(
                "/api/alert/outcome",
                {
                    "alert_id": alert_id,
                    "decision_id": decision_id,
                    "outcome": "correct",
                    "analyst_action": action,
                },
            )
            if outcome.get("_http_status") == 200:
                posted_outcomes += 1
        loops.append(
            {
                "alert_id": alert_id,
                "analyze_status": analyze.get("_http_status"),
                "category": category,
                "action": action,
                "confidence": confidence,
                "decision_id": decision_id,
                "factor_vector": factor_vector,
                "factor_vector_len": len(factor_vector) if isinstance(factor_vector, list) else None,
                "routing_zone": first_present(analyze, [("recommendation", "routing_zone"), ("routing_zone",)]),
                "analyze_response": analyze,
                "outcome_status": outcome.get("_http_status") if outcome else None,
                "outcome_response": outcome,
                "l5_centroid_persisted": first_present(outcome or {}, [("l5_centroid_persisted",), ("l5_persistence", "l5_centroid_persisted")]),
                "l5_persistence_skipped_reason": first_present(outcome or {}, [("l5_persistence_skipped_reason",), ("l5_persistence", "skipped_reason")]),
            }
        )
    rb = await readback(decision_ids)
    return {
        "seed": seed_summary,
        "loops": loops,
        "posted_outcomes": posted_outcomes,
        "decision_ids": decision_ids,
        "readback": rb,
    }


if __name__ == "__main__":
    print(json.dumps(asyncio.run(main()), indent=2, sort_keys=True))
