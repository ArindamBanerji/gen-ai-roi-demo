"""Cross-domain regression coverage for SOC Decision graph reads and writes."""

import re

import pytest

from ci_platform.graph.age_client import AGEClient
from app.db.graph_client import soc_decision_where
from app.services.graph_explorer import GraphExplorerService
from app.services.state_manager import StateManager
from app.state.graph_snapshot import GraphSnapshot


class InMemorySocGraphClient(AGEClient):
    """Query-aware test double that fails closed when SOC predicates disappear."""

    def __init__(self, decisions=()):
        self.decisions = [dict(decision) for decision in decisions]
        self.created_decisions = []
        self.queries = []

    def _matching_decisions(self, query):
        decisions = list(self.decisions)
        if "d.domain = 'soc'" in query:
            decisions = [d for d in decisions if d.get("domain") == "soc"]
        if "d.archived IS NULL OR d.archived <> true" in query:
            decisions = [d for d in decisions if d.get("archived") is not True]
        if "d.archived = true" in query:
            decisions = [d for d in decisions if d.get("archived") is True]
        return decisions

    async def run_query(self, query, parameters=None):
        self.queries.append(query)
        if "SET d.domain" in query and "RETURN d" in query and parameters:
            if parameters.get("did"):
                self.created_decisions.append({
                    "decision_id": parameters.get("did"),
                    "domain": "soc",
                })
            return []
        if "CREATE (d)-[:DECIDED_ON]" in query:
            return []
        if "CREATE (d:Decision" in query:
            decision_id = re.search(r"decision_id:\s*'([^']+)'", query)
            domain = re.search(r"domain:\s*'([^']+)'", query)
            self.created_decisions.append({
                "decision_id": decision_id.group(1) if decision_id else None,
                "domain": domain.group(1) if domain else None,
            })
            return []

        decisions = self._matching_decisions(query)
        if "DETACH DELETE d, ctx" in query:
            deleted_ids = {d["decision_id"] for d in decisions}
            self.decisions = [
                d for d in self.decisions
                if d["decision_id"] not in deleted_ids
            ]
            return []
        if "RETURN count(CASE WHEN d.origin" in query:
            return [{"n": sum(
                d.get("origin") == "zero_day_synthetic"
                for d in decisions
            )}]
        if "RETURN count(d) AS n" in query:
            return [{"n": len(decisions)}]
        if "RETURN d.decision_id AS id" in query:
            return [
                {
                    "id": d["decision_id"],
                    "category": d["category"],
                    "action": d.get("action"),
                    "confidence": d.get("confidence"),
                    "auto_approved": d.get("auto_approved"),
                }
                for d in decisions
            ]
        if "count(DISTINCT d.decision_id)" in query:
            verified = [
                d for d in decisions
                if (
                    d.get("status") in {"confirmed", "overridden"}
                    if d.get("status") is not None
                    else d.get("outcome") is not None
                )
            ]
            return [{"cnt": len(verified)}]
        if "d.status IS NULL AND d.correct = true" in query:
            return [{"cnt": sum(
                d.get("status") is None and d.get("correct") is True
                for d in decisions
            )}]
        if "RETURN d.category AS category" in query:
            counts = {}
            for decision in decisions:
                if decision.get("outcome") is not None and decision.get("category"):
                    category = decision["category"]
                    counts[category] = counts.get(category, 0) + 1
            return [
                {"category": category, "cnt": count}
                for category, count in counts.items()
            ]
        if "count(d) AS total" in query:
            verified = [d for d in decisions if d.get("outcome") is not None]
            overrides = [d for d in verified if d.get("was_override") is True]
            qualities = [
                d["quality_signal"] for d in overrides
                if d.get("quality_signal") is not None
            ]
            return [{
                "total": len(verified),
                "overrides": len(overrides),
                "avg_quality": sum(qualities) / len(qualities) if qualities else None,
            }]
        if "RETURN d.decision_id AS decision_id" in query:
            return [{"decision_id": d["decision_id"]} for d in decisions]
        raise AssertionError(f"Unexpected test query: {query}")

    async def compute_iks(self):
        return 1.0


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
async def test_v_soc_baseline():
    client = InMemorySocGraphClient([
        _decision("SOC-1", "soc", "malware"),
        _decision("SOC-2", "soc", "malware", status="overridden"),
        _decision("SOC-3", "soc", "phishing", status=None, correct=True),
        _decision("TRADING-1", "trading", "mean_reversion"),
    ])

    v_soc = await client.count_verified_decisions()

    assert v_soc == 3


@pytest.mark.asyncio
async def test_foreign_decision_excluded_from_soc_counts():
    client = InMemorySocGraphClient([
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
async def test_foreign_decision_excluded_from_category_counts():
    client = InMemorySocGraphClient([
        _decision("SOC-1", "soc", "malware"),
        _decision("TRADING-1", "trading", "mean_reversion"),
    ])

    categories = await client.count_decisions_by_category()

    assert categories == {"malware": 1}
    assert "mean_reversion" not in categories


@pytest.mark.asyncio
async def test_foreign_decision_excluded_from_outcome_stats():
    client = InMemorySocGraphClient([
        _decision("SOC-1", "soc", "malware", was_override=False),
        _decision("SOC-2", "soc", "malware", was_override=True, quality_signal=0.8),
        _decision("TRADING-1", "trading", "mean_reversion", was_override=True, quality_signal=0.1),
    ])

    outcome_stats = await client.compute_outcome_stats()

    assert outcome_stats == {"override_rate": 0.5, "override_quality": 0.8}


@pytest.mark.asyncio
async def test_soc_write_sets_domain():
    client = InMemorySocGraphClient()

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

    assert any(row.get("decision_id") == "SOC-WRITE-1" for row in client.created_decisions)
    assert all(row.get("domain") == "soc" for row in client.created_decisions)


def test_soc_decision_where_helper_exact():
    active = soc_decision_where()
    inactive = soc_decision_where(active_only=False)

    for result in (active, inactive):
        assert "d.domain IS NULL" not in result
        assert "d.domain = 'soc'" in result
    assert "(d.archived IS NULL OR d.archived <> true)" in active
    assert inactive == "d.domain = 'soc'"


@pytest.mark.asyncio
async def test_archive_scoped_to_soc():
    client = InMemorySocGraphClient([
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
async def test_explorer_excludes_foreign_decisions():
    client = InMemorySocGraphClient([
        _decision("SOC-1", "soc", "malware"),
        _decision("TRADING-1", "trading", "mean_reversion"),
    ])

    result = await GraphExplorerService.run_prebuilt_query(
        "recent_decisions", client
    )

    assert result["rows"] == [{
        "id": "SOC-1",
        "category": "malware",
        "action": None,
        "confidence": None,
        "auto_approved": None,
    }]


@pytest.mark.asyncio
async def test_mutation_excludes_foreign_decisions():
    client = InMemorySocGraphClient([
        _decision("SOC-1", "soc", "malware"),
        _decision("TRADING-1", "trading", "mean_reversion"),
    ])
    state_manager = StateManager(None, None, client, None)

    await state_manager.delete_session_decisions()

    assert client.decisions == [
        _decision("TRADING-1", "trading", "mean_reversion")
    ]


@pytest.mark.asyncio
async def test_graph_snapshot_uses_scoped_methods():
    client = InMemorySocGraphClient([
        _decision("SOC-1", "soc", "malware", status=None, correct=True),
        _decision("SOC-2", "soc", "phishing", status=None, correct=True),
        _decision("TRADING-1", "trading", "mean_reversion", status=None, correct=True),
    ])

    snapshot = await GraphSnapshot.from_graph(client)

    assert snapshot.verified_decisions == 2
    assert snapshot.correct_decisions == 2
    assert snapshot.category_counts == {"malware": 1, "phishing": 1}
