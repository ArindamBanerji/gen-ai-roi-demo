"""
Block 9.3 -- D2 Category freeze tests.
Coupled to D3 spike detector -- freeze only activates during volume spikes.
No live AGE required.
"""
import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.services.learning_health import (
    compute_category_baseline,
    detect_frozen_categories,
)
from app.services.gae_state import (
    set_volume_spike,
    is_volume_spike_active,
    set_frozen_categories,
    get_frozen_categories,
    is_category_frozen,
    guarded_update,
)


def _run(coro):
    return asyncio.run(coro)


def _graph_with_baseline(category_rows):
    mock = AsyncMock()
    mock.run_query.return_value = category_rows
    return mock


# ---------------------------------------------------------------------------
# Test 1 — no freeze returned when spike is NOT active
# ---------------------------------------------------------------------------

def test_no_freeze_when_no_spike():
    """
    detect_frozen_categories() returns [] immediately when spike is inactive.
    D3 coupling: category freeze must NEVER fire without an active spike.
    """
    assert not is_volume_spike_active(), "Precondition: spike should be inactive"

    mock = _graph_with_baseline([])    # baseline irrelevant -- guard fires first
    today = {"lateral_movement": 100, "malware": 10}

    result = _run(detect_frozen_categories(mock, today))

    assert result == [], f"Expected no frozen categories without spike, got {result}"
    mock.run_query.assert_not_called()  # should not even query AGE


# ---------------------------------------------------------------------------
# Test 2 — over-represented category is frozen during spike
# ---------------------------------------------------------------------------

def test_overrepresented_category_frozen():
    """
    Baseline: lateral_movement = 15% of alerts.
    Spike day: lateral_movement = 90 / 100 = 90% -> 90% > 2 x 15% -> freeze.
    malware:   10 / 100 = 10% vs baseline 50% -> not over-represented -> no freeze.
    """
    baseline_rows = [
        {"category": "lateral_movement", "cnt": 15},
        {"category": "malware",          "cnt": 50},
        {"category": "phishing",         "cnt": 35},
    ]
    mock = _graph_with_baseline(baseline_rows)
    today = {"lateral_movement": 90, "malware": 10}   # total = 100

    try:
        set_volume_spike(True)
        frozen = _run(detect_frozen_categories(mock, today))
    finally:
        set_volume_spike(False)

    assert "lateral_movement" in frozen, (
        f"lateral_movement (90%) should be frozen vs baseline (15%); got {frozen}"
    )
    assert "malware" not in frozen, (
        f"malware (10%) should NOT be frozen vs baseline (50%); got {frozen}"
    )


# ---------------------------------------------------------------------------
# Test 3 — normal category NOT frozen even during spike
# ---------------------------------------------------------------------------

def test_normal_category_not_frozen():
    """
    All categories within 2x baseline share -> no freezes.
    Baseline: lateral_movement=20%, malware=30%, phishing=50%.
    Today:    lateral_movement=22%, malware=28%, phishing=50% -- all within 2x.
    """
    baseline_rows = [
        {"category": "lateral_movement", "cnt": 20},
        {"category": "malware",          "cnt": 30},
        {"category": "phishing",         "cnt": 50},
    ]
    mock = _graph_with_baseline(baseline_rows)
    today = {"lateral_movement": 22, "malware": 28, "phishing": 50}   # total=100

    try:
        set_volume_spike(True)
        frozen = _run(detect_frozen_categories(mock, today))
    finally:
        set_volume_spike(False)

    assert frozen == [], f"Expected no frozen categories, got {frozen}"


# ---------------------------------------------------------------------------
# Test 4 — frozen category skips guarded_update; unfrozen proceeds
# ---------------------------------------------------------------------------

def test_frozen_category_skips_update():
    """
    is_category_frozen("lateral_movement") = True -> guarded_update returns None.
    is_category_frozen("malware")          = False -> guarded_update calls scorer.
    """
    scorer = MagicMock()
    scorer.update.return_value = MagicMock()   # simulate CentroidUpdate
    f = np.zeros(6)

    try:
        set_frozen_categories(["lateral_movement"])

        # Frozen category — must skip
        result_frozen = guarded_update(
            scorer, f=f, category_index=0, action_index=0,
            correct=True, category_name="lateral_movement",
        )
        assert result_frozen is None, "Frozen category should return None"
        scorer.update.assert_not_called()

        # Unfrozen category — must proceed
        result_ok = guarded_update(
            scorer, f=f, category_index=1, action_index=0,
            correct=True, category_name="malware",
        )
        assert result_ok is not None, "Unfrozen category should call scorer.update"
        scorer.update.assert_called_once()

    finally:
        set_frozen_categories([])


# ---------------------------------------------------------------------------
# Test 5 — endpoint returns frozen list and baseline
# ---------------------------------------------------------------------------

def test_endpoint_returns_frozen_list():
    """GET /api/soc/frozen-categories returns required fields."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    baseline_data = {
        "lateral_movement":  0.15,
        "credential_access": 0.35,
        "malware":           0.50,
    }

    try:
        set_frozen_categories(["lateral_movement"])

        with patch(
            "app.services.learning_health.compute_category_baseline",
            new=AsyncMock(return_value=baseline_data),
        ):
            resp = client.get("/api/soc/frozen-categories")
    finally:
        set_frozen_categories([])

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()

    assert "spike_active"      in body
    assert "frozen_categories" in body
    assert "category_baseline" in body
    assert "freeze_threshold"  in body

    assert body["freeze_threshold"] == 2.0
    assert "lateral_movement" in body["frozen_categories"]
    assert body["category_baseline"] == baseline_data
