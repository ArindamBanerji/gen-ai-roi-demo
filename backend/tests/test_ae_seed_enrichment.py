from __future__ import annotations

import importlib.util
from collections import Counter, defaultdict
from pathlib import Path

import pytest


def _load_seed_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "seed_verified_decisions.py"
    spec = importlib.util.spec_from_file_location("seed_verified_decisions", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


seed_mod = _load_seed_module()

FIXED_NOW_MS = 1_800_000_000_000.0
VALID_EVENT_TYPES = {
    "variant_created",
    "shadow_started",
    "shadow_result",
    "promotion_approved",
    "promotion_rejected",
}
REQUIRED_FIELDS = {"event_type", "variant_id", "artifact_type", "description", "timestamp_override"}
EXPECTED_VARIANT_IDS = {
    "ae_rule_drift_threshold_credential_access_v2",
    "ae_rule_drift_threshold_lateral_movement_v1",
    "ae_rule_drift_threshold_cloud_infrastructure_v1",
    "ae_rule_campaign_escalate_campaign_c012",
    "ae_rule_campaign_escalate_campaign_c015",
    "ae_rule_campaign_escalate_campaign_c018",
    "ae_rule_coverage_gap_insider_threat_v1",
    "ae_rule_coverage_gap_data_exfiltration_v1",
}


def _events():
    return seed_mod._build_enrichment_events(FIXED_NOW_MS, seed_mod.MILLISECONDS_PER_DAY)


def _by_variant(events):
    grouped = defaultdict(list)
    for event in events:
        grouped[event["variant_id"]].append(event)
    return grouped


def test_enrichment_event_count():
    events = _events()
    assert len(events) == 32
    assert {event["variant_id"] for event in events} == EXPECTED_VARIANT_IDS


def test_event_types_valid():
    events = _events()
    assert {event["event_type"] for event in events} <= VALID_EVENT_TYPES
    assert all(event["event_type"] == event["event_type"].lower() for event in events)


def test_rejected_variant_exists():
    events = _by_variant(_events())["ae_rule_campaign_escalate_campaign_c018"]
    event_types = {event["event_type"] for event in events}
    assert "promotion_rejected" in event_types

    shadow_result = next(event for event in events if event["event_type"] == "shadow_result")
    assert shadow_result["after_state"]["win_rate"] == 0.47
    assert shadow_result["after_state"]["comparisons"] == 30
    assert shadow_result["after_state"]["wins"] == 14

    rejection = next(event for event in events if event["event_type"] == "promotion_rejected")
    assert "win_rate 0.47 < threshold 0.60" in rejection["after_state"]["reason"]
    assert "win_rate 0.47 < threshold 0.60" in rejection["description"]


def test_event_types_balanced():
    variant_ids = {event["variant_id"] for event in _events()}
    assert sum("drift_threshold" in variant_id for variant_id in variant_ids) >= 2
    assert sum("campaign_escalate" in variant_id for variant_id in variant_ids) >= 2
    assert sum("coverage_gap" in variant_id for variant_id in variant_ids) >= 2


def test_timestamps_chronological():
    expected_order = [
        "variant_created",
        "shadow_started",
        "shadow_result",
    ]
    for variant_id, events in _by_variant(_events()).items():
        ordered = sorted(events, key=lambda event: event["timestamp_override"])
        assert [event["event_type"] for event in ordered[:3]] == expected_order
        assert ordered[-1]["event_type"] in {"promotion_approved", "promotion_rejected"}
        timestamps = [event["timestamp_override"] for event in ordered]
        assert timestamps == sorted(timestamps), variant_id
        assert len(set(timestamps)) == len(timestamps), variant_id


def test_all_events_have_required_fields():
    for event in _events():
        assert REQUIRED_FIELDS <= set(event)
        assert isinstance(event["variant_id"], str) and event["variant_id"]
        assert isinstance(event["artifact_type"], str) and event["artifact_type"]
        assert isinstance(event["description"], str) and event["description"]
        assert isinstance(event["timestamp_override"], (int, float))
        assert event["timestamp_override"] > 1_000_000_000_000


@pytest.mark.asyncio
async def test_enrichment_idempotency_skips_existing_variants(monkeypatch):
    existing_variant = "ae_rule_campaign_escalate_campaign_c018"
    recorded = []

    class FakeClient:
        async def run_query(self, query):
            assert "MATCH (e:EvolutionEvent) RETURN DISTINCT e.variant_id AS variant_id" in query
            return [{"variant_id": existing_variant}]

    async def fake_record(client, **kwargs):
        recorded.append(kwargs)
        return kwargs

    monkeypatch.setattr("gae.evolution.record_evolution_event", fake_record)
    monkeypatch.setattr("time.time", lambda: FIXED_NOW_MS / 1000)

    summary = await seed_mod.enrich_evolution_events(FakeClient())

    assert summary["events_added"] == 28
    assert summary["events_skipped"] == 4
    assert summary["variants_added"] == 7
    assert summary["variants_skipped"] == 1
    assert existing_variant in summary["variant_ids_skipped"]
    assert all(event["variant_id"] != existing_variant for event in recorded)


@pytest.mark.asyncio
async def test_enrichment_records_with_valid_signature(monkeypatch):
    recorded = []

    class FakeClient:
        async def run_query(self, query):
            return []

    async def fake_record(
        neo4j_client,
        event_type,
        variant_id,
        artifact_type,
        description,
        before_state=None,
        after_state=None,
        triggered_by=None,
        graph_context=None,
        metadata=None,
        impact="operational",
        magnitude=0.0,
        timestamp_override=None,
    ):
        assert neo4j_client is not None
        assert event_type in VALID_EVENT_TYPES
        assert variant_id in EXPECTED_VARIANT_IDS
        assert artifact_type in {"routing_rule", "scoring_threshold"}
        assert description
        assert timestamp_override is not None
        recorded.append(
            {
                "event_type": event_type,
                "variant_id": variant_id,
                "artifact_type": artifact_type,
                "description": description,
                "before_state": before_state,
                "after_state": after_state,
                "triggered_by": triggered_by,
                "graph_context": graph_context,
                "metadata": metadata,
                "impact": impact,
                "magnitude": magnitude,
                "timestamp_override": timestamp_override,
            }
        )

    monkeypatch.setattr("gae.evolution.record_evolution_event", fake_record)
    monkeypatch.setattr("time.time", lambda: FIXED_NOW_MS / 1000)

    summary = await seed_mod.enrich_evolution_events(FakeClient())

    assert len(recorded) == 32
    assert summary["events_added"] == 32
    assert summary["events_skipped"] == 0
    counts = Counter(event["event_type"] for event in recorded)
    assert counts["variant_created"] == 8
    assert counts["shadow_started"] == 8
    assert counts["shadow_result"] == 8
    assert counts["promotion_approved"] == 7
    assert counts["promotion_rejected"] == 1
