from __future__ import annotations

import asyncio
from pathlib import Path

from ci_platform.graph.age_graph_store import AGEGraphStore
from ci_platform.audit.evidence_ledger import OutcomeEntry

from app.framework.audit import _LEDGER, _SITUATION_TYPES, record_decision, record_outcome
from app.framework.feedback_store import FEEDBACK_GIVEN


def _run(coro):
    return asyncio.run(coro)


def _store(soc_stress_test_graph) -> AGEGraphStore:
    dsn, graph_name = soc_stress_test_graph
    return AGEGraphStore(dsn=dsn, graph_name=graph_name)


def _write_decision(store: AGEGraphStore) -> str:
    return str(store.write_decision(
        domain="soc",
        category="test",
        action="approve",
        confidence=0.9,
        factors={"risk": 0.1},
    ))


def test_outcome_sets_d_correct_via_contract(soc_stress_test_graph) -> None:
    store = _store(soc_stress_test_graph)
    try:
        decision_id = _write_decision(store)
        store.write_outcome(
            decision_id,
            actual_action="approve",
            is_correct=True,
            domain="soc",
            outcome="correct",
            quality_signal=1.0,
        )

        decision = store.get_decision(decision_id, domain="soc")
        assert decision is not None
        assert decision["correct"] is True
        assert decision["status"] in ("confirmed", "overridden")
    finally:
        store.close()


def test_outcome_no_raw_cypher_set_correct() -> None:
    triage_path = Path(__file__).resolve().parents[1] / "app" / "routers" / "triage.py"
    source = triage_path.read_text(encoding="utf-8")
    assert "SET d.correct" not in source
    assert ".write_outcome(" in source


def test_outcome_audit_chain_still_called() -> None:
    _LEDGER._entries.clear()
    _SITUATION_TYPES.clear()
    FEEDBACK_GIVEN.clear()
    decision = _run(
        record_decision(
            alert_id="SOC-AUDIT-001",
            situation_type="contract_test",
            action_taken="approve",
            factors=["risk"],
            confidence=0.9,
        )
    )

    outcome = _run(record_outcome(decision["id"], "correct"))

    assert outcome is not None
    assert any(
        isinstance(entry, OutcomeEntry)
        and entry.decision_id == decision["id"]
        and entry.outcome == "correct"
        for entry in _LEDGER.entries()
    )


def test_outcome_quality_signal_preserved(soc_stress_test_graph) -> None:
    store = _store(soc_stress_test_graph)
    try:
        decision_id = _write_decision(store)
        store.write_outcome(
            decision_id,
            actual_action="review",
            is_correct=False,
            domain="soc",
            outcome="incorrect",
            quality_signal=0.0,
        )

        decision = store.get_decision(decision_id, domain="soc")
        assert decision is not None
        assert decision["quality_signal"] == 0.0
    finally:
        store.close()


def test_outcome_verified_at_epoch_set(soc_stress_test_graph) -> None:
    store = _store(soc_stress_test_graph)
    try:
        decision_id = _write_decision(store)
        expected_epoch = 1_700_000_000_000.0
        store.write_outcome(
            decision_id,
            actual_action="approve",
            is_correct=True,
            domain="soc",
            verified_at_epoch=expected_epoch,
        )

        decision = store.get_decision(decision_id, domain="soc")
        assert decision is not None
        assert decision["verified_at_epoch"] == expected_epoch
    finally:
        store.close()
