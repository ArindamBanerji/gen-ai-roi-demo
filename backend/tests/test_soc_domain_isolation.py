"""Cross-domain regression coverage for SOC Decision graph reads and writes."""

import re

import pytest

from ci_platform.graph.age_client import AGEClient
from app.db.graph_client import soc_decision_where
from app.services.graph_explorer import GraphExplorerService
from app.services.state_manager import StateManager
from app.state.graph_snapshot import GraphSnapshot


def _soc_client(age_graph, decisions=()):
    for decision in decisions:
        age_graph.decision(**decision)
    return age_graph.client


def _decision(
    decision_id,
    domain,
    category,
    *,
    status="confirmed",
    outcome="correct",
    correct=False,
    archived=False,
    was_override=False,
    quality_signal=None,
):
    return {
        "decision_id": decision_id,
        "domain": domain,
        "category": category,
        "status": status,
        "outcome": outcome,
        "correct": correct,
        "archived": archived,
        "was_override": was_override,
        "quality_signal": quality_signal,
    }


@pytest.mark.asyncio
@pytest.mark.age
async def test_v_soc_baseline(age_graph):
    client = _soc_client(age_graph, [
        _decision("SOC-1", "soc", "malware"),
        _decision("SOC-2", "soc", "malware", status="overridden"),
        _decision("SOC-3", "soc", "phishing", status="confirmed", correct=True),
        _decision("TRADING-1", "trading", "mean_reversion"),
    ])

    v_soc = await client.count_verified_decisions()

    assert v_soc == 3


@pytest.mark.asyncio
@pytest.mark.age
async def test_foreign_decision_excluded_from_soc_counts(age_graph):
    client = _soc_client(age_graph, [
        _decision("TRADING-1", "trading", "mean_reversion", correct=True),
        _decision("PURCHASING-1", "purchasing", "supplier_risk", correct=True),
        _decision("DATAOPS-1", "dataops", "pipeline_health", correct=True),
        _decision("S2P-1", "s2p", "procurement", correct=True),
    ])

    verified = await client.count_verified_decisions()
    correct = await client.count_correct_decisions()
    categories = await client.count_decisions_by_category()
    outcome_stats = await client.compute_outcome_stats()

    assert verified == 0
    assert correct == 0
    assert categories == {}
    assert outcome_stats == {"override_rate": 0.0, "override_quality": 0.0}


@pytest.mark.asyncio
@pytest.mark.age
async def test_foreign_decision_excluded_from_category_counts(age_graph):
    client = _soc_client(age_graph, [
        _decision("SOC-1", "soc", "malware"),
        _decision("TRADING-1", "trading", "mean_reversion"),
    ])

    categories = await client.count_decisions_by_category()

    assert categories == {"malware": 1}
    assert "mean_reversion" not in categories


@pytest.mark.asyncio
@pytest.mark.age
async def test_foreign_decision_excluded_from_outcome_stats(age_graph):
    client = _soc_client(age_graph, [
        _decision("SOC-1", "soc", "malware", was_override=False),
        _decision("SOC-2", "soc", "malware", was_override=True, quality_signal=0.8),
        _decision("TRADING-1", "trading", "mean_reversion", was_override=True, quality_signal=0.1),
    ])

    outcome_stats = await client.compute_outcome_stats()

    assert outcome_stats == {"override_rate": 0.5, "override_quality": 0.8}


@pytest.mark.asyncio
@pytest.mark.age
async def test_soc_write_sets_domain(age_graph):
    client = _soc_client(age_graph)

    await client.create_decision_trace(
        decision_id="SOC-WRITE-1",
        alert_id="ALERT-1",
        action="contain",
        confidence=0.9,
        category="malware",
        reasoning="test",
        pattern_id=None,
        playbook_id=None,
        nodes_consulted=1,
        context_snapshot={},
    )

    rows = age_graph.query("MATCH (d:Decision) RETURN d.decision_id AS decision_id, d.domain AS domain")
    assert rows == [{"decision_id": "SOC-WRITE-1", "domain": "soc"}]


def test_soc_decision_where_helper_exact():
    active = soc_decision_where()
    inactive = soc_decision_where(active_only=False)

    for result in (active, inactive):
        assert "d.domain IS NULL" not in result
        assert "d.domain = 'soc'" in result
    assert "(d.archived IS NULL OR d.archived <> true)" in active
    assert inactive == "d.domain = 'soc'"


@pytest.mark.asyncio
@pytest.mark.age
async def test_archive_scoped_to_soc(age_graph):
    client = _soc_client(age_graph, [
        _decision("SOC-ARCHIVED", "soc", "malware", archived=True),
        _decision("TRADING-ARCHIVED", "trading", "mean_reversion", archived=True),
    ])

    archived = await client.run_query(
        "MATCH (d:Decision) WHERE "
        f"{soc_decision_where(active_only=False)} AND d.archived = true "
        "RETURN d.decision_id AS decision_id"
    )

    assert archived == [{"decision_id": "SOC-ARCHIVED"}]


@pytest.mark.asyncio
@pytest.mark.age
async def test_explorer_excludes_foreign_decisions(age_graph):
    client = _soc_client(age_graph, [
        _decision("SOC-1", "soc", "malware"),
        _decision("TRADING-1", "trading", "mean_reversion"),
    ])

    result = await GraphExplorerService.run_prebuilt_query(
        "recent_decisions", client
    )

    assert result["rows"] == [{
        "id": "SOC-1",
        "category": "malware",
        "action": "investigate",
        "confidence": 0.8,
        "auto_approved": None,
    }]


@pytest.mark.asyncio
@pytest.mark.age
async def test_mutation_excludes_foreign_decisions(age_graph):
    client = _soc_client(age_graph, [
        _decision("SOC-1", "soc", "malware"),
        _decision("TRADING-1", "trading", "mean_reversion"),
    ])
    state_manager = StateManager(None, None, client, None)

    await state_manager.delete_session_decisions()

    assert age_graph.query("MATCH (d:Decision) RETURN d.decision_id AS decision_id") == [{"decision_id": "TRADING-1"}]



@pytest.mark.asyncio
@pytest.mark.age
async def test_graph_snapshot_uses_scoped_methods(age_graph):
    client = _soc_client(age_graph, [
        _decision("SOC-1", "soc", "malware", status="confirmed", correct=True),
        _decision("SOC-2", "soc", "phishing", status="confirmed", correct=True),
        _decision("TRADING-1", "trading", "mean_reversion", status="confirmed", correct=True),
    ])

    snapshot = await GraphSnapshot.from_graph(client)

    assert snapshot.verified_decisions == 2
    assert snapshot.correct_decisions == 2
    assert snapshot.category_counts == {"malware": 1, "phishing": 1}
