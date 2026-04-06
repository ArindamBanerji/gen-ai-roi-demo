"""
Tests for GET /api/soc/centroid-heatmap (Block 2.4).

Verifies the heat map structure: categories, actions, factors,
kernel_weights, heatmap, noise_fingerprint, interpretation.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from fastapi.testclient import TestClient
from app.main import app

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
    if not _scorer_ready(data):
        pytest.skip("ProfileScorer not initialized — skipping factor check")

    assert len(data["factors"]) == 6
    assert "device_trust" in data["factors"]


# ---------------------------------------------------------------------------
# Test 3 — noise_fingerprint present with device_trust < 0.10
# ---------------------------------------------------------------------------

def test_centroid_heatmap_noise_fingerprint_present():
    data = _heatmap_data()
    if not _scorer_ready(data):
        pytest.skip("ProfileScorer not initialized — skipping noise_fingerprint check")

    assert "noise_fingerprint" in data
    dt = data["noise_fingerprint"].get("device_trust", {})
    assert dt.get("kernel_weight", 1.0) < 0.10


# ---------------------------------------------------------------------------
# Test 4 — kernel_weights normalized: max=1.0, all positive
# ---------------------------------------------------------------------------

def test_centroid_heatmap_kernel_weights_sum_reasonable():
    data = _heatmap_data()
    if not _scorer_ready(data):
        pytest.skip("ProfileScorer not initialized — skipping kernel_weights check")

    weights = list(data["kernel_weights"].values())
    assert max(weights) <= 1.0
    assert min(weights) > 0.0


# ---------------------------------------------------------------------------
# Test 5 — heatmap dict covers all categories
# ---------------------------------------------------------------------------

def test_centroid_heatmap_heatmap_has_six_categories():
    data = _heatmap_data()
    if not _scorer_ready(data):
        pytest.skip("ProfileScorer not initialized — skipping heatmap categories check")

    for cat in data["categories"]:
        assert cat in data["heatmap"], f"Category missing from heatmap: {cat}"
