"""
tests/test_soc_constants.py -- SOC accuracy constants (V-ACC-TRAJ-2 + V-ACC-TRAJ-3).

3 tests validating constants.py values and helper functions.

Run from backend/:
    pytest tests/test_soc_constants.py -v
"""

from app.domains.soc.constants import (
    get_sigma_band,
    get_permanent_gap_pp,
    n_half_applicable,
    COLD_START_REFERENCE_TRAJECTORY,
    S2P_COLD_START_REFERENCE,
)
from app.domains.soc.config import SOC_FACTORS, soc_config


def test_get_sigma_band_boundaries():
    """get_sigma_band(): <=0.12 -> low, <=0.22 -> medium, >0.22 -> high."""
    assert get_sigma_band(0.08)  == "low"
    assert get_sigma_band(0.12)  == "low"
    assert get_sigma_band(0.13)  == "medium"
    assert get_sigma_band(0.18)  == "medium"
    assert get_sigma_band(0.22)  == "medium"
    assert get_sigma_band(0.23)  == "high"
    assert get_sigma_band(0.35)  == "high"


def test_permanent_gap_pp_returns_float():
    """get_permanent_gap_pp() returns correct pp values for each sigma band."""
    assert get_permanent_gap_pp(0.18) == 6.8   # medium band: 0.068 x 100
    assert get_permanent_gap_pp(0.08) == 3.4   # low band:    0.034 x 100
    assert get_permanent_gap_pp(0.30) == 8.4   # high band:   0.084 x 100


def test_n_half_applicable():
    """n_half_applicable() is True only for low-sigma (sigma<=0.12) environments."""
    assert n_half_applicable(0.08)  is True   # low sigma
    assert n_half_applicable(0.12)  is True   # boundary -- still low
    assert n_half_applicable(0.13)  is False  # medium
    assert n_half_applicable(0.18)  is False
    assert n_half_applicable(0.30)  is False


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


def test_config_factors_order_matches_tensor_order():
    display_names = [factor.id for factor in soc_config.factors]
    assert display_names == SOC_FACTORS


def test_factor_computers_order_matches_tensor_order():
    computer_names = [computer.name for computer in soc_config.get_factor_computers()]
    assert computer_names == SOC_FACTORS
