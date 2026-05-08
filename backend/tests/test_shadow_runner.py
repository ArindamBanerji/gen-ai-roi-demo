import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
import pytest

from app.framework.evolution_ledger import ARTIFACT_PROMPT_MODULE, ARTIFACT_ROUTING_RULE
from app.main import app
from app.services import shadow_runner
from app.services import variant_registry as registry


def _variant(
    variant_id="variant_shadow",
    artifact_type="routing_rule",
    category="credential_access",
    status="shadow",
    config=None,
):
    return SimpleNamespace(
        variant_id=variant_id,
        artifact_type=artifact_type,
        category=category,
        status=status,
        config=config
        or {
            "action": "escalate",
            "trigger_categories": ["credential_access"],
            "min_confidence": 0.7,
        },
    )


def _comparison(
    variant_id="variant_shadow",
    alert_id="ALERT-1",
    category="credential_access",
    production_action="monitor",
    variant_action="escalate",
    correct_action=None,
):
    return shadow_runner.ShadowComparison(
        variant_id=variant_id,
        alert_id=alert_id,
        category=category,
        production_action=production_action,
        variant_action=variant_action,
        production_confidence=0.8,
        correct_action=correct_action,
        timestamp=1.0,
    )


@pytest.fixture(autouse=True)
def reset_runner():
    shadow_runner.reset_shadow_runner()
    registry.reset_variant_registry()
    yield
    shadow_runner.reset_shadow_runner()
    registry.reset_variant_registry()


def test_shadow_testable_artifacts_exact_set():
    assert shadow_runner.SHADOW_TESTABLE_ARTIFACTS == {"routing_rule", "scoring_threshold"}


def _registry_record(
    variant_id="variant_shadow_start",
    artifact_type=ARTIFACT_ROUTING_RULE,
    status=registry.CANDIDATE,
):
    return registry.VariantRecord(
        variant_id=variant_id,
        artifact_type=artifact_type,
        category="credential_access",
        config={
            "action": "escalate",
            "trigger_categories": ["credential_access"],
            "min_confidence": 0.7,
        },
        status=status,
        trigger_key=f"trigger:{variant_id}",
        graph_trigger={"campaign_id": "C-007"},
        created_at=1000.0,
    )


def test_admin_shadow_start_valid_candidate_routing_rule_sets_shadow(monkeypatch):
    ledger = AsyncMock(return_value={"id": "evo_shadow"})
    monkeypatch.setattr("gae.evolution.record_evolution_event", ledger)
    registry.register_variant(_registry_record())

    response = TestClient(app).post("/api/admin/shadow-start?variant_id=variant_shadow_start")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "variant_id": "variant_shadow_start",
        "status": "shadow",
    }
    assert registry.get_variant("variant_shadow_start").status == registry.SHADOW


def test_admin_shadow_start_records_shadow_started(monkeypatch):
    ledger = AsyncMock(return_value={"id": "evo_shadow"})
    monkeypatch.setattr("gae.evolution.record_evolution_event", ledger)
    registry.register_variant(_registry_record())

    response = TestClient(app).post("/api/admin/shadow-start?variant_id=variant_shadow_start")

    assert response.status_code == 200
    ledger.assert_awaited_once()
    kwargs = ledger.await_args.kwargs
    assert kwargs["event_type"] == "shadow_started"
    assert kwargs["variant_id"] == "variant_shadow_start"
    assert kwargs["artifact_type"] == ARTIFACT_ROUTING_RULE
    assert kwargs["before_state"] == {"status": "candidate"}
    assert kwargs["after_state"] == {"status": "shadow"}
    assert kwargs["graph_context"] == {"campaign_id": "C-007"}


def test_admin_shadow_start_unknown_variant_returns_404():
    response = TestClient(app).post("/api/admin/shadow-start?variant_id=missing")

    assert response.status_code == 404


def test_admin_shadow_start_non_candidate_returns_400(monkeypatch):
    ledger = AsyncMock(return_value={"id": "evo_shadow"})
    monkeypatch.setattr("gae.evolution.record_evolution_event", ledger)
    registry.register_variant(_registry_record(status=registry.CANDIDATE))
    registry.transition_status("variant_shadow_start", registry.SHADOW)

    response = TestClient(app).post("/api/admin/shadow-start?variant_id=variant_shadow_start")

    assert response.status_code == 400
    ledger.assert_not_awaited()


@pytest.mark.parametrize(
    "artifact_type",
    [ARTIFACT_PROMPT_MODULE, "evidence_order", "context_policy"],
)
def test_admin_shadow_start_non_shadow_testable_artifact_returns_400(monkeypatch, artifact_type):
    ledger = AsyncMock(return_value={"id": "evo_shadow"})
    monkeypatch.setattr("gae.evolution.record_evolution_event", ledger)
    registry.register_variant(_registry_record(artifact_type=artifact_type))

    response = TestClient(app).post("/api/admin/shadow-start?variant_id=variant_shadow_start")

    assert response.status_code == 400
    assert "not MVP shadow-testable" in response.json()["detail"]
    ledger.assert_not_awaited()


@pytest.mark.asyncio
async def test_maybe_shadow_compare_with_no_shadow_variant_adds_no_buffer(monkeypatch):
    monkeypatch.setattr(
        "app.services.variant_registry.get_all_variants",
        lambda status_filter=None: [],
    )

    await shadow_runner.maybe_shadow_compare(
        "ALERT-1", "credential_access", "monitor", 0.8, {"email": "redacted"}
    )

    assert shadow_runner._shadow_buffer == []


@pytest.mark.asyncio
async def test_maybe_shadow_compare_with_shadow_routing_rule_adds_buffer(monkeypatch):
    monkeypatch.setattr(
        "app.services.variant_registry.get_all_variants",
        lambda status_filter=None: [_variant()] if status_filter == "shadow" else [],
    )

    await shadow_runner.maybe_shadow_compare(
        "ALERT-1", "credential_access", "monitor", 0.8, {"some": "context"}
    )

    assert len(shadow_runner._shadow_buffer) == 1
    entry = shadow_runner._shadow_buffer[0]
    assert entry.variant_id == "variant_shadow"
    assert entry.production_action == "monitor"
    assert entry.variant_action == "escalate"
    assert entry.correct_action is None


@pytest.mark.asyncio
async def test_maybe_shadow_compare_with_candidate_or_active_adds_no_buffer(monkeypatch):
    monkeypatch.setattr(
        "app.services.variant_registry.get_all_variants",
        lambda status_filter=None: [] if status_filter == "shadow" else [
            _variant(status="candidate"),
            _variant(variant_id="active", status="active"),
        ],
    )

    await shadow_runner.maybe_shadow_compare(
        "ALERT-1", "credential_access", "monitor", 0.8, {}
    )

    assert shadow_runner._shadow_buffer == []


def test_routing_rule_category_and_confidence_match_returns_configured_action():
    action = shadow_runner.compute_variant_action(
        "routing_rule",
        {"trigger_categories": ["credential_access"], "min_confidence": 0.7, "action": "escalate"},
        "monitor",
        0.8,
        "credential_access",
        {},
    )

    assert action == "escalate"


def test_routing_rule_category_mismatch_returns_production_action():
    action = shadow_runner.compute_variant_action(
        "routing_rule",
        {"trigger_categories": ["lateral_movement"], "min_confidence": 0.7, "action": "escalate"},
        "monitor",
        0.8,
        "credential_access",
        {},
    )

    assert action == "monitor"


def test_scoring_threshold_confidence_between_thresholds_changes_action():
    action = shadow_runner.compute_variant_action(
        "scoring_threshold",
        {
            "category": "credential_access",
            "current_value": 0.9,
            "proposed_value": 0.85,
        },
        "investigate",
        0.87,
        "credential_access",
        {},
    )

    assert action == "suppress"


def test_scoring_threshold_custom_auto_approve_action_changes_action():
    action = shadow_runner.compute_variant_action(
        "scoring_threshold",
        {
            "category": "credential_access",
            "current_value": 0.9,
            "proposed_value": 0.85,
            "auto_approve_action": "auto_approve_po",
        },
        "investigate",
        0.87,
        "credential_access",
        {},
    )

    assert action == "auto_approve_po"


def test_scoring_threshold_generic_auto_approve_action_changes_action():
    action = shadow_runner.compute_variant_action(
        "scoring_threshold",
        {
            "category": "credential_access",
            "current_value": 0.9,
            "proposed_value": 0.85,
            "auto_approve_action": "approve",
        },
        "investigate",
        0.87,
        "credential_access",
        {},
    )

    assert action == "approve"


def test_scoring_threshold_above_both_returns_production_action():
    action = shadow_runner.compute_variant_action(
        "scoring_threshold",
        {
            "category": "credential_access",
            "current_value": 0.9,
            "proposed_value": 0.85,
        },
        "investigate",
        0.95,
        "credential_access",
        {},
    )

    assert action == "investigate"


def test_scoring_threshold_custom_action_above_both_returns_production_action():
    action = shadow_runner.compute_variant_action(
        "scoring_threshold",
        {
            "category": "credential_access",
            "current_value": 0.9,
            "proposed_value": 0.85,
            "auto_approve_action": "auto_approve_po",
        },
        "investigate",
        0.95,
        "credential_access",
        {},
    )

    assert action == "investigate"


def test_context_policy_returns_production_action():
    assert (
        shadow_runner.compute_variant_action(
            "context_policy", {}, "monitor", 0.9, "credential_access", {}
        )
        == "monitor"
    )


def test_prompt_module_returns_production_action():
    assert (
        shadow_runner.compute_variant_action(
            "prompt_module", {}, "monitor", 0.9, "credential_access", {}
        )
        == "monitor"
    )


def test_malformed_config_returns_production_action():
    assert (
        shadow_runner.compute_variant_action(
            "routing_rule",
            {"trigger_categories": None, "min_confidence": object()},
            "monitor",
            0.9,
            "credential_access",
            {},
        )
        == "monitor"
    )


def test_fill_shadow_outcome_fills_matching_alert_id():
    shadow_runner._add_to_shadow_buffer(_comparison(alert_id="ALERT-1"))
    shadow_runner._add_to_shadow_buffer(_comparison(alert_id="ALERT-2"))

    shadow_runner.fill_shadow_outcome("ALERT-1", "escalate")

    assert shadow_runner._shadow_buffer[0].correct_action == "escalate"
    assert shadow_runner._shadow_buffer[1].correct_action is None


def test_fill_shadow_outcome_ignores_non_matching_alert_id():
    shadow_runner._add_to_shadow_buffer(_comparison(alert_id="ALERT-1"))

    shadow_runner.fill_shadow_outcome("ALERT-404", "escalate")

    assert shadow_runner._shadow_buffer[0].correct_action is None


@pytest.mark.asyncio
async def test_fill_shadow_outcome_schedules_flush_when_threshold_reached(monkeypatch):
    scheduled = []

    def fake_create_task(coro):
        scheduled.append(coro)
        coro.close()
        return SimpleNamespace(done=lambda: False)

    monkeypatch.setattr(asyncio, "create_task", fake_create_task)
    monkeypatch.setattr("app.db.neo4j.neo4j_client", object())
    for index in range(shadow_runner.SHADOW_BATCH_SIZE):
        shadow_runner._add_to_shadow_buffer(_comparison(alert_id=f"ALERT-{index}"))

    shadow_runner.fill_shadow_outcome("ALERT-0", "escalate")
    for index in range(1, shadow_runner.SHADOW_BATCH_SIZE):
        shadow_runner._shadow_buffer[index].correct_action = "escalate"
    shadow_runner.fill_shadow_outcome("ALERT-1", "escalate")

    assert scheduled


@pytest.mark.asyncio
async def test_flush_shadow_batch_groups_by_variant_id(monkeypatch):
    ledger = AsyncMock()
    monkeypatch.setattr("gae.evolution.record_evolution_event", ledger)

    def fake_get_variant(variant_id):
        return _variant(variant_id=variant_id)

    monkeypatch.setattr("app.services.variant_registry.get_variant", fake_get_variant)
    for index in range(shadow_runner.SHADOW_BATCH_SIZE):
        shadow_runner._add_to_shadow_buffer(
            _comparison(variant_id="variant_a", alert_id=f"A-{index}", correct_action="escalate")
        )
    for index in range(shadow_runner.SHADOW_BATCH_SIZE):
        shadow_runner._add_to_shadow_buffer(
            _comparison(variant_id="variant_b", alert_id=f"B-{index}", correct_action="escalate")
        )

    await shadow_runner._flush_shadow_batch(object())

    assert ledger.await_count == 2
    assert {call.kwargs["variant_id"] for call in ledger.await_args_list} == {
        "variant_a",
        "variant_b",
    }


@pytest.mark.asyncio
async def test_flush_shadow_batch_only_counts_verified_comparisons(monkeypatch):
    ledger = AsyncMock()
    monkeypatch.setattr("gae.evolution.record_evolution_event", ledger)
    monkeypatch.setattr(
        "app.services.variant_registry.get_variant",
        lambda variant_id: _variant(variant_id=variant_id),
    )
    for index in range(shadow_runner.SHADOW_BATCH_SIZE):
        shadow_runner._add_to_shadow_buffer(
            _comparison(alert_id=f"VER-{index}", correct_action="escalate")
        )
    shadow_runner._add_to_shadow_buffer(_comparison(alert_id="UNVER-1"))
    shadow_runner._add_to_shadow_buffer(_comparison(alert_id="UNVER-2"))

    await shadow_runner._flush_shadow_batch(object())

    assert ledger.await_args.kwargs["metadata"]["total"] == shadow_runner.SHADOW_BATCH_SIZE
    assert len(shadow_runner._shadow_buffer) == 2
    assert all(entry.correct_action is None for entry in shadow_runner._shadow_buffer)


@pytest.mark.asyncio
async def test_below_shadow_batch_size_writes_no_ledger(monkeypatch):
    ledger = AsyncMock()
    monkeypatch.setattr("gae.evolution.record_evolution_event", ledger)
    for index in range(shadow_runner.SHADOW_BATCH_SIZE - 1):
        shadow_runner._add_to_shadow_buffer(
            _comparison(alert_id=f"ALERT-{index}", correct_action="escalate")
        )

    await shadow_runner._flush_shadow_batch(object())

    ledger.assert_not_awaited()


@pytest.mark.asyncio
async def test_flush_writes_shadow_result(monkeypatch):
    ledger = AsyncMock()
    monkeypatch.setattr("gae.evolution.record_evolution_event", ledger)
    monkeypatch.setattr(
        "app.services.variant_registry.get_variant",
        lambda variant_id: _variant(variant_id=variant_id, artifact_type="routing_rule"),
    )
    for index in range(shadow_runner.SHADOW_BATCH_SIZE):
        shadow_runner._add_to_shadow_buffer(
            _comparison(alert_id=f"ALERT-{index}", correct_action="escalate")
        )

    await shadow_runner._flush_shadow_batch(object())

    ledger.assert_awaited_once()
    kwargs = ledger.await_args.kwargs
    assert kwargs["event_type"] == "shadow_result"
    assert kwargs["variant_id"] == "variant_shadow"
    assert kwargs["artifact_type"] == "routing_rule"
    assert kwargs["graph_context"]["evidence_type"] == "contextual_performance"
    assert kwargs["metadata"]["wins"] == shadow_runner.SHADOW_BATCH_SIZE
    assert kwargs["metadata"]["total"] == shadow_runner.SHADOW_BATCH_SIZE


@pytest.mark.parametrize(
    ("production_action", "variant_action", "correct_action", "expected_wins"),
    [
        ("monitor", "escalate", "escalate", 1),
        ("escalate", "escalate", "escalate", 0),
        ("monitor", "investigate", "escalate", 0),
        ("escalate", "monitor", "escalate", 0),
    ],
)
@pytest.mark.asyncio
async def test_win_counting_cases(
    monkeypatch, production_action, variant_action, correct_action, expected_wins
):
    ledger = AsyncMock()
    monkeypatch.setattr("gae.evolution.record_evolution_event", ledger)
    monkeypatch.setattr(
        "app.services.variant_registry.get_variant",
        lambda variant_id: _variant(variant_id=variant_id),
    )
    shadow_runner._add_to_shadow_buffer(
        _comparison(
            alert_id="CASE",
            production_action=production_action,
            variant_action=variant_action,
            correct_action=correct_action,
        )
    )
    for index in range(shadow_runner.SHADOW_BATCH_SIZE - 1):
        shadow_runner._add_to_shadow_buffer(
            _comparison(
                alert_id=f"FILL-{index}",
                production_action="monitor",
                variant_action="monitor",
                correct_action="monitor",
            )
        )

    await shadow_runner._flush_shadow_batch(object())

    assert ledger.await_args.kwargs["metadata"]["wins"] == expected_wins


def test_reset_shadow_runner_clears_buffer():
    shadow_runner._add_to_shadow_buffer(_comparison())

    shadow_runner.reset_shadow_runner()

    assert shadow_runner._shadow_buffer == []


@pytest.mark.asyncio
async def test_stale_non_shadow_variant_is_pruned_at_flush(monkeypatch):
    ledger = AsyncMock()
    monkeypatch.setattr("gae.evolution.record_evolution_event", ledger)
    monkeypatch.setattr(
        "app.services.variant_registry.get_variant",
        lambda variant_id: _variant(variant_id=variant_id, status="active"),
    )
    for index in range(shadow_runner.SHADOW_BATCH_SIZE):
        shadow_runner._add_to_shadow_buffer(
            _comparison(alert_id=f"ALERT-{index}", correct_action="escalate")
        )

    await shadow_runner._flush_shadow_batch(object())

    ledger.assert_not_awaited()
    assert shadow_runner._shadow_buffer == []


@pytest.mark.asyncio
async def test_missing_variant_verified_entries_are_pruned_at_flush(monkeypatch):
    ledger = AsyncMock()
    monkeypatch.setattr("gae.evolution.record_evolution_event", ledger)
    monkeypatch.setattr("app.services.variant_registry.get_variant", lambda variant_id: None)
    for index in range(shadow_runner.SHADOW_BATCH_SIZE):
        shadow_runner._add_to_shadow_buffer(
            _comparison(alert_id=f"ALERT-{index}", correct_action="escalate")
        )

    await shadow_runner._flush_shadow_batch(object())

    ledger.assert_not_awaited()
    assert shadow_runner._shadow_buffer == []


@pytest.mark.asyncio
async def test_stale_cleanup_preserves_unverified_entries(monkeypatch):
    ledger = AsyncMock()
    monkeypatch.setattr("gae.evolution.record_evolution_event", ledger)
    monkeypatch.setattr("app.services.variant_registry.get_variant", lambda variant_id: None)
    for index in range(shadow_runner.SHADOW_BATCH_SIZE):
        shadow_runner._add_to_shadow_buffer(
            _comparison(alert_id=f"VER-{index}", correct_action="escalate")
        )
    shadow_runner._add_to_shadow_buffer(_comparison(alert_id="UNVER-1"))

    await shadow_runner._flush_shadow_batch(object())

    ledger.assert_not_awaited()
    assert len(shadow_runner._shadow_buffer) == 1
    assert shadow_runner._shadow_buffer[0].alert_id == "UNVER-1"
    assert shadow_runner._shadow_buffer[0].correct_action is None


@pytest.mark.asyncio
async def test_stale_cleanup_prevents_repeated_flush_scheduling(monkeypatch):
    scheduled = []

    def fake_create_task(coro):
        scheduled.append(coro)
        coro.close()
        return SimpleNamespace(done=lambda: False)

    ledger = AsyncMock()
    monkeypatch.setattr("gae.evolution.record_evolution_event", ledger)
    monkeypatch.setattr(
        "app.services.variant_registry.get_variant",
        lambda variant_id: _variant(variant_id=variant_id, status="active"),
    )
    monkeypatch.setattr(asyncio, "create_task", fake_create_task)
    monkeypatch.setattr("app.db.neo4j.neo4j_client", object())
    for index in range(shadow_runner.SHADOW_BATCH_SIZE):
        shadow_runner._add_to_shadow_buffer(
            _comparison(alert_id=f"ALERT-{index}", correct_action="escalate")
        )

    await shadow_runner._flush_shadow_batch(object())

    shadow_runner._maybe_schedule_flush()

    ledger.assert_not_awaited()
    assert shadow_runner._shadow_buffer == []
    assert scheduled == []


@pytest.mark.asyncio
async def test_failed_variant_write_preserves_entries_and_continues(monkeypatch):
    ledger = AsyncMock(side_effect=[RuntimeError("boom"), None])
    monkeypatch.setattr("gae.evolution.record_evolution_event", ledger)
    monkeypatch.setattr(
        "app.services.variant_registry.get_variant",
        lambda variant_id: _variant(variant_id=variant_id),
    )
    for index in range(shadow_runner.SHADOW_BATCH_SIZE):
        shadow_runner._add_to_shadow_buffer(
            _comparison(variant_id="variant_a", alert_id=f"A-{index}", correct_action="escalate")
        )
    for index in range(shadow_runner.SHADOW_BATCH_SIZE):
        shadow_runner._add_to_shadow_buffer(
            _comparison(variant_id="variant_b", alert_id=f"B-{index}", correct_action="escalate")
        )

    await shadow_runner._flush_shadow_batch(object())

    assert ledger.await_count == 2
    assert {entry.variant_id for entry in shadow_runner._shadow_buffer} == {"variant_a"}


@pytest.mark.asyncio
async def test_flush_lock_prevents_concurrent_duplicate_flush(monkeypatch):
    ledger = AsyncMock()
    monkeypatch.setattr("gae.evolution.record_evolution_event", ledger)
    monkeypatch.setattr(
        "app.services.variant_registry.get_variant",
        lambda variant_id: _variant(variant_id=variant_id),
    )
    for index in range(shadow_runner.SHADOW_BATCH_SIZE):
        shadow_runner._add_to_shadow_buffer(
            _comparison(alert_id=f"ALERT-{index}", correct_action="escalate")
        )

    await asyncio.gather(
        shadow_runner._flush_shadow_batch(object()),
        shadow_runner._flush_shadow_batch(object()),
    )

    ledger.assert_awaited_once()
    assert shadow_runner._shadow_buffer == []
