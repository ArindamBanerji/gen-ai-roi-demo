from __future__ import annotations

import logging
from typing import Any

import pytest

from app.domains.soc.config import SCORER_ACTIONS, SOC_CATEGORIES, SOC_FACTORS
from app.domains.soc.scorer_adapter import SOCCompoundingScorerAdapter
from app.services.graph_store_adapter import GraphStoreAdapter
from copilot_sdk.graph import InMemoryGraphStore
from copilot_sdk.scoring.scorer import CompoundingScorer, _is_verified_decision


pytestmark = pytest.mark.no_data_guard


def _wrapped(store: InMemoryGraphStore) -> GraphStoreAdapter:
    return GraphStoreAdapter(graph_client=object(), store=store)


def _seed_legacy_rows(
    store: InMemoryGraphStore,
    *,
    count: int,
    domain: str = "soc",
    correct: bool = True,
    outcome: str | None = None,
) -> list[str]:
    decision_ids: list[str] = []
    expected_outcome = outcome or ("correct" if correct else "incorrect")
    recommended = SCORER_ACTIONS[0]
    actual = recommended if correct else SCORER_ACTIONS[1]
    for index in range(count):
        decision_id = f"{domain}-legacy-{expected_outcome}-{index}"
        vector = [0.2 + index * 0.01] * len(SOC_FACTORS)
        stored_id = store.write_decision(
            domain,
            category=SOC_CATEGORIES[index % len(SOC_CATEGORIES)],
            action=recommended,
            confidence=0.9,
            factors=dict(zip(SOC_FACTORS, vector, strict=True)),
            metadata={
                "decision_id": decision_id,
                "category_index": index % len(SOC_CATEGORIES),
                "recommended_index": 0,
                "factor_vector": vector,
                "factor_names": list(SOC_FACTORS),
                "probabilities": [0.9, 0.05, 0.03, 0.02],
                "created_at": float(index + 1),
            },
        )
        store.write_outcome(
            stored_id,
            actual,
            correct,
            domain=domain,
            outcome=expected_outcome,
            metadata={"actual_index": 0 if correct else 1, "verified_at": index + 1.5},
        )
        decision_ids.append(stored_id)
    return decision_ids


def _capture_adapter(store: InMemoryGraphStore) -> SOCCompoundingScorerAdapter:
    compound = CompoundingScorer.from_preset(
        "soc",
        graph_store=_wrapped(store),
        profile="test",
        enable_rl=False,
    )
    adapter = object.__new__(SOCCompoundingScorerAdapter)
    object.__setattr__(adapter, "_compound", compound)
    object.__setattr__(adapter, "_scorer", compound._scorer)
    return adapter


def test_legacy_correct_rows_use_canonical_status_and_pass_sdk_predicate() -> None:
    store = InMemoryGraphStore(domain="soc")
    _seed_legacy_rows(store, count=10, correct=True)

    rows = _wrapped(store).get_verified_decisions("soc")

    assert len(rows) == 10
    assert all(row["outcome"] == row["status"] == "confirmed" for row in rows)
    assert all(_is_verified_decision(row) for row in rows)


def test_legacy_incorrect_rows_use_canonical_status_and_pass_sdk_predicate() -> None:
    store = InMemoryGraphStore(domain="soc")
    _seed_legacy_rows(store, count=6, correct=False)

    rows = _wrapped(store).get_verified_decisions("soc")

    assert len(rows) == 6
    assert all(row["outcome"] == row["status"] == "overridden" for row in rows)
    assert all(_is_verified_decision(row) for row in rows)


def test_canonical_outcomes_pass_through_unchanged() -> None:
    store = InMemoryGraphStore(domain="soc")
    _seed_legacy_rows(store, count=1, outcome="confirmed")
    raw = store.get_verified_decisions("soc")

    assert _wrapped(store).get_verified_decisions("soc") == raw


def test_inconsistent_legacy_row_is_excluded_with_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    store = InMemoryGraphStore(domain="soc")
    _seed_legacy_rows(store, count=1, correct=False, outcome="correct")
    _seed_legacy_rows(store, count=1, correct=True, outcome="incorrect")

    with caplog.at_level(logging.WARNING):
        rows = _wrapped(store).get_verified_decisions("soc")

    assert rows == []
    assert caplog.text.count("Excluding inconsistent SOC verified decision") == 2


def test_unknown_outcome_is_excluded_with_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    store = InMemoryGraphStore(domain="soc")
    _seed_legacy_rows(store, count=1, outcome="maybe")

    with caplog.at_level(logging.WARNING):
        rows = _wrapped(store).get_verified_decisions("soc")

    assert rows == []
    assert "Excluding SOC verified decision with unknown outcome" in caplog.text


def test_empty_verified_projection_returns_empty() -> None:
    assert _wrapped(InMemoryGraphStore(domain="soc")).get_verified_decisions("soc") == []


def test_non_soc_rows_pass_through_without_normalization() -> None:
    store = InMemoryGraphStore(domain="dataops")
    _seed_legacy_rows(store, count=1, domain="dataops", outcome="correct")
    raw = store.get_verified_decisions("dataops")

    assert _wrapped(store).get_verified_decisions("dataops") == raw
    assert raw[0]["outcome"] == "correct"


def test_projection_does_not_mutate_stored_legacy_outcomes() -> None:
    store = InMemoryGraphStore(domain="soc")
    _seed_legacy_rows(store, count=2, correct=True)
    before = store.get_verified_decisions("soc")

    projected = _wrapped(store).get_verified_decisions("soc")
    after = store.get_verified_decisions("soc")

    assert all(row["outcome"] == "confirmed" for row in projected)
    assert before == after
    assert all(row["outcome"] == "correct" for row in after)


def test_verified_projection_forwards_pagination_order_and_cursor() -> None:
    class RecordingStore(InMemoryGraphStore):
        call: tuple[Any, ...] | None = None

        def get_verified_decisions(
            self,
            domain: str,
            *,
            offset: int = 0,
            limit: int | None = None,
            chronological: bool = False,
            verified_after: tuple[float, str] | None = None,
        ) -> list[dict[str, Any]]:
            self.call = (domain, offset, limit, chronological, verified_after)
            return []

    store = RecordingStore(domain="soc")
    cursor = (123.5, "soc-42")

    assert _wrapped(store).get_verified_decisions(
        "soc",
        offset=7,
        limit=11,
        chronological=True,
        verified_after=cursor,
    ) == []
    assert store.call == ("soc", 7, 11, True, cursor)


def test_verified_projection_propagates_underlying_exception() -> None:
    class FailingStore(InMemoryGraphStore):
        def get_verified_decisions(self, domain: str, **kwargs: Any) -> list[dict[str, Any]]:
            raise ValueError(f"cannot read {domain}")

    with pytest.raises(ValueError, match="cannot read soc"):
        _wrapped(FailingStore(domain="soc")).get_verified_decisions("soc")


def test_state_capture_persists_conservation_and_fingerprint_from_legacy_rows() -> None:
    store = InMemoryGraphStore(domain="soc")
    _seed_legacy_rows(store, count=12, correct=True)
    adapter = _capture_adapter(store)

    result = adapter.capture_existing_state(capture_reason="startup_restore")

    assert result["conservation"] == 1
    assert result["fingerprint"] == 1
    assert store._conservation_snapshots
    assert store._fingerprints
    fingerprint = next(iter(store._fingerprints.values()))
    assert fingerprint["factor_names"]

