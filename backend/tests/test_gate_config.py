"""
Block 7.4 -- tests for GateConfig self-calibrating gate class.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.domains.soc.config import GateConfig


# ── fixtures ─────────────────────────────────────────────────────────────────

ANALYSTS = {"alice": 0.90, "bob": 0.70, "carol": 0.80}

def _conservative():
    """500 decisions < n_min=1000 -> conservative mode."""
    return GateConfig(n_decisions=500, V=200.0, alpha=0.25,
                      per_analyst_precision=ANALYSTS)

def _calibrated():
    """1001 decisions >= n_min=1000 -> calibrated mode."""
    return GateConfig(n_decisions=1001, V=200.0, alpha=0.25,
                      per_analyst_precision=ANALYSTS)


# ── tests ─────────────────────────────────────────────────────────────────────

def test_conservative_before_nmin():
    cfg = _conservative()
    assert cfg.n_min == 1000
    assert not cfg.calibrated
    assert cfg.spike_sigma == 5.0, f"Expected 5.0, got {cfg.spike_sigma}"


def test_calibrated_after_nmin():
    cfg = _calibrated()
    assert cfg.n_min == 1000
    assert cfg.calibrated
    assert cfg.spike_sigma == 3.0, f"Expected 3.0, got {cfg.spike_sigma}"


def test_eta_cap_conservative():
    cfg = _conservative()
    assert cfg.eta_cap == 2.0, f"Expected 2.0, got {cfg.eta_cap}"


def test_eta_cap_calibrated():
    """vol_std=0.0 -> default calibrated cap = 1.5"""
    cfg = _calibrated()   # vol_std defaults to 0.0
    assert cfg.eta_cap == 1.5, f"Expected 1.5, got {cfg.eta_cap}"


def test_eta_weights_uniform_conservative():
    cfg = _conservative()
    weights = cfg.eta_weights
    assert set(weights.keys()) == set(ANALYSTS.keys())
    assert all(w == 1.0 for w in weights.values()), (
        f"Conservative weights must all be 1.0, got {weights}"
    )


def test_eta_weights_precision_calibrated():
    cfg = _calibrated()
    weights = cfg.eta_weights
    assert set(weights.keys()) == set(ANALYSTS.keys())
    # Mean precision = (0.90+0.70+0.80)/3 = 0.80
    # alice: 0.90/0.80=1.125 → clamped to [0.5, 1.5] → 1.125
    # bob:   0.70/0.80=0.875
    # carol: 0.80/0.80=1.0
    assert 1.0 < weights["alice"] <= 1.5,  f"alice weight out of range: {weights['alice']}"
    assert 0.5 <= weights["bob"] < 1.0,    f"bob weight out of range: {weights['bob']}"
    assert abs(weights["carol"] - 1.0) < 0.01, f"carol weight should be ~1.0: {weights['carol']}"
