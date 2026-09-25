import sqlite3

import numpy as np
import pytest
from gae import ProfileScorer

from app.services.gae_state import guarded_update, reset_spike_counter, set_volume_spike
from app.services.rl_engine import CreditAssigner

from copilot_sdk.scoring.composite_gate import CompositeGate


def _scorer() -> ProfileScorer:
    scorer = ProfileScorer(
        mu=np.full((2, 2, 4), 0.5, dtype=float),
        actions=["block", "escalate"],
        categories=["category_a", "category_b"],
        auto_pause_on_amber=True,
    )
    scorer.set_conservation_status("GREEN")
    set_volume_spike(False)
    reset_spike_counter()
    return scorer


def _factors() -> np.ndarray:
    return np.array([0.8, 0.6, 0.4, 0.2], dtype=float)


def test_pipeline_with_real_scorer(tmp_path):
    scorer = _scorer()
    gate = CompositeGate()
    db = sqlite3.connect(tmp_path / "pipeline.sqlite3")
    db.execute("CREATE TABLE outcomes (correct INTEGER NOT NULL)")

    scored = scorer.score(_factors(), category_index=0)
    update = guarded_update(
        scorer,
        f=_factors(),
        category_index=0,
        action_index=int(scored.action_index),
        correct=True,
        category_name="category_a",
    )
    db.execute("INSERT INTO outcomes VALUES (1)")
    db.commit()
    gate_result = gate.evaluate(
        alpha_q_v=1.0,
        theta_min=None,
        rolling_accuracy=1.0,
        baseline=1.0,
        verified_outcomes=[True],
    )
    db.close()
    assert update is not None
    assert gate_result["status"] == "GREEN"


def test_pipeline_gate_blocks_bad_outcome():
    scorer = _scorer()
    gate = CompositeGate()
    bad_outcomes = [True] * 20 + [False] * 20
    gate_result = gate.evaluate(
        alpha_q_v=1.0,
        theta_min=None,
        rolling_accuracy=0.0,
        baseline=1.0,
        verified_outcomes=bad_outcomes,
    )
    assert gate_result["g_rate"]["active"] is True
    scorer.set_conservation_status("RED")
    assert (
        guarded_update(
            scorer,
            f=_factors(),
            category_index=0,
            action_index=0,
            correct=False,
            category_name="category_a",
        )
        is None
    )


def test_pipeline_credit_assignment_real():
    scorer = _scorer()
    attribution = CreditAssigner().compute_factor_attribution(
        scorer, _factors().tolist(), 0, 0, 1.0
    )
    assert len(attribution) == 4
    assert all(value is not None and np.isfinite(value) for value in attribution.values())


def test_pipeline_conservation_state_updates(tmp_path):
    db = sqlite3.connect(tmp_path / "outcomes.sqlite3")
    db.execute("CREATE TABLE outcomes (correct INTEGER NOT NULL)")
    db.executemany("INSERT INTO outcomes VALUES (?)", [(1,), (1,), (0,), (1,)])
    db.commit()
    verified_count = db.execute("SELECT count(*) FROM outcomes").fetchone()[0]
    gate_result = CompositeGate().evaluate(
        alpha_q_v=1.0,
        theta_min=None,
        rolling_accuracy=0.75,
        baseline=0.75,
        verified_outcomes=[True, True, False, True],
    )
    db.close()
    assert verified_count == 4
    assert gate_result["g_rate"]["short_window_count"] == 4


def test_pipeline_centroid_changes():
    scorer = _scorer()
    before = scorer.centroids.copy()
    for _ in range(5):
        update = guarded_update(
            scorer,
            f=_factors(),
            category_index=0,
            action_index=0,
            correct=True,
            category_name="category_a",
        )
        assert update is not None
    assert not np.array_equal(before, scorer.centroids)
