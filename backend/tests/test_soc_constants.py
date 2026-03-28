"""
tests/test_soc_constants.py — SOC accuracy constants (V-ACC-TRAJ-2 + V-ACC-TRAJ-3).

3 tests validating constants.py values and helper functions.

Run from backend/:
    pytest tests/test_soc_constants.py -v
"""

from app.domains.soc.constants import (
    get_sigma_band,
    get_permanent_gap_pp,
    COLD_START_REFERENCE_TRAJECTORY,
    S2P_COLD_START_REFERENCE,
)


def test_get_sigma_band_boundaries():
    """get_sigma_band(): ≤0.12 → low, ≤0.22 → medium, >0.22 → high."""
    assert get_sigma_band(0.08)  == "low"
    assert get_sigma_band(0.12)  == "low"
    assert get_sigma_band(0.13)  == "medium"
    assert get_sigma_band(0.18)  == "medium"
    assert get_sigma_band(0.22)  == "medium"
    assert get_sigma_band(0.23)  == "high"
    assert get_sigma_band(0.35)  == "high"


def test_permanent_gap_pp_returns_float():
    """get_permanent_gap_pp() returns correct pp values for each sigma band."""
    assert get_permanent_gap_pp(0.18) == 7.5   # medium band: 0.075 × 100
    assert get_permanent_gap_pp(0.08) == 3.5   # low band:    0.035 × 100
    assert get_permanent_gap_pp(0.30) == 8.8   # high band:   0.088 × 100


def test_trajectory_dicts_monotonically_increasing():
    """Both reference trajectories must be strictly monotonically increasing."""
    vals = list(COLD_START_REFERENCE_TRAJECTORY.values())
    assert all(vals[i] < vals[i + 1] for i in range(len(vals) - 1)), (
        f"SOC trajectory not monotonically increasing: {vals}"
    )

    s2p_vals = list(S2P_COLD_START_REFERENCE.values())
    assert all(s2p_vals[i] < s2p_vals[i + 1] for i in range(len(s2p_vals) - 1)), (
        f"S2P trajectory not monotonically increasing: {s2p_vals}"
    )
