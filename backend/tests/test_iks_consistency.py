"""
V-01 regression tests: canonical visible IKS must agree across startup,
snapshot refresh, Tab 2, and Tab 5 for the same scorer state.
"""

import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.routers.soc import _tab2_content
from app.services.executive_narrative import build_executive_narrative_async
from app.services.iks import compute_visible_iks
from app.state.graph_snapshot import GraphSnapshot


class _FakeNeo4jClient:
    def __init__(self):
        self.compute_iks = AsyncMock(return_value=0.0)

    async def count_verified_decisions(self):
        return 4860

    async def count_correct_decisions(self):
        return 3966

    async def count_decisions_by_category(self):
        return {
            "credential_access": 1000,
            "lateral_movement": 900,
        }

    async def compute_outcome_stats(self):
        return {"override_rate": 0.0, "override_quality": 0.0}

    async def run_query(self, query, params=None):
        q = " ".join(query.split())
        if "WHERE d.confidence IS NOT NULL AND d.confidence < 0.50" in q:
            return [{"cnt": 12}]
        if "MATCH (d:Decision) RETURN count(d) AS total" in q:
            return [{"total": 4860}]
        if "RETURN d.category AS category, count(d) AS n" in q and "WHERE d.outcome IS NOT NULL" not in q:
            return [
                {"category": "credential_access", "n": 1200},
                {"category": "lateral_movement", "n": 1100},
            ]
        if "WHERE d.confidence >= 0.70" in q:
            return [{"high_conf": 4200}]
        if "WHERE d.outcome IS NOT NULL RETURN d.category AS category, avg" in q:
            return [
                {"category": "credential_access", "accuracy": 0.91},
                {"category": "lateral_movement", "accuracy": 0.89},
            ]
        if "MATCH (d:Decision) RETURN count(d) AS cnt" in q:
            return [{"cnt": 4860}]
        if "MATCH (d:Decision) WHERE d.correct = true RETURN count(d) AS cnt" in q:
            return [{"cnt": 3966}]
        if "MATCH (c:Campaign) RETURN count(c) AS cnt" in q:
            return [{"cnt": 4}]
        if "MATCH (a:Alert) RETURN count(a) AS cnt" in q:
            return [{"cnt": 9200}]
        if "WHERE d.outcome IS NOT NULL RETURN d.category AS category, count(d) AS n" in q:
            return [
                {"category": "credential_access", "n": 800},
                {"category": "lateral_movement", "n": 700},
            ]
        if "RETURN d.category AS category, d.action AS action, count(d) AS n" in q:
            return [{"category": "credential_access", "action": "escalate", "n": 300}]
        if "MATCH (c:Campaign) RETURN c.campaign_id AS id, c.name AS name" in q:
            return [{"id": "c1", "name": "cred campaign", "alert_count": 120, "category_sequence": "[\"credential_access\"]"}]
        if "MATCH ()-[e:TRIGGERED_EVOLUTION]->()" in q:
            return [{"cnt": 9}]
        return [{"cnt": 0}]


def _fake_scorer():
    return SimpleNamespace(centroids="sentinel-centroids")


@pytest.mark.asyncio
async def test_iks_startup_matches_tab2():
    fake_client = _FakeNeo4jClient()
    with patch("app.services.gae_state.get_profile_scorer", return_value=_fake_scorer()):
        with patch("app.services.iks.compute_iks", return_value={"current": 89.0}):
            with patch("app.routers.soc.neo4j_client", fake_client):
                snap = await GraphSnapshot.from_graph(fake_client)
                tab2 = await _tab2_content()

    assert snap.iks_score == 89.0
    assert tab2["iks_score"] == 89.0
    fake_client.compute_iks.assert_awaited_once()


@pytest.mark.asyncio
async def test_iks_stable_after_single_decision():
    fake_client = _FakeNeo4jClient()
    snap = GraphSnapshot(verified_decisions=4860, correct_decisions=3966, iks_score=89.0)

    with patch("app.services.gae_state.get_profile_scorer", return_value=_fake_scorer()):
        with patch("app.services.iks.compute_iks", return_value={"current": 89.0}):
            snap.on_verified_decision("credential_access", False, 1.0)
            recalculated = await compute_visible_iks(fake_client, scorer=_fake_scorer())
            snap.on_iks_recalculated(recalculated)

    assert snap.iks_score == 89.0
    assert snap.verified_decisions == 4861


@pytest.mark.asyncio
async def test_iks_snapshot_matches_tab2_after_update():
    fake_client = _FakeNeo4jClient()
    snap = GraphSnapshot(iks_score=0.0)

    with patch("app.services.gae_state.get_profile_scorer", return_value=_fake_scorer()):
        with patch("app.services.iks.compute_iks", return_value={"current": 89.0}):
            with patch("app.routers.soc.neo4j_client", fake_client):
                snap.on_iks_recalculated(await compute_visible_iks(fake_client, scorer=_fake_scorer()))
                tab2 = await _tab2_content()

    assert snap.iks_score == tab2["iks_score"] == 89.0


@pytest.mark.asyncio
async def test_iks_all_paths_agree():
    fake_client = _FakeNeo4jClient()

    with patch("app.services.gae_state.get_profile_scorer", return_value=_fake_scorer()):
        with patch("app.services.iks.compute_iks", return_value={"current": 89.0}):
            with patch("app.routers.soc.neo4j_client", fake_client):
                startup = await GraphSnapshot.from_graph(fake_client)
                tab2 = await _tab2_content()
            narrative = await build_executive_narrative_async(fake_client)
            updated = await compute_visible_iks(fake_client, scorer=_fake_scorer())

    assert startup.iks_score == 89.0
    assert tab2["iks_score"] == 89.0
    assert narrative["what_knows"]["iks_current"] == 89.0
    assert updated == 89.0
