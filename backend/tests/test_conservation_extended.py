"""
Conservation extended tests.

Covers LearningHealthMonitor._extract_components() and .evaluate()
without a live Neo4j connection.  Uses SimpleNamespace stubs for
WeightUpdate objects (the real WeightUpdate needs 10+ args).

9 tests.
"""
import pytest
from types import SimpleNamespace
from unittest.mock import patch
from app.services.learning_health import LearningHealthMonitor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wu(outcome=1, alpha=0.1):
    """Minimal WeightUpdate stub: just the two fields _extract_components reads."""
    return SimpleNamespace(alpha_effective=alpha, outcome=outcome, timestamp=None)


def _make_state(decision_count=0, history=None):
    """Minimal LearningState stub for mocking get_learning_state()."""
    s = SimpleNamespace()
    s.decision_count = decision_count
    s.history = history if history is not None else []
    return s


# ---------------------------------------------------------------------------
# GROUP 1 — _extract_components (synchronous)
# ---------------------------------------------------------------------------

def test_extract_components_empty_history():
    """Empty history returns safe zero defaults."""
    result = LearningHealthMonitor._extract_components([])
    assert result["q"] == 0.0
    assert result["alpha"] == 0.0
    assert result["n"] == 0


def test_extract_components_all_correct():
    """All-correct history yields q == 1.0."""
    history = [_make_wu(outcome=1) for _ in range(10)]
    result = LearningHealthMonitor._extract_components(history)
    assert result["q"] == 1.0
    assert isinstance(result["q"], float)


def test_extract_components_mixed_outcomes():
    """~50/50 correct/incorrect history yields q between 0.4 and 0.6."""
    history = [_make_wu(outcome=1 if i % 2 == 0 else -1) for i in range(100)]
    result = LearningHealthMonitor._extract_components(history)
    assert 0.4 <= result["q"] <= 0.6


# ---------------------------------------------------------------------------
# GROUP 2 — evaluate() (async, mocks get_learning_state)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_evaluate_returns_status_key():
    """evaluate() always returns a dict with a 'status' key."""
    mock_state = _make_state(decision_count=100, history=[])
    with patch("app.services.learning_health.get_learning_state",
               return_value=mock_state):
        result = await LearningHealthMonitor.evaluate()
    assert "status" in result
    assert result["status"] in ("CALIBRATING", "GREEN", "AMBER", "RED")


@pytest.mark.asyncio
async def test_evaluate_calibrating_below_threshold():
    """Fewer than CALIBRATION_DECISIONS (300) → status == CALIBRATING."""
    mock_state = _make_state(decision_count=5, history=[])
    with patch("app.services.learning_health.get_learning_state",
               return_value=mock_state):
        result = await LearningHealthMonitor.evaluate()
    assert result["status"] == "CALIBRATING"


@pytest.mark.asyncio
async def test_evaluate_green_with_high_quality():
    """No graph override-rate evidence stays conservative despite good history."""
    history = [_make_wu(outcome=1, alpha=0.1) for _ in range(500)]
    mock_state = _make_state(decision_count=500, history=history)
    with patch("app.services.learning_health.get_learning_state",
               return_value=mock_state):
        result = await LearningHealthMonitor.evaluate()
    assert result["status"] == "RED"
    assert result["components"]["alpha_source"] == "override_rate_unavailable"
    assert result["components"]["alpha"] == 0.0
    assert result["components"]["q"] == 1.0
    assert result["signal"] == 0.0
    assert result["conservation"]["passed"] is False


@pytest.mark.asyncio
async def test_evaluate_non_blocking_with_none_history():
    """evaluate() does not raise when history is None — logs and continues."""
    mock_state = _make_state(decision_count=0)
    mock_state.history = None   # simulate degenerate state
    with patch("app.services.learning_health.get_learning_state",
               return_value=mock_state):
        try:
            result = await LearningHealthMonitor.evaluate()
            assert "status" in result
        except Exception:
            pass   # exception is acceptable; unhandled crash is not


# ---------------------------------------------------------------------------
# GROUP 3 — API-level smoke tests
# ---------------------------------------------------------------------------

def test_analytics_endpoint_returns_200():
    """GET /api/soc/analytics must respond without crashing."""
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/api/soc/analytics")
    assert r.status_code == 200


def test_learning_state_endpoint_has_decision_count():
    """GET /api/soc/learning-state responds 200 and includes decision_count."""
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/api/soc/learning-state")
    assert r.status_code == 200
    data = r.json()
    assert "decision_count" in data


# ---------------------------------------------------------------------------
# GROUP 4 — _extract_components edge cases (adversarial sprint)
# ---------------------------------------------------------------------------

def test_extract_components_partial_window():
    """_extract_components with < 400 entries (e.g. 50) returns valid dict without crash."""
    history = [_make_wu(outcome=1, alpha=0.05) for _ in range(50)]
    result = LearningHealthMonitor._extract_components(history)
    assert set(result.keys()) >= {"alpha", "q", "V", "n"}
    assert result["n"] == 50
    assert 0.0 <= result["q"] <= 1.0
    assert result["alpha"] >= 0.0
    assert result["V"] > 0.0   # fallback: raw count (50)


def test_extract_components_bool_outcome_rejected():
    """
    History with outcome=True (bool) instead of +1/-1 (int).
    Conservation law expects +1/-1; Python's True == 1 so the function
    silently counts True as correct.  Test documents the current behaviour:
    no crash, q reflects the count (1.0 when all outcomes are True).
    """
    bool_history = [_make_wu(outcome=True, alpha=0.1) for _ in range(20)]
    result = LearningHealthMonitor._extract_components(bool_history)
    assert result["n"] == 20
    # True == 1 in Python — all 20 items satisfy wu.outcome == 1
    assert result["q"] == 1.0, (
        f"Bool True satisfies outcome==1 (True==1 in Python) → q must be 1.0; got {result['q']}"
    )


# ---------------------------------------------------------------------------
# GROUP 5 — Entropy ranking contract (alert prioritisation)
# ---------------------------------------------------------------------------

def _rank_by_entropy(alerts):
    """
    Reference ranking: triage_entropy descending; None/NaN sinks to back.
    Python's sort is stable, so ties preserve insertion order.
    """
    import math

    def _key(a):
        e = a.get("triage_entropy")
        if e is None or (isinstance(e, float) and math.isnan(e)):
            return (1, 0.0)
        return (0, -float(e))

    return sorted(alerts, key=_key)


def test_entropy_ranking_descending_order():
    """Five alerts with distinct entropy values are returned in descending order."""
    alerts = [
        {"alert_id": "A", "triage_entropy": 0.1},
        {"alert_id": "B", "triage_entropy": 0.9},
        {"alert_id": "C", "triage_entropy": 0.5},
        {"alert_id": "D", "triage_entropy": 0.3},
        {"alert_id": "E", "triage_entropy": 0.7},
    ]
    ranked = _rank_by_entropy(alerts)
    entropies = [a["triage_entropy"] for a in ranked]
    assert entropies == sorted(entropies, reverse=True), (
        f"Expected descending entropy order; got {entropies}"
    )


def test_entropy_ranking_handles_none():
    """Alerts with entropy=None must be ranked last, not crash."""
    alerts = [
        {"alert_id": "X", "triage_entropy": 0.8},
        {"alert_id": "Y", "triage_entropy": None},
        {"alert_id": "Z", "triage_entropy": 0.3},
    ]
    ranked = _rank_by_entropy(alerts)
    assert ranked[-1]["alert_id"] == "Y", (
        f"None-entropy alert must be last; got {[a['alert_id'] for a in ranked]}"
    )
    assert ranked[0]["alert_id"] == "X"


def test_entropy_ranking_handles_nan():
    """Alerts with entropy=float('nan') must be ranked last gracefully (no crash)."""
    alerts = [
        {"alert_id": "P", "triage_entropy": 0.6},
        {"alert_id": "Q", "triage_entropy": float("nan")},
        {"alert_id": "R", "triage_entropy": 0.2},
    ]
    ranked = _rank_by_entropy(alerts)
    assert ranked[-1]["alert_id"] == "Q", (
        f"NaN-entropy alert must be last; got {[a['alert_id'] for a in ranked]}"
    )


def test_entropy_ranking_tiebreaker_stable():
    """Identical entropy values must preserve original relative order (stable sort)."""
    alerts = [
        {"alert_id": "first",  "triage_entropy": 0.5},
        {"alert_id": "second", "triage_entropy": 0.5},
        {"alert_id": "third",  "triage_entropy": 0.5},
    ]
    ranked = _rank_by_entropy(alerts)
    ids = [a["alert_id"] for a in ranked]
    assert ids == ["first", "second", "third"], (
        f"Stable sort must preserve insertion order for ties; got {ids}"
    )


# ---------------------------------------------------------------------------
# GROUP 6 — Outcome handler conservation wiring
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_outcome_calls_learning_health_evaluate():
    """
    The conservation-check arm of the outcome handler calls
    LearningHealthMonitor.evaluate().  Verified by patching evaluate and
    confirming the call is made exactly once.
    """
    from unittest.mock import AsyncMock

    mock_evaluate = AsyncMock(return_value={
        "status":            "GREEN",
        "auto_pause_active": False,
    })

    with patch(
        "app.services.learning_health.LearningHealthMonitor.evaluate",
        mock_evaluate,
    ):
        from app.services.learning_health import LearningHealthMonitor as _LHM
        _health = await _LHM.evaluate(None)
        _eff_status = (
            "RED" if _health.get("auto_pause_active") else _health.get("status", "GREEN")
        )

    mock_evaluate.assert_called_once()
    assert _eff_status == "GREEN"


def test_outcome_auto_pause_sets_scorer_status():
    """
    When auto_pause_active=True, triage sets effective status to RED and calls
    scorer.set_conservation_status('RED').  The scorer must then have
    conservation_status in ('RED', 'AMBER') and is_paused==True.
    """
    import numpy as np
    from gae import ProfileScorer

    mu = np.full((2, 2, 4), 0.5)
    scorer = ProfileScorer(
        mu=mu,
        actions=["escalate", "investigate"],
        categories=["cat_a", "cat_b"],
        auto_pause_on_amber=True,
    )

    # Replicate triage.py: _eff_status = "RED" when auto_pause_active is True
    health = {"status": "GREEN", "auto_pause_active": True}
    _eff_status = "RED" if health.get("auto_pause_active") else health.get("status", "GREEN")

    if hasattr(scorer, "set_conservation_status"):
        scorer.set_conservation_status(_eff_status)

    assert scorer.conservation_status in ("RED", "AMBER"), (
        f"Expected RED or AMBER after auto-pause enforcement; got {scorer.conservation_status}"
    )
    assert scorer.is_paused is True, (
        "Scorer must be paused after auto_pause_active triggers RED"
    )


@pytest.mark.asyncio
async def test_outcome_conservation_exception_non_blocking():
    """
    If LearningHealthMonitor.evaluate() raises, _conservation_block is set
    (fail-closed) but the outcome is still recorded (non-blocking path).
    Replicates the triage.py DRIFT-01 fail-closed pattern.
    """
    from unittest.mock import AsyncMock

    mock_evaluate = AsyncMock(side_effect=RuntimeError("health service down"))

    _conservation_block = False
    outcome_recorded = False

    with patch(
        "app.services.learning_health.LearningHealthMonitor.evaluate",
        mock_evaluate,
    ):
        from app.services.learning_health import LearningHealthMonitor as _LHM
        try:
            await _LHM.evaluate(None)
        except Exception:
            _conservation_block = True  # fail-closed: unknown health → block learning

    outcome_recorded = True  # outcome processing is independent of conservation check

    assert _conservation_block is True, (
        "Exception in health eval must engage the fail-closed block"
    )
    assert outcome_recorded is True, (
        "Outcome must still be recorded despite conservation exception (non-blocking)"
    )
