from __future__ import annotations

import os
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from app.domains.soc.scorer_adapter import SOCCompoundingScorerAdapter
from copilot_sdk.graph import InMemoryGraphStore
from copilot_sdk.scoring.scorer import CompoundingScorer


@pytest.fixture(autouse=True)
def isolated_outbox(tmp_path: Path) -> Iterator[None]:
    previous = os.environ.get("CI_PERSISTENCE_OUTBOX_PATH")
    os.environ["CI_PERSISTENCE_OUTBOX_PATH"] = str(tmp_path / "soc-outbox.db")
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("CI_PERSISTENCE_OUTBOX_PATH", None)
        else:
            os.environ["CI_PERSISTENCE_OUTBOX_PATH"] = previous


def _adapter(store: InMemoryGraphStore) -> SOCCompoundingScorerAdapter:
    compound = CompoundingScorer.from_preset(
        "soc",
        graph_store=store,
        profile="test",
        enable_rl=False,
    )
    adapter = object.__new__(SOCCompoundingScorerAdapter)
    object.__setattr__(adapter, "_compound", compound)
    object.__setattr__(adapter, "_scorer", compound._scorer)
    return adapter


def _seed_verified(store: InMemoryGraphStore, scorer: CompoundingScorer, count: int = 5) -> None:
    names = list(scorer._preset.shape.factor_names)
    action = scorer._preset.shape.action_names[0]
    category = scorer._preset.shape.category_names[0]
    for index in range(count):
        vector = [0.2 + index * 0.01] * len(names)
        decision_id = store.write_decision(
            "soc",
            category=category,
            action=action,
            confidence=0.9,
            factors=dict(zip(names, vector, strict=False)),
            metadata={
                "decision_id": f"soc-capture-{index}",
                "category_index": 0,
                "recommended_index": 0,
                "factor_vector": vector,
                "probabilities": [0.9, 0.1],
            },
        )
        store.write_outcome(
            decision_id,
            action,
            True,
            domain="soc",
            metadata={"actual_index": 0},
        )


def test_non_scorable_state_capture_writes_type_a_artifacts() -> None:
    store = InMemoryGraphStore(domain="soc")
    adapter = _adapter(store)
    _seed_verified(store, adapter._compound)

    result = adapter.capture_existing_state(
        capture_reason="non_scorable",
        decision_id="soc-routing-1",
    )

    assert result["conservation"] == 1
    assert result["fingerprint"] == 1
    assert result["checkpoint"] == 1
    assert not store._evidence_receipts
    assert all(item["domain"] == "soc" for item in store._conservation_snapshots.values())
    assert all(item["domain"] == "soc" for item in store._fingerprints.values())
    assert all(item["domain"] == "soc" for item in store._protocol_centroid_checkpoints.values())


def test_soc_startup_capture_produces_artifacts() -> None:
    store = InMemoryGraphStore(domain="soc")
    adapter = _adapter(store)
    _seed_verified(store, adapter._compound)

    result = adapter.capture_existing_state(capture_reason="startup_restore")

    assert result["conservation"] == 1
    assert result["fingerprint"] == 1
    assert result["checkpoint"] == 1
    assert not store._evidence_receipts


def test_soc_capture_failure_does_not_block_startup(caplog: pytest.LogCaptureFixture) -> None:
    class FailingStore(InMemoryGraphStore):
        def write_conservation_status(self, *args: Any, **kwargs: Any) -> None:
            raise RuntimeError("conservation unavailable")

        def write_fingerprint(self, *args: Any, **kwargs: Any) -> None:
            raise RuntimeError("fingerprint unavailable")

        def write_centroid_checkpoint(self, *args: Any, **kwargs: Any) -> None:
            raise RuntimeError("checkpoint unavailable")

    store = FailingStore(domain="soc")
    adapter = _adapter(store)
    _seed_verified(store, adapter._compound)

    with caplog.at_level(logging.WARNING):
        result = adapter.capture_existing_state(capture_reason="startup_restore")

    assert result["conservation"] == 0
    assert result["fingerprint"] == 0
    assert result["checkpoint"] == 0
    assert "Persistence failed" in caplog.text
