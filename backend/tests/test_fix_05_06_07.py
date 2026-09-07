"""
Regression tests for FIX-05, FIX-06, FIX-07 (P1 bugs from adversarial bug hunt v2).

FIX-05: Simulation must not mutate production LearningState.

FIX-06: Empty alert_pool must not crash with ZeroDivisionError; must return
        a valid SimulationResult gracefully.

FIX-07: LearningHealthMonitor.evaluate() must not raise TypeError when
        state.history is explicitly set to None.
"""

from __future__ import annotations

import numpy as np
import pytest
import ast
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import app.services.simulation as sim_mod
from app.domains.soc.scorer_adapter import SOCCompoundingScorerAdapter
from app.services.simulation import SimulationOrchestrator
from app.services.learning_health import LearningHealthMonitor


def _profile_scorer_with_graph_store(graph_store):
    profile_scorer = object.__new__(SOCCompoundingScorerAdapter)
    object.__setattr__(profile_scorer, "_compound", SimpleNamespace(graph_store=graph_store))
    object.__setattr__(profile_scorer, "_scorer", MagicMock())
    return profile_scorer


# ===========================================================================
# FIX-05: Simulation must not mutate production learning state
# ===========================================================================

def test_simulation_learning_path_does_not_reacquire_or_snapshot_production():
    source = open(sim_mod.__file__, encoding="utf-8").read()
    tree = ast.parse(source)
    scorer_calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "get_profile_scorer"
    ]
    assert len(scorer_calls) == 1
    assert scorer_calls[0].lineno < 331
    assert "maybe_write_centroid_snapshot" not in source
    assert "Simulation clone is attached to the production ProfileScorer" in source

@pytest.mark.asyncio
async def test_simulation_does_not_mutate_production_state():
    """
    Production LearningState is isolated via a local deepcopy (sim_ls), so
    simulation updates must leave the original state unchanged.
    """
    mock_ls = MagicMock()
    mock_ls.W = np.zeros((4, 6))
    mock_ls.n_actions = 4
    mock_ls.n_factors = 6
    mock_ls.factor_names = [f"f{i}" for i in range(6)]
    mock_ls.profile = SimpleNamespace(
        learning_rate=0.05,
        penalty_ratio=-0.25,
        factor_decay_classes={},
        decay_class_rates={"standard": 0.02},
        epsilon_default=0.02,
    )
    mock_ls.history = []
    mock_ls.expansion_history = []
    mock_ls.discount_strength = 0.0
    mock_ls.epsilon_vector = np.full(6, 0.02)
    mock_ls.dimension_metadata = []
    mock_ls.pending_validations = []
    mock_ls.decision_count = 99
    before_w = mock_ls.W.copy()
    before_history = list(mock_ls.history)
    before_expansion_history = list(mock_ls.expansion_history)
    before_discount_strength = mock_ls.discount_strength
    before_epsilon_vector = mock_ls.epsilon_vector.copy()
    before_dimension_metadata = list(mock_ls.dimension_metadata)
    before_pending_validations = list(mock_ls.pending_validations)
    before_decision_count = mock_ls.decision_count

    mock_scoring = MagicMock()
    mock_scoring.selected_action = "suppress"
    mock_scoring.confidence = 0.75

    mock_graph = MagicMock()
    mock_graph.get_alert = AsyncMock(return_value=None)
    mock_graph.get_security_context = AsyncMock(return_value=None)
    mock_graph.run_query = AsyncMock(return_value=[])

    mock_eb = MagicMock()
    mock_eb.emit = AsyncMock()
    graph_store = MagicMock()
    profile_scorer = _profile_scorer_with_graph_store(graph_store)

    factor_vec = np.array([0.5, 0.3, 0.7, 0.2, 0.6, 0.4])

    with patch.object(sim_mod, "get_learning_state", return_value=mock_ls), \
         patch("app.services.gae_state.get_profile_scorer", return_value=profile_scorer), \
         patch.object(sim_mod, "event_bus", mock_eb), \
         patch.object(sim_mod, "score_alert", return_value=mock_scoring), \
         patch.object(sim_mod, "compute_factor_vector",
                      new_callable=AsyncMock, return_value=factor_vec), \
         patch.object(sim_mod, "audit_record_decision",
                      new_callable=AsyncMock, return_value={}), \
         patch("app.db.graph_client.graph_client", mock_graph), \
         patch("app.services.situation.analyze_situation",
               return_value=MagicMock(situation_type="unknown")):

        orch = SimulationOrchestrator(MagicMock(), MagicMock(), MagicMock())
        alert_pool = [{
            "alert_id": "FB-CA-001",
            "category": "credential_access",
            "ground_truth_action": "suppress",
        }]
        await orch.run(n_decisions=1, alert_pool=alert_pool, speed_ms=0)

    np.testing.assert_allclose(mock_ls.W, before_w)
    assert mock_ls.history == before_history
    assert mock_ls.expansion_history == before_expansion_history
    assert mock_ls.discount_strength == before_discount_strength
    np.testing.assert_allclose(mock_ls.epsilon_vector, before_epsilon_vector)
    assert mock_ls.dimension_metadata == before_dimension_metadata
    assert mock_ls.pending_validations == before_pending_validations
    assert mock_ls.decision_count == before_decision_count


# ===========================================================================
# FIX-06: Empty alert pool must return gracefully, not crash
# ===========================================================================

@pytest.mark.asyncio
async def test_simulation_empty_pool_returns_gracefully():
    """
    alert_pool=[] must return a zero-decision SimulationResult without raising
    ZeroDivisionError (step % len(alert_pool) with len==0).
    """
    mock_ls = MagicMock()
    mock_ls.W = np.zeros((4, 6))
    mock_ls.n_actions = 4
    mock_ls.n_factors = 6
    mock_ls.factor_names = [f"f{i}" for i in range(6)]
    mock_ls.profile = SimpleNamespace(
        learning_rate=0.05,
        penalty_ratio=-0.25,
        factor_decay_classes={},
        decay_class_rates={"standard": 0.02},
        epsilon_default=0.02,
    )
    mock_ls.history = []
    mock_ls.expansion_history = []
    mock_ls.discount_strength = 0.0
    mock_ls.epsilon_vector = np.full(6, 0.02)
    mock_ls.dimension_metadata = []
    mock_ls.pending_validations = []
    mock_ls.decision_count = 0
    profile_scorer = _profile_scorer_with_graph_store(MagicMock())

    with patch.object(sim_mod, "get_learning_state", return_value=mock_ls), \
         patch("app.services.gae_state.get_profile_scorer", return_value=profile_scorer):

        orch = SimulationOrchestrator(MagicMock(), MagicMock(), MagicMock())
        result = await orch.run(n_decisions=10, alert_pool=[], speed_ms=0)

    assert result.n_decisions == 0
    assert result.overall_accuracy == 0.0
    assert result.category_accuracy == {}
    assert result.weight_trajectory == []
    assert result.experiment_log == []


# ===========================================================================
# FIX-07: history=None must not raise TypeError in health monitor
# ===========================================================================

@pytest.mark.asyncio
async def test_evaluate_handles_none_history():
    """
    LearningHealthMonitor.evaluate() must not raise TypeError when
    state.history is explicitly None (len(None) was evaluated eagerly).
    """
    state = SimpleNamespace(decision_count=5, history=None)

    with patch("app.services.learning_health.get_learning_state", return_value=state):
        result = await LearningHealthMonitor.evaluate(graph_service=None)

    assert result["status"] in ("CALIBRATING", "GREEN", "AMBER", "RED")
    assert "signal" in result
    assert "conservation" in result
