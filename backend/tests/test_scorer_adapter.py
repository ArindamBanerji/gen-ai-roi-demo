from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from app.domains.soc.config import SCORER_ACTIONS, SOC_CATEGORIES, SOCDomainConfig
from app.domains.soc.scorer_adapter import SOCCompoundingScorerAdapter
from copilot_sdk.graph.memory_store import InMemoryGraphStore
from copilot_sdk.scoring.scorer import CompoundingScorer


@pytest.fixture(autouse=True)
def _test_profile_for_in_memory_scorers(monkeypatch):
    original = CompoundingScorer.from_preset

    def from_preset(*args, **kwargs):
        kwargs.setdefault("profile", "test")
        return original(*args, **kwargs)

    monkeypatch.setattr(CompoundingScorer, "from_preset", from_preset)


def _raw_scorer():
    return SOCDomainConfig().build_profile_scorer()


def _adapter() -> SOCCompoundingScorerAdapter:
    return SOCCompoundingScorerAdapter(
        graph_store=InMemoryGraphStore(domain="soc")
    )


def _vector(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.uniform(0.05, 0.95, size=6)


def test_adapter_creates_compound_scorer():
    scorer = _adapter()

    assert scorer._compound is not None
    assert scorer._scorer is scorer._compound._scorer
    assert not hasattr(scorer, "compound")


def test_adapter_uses_soc_preset():
    scorer = _adapter()

    assert scorer._compound._preset.name == "soc"
    assert scorer.centroids.shape == (6, 4, 6)
    assert scorer.actions == list(SCORER_ACTIONS)
    assert scorer.categories == list(SOC_CATEGORIES)


def test_adapter_score_matches_raw():
    raw = _raw_scorer()
    scorer = _adapter()
    factors = _vector(1)

    expected = raw.score(factors, category_index=0)
    actual = scorer.score(factors, category_index=0)

    assert actual.action_index == expected.action_index
    assert actual.action_name == expected.action_name
    np.testing.assert_allclose(actual.probabilities, expected.probabilities)


def test_adapter_mu_accessible():
    scorer = _adapter()

    assert scorer.mu.shape == (6, 4, 6)
    assert scorer.centroids.shape == (6, 4, 6)


def test_adapter_update_works():
    scorer = _adapter()
    before = scorer.centroids[0, 1].copy()

    scorer.update(_vector(2), category_index=0, action_index=1, correct=True)

    assert not np.array_equal(scorer.centroids[0, 1], before)
    assert scorer.counts[0, 1] == 1


def test_adapter_reestimate_dk_works():
    scorer = _adapter()

    scorer.reestimate_dk()


def test_adapter_dk_weights_none_initially():
    scorer = _adapter()

    assert scorer._dk_weights is None
    assert scorer.get_dk_weights() is None
    assert scorer.get_dk_weights(0) is None


def test_adapter_category_states_accessible():
    scorer = _adapter()

    assert scorer._category_states is not None
    assert len(scorer._category_states) == 6


def test_adapter_getattr_delegates():
    scorer = _adapter()

    assert scorer.n_categories == 6
    assert scorer.n_actions == 4
    assert scorer.tau == pytest.approx(0.1)


def test_adapter_setattr_delegates_raw_attributes():
    scorer = _adapter()

    scorer.tau = 0.2
    scorer.decision_count = 12

    assert scorer._scorer.tau == pytest.approx(0.2)
    assert scorer._scorer.decision_count == 12


def test_adapter_centroids_setter_delegates():
    scorer = _adapter()
    replacement = np.full((6, 4, 6), 0.25)

    scorer.centroids = replacement

    np.testing.assert_allclose(scorer._scorer.centroids, replacement)


def test_adapter_get_dk_weights():
    scorer = _adapter()

    assert scorer.get_dk_weights() is None


def test_adapter_get_centroid():
    scorer = _adapter()

    centroid = scorer.get_centroid("credential_access", "escalate")

    assert isinstance(centroid, list)
    assert len(centroid) == 6


def test_adapter_get_category_phase():
    scorer = _adapter()

    phase = scorer.get_category_phase("credential_access")

    assert phase in {"MEAN_CONVERGENCE", "VARIANCE_LEARNING"}


def test_score_through_adapter_equals_direct():
    raw = _raw_scorer()
    scorer = _adapter()
    rng = np.random.default_rng(42)

    for _ in range(100):
        factors = rng.uniform(0.0, 1.0, size=6)
        category_index = int(rng.integers(0, 6))
        expected = raw.score(factors, category_index=category_index)
        actual = scorer.score(factors, category_index=category_index)

        assert actual.action_index == expected.action_index
        assert actual.action_name == expected.action_name
        np.testing.assert_allclose(actual.probabilities, expected.probabilities, atol=1e-10)


def test_score_all_categories():
    scorer = _adapter()
    factors = np.full(6, 0.5)

    for category_index in range(6):
        result = scorer.score(factors, category_index=category_index)
        assert result.action_name in SCORER_ACTIONS


def test_adapter_phase_transition_at_200():
    scorer = _adapter()
    factors = np.full(6, 0.8)

    for _ in range(210):
        scorer.update(factors, category_index=0, action_index=1, correct=True)
    scorer.reestimate_dk()

    assert scorer.get_phase(0) == "VARIANCE_LEARNING"
    assert scorer.get_dk_weights(0) is not None
    assert scorer.get_dk_weights() is not None


def test_gae_state_uses_adapter(monkeypatch, tmp_path):
    from app.services import gae_state
    from copilot_sdk.config import GraphConfig
    from copilot_sdk.graph import factory as graph_factory

    monkeypatch.setattr(gae_state, "_STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(gae_state, "_MU_ZERO_PATH", tmp_path / "mu_zero.json")
    monkeypatch.setattr(gae_state, "_learning_state", None)
    monkeypatch.setattr(gae_state, "_learning_store", None)
    monkeypatch.setattr(gae_state, "_bootstrap_metadata", None)
    monkeypatch.setattr(gae_state, "_bootstrap_result", None)
    monkeypatch.delenv("GRAPH_DSN", raising=False)
    monkeypatch.setattr(
        GraphConfig,
        "load",
        lambda _domain: SimpleNamespace(
            backend="sqlite",
            dsn=None,
            graph="test_graph",
            authorized="soc:test_graph",
        ),
    )
    monkeypatch.setattr(
        graph_factory,
        "create_graph_store",
        lambda **_kwargs: InMemoryGraphStore(domain="soc"),
    )
    monkeypatch.setattr(
        gae_state,
        "bootstrap_calibration",
        lambda **_kwargs: SimpleNamespace(
            n_decisions=0,
            final_drift=0.0,
            converged=True,
        ),
    )
    monkeypatch.setattr(gae_state, "save_learning_state", lambda: None)

    state = gae_state.init_learning_state()

    assert isinstance(state.profile_scorer, SOCCompoundingScorerAdapter)
