"""Tests for iks_bootstrap_soc.json — shape and value parity with SCORER_PROFILE_CENTROIDS.

Scorer uses A=4 (SCORER_ACTIONS) → sidecar shape is (6, 4, 6).
Key is "mu_zero" — matches the loader in app/services/iks.py.
"""
import json
import numpy as np
from pathlib import Path


_JSON_PATH = Path(__file__).parent.parent / "app" / "data" / "iks_bootstrap_soc.json"


def test_iks_bootstrap_shape_matches_config():
    """Sidecar must be {"mu_zero": [...]} with shape (6, 4, 6) — 4-action scorer."""
    from app.domains.soc.config import SCORER_PROFILE_CENTROIDS
    with open(_JSON_PATH) as f:
        data = json.load(f)
    assert "mu_zero" in data, f"Expected key 'mu_zero', got keys: {list(data.keys())}"
    mu0 = np.array(data["mu_zero"])
    mu_config = np.array(SCORER_PROFILE_CENTROIDS)
    assert mu0.shape == (6, 4, 6), f"Expected shape (6, 4, 6), got {mu0.shape}"
    assert mu0.shape == mu_config.shape


def test_iks_bootstrap_values_match_config():
    """μ₀ must equal SCORER_PROFILE_CENTROIDS (A=4 slice) at generation time."""
    from app.domains.soc.config import SCORER_PROFILE_CENTROIDS
    with open(_JSON_PATH) as f:
        data = json.load(f)
    mu0 = np.array(data["mu_zero"])
    mu_config = np.array(SCORER_PROFILE_CENTROIDS)
    np.testing.assert_array_almost_equal(mu0, mu_config, decimal=6)
