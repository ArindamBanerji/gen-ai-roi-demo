import asyncio
import inspect
import json
import os
import sys
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.main import app
from app.framework import evolution_ledger as ledger


def _run(coro):
    return asyncio.run(coro)


def _client(rows=None):
    mock = AsyncMock()
    mock.run_query = AsyncMock(return_value=rows or [])
    return mock


def _last_query(mock):
    return mock.run_query.call_args.args[0]


def _empty_summary():
    return {
        "variants_generated": 0,
        "variants_promoted": 0,
        "variants_rejected": 0,
        "variants_rolled_back": 0,
        "shadow_batches": 0,
        "shadow_started": 0,
        "by_artifact_type": {},
        "avg_shadow_win_rate": 0.0,
        "total_shadow_decisions": 0,
    }


def setup_function():
    ledger.reset_evolution_ledger()


def test_record_evolution_event_writes_standalone_create_query():
    mock = _client()
    event = _run(ledger.record_evolution_event(
        mock,
        ledger.VARIANT_CREATED,
        "variant_a",
        ledger.ARTIFACT_ROUTING_RULE,
        "created from campaign graph",
        before_state={"threshold": 0.7},
        after_state={"threshold": 0.8},
        graph_context={"campaign_id": "camp-1"},
        metadata={"source": "ucl"},
    ))

    query = _last_query(mock)
    assert "CREATE (e:EvolutionEvent" in query
    assert "variant_id" in query
    assert "artifact_type" in query
    assert event["graph_context"] == {"campaign_id": "camp-1"}


def test_query_pattern_has_no_forbidden_legacy_constructs():
    mock = _client()
    _run(ledger.record_evolution_event(
        mock,
        ledger.VARIANT_CREATED,
        "variant_a",
        ledger.ARTIFACT_ROUTING_RULE,
        "safe create",
    ))

    query = _last_query(mock)
    assert "MERGE" not in query
    assert "$" not in query
    assert "MATCH (decision:Decision" not in query
    assert "TRIGGERED_EVOLUTION" not in query


@pytest.mark.parametrize("event_type", sorted(ledger.VALID_EVENT_TYPES))
def test_all_event_types_accepted(event_type):
    mock = _client()
    event = _run(ledger.record_evolution_event(
        mock,
        event_type,
        f"variant_{event_type}",
        ledger.ARTIFACT_CONTEXT_POLICY,
        "event accepted",
        metadata={"win": True} if event_type == ledger.SHADOW_RESULT else None,
    ))
    assert event["event_type"] == event_type


def test_invalid_event_type_rejected():
    with pytest.raises(ValueError):
        _run(ledger.record_evolution_event(
            _client(),
            "pattern_learned",
            "variant_a",
            ledger.ARTIFACT_CONTEXT_POLICY,
            "legacy event rejected",
        ))


@pytest.mark.parametrize("artifact_type", sorted(ledger.VALID_ARTIFACT_TYPES))
def test_all_artifact_types_accepted(artifact_type):
    mock = _client()
    event = _run(ledger.record_evolution_event(
        mock,
        ledger.VARIANT_CREATED,
        f"variant_{artifact_type}",
        artifact_type,
        "artifact accepted",
    ))
    assert event["artifact_type"] == artifact_type


def test_invalid_artifact_type_rejected():
    with pytest.raises(ValueError):
        _run(ledger.record_evolution_event(
            _client(),
            ledger.VARIANT_CREATED,
            "variant_a",
            "centroid",
            "level 1 artifact rejected",
        ))


def test_variant_created_works_without_triggered_by():
    event = _run(ledger.record_evolution_event(
        _client(),
        ledger.VARIANT_CREATED,
        "variant_a",
        ledger.ARTIFACT_PROMPT_MODULE,
        "created",
    ))
    assert event["triggered_by"] is None


def test_artifact_type_written_for_routing_rule_and_prompt_module():
    for artifact_type in (ledger.ARTIFACT_ROUTING_RULE, ledger.ARTIFACT_PROMPT_MODULE):
        mock = _client()
        _run(ledger.record_evolution_event(
            mock,
            ledger.VARIANT_CREATED,
            f"variant_{artifact_type}",
            artifact_type,
            "artifact write",
        ))
        assert artifact_type in _last_query(mock)


def test_graph_context_campaign_evidence_stored_as_json_and_returned_as_dict():
    mock = _client()
    context = {"campaign_id": "camp-7", "alerts": ["A1", "A2"]}
    event = _run(ledger.record_evolution_event(
        mock,
        ledger.VARIANT_CREATED,
        "variant_campaign",
        ledger.ARTIFACT_EVIDENCE_ORDER,
        "campaign evidence",
        graph_context=context,
    ))
    query = _last_query(mock)
    assert json.dumps(context, sort_keys=True, separators=(",", ":")) in query
    assert event["graph_context"] == context


def test_graph_context_factor_drift_evidence_round_trips():
    context = {"factor_drift": {"F1": 0.21}, "correlation_change": 0.13}
    event = _run(ledger.record_evolution_event(
        _client(),
        ledger.PROMOTION_APPROVED,
        "variant_drift",
        ledger.ARTIFACT_SCORING_THRESHOLD,
        "factor drift gate",
        graph_context=context,
    ))
    assert event["graph_context"] == context


def test_state_fields_are_json_strings_not_python_repr():
    mock = _client()
    _run(ledger.record_evolution_event(
        mock,
        ledger.VARIANT_CREATED,
        "variant_json",
        ledger.ARTIFACT_CONTEXT_POLICY,
        "json storage",
        before_state={"enabled": False},
        after_state={"enabled": True},
        metadata={"wins": 1, "total": 2},
    ))
    query = _last_query(mock)
    assert '{"enabled":false}' in query
    assert "{'enabled': False}" not in query
    assert '{"total":2,"wins":1}' in query


@pytest.mark.parametrize("bad_magnitude", [float("nan"), float("inf"), float("-inf")])
def test_record_evolution_event_rejects_non_finite_magnitude_before_query(bad_magnitude):
    mock = _client()
    with pytest.raises(ValueError, match="magnitude must be finite"):
        _run(ledger.record_evolution_event(
            mock,
            ledger.VARIANT_CREATED,
            "variant_bad_magnitude",
            ledger.ARTIFACT_CONTEXT_POLICY,
            "bad magnitude",
            magnitude=bad_magnitude,
        ))
    mock.run_query.assert_not_called()


def test_record_evolution_event_rejects_non_numeric_magnitude_before_query():
    mock = _client()
    with pytest.raises(ValueError, match="magnitude must be numeric"):
        _run(ledger.record_evolution_event(
            mock,
            ledger.VARIANT_CREATED,
            "variant_bad_magnitude",
            ledger.ARTIFACT_CONTEXT_POLICY,
            "bad magnitude",
            magnitude="not-a-number",
        ))
    mock.run_query.assert_not_called()


def test_record_evolution_event_writes_finite_numeric_magnitude():
    mock = _client()
    event = _run(ledger.record_evolution_event(
        mock,
        ledger.VARIANT_CREATED,
        "variant_magnitude",
        ledger.ARTIFACT_CONTEXT_POLICY,
        "finite magnitude",
        magnitude=1.25,
    ))
    query = _last_query(mock)
    assert "magnitude: 1.25" in query
    assert "nan" not in query.lower()
    assert "inf" not in query.lower()
    assert event["magnitude"] == 1.25


def test_shadow_started_sets_shadow_active_true():
    _run(ledger.record_evolution_event(
        _client(),
        ledger.SHADOW_STARTED,
        "variant_shadow",
        ledger.ARTIFACT_ROUTING_RULE,
        "shadow started",
    ))
    assert ledger.get_shadow_summary("variant_shadow")["shadow_active"] is True


def test_shadow_result_sets_tested_clears_active_and_updates_rate():
    _run(ledger.record_evolution_event(
        _client(),
        ledger.SHADOW_RESULT,
        "variant_shadow",
        ledger.ARTIFACT_ROUTING_RULE,
        "shadow result",
        metadata={"wins": 2, "total": 4},
    ))
    summary = ledger.get_shadow_summary("variant_shadow")
    assert summary["shadow_active"] is False
    assert summary["shadow_tested"] is True
    assert summary["wins"] == 2
    assert summary["total"] == 4
    assert summary["win_rate"] == 0.5


def test_shadow_result_after_shadow_started_clears_active():
    _run(ledger.record_evolution_event(
        _client(),
        ledger.SHADOW_STARTED,
        "variant_shadow",
        ledger.ARTIFACT_ROUTING_RULE,
        "shadow started",
    ))
    _run(ledger.record_evolution_event(
        _client(),
        ledger.SHADOW_RESULT,
        "variant_shadow",
        ledger.ARTIFACT_ROUTING_RULE,
        "shadow result",
        metadata={"win": True},
    ))
    summary = ledger.get_shadow_summary("variant_shadow")
    assert summary["shadow_active"] is False
    assert summary["shadow_tested"] is True


def test_multiple_shadow_results_aggregate_wins_total_win_rate():
    for metadata in ({"wins": 1, "total": 2}, {"wins": 2, "total": 3}):
        _run(ledger.record_evolution_event(
            _client(),
            ledger.SHADOW_RESULT,
            "variant_multi",
            ledger.ARTIFACT_ROUTING_RULE,
            "shadow result",
            metadata=metadata,
        ))
    summary = ledger.get_shadow_summary("variant_multi")
    assert summary["wins"] == 3
    assert summary["total"] == 5
    assert summary["win_rate"] == 0.6


def test_rebuild_shadow_index_handles_started_and_result_rows():
    rows = [
        {
            "event_type": ledger.SHADOW_STARTED,
            "variant_id": "variant_rebuild",
            "metadata": "{}",
            "after_state": "{}",
            "graph_context": "{}",
        },
        {
            "event_type": ledger.SHADOW_RESULT,
            "variant_id": "variant_rebuild",
            "metadata": '{"wins":2,"total":3}',
            "after_state": "{}",
            "graph_context": "{}",
        },
    ]
    index = _run(ledger.rebuild_shadow_index(_client(rows)))
    assert index["variant_rebuild"]["shadow_active"] is False
    assert index["variant_rebuild"]["shadow_tested"] is True
    assert index["variant_rebuild"]["wins"] == 2
    assert index["variant_rebuild"]["total"] == 3


def test_rebuild_shadow_index_skips_legacy_nodes_without_variant_id():
    rows = [
        {"event_type": ledger.SHADOW_STARTED, "variant_id": None},
        {"event_type": "pattern_learned", "variant_id": "legacy"},
    ]
    index = _run(ledger.rebuild_shadow_index(_client(rows)))
    assert index == {}


def test_get_shadow_summary_returns_copy_and_unknown_none():
    _run(ledger.record_evolution_event(
        _client(),
        ledger.SHADOW_STARTED,
        "variant_copy",
        ledger.ARTIFACT_CONTEXT_POLICY,
        "started",
    ))
    summary = ledger.get_shadow_summary("variant_copy")
    summary["shadow_active"] = False
    assert ledger.get_shadow_summary("variant_copy")["shadow_active"] is True
    assert ledger.get_shadow_summary("unknown") is None


def test_reset_evolution_ledger_clears_index_and_issues_no_delete():
    mock = _client()
    _run(ledger.record_evolution_event(
        mock,
        ledger.SHADOW_STARTED,
        "variant_reset",
        ledger.ARTIFACT_CONTEXT_POLICY,
        "started",
    ))
    ledger.reset_evolution_ledger()
    assert ledger.get_shadow_summary("variant_reset") is None
    queries = " ".join(c.args[0] for c in mock.run_query.call_args_list)
    assert "DELETE" not in queries


def test_get_variant_history_returns_ordered_events_with_graph_context():
    rows = [
        {
            "id": "e1",
            "event_type": ledger.VARIANT_CREATED,
            "variant_id": "variant_history",
            "artifact_type": ledger.ARTIFACT_ROUTING_RULE,
            "description": "created",
            "graph_context": '{"campaign_id":"camp"}',
            "before_state": "{}",
            "after_state": "{}",
            "metadata": "{}",
            "timestamp_epoch": 1,
        }
    ]
    mock = _client(rows)
    events = _run(ledger.get_variant_history(mock, "variant_history"))
    query = _last_query(mock)
    assert "ORDER BY e.timestamp_epoch ASC" in query
    assert events[0]["graph_context"] == {"campaign_id": "camp"}
    assert events[0]["timestamp_epoch"] == 1


def test_get_recent_events_respects_limit_and_excludes_legacy_event_types_in_query():
    mock = _client([])
    _run(ledger.get_recent_events(mock, limit=250))
    query = _last_query(mock)
    assert "LIMIT 100" in query
    assert "pattern_learned" not in query
    assert ledger.VARIANT_CREATED in query


def test_get_evolution_summary_empty_ledger_returns_zero_summary():
    summary = _run(ledger.get_evolution_summary(_client([])))

    assert summary == _empty_summary()


def test_get_evolution_summary_counts_variant_created_events():
    rows = [
        {"event_type": ledger.VARIANT_CREATED, "artifact_type": ledger.ARTIFACT_ROUTING_RULE},
        {"event_type": ledger.VARIANT_CREATED, "artifact_type": ledger.ARTIFACT_SCORING_THRESHOLD},
        {"event_type": ledger.VARIANT_CREATED, "artifact_type": ledger.ARTIFACT_PROMPT_MODULE},
    ]

    summary = _run(ledger.get_evolution_summary(_client(rows)))

    assert summary["variants_generated"] == 3


def test_get_evolution_summary_counts_mixed_lifecycle_events():
    rows = [
        {"event_type": ledger.VARIANT_CREATED, "artifact_type": ledger.ARTIFACT_ROUTING_RULE},
        {"event_type": ledger.VARIANT_CREATED, "artifact_type": ledger.ARTIFACT_SCORING_THRESHOLD},
        {"event_type": ledger.PROMOTION_APPROVED, "artifact_type": ledger.ARTIFACT_ROUTING_RULE},
        {"event_type": ledger.PROMOTION_REJECTED, "artifact_type": ledger.ARTIFACT_SCORING_THRESHOLD},
        {"event_type": ledger.ROLLBACK, "artifact_type": ledger.ARTIFACT_ROUTING_RULE},
    ]

    summary = _run(ledger.get_evolution_summary(_client(rows)))

    assert summary["variants_generated"] == 2
    assert summary["variants_promoted"] == 1
    assert summary["variants_rejected"] == 1
    assert summary["variants_rolled_back"] == 1


def test_get_evolution_summary_groups_by_artifact_type():
    rows = [
        {"event_type": ledger.VARIANT_CREATED, "artifact_type": ledger.ARTIFACT_ROUTING_RULE},
        {"event_type": ledger.PROMOTION_APPROVED, "artifact_type": ledger.ARTIFACT_ROUTING_RULE},
        {"event_type": ledger.PROMOTION_REJECTED, "artifact_type": ledger.ARTIFACT_SCORING_THRESHOLD},
    ]

    summary = _run(ledger.get_evolution_summary(_client(rows)))

    assert summary["by_artifact_type"][ledger.ARTIFACT_ROUTING_RULE]["generated"] == 1
    assert summary["by_artifact_type"][ledger.ARTIFACT_ROUTING_RULE]["promoted"] == 1
    assert summary["by_artifact_type"][ledger.ARTIFACT_SCORING_THRESHOLD]["rejected"] == 1


def test_get_evolution_summary_promotion_rate_uses_terminal_denominator():
    rows = [
        {"event_type": ledger.PROMOTION_APPROVED, "artifact_type": ledger.ARTIFACT_ROUTING_RULE},
        {"event_type": ledger.PROMOTION_REJECTED, "artifact_type": ledger.ARTIFACT_ROUTING_RULE},
    ]

    summary = _run(ledger.get_evolution_summary(_client(rows)))

    assert summary["by_artifact_type"][ledger.ARTIFACT_ROUTING_RULE]["promotion_rate"] == 0.5


def test_get_evolution_summary_promotion_rate_zero_denominator():
    rows = [
        {"event_type": ledger.VARIANT_CREATED, "artifact_type": ledger.ARTIFACT_ROUTING_RULE},
    ]

    summary = _run(ledger.get_evolution_summary(_client(rows)))

    assert summary["by_artifact_type"][ledger.ARTIFACT_ROUTING_RULE]["promotion_rate"] == 0.0


def test_get_evolution_summary_averages_shadow_win_rate():
    rows = [
        {
            "event_type": ledger.SHADOW_RESULT,
            "artifact_type": ledger.ARTIFACT_ROUTING_RULE,
            "graph_context": '{"win_rate":0.60,"sample_size":25}',
        },
        {
            "event_type": ledger.SHADOW_RESULT,
            "artifact_type": ledger.ARTIFACT_ROUTING_RULE,
            "graph_context": {"win_rate": 0.80, "sample_size": 50},
        },
    ]

    summary = _run(ledger.get_evolution_summary(_client(rows)))

    assert summary["avg_shadow_win_rate"] == 0.7


def test_get_evolution_summary_sums_total_shadow_decisions():
    rows = [
        {
            "event_type": ledger.SHADOW_RESULT,
            "artifact_type": ledger.ARTIFACT_ROUTING_RULE,
            "graph_context": '{"win_rate":0.60,"sample_size":25}',
        },
        {
            "event_type": ledger.SHADOW_RESULT,
            "artifact_type": ledger.ARTIFACT_SCORING_THRESHOLD,
            "graph_context": '{"win_rate":0.80,"sample_size":50}',
        },
    ]

    summary = _run(ledger.get_evolution_summary(_client(rows)))

    assert summary["total_shadow_decisions"] == 75


def test_get_evolution_summary_missing_shadow_context_does_not_crash():
    rows = [
        {"event_type": ledger.SHADOW_RESULT, "artifact_type": ledger.ARTIFACT_ROUTING_RULE},
        {
            "event_type": ledger.SHADOW_RESULT,
            "artifact_type": ledger.ARTIFACT_ROUTING_RULE,
            "graph_context": "{malformed",
        },
    ]

    summary = _run(ledger.get_evolution_summary(_client(rows)))

    assert summary["shadow_batches"] == 2
    assert summary["avg_shadow_win_rate"] == 0.0
    assert summary["total_shadow_decisions"] == 0


def test_get_evolution_summary_counts_shadow_started():
    rows = [
        {"event_type": ledger.SHADOW_STARTED, "artifact_type": ledger.ARTIFACT_ROUTING_RULE},
        {"event_type": ledger.SHADOW_STARTED, "artifact_type": ledger.ARTIFACT_SCORING_THRESHOLD},
    ]

    summary = _run(ledger.get_evolution_summary(_client(rows)))

    assert summary["shadow_started"] == 2


def test_get_evolution_summary_query_failure_returns_zero_summary():
    mock = AsyncMock()
    mock.run_query = AsyncMock(side_effect=RuntimeError("graph unavailable"))

    summary = _run(ledger.get_evolution_summary(mock))

    assert summary == _empty_summary()


def test_get_evolution_summary_query_pattern_is_age_safe_and_filters_events():
    mock = _client([])

    _run(ledger.get_evolution_summary(mock))

    query = _last_query(mock)
    assert "MATCH (e:EvolutionEvent)" in query
    assert "LIMIT 10000" in query
    assert "MERGE" not in query
    assert "$" not in query
    assert "pattern_learned" not in query
    assert ledger.VARIANT_CREATED in query
    assert ledger.ROLLBACK in query


def test_routing_rule_threshold_state_round_trips():
    event = _run(ledger.record_evolution_event(
        _client(),
        ledger.PROMOTION_APPROVED,
        "variant_threshold",
        ledger.ARTIFACT_ROUTING_RULE,
        "threshold changed",
        before_state={"threshold": 0.72},
        after_state={"threshold": 0.81},
    ))
    assert event["before_state"]["threshold"] == 0.72
    assert event["after_state"]["threshold"] == 0.81


def test_context_policy_traversal_order_state_round_trips():
    event = _run(ledger.record_evolution_event(
        _client(),
        ledger.PROMOTION_REJECTED,
        "variant_policy",
        ledger.ARTIFACT_CONTEXT_POLICY,
        "policy rejected",
        before_state={"traversal_order": ["user", "asset"]},
        after_state={"traversal_order": ["campaign", "user", "asset"]},
    ))
    assert event["after_state"]["traversal_order"][0] == "campaign"


def test_reset_evolver_state_calls_reset_evolution_ledger():
    with patch("gae.evolution.reset_evolution_ledger") as reset_mock:
        from app.services.evolver import reset_evolver_state
        reset_evolver_state()
    reset_mock.assert_called_once()


def test_variant_history_endpoint_returns_events_for_variant_id():
    event = {
        "id": "e1",
        "event_type": ledger.VARIANT_CREATED,
        "variant_id": "variant_api",
        "graph_context": {"campaign_id": "camp"},
    }
    with patch(
        "app.routers.evolution.get_ledger_variant_history",
        new=AsyncMock(return_value=[event]),
    ):
        response = TestClient(app).get("/api/evolution/variant-history?variant_id=variant_api")
    assert response.status_code == 200
    body = response.json()
    assert body["variant_id"] == "variant_api"
    assert body["count"] == 1
    assert body["events"][0]["graph_context"]["campaign_id"] == "camp"


def test_variant_history_endpoint_returns_empty_for_unknown_variant():
    with patch(
        "app.routers.evolution.get_ledger_variant_history",
        new=AsyncMock(return_value=[]),
    ):
        response = TestClient(app).get("/api/evolution/variant-history?variant_id=unknown")
    assert response.status_code == 200
    assert response.json()["events"] == []


def test_recent_events_endpoint_returns_events_and_respects_limit():
    event = {
        "id": "e1",
        "event_type": ledger.SHADOW_RESULT,
        "variant_id": "variant_api",
        "artifact_type": ledger.ARTIFACT_PROMPT_MODULE,
    }
    with patch(
        "app.routers.evolution.get_ledger_recent_events",
        new=AsyncMock(return_value=[event]),
    ) as recent_mock:
        response = TestClient(app).get("/api/evolution/recent-events?limit=5")
    assert response.status_code == 200
    assert response.json()["limit"] == 5
    assert response.json()["events"][0]["event_type"] == ledger.SHADOW_RESULT
    recent_mock.assert_awaited_once()


def test_recent_events_endpoint_excludes_legacy_by_delegating_to_ledger():
    with patch(
        "app.routers.evolution.get_ledger_recent_events",
        new=AsyncMock(return_value=[]),
    ) as recent_mock:
        response = TestClient(app).get("/api/evolution/recent-events")
    assert response.status_code == 200
    recent_mock.assert_awaited_once()


def test_evolution_summary_endpoint_returns_summary():
    expected = _empty_summary()
    expected["variants_generated"] = 3
    expected["by_artifact_type"] = {
        ledger.ARTIFACT_ROUTING_RULE: {
            "generated": 3,
            "promoted": 1,
            "rejected": 0,
            "promotion_rate": 1.0,
        }
    }
    with patch(
        "app.routers.evolution.get_ledger_evolution_summary",
        new=AsyncMock(return_value=expected),
    ) as summary_mock:
        response = TestClient(app).get("/api/evolution/summary")

    assert response.status_code == 200
    assert response.json()["variants_generated"] == 3
    assert response.json()["by_artifact_type"][ledger.ARTIFACT_ROUTING_RULE]["promotion_rate"] == 1.0
    summary_mock.assert_awaited_once()


def test_evolution_summary_endpoint_empty_ledger_returns_zeros():
    with patch(
        "app.routers.evolution.get_ledger_evolution_summary",
        new=AsyncMock(return_value=_empty_summary()),
    ):
        response = TestClient(app).get("/api/evolution/summary")

    assert response.status_code == 200
    assert response.json() == _empty_summary()


def test_evolution_summary_endpoint_failure_returns_503():
    with patch(
        "app.routers.evolution.get_ledger_evolution_summary",
        new=AsyncMock(side_effect=RuntimeError("graph unavailable")),
    ):
        response = TestClient(app).get("/api/evolution/summary")

    assert response.status_code == 503
    assert response.json()["detail"] == "AGE query failed for evolution summary"


def test_p16_separation_no_profile_scorer_or_centroid_imports():
    source = inspect.getsource(ledger)
    forbidden = ["from app.services.gae_state", "get_profile_scorer(", "ProfileScorer("]
    assert not any(term in source for term in forbidden)
