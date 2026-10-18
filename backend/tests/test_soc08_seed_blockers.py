"""SOC-08 regressions with real scoring, authority, graph and snapshot stores."""
from __future__ import annotations

import asyncio
import importlib.util
import os
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from fastapi import HTTPException

from app.routers.soc_learning import (
    DemoRefreezeRequest, demo_comparison_enabled, demo_refreeze,
)
from app.services.authority_ladder import AuthorityManager, GraphPromotionStore
from app.services.authority_ladder import AuthorityDecision
from app.services.gae_state import guarded_update, persist_soc_outcome_and_centroid
from app.services.soc_learning_control import SOCLearningControlService
from app.routers.triage import _referral_response, _verified_learning_action
from gae.referral import ReferralDecision
from ci_platform.audit.evidence_ledger import EvidenceLedger
from copilot_sdk.graph.protocol import ProtocolV2GraphStore
from copilot_sdk.scoring.scorer import CompoundingScorer
from copilot_sdk.graph import InMemoryGraphStore
from copilot_sdk.twin import FrozenTwinStore
from support.real_graph import SOCGraphFixture

pytestmark = pytest.mark.no_data_guard
VECTOR = np.array([0.5, 0.8, 0.0, 0.4, 0.7, 1.0])


@pytest.fixture
def twin_graph() -> InMemoryGraphStore:
    return InMemoryGraphStore()


@pytest.mark.parametrize("allowed", [True, False])
def test_authority_veto_is_reflected_without_changing_gate_decisions(allowed: bool) -> None:
    referral = ReferralDecision(should_refer=False)
    authority = AuthorityDecision(
        category="credential_access", authority="observed", conservation="GREEN",
        allowed=allowed, reason=None if allowed else "authority_not_auto_approved",
        would_have_action="suppress",
    )
    body = _referral_response(referral, authority)
    assert body["should_refer"] is (not allowed)
    assert referral.should_refer is False and authority.allowed is allowed
    if allowed:
        assert body["reasons"] == []
        assert body["audit_summary"] == referral.audit_summary
        assert "authority_veto" not in body
    else:
        assert body["reasons"] == ["authority_not_auto_approved"]
        assert "authority veto" in body["audit_summary"]
        assert body["authority_veto"] == authority.to_dict()


@pytest.fixture(autouse=True)
def isolated_outbox(tmp_path: Path) -> Iterator[None]:
    previous = os.environ.get("CI_PERSISTENCE_OUTBOX_PATH")
    os.environ["CI_PERSISTENCE_OUTBOX_PATH"] = str(tmp_path / "outbox")
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("CI_PERSISTENCE_OUTBOX_PATH", None)
        else:
            os.environ["CI_PERSISTENCE_OUTBOX_PATH"] = previous


def _seed_module() -> Any:
    path = Path(__file__).resolve().parents[2] / "scripts/preseed_demo_scenarios.py"
    spec = importlib.util.spec_from_file_location("soc08_seed", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _decision(
    store: ProtocolV2GraphStore, scorer: Any, action: str, *,
    category_index: int = 0, original_action: str | None = None,
) -> str:
    """Persist the full governed input needed for frozen/live comparison."""
    scored = scorer.score(VECTOR, category_index)
    decision_id = store.generate_decision_id("soc")
    metadata: dict[str, Any] = {"planted": True}
    if original_action is not None:
        metadata["original_action"] = original_action
    store.write_governed_decision(
        decision_id=decision_id, domain="soc", category=scorer.categories[category_index],
        category_index=category_index, recommended_action=action,
        recommended_index=scorer.actions.index(action) if action in scorer.actions else -1,
        confidence=float(scored.confidence), probabilities=scored.probabilities.tolist(),
        factor_vector=VECTOR.tolist(), factor_names=[f"f{i}" for i in range(len(VECTOR))],
        metadata=metadata,
    )
    return str(decision_id)


def test_ninety_verified_referrals_do_not_change_geometry(tmp_path: Path, twin_graph: InMemoryGraphStore) -> None:
    store = InMemoryGraphStore(domain="soc")
    compound = CompoundingScorer.from_preset("soc", graph_store=store, profile="test", enable_rl=False)
    scorer = compound._scorer
    authority = AuthorityManager(store=GraphPromotionStore(twin_graph))
    service = SOCLearningControlService(FrozenTwinStore(twin_graph, "soc"))
    freeze = service.freeze(scorer, {}, 70, scorer.mu)
    original = scorer.mu.copy()
    try:
        scored = scorer.score(VECTOR, 0)
        assert scored.action_name == "monitor"
        assert scored.confidence > 0.62
        veto = authority.evaluate("credential_access", scored.action_name, "GREEN")
        assert not veto.allowed
        assert veto.reason == "authority_not_auto_approved"
        for action in scorer.actions:
            assert authority.evaluate("credential_access", action, "GREEN").reason == "authority_not_auto_approved"
        for _ in range(90):
            decision_id = _decision(store, scorer, "refer_to_analyst")
            store.write_outcome(decision_id, "monitor", True, domain="soc",
                                verified_at_epoch=freeze["snapshot_time"] + 1)
        rows = store.get_decisions("soc", limit=100)
        assert store.count_verified("soc") == 90
        comparison = service.comparison(scorer, decisions=rows)
        assert comparison["compared_decisions"] == 90
        assert comparison["mean_confidence_delta"] == 0
        np.testing.assert_array_equal(scorer.mu, original)
        assert _seed_module().twin_learning_failure(200, {
            "centroid_update": None, "l5_centroid_persisted": False,
            "l5_persistence_skipped_reason": "routing_action_not_scorable",
        }) == "routing_action_not_scorable"
    finally:
        store.close()
        authority.store.close()


def test_real_guarded_update_and_checkpoint_survive_reload(age_graph: SOCGraphFixture, twin_graph: InMemoryGraphStore) -> None:
    store = age_graph.store
    compound = CompoundingScorer.from_preset("soc", graph_store=store, profile="test", enable_rl=False)
    scorer = compound._scorer
    service = SOCLearningControlService(FrozenTwinStore(twin_graph, "soc"))
    freeze = service.freeze(scorer, {}, 70, scorer.mu)
    snapshot_bytes = FrozenTwinStore(twin_graph, "soc").load("soc").to_json()
    decision_id = _decision(store, scorer, "monitor")
    action_index = scorer.actions.index("monitor")
    before = scorer.mu[0, action_index].tolist()
    try:
        scorer.set_conservation_status("RED")
        assert guarded_update(scorer, VECTOR, 0, action_index, True) is None
        scorer.set_conservation_status("GREEN")
        update = guarded_update(scorer, VECTOR, 0, action_index, True)
        assert update is not None and update.centroid_delta_norm > 0
        persisted = asyncio.run(persist_soc_outcome_and_centroid(
            store=store,
            outcome={"decision_id": decision_id, "actual_action": "monitor",
                     "is_correct": True, "domain": "soc", "verified_at_epoch": freeze["snapshot_time"] + 1},
            centroid={"scorer": scorer, "category": "credential_access", "category_index": 0,
                      "action": "monitor", "action_index": action_index,
                      "caused_by_decision_id": decision_id, "pre_centroid": before},
            checkpoint_writer=lambda transaction, replay_verified_at: compound._persist_learning_artifacts(
                decision_id, actual_action="monitor", is_correct=True, category="credential_access",
                replay_verified_at=replay_verified_at,
                evidence_already_persisted=True, skip_history_scan=True, raise_on_error=True,
                transaction=transaction,
            ),
        ))
        assert _seed_module().twin_learning_failure(200, {
            "l5_centroid_persisted": persisted,
            "centroid_update": {"centroid_delta_norm": update.centroid_delta_norm},
        }) is None
        expected = service.comparison(scorer, decisions=store.get_decisions("soc"))
        assert expected["mean_confidence_delta"] > 0
        learned = scorer.mu.copy()
    finally:
        store.close()
    reloaded_store = age_graph.reopen_store()
    try:
        reloaded = CompoundingScorer.from_preset("soc", graph_store=reloaded_store, profile="test", enable_rl=False)
        np.testing.assert_array_equal(reloaded._scorer.mu, learned)
        result = SOCLearningControlService(FrozenTwinStore(twin_graph, "soc")).comparison(
            reloaded._scorer, decisions=reloaded_store.get_decisions("soc"),
        )
        assert result["mean_confidence_delta"] == expected["mean_confidence_delta"]
        assert FrozenTwinStore(twin_graph, "soc").load("soc").to_json() == snapshot_bytes
    finally:
        reloaded_store.close()


def test_demo_read_flag_keeps_archived_baseline_without_write_privileges(tmp_path: Path, twin_graph: InMemoryGraphStore) -> None:
    store = InMemoryGraphStore(domain="soc")
    scorer = CompoundingScorer.from_preset("soc", graph_store=store, profile="test", enable_rl=False)._scorer
    service = SOCLearningControlService(FrozenTwinStore(twin_graph, "soc"))
    service.freeze(scorer, {}, 70, scorer.mu)
    production_bytes = FrozenTwinStore(twin_graph, "soc").load("soc").to_json()
    demo = service.demo_refreeze(scorer, {"components": {"verified_decisions": 0}}, 71)
    keys = ("SOC_DEMO_COMPARISON_ENABLED", "SOC_DEMO_RESEED_ENABLED")
    previous = {key: os.environ.get(key) for key in keys}
    try:
        os.environ["SOC_DEMO_COMPARISON_ENABLED"] = "true"
        os.environ.pop("SOC_DEMO_RESEED_ENABLED", None)
        assert demo_comparison_enabled()
        restarted = SOCLearningControlService(FrozenTwinStore(twin_graph, "soc"))
        comparison = restarted.comparison(scorer, demo=demo_comparison_enabled())
        assert comparison["provenance"] == demo["provenance"]
        assert comparison["frozen_iks"] == 71
        assert restarted.comparison(scorer)["frozen_iks"] == 70
        with pytest.raises(HTTPException) as error:
            asyncio.run(demo_refreeze(DemoRefreezeRequest(confirm_demo_reseed=True)))
        assert error.value.status_code == 403
        assert FrozenTwinStore(twin_graph, "soc").load("soc").to_json() == production_bytes
        os.environ.pop("SOC_DEMO_COMPARISON_ENABLED")
        assert not demo_comparison_enabled()
        os.environ["SOC_DEMO_RESEED_ENABLED"] = "true"
        assert demo_comparison_enabled()
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        store.close()


@pytest.mark.parametrize("original,analyst,expected", [
    (None, "monitor", None), ("refer_to_analyst", "monitor", None),
    ("monitor", None, None), ("monitor", "refer_to_analyst", None),
    ("monitor", "bogus", None), ("monitor", "monitor", "monitor"),
    ("escalate", "monitor", "escalate"),
])
def test_referral_requires_stored_prediction_and_explicit_classification(
    original: str | None, analyst: str | None, expected: str | None,
) -> None:
    decision = {"action": "refer_to_analyst", "original_action": original}
    assert _verified_learning_action(decision, analyst) == expected
    assert decision == {"action": "refer_to_analyst", "original_action": original}
    assert _verified_learning_action({"action": "monitor"}, None) == "monitor"


@pytest.mark.parametrize("status", ["RED", "AMBER"])
def test_verified_referral_cannot_bypass_conservation(tmp_path: Path, status: str) -> None:
    store = InMemoryGraphStore(domain="soc")
    try:
        scorer = CompoundingScorer.from_preset("soc", graph_store=store, profile="test", enable_rl=False)._scorer
        action = _verified_learning_action({"action": "refer_to_analyst", "original_action": "monitor"}, "monitor")
        assert action == "monitor"
        scorer.set_conservation_status(status)
        before = scorer.mu.copy()
        update = guarded_update(scorer, VECTOR, 0, scorer.actions.index(action), True,
                                gt_action_index=scorer.actions.index("monitor"))
        assert update is None
        np.testing.assert_array_equal(scorer.mu, before)
        assert store.get_centroid_checkpoints("soc", include_v2=True) == []
    finally:
        store.close()


def test_verified_referrals_learn_persist_and_keep_routing_and_audit(age_graph: SOCGraphFixture, twin_graph: InMemoryGraphStore) -> None:
    """Production resolver, guards and persistence with real scorer/store/ledger."""
    fixture = _seed_module().frozen_twin_learning_fixture()
    category = fixture["category"]
    ground_truth = fixture["verified_action"]
    assert category == "lateral_movement" and ground_truth == "monitor"
    store = age_graph.store
    compound = CompoundingScorer.from_preset("soc", graph_store=store, profile="test", enable_rl=False)
    scorer = compound._scorer
    assert scorer.categories is not None
    category_index = scorer.categories.index(category)
    policy_index = scorer.categories.index("credential_access")
    policy_geometry = scorer.mu[policy_index].copy()
    authority = AuthorityManager(store=GraphPromotionStore(twin_graph))
    ledger = EvidenceLedger()
    service = SOCLearningControlService(FrozenTwinStore(twin_graph, "soc"))
    service.freeze(scorer, {}, 70, scorer.mu)
    production = FrozenTwinStore(twin_graph, "soc").load("soc").to_json()
    demo = service.demo_refreeze(scorer, {"components": {"verified_decisions": 0}}, 70)
    try:
        scorer.set_conservation_status("GREEN")
        for index in range(60):
            scored = scorer.score(VECTOR, category_index)
            veto = authority.evaluate(category, scored.action_name, "GREEN")
            assert not veto.allowed
            decision_id = _decision(
                store, scorer, "refer_to_analyst", category_index=category_index,
                original_action=scored.action_name,
            )
            audit = ledger.append(decision_id, f"referral-{index}", {}, "refer_to_analyst",
                                  scored.confidence, "pending", False, "")
            original_hash = audit.entry_hash
            stored = store.get_decision(decision_id, "soc")
            assert stored is not None
            learning_action = _verified_learning_action({
                "action": stored["recommended_action"],
                "original_action": stored["metadata"]["original_action"],
            }, ground_truth)
            assert learning_action == scored.action_name
            predicted_index = scorer.actions.index(learning_action)
            gt_index = scorer.actions.index(ground_truth)
            correct = predicted_index == gt_index
            before = scorer.mu[category_index, gt_index].tolist()
            update = guarded_update(scorer, VECTOR, category_index, predicted_index, correct,
                                    category_name=category, gt_action_index=gt_index)
            assert update is not None and update.centroid_delta_norm > 0
            scorer.reestimate_dk()
            persisted = asyncio.run(persist_soc_outcome_and_centroid(
                store=store,
                outcome={"decision_id": decision_id, "actual_action": ground_truth,
                         "is_correct": correct, "domain": "soc",
                         "verified_at_epoch": (demo["snapshot_time"] + index + 1) * 1000,
                         "analyst_action": ground_truth, "recommended_action": "refer_to_analyst"},
                centroid={"scorer": scorer, "category": category, "category_index": category_index,
                          "action": ground_truth, "action_index": gt_index,
                          "caused_by_decision_id": decision_id, "pre_centroid": before},
                checkpoint_writer=lambda transaction, replay_verified_at: compound._persist_learning_artifacts(
                    decision_id, actual_action=ground_truth, is_correct=correct, category=category,
                    replay_verified_at=replay_verified_at,
                    evidence_already_persisted=True, skip_history_scan=True, raise_on_error=True,
                    transaction=transaction,
                ),
            ))
            assert persisted
            ledger.append_outcome(decision_id, original_hash, "correct" if correct else "incorrect", True)
            assert audit.action == "refer_to_analyst" and audit.entry_hash == original_hash
            after = store.get_decision(decision_id, "soc")
            assert after is not None
            assert after["recommended_action"] == "refer_to_analyst"
            assert after["metadata"]["original_action"] == scored.action_name
            assert after["analyst_action"] == ground_truth
        assert ledger.verify_chain()
        assert authority.get_authority(category) == "observed"
        np.testing.assert_array_equal(scorer.mu[policy_index], policy_geometry)
        result = service.comparison(scorer, 70, store.count_verified("soc"), demo=True,
                                    decisions=store.get_decisions("soc"))
        assert result["compared_decisions"] == 60
        assert result["mean_confidence_delta"] > 0
        assert result["mean_confidence_delta"] == pytest.approx(sum(
            point["live"]["confidence"] - point["frozen"]["confidence"]
            for point in result["comparison_points"]
        ) / 60)
        learned = scorer.mu.copy()
    finally:
        store.close()
        authority.store.close()
    reloaded_store = age_graph.reopen_store()
    try:
        restored = CompoundingScorer.from_preset("soc", graph_store=reloaded_store, profile="test", enable_rl=False)._scorer
        np.testing.assert_array_equal(restored.mu, learned)
        comparison = SOCLearningControlService(FrozenTwinStore(twin_graph, "soc")).comparison(
            restored, 70, reloaded_store.count_verified("soc"), demo=True,
            decisions=reloaded_store.get_decisions("soc"),
        )
        assert comparison["mean_confidence_delta"] == result["mean_confidence_delta"]
        assert comparison["provenance"] == demo["provenance"]
        assert FrozenTwinStore(twin_graph, "soc").load("soc").to_json() == production
    finally:
        reloaded_store.close()
