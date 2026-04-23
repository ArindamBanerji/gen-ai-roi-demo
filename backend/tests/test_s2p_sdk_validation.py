"""
Cross-repo validation: S2P and copilot-SDK consumer contracts.

Verifies that the GAE library works for non-SOC tensor shapes (S2P)
and that all fields the SDK consumer protocol expects are present.

5 tests.  No live DB required.
"""
import warnings
import numpy as np
import pytest


# ---------------------------------------------------------------------------
# S2P scorer shape independence (2 tests)
# ---------------------------------------------------------------------------

def test_s2p_scorer_independent_shape():
    """S2P tensor shape (5 categories × 8 actions × 6 factors) scores correctly."""
    from gae.profile_scorer import ProfileScorer
    scorer = ProfileScorer(
        mu=np.full((5, 8, 6), 0.5),
        actions=["approve", "reject", "flag", "escalate",
                 "defer", "negotiate", "split", "cancel"],
    )
    result = scorer.score(np.random.rand(6), category_index=0)
    assert 0 <= result.action_index < 8


def test_s2p_centroids_setter_rejects_nan():
    """Centroid setter validation fires for S2P tensor shape too."""
    from gae.profile_scorer import ProfileScorer
    scorer = ProfileScorer(
        mu=np.full((5, 8, 6), 0.5),
        actions=["a", "b", "c", "d", "e", "f", "g", "h"],
    )
    with pytest.raises(ValueError):
        scorer.centroids = np.full((5, 8, 6), np.nan)


# ---------------------------------------------------------------------------
# SDK consumer protocol (3 tests)
# ---------------------------------------------------------------------------

def test_sdk_protocol_scorer_importable():
    """ProfileScorer is importable and exposes the SDK-expected interface."""
    from gae.profile_scorer import ProfileScorer
    assert callable(ProfileScorer)
    assert hasattr(ProfileScorer, "score")
    assert hasattr(ProfileScorer, "update")
    assert hasattr(type(ProfileScorer(
        mu=np.full((2, 2, 2), 0.5), actions=["a", "b"]
    )), "centroids")


def test_sdk_scoring_result_fields():
    """ScoringResult has all fields SDK consumers depend on."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from gae.profile_scorer import ProfileScorer
    scorer = ProfileScorer.for_soc(mu=np.full((6, 4, 6), 0.5))
    result = scorer.score(np.random.rand(6), category_index=0)
    # Core decision fields
    assert hasattr(result, "action_index")
    assert hasattr(result, "confidence")
    # Epistemic / uncertainty fields
    assert hasattr(result, "entropy")
    assert hasattr(result, "confidence_gap")
    # Probability distribution (SDK uses `probabilities`, not `action_scores`)
    assert hasattr(result, "probabilities")


def test_calibration_profile_importable():
    """CalibrationProfile is importable for SDK calibration workflows."""
    from gae.calibration import CalibrationProfile
    assert callable(CalibrationProfile)
