"""Demo replacement archives immutable real snapshots; production freeze stays pinned."""
import json
from pathlib import Path

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from gae.profile_scorer import ProfileScorer

from app.routers.soc_learning import router
from app.services.soc_learning_control import SOCLearningControlService
from copilot_sdk.graph import InMemoryGraphStore
from copilot_sdk.twin import FrozenSnapshot, FrozenTwinStore


def test_refreeze_preserves_production_and_archives_previous(tmp_path: Path) -> None:
    scorer = ProfileScorer(mu=np.full((2, 3, 4), 0.5), actions=["a", "b", "c"], categories=["one", "two"])
    graph = InMemoryGraphStore()
    store = FrozenTwinStore(graph, "soc")
    service = SOCLearningControlService(store)
    health = {"components": {"verified_decisions": 30}}
    production = service.freeze(scorer, health, 70.0, scorer.mu)
    original_bytes = store.load("soc").to_json()
    scorer.update(np.zeros(4), 0, 0, True)
    demo = service.demo_refreeze(scorer, health, 71.0)
    provenance = demo["provenance"]
    assert provenance["origin"] == "demo_reseed"
    assert provenance["archived_previous"] is True
    archived = FrozenSnapshot.from_json(json.dumps(graph.get_evolution("soc", f"frozen_twin_archive:{provenance['archive_id']}")["snapshot"]))
    assert archived.checksum == production["checksum"]
    assert store.load("soc").to_json() == original_bytes
    assert service.freeze(scorer, health, 99.0, scorer.mu)["checksum"] == production["checksum"]
    restarted = SOCLearningControlService(FrozenTwinStore(graph, "soc"))
    assert restarted.comparison(scorer, 72.0)["frozen_iks"] == 70.0
    assert "provenance" not in restarted.comparison(scorer, 72.0)
    comparison = restarted.comparison(scorer, 72.0, verified_count=31, demo=True)
    assert comparison["provenance"] == provenance
    assert comparison["frozen_iks"] == 71.0
    assert comparison["iks_delta"] == 1.0
    assert comparison["decisions_since_freeze"] == 1
    assert comparison["measured"] is True
    assert comparison["evidence_tier"] == "T_S"
    assert "synthetic" in comparison["evidence_label"]
    # A repeat archives the previous demo, not the unchanged production file.
    second = restarted.demo_refreeze(scorer, {"components": {"verified_decisions": 31}}, 72.0)
    assert second["provenance"]["previous_checksum"] == demo["checksum"]
    assert len([row for row in graph.list_evolutions("soc") if row["key"].startswith("frozen_twin_archive:")]) == 2
    assert store.load("soc").to_json() == original_bytes


def test_refreeze_rejects_missing_verified_population(tmp_path: Path) -> None:
    graph = InMemoryGraphStore()
    scorer = ProfileScorer(mu=np.full((1, 2, 2), 0.5), actions=["a", "b"], categories=["one"])
    service = SOCLearningControlService(FrozenTwinStore(graph, "soc"))
    with pytest.raises(ValueError, match="verified population"):
        service.demo_refreeze(scorer, {}, 70.0)
    assert not service.has_demo_twin()


def test_demo_route_requires_explicit_enablement(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SOC_DEMO_RESEED_ENABLED", raising=False)
    app = FastAPI()
    app.include_router(router, prefix="/api")
    with TestClient(app) as client:
        assert client.post("/api/demo/learning/re-freeze", json={"confirm_demo_reseed": True}).status_code == 403
        assert client.post("/api/demo/learning/re-freeze", json={}).status_code == 422
        assert client.post("/api/demo/learning/re-freeze", json={"confirm_demo_reseed": False}).status_code == 422
