"""Standing data integrity checks — run after any bulk graph operation."""
import pytest
import asyncio
import os

pytestmark = pytest.mark.skipif(
    os.getenv("GRAPH_BACKEND") != "age",
    reason="AGE integration test"
)

@pytest.fixture
def graph_client():
    from ci_platform.graph import get_graph_client
    return get_graph_client()

@pytest.mark.asyncio
async def test_no_orphan_decisions(graph_client):
    r = await graph_client.run_query(
        "MATCH (d:Decision) WHERE NOT EXISTS((d)-[:DECIDED_ON]->()) "
        "RETURN count(d) AS n"
    )
    orphans = int(r[0]["n"])
    assert orphans < 50, f"Found {orphans} orphan Decision nodes (no DECIDED_ON edge)"

@pytest.mark.asyncio
async def test_correct_outcome_coverage(graph_client):
    r = await graph_client.run_query(
        "MATCH (d:Decision)-[:DECIDED_ON]->() "
        "WHERE d.outcome IS NULL AND d.origin IS NOT NULL "
        "RETURN count(d) AS n"
    )
    missing = int(r[0]["n"])
    assert missing < 100, (
        f"{missing} Decision nodes with origin set but outcome=NULL. "
        f"Run: python support/setup/seed_zero_day.py --backfill && "
        f"python support/setup/bootstrap_learning_loop.py --live"
    )

@pytest.mark.asyncio
async def test_correct_decisions_nonzero(graph_client):
    r = await graph_client.run_query(
        "MATCH (d:Decision) WHERE d.correct = true RETURN count(d) AS n"
    )
    correct = int(r[0]["n"])
    assert correct > 1000, (
        f"correct_decisions={correct} — expected >1000. "
        f"Data may have been wiped by a bulk operation."
    )

@pytest.mark.asyncio
async def test_categories_are_canonical(graph_client):
    r = await graph_client.run_query(
        "MATCH (d:Decision) RETURN DISTINCT d.category AS cat"
    )
    cats = {row["cat"] for row in r if row["cat"]}
    VALID = {"credential_access", "malware_execution", "lateral_movement",
             "data_exfiltration", "insider_threat", "cloud_infrastructure"}
    invalid = cats - VALID
    assert not invalid, f"Non-canonical categories found: {invalid}"
