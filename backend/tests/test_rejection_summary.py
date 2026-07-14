from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.routers import evolution as evolution_router


client = TestClient(app)


def test_rejection_summary_returns_200(monkeypatch):
    async def fake_summary(_client):
        return {"variants_generated": 1, "variants_promoted": 0, "variants_rejected": 0}

    async def fake_events(_client, limit):
        return []

    monkeypatch.setattr(evolution_router, "get_ledger_evolution_summary", fake_summary)
    monkeypatch.setattr(evolution_router, "get_ledger_recent_events", fake_events)
    response = client.get("/api/soc/evolution/rejection-summary")
    assert response.status_code == 200


def test_rejection_summary_has_breakdown(monkeypatch):
    async def fake_summary(_client):
        return {"variants_generated": 2, "variants_promoted": 0, "variants_rejected": 1}

    async def fake_events(_client, limit):
        return [{"event_type": "PROMOTION_REJECTED", "variant_id": "SOC-V-1", "reason": "conservation"}]

    monkeypatch.setattr(evolution_router, "get_ledger_evolution_summary", fake_summary)
    monkeypatch.setattr(evolution_router, "get_ledger_recent_events", fake_events)
    body = client.get("/api/soc/evolution/rejection-summary").json()
    assert set(body["rejection_breakdown"]) == {"correctness_floor", "conservation", "variance_stability"}
    assert body["rejection_breakdown"]["conservation"] == 1


def test_rejection_summary_counts_match_log(monkeypatch):
    async def fake_summary(_client):
        return {"variants_generated": 3, "variants_promoted": 1, "variants_rejected": 2}

    async def fake_events(_client, limit):
        return [
            {"event_type": "PROMOTION_REJECTED", "variant_id": "SOC-V-1", "reason": "conservation"},
            {"event_type": "PROMOTION_REJECTED", "variant_id": "SOC-V-2", "reason": "variance_stability"},
        ]

    monkeypatch.setattr(evolution_router, "get_ledger_evolution_summary", fake_summary)
    monkeypatch.setattr(evolution_router, "get_ledger_recent_events", fake_events)
    body = client.get("/api/soc/evolution/rejection-summary").json()
    assert body["total_tested"] == 3
    assert body["total_promoted"] == 1
    assert body["total_rejected"] == 2
    assert len(body["rejected_variants"]) == 2


def test_rejection_summary_empty_when_no_rejections(monkeypatch):
    async def fake_summary(_client):
        return {"variants_generated": 0, "variants_promoted": 0, "variants_rejected": 0}

    async def fake_events(_client, limit):
        return []

    monkeypatch.setattr(evolution_router, "get_ledger_evolution_summary", fake_summary)
    monkeypatch.setattr(evolution_router, "get_ledger_recent_events", fake_events)
    body = client.get("/api/soc/evolution/rejection-summary").json()
    assert body["total_rejected"] == 0
    assert body["rejected_variants"] == []
