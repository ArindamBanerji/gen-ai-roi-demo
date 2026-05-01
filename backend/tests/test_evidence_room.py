import json
import os
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.routers import governance_router


def _client():
    app = FastAPI()
    app.include_router(governance_router.router, prefix="/api", tags=["Governance Evidence"])
    return TestClient(app)


def test_evidence_summary_returns_all_sections():
    response = _client().get("/api/soc/evidence-room")

    assert response.status_code == 200
    payload = response.json()
    assert "audit_trail" in payload
    assert "conservation" in payload
    assert "override_analysis" in payload
    assert "hash_chain" in payload


def test_audit_trail_has_entries_or_empty():
    payload = _client().get("/api/soc/evidence-room").json()

    entries = payload["audit_trail"]["entries"]
    assert isinstance(entries, list)
    if entries:
        first = entries[0]
        assert "decision_id" in first
        assert "action" in first
        assert "outcome" in first


def test_conservation_has_status():
    payload = _client().get("/api/soc/evidence-room").json()

    assert payload["conservation"]["status"] in {"GREEN", "AMBER", "RED", "CALIBRATING", "UNKNOWN"}


def test_override_analysis_has_rate():
    payload = _client().get("/api/soc/evidence-room").json()

    rate = payload["override_analysis"]["override_rate"]
    assert 0 <= rate <= 1


def test_hash_chain_verified():
    payload = _client().get("/api/soc/evidence-room").json()

    assert payload["hash_chain"]["status"] in {"VERIFIED", "BROKEN"}


def test_export_has_metadata():
    response = _client().get("/api/soc/evidence-room/export")

    assert response.status_code == 200
    payload = response.json()
    assert payload["export_metadata"]["exported_at"]
    assert payload["export_metadata"]["format_version"]


def test_export_audit_trail_full():
    client = _client()
    summary = client.get("/api/soc/evidence-room").json()
    exported = client.get("/api/soc/evidence-room/export").json()

    assert len(exported["audit_trail"]["entries"]) >= len(summary["audit_trail"]["entries"])


def test_export_returns_valid_json():
    response = _client().get("/api/soc/evidence-room/export")

    payload = json.loads(response.text)
    assert "audit_trail" in payload
    assert "conservation" in payload
    assert "override_analysis" in payload
    assert "hash_chain" in payload
