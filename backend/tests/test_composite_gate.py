"""
Tests for Phase 5: CompositeDiscriminant, DecisionHistoryService, and endpoints.

Coverage:
  test_composite_evaluate_low_confidence    — confidence < 0.70 → False
  test_composite_evaluate_low_cat_count     — cat_count < 50 → False (maturity gate)
  test_composite_evaluate_all_pass          — all gates pass → True, reason_codes=["all gates passed"]
  test_composite_suppress_safety            — suppress action, confidence=0.80 → False
  test_composite_features_computed          — all 13 features present
  test_auto_approve_stats_endpoint          — GET /api/soc/auto-approve-stats structure
  test_analyze_includes_composite_gate      — POST /api/alert/analyze includes composite_gate
  test_decision_history_empty_category      — empty category → cat_count=0, rolling_accuracy=0.5
"""

import asyncio
import dataclasses
import numpy as np
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.domains.soc.config import SOCDomainConfig
from app.services.composite_gate import CompositeDiscriminant
from app.services.decision_history import DecisionHistoryService


# ---------------------------------------------------------------------------
# Shared scorer + fake ScoringResult
# ---------------------------------------------------------------------------

def _scorer():
    return SOCDomainConfig().build_profile_scorer()


def _make_score_result(action_index=0, confidence=0.85, n_actions=5):
    """Build a minimal ScoringResult-like object."""
    probs = np.zeros(n_actions)
    probs[action_index] = confidence
    # Distribute remainder across other actions
    remainder = (1.0 - confidence) / max(n_actions - 1, 1)
    for i in range(n_actions):
        if i != action_index:
            probs[i] = remainder

    distances = np.array([0.10, 0.40, 0.55, 0.70, 0.30])[:n_actions]

    @dataclasses.dataclass
    class FakeScoringResult:
        action_index: int
        action_name: str
        confidence: float
        probabilities: np.ndarray
        distances: np.ndarray

    from app.domains.soc.config import SOC_ACTIONS
    return FakeScoringResult(
        action_index=action_index,
        action_name=SOC_ACTIONS[action_index] if action_index < len(SOC_ACTIONS) else "unknown",
        confidence=float(probs[action_index]),
        probabilities=probs,
        distances=distances,
    )


def _cat_stats_neo4j(cat_count: int, correct: int = 0, verified: int = 0):
    """Return a FakeNeo4j that answers DecisionHistoryService queries."""
    async def run_query(query, params=None):
        if "d.category = $cat" in query:
            return [{"cat_count": cat_count, "correct_count": correct, "verified_count": verified}]
        return []

    class FakeNeo4j:
        pass
    FakeNeo4j.run_query = staticmethod(run_query)
    return FakeNeo4j()


# ---------------------------------------------------------------------------
# Test 1: low confidence → auto_approve = False
# ---------------------------------------------------------------------------

def test_composite_evaluate_low_confidence():
    """confidence < CONFIDENCE_THRESHOLD (0.70) → auto_approve=False."""
    f = [0.5] * 6
    result_sr = _make_score_result(action_index=0, confidence=0.50)
    neo4j = _cat_stats_neo4j(cat_count=100, correct=90, verified=100)

    result = asyncio.run(
        CompositeDiscriminant.evaluate(result_sr, "credential_access", f, 0.0, neo4j)
    )

    assert result["auto_approve"] is False
    assert any("confidence" in r for r in result["reason_codes"]), (
        f"Expected confidence mention in reason_codes: {result['reason_codes']}"
    )


# ---------------------------------------------------------------------------
# Test 2: low cat_count → False (maturity gate)
# ---------------------------------------------------------------------------

def test_composite_evaluate_low_cat_count():
    """cat_count < MIN_CAT_COUNT (50) → auto_approve=False even with high confidence."""
    f = [0.8, 0.9, 0.1, 0.7, 0.8, 0.2]
    result_sr = _make_score_result(action_index=0, confidence=0.90)
    neo4j = _cat_stats_neo4j(cat_count=10)

    result = asyncio.run(
        CompositeDiscriminant.evaluate(result_sr, "credential_access", f, 0.0, neo4j)
    )

    assert result["auto_approve"] is False
    assert any("maturity gate" in r for r in result["reason_codes"]), (
        f"Expected 'maturity gate' in reason_codes: {result['reason_codes']}"
    )


# ---------------------------------------------------------------------------
# Test 3: all gates pass → auto_approve=True
# ---------------------------------------------------------------------------

def test_composite_evaluate_all_pass():
    """With confidence=0.85, large margin, cat_count=100 → auto_approve=True."""
    # action_index=0 (escalate), high confidence, clear margin from other actions
    probs = np.array([0.85, 0.10, 0.02, 0.02, 0.01])
    distances = np.array([0.10, 0.50, 0.60, 0.65, 0.70])

    @dataclasses.dataclass
    class SR:
        action_index: int = 0
        action_name: str = "escalate"
        confidence: float = 0.85
        probabilities: np.ndarray = dataclasses.field(default_factory=lambda: probs)
        distances: np.ndarray = dataclasses.field(default_factory=lambda: distances)

    neo4j = _cat_stats_neo4j(cat_count=100, correct=92, verified=100)

    result = asyncio.run(
        CompositeDiscriminant.evaluate(SR(), "credential_access", [0.7, 0.8, 0.1, 0.6, 0.7, 0.2], 0.0, neo4j)
    )

    assert result["auto_approve"] is True, f"Expected True: {result['reason_codes']}"
    assert result["reason_codes"] == ["all gates passed"], result["reason_codes"]


# ---------------------------------------------------------------------------
# Test 4: suppress action + confidence < 0.95 → False
# ---------------------------------------------------------------------------

def test_composite_suppress_safety():
    """suppress action with confidence=0.80 → auto_approve=False (needs >= 0.95)."""
    from app.domains.soc.config import SOC_ACTIONS
    suppress_idx = SOC_ACTIONS.index("suppress")  # index 2

    probs = np.zeros(5)
    probs[suppress_idx] = 0.80
    remainder = 0.20 / 4
    for i in range(5):
        if i != suppress_idx:
            probs[i] = remainder
    distances = np.array([0.50, 0.45, 0.05, 0.40, 0.38])

    @dataclasses.dataclass
    class SR:
        action_index: int = suppress_idx
        action_name: str = "suppress"
        confidence: float = 0.80
        probabilities: np.ndarray = dataclasses.field(default_factory=lambda: probs)
        distances: np.ndarray = dataclasses.field(default_factory=lambda: distances)

    # cat_count=100 so maturity gate passes — only suppress safety should block it
    neo4j = _cat_stats_neo4j(cat_count=100, correct=90, verified=100)

    result = asyncio.run(
        CompositeDiscriminant.evaluate(SR(), "credential_access", [0.5]*6, 0.0, neo4j)
    )

    assert result["auto_approve"] is False
    assert any("suppress" in r for r in result["reason_codes"]), (
        f"Expected suppress safety mention: {result['reason_codes']}"
    )


# ---------------------------------------------------------------------------
# Test 5: all 13 features present
# ---------------------------------------------------------------------------

def test_composite_features_computed():
    """All 13 feature keys must be present in the result."""
    EXPECTED_FEATURES = {
        "confidence", "margin", "entropy", "top3_mass", "prob_std",
        "dist_ratio", "dist_gap", "factor_extremity", "factor_norm",
        "factor_center_dist", "cat_count", "rolling_accuracy", "decision_position",
    }
    result_sr = _make_score_result(action_index=1, confidence=0.60)
    neo4j = _cat_stats_neo4j(cat_count=20)

    result = asyncio.run(
        CompositeDiscriminant.evaluate(result_sr, "lateral_movement", [0.5]*6, 0.3, neo4j)
    )

    missing = EXPECTED_FEATURES - set(result["features"].keys())
    assert not missing, f"Missing features: {missing}"
    assert len(result["features"]) == 13, (
        f"Expected 13 features, got {len(result['features'])}: {list(result['features'].keys())}"
    )


# ---------------------------------------------------------------------------
# Test 6: GET /api/soc/auto-approve-stats structure
# ---------------------------------------------------------------------------

def test_auto_approve_stats_endpoint():
    """GET /api/soc/auto-approve-stats returns valid structure."""
    from app.main import app

    async def fake_run_query(query, params=None):
        if "d.auto_approved" in query:
            return [
                {"category": "credential_access", "total": 30, "approved": 5},
                {"category": "lateral_movement",  "total": 20, "approved": 2},
            ]
        return []

    with patch("app.routers.soc.neo4j_client") as mock_neo4j:
        mock_neo4j.run_query = fake_run_query
        client = TestClient(app)
        resp = client.get("/api/soc/auto-approve-stats")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "total_decisions" in data,  f"Missing total_decisions: {data}"
    assert "auto_approved"   in data,  f"Missing auto_approved: {data}"
    assert "coverage_pct"    in data,  f"Missing coverage_pct: {data}"
    assert "by_category"     in data,  f"Missing by_category: {data}"
    assert data["total_decisions"] == 50
    assert data["auto_approved"]   == 7
    assert abs(data["coverage_pct"] - 14.0) < 0.1


# ---------------------------------------------------------------------------
# Test 7: analyze response includes composite_gate
# ---------------------------------------------------------------------------

def test_analyze_includes_composite_gate():
    """POST /api/alert/analyze response includes composite_gate field."""
    from app.main import app

    _alert_data = {
        "id": "ALERT-7823", "alert_type": "anomalous_login",
        "severity": "medium", "source_ip": "1.2.3.4",
        "source_location": "Singapore", "timestamp": "2026-02-06T03:47:00Z",
        "description": "test", "asset_id": "LAPTOP-JSMITH",
        "user_id": "jsmith@company.com", "status": "pending",
        "mfa_completed": True, "device_fingerprint_match": True,
        "mitre_technique": "T1078", "mitre_tactic": "Initial Access",
    }

    async def fake_run_query(query, params=None):
        return []   # empty is fine; Decision write, graph data etc. all tolerate []

    mock_neo4j = MagicMock()
    mock_neo4j.get_alert            = AsyncMock(return_value=_alert_data)
    mock_neo4j.get_security_context = AsyncMock(return_value={
        "alert_type": "anomalous_login", "alert_id": "ALERT-7823",
    })
    mock_neo4j.run_query                = AsyncMock(side_effect=fake_run_query)
    mock_neo4j.get_sequence_count       = AsyncMock(return_value=0)
    mock_neo4j.get_cross_category_count = AsyncMock(return_value=0)

    scorer = _scorer()
    mock_ls = MagicMock()
    mock_ls.decision_count = 10
    with patch("app.routers.triage.neo4j_client", mock_neo4j), \
         patch("app.routers.triage.get_profile_scorer", new=lambda: scorer), \
         patch("app.routers.triage.get_learning_state", return_value=mock_ls):
        client = TestClient(app)
        resp = client.post("/api/alert/analyze", json={"alert_id": "ALERT-7823"})

    assert resp.status_code == 200, f"Status: {resp.status_code}, body: {resp.text[:500]}"
    data = resp.json()
    assert "composite_gate" in data, (
        f"'composite_gate' missing from analyze response. Keys: {list(data.keys())}"
    )
    cg = data["composite_gate"]
    assert "auto_approve"   in cg, f"Missing auto_approve: {cg}"
    assert "approval_score" in cg, f"Missing approval_score: {cg}"
    assert "reason_codes"   in cg, f"Missing reason_codes: {cg}"


# ---------------------------------------------------------------------------
# Test 8: decision history empty category
# ---------------------------------------------------------------------------

def test_decision_history_empty_category():
    """Query a category with no decisions → cat_count=0, rolling_accuracy=0.5."""
    async def run_query(query, params=None):
        return [{"cat_count": 0, "correct_count": 0, "verified_count": 0}]

    class FakeNeo4j:
        pass
    FakeNeo4j.run_query = staticmethod(run_query)

    result = asyncio.run(
        DecisionHistoryService.get_category_stats("cloud_infrastructure", FakeNeo4j())
    )

    assert result["cat_count"] == 0
    assert result["rolling_accuracy"] == 0.5, (
        f"Expected 0.5 uninformative prior, got {result['rolling_accuracy']}"
    )
    assert result["verified_count"] == 0
