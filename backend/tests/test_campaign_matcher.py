"""
tests/test_campaign_matcher.py — F6 CampaignRepository + CampaignMatcher tests.

4 tests using AsyncMock Neo4j — no live database required.

Run from backend/:
    pytest tests/test_campaign_matcher.py -v
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import asyncio
import re
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

from app.domains.soc.campaigns import (
    Campaign,
    CampaignCorrelationEngine,
    CampaignMatcher,
    CampaignRepository,
    CampaignTraceCollector,
    derived_entity_key,
)

DEFAULT_CONFIG = {
    "correlation_window_hours": 24,
    "temporal_window_minutes": 60,
    "min_alerts_for_campaign": 2,
    "max_campaign_age_days": 30,
}


def run(coro):
    return asyncio.run(coro)


def _campaign(member_alert_ids, campaign_id="c-001"):
    return Campaign(
        campaign_id=campaign_id,
        first_seen=datetime(2026, 3, 25, 10, 0),
        last_seen=datetime(2026, 3, 25, 16, 0),
        alert_count=len(member_alert_ids),
        category_sequence=["credential_access", "lateral_movement"],
        shared_entities=["ip-1"],
        technique_sequence=[],
        confidence=0.85,
        trigger_rule="technique_sequence",
        severity="HIGH",
        member_decision_ids=[],
        member_alert_ids=member_alert_ids,
        correlation_window_hours=24,
        nl_summary="campaign summary",
        rule_type="technique_sequence",
        derived_entity_key="entity:ip-1",
        category="credential_access",
        time_bucket=493112,
    )


def _event(
    alert_id,
    *,
    category="credential_access",
    source_entity_id=None,
    user_id=None,
    asset_id=None,
    source_location=None,
    technique_id=None,
    minutes=0,
    severity="MEDIUM",
):
    return {
        "alert_id": alert_id,
        "category": category,
        "source_entity_id": source_entity_id,
        "user_id": user_id,
        "asset_id": asset_id,
        "source_location": source_location,
        "technique_id": technique_id,
        "ts": datetime(2026, 3, 25, 0, 0) + timedelta(minutes=minutes),
        "severity": severity,
        "decision_id": f"decision-{alert_id}",
    }


def _correlate(events):
    return CampaignCorrelationEngine(DEFAULT_CONFIG).correlate(events)


class FakeCampaignGraph:
    def __init__(self, alerts=None, campaigns=None, edges=None, fail_on=None):
        self.alerts = set(alerts or [])
        self.campaigns = set(campaigns or [])
        self.edges = set(edges or [])
        self.fail_on = fail_on
        self.queries = []

    async def run_query(self, query, params=None):
        self.queries.append(query)
        if self.fail_on and self.fail_on in query:
            raise RuntimeError("injected graph failure")

        campaign_id = self._campaign_id(query)
        if "MATCH (c:Campaign" in query and "RETURN c" in query:
            return [{"c": {"campaign_id": campaign_id}}] if campaign_id in self.campaigns else []

        if "CREATE (c:Campaign" in query:
            self.campaigns.add(campaign_id)
            return []

        if "SET c.first_seen" in query or "SET c.last_seen" in query:
            return []

        if "-[:MEMBER_OF]->" in query and "RETURN a.alert_id AS alert_id" in query:
            requested = set(self._predicate_alert_ids(query))
            return [
                {"alert_id": alert_id}
                for alert_id, cid in sorted(self.edges)
                if cid == campaign_id and alert_id in requested
            ]

        if "MATCH (a:Alert)" in query and "RETURN a.alert_id AS alert_id" in query:
            requested = set(self._predicate_alert_ids(query))
            return [{"alert_id": alert_id} for alert_id in sorted(requested & self.alerts)]

        if "CREATE (a" in query and "[:MEMBER_OF]->(c)" in query:
            created_count = 0
            for alert_id in self._create_alert_ids(query):
                if alert_id in self.alerts and campaign_id in self.campaigns:
                    self.edges.add((alert_id, campaign_id))
                    created_count += 1
            return [{"created_count": created_count}]

        return []

    @staticmethod
    def _campaign_id(query):
        match = re.search(r"campaign_id: '([^']+)'", query)
        return match.group(1) if match else None

    @staticmethod
    def _predicate_alert_ids(query):
        return re.findall(r"a\.alert_id = '([^']+)'", query)

    @staticmethod
    def _create_alert_ids(query):
        return re.findall(r"MATCH \(a\d+:Alert \{alert_id: '([^']+)'\}\)", query)

    def count_queries_containing(self, text):
        return sum(1 for query in self.queries if text in query)


class FakeReadGraph:
    def __init__(self, rows):
        self.rows = rows
        self.queries = []
        self.params = []

    async def run_query(self, query, params=None):
        self.queries.append(query)
        self.params.append(params or {})
        return list(self.rows)


class FakeNoopMemberCreateGraph(FakeCampaignGraph):
    async def run_query(self, query, params=None):
        if "CREATE (a0)-[:MEMBER_OF]->(c)" in query:
            self.queries.append(query)
            return []
        return await super().run_query(query, params)


# ============================================================================
# Test 1 — check_alert returns None on exception (never raises)
# ============================================================================

def test_check_alert_returns_none_on_exception():
    """
    CampaignMatcher.check_alert must never raise.
    Neo4j failure → log warning → return None.
    """
    mock_neo4j = AsyncMock()
    mock_neo4j.run_query.side_effect = Exception("Neo4j down")

    engine = CampaignCorrelationEngine(DEFAULT_CONFIG)
    repo = CampaignRepository(mock_neo4j)
    matcher = CampaignMatcher(mock_neo4j, DEFAULT_CONFIG, engine, repo)

    result = run(matcher.check_alert("alert-123"))

    assert result is None, (
        f"check_alert must return None on Neo4j failure, not raise. Got: {result!r}"
    )


# ============================================================================
# Test 2 — check_alert joins existing campaign when found
# ============================================================================

def test_check_alert_reuses_stable_campaign_identity_after_correlation():
    """
    Phase 1 does not use an early source_entity lookup. The matcher correlates
    first, then write_campaign updates the stable identity-keyed Campaign.
    """

    class StubRepo:
        def __init__(self):
            self.written = []

        async def fetch_recent_events(self, *_args, **_kwargs):
            return [
                _event("alert-old", user_id="user-1", minutes=0),
                _event("alert-new", user_id="user-1", minutes=1),
            ]

        async def fetch_single_alert_event(self, *_args, **_kwargs):
            return None

        async def write_campaign(self, campaign, trace=None):
            self.written.append(campaign)
            return True

    engine = CampaignCorrelationEngine(DEFAULT_CONFIG)
    repo = StubRepo()
    matcher = CampaignMatcher(None, DEFAULT_CONFIG, engine, repo)

    result = run(matcher.check_alert("alert-new"))

    assert result == repo.written[0].campaign_id
    assert repo.written[0].rule_type == "shared_entity"
    assert repo.written[0].derived_entity_key == "user:user-1"


# ============================================================================
# Test 3 — check_alert returns None when no campaign and insufficient events
# ============================================================================

def test_check_alert_returns_none_when_no_campaign():
    """
    When no existing campaign and Neo4j returns no recent events,
    check_alert must return None (not create a spurious campaign).
    """
    mock_neo4j = AsyncMock()
    # All reads return empty — no existing campaign, no recent events
    mock_neo4j.run_query.return_value = []

    engine = CampaignCorrelationEngine(DEFAULT_CONFIG)
    repo = CampaignRepository(mock_neo4j)
    matcher = CampaignMatcher(mock_neo4j, DEFAULT_CONFIG, engine, repo)

    result = run(matcher.check_alert("alert-xyz"))

    assert result is None, (
        f"Expected None when no campaign and no events. Got: {result!r}"
    )


# ============================================================================
# Test 4 — write_campaign is idempotent (MERGE safe to call twice)
# ============================================================================

def test_repository_write_campaign_is_idempotent():
    """
    write_campaign uses MERGE — calling it twice with the same campaign_id
    must succeed both times (return True). No unique-constraint violation.
    """
    mock_neo4j = AsyncMock()
    mock_neo4j.run_query.return_value = None

    repo = CampaignRepository(mock_neo4j)

    campaign = Campaign(
        campaign_id="c-001",
        first_seen=datetime(2026, 3, 25, 10, 0),
        last_seen=datetime(2026, 3, 25, 16, 0),
        alert_count=2,
        category_sequence=["credential_access", "lateral_movement"],
        shared_entities=["ip-1"],
        technique_sequence=[],
        confidence=0.85,
        trigger_rule="technique_sequence",
        severity="HIGH",
        member_decision_ids=[],
        member_alert_ids=["a1", "a2"],
        correlation_window_hours=24,
        nl_summary="2 alerts: credential_access → lateral_movement over 6h.",
    )

    result1 = run(repo.write_campaign(campaign))
    result2 = run(repo.write_campaign(campaign))  # second write — MERGE is safe

    assert result1 is True, f"First write_campaign must return True. Got: {result1!r}"
    assert result2 is True, f"Second write_campaign must return True. Got: {result2!r}"


def test_write_campaign_batches_new_member_edges():
    graph = FakeCampaignGraph(alerts=["a1", "a2", "a3"])
    repo = CampaignRepository(graph)

    result = run(repo.write_campaign(_campaign(["a1", "a2", "a3"])))

    assert result is True
    assert graph.edges == {("a1", "c-001"), ("a2", "c-001"), ("a3", "c-001")}
    assert graph.count_queries_containing("RETURN a.alert_id AS alert_id") == 2
    assert graph.count_queries_containing("CREATE (a0)-[:MEMBER_OF]->(c)") == 1


def test_write_campaign_repeated_call_does_not_duplicate_member_edges():
    graph = FakeCampaignGraph(alerts=["a1", "a2"])
    repo = CampaignRepository(graph)
    campaign = _campaign(["a1", "a2"])

    assert run(repo.write_campaign(campaign)) is True
    assert run(repo.write_campaign(campaign)) is True

    assert graph.edges == {("a1", "c-001"), ("a2", "c-001")}
    assert graph.count_queries_containing("CREATE (a0)-[:MEMBER_OF]->(c)") == 1


def test_write_campaign_skips_missing_alert_without_blocking_valid_edges():
    graph = FakeCampaignGraph(alerts=["a1", "a3"])
    repo = CampaignRepository(graph)

    result = run(repo.write_campaign(_campaign(["a1", "missing", "a3"])))

    assert result is True
    assert graph.edges == {("a1", "c-001"), ("a3", "c-001")}
    assert ("missing", "c-001") not in graph.edges


def test_write_campaign_handles_zero_member_ids():
    graph = FakeCampaignGraph(alerts=["a1"])
    repo = CampaignRepository(graph)

    result = run(repo.write_campaign(_campaign([])))

    assert result is True
    assert graph.edges == set()
    assert graph.count_queries_containing("RETURN a.alert_id AS alert_id") == 0
    assert graph.count_queries_containing("[:MEMBER_OF]->(c)") == 0


def test_write_campaign_dedupes_duplicate_member_ids():
    graph = FakeCampaignGraph(alerts=["a1", "a2"])
    repo = CampaignRepository(graph)

    result = run(repo.write_campaign(_campaign(["a1", "a1", "a2", "a2"])))

    assert result is True
    assert graph.edges == {("a1", "c-001"), ("a2", "c-001")}
    assert graph.count_queries_containing("CREATE (a0)-[:MEMBER_OF]->(c)") == 1


def test_write_campaign_chunks_member_edge_creates_at_25():
    alert_ids = [f"a{i}" for i in range(26)]
    graph = FakeCampaignGraph(alerts=alert_ids)
    repo = CampaignRepository(graph)

    result = run(repo.write_campaign(_campaign(alert_ids)))

    assert result is True
    assert graph.edges == {(alert_id, "c-001") for alert_id in alert_ids}
    assert graph.count_queries_containing("CREATE (a0)-[:MEMBER_OF]->(c)") == 2


def test_write_campaign_only_creates_missing_subset():
    graph = FakeCampaignGraph(
        alerts=["a1", "a2", "a3"],
        campaigns=["c-001"],
        edges={("a1", "c-001"), ("a2", "c-001")},
    )
    repo = CampaignRepository(graph)

    result = run(repo.write_campaign(_campaign(["a1", "a2", "a3"])))

    assert result is True
    assert graph.edges == {("a1", "c-001"), ("a2", "c-001"), ("a3", "c-001")}
    assert graph.count_queries_containing("CREATE (a0)-[:MEMBER_OF]->(c)") == 1


def test_write_campaign_all_edges_already_exist_creates_no_edges():
    graph = FakeCampaignGraph(
        alerts=["a1", "a2"],
        campaigns=["c-001"],
        edges={("a1", "c-001"), ("a2", "c-001")},
    )
    repo = CampaignRepository(graph)

    result = run(repo.write_campaign(_campaign(["a1", "a2"])))

    assert result is True
    assert graph.edges == {("a1", "c-001"), ("a2", "c-001")}
    assert graph.count_queries_containing("CREATE (a0)-[:MEMBER_OF]->(c)") == 0


def test_write_campaign_returns_false_on_batched_query_failure():
    graph = FakeCampaignGraph(alerts=["a1"], fail_on="MATCH (a:Alert)")
    repo = CampaignRepository(graph)

    result = run(repo.write_campaign(_campaign(["a1"])))

    assert result is False


def test_write_campaign_diagnostics_use_batched_labels(monkeypatch, tmp_path):
    monkeypatch.setenv("SOC_PERF_TRACE_ENABLED", "true")
    monkeypatch.setenv("SOC_PERF_TRACE_OUTPUT", str(tmp_path / "campaign_trace.jsonl"))
    graph = FakeCampaignGraph(alerts=["a1", "a2"], edges={("a1", "c-001")})
    repo = CampaignRepository(graph)
    trace = CampaignTraceCollector("a2")

    result = run(repo.write_campaign(_campaign(["a1", "a2"], campaign_id="c-001"), trace=trace))

    assert result is True
    assert trace.member_alert_count == 2
    assert trace.member_edge_existing_count == 1
    assert trace.member_edge_missing_count == 1
    assert trace.member_alert_missing_count == 0
    assert trace.member_edge_create_chunk_count == 1
    assert trace.member_edges_created_count == 1
    labels = [query["label"] for query in trace.queries]
    assert "member_edges_existing_read" in labels
    assert "member_alert_nodes_read" in labels
    assert "member_edges_batch_create" in labels
    assert "member_edge_check" not in labels
    assert "member_edge_create" not in labels


def test_write_campaign_batch_create_query_uses_single_create_with_returned_count():
    graph = FakeCampaignGraph(alerts=["a1", "a2", "a3"])
    repo = CampaignRepository(graph)

    result = run(repo.write_campaign(_campaign(["a1", "a2", "a3"])))

    assert result is True
    batch_queries = [
        query for query in graph.queries
        if "CREATE (a0)-[:MEMBER_OF]->(c)" in query
    ]
    assert len(batch_queries) == 1
    batch_query = batch_queries[0]
    assert "MATCH (c:Campaign {campaign_id: 'c-001'})" in batch_query
    assert "MATCH (a0:Alert {alert_id: 'a1'})" in batch_query
    assert "MATCH (a1:Alert {alert_id: 'a2'})" in batch_query
    assert "MATCH (a2:Alert {alert_id: 'a3'})" in batch_query
    assert "CREATE (a0)-[:MEMBER_OF]->(c), (a1)-[:MEMBER_OF]->(c), (a2)-[:MEMBER_OF]->(c)" in batch_query
    assert "RETURN 3 AS created_count" in batch_query


def test_write_campaign_diagnostics_do_not_claim_edges_without_create_ack(monkeypatch, tmp_path):
    monkeypatch.setenv("SOC_PERF_TRACE_ENABLED", "true")
    monkeypatch.setenv("SOC_PERF_TRACE_OUTPUT", str(tmp_path / "campaign_trace.jsonl"))
    graph = FakeNoopMemberCreateGraph(alerts=["a1", "a2"])
    repo = CampaignRepository(graph)
    trace = CampaignTraceCollector("a1")

    result = run(repo.write_campaign(_campaign(["a1", "a2"], campaign_id="c-001"), trace=trace))

    assert result is True
    assert graph.edges == set()
    assert trace.member_edge_missing_count == 2
    assert trace.member_edge_create_chunk_count == 1
    assert trace.member_edges_created_count == 0


def test_phase1_same_stream_same_user_same_category_reuses_one_campaign_with_25_edges():
    events = [
        _event(f"a{i:02d}", user_id="user-1", category="credential_access", minutes=i)
        for i in range(25)
    ]
    campaigns = _correlate(events)

    assert len(campaigns) == 1
    campaign = campaigns[0]
    assert campaign.alert_count == 25
    assert campaign.derived_entity_key == "user:user-1"
    assert campaign.category == "credential_access"

    graph = FakeCampaignGraph(alerts=[event["alert_id"] for event in events])
    assert run(CampaignRepository(graph).write_campaign(campaign)) is True
    assert graph.campaigns == {campaign.campaign_id}
    assert graph.edges == {
        (event["alert_id"], campaign.campaign_id) for event in events
    }


def test_phase1_five_users_create_five_entity_scoped_campaigns():
    events = []
    for user_idx in range(5):
        for alert_idx in range(5):
            events.append(
                _event(
                    f"u{user_idx}-a{alert_idx}",
                    user_id=f"user-{user_idx}",
                    category="credential_access",
                    minutes=user_idx * 10 + alert_idx,
                )
            )

    campaigns = _correlate(events)

    assert len(campaigns) == 5
    assert {campaign.derived_entity_key for campaign in campaigns} == {
        f"user:user-{idx}" for idx in range(5)
    }


def test_phase1_three_categories_same_user_create_three_campaigns():
    events = []
    categories = ["credential_access", "lateral_movement", "data_exfiltration"]
    for cat_idx, category in enumerate(categories):
        for alert_idx in range(2):
            events.append(
                _event(
                    f"{category}-{alert_idx}",
                    user_id="user-1",
                    category=category,
                    minutes=cat_idx * 10 + alert_idx,
                )
            )

    campaigns = _correlate(events)

    assert len(campaigns) == 3
    assert {campaign.category for campaign in campaigns} == set(categories)
    assert {campaign.derived_entity_key for campaign in campaigns} == {"user:user-1"}


def test_phase1_temporal_same_category_different_users_do_not_merge():
    events = [
        _event("u1-a1", user_id="user-1", category="credential_access", minutes=0),
        _event("u1-a2", user_id="user-1", category="credential_access", minutes=1),
        _event("u2-a1", user_id="user-2", category="credential_access", minutes=2),
        _event("u2-a2", user_id="user-2", category="credential_access", minutes=3),
    ]

    campaigns = _correlate(events)

    assert len(campaigns) == 2
    for campaign in campaigns:
        assert len({derived_entity_key(event) for event in events if event["alert_id"] in campaign.member_alert_ids}) == 1


def test_phase1_cross_category_technique_case_does_not_create_l1_attack_chain():
    events = [
        _event("a1", user_id="user-1", category="credential_access", minutes=0),
        _event("a2", user_id="user-1", category="lateral_movement", minutes=1),
    ]

    campaigns = _correlate(events)

    assert campaigns == []


def test_phase1_campaign_id_stable_as_members_grow():
    first_batch = [
        _event(f"a{i}", user_id="user-1", category="credential_access", minutes=i)
        for i in range(2)
    ]
    later_batch = [
        _event(f"a{i}", user_id="user-1", category="credential_access", minutes=i)
        for i in range(10)
    ]

    first_campaign = _correlate(first_batch)[0]
    later_campaign = _correlate(later_batch)[0]

    assert first_campaign.campaign_id == later_campaign.campaign_id
    assert later_campaign.alert_count == 10


def test_phase1_user_id_fallback_when_source_entity_id_absent():
    campaigns = _correlate([
        _event("a1", user_id="user-1", category="credential_access", minutes=0),
        _event("a2", user_id="user-1", category="credential_access", minutes=1),
    ])

    assert len(campaigns) == 1
    assert campaigns[0].derived_entity_key == "user:user-1"


def test_phase1_cross_type_same_value_entities_remain_separate():
    campaigns = _correlate([
        _event("user-a1", user_id="X", category="credential_access", minutes=0),
        _event("user-a2", user_id="X", category="credential_access", minutes=1),
        _event("asset-a1", asset_id="X", category="credential_access", minutes=2),
        _event("asset-a2", asset_id="X", category="credential_access", minutes=3),
    ])

    assert len(campaigns) == 2
    assert {campaign.derived_entity_key for campaign in campaigns} == {"user:X", "asset:X"}


def test_phase1_no_entity_identifiers_create_no_campaign_through_rule_paths():
    campaigns = _correlate([
        _event("a1", category="credential_access", minutes=0),
        _event("a2", category="credential_access", minutes=1),
        _event("a3", category="lateral_movement", minutes=2),
    ])

    assert campaigns == []


def test_phase1_unrelated_alerts_do_not_merge():
    campaigns = _correlate([
        _event("a1", user_id="user-1", category="credential_access", minutes=0),
        _event("a2", user_id="user-2", category="lateral_movement", minutes=1),
        _event("a3", asset_id="asset-1", category="data_exfiltration", minutes=2),
    ])

    assert campaigns == []


def test_phase1_bucket_boundary_splits_campaign_identity():
    events = [
        _event("d1-a1", user_id="user-1", category="credential_access", minutes=0),
        _event("d1-a2", user_id="user-1", category="credential_access", minutes=1),
        _event("d2-a1", user_id="user-1", category="credential_access", minutes=24 * 60),
        _event("d2-a2", user_id="user-1", category="credential_access", minutes=24 * 60 + 1),
    ]

    campaigns = _correlate(events)

    assert len(campaigns) == 2
    assert len({campaign.time_bucket for campaign in campaigns}) == 2
    assert len({campaign.campaign_id for campaign in campaigns}) == 2


def test_phase1_diagnostic_like_rows_group_by_decision_source_id_after_normalization():
    events = [
        _event(
            f"diag-{idx:04d}",
            category="credential_access",
            source_entity_id="diag-zone-1",
            user_id=f"diag-user-{idx:04d}",
            asset_id=f"diag-asset-{idx:04d}",
            source_location="diag-zone-1",
            minutes=idx,
        )
        for idx in range(25)
    ]

    campaigns = _correlate(events)

    assert len(campaigns) == 1
    assert campaigns[0].derived_entity_key == "entity:diag-zone-1"
    assert campaigns[0].alert_count == 25

    graph = FakeCampaignGraph(alerts=[event["alert_id"] for event in events])
    assert run(CampaignRepository(graph).write_campaign(campaigns[0])) is True
    assert graph.campaigns == {campaigns[0].campaign_id}
    assert len(graph.edges) == 25


def test_fetch_recent_events_preserves_phase1_identity_fields_from_decision_source():
    graph = FakeReadGraph([
        {
            "alert_id": "diag-0001",
            "category": "credential_access",
            "source_entity_id": "diag-zone-1",
            "user_id": "diag-user-0001",
            "asset_id": "diag-asset-0001",
            "source_location": "diag-zone-1",
            "technique_id": None,
            "ts": 1725000000001,
            "severity": "critical",
            "decision_id": "decision-diag-0001",
        },
    ])

    events = run(CampaignRepository(graph).fetch_recent_events())

    assert events[0]["source_entity_id"] == "diag-zone-1"
    assert events[0]["user_id"] == "diag-user-0001"
    assert events[0]["asset_id"] == "diag-asset-0001"
    assert events[0]["source_location"] == "diag-zone-1"
    assert events[0]["category"] == "credential_access"
    assert "COALESCE(a.source_entity_id, d.source_id) AS source_entity_id" in graph.queries[0]
    assert "COALESCE(a.category, d.category) AS category" in graph.queries[0]
