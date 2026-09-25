from __future__ import annotations

from copilot_sdk.graph.memory_store import InMemoryGraphStore
import numpy as np
import pytest
from fastapi.testclient import TestClient

from copilot_sdk.scoring.investigation import EvidenceProvider, VLDInvestigator
from copilot_sdk.scoring.situation_classifier import SituationClassifier

from app.evidence_provider import SOCEvidenceProvider, SOC_VLD_FACTOR_NAMES, get_showcase_evidence
from app.vld_preseed import SHOWCASE_ALERTS, seed_vld_showcase


class TrackingProvider(SOCEvidenceProvider):
    def __init__(self, graph_client, alert_id):
        super().__init__(graph_client, alert_id)
        self.reads = []

    def read_evidence(self, decision_id, dimension, factor_name):
        self.reads.append(int(dimension))
        return super().read_evidence(decision_id, dimension, factor_name)


class FakeScorer:
    def __init__(self, mu):
        self.centroids = np.asarray(mu, dtype=float)
        self.sigma = np.full(self.centroids.shape[-1], 0.1, dtype=float)
        self.categories = ["credential_access", "malware_execution"]
        self.actions = ["escalate", "investigate", "suppress", "monitor"]
        self.tau = 0.1


def _soc1_geometry():
    return np.array([
        [0.92, 0.30, 0.50, 0.30, 0.40, 0.50],
        [0.45, 0.30, 0.50, 0.30, 0.40, 0.50],
        [0.20, 0.30, 0.50, 0.30, 0.40, 0.50],
        [0.60, 0.30, 0.50, 0.30, 0.40, 0.50],
    ], dtype=float)


def _soc2_geometry():
    return np.array([
        [0.50, 0.40, 0.60, 0.90, 0.50, 0.40],
        [0.50, 0.40, 0.95, 0.20, 0.50, 0.40],
        [0.50, 0.40, 0.30, 0.20, 0.50, 0.40],
        [0.50, 0.40, 0.60, 0.20, 0.50, 0.40],
    ], dtype=float)


def _actions_from_trace(trace):
    return trace.surface_action, trace.final_action


def test_evidence_provider_protocol():
    provider = SOCEvidenceProvider(InMemoryGraphStore(domain="soc"), "VLD-SOC-1")
    assert isinstance(provider, EvidenceProvider)


def test_evidence_identity_with_campaign():
    graph = InMemoryGraphStore(domain="soc")
    seed_vld_showcase(graph)
    evidence = SOCEvidenceProvider(graph, "VLD-SOC-1").read_evidence(
        "VLD-SOC-1", 0, "identity_confidence"
    )
    assert evidence is not None
    assert evidence["value"] > 0.8
    assert evidence["source"] == "identity_graph"


def test_evidence_identity_no_campaign():
    graph = InMemoryGraphStore(domain="soc")
    from app.evidence_provider import register_showcase_evidence
    register_showcase_evidence("plain-alert", {0: {"value": 0.35, "confidence": 0.7, "source": "identity_graph"}})
    evidence = SOCEvidenceProvider(graph, "plain-alert").read_evidence(
        "plain-alert", 0, "identity_confidence"
    )
    assert evidence is not None
    assert evidence["value"] < 0.5


def test_evidence_empty_branch():
    graph = InMemoryGraphStore(domain="soc")
    seed_vld_showcase(graph)
    evidence = SOCEvidenceProvider(graph, "VLD-SOC-2").read_evidence(
        "VLD-SOC-2", 2, "intel_corroboration"
    )
    assert evidence is None


def test_evidence_all_six_factors():
    provider = SOCEvidenceProvider(InMemoryGraphStore(domain="soc"), "missing")
    for idx, name in enumerate(SOC_VLD_FACTOR_NAMES):
        query = provider._query_for_factor(name)
        assert "MATCH" in query
        assert "Alert" in query
        assert idx in range(6)


def test_preseed_registers_three_alerts():
    graph = InMemoryGraphStore(domain="soc")
    result = seed_vld_showcase(graph)
    assert result["alert_count"] == 3
    assert {a["alert_id"] for a in SHOWCASE_ALERTS} == {"VLD-SOC-1", "VLD-SOC-2", "VLD-SOC-S1"}
    assert get_showcase_evidence("VLD-SOC-1")[0]["value"] == pytest.approx(0.92)


def test_preseed_idempotent():
    graph = InMemoryGraphStore(domain="soc")
    first = seed_vld_showcase(graph)
    second = seed_vld_showcase(graph)
    assert first == second
    assert sorted(graph.vld_evidence) == ["VLD-SOC-1", "VLD-SOC-2", "VLD-SOC-S1"]


def test_vld_soc1_scenario_flips_monitor_to_escalate():
    graph = InMemoryGraphStore(domain="soc")
    seed_vld_showcase(graph)
    investigator = VLDInvestigator(_soc1_geometry(), np.full(6, 0.1), SOC_VLD_FACTOR_NAMES)
    trace = investigator.investigate(
        "VLD-SOC-1",
        "credential_access",
        np.array([0.60, 0.30, 0.50, 0.30, 0.40, 0.50]),
        SOCEvidenceProvider(graph, "VLD-SOC-1"),
        budget=2,
        gated_sources={"identity_graph"},
    )
    assert _actions_from_trace(trace) == (3, 0)
    assert trace.steps[0].dimension == 0
    assert trace.steps[0].flipped is True
    assert trace.steps[0].evidence_value == pytest.approx(0.92)


def test_vld_soc2_empty_branch_then_recompute_flips():
    graph = InMemoryGraphStore(domain="soc")
    seed_vld_showcase(graph)
    provider = TrackingProvider(graph, "VLD-SOC-2")
    investigator = VLDInvestigator(_soc2_geometry(), np.array([0.20, 0.20, 0.05, 0.06, 0.20, 0.20]), SOC_VLD_FACTOR_NAMES)
    trace = investigator.investigate(
        "VLD-SOC-2",
        "malware_execution",
        np.array([0.50, 0.40, 0.60, 0.20, 0.50, 0.40]),
        provider,
        budget=3,
    )
    assert provider.reads[:2] == [2, 3]
    assert _actions_from_trace(trace) == (3, 0)
    evidence_step = next(step for step in trace.steps if step.status != "empty")
    assert evidence_step.dimension == 3
    assert evidence_step.flipped is True


def test_s1_no_investigation_budget_zero():
    investigator = VLDInvestigator(_soc1_geometry(), np.full(6, 0.1), SOC_VLD_FACTOR_NAMES)
    v = _soc1_geometry()[0].copy()
    _, probabilities = investigator.score(v)
    Q = investigator.compute_Q(v, probabilities)
    assessment = SituationClassifier().classify(v, _soc1_geometry(), np.full(6, 0.1), probabilities, Q)
    trace = investigator.investigate("VLD-SOC-S1", "malware_execution", v, SOCEvidenceProvider(InMemoryGraphStore(domain="soc"), "VLD-SOC-S1"), budget=assessment.recommended_budget)
    assert assessment.situation == "S1"
    assert assessment.recommended_budget == 0
    assert trace.steps == []


def test_router_mounted_health():
    from app.main import app

    client = TestClient(app)
    response = client.get("/api/investigation/health")
    assert response.status_code == 200
    assert response.json()["investigation_available"] is True


def test_router_investigate_alert(monkeypatch):
    from app.main import app
    from app.services import gae_state

    mu = np.stack([_soc1_geometry(), _soc1_geometry()])
    monkeypatch.setattr(gae_state, "get_profile_scorer", lambda: FakeScorer(mu))
    graph = InMemoryGraphStore(domain="soc")
    seed_vld_showcase(graph)

    client = TestClient(app)
    response = client.post(
        "/api/investigation/investigate",
        json={
            "decision_id": "VLD-SOC-1",
            "category": "credential_access",
            "factor_vector": [0.60, 0.30, 0.50, 0.30, 0.40, 0.50],
            "budget": 2,
            "use_K": False,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["action_changed"] is True
    assert payload["surface_action"] == 3
    assert payload["final_action"] == 0
    assert payload["steps"][0]["flipped"] is True
