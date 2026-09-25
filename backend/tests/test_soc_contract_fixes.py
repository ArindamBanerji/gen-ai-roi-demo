import os
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.routers import compat_router, discoveries_router, framework_router, soc_demo_beats


PAIR = {
    "A": {
        "alert_id": "A",
        "category": "credential_access",
        "severity": "low",
        "user_id": "u-1",
        "asset_id": "a-1",
        "planted": True,
        "sample": True,
        "origin": "fixture",
    },
    "B": {
        "alert_id": "B",
        "category": "lateral_movement",
        "severity": "low",
        "user_id": "u-1",
        "asset_id": "a-1",
    },
}


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(compat_router.router, prefix="/api")
    app.include_router(discoveries_router.router, prefix="/api")
    app.include_router(soc_demo_beats.router, prefix="/api")
    return app


def test_fingerprint_alias_has_engine(monkeypatch):
    class Scorer:
        def fingerprint(self):
            return {"factors": []}

    monkeypatch.setattr(compat_router, "_compound_scorer", lambda: Scorer())
    response = TestClient(_app()).get("/api/fingerprint")
    assert response.status_code == 200
    assert response.json()["engine"]["domain"] == "soc"


def test_trajectory_alias_has_engine(monkeypatch):
    class Scorer:
        def trajectory(self):
            return {"points": [], "current_iks": 0.4}

    monkeypatch.setattr(compat_router, "_compound_scorer", lambda: Scorer())
    response = TestClient(_app()).get("/api/trajectory")
    body = response.json()
    assert response.status_code == 200
    assert body["engine"]["domain"] == "soc"
    assert body["decisions_total"] == 0


def test_conservation_alias_flat(monkeypatch):
    async def health():
        return {
            "status": "GREEN",
            "components": {"alpha": 0.8, "q": 0.7, "V": 12, "n": 12},
        }

    monkeypatch.setattr(framework_router, "learning_health", health)
    response = TestClient(_app()).get("/api/conservation/status")
    body = response.json()
    assert response.status_code == 200
    assert body["verified_count"] == 12
    assert body["V"] == 12
    assert body["domain"] == "soc"


def test_missed_decisions_is_list(monkeypatch):
    async def comparison():
        return {"decisions_since_freeze": 7, "missed_decisions": ["d-2"]}

    async def decisions():
        return []

    monkeypatch.setattr(soc_demo_beats, "get_frozen_comparison", comparison)
    monkeypatch.setattr(soc_demo_beats, "_recent_decisions", decisions)
    body = TestClient(_app()).get("/api/learning/frozen-twin").json()
    assert isinstance(body["missed_decisions"], list)


def test_decisions_since_freeze_is_int(monkeypatch):
    async def comparison():
        return {"decisions_since_freeze": 7, "missed_decisions": []}

    monkeypatch.setattr(soc_demo_beats, "get_frozen_comparison", comparison)
    async def decisions():
        return []

    monkeypatch.setattr(soc_demo_beats, "_recent_decisions", decisions)
    body = TestClient(_app()).get("/api/learning/frozen-twin").json()
    assert body["decisions_since_freeze"] == 7
    assert isinstance(body["decisions_since_freeze"], int)


def test_killchain_forward(monkeypatch):
    async def get_alert(alert_id):
        return PAIR[alert_id]

    monkeypatch.setattr(discoveries_router.graph_client, "get_alert", get_alert)
    body = TestClient(_app()).post("/api/alert/cross-correlate", json={"alert_ids": ["A", "B"]}).json()
    assert body["correlation"]["kill_chain_detected"] is True
    assert body["correlation"]["pattern_direction"] == "forward"


def test_killchain_reverse(monkeypatch):
    async def get_alert(alert_id):
        return PAIR[alert_id]

    monkeypatch.setattr(discoveries_router.graph_client, "get_alert", get_alert)
    body = TestClient(_app()).post("/api/alert/cross-correlate", json={"alert_ids": ["B", "A"]}).json()
    assert body["correlation"]["kill_chain_detected"] is True
    assert body["correlation"]["pattern_direction"] == "reverse"


def test_killchain_confidence_not_hardcoded(monkeypatch):
    async def get_alert(alert_id):
        return PAIR[alert_id]

    monkeypatch.setattr(discoveries_router.graph_client, "get_alert", get_alert)
    response = TestClient(_app()).post("/api/alert/cross-correlate", json={"alert_ids": ["A", "B"]})
    assert response.json()["correlation"]["confidence"] == 0.5


def test_killchain_provenance_preserved(monkeypatch):
    async def get_alert(alert_id):
        return PAIR[alert_id]

    monkeypatch.setattr(discoveries_router.graph_client, "get_alert", get_alert)
    body = TestClient(_app()).post("/api/alert/cross-correlate", json={"alert_ids": ["A", "B"]}).json()
    alert = body["correlation"]["alert_1"]
    assert alert["planted"] is True
    assert alert["sample"] is True
    assert alert["origin"] == "fixture"


def test_killchain_evidence_tier(monkeypatch):
    async def get_alert(alert_id):
        return PAIR[alert_id]

    monkeypatch.setattr(discoveries_router.graph_client, "get_alert", get_alert)
    body = TestClient(_app()).post("/api/alert/cross-correlate", json={"alert_ids": ["A", "B"]}).json()
    assert body["correlation"]["evidence_tier"] == "T_H"
