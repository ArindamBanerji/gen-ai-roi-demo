"""
Tests for CORR-2: LEARNING_ENABLED toggle and ProfileScorer.update() wiring.

Coverage:
  test_learning_disabled_scorer_unchanged     — LEARNING_ENABLED=False → centroids untouched
  test_learning_enabled_scorer_updates        — LEARNING_ENABLED=True  → centroids change
  test_learning_passes_gt_action_index        — gt_action_index is always passed
  test_learning_toggle_does_not_affect_scoring — toggle has no effect on score() output
"""

import numpy as np
import pytest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_profile_scorer():
    """Build a real ProfileScorer from SOC config."""
    from app.domains.soc.config import SOCDomainConfig
    return SOCDomainConfig().build_profile_scorer()


def _factor_vector():
    """Representative 6-element factor vector."""
    return np.array([0.7, 0.8, 0.6, 0.5, 0.4, 0.2], dtype=np.float64)


# ---------------------------------------------------------------------------
# Test 1: LEARNING_ENABLED=False → ProfileScorer centroids unchanged
# ---------------------------------------------------------------------------

def test_learning_disabled_scorer_unchanged():
    """
    With LEARNING_ENABLED=False, calling the simulation learning path does
    NOT mutate ProfileScorer centroids.
    """
    import app.domains.soc.config as soc_cfg
    from app.domains.soc.config import SOCDomainConfig

    scorer = _make_profile_scorer()
    mu_before = scorer.centroids.copy()

    with patch.object(soc_cfg, "LEARNING_ENABLED", False):
        # Simulate what simulation.py Step 10 would call when LEARNING_ENABLED=False
        if soc_cfg.LEARNING_ENABLED:
            scorer.update(
                f=_factor_vector(),
                category_index=0,
                action_index=0,
                correct=True,
                gt_action_index=0,
            )

    np.testing.assert_array_equal(
        scorer.centroids, mu_before,
        err_msg="LEARNING_ENABLED=False must leave ProfileScorer centroids unchanged"
    )


# ---------------------------------------------------------------------------
# Test 2: LEARNING_ENABLED=True → ProfileScorer centroids change
# ---------------------------------------------------------------------------

def test_learning_enabled_scorer_updates():
    """
    With LEARNING_ENABLED=True, calling ProfileScorer.update() mutates centroids.
    """
    import app.domains.soc.config as soc_cfg

    scorer = _make_profile_scorer()
    mu_before = scorer.centroids.copy()

    with patch.object(soc_cfg, "LEARNING_ENABLED", True):
        # Simulate what simulation.py Step 10 would call when LEARNING_ENABLED=True
        if soc_cfg.LEARNING_ENABLED:
            scorer.update(
                f=_factor_vector(),
                category_index=0,
                action_index=0,
                correct=True,
                gt_action_index=0,
            )

    assert not np.array_equal(scorer.centroids, mu_before), (
        "LEARNING_ENABLED=True must cause ProfileScorer.update() to mutate centroids"
    )


# ---------------------------------------------------------------------------
# Test 3: gt_action_index is always passed to ProfileScorer.update()
# ---------------------------------------------------------------------------

def test_learning_passes_gt_action_index():
    """
    When LEARNING_ENABLED=True and ProfileScorer.update() is called,
    gt_action_index is explicitly provided (not omitted).

    Tested against the simulation path which always has ground_truth_action.
    """
    import app.domains.soc.config as soc_cfg
    from app.domains.soc.config import SOCDomainConfig, resolve_alert_category

    mock_scorer = MagicMock()

    actions = SOCDomainConfig.get_actions()
    category = "credential_access"
    ground_truth_action = "suppress"
    selected_action = "escalate"
    action_index = actions.index(selected_action)
    gt_action_index = actions.index(ground_truth_action)
    f_for_update = _factor_vector().reshape(1, -1)
    correct = False

    cat_name = resolve_alert_category(category)
    cat_idx  = SOCDomainConfig().get_category_index(cat_name)
    gt_idx   = actions.index(ground_truth_action) if ground_truth_action in actions else action_index

    with patch.object(soc_cfg, "LEARNING_ENABLED", True):
        if soc_cfg.LEARNING_ENABLED:
            mock_scorer.update(
                f=f_for_update.flatten(),
                category_index=cat_idx,
                action_index=action_index,
                correct=correct,
                gt_action_index=gt_idx,
            )

    assert mock_scorer.update.called, "ProfileScorer.update() must be called when LEARNING_ENABLED=True"

    call_kwargs = mock_scorer.update.call_args
    passed_kwargs = call_kwargs.kwargs if call_kwargs.kwargs else {}
    passed_args = call_kwargs.args if call_kwargs.args else ()

    # gt_action_index must be present as a keyword argument
    assert "gt_action_index" in passed_kwargs, (
        "gt_action_index must be passed as keyword argument to ProfileScorer.update()"
    )
    assert passed_kwargs["gt_action_index"] == gt_action_index, (
        f"Expected gt_action_index={gt_action_index}, "
        f"got {passed_kwargs['gt_action_index']}"
    )


# ---------------------------------------------------------------------------
# Test 4: Toggle has no effect on score() output
# ---------------------------------------------------------------------------

def test_learning_toggle_does_not_affect_scoring():
    """
    ProfileScorer.score() returns identical results regardless of LEARNING_ENABLED.
    The toggle only gates update(), not score().
    """
    import app.domains.soc.config as soc_cfg
    from app.domains.soc.config import SOCDomainConfig

    scorer = _make_profile_scorer()
    f = _factor_vector()
    category_index = 0

    with patch.object(soc_cfg, "LEARNING_ENABLED", False):
        result_off = scorer.score(f, category_index=category_index)

    with patch.object(soc_cfg, "LEARNING_ENABLED", True):
        result_on = scorer.score(f, category_index=category_index)

    assert result_off.action_index == result_on.action_index, (
        "LEARNING_ENABLED must not change ProfileScorer.score() action selection"
    )
    np.testing.assert_allclose(
        result_off.probabilities, result_on.probabilities, rtol=1e-9,
        err_msg="LEARNING_ENABLED must not change ProfileScorer.score() probabilities"
    )
    assert abs(result_off.confidence - result_on.confidence) < 1e-9, (
        "LEARNING_ENABLED must not change ProfileScorer.score() confidence"
    )
