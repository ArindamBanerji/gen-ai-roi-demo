from __future__ import annotations

from typing import Any

from support import SOCTriageHarness


_FACTORS = {f"f{i}": 0.1 * (i + 1) for i in range(6)}


def _add(harness: SOCTriageHarness, **kwargs: Any) -> str:
    return harness.add_decision(
        category="credential_access",
        action="escalate",
        factors=_FACTORS,
        **kwargs,
    )


def test_harness_decision_visible_through_store() -> None:
    harness = SOCTriageHarness()
    decision_id = _add(harness)

    decision = harness.get_decision(decision_id)

    assert decision is not None
    assert decision["domain"] == "soc"
    assert decision["category"] == "credential_access"


def test_harness_write_outcome_sets_correct() -> None:
    harness = SOCTriageHarness()
    decision_id = _add(harness)

    harness.store.write_outcome(
        decision_id,
        "escalate",
        True,
        domain="soc",
    )
    decision = harness.get_decision(decision_id)

    assert decision is not None
    assert decision["correct"] is True
    assert decision["status"] in ("confirmed", "overridden")


def test_harness_unknown_decision_returns_none() -> None:
    harness = SOCTriageHarness()

    assert harness.get_decision("nonexistent-id") is None


def test_harness_non_decision_client_independent() -> None:
    harness = SOCTriageHarness()
    harness.graph_client._alerts["alert-1"] = {"category": "credential_access"}

    assert harness.get_decision("alert-1") is None


def test_harness_outbox_isolated() -> None:
    first = SOCTriageHarness()
    second = SOCTriageHarness()
    decision_id = _add(first)

    assert second.get_decision(decision_id) is None
