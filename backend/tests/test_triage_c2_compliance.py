from __future__ import annotations

import os
from pathlib import Path
from typing import cast

import numpy as np

from app.domains.soc.scorer_adapter import SOCCompoundingScorerAdapter
from copilot_sdk.graph.memory_store import InMemoryGraphStore
from copilot_sdk.scoring.scorer import CompoundingScorer


def _triage_source() -> str:
    return (Path(__file__).resolve().parents[1] / "app" / "routers" / "triage.py").read_text(
        encoding="utf-8"
    )


def _centroid_query_source() -> str:
    source = _triage_source()
    start = source.index("if wu and wu.centroid_update is not None:")
    end = source.index("centroid_update_payload = {", start)
    return source[start:end]


def _seed_decision(store: InMemoryGraphStore) -> str:
    return cast(str, store.write_decision(
        "soc",
        category="credential_access",
        action="investigate",
        confidence=0.9,
        factors={"factor_0": 0.8, "factor_1": 0.7},
        metadata={"recommended_action": "investigate"},
    ))


def _test_adapter(store: InMemoryGraphStore) -> SOCCompoundingScorerAdapter:
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


def test_centroid_path_does_not_write_d_correct() -> None:
    query_source = _centroid_query_source()

    assert "SET d.correct" not in query_source
    assert "d.correct" not in query_source
    assert "d.verified_at_epoch" not in query_source


def test_outcome_d_correct_survives_centroid_update(tmp_path: Path) -> None:
    previous_outbox = os.environ.get("CI_PERSISTENCE_OUTBOX_PATH")
    os.environ["CI_PERSISTENCE_OUTBOX_PATH"] = str(tmp_path / "soc-c2-outbox.db")
    store = InMemoryGraphStore(domain="soc")
    try:
        decision_id = _seed_decision(store)
        store.write_outcome(
            decision_id,
            actual_action="investigate",
            is_correct=True,
            domain="soc",
            outcome="correct",
            verified_at_epoch=1_700_000_000_000.0,
        )

        scorer = _test_adapter(store)
        scorer.update(
            f=np.full(6, 0.8, dtype=np.float64),
            category_index=0,
            action_index=1,
            correct=True,
            gt_action_index=1,
        )

        decision = store.get_decision(decision_id, domain="soc")
        assert decision is not None
        assert decision["correct"] is True
    finally:
        store.close()
        if previous_outbox is None:
            os.environ.pop("CI_PERSISTENCE_OUTBOX_PATH", None)
        else:
            os.environ["CI_PERSISTENCE_OUTBOX_PATH"] = previous_outbox


def test_centroid_metadata_still_written() -> None:
    query_source = _centroid_query_source()

    assert "SET d.centroid_delta_norm" in query_source
    assert "d.category" in query_source
    assert "d.correct" not in query_source
    assert "d.verified_at_epoch" not in query_source
