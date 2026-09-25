"""Measured comparisons using real ProfileScorers and immutable disk snapshots."""
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from gae.profile_scorer import ProfileScorer

from app.services.soc_learning_control import SOCLearningControlService
from copilot_sdk.twin import FrozenTwinStore


def setup_twin(tmp_path: Path) -> tuple[Any, SOCLearningControlService, dict[str, Any]]:
    scorer = ProfileScorer(mu=np.array([[[0.4, 0.4], [0.6, 0.6]]]),
                           actions=["escalate", "monitor"], categories=["identity"])
    service = SOCLearningControlService(FrozenTwinStore(tmp_path))
    snapshot = service.freeze(scorer, {"components": {"verified_decisions": 0}}, 70, scorer.mu)
    row = {"decision_id": "verified-1", "category": "identity", "factor_vector": [0.2, 0.2],
           "verified_at_epoch": snapshot["snapshot_time"] + 1}
    return scorer, service, row


def test_comparison_scores_identical_inputs_without_mutation(tmp_path: Path) -> None:
    scorer, service, row = setup_twin(tmp_path)
    original = (tmp_path / "soc.json").read_bytes()
    for _ in range(10):
        scorer.update(np.array(row["factor_vector"]), 0, 0, True)
    before = scorer.mu.copy()
    count = scorer.decision_count
    expected = scorer.score(np.array(row["factor_vector"]), 0)
    result = service.comparison(scorer, 69, decisions=[row])
    point = result["comparison_points"][0]
    assert point["decision_id"] == row["decision_id"]
    assert point["live"]["confidence"] == pytest.approx(expected.confidence)
    assert point["confidence_delta"] == pytest.approx(point["live"]["confidence"] - point["frozen"]["confidence"])
    assert point["confidence_delta"] > 0
    assert result["iks_delta"] < 0  # Confidence and IKS are separate metrics.
    assert result["mean_confidence_delta"] == point["confidence_delta"]
    np.testing.assert_array_equal(scorer.mu, before)
    assert scorer.decision_count == count
    assert (tmp_path / "soc.json").read_bytes() == original


def test_equal_and_negative_deltas_not_clamped(tmp_path: Path) -> None:
    scorer, service, row = setup_twin(tmp_path)
    assert service.comparison(scorer, decisions=[row])["mean_confidence_delta"] == pytest.approx(0)
    for _ in range(10):
        scorer.update(np.array(row["factor_vector"]), 0, 1, True)
    assert service.comparison(scorer, decisions=[row])["mean_confidence_delta"] < 0


def test_empty_cohort_and_pre_freeze_rows(tmp_path: Path) -> None:
    scorer, service, row = setup_twin(tmp_path)
    row["verified_at_epoch"] = 0
    for rows in ([], [row]):
        result = service.comparison(scorer, decisions=rows)
        assert result["comparison_points"] == []
        assert result["compared_decisions"] == 0
        assert result["mean_confidence_delta"] is None


def test_millisecond_epochs_use_same_post_freeze_boundary(tmp_path: Path) -> None:
    scorer, service, row = setup_twin(tmp_path)
    before = {**row, "verified_at_epoch": (row["verified_at_epoch"] - 2) * 1000}
    after = {**row, "verified_at_epoch": row["verified_at_epoch"] * 1000}
    result = service.comparison(scorer, decisions=[before, after])
    assert result["compared_decisions"] == 1
    assert result["comparison_points"][0]["verified_at_epoch"] == pytest.approx(row["verified_at_epoch"])


def test_real_soc_adapter_comparison_does_not_copy_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.domains.soc.scorer_adapter import SOCCompoundingScorerAdapter
    from copilot_sdk.graph.memory_store import InMemoryGraphStore
    from copilot_sdk.scoring.scorer import CompoundingScorer

    # Only select the explicit test profile; keep the real scorer and store.
    original = CompoundingScorer.from_preset

    def test_profile(*args: Any, **kwargs: Any) -> Any:
        return original(*args, **{**kwargs, "profile": "test"})

    monkeypatch.setattr(CompoundingScorer, "from_preset", test_profile)
    scorer = SOCCompoundingScorerAdapter(InMemoryGraphStore(domain="soc"))
    service = SOCLearningControlService(FrozenTwinStore(tmp_path))
    snapshot = service.freeze(scorer, {}, 70, scorer.mu)
    vector = [0.5] * scorer.n_factors
    expected = scorer.score(vector, 0)
    before = scorer.mu.copy()
    result = service.comparison(scorer, decisions=[{
        "decision_id": "adapter-verified", "category": scorer.categories[0],
        "factor_vector": vector, "verified_at_epoch": snapshot["snapshot_time"] + 1,
    }])
    assert result["comparison_points"][0]["live"]["confidence"] == pytest.approx(expected.confidence)
    np.testing.assert_array_equal(scorer.mu, before)


@pytest.mark.parametrize("change", [
    {"category": "unknown"}, {"factor_vector": [0.2]},
    {"factor_vector": [float("nan"), 0.2]}, {"factor_vector": "invalid JSON"},
    {"decision_id": None}, {"verified_at_epoch": None},
])
def test_invalid_rows_are_counted_not_fabricated(tmp_path: Path, change: dict[str, Any]) -> None:
    scorer, service, row = setup_twin(tmp_path)
    result = service.comparison(scorer, decisions=[{**row, **change}, row])
    assert result["excluded_comparison_rows"] == 1
    assert result["compared_decisions"] == 1


def test_json_vector_and_demo_snapshot_selection_survive_reload(tmp_path: Path) -> None:
    scorer, service, row = setup_twin(tmp_path)
    for _ in range(8):
        scorer.update(np.array(row["factor_vector"]), 0, 0, True)
    freeze = service.demo_refreeze(scorer, {"components": {"verified_decisions": 8}}, 72)
    row.update(factor_vector="[0.2, 0.2]", verified_at_epoch=freeze["snapshot_time"] + 1)
    restarted = SOCLearningControlService(FrozenTwinStore(tmp_path))
    demo = restarted.comparison(scorer, 72, 9, demo=True, decisions=[row])
    production = restarted.comparison(scorer, 72, decisions=[row])
    assert demo["mean_confidence_delta"] == pytest.approx(0)
    assert production["mean_confidence_delta"] > 0
    assert demo["provenance"]["archived_previous"] is True
    assert demo["evidence_tier"] == "T_S"
