"""
Progressive RL impact tests.

Validates that correct vs incorrect decisions have measurably different
and asymmetric impact on ProfileScorer centroids.

No live Neo4j required.
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from gae.profile_scorer import ProfileScorer, MAX_ETA_DELTA


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ACTIONS    = ["escalate", "investigate", "suppress", "monitor"]
_CATEGORIES = ["credential_access", "lateral_movement", "malware_execution",
               "data_exfiltration", "insider_threat", "cloud_infrastructure"]
_N_CATS     = len(_CATEGORIES)
_N_ACTS     = len(_ACTIONS)
_N_FACTORS  = 6

_CAT_IDX_CRED = 0   # credential_access
_ACT_IDX_ESC  = 0   # escalate


def _make_scorer(eta=0.05, eta_override=None) -> ProfileScorer:
    """ProfileScorer with mu=0.5 everywhere, matching SOC category/action shape."""
    mu = np.full((_N_CATS, _N_ACTS, _N_FACTORS), 0.5, dtype=float)
    return ProfileScorer(
        mu=mu,
        actions=_ACTIONS,
        categories=_CATEGORIES,
        eta_override=eta_override,
    )


def _fvec(value: float) -> np.ndarray:
    return np.full(_N_FACTORS, value, dtype=float)


# ---------------------------------------------------------------------------
# Test 1 — correct decisions move centroid toward the chosen action
# ---------------------------------------------------------------------------

def test_correct_decisions_move_centroid_toward_action():
    """5 correct escalate decisions on credential_access must increase that centroid."""
    scorer = _make_scorer()
    mu_before = scorer.mu[_CAT_IDX_CRED, _ACT_IDX_ESC, :].copy()

    # f=1.0 → gradient = 1.0 - 0.5 = 0.5 (positive → centroid should rise)
    for _ in range(5):
        scorer.update(
            f=_fvec(1.0),
            category_index=_CAT_IDX_CRED,
            action_index=_ACT_IDX_ESC,
            correct=True,
        )

    mu_after = scorer.mu[_CAT_IDX_CRED, _ACT_IDX_ESC, :]
    delta = mu_after - mu_before

    assert np.all(delta > 0), (
        f"5 correct escalate decisions must increase centroid; got delta={delta}"
    )
    assert np.all(delta <= MAX_ETA_DELTA * 5 + 1e-9), (
        f"Cumulative delta must not exceed MAX_ETA_DELTA×5={MAX_ETA_DELTA * 5:.4f}; "
        f"got max delta={delta.max():.6f}"
    )


# ---------------------------------------------------------------------------
# Test 2 — override updates use asymmetric (smaller) eta
# ---------------------------------------------------------------------------

def test_override_decisions_use_asymmetric_eta():
    """
    η_confirm=0.05 (default), η_override=0.01.
    Correct update delta must be ~5× larger than override update delta.
    """
    ETA_CONFIRM  = 0.05
    ETA_OVERRIDE = 0.01

    # Scorer A: correct update
    scorer_a = _make_scorer()
    mu_before_a = scorer_a.mu[_CAT_IDX_CRED, _ACT_IDX_ESC, :].copy()
    scorer_a.update(
        f=_fvec(0.55),   # small gradient → below cap so raw ratio is preserved
        category_index=_CAT_IDX_CRED,
        action_index=_ACT_IDX_ESC,
        correct=True,
    )
    delta_correct = float(np.mean(np.abs(
        scorer_a.mu[_CAT_IDX_CRED, _ACT_IDX_ESC, :] - mu_before_a
    )))

    # Scorer B: override update (correct=False, eta_override set)
    scorer_b = _make_scorer(eta_override=ETA_OVERRIDE)
    mu_before_b = scorer_b.mu[_CAT_IDX_CRED, _ACT_IDX_ESC, :].copy()
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        scorer_b.update(
            f=_fvec(0.55),
            category_index=_CAT_IDX_CRED,
            action_index=_ACT_IDX_ESC,
            correct=False,
            gt_action_index=None,
        )
    delta_override = float(np.mean(np.abs(
        scorer_b.mu[_CAT_IDX_CRED, _ACT_IDX_ESC, :] - mu_before_b
    )))

    assert delta_correct > 0, "Correct update must move centroid"
    assert delta_override > 0, "Override update must move centroid"
    ratio = delta_correct / delta_override
    assert ratio > 1.0, (
        f"Correct delta must exceed override delta; ratio={ratio:.2f}"
    )
    # Expected ratio ≈ 5 (0.05 / 0.01); allow generous tolerance
    assert ratio == pytest.approx(ETA_CONFIRM / ETA_OVERRIDE, rel=0.30), (
        f"Expected ratio ≈{ETA_CONFIRM / ETA_OVERRIDE:.1f}, got {ratio:.2f}"
    )


# ---------------------------------------------------------------------------
# Test 3 — eta cap limits single update to MAX_ETA_DELTA
# ---------------------------------------------------------------------------

def test_eta_cap_limits_single_update():
    """
    f=1.0, mu=0.5, η=0.05 → raw delta = 0.05 * 0.5 = 0.025 > MAX_ETA_DELTA.
    Each coordinate must be capped at exactly MAX_ETA_DELTA = 0.005.
    """
    scorer = _make_scorer()
    mu_before = scorer.mu[_CAT_IDX_CRED, _ACT_IDX_ESC, :].copy()

    scorer.update(
        f=_fvec(1.0),
        category_index=_CAT_IDX_CRED,
        action_index=_ACT_IDX_ESC,
        correct=True,
    )

    delta = scorer.mu[_CAT_IDX_CRED, _ACT_IDX_ESC, :] - mu_before

    np.testing.assert_allclose(
        delta,
        np.full(_N_FACTORS, MAX_ETA_DELTA),
        atol=1e-9,
        err_msg=(
            f"Each coordinate must be capped at MAX_ETA_DELTA={MAX_ETA_DELTA}; "
            f"got {delta}"
        ),
    )


# ---------------------------------------------------------------------------
# Test 4 — centroid stays in [0.0, 1.0] after 100 correct updates
# ---------------------------------------------------------------------------

def test_centroid_stays_in_bounds_after_many_updates():
    """100 correct escalate decisions must not push any centroid outside [0.0, 1.0]."""
    scorer = _make_scorer()

    for _ in range(100):
        scorer.update(
            f=_fvec(1.0),
            category_index=_CAT_IDX_CRED,
            action_index=_ACT_IDX_ESC,
            correct=True,
        )

    assert np.all(scorer.mu >= 0.0), (
        f"Centroid below 0.0 after 100 updates; min={scorer.mu.min():.6f}"
    )
    assert np.all(scorer.mu <= 1.0), (
        f"Centroid above 1.0 after 100 updates; max={scorer.mu.max():.6f}"
    )


# ---------------------------------------------------------------------------
# Test 5 — incorrect decisions (correct=False, no gt) do not update centroid
# ---------------------------------------------------------------------------

def test_incorrect_decisions_do_not_update_centroid():
    """
    correct=False with gt_action_index=None → push-away path only.
    The *predicted* action's centroid is pushed away (moves), but the
    correct-action centroid is untouched.

    More specifically: with correct=False, the scorer's predicted action
    centroid moves (push-away), but a *different* action's centroid
    (one not involved in the update) must remain unchanged.
    """
    scorer = _make_scorer()
    # Record centroid for an action that is NOT action_index=0 (escalate)
    uninvolved_act = 2  # suppress
    mu_uninvolved_before = scorer.mu[_CAT_IDX_CRED, uninvolved_act, :].copy()

    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        scorer.update(
            f=_fvec(1.0),
            category_index=_CAT_IDX_CRED,
            action_index=_ACT_IDX_ESC,   # escalate is predicted (pushed away)
            correct=False,
            gt_action_index=None,
        )

    mu_uninvolved_after = scorer.mu[_CAT_IDX_CRED, uninvolved_act, :]

    np.testing.assert_array_equal(
        mu_uninvolved_after,
        mu_uninvolved_before,
        err_msg=(
            "Uninvolved action centroid (suppress) must not change "
            "on a push-only incorrect update"
        ),
    )
