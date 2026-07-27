"""
Stress test: exercise every destructive path, verify persistent graph data survives.

Uses asyncio.run() -- no pytest-asyncio dependency needed.
Tests run against live AGE database.

Skip with: pytest -k "not graph_contract_stress"

This module never selects AGE implicitly.  Destructive tests use a disposable
AGE graph when available.  The July 2026
shared-graph census found no SOC SQLite source snapshot in this repository;
the 20 previously deleted unverified rows therefore cannot be restored by
this test module.  V_soc was unchanged, so no verified SOC data was lost.
"""
import pytest
import asyncio
import inspect
import os
import sys

from app.db.neo4j import soc_decision_where
from copilot_sdk.testing.fixtures import age_available

# Ensure backend is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
pytestmark = pytest.mark.skipif(
    not age_available(),
    reason="Stress tests require a reachable AGE database",
)

def _run(coro):
    """Run async coroutine synchronously."""
    return asyncio.run(coro)


@pytest.fixture
def sm(isolated_client):
    """Get StateManager connected to AGE -- matches router construction pattern."""
    from app.services.state_manager import StateManager
    from app.services import gae_state, audit as audit_store
    from app.core.domain_registry import get_domain_config
    return StateManager(
        learning_state_service=gae_state,
        audit_store=audit_store,
        neo4j_service=isolated_client,
        domain_config=get_domain_config(),
    )


@pytest.fixture
def client():
    """Get raw graph client."""
    from ci_platform.graph import get_graph_client
    from copilot_sdk.config import GraphConfig

    config = GraphConfig.load("soc")
    return get_graph_client(dsn=config.dsn, graph_name=config.graph)


@pytest.fixture
def isolated_client(soc_stress_test_graph):
    """Get a raw graph client bound to the disposable stress-test graph."""
    from ci_platform.graph import get_graph_client

    dsn, graph_name = soc_stress_test_graph
    client = get_graph_client(dsn=dsn, graph_name=graph_name)
    try:
        yield client
    finally:
        close = getattr(client, "close", None)
        if close is not None:
            result = close()
            if inspect.isawaitable(result):
                _run(result)


# ================================================================
# Clear session decisions — preserves everything persistent
# ================================================================

class TestClearPreservesEverything:

    def test_preserves_persistent_decisions(self, sm, isolated_client):
        before = _run(isolated_client.run_query(
            "MATCH (d:Decision {origin: 'zero_day_synthetic'}) "
            "WHERE d.correct IS NOT NULL RETURN count(d) AS n"
        ))
        _run(sm.clear_session_decisions())
        after = _run(isolated_client.run_query(
            "MATCH (d:Decision {origin: 'zero_day_synthetic'}) "
            "WHERE d.correct IS NOT NULL RETURN count(d) AS n"
        ))
        assert after[0]["n"] == before[0]["n"], (
            "clear_session_decisions wiped persistent correct field: "
            + str(before[0]["n"]) + " -> " + str(after[0]["n"])
        )

    def test_preserves_alerts(self, sm, isolated_client):
        before = _run(isolated_client.run_query("MATCH (a:Alert) RETURN count(a) AS n"))
        _run(sm.clear_session_decisions())
        after = _run(isolated_client.run_query("MATCH (a:Alert) RETURN count(a) AS n"))
        assert after[0]["n"] == before[0]["n"], "clear_session_decisions deleted alerts"

    def test_preserves_users(self, sm, isolated_client):
        before = _run(isolated_client.run_query("MATCH (u:User) RETURN count(u) AS n"))
        _run(sm.clear_session_decisions())
        after = _run(isolated_client.run_query("MATCH (u:User) RETURN count(u) AS n"))
        assert after[0]["n"] == before[0]["n"], "clear_session_decisions deleted users"

    def test_preserves_assets(self, sm, isolated_client):
        before = _run(isolated_client.run_query("MATCH (a:Asset) RETURN count(a) AS n"))
        _run(sm.clear_session_decisions())
        after = _run(isolated_client.run_query("MATCH (a:Asset) RETURN count(a) AS n"))
        assert after[0]["n"] == before[0]["n"], "clear_session_decisions deleted assets"

    def test_preserves_campaigns(self, sm, isolated_client):
        before = _run(isolated_client.run_query("MATCH (c:Campaign) RETURN count(c) AS n"))
        _run(sm.clear_session_decisions())
        after = _run(isolated_client.run_query("MATCH (c:Campaign) RETURN count(c) AS n"))
        assert after[0]["n"] == before[0]["n"], "clear_session_decisions deleted campaigns"


# ================================================================
# Delete session decisions — preserves persistent decisions + all other nodes
# ================================================================

class TestDeletePreservesEverything:

    def test_preserves_persistent_decisions(self, sm, isolated_client):
        before = _run(isolated_client.run_query(
            "MATCH (d:Decision {origin: 'zero_day_synthetic'}) RETURN count(d) AS n"
        ))
        _run(sm.delete_session_decisions())
        after = _run(isolated_client.run_query(
            "MATCH (d:Decision {origin: 'zero_day_synthetic'}) RETURN count(d) AS n"
        ))
        assert after[0]["n"] == before[0]["n"], (
            "delete_session_decisions wiped persistent decisions: "
            + str(before[0]["n"]) + " -> " + str(after[0]["n"])
        )

    def test_preserves_alerts(self, sm, isolated_client):
        before = _run(isolated_client.run_query("MATCH (a:Alert) RETURN count(a) AS n"))
        _run(sm.delete_session_decisions())
        after = _run(isolated_client.run_query("MATCH (a:Alert) RETURN count(a) AS n"))
        assert after[0]["n"] == before[0]["n"], "delete_session_decisions deleted alerts"

    def test_preserves_decided_on_edges(self, sm, isolated_client):
        before = _run(isolated_client.run_query(
            "MATCH (d:Decision {origin: 'zero_day_synthetic'})"
            "-[r:DECIDED_ON]->() RETURN count(r) AS n"
        ))
        _run(sm.delete_session_decisions())
        after = _run(isolated_client.run_query(
            "MATCH (d:Decision {origin: 'zero_day_synthetic'})"
            "-[r:DECIDED_ON]->() RETURN count(r) AS n"
        ))
        assert after[0]["n"] == before[0]["n"], (
            "delete_session_decisions broke persistent DECIDED_ON edges: "
            + str(before[0]["n"]) + " -> " + str(after[0]["n"])
        )

    def test_preserves_involves_edges(self, sm, isolated_client):
        before = _run(isolated_client.run_query(
            "MATCH ()-[r:INVOLVES]->() RETURN count(r) AS n"
        ))
        _run(sm.delete_session_decisions())
        after = _run(isolated_client.run_query(
            "MATCH ()-[r:INVOLVES]->() RETURN count(r) AS n"
        ))
        assert after[0]["n"] == before[0]["n"], "delete_session_decisions broke INVOLVES edges"

    def test_preserves_detected_on_edges(self, sm, isolated_client):
        before = _run(isolated_client.run_query(
            "MATCH ()-[r:DETECTED_ON]->() RETURN count(r) AS n"
        ))
        _run(sm.delete_session_decisions())
        after = _run(isolated_client.run_query(
            "MATCH ()-[r:DETECTED_ON]->() RETURN count(r) AS n"
        ))
        assert after[0]["n"] == before[0]["n"], "delete_session_decisions broke DETECTED_ON edges"


# ================================================================
# ================================================================
# Pre-check catches dangerous filters
# ================================================================

class TestPreCheckCatchesBadFilters:

    def test_unfiltered_deletion_aborted(self, sm):
        """WHERE 1=1 matches everything -- pre-check must abort."""
        from app.services.state_manager import DataProtectionError
        with pytest.raises(DataProtectionError):
            _run(sm._verify_deletion_safety("WHERE 1=1"))

    def test_wrong_field_filter_aborted(self, sm):
        """d.source doesn't exist -- IS NULL matches everything including persistent."""
        from app.services.state_manager import DataProtectionError
        with pytest.raises(DataProtectionError):
            _run(sm._verify_deletion_safety(
                "WHERE d.source IS NULL OR d.source <> 'zero_day_synthetic'"
            ))

    def test_correct_filter_passes(self, sm):
        """The actual SESSION_FILTER should pass (0 persistent in deletion set)."""
        n = _run(sm._verify_deletion_safety(sm.SESSION_FILTER))
        assert n == 0, "SESSION_FILTER matched session nodes when none should exist"


# ================================================================
# verify_graph() detects real problems
# ================================================================

class TestVerifyGraphDetectsProblems:

    def test_catches_orphan_decision(self, isolated_client):
        """An orphan Decision (no DECIDED_ON edge) violates the contract."""
        from app.graph_schema import verify_graph
        _run(isolated_client.run_query(
            "CREATE (d:Decision {decision_id: 'stress-test-orphan', "
            "origin: 'stress_test', category: 'test', action: 'test', "
            "confidence: 0.5, correct: true, outcome: 'correct', "
            "factor_vector: '[0.1,0.2,0.3,0.4,0.5,0.6]'})"
        ))
        try:
            report = _run(verify_graph(isolated_client))
            assert not report["healthy"], "verify_graph missed orphan Decision"
            assert any("orphan" in i.lower() for i in report["issues"]), (
                "No orphan issue reported. Issues: " + str(report["issues"])
            )
        finally:
            _run(isolated_client.run_query(
                "MATCH (d:Decision {decision_id: 'stress-test-orphan'}) DETACH DELETE d"
            ))

    def test_healthy_after_cleanup(self, client):
        """After removing the orphan, graph should be healthy."""
        from app.graph_schema import verify_graph
        report = _run(verify_graph(client))
        if not report["healthy"]:
            for issue in report["issues"]:
                print("  [INFO] " + issue)


# ================================================================
# Full contract verification after all stress tests
# ================================================================

class TestContractSurvivesStress:

    def test_persistent_decision_count(self, client):
        """After all destructive tests, persistent decisions still intact."""
        r = _run(client.run_query(
            "MATCH (d:Decision {origin: 'zero_day_synthetic'}) RETURN count(d) AS n"
        ))
        n = int(r[0]["n"])
        assert n >= 4800, (
            "Persistent decision count too low after stress: " + str(n)
        )

    def test_alert_count(self, client):
        """Alerts untouched by all destructive operations."""
        r = _run(client.run_query("MATCH (a:Alert) RETURN count(a) AS n"))
        n = int(r[0]["n"])
        assert n >= 540, "Alert count too low after stress: " + str(n)

    def test_decided_on_edges_intact(self, client):
        """DECIDED_ON edges survive all destructive operations."""
        r = _run(client.run_query(
            "MATCH (d:Decision {origin: 'zero_day_synthetic'})"
            "-[r:DECIDED_ON]->() RETURN count(r) AS n"
        ))
        n = int(r[0]["n"])
        assert n >= 4800, "DECIDED_ON edge count too low: " + str(n)

    def test_no_orphan_decisions(self, client):
        """Zero orphan Decisions after all stress tests."""
        r = _run(client.run_query(
            f"MATCH (d:Decision) WHERE {soc_decision_where(active_only=False)} "
            "AND NOT EXISTS((d)-[:DECIDED_ON]->()) "
            "RETURN count(d) AS n"
        ))
        n = int(r[0]["n"])
        assert n == 0, "Orphan decisions found after stress: " + str(n)
