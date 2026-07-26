import numpy as np
import pytest

from app.domains.soc import config as soc_config
from app.domains.soc.config import SCORER_ACTIONS
from app.domains.soc.scorer_adapter import SOCCompoundingScorerAdapter
from app.routers import triage
from copilot_sdk.graph.memory_store import InMemoryGraphStore
from copilot_sdk.scoring.scorer import CompoundingScorer


@pytest.fixture(autouse=True)
def _test_profile_for_in_memory_scorers(monkeypatch):
    original = CompoundingScorer.from_preset

    def from_preset(*args, **kwargs):
        kwargs.setdefault("profile", "test")
        return original(*args, **kwargs)

    monkeypatch.setattr(CompoundingScorer, "from_preset", from_preset)


FACTOR_VECTOR = np.array([0.9, 0.9, 0.9, 0.9, 0.9, 0.1], dtype=float)
CATEGORY_INDEX = 0
GROUND_TRUTH_ACTION = "investigate"


def _set_soc_learning(monkeypatch, enabled: bool) -> None:
    monkeypatch.setattr(soc_config, "LEARNING_ENABLED", False)
    monkeypatch.setattr(triage, "LEARNING_ENABLED", False)
    if enabled:
        monkeypatch.setenv("SOC_LEARNING_ENABLED", "true")
    else:
        monkeypatch.delenv("SOC_LEARNING_ENABLED", raising=False)


def _score_probabilities(scorer: SOCCompoundingScorerAdapter) -> np.ndarray:
    result = scorer.score(FACTOR_VECTOR, category_index=CATEGORY_INDEX)
    return np.asarray(result.probabilities, dtype=float)


def _apply_verified_outcome_if_enabled(scorer: SOCCompoundingScorerAdapter) -> float:
    if not triage._soc_learning_enabled():
        return 0.0
    result = scorer.score(FACTOR_VECTOR, category_index=CATEGORY_INDEX)
    action_index = int(result.action_index)
    gt_action_index = SCORER_ACTIONS.index(GROUND_TRUTH_ACTION)
    before = np.asarray(scorer.mu, dtype=float).copy()
    scorer.update(
        f=FACTOR_VECTOR,
        category_index=CATEGORY_INDEX,
        action_index=action_index,
        correct=(action_index == gt_action_index),
        gt_action_index=gt_action_index,
    )
    return float(np.linalg.norm(np.asarray(scorer.mu, dtype=float) - before))


def test_soc_learning_changes_score(monkeypatch):
    _set_soc_learning(monkeypatch, True)
    scorer = SOCCompoundingScorerAdapter(
        graph_store=InMemoryGraphStore(domain="soc")
    )

    score_1 = _score_probabilities(scorer)
    centroid_delta = _apply_verified_outcome_if_enabled(scorer)
    score_2 = _score_probabilities(scorer)

    assert triage._soc_learning_enabled() is True
    assert centroid_delta > 0.0
    assert not np.allclose(score_2, score_1)


def test_soc_learning_disabled_no_change(monkeypatch):
    _set_soc_learning(monkeypatch, False)
    scorer = SOCCompoundingScorerAdapter(
        graph_store=InMemoryGraphStore(domain="soc")
    )

    score_1 = _score_probabilities(scorer)
    centroid_delta = _apply_verified_outcome_if_enabled(scorer)
    score_2 = _score_probabilities(scorer)

    assert triage._soc_learning_enabled() is False
    assert centroid_delta == 0.0
    np.testing.assert_allclose(score_2, score_1)


def test_soc_learning_toggle(monkeypatch):
    scorer = SOCCompoundingScorerAdapter(
        graph_store=InMemoryGraphStore(domain="soc")
    )

    _set_soc_learning(monkeypatch, False)
    score_1 = _score_probabilities(scorer)
    disabled_delta = _apply_verified_outcome_if_enabled(scorer)
    score_2 = _score_probabilities(scorer)

    _set_soc_learning(monkeypatch, True)
    enabled_delta = _apply_verified_outcome_if_enabled(scorer)
    score_3 = _score_probabilities(scorer)

    assert disabled_delta == 0.0
    np.testing.assert_allclose(score_2, score_1)
    assert enabled_delta > 0.0
    assert not np.allclose(score_3, score_2)
