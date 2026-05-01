"""
Tests for GET /api/soc/centroid-heatmap (Block 2.4).

Verifies the heat map structure: categories, actions, factors,
kernel_weights, heatmap, noise_fingerprint, interpretation.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.services.gae_state import init_learning_state

# Ensure ProfileScorer is initialized before tests run (startup event not fired
# by TestClient unless used as context manager — call init_learning_state directly,
# matching the pattern used in test_centroid_export.py tests 7–10).
init_learning_state()

client = TestClient(app)


def _heatmap_data():
    resp = client.get("/api/soc/centroid-heatmap")
    assert resp.status_code == 200
    return resp.json()


def _scorer_ready(data: dict) -> bool:
    return data.get("status") != "cold_start"


# ---------------------------------------------------------------------------
# Test 1 — endpoint returns 200 (including cold_start)
# ---------------------------------------------------------------------------

def test_centroid_heatmap_returns_200():
    resp = client.get("/api/soc/centroid-heatmap")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Test 2 — factors list has six entries including device_trust
# ---------------------------------------------------------------------------

def test_centroid_heatmap_has_six_factors():
    data = _heatmap_data()
    assert _scorer_ready(data), "ProfileScorer must be initialized (init_learning_state called at module level)"
    assert len(data["factors"]) == 6
    assert "device_trust" in data["factors"]


# ---------------------------------------------------------------------------
# Test 3 — noise_fingerprint present with device_trust < 0.10
# ---------------------------------------------------------------------------

def test_centroid_heatmap_noise_fingerprint_present():
    data = _heatmap_data()
    assert _scorer_ready(data), "ProfileScorer must be initialized (init_learning_state called at module level)"
    assert "noise_fingerprint" in data
    dt = data["noise_fingerprint"].get("device_trust", {})
    assert dt.get("kernel_weight", 1.0) < 0.10


# ---------------------------------------------------------------------------
# Test 4 — kernel_weights normalized: max=1.0, all positive
# ---------------------------------------------------------------------------

def test_centroid_heatmap_kernel_weights_sum_reasonable():
    data = _heatmap_data()
    assert _scorer_ready(data), "ProfileScorer must be initialized (init_learning_state called at module level)"
    weights = list(data["kernel_weights"].values())
    assert max(weights) <= 1.0
    assert min(weights) > 0.0


# ---------------------------------------------------------------------------
# Test 5 — heatmap dict covers all categories
# ---------------------------------------------------------------------------

def test_centroid_heatmap_heatmap_has_six_categories():
    data = _heatmap_data()
    assert _scorer_ready(data), "ProfileScorer must be initialized (init_learning_state called at module level)"
    for cat in data["categories"]:
        assert cat in data["heatmap"], f"Category missing from heatmap: {cat}"
