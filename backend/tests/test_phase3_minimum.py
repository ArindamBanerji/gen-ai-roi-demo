"""
Block 7.3 -- tests for compute_phase3_minimum(V, alpha)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.domains.soc.config import compute_phase3_minimum


def test_reference_point():
    """V=200, alpha=0.25 -> max(1000, 20*50) = max(1000, 1000) = 1000"""
    assert compute_phase3_minimum(200, 0.25) == 1000


def test_low_volume_floor():
    """V=50, alpha=0.25 -> max(1000, 20*12.5) = max(1000, 250) = 1000"""
    assert compute_phase3_minimum(50, 0.25) == 1000


def test_high_volume():
    """V=500, alpha=0.25 -> max(1000, 20*125) = max(1000, 2500) = 2500"""
    assert compute_phase3_minimum(500, 0.25) == 2500
