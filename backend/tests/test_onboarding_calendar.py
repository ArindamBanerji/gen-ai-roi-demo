"""Tests for GET /api/soc/onboarding-calendar (P8)."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_calendar_returns_six_categories():
    response = client.get("/api/soc/onboarding-calendar")
    assert response.status_code == 200
    data = response.json()
    assert len(data["predictions"]) == 6


def test_calendar_has_weeks():
    response = client.get("/api/soc/onboarding-calendar")
    data = response.json()
    for pred in data["predictions"]:
        assert "weeks" in pred
        assert pred["weeks"] > 0


def test_calendar_higher_volume_faster():
    low  = client.get("/api/soc/onboarding-calendar?alerts_per_day=50").json()
    high = client.get("/api/soc/onboarding-calendar?alerts_per_day=500").json()
    assert high["total_weeks"] < low["total_weeks"]


def test_calendar_g4_faster_than_g1():
    g1 = client.get("/api/soc/onboarding-calendar?graph_level=G1").json()
    g4 = client.get("/api/soc/onboarding-calendar?graph_level=G4").json()
    assert g4["total_weeks"] < g1["total_weeks"]


def test_calendar_default_params():
    response = client.get("/api/soc/onboarding-calendar")
    data = response.json()
    assert data["assumptions"]["alerts_per_day"] == 200
    assert data["assumptions"]["verification_rate"] == 0.30
