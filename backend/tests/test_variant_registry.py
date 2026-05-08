import asyncio
import inspect
import json
from unittest.mock import AsyncMock

import pytest

from app.services import variant_registry as registry


def _run(coro):
    return asyncio.run(coro)


def _record(
    variant_id="variant_a",
    *,
    artifact_type=registry.ARTIFACT_ROUTING_RULE,
    category="credential_access",
    status=registry.CANDIDATE,
    trigger_key="campaign:camp-1",
):
    return registry.VariantRecord(
        variant_id=variant_id,
        artifact_type=artifact_type,
        category=category,
        config={"threshold": 0.8},
        status=status,
        trigger_key=trigger_key,
        graph_trigger={"campaign_id": "camp-1"},
        created_at=1000.0,
    )


def _client(side_effect=None):
    mock = AsyncMock()
    if side_effect is not None:
        mock.run_query = AsyncMock(side_effect=side_effect)
    else:
        mock.run_query = AsyncMock(return_value=[])
    return mock


def setup_function():
    registry.reset_variant_registry()


def test_register_and_retrieve_by_id_returns_copy():
    registered = registry.register_variant(_record())
    retrieved = registry.get_variant("variant_a")

    assert registered.variant_id == "variant_a"
    assert retrieved is not None
    assert retrieved.variant_id == "variant_a"
    retrieved.config["threshold"] = 0.1
    assert registry.get_variant("variant_a").config["threshold"] == 0.8


def test_retrieve_active_by_category_and_artifact_type():
    registry.register_variant(_record("variant_old", status=registry.ACTIVE))
    newer = _record("variant_new", status=registry.ACTIVE)
    newer.promoted_at = 2000.0
    newer.created_at = 2000.0
    registry.register_variant(newer)

    result = registry.get_active_variant_for_category(
        "credential_access",
        registry.ARTIFACT_ROUTING_RULE,
    )

    assert result is not None
    assert result.variant_id == "variant_new"


def test_global_active_variant_matches_any_category():
    global_record = _record("variant_global", category=None, status=registry.ACTIVE)
    registry.register_variant(global_record)

    result = registry.get_active_variant_for_category(
        "lateral_movement",
        registry.ARTIFACT_ROUTING_RULE,
    )

    assert result is not None
    assert result.variant_id == "variant_global"


@pytest.mark.parametrize("status", [registry.CANDIDATE, registry.SHADOW, registry.ACTIVE])
def test_has_active_or_shadow_true_for_dedup_statuses(status):
    registry.register_variant(_record(status=status, trigger_key="signal:1"))

    assert registry.has_active_or_shadow("signal:1") is True


@pytest.mark.parametrize("status", [registry.REJECTED, registry.ROLLED_BACK])
def test_has_active_or_shadow_false_for_terminal_statuses(status):
    registry.register_variant(_record(status=status, trigger_key="signal:1"))

    assert registry.has_active_or_shadow("signal:1") is False


def test_dedup_by_trigger_key():
    registry.register_variant(_record("variant_a", trigger_key="shared:user-1"))
    registry.register_variant(_record("variant_b", trigger_key="shared:user-2"))

    assert registry.has_active_or_shadow("shared:user-1") is True
    assert registry.has_active_or_shadow("shared:user-2") is True
    assert registry.has_active_or_shadow("shared:user-3") is False


def test_valid_transitions_preserve_created_at_and_set_promoted_at():
    registry.register_variant(_record())

    shadow = registry.transition_status("variant_a", registry.SHADOW)
    active = registry.transition_status("variant_a", registry.ACTIVE)
    rolled_back = registry.transition_status("variant_a", registry.ROLLED_BACK)

    assert shadow.status == registry.SHADOW
    assert active.status == registry.ACTIVE
    assert active.promoted_at is not None
    assert rolled_back.status == registry.ROLLED_BACK
    assert rolled_back.created_at == 1000.0


def test_invalid_transitions_raise():
    registry.register_variant(_record("candidate_variant", status=registry.CANDIDATE))
    registry.register_variant(_record("rejected_variant", status=registry.REJECTED))

    with pytest.raises(ValueError):
        registry.transition_status("candidate_variant", registry.ACTIVE)
    with pytest.raises(ValueError):
        registry.transition_status("rejected_variant", registry.SHADOW)


def test_get_all_variants_with_status_filter():
    registry.register_variant(_record("variant_a", status=registry.CANDIDATE))
    registry.register_variant(_record("variant_b", status=registry.ACTIVE))

    active = registry.get_all_variants(status_filter=registry.ACTIVE)

    assert [record.variant_id for record in active] == ["variant_b"]


def test_reset_clears_memory_and_does_not_call_graph():
    registry.register_variant(_record())
    mock = _client()

    registry.reset_variant_registry()

    assert registry.get_all_variants() == []
    mock.run_query.assert_not_called()


def test_get_active_variant_for_category_returns_none_when_absent():
    registry.register_variant(_record(status=registry.CANDIDATE))

    assert registry.get_active_variant_for_category(
        "credential_access",
        registry.ARTIFACT_ROUTING_RULE,
    ) is None


def test_rebuild_from_mock_evolution_event_rows():
    created_rows = [
        {
            "event_type": "variant_created",
            "variant_id": "variant_a",
            "artifact_type": registry.ARTIFACT_ROUTING_RULE,
            "after_state": json.dumps({
                "category": "credential_access",
                "config": {"threshold": 0.82},
            }),
            "metadata": json.dumps({"trigger_key": "campaign:camp-1"}),
            "graph_context": json.dumps({"campaign_id": "camp-1"}),
            "timestamp_epoch": 100000,
        },
        {
            "event_type": "variant_created",
            "variant_id": "",
            "artifact_type": registry.ARTIFACT_ROUTING_RULE,
            "after_state": "{}",
            "metadata": "{}",
            "graph_context": "{}",
            "timestamp_epoch": 100001,
        },
    ]
    promotion_rows = [
        {
            "event_type": "promotion_approved",
            "variant_id": "variant_a",
            "timestamp_epoch": 200000,
        }
    ]
    rollback_rows = [
        {
            "event_type": "rollback",
            "variant_id": "variant_a",
            "timestamp_epoch": 300000,
        }
    ]
    mock = _client(side_effect=[created_rows, promotion_rows, rollback_rows, []])

    summary = _run(registry.rebuild_registry(mock))

    rebuilt = registry.get_variant("variant_a")
    assert summary["rebuilt"] == 1
    assert summary["rolled_back"] == 1
    assert rebuilt is not None
    assert rebuilt.status == registry.ROLLED_BACK
    assert rebuilt.config == {"threshold": 0.82}
    assert rebuilt.graph_trigger == {"campaign_id": "camp-1"}
    assert rebuilt.promoted_at == 200.0


def test_rebuild_handles_query_failure_independently():
    created_rows = [
        {
            "event_type": "variant_created",
            "variant_id": "variant_a",
            "artifact_type": registry.ARTIFACT_PROMPT_MODULE,
            "after_state": json.dumps({"category": "phishing"}),
            "metadata": json.dumps({"trigger_key": "override:phishing"}),
            "graph_context": "{}",
            "timestamp_epoch": 100000,
        }
    ]
    mock = _client(side_effect=[
        created_rows,
        RuntimeError("promotion unavailable"),
        [],
        [],
    ])

    summary = _run(registry.rebuild_registry(mock))

    assert summary["rebuilt"] == 1
    assert summary["errors"] == [
        {"event_type": "promotion_approved", "error": "promotion unavailable"}
    ]
    assert registry.get_variant("variant_a").status == registry.CANDIDATE


def test_rebuild_queries_are_age_safe_and_read_only():
    mock = _client(side_effect=[[], [], [], []])

    _run(registry.rebuild_registry(mock))

    queries = "\n".join(call.args[0] for call in mock.run_query.call_args_list)
    assert "MATCH (e:EvolutionEvent)" in queries
    assert "CREATE" not in queries
    assert "MERGE" not in queries
    assert "$" not in queries
    assert "DELETE" not in queries


def test_invalid_status_and_artifact_rejected():
    with pytest.raises(ValueError):
        registry.register_variant(_record(status="unknown"))
    with pytest.raises(ValueError):
        registry.register_variant(_record(artifact_type="unknown"))


def test_p16_registry_has_no_level1_imports_or_writes():
    source = inspect.getsource(registry)

    forbidden = [
        "ProfileScorer",
        "gae_state",
        "get_profile_scorer",
        "build_profile_scorer",
    ]
    for token in forbidden:
        assert token not in source


def test_rebuild_promotion_rejected_sets_status_rejected():
    created_rows = [
        {
            "event_type": "variant_created",
            "variant_id": "variant_a",
            "artifact_type": registry.ARTIFACT_ROUTING_RULE,
            "after_state": json.dumps({"category": "credential_access"}),
            "metadata": json.dumps({"trigger_key": "campaign:camp-1"}),
            "graph_context": "{}",
            "timestamp_epoch": 100000,
        }
    ]
    rejection_rows = [
        {
            "event_type": "promotion_rejected",
            "variant_id": "variant_a",
            "timestamp_epoch": 200000,
        }
    ]
    mock = _client(side_effect=[created_rows, [], [], rejection_rows])

    summary = _run(registry.rebuild_registry(mock))

    rebuilt = registry.get_variant("variant_a")
    assert rebuilt is not None
    assert rebuilt.status == registry.REJECTED
    assert summary["rejected"] == 1
    assert summary["active"] == 0


def test_rebuild_no_rejection_event_status_stays_candidate():
    created_rows = [
        {
            "event_type": "variant_created",
            "variant_id": "variant_b",
            "artifact_type": registry.ARTIFACT_PROMPT_MODULE,
            "after_state": json.dumps({"category": "phishing"}),
            "metadata": json.dumps({"trigger_key": "override:phishing"}),
            "graph_context": "{}",
            "timestamp_epoch": 100000,
        }
    ]
    mock = _client(side_effect=[created_rows, [], [], []])

    summary = _run(registry.rebuild_registry(mock))

    rebuilt = registry.get_variant("variant_b")
    assert rebuilt is not None
    assert rebuilt.status == registry.CANDIDATE
    assert summary["rejected"] == 0
