"""
Block 7.2 -- tests for compute_theta_min(alpha, V)
"""
import math
import sys, os
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.domains.soc.config import compute_theta_min
from gae.calibration import compute_theta_min as gae_compute_theta_min, check_conservation


def test_reference_point():
    """V=200, alpha=0.25 -> 23.53/50 = 0.4706, within 0.001 of 0.467"""
    result = compute_theta_min(0.25, 200)
    assert abs(result - 0.4706) < 0.001, (
        f"Expected ~0.4706, got {result}"
    )


def test_impossible_deployment():
    """V=50, alpha=0.25 -> 23.53/12.5 = 1.882 > 1.0"""
    result = compute_theta_min(0.25, 50)
    assert result > 1.0, f"Expected > 1.0 for impossible deployment, got {result}"


def test_zero_volume_returns_inf():
    """alpha=0, V=200 -> inf"""
    result = compute_theta_min(0, 200)
    assert result == float('inf'), f"Expected inf, got {result}"


# ── gae.calibration.compute_theta_min tests ──────────────────────────────────

def test_gae_compute_theta_min_at_v200_alpha025():
    """23.53 / (0.25 * 200) = 23.53 / 50 = 0.4706"""
    result = gae_compute_theta_min(0.25, 200)
    assert abs(result - 0.4706) < 0.001, f"Expected ~0.4706, got {result}"


def test_gae_compute_theta_min_at_v20_alpha025():
    """23.53 / (0.25 * 20) = 23.53 / 5 = 4.706"""
    result = gae_compute_theta_min(0.25, 20)
    assert abs(result - 4.706) < 0.01, f"Expected ~4.706, got {result}"


def test_gae_compute_theta_min_rejects_zero_alpha():
    with pytest.raises(ValueError):
        gae_compute_theta_min(0, 200)


def test_gae_compute_theta_min_rejects_zero_v():
    with pytest.raises(ValueError):
        gae_compute_theta_min(0.25, 0)


def test_gae_conservation_red_at_v20():
    """signal = 0.25 * 0.85 * 20 = 4.25 < theta_min = 4.706 -> RED"""
    theta = gae_compute_theta_min(0.25, 20)
    cc = check_conservation(alpha=0.25, q=0.85, V=20, theta_min=theta)
    assert cc.status == "RED", (
        f"Expected RED (signal=4.25 < theta_min={theta:.3f}), got {cc.status}"
    )
