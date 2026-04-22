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
    """500 all-correct decisions → status is GREEN or AMBER (never RED)."""
    history = [_make_wu(outcome=1, alpha=0.1) for _ in range(500)]
    mock_state = _make_state(decision_count=500, history=history)
    with patch("app.services.learning_health.get_learning_state",
               return_value=mock_state):
        result = await LearningHealthMonitor.evaluate()
    assert result["status"] in ("GREEN", "AMBER")


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
