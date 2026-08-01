"""
test_triggered_evolution.py -- TRIGGERED_EVOLUTION edge creation tests.

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
from typing import Any, cast
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

def _make_learning_state():
    ls                = MagicMock()
    ls.decision_count = 100
    ls.W              = np.ones((4, 6))
    ls.update.return_value = None   # wu=None -> skips centroid/snapshot blocks
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
        outcome     = cast(Any, outcome),
    )


def _patches(ls):
    return [
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


async def _call(harness, *, action: str = _SCORER_ACTION, outcome: str = "correct") -> dict[str, Any]:
    harness.add_decision(
        decision_id=_DECISION_ID,
        category=_CATEGORY,
        action=action,
        confidence=0.85,
        factors={f"f{i}": value for i, value in enumerate([0.7, 0.8, 0.5, 0.4, 0.6, 0.9])},
        factor_vector=_FV_JSON,
        alert_type=_CATEGORY,
    )
    ls = _make_learning_state()
    with contextlib.ExitStack() as stack:
        for p in _patches(ls):
            stack.enter_context(p)
        return cast(dict[str, Any], await report_decision_outcome(_make_request(outcome)))
    raise AssertionError("unreachable")


def _run(coro):
    return asyncio.run(coro)


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_correct_outcome_creates_triggered_evolution_edge(soc_triage_harness):
    """
    Verified correct outcome on a SCORER_ACTION must create exactly one
    (Decision)-[:TRIGGERED_EVOLUTION]->(EvolutionEvent) write in the graph.
    """
    _run(_call(soc_triage_harness, outcome="correct"))
    events = soc_triage_harness.graph_client._evolution_events
    assert len(events) == 1, (
        f"Expected 1 TRIGGERED_EVOLUTION write, got {len(events)}"
    )
    assert events[0]["properties"]


def test_incorrect_outcome_does_not_create_evolution_edge(soc_triage_harness):
    """
    Verified incorrect outcome must NOT create a TRIGGERED_EVOLUTION edge.
    Incorrect outcomes do not encode positive patterns for the flywheel.
    """
    _run(_call(soc_triage_harness, outcome="incorrect"))
    assert len(soc_triage_harness.graph_client._evolution_events) == 0, (
        f"Expected 0 TRIGGERED_EVOLUTION writes for incorrect outcome, "
        f"got {len(soc_triage_harness.graph_client._evolution_events)}"
    )


def test_routing_action_does_not_create_evolution_edge(soc_triage_harness):
    """
    refer_to_analyst is a routing decision, not a SCORER_ACTION.
    TRIGGERED_EVOLUTION edges must NOT be created for it.
    """
    _run(_call(soc_triage_harness, action=_ROUTING_ACTION, outcome="correct"))
    assert len(soc_triage_harness.graph_client._evolution_events) == 0, (
        f"Expected 0 TRIGGERED_EVOLUTION writes for routing action "
        f"'{_ROUTING_ACTION}', got {len(soc_triage_harness.graph_client._evolution_events)}"
    )


def test_evolution_edge_has_required_properties(soc_triage_harness):
    """
    The TRIGGERED_EVOLUTION Cypher write must include all required properties:
    timestamp_epoch, decision_id, category, correct=true, action.
    PatternHistoryFactorComputer reads d.category, d.verified_correct=true,
    d.factor_snapshot, d.decision_number, and d.action_index.
    """
    _run(_call(soc_triage_harness, outcome="correct"))
    events = soc_triage_harness.graph_client._evolution_events
    assert len(events) == 1, "Expected exactly one TRIGGERED_EVOLUTION write"
    properties = events[0]["properties"]
    for prop in ("timestamp_epoch", "decision_id", "category", "correct", "action"):
        assert prop in properties, (
            f"Required property '{prop}' missing from TRIGGERED_EVOLUTION query"
        )
    for prop in ("verified_correct", "action_index", "factor_snapshot", "decision_number"):
        assert prop in properties
    decision = soc_triage_harness.get_decision(_DECISION_ID)
    assert decision is not None
    assert decision["correct"] is True
    assert decision["category"] == _CATEGORY
    assert decision["recommended_action"] == _SCORER_ACTION


def test_evolution_edge_failure_does_not_block_outcome(soc_triage_harness):
    """
    When the TRIGGERED_EVOLUTION graph write raises, the outcome response
    must still succeed. Edge creation is fire-and-forget -- non-blocking.
    """
    soc_triage_harness.graph_client.fail_triggered_evolution = True
    result = _run(_call(soc_triage_harness, outcome="correct"))
    assert isinstance(result, dict), (
        f"Expected dict response even after edge write failure, got {type(result)}"
    )
    assert "graph_updates" in result or "centroid_update" in result, (
        "Response must contain expected outcome fields after edge write failure"
    )
    assert any("TRIGGERED_EVOLUTION" in query for query, _ in soc_triage_harness.graph_client._queries)
