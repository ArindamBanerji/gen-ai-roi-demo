"""Tests for iks_bootstrap_soc.json — shape and value parity with SOC_PROFILE_CENTROIDS."""
import json
import numpy as np
import pytest
from pathlib import Path


_JSON_PATH = Path(__file__).parent.parent / "app" / "data" / "iks_bootstrap_soc.json"


def test_iks_bootstrap_shape_matches_config():
    from app.domains.soc.config import SOC_PROFILE_CENTROIDS
    with open(_JSON_PATH) as f:
        data = json.load(f)
    mu0 = np.array(data["data"])
    mu_config = np.array(SOC_PROFILE_CENTROIDS)
    assert data["shape"] == [6, 5, 6]
    assert mu0.shape == (6, 5, 6)
    assert mu0.shape == mu_config.shape


def test_iks_bootstrap_values_match_config():
    """μ₀ should be identical to SOC_PROFILE_CENTROIDS at generation time."""
    from app.domains.soc.config import SOC_PROFILE_CENTROIDS
    with open(_JSON_PATH) as f:
        data = json.load(f)
    mu0 = np.array(data["data"])
    mu_config = np.array(SOC_PROFILE_CENTROIDS)
    np.testing.assert_array_almost_equal(mu0, mu_config, decimal=6)
