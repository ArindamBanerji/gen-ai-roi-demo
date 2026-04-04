"""
Block 7.2 — tests for compute_theta_min(alpha, V)
"""
import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.domains.soc.config import compute_theta_min


def test_reference_point():
    """V=200, alpha=0.25 → 23.53/50 = 0.4706, within 0.001 of 0.467"""
    result = compute_theta_min(0.25, 200)
    assert abs(result - 0.4706) < 0.001, (
        f"Expected ~0.4706, got {result}"
    )


def test_impossible_deployment():
    """V=50, alpha=0.25 → 23.53/12.5 = 1.882 > 1.0"""
    result = compute_theta_min(0.25, 50)
    assert result > 1.0, f"Expected > 1.0 for impossible deployment, got {result}"


def test_zero_volume_returns_inf():
    """alpha=0, V=200 → inf"""
    result = compute_theta_min(0, 200)
    assert result == float('inf'), f"Expected inf, got {result}"
