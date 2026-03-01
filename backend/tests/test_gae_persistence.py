"""
Test: GAE history persists across simulated server restart.

Verifies that save_learning_state() serializes WeightUpdate history and
_load_from_file() reconstructs it, so GAE chart endpoints return data
after a uvicorn --reload.

Run from backend/ directory:
    pytest tests/test_gae_persistence.py -v
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_weight_update(decision_number: int, outcome: int, n_a=4, n_f=6):
    """Return a synthetic WeightUpdate for testing."""
    from gae.learning import WeightUpdate
    return WeightUpdate(
        decision_number=decision_number,
        timestamp=1700000000.0 + decision_number,
        action_index=0,
        action_name="escalate",
        outcome=outcome,
        factor_vector=np.ones((1, n_f), dtype=np.float64) * decision_number,
        delta_applied=np.ones(n_f, dtype=np.float64) * 0.01 * decision_number,
        W_before=np.zeros((n_a, n_f), dtype=np.float64),
        W_after=np.eye(n_a, n_f, dtype=np.float64) * (1.0 + decision_number * 0.1),
        alpha_effective=0.05,
        confidence_at_decision=0.5 + decision_number * 0.05,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_history_survives_save_and_reload(tmp_path):
    """
    Core regression: history=[] after reload was the original bug.

    Steps:
    1. Init a fresh LearningState
    2. Append 3 synthetic WeightUpdates to history
    3. save_learning_state() → writes to tmp file
    4. Call _load_from_file() (simulates server restart)
    5. Assert restored state has len(history)==3 and correct field values
    """
    from app.services import gae_state

    checkpoint = tmp_path / "gae_learning_state.json"

    # Patch the module-level path and singleton
    with patch.object(gae_state, "_STATE_PATH", checkpoint):
        with patch.object(gae_state, "_learning_state", None):
            # Build a fresh state
            gae_state._learning_state = gae_state._make_fresh_state()
            state = gae_state._learning_state

            # Inject synthetic history
            updates = [_make_weight_update(i + 1, outcome=1 if i % 2 == 0 else -1)
                       for i in range(3)]
            state.history = updates
            state.decision_count = 3

            # Save
            gae_state.save_learning_state()

    # Verify checkpoint contains history key
    saved = json.loads(checkpoint.read_text())
    assert "history" in saved, "Checkpoint must contain 'history' key"
    assert len(saved["history"]) == 3, f"Expected 3 entries, got {len(saved['history'])}"

    # Check one entry has expected fields
    entry = saved["history"][0]
    for field in ("decision_number", "timestamp", "action_index", "action_name",
                  "outcome", "alpha_effective", "confidence_at_decision",
                  "factor_vector", "delta_applied", "W_after"):
        assert field in entry, f"Missing field '{field}' in serialized history entry"

    # Reload — simulate server restart
    with patch.object(gae_state, "_STATE_PATH", checkpoint):
        restored = gae_state._load_from_file()

    assert len(restored.history) == 3, (
        f"history should have 3 entries after reload, got {len(restored.history)}"
    )
    assert restored.decision_count == 3

    # Verify field fidelity on first entry
    wu0_orig = updates[0]
    wu0_rest = restored.history[0]

    assert wu0_rest.decision_number == wu0_orig.decision_number
    assert wu0_rest.action_name == wu0_orig.action_name
    assert wu0_rest.outcome == wu0_orig.outcome
    assert abs(wu0_rest.alpha_effective - wu0_orig.alpha_effective) < 1e-9
    assert abs(wu0_rest.confidence_at_decision - wu0_orig.confidence_at_decision) < 1e-9
    np.testing.assert_allclose(wu0_rest.factor_vector, wu0_orig.factor_vector)
    np.testing.assert_allclose(wu0_rest.delta_applied, wu0_orig.delta_applied)
    np.testing.assert_allclose(wu0_rest.W_after, wu0_orig.W_after)

    print("PASS: history survives save/reload")


def test_empty_history_checkpoint_backward_compatible(tmp_path):
    """
    Old checkpoints without 'history' key must still load cleanly (history=[]).
    """
    from app.services import gae_state

    checkpoint = tmp_path / "gae_learning_state.json"

    # Write an old-format checkpoint (no history key)
    old_payload = {
        "W": np.eye(4, 6).tolist(),
        "n_actions": 4,
        "n_factors": 6,
        "factor_names": ["f1", "f2", "f3", "f4", "f5", "f6"],
        "decision_count": 7,
    }
    checkpoint.write_text(json.dumps(old_payload))

    with patch.object(gae_state, "_STATE_PATH", checkpoint):
        restored = gae_state._load_from_file()

    assert restored.history == [], "Old checkpoint should give history=[]"
    assert restored.decision_count == 7
    print("PASS: old checkpoint without history loads cleanly")


def test_chart_endpoints_return_data_after_reload(tmp_path):
    """
    GAE chart endpoints return data (not empty-state placeholders) when
    history is present after reload.

    Uses the trust-curve logic directly (no HTTP) to validate the data path.
    """
    from app.services import gae_state

    checkpoint = tmp_path / "gae_learning_state.json"

    # Build and save state with 5 decisions
    with patch.object(gae_state, "_STATE_PATH", checkpoint):
        with patch.object(gae_state, "_learning_state", None):
            gae_state._learning_state = gae_state._make_fresh_state()
            state = gae_state._learning_state
            state.history = [_make_weight_update(i + 1, outcome=1) for i in range(5)]
            state.decision_count = 5
            gae_state.save_learning_state()

    # Reload
    with patch.object(gae_state, "_STATE_PATH", checkpoint):
        restored = gae_state._load_from_file()

    assert len(restored.history) == 5

    # Simulate what gae/trust-curve endpoint does
    trust = {}
    curves = {}
    for wu in restored.history:
        action = wu.action_name
        if action not in trust:
            trust[action] = 0.50
            curves[action] = []
        trust[action] = min(1.0, trust[action] + 0.03) if wu.outcome == 1 else max(0.0, trust[action] - 0.60)
        curves[action].append({"trust_level": round(trust[action], 4)})

    assert "escalate" in curves, "escalate action should appear in trust curves"
    assert len(curves["escalate"]) == 5
    assert curves["escalate"][-1]["trust_level"] > 0.50, "5 correct decisions → trust should be above initial 0.50"

    # Simulate what gae/before-after endpoint does
    assert len(restored.history) >= 2
    first = restored.history[0]
    latest = restored.history[-1]
    improvement_pp = round((latest.confidence_at_decision - first.confidence_at_decision) * 100, 2)
    assert improvement_pp >= 0, "confidence should not decrease with all-correct outcomes"

    print(f"PASS: chart endpoints return real data after reload (improvement_pp={improvement_pp}pp)")


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
