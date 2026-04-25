"""
test_triggered_evolution.py — TRIGGERED_EVOLUTION edge creation tests.

Tests that the triage outcome path creates (Decision)-[:TRIGGERED_EVOLUTION]->
(EvolutionEvent) edges for verified correct outcomes on SCORER_ACTIONS.
These edges feed PatternHistoryFactorComputer (CLAIM-W2, +10.13pp accuracy).

Run from backend/:
    pytest tests/test_triggered_evolution.py -v
"""
import asyncio
import contextlib
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.domains.soc.config import SCORER_ACTIONS
from app.models.schemas import OutcomeRequest
from app.routers.triage import report_decision_outcome

_SCORER_ACTION  = list(SCORER_ACTIONS)[0]   # "escalate"
_ROUTING_ACTION = "refer_to_analyst"
_DECISION_ID    = "DEC-TRIAGETEST-001"
_ALERT_ID       = "ALERT-TRIAGETEST-001"
_CATEGORY       = "credential_access"
_FV_JSON        = json.dumps([0.7, 0.8, 0.5, 0.4, 0.6, 0.9])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_neo4j(action: str = _SCORER_ACTION, raise_on_evolution: bool = False):
    """
    Fake neo4j client that:
    - Returns Decision data when the factor_vector query runs.
    - Captures all run_query calls that mention TRIGGERED_EVOLUTION.
    - Optionally raises on the TRIGGERED_EVOLUTION write to test resilience.
    """
    evo_calls: list[str] = []

    async def _run(query, params=None):
        if "TRIGGERED_EVOLUTION" in query:
            evo_calls.append(query)
            if raise_on_evolution:
                raise RuntimeError("Simulated graph write failure")
        if "factor_vector" in query:
            return [{
                "factor_vector": _FV_JSON,
                "action":        action,
                "confidence":    0.85,
                "category":      _CATEGORY,
                "alert_type":    _CATEGORY,
            }]
        return []

    client           = AsyncMock()
    client.run_query.side_effect = _run
    client._evo      = evo_calls
    return client


def _make_learning_state():
    ls                = MagicMock()
    ls.decision_count = 100
    ls.W              = np.ones((4, 6))
    ls.update.return_value = None   # wu=None → skips centroid/snapshot blocks
    return ls


def _make_outcome_result():
    r = MagicMock()
    r.model_dump.return_value = {
        "graph_updates": [], "consequence": "stable", "narrative": "ok",
    }
    return r


def _make_request(outcome: str = "correct") -> OutcomeRequest:
    return OutcomeRequest(
        alert_id    = _ALERT_ID,
        decision_id = _DECISION_ID,
        outcome     = outcome,
    )


def _patches(neo4j, ls):
    return [
        patch("app.routers.triage.neo4j_client",        neo4j),
        patch("app.routers.triage.get_feedback_status",  return_value={"has_feedback": False}),
        patch("app.routers.triage.process_outcome",      return_value=_make_outcome_result()),
        patch("app.routers.triage.event_bus.emit",       new_callable=AsyncMock),
        patch("app.routers.triage.get_learning_state",   return_value=ls),
        patch("app.routers.triage.save_learning_state"),
        patch("app.framework.audit.record_outcome",      new_callable=AsyncMock,
              return_value={"hash": "fakehash", "chain_index": 0}),
        patch("app.state.graph_snapshot.get_snapshot",   return_value=MagicMock()),
        patch("app.services.gae_state.get_mu_zero",      return_value=None),
    ]


async def _call(neo4j, outcome: str = "correct") -> dict:
    ls = _make_learning_state()
    with contextlib.ExitStack() as stack:
        for p in _patches(neo4j, ls):
            stack.enter_context(p)
        return await report_decision_outcome(_make_request(outcome))


def _run(coro):
    return asyncio.run(coro)


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_correct_outcome_creates_triggered_evolution_edge():
    """
    Verified correct outcome on a SCORER_ACTION must create exactly one
    (Decision)-[:TRIGGERED_EVOLUTION]->(EvolutionEvent) write in the graph.
    """
    neo4j = _make_neo4j(action=_SCORER_ACTION)
    _run(_call(neo4j, outcome="correct"))
    assert len(neo4j._evo) == 1, (
        f"Expected 1 TRIGGERED_EVOLUTION write, got {len(neo4j._evo)}"
    )
    assert "EvolutionEvent" in neo4j._evo[0], (
        "TRIGGERED_EVOLUTION query must CREATE an EvolutionEvent node"
    )


def test_incorrect_outcome_does_not_create_evolution_edge():
    """
    Verified incorrect outcome must NOT create a TRIGGERED_EVOLUTION edge.
    Incorrect outcomes do not encode positive patterns for the flywheel.
    """
    neo4j = _make_neo4j(action=_SCORER_ACTION)
    _run(_call(neo4j, outcome="incorrect"))
    assert len(neo4j._evo) == 0, (
        f"Expected 0 TRIGGERED_EVOLUTION writes for incorrect outcome, "
        f"got {len(neo4j._evo)}"
    )


def test_routing_action_does_not_create_evolution_edge():
    """
    refer_to_analyst is a routing decision, not a SCORER_ACTION.
    TRIGGERED_EVOLUTION edges must NOT be created for it.
    """
    neo4j = _make_neo4j(action=_ROUTING_ACTION)
    _run(_call(neo4j, outcome="correct"))
    assert len(neo4j._evo) == 0, (
        f"Expected 0 TRIGGERED_EVOLUTION writes for routing action "
        f"'{_ROUTING_ACTION}', got {len(neo4j._evo)}"
    )


def test_evolution_edge_has_required_properties():
    """
    The TRIGGERED_EVOLUTION Cypher write must include all required properties:
    timestamp_epoch, decision_id, category, correct=true, action.
    PatternHistoryFactorComputer reads d.category, d.verified_correct=true,
    d.factor_snapshot, d.decision_number, and d.action_index.
    """
    neo4j = _make_neo4j(action=_SCORER_ACTION)
    _run(_call(neo4j, outcome="correct"))
    assert len(neo4j._evo) == 1, "Expected exactly one TRIGGERED_EVOLUTION write"
    q = neo4j._evo[0]
    for prop in ("timestamp_epoch", "decision_id", "category", "correct", "action"):
        assert prop in q, (
            f"Required property '{prop}' missing from TRIGGERED_EVOLUTION query"
        )
    assert _DECISION_ID in q, f"decision_id {_DECISION_ID!r} not embedded in query"
    assert _CATEGORY    in q, f"category {_CATEGORY!r} not embedded in query"
    assert "true"       in q.lower(), "correct:true not present in query"
    assert "verified_correct" in q, (
        "SET d.verified_correct must be present so PatternHistoryFactorComputer "
        "can find this Decision via d.verified_correct = true"
    )
    assert "action_index" in q, (
        "SET d.action_index must be present — PatternHistoryFactorComputer "
        "filters by d.action_index = $action_index in its action-specific path"
    )
    assert "factor_snapshot" in q, (
        "SET d.factor_snapshot must be present — PatternHistoryFactorComputer "
        "reads d.factor_snapshot[3] for the pattern_history feature value"
    )
    assert "decision_number" in q, (
        "SET d.decision_number must be present — used for recency weighting "
        "in PatternHistoryFactorComputer"
    )


def test_evolution_edge_failure_does_not_block_outcome():
    """
    When the TRIGGERED_EVOLUTION graph write raises, the outcome response
    must still succeed. Edge creation is fire-and-forget — non-blocking.
    """
    neo4j = _make_neo4j(action=_SCORER_ACTION, raise_on_evolution=True)
    result = _run(_call(neo4j, outcome="correct"))
    assert isinstance(result, dict), (
        f"Expected dict response even after edge write failure, got {type(result)}"
    )
    assert "graph_updates" in result or "centroid_update" in result, (
        "Response must contain expected outcome fields after edge write failure"
    )
    assert len(neo4j._evo) == 1, (
        "TRIGGERED_EVOLUTION write must be attempted (so we know the failure was real)"
    )
