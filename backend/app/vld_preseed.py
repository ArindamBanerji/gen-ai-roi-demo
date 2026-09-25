"""Seed VLD SOC showcase alerts for investigation demo beats."""
from __future__ import annotations

from typing import Any

from app.evidence_provider import register_showcase_evidence

SHOWCASE_ALERTS: list[dict[str, Any]] = [
    {
        "alert_id": "VLD-SOC-1",
        "title": "Suspicious lateral movement from workstation-47",
        "category": "credential_access",
        "surface_factors": [0.0005, 0.7288, 0.693, 0.1188, 0.563, 0.2283],
        "surface_action": "monitor",
        "expected_action": "escalate",
        "evidence": {
            0: {"value": 0.92, "confidence": 0.92, "source": "identity_graph"},
        },
        "nodes": [
            ("Alert", "VLD-SOC-1", {"alert_id": "VLD-SOC-1", "category": "credential_access", "origin": "vld_showcase", "severity": 0.6, "status": "open"}),
            ("User", "attacker_id_7", {"user_id": "attacker_id_7", "name": "attacker_id_7", "origin": "vld_showcase", "department": "unknown", "risk_level": "high"}),
            ("Campaign", "APT-29-variant", {"campaign_id": "APT-29-variant", "name": "APT-29 variant", "origin": "vld_showcase", "severity": 0.92, "confidence": 0.92, "alert_count": 3}),
        ],
        "edges": [
            ("Alert", "VLD-SOC-1", "INVOLVES", "User", "attacker_id_7"),
            ("Alert", "VLD-SOC-1", "MEMBER_OF", "Campaign", "APT-29-variant"),
        ],
    },
    {
        "alert_id": "VLD-SOC-2",
        "title": "Anomalous DNS queries from server-12",
        "category": "malware_execution",
        "surface_factors": [0.2939, 1.0, 0.2585, 0.0832, 0.6491, 0.2751],
        "surface_action": "monitor",
        "expected_action": "escalate",
        "evidence": {
            0: {"value": 0.92, "confidence": 0.92, "source": "identity_graph"},
            3: {"value": 0.90, "confidence": 0.85, "source": "historical_db"},
        },
        "nodes": [
            ("Alert", "VLD-SOC-2", {"alert_id": "VLD-SOC-2", "category": "malware_execution", "origin": "vld_showcase", "severity": 0.5, "status": "open", "similar_alerts_30d": 14, "narrative": "No threat-intelligence hit; identity investigation links the activity to a high-risk privileged identity."}),
            ("Asset", "server-12", {"asset_id": "server-12", "hostname": "server-12", "origin": "vld_showcase", "criticality": 0.7, "asset_type": "server"}),
            ("User", "privileged_identity_server_12", {"user_id": "privileged_identity_server_12", "name": "privileged_identity_server_12", "origin": "vld_showcase", "risk_level": "high", "privileged": True}),
            ("Campaign", "high-risk-identity-cluster", {"campaign_id": "high-risk-identity-cluster", "name": "High-risk privileged identity cluster", "origin": "vld_showcase", "severity": 0.92, "confidence": 0.92}),
        ],
        "edges": [
            ("Alert", "VLD-SOC-2", "DETECTED_ON", "Asset", "server-12"),
            ("Alert", "VLD-SOC-2", "INVOLVES", "User", "privileged_identity_server_12"),
            ("Alert", "VLD-SOC-2", "MEMBER_OF", "Campaign", "high-risk-identity-cluster"),
        ],
    },
    {
        "alert_id": "VLD-SOC-S1",
        "title": "Known scanner probe from blocklisted IP",
        "category": "malware_execution",
        "surface_factors": [0.75, 0.8, 0.9, 0.55, 0.6, 0.2],
        "surface_action": "escalate",
        "expected_action": "escalate",
        "budget": 0,
        "evidence": {},
        "nodes": [
            ("Alert", "VLD-SOC-S1", {"alert_id": "VLD-SOC-S1", "category": "malware_execution", "origin": "vld_showcase", "severity": 0.9, "status": "open"}),
            ("ThreatIndicator", "blocklisted-ip", {"indicator": "blocklisted-ip", "indicator_type": "ip", "origin": "vld_showcase", "source": "threat_intel", "severity": 0.9}),
        ],
        "edges": [
            ("Alert", "VLD-SOC-S1", "HAS_INDICATOR", "ThreatIndicator", "blocklisted-ip"),
        ],
    },
]


def seed_vld_showcase(graph_client: Any) -> dict[str, Any]:
    """Register and optionally persist VLD showcase graph facts.

    The function is idempotent.  It always registers process-local evidence for
    the synchronous VLD EvidenceProvider.  If the supplied graph client exposes a
    simple ``vld_evidence`` mapping, it is populated too.  AGE persistence is
    best-effort and skipped for async clients because startup handles real graph
    readiness separately.
    """
    seeded_alerts: list[str] = []
    node_count = 0
    edge_count = 0

    if graph_client is not None and not hasattr(graph_client, "vld_evidence"):
        try:
            graph_client.vld_evidence = {}
        except Exception:
            pass

    for alert in SHOWCASE_ALERTS:
        alert_id = str(alert["alert_id"])
        evidence = {int(k): dict(v) for k, v in alert.get("evidence", {}).items()}
        register_showcase_evidence(alert_id, evidence)
        if graph_client is not None and isinstance(getattr(graph_client, "vld_evidence", None), dict):
            graph_client.vld_evidence[alert_id] = evidence
        seeded_alerts.append(alert_id)
        node_count += len(alert.get("nodes", []))
        edge_count += len(alert.get("edges", []))

    return {
        "alerts": seeded_alerts,
        "alert_count": len(seeded_alerts),
        "nodes": node_count,
        "edges": edge_count,
        "status": "registered",
    }
