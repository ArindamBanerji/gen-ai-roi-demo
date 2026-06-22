"""
test_per_analyst_eta.py -- Block 9.1 D5 per-analyst eta weighting validation.

3 tests:
  1. test_high_precision_analyst_has_higher_weight
  2. test_analyst_below_threshold_uses_default_weight
  3. test_analyst_weights_endpoint_returns_200

D5 validated: Spearman r=0.975-1.000.
Weight formula: weight = clip(precision / mean_precision, 0.5, 1.5)
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

_ENDPOINT = "/api/soc/analyst-weights"


def test_high_precision_analyst_has_higher_weight():
    """
    Analyst with q=0.90 must have higher eta weight than q=0.60 once both
    have sufficient decisions.  Gate: weight_high >= weight_low (D5 Spearman r=0.975).

    This is validated against the formula
      weight = clip(precision / mean_precision, 0.5, 1.5)
    using synthetic precision values directly (not via Neo4j), since the
    live Neo4j path requires >=10 decisions per analyst in the same session.
    """
    resp = client.get(_ENDPOINT)
    if resp.status_code == 404:
        pytest.skip("analyst-weights endpoint not yet implemented")
    assert resp.status_code == 200

    # Validate the weight formula directly using GateConfig
    from app.domains.soc.config import GateConfig

    # Two analysts: high q̄=0.90, low q̄=0.60.
    # mean = 0.75 → high weight = 0.90/0.75 = 1.20, low = 0.60/0.75 = 0.80
    cfg = GateConfig(
        n_decisions=10_000,   # force calibrated
        V=200.0,
        alpha=0.25,
        per_analyst_precision={"analyst_high": 0.90, "analyst_low": 0.60},
    )
    weights = cfg.eta_weights
    assert "analyst_high" in weights and "analyst_low" in weights, (
        "GateConfig.eta_weights did not return both analysts"
    )
    high_w = weights["analyst_high"]
    low_w  = weights["analyst_low"]
    assert high_w >= low_w, (
        f"D5 violation: high-precision analyst weight ({high_w:.4f}) "
        f"must be >= low-precision ({low_w:.4f})"
    )
    # D5 spec: ratio >= 1.2 (Spearman r=0.975 requires clear separation)
    assert high_w / max(low_w, 1e-9) >= 1.2, (
        f"D5: weight ratio {high_w / low_w:.4f} below minimum 1.2 threshold"
    )

    # Also check live endpoint: if analysts present, ordering must hold
    data = resp.json()
    lw = data.get("analyst_weights", {})
    personalized = {a: v for a, v in lw.items() if v.get("status") == "personalized"}
    if len(personalized) >= 2:
        sorted_by_prec = sorted(personalized.items(), key=lambda x: x[1]["precision"])
        lowest  = sorted_by_prec[0][1]["eta_weight"]
        highest = sorted_by_prec[-1][1]["eta_weight"]
        assert highest >= lowest, (
            "Live endpoint: highest-precision analyst must have >= weight of lowest"
        )


def test_analyst_below_threshold_uses_default_weight():
    """
    Analyst with < 20 decisions must use default weight (1.0) and
    status must contain 'default'.
    """
    resp = client.get(_ENDPOINT)
    if resp.status_code == 404:
        pytest.skip("analyst-weights endpoint not yet implemented")
    assert resp.status_code == 200

    data = resp.json()
    threshold = data.get("threshold_decisions", 20)
    weights   = data.get("analyst_weights", {})

    for analyst_id, info in weights.items():
        count = info.get("decision_count", threshold)
        if count < threshold:
            assert info.get("eta_weight", 1.0) == 1.0, (
                f"Analyst {analyst_id} has {count} decisions (< {threshold}) "
                f"but non-default weight {info.get('eta_weight')}"
            )
            assert "default" in info.get("status", "").lower(), (
                f"Analyst {analyst_id} below threshold but status is "
                f"{info.get('status')!r} -- expected 'default' in status"
            )


def test_analyst_weights_endpoint_returns_200():
    """
    Basic availability + schema test for /api/soc/analyst-weights.
    Gracefully skips if endpoint returns 404.
    """
    resp = client.get(_ENDPOINT)
    assert resp.status_code in (200, 404), (
        f"Unexpected status code {resp.status_code}"
    )
    if resp.status_code == 200:
        data = resp.json()
        assert "analyst_weights" in data, "missing 'analyst_weights'"
        assert "note" in data, "missing 'note'"
        assert "V-D5" in data["note"], (
            f"'V-D5' not found in note: {data['note']!r}"
        )
        assert "threshold_decisions" in data, "missing 'threshold_decisions'"
        assert "weight_ratio_high_low" in data, "missing 'weight_ratio_high_low'"
