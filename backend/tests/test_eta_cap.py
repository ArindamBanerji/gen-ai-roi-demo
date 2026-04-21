"""
Block 9.5 — η change-rate cap tests (V-STABILITY F=8.14).

Verifies that ProfileScorer.update() caps any single coordinate delta at
±MAX_ETA_DELTA = 0.005, for both the correct (η_confirm) and override (η_override)
update paths.
"""
import os
import sys
import warnings

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from gae.profile_scorer import ProfileScorer, MAX_ETA_DELTA
from app.domains.soc.config import MAX_ETA_DELTA as APP_MAX_ETA_DELTA


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ACTIONS     = ["escalate", "investigate", "suppress"]
_CATEGORIES  = ["malware", "phishing"]
_N_CATS      = len(_CATEGORIES)
_N_ACTS      = len(_ACTIONS)
_N_FACTORS   = 6


def _make_scorer(eta_override=None) -> ProfileScorer:
    """
    Minimal ProfileScorer with mu=0.5 everywhere.
    Default eta=0.05, eta_neg=0.05 (ProfileScorer built-ins when profile=None).
    """
    mu = np.full((_N_CATS, _N_ACTS, _N_FACTORS), 0.5, dtype=float)
    scorer = ProfileScorer(
        mu=mu,
        actions=_ACTIONS,
        categories=_CATEGORIES,
        eta_override=eta_override,
    )
    return scorer


def _fvec(value: float) -> np.ndarray:
    return np.full(_N_FACTORS, value, dtype=float)


# ---------------------------------------------------------------------------
# Test 1 — large update is capped on the correct (η_confirm) path
# ---------------------------------------------------------------------------

def test_large_update_is_capped():
    """
    Default η=0.05, f=1.0, mu=0.5 → raw delta per coord = 0.05*(1.0-0.5) = 0.025.
    0.025 > MAX_ETA_DELTA=0.005 → each coordinate must be capped at 0.005.
    """
    scorer = _make_scorer()
    mu_before = scorer.centroids[0, 0, :].copy()

    scorer.update(f=_fvec(1.0), category_index=0, action_index=0, correct=True)

    actual_delta = scorer.centroids[0, 0, :] - mu_before

    assert np.all(np.abs(actual_delta) <= MAX_ETA_DELTA + 1e-9), (
        f"Delta exceeds cap: max|Δ|={np.max(np.abs(actual_delta)):.6f}, "
        f"cap={MAX_ETA_DELTA}"
    )
    np.testing.assert_allclose(
        actual_delta,
        np.full(_N_FACTORS, MAX_ETA_DELTA),
        atol=1e-9,
        err_msg="Each coordinate should be capped at exactly MAX_ETA_DELTA",
    )


# ---------------------------------------------------------------------------
# Test 2 — small update passes through unmodified
# ---------------------------------------------------------------------------

def test_small_update_passes_through():
    """
    η=0.05, f=0.55, mu=0.5 → raw delta per coord = 0.05*(0.55-0.5) = 0.0025.
    0.0025 < MAX_ETA_DELTA=0.005 → no cap; mu moves by exactly 0.0025.
    """
    scorer = _make_scorer()
    mu_before = scorer.centroids[0, 0, :].copy()

    scorer.update(f=_fvec(0.55), category_index=0, action_index=0, correct=True)

    actual_delta = scorer.centroids[0, 0, :] - mu_before
    expected_delta = 0.05 * (0.55 - 0.5)   # = 0.0025

    assert expected_delta < MAX_ETA_DELTA, "Pre-condition: delta should be below cap"
    np.testing.assert_allclose(
        actual_delta,
        np.full(_N_FACTORS, expected_delta),
        atol=1e-9,
        err_msg=f"Small delta should pass through unmodified (expected {expected_delta:.4f})",
    )


# ---------------------------------------------------------------------------
# Test 3 — cap applies to the override (η_override) path
# ---------------------------------------------------------------------------

def test_cap_applies_to_override_path():
    """
    η_override=0.05, f=1.0, mu=0.5 → raw push delta per coord = 0.05*(1.0-0.5) = 0.025.
    Capped at MAX_ETA_DELTA=0.005 on the override (correct=False, push-only) path.
    """
    scorer = _make_scorer(eta_override=0.05)
    scorer.centroids[:] = 0.5
    mu_before = scorer.centroids[0, 1, :].copy()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        scorer.update(
            f=_fvec(1.0),
            category_index=0,
            action_index=1,
            correct=False,
            gt_action_index=None,   # push-only backward-compat path
        )

    actual_delta = scorer.centroids[0, 1, :] - mu_before

    assert np.all(np.abs(actual_delta) <= MAX_ETA_DELTA + 1e-9), (
        f"Override path delta exceeds cap: max|Δ|={np.max(np.abs(actual_delta)):.6f}"
    )


# ---------------------------------------------------------------------------
# Test 4 — app constant matches GAE library constant
# ---------------------------------------------------------------------------

def test_app_constant_matches_gae_constant():
    """MAX_ETA_DELTA in config.py must equal MAX_ETA_DELTA in gae.profile_scorer."""
    assert APP_MAX_ETA_DELTA == MAX_ETA_DELTA, (
        f"Constant mismatch: app={APP_MAX_ETA_DELTA}, gae={MAX_ETA_DELTA}"
    )
