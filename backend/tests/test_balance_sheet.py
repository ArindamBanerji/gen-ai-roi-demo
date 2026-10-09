import asyncio
from dataclasses import asdict
from unittest.mock import MagicMock

import numpy as np
from fastapi.testclient import TestClient

from app.domains.soc.config import SOC_CATEGORIES
from app.services import balance_sheet


def _run(awaitable):
    return asyncio.run(awaitable)


class _SnapshotStub:
    def __init__(self, categories, verified_decisions):
        self._categories = categories
        self.verified_decisions = verified_decisions

    def get_epistemic_state(self):
        return self._categories


class _ScorerStub:
    def __init__(self, centroids):
        self.centroids = np.array(centroids, dtype=np.float64)


def _fake_centroid_export():
    current_mu = [
        [[1.0] * 6, [1.0] * 6, [1.0] * 6, [1.0] * 6],
        [[1.2] * 6, [1.2] * 6, [1.2] * 6, [1.2] * 6],
        [[1.4] * 6, [1.4] * 6, [1.4] * 6, [1.4] * 6],
        [[1.6] * 6, [1.6] * 6, [1.6] * 6, [1.6] * 6],
        [[1.8] * 6, [1.8] * 6, [1.8] * 6, [1.8] * 6],
        [[2.2] * 6, [2.2] * 6, [2.2] * 6, [2.2] * 6],
    ]
    bootstrap_mu = [
        [[1.0] * 6, [1.0] * 6, [1.0] * 6, [1.0] * 6],
        [[1.0] * 6, [1.0] * 6, [1.0] * 6, [1.0] * 6],
        [[1.0] * 6, [1.0] * 6, [1.0] * 6, [1.0] * 6],
        [[1.0] * 6, [1.0] * 6, [1.0] * 6, [1.0] * 6],
        [[1.0] * 6, [1.0] * 6, [1.0] * 6, [1.0] * 6],
        [[1.0] * 6, [1.0] * 6, [1.0] * 6, [1.0] * 6],
    ]
    return {
        "current_mu": current_mu,
        "bootstrap_mu": bootstrap_mu,
        "categories": list(SOC_CATEGORIES),
    }


def _install_happy_path(monkeypatch):
    categories = {
        "credential_access": {"count": 600, "band": "expert"},
        "malware_execution": {"count": 320, "band": "calibrating"},
        "lateral_movement": {"count": 180, "band": "learning"},
        "data_exfiltration": {"count": 95, "band": "learning"},
        "insider_threat": {"count": 20, "band": "novice"},
        "cloud_infrastructure": {"count": 55, "band": "learning"},
    }
    monkeypatch.setattr(
        balance_sheet,
        "get_snapshot",
        lambda: _SnapshotStub(categories=categories, verified_decisions=sum(v["count"] for v in categories.values())),
    )

    async def fake_visible_iks(_graph=None):
        return 72.5

    async def fake_build_centroid_export(_scorer, _graph=None):
        return _fake_centroid_export()

    async def fake_learning_health(_graph=None):
        return {"status": "GREEN", "signal": 0.91}

    async def fake_auto_approve():
        return {
            "coverage_pct": 24.0,
            "by_category": {
                "credential_access": {"coverage_pct": 40.0},
                "malware_execution": {"coverage_pct": 20.0},
                "lateral_movement": {"coverage_pct": 15.0},
                "data_exfiltration": {"coverage_pct": 10.0},
                "insider_threat": {"coverage_pct": 0.0},
                "cloud_infrastructure": {"coverage_pct": 8.0},
            },
        }

    async def fake_timeline(_graph=None):
        return {
            "timeline": [{"snapshot_id": "one"}],
            "timeline_available": True,
            "iks_available": True,
            "ceiling_estimate": 80.0,
            "ceiling_available": True,
        }

    monkeypatch.setattr(balance_sheet, "compute_visible_iks", fake_visible_iks)
    monkeypatch.setattr(
        balance_sheet,
        "get_profile_scorer",
        lambda: _ScorerStub(_fake_centroid_export()["current_mu"]),
    )
    monkeypatch.setattr(balance_sheet, "build_centroid_export", fake_build_centroid_export)
    monkeypatch.setattr(balance_sheet.LearningHealthMonitor, "evaluate", fake_learning_health)
    monkeypatch.setattr(balance_sheet, "_safe_auto_approve_stats", fake_auto_approve)
    monkeypatch.setattr(balance_sheet, "get_evolution_timeline", fake_timeline)


def test_generate_balance_sheet_has_six_categories(monkeypatch):
    _install_happy_path(monkeypatch)

    result = _run(balance_sheet.generate_balance_sheet())

    assert len(result.categories) == 6
    assert [item.category for item in result.categories] == SOC_CATEGORIES


def test_generate_balance_sheet_overall_iks_non_negative(monkeypatch):
    _install_happy_path(monkeypatch)

    result = _run(balance_sheet.generate_balance_sheet())

    assert result.overall_iks > 0


def test_balance_sheet_ceiling_populated(monkeypatch):
    _install_happy_path(monkeypatch)

    result = _run(balance_sheet.generate_balance_sheet())

    assert all(item.ceiling_estimate is not None for item in result.categories)


def test_balance_sheet_overall_ceiling_populated(monkeypatch):
    _install_happy_path(monkeypatch)

    result = _run(balance_sheet.generate_balance_sheet())

    assert result.overall_ceiling is not None
    assert result.overall_ceiling > 0.0


def test_generate_balance_sheet_summary_has_recommendation(monkeypatch):
    _install_happy_path(monkeypatch)

    result = _run(balance_sheet.generate_balance_sheet())

    assert result.summary["recommendation"]
    assert "insider threat" in result.summary["recommendation"]


def test_pre_activation_recommendation_is_not_degraded_or_paused():
    weakest = balance_sheet.CategoryBalance(
        category="credential_access",
        epistemic_band="expert",
        verified_count=600,
        centroid_drift=0.0,
        auto_approve_rate=0.2,
        accuracy=0.0,
        accuracy_note="fallback",
        iks_contribution=0.0,
        ceiling_estimate=0.0,
        ceiling_available=False,
        status="converging",
    )

    recommendation = balance_sheet._build_recommendation(
        weakest=weakest,
        health_status="CALIBRATING",
        accuracy_fallback_used=False,
        pre_activation=True,
    )

    assert "pre-activation" in recommendation.lower()
    assert "configured" in recommendation
    assert "not yet enabled" in recommendation
    assert "degraded" not in recommendation.lower()
    assert "paused" not in recommendation.lower()
    assert "RED" not in recommendation
    assert "AMBER" not in recommendation


def test_generate_balance_sheet_strongest_and_weakest(monkeypatch):
    _install_happy_path(monkeypatch)

    result = _run(balance_sheet.generate_balance_sheet())

    assert result.summary["strongest_category"] == "credential_access"
    assert result.summary["weakest_category"] == "insider_threat"


def test_compute_status():
    assert balance_sheet._compute_status(5, "learning", 0.2) == "insufficient_data"
    assert balance_sheet._compute_status(600, "expert", 0.2, 80.0) == "converging"
    assert balance_sheet._compute_status(120, "calibrating", 0.2) == "converging"
    assert balance_sheet._compute_status(120, "learning", 0.01) == "early"


def test_balance_sheet_status_at_ceiling_when_low_ceiling():
    assert balance_sheet._compute_status(120, "learning", 0.01, 69.0) == "at_ceiling"
    assert balance_sheet._compute_status(600, "expert", 0.01, 74.0) == "at_ceiling"


def test_category_status_enum_is_restricted(monkeypatch):
    _install_happy_path(monkeypatch)

    result = _run(balance_sheet.generate_balance_sheet())

    allowed = {"at_ceiling", "converging", "early", "insufficient_data"}
    assert {item.status for item in result.categories} <= allowed


def test_learning_balance_sheet_endpoint_returns_200(monkeypatch):
    from app.main import app

    async def fake_generate(_graph=None):
        return balance_sheet.LearningBalanceSheet(
            categories=[
                balance_sheet.CategoryBalance(
                    category=category,
                    epistemic_band="novice",
                    verified_count=0,
                    centroid_drift=0.0,
                    auto_approve_rate=0.0,
                    accuracy=0.0,
                    accuracy_note="fallback",
                    iks_contribution=0.0,
                    ceiling_estimate=0.0,
                    ceiling_available=False,
                    status="insufficient_data",
                )
                for category in SOC_CATEGORIES
            ],
            overall_iks=0.0,
            iks_available=False,
            health_status="unavailable",
            overall_ceiling=0.0,
            ceiling_available=False,
            summary={"recommendation": "Collect verified outcomes."},
            notes=["fallback"],
            sources={"overall_iks": "compute_visible_iks()"},
        )

    monkeypatch.setattr("app.services.balance_sheet.generate_balance_sheet", fake_generate)
    client = TestClient(app)
    response = client.get("/api/soc/learning-balance-sheet")

    assert response.status_code == 200
    body = response.json()
    assert len(body["categories"]) == 6
    assert body["overall_ceiling"] == 0.0
    assert body["ceiling_available"] is False
    assert {item["status"] for item in body["categories"]} <= {
        "at_ceiling", "converging", "early", "insufficient_data",
    }
    assert "generated_at" in body
    assert isinstance(body["generated_at"], str)
    assert "total_verified" in body
    assert isinstance(body["total_verified"], int)
    assert body["total_verified"] >= 0


def test_generate_balance_sheet_handles_cold_start(monkeypatch):
    monkeypatch.setattr(balance_sheet, "get_snapshot", lambda: (_ for _ in ()).throw(RuntimeError("cold start")))
    monkeypatch.setattr(balance_sheet, "get_profile_scorer", lambda: None)

    async def fake_visible_iks(_graph=None):
        return 0.0

    async def fake_learning_health(_graph=None):
        return {"status": "CALIBRATING"}

    async def fake_auto_approve():
        return {"by_category": {}, "coverage_pct": 0.0}

    async def fake_timeline(_graph=None):
        return {
            "timeline": [],
            "timeline_available": False,
            "iks_available": True,
            "ceiling_estimate": 0.0,
            "ceiling_available": False,
        }

    monkeypatch.setattr(balance_sheet, "compute_visible_iks", fake_visible_iks)
    monkeypatch.setattr(balance_sheet.LearningHealthMonitor, "evaluate", fake_learning_health)
    monkeypatch.setattr(balance_sheet, "_safe_auto_approve_stats", fake_auto_approve)
    monkeypatch.setattr(balance_sheet, "get_evolution_timeline", fake_timeline)

    result = _run(balance_sheet.generate_balance_sheet())

    assert len(result.categories) == 6
    assert result.overall_iks >= 0.0
    assert result.overall_ceiling == 0.0
    assert result.ceiling_available is False
    assert result.summary["recommendation"]
    assert "epistemic state unavailable" in result.summary["recommendation"].lower()
    assert all(item.verified_count == 0 for item in result.categories)


def test_balance_sheet_iks_helper_raises(monkeypatch):
    _install_happy_path(monkeypatch)

    async def fail_iks(_graph=None):
        raise RuntimeError("iks down")

    monkeypatch.setattr(balance_sheet, "compute_visible_iks", fail_iks)
    result = _run(balance_sheet.generate_balance_sheet())

    assert result.overall_iks == 0.0
    assert result.iks_available is False
    assert result.degraded is True
    assert all(item.iks_contribution == 0.0 for item in result.categories)
    assert all(item.iks_contribution_available is False for item in result.categories)


def test_balance_sheet_epistemic_failure(monkeypatch):
    _install_happy_path(monkeypatch)
    monkeypatch.setattr(
        balance_sheet,
        "get_snapshot",
        lambda: (_ for _ in ()).throw(RuntimeError("snapshot down")),
    )

    result = _run(balance_sheet.generate_balance_sheet())

    assert result.epistemic_state_available is False
    assert result.total_verified == 0
    assert "unavailable" in result.summary["recommendation"].lower()


def test_balance_sheet_epistemic_none_is_typed_unavailable(monkeypatch):
    _install_happy_path(monkeypatch)
    snapshot = MagicMock()
    snapshot.get_epistemic_state.return_value = None
    snapshot.verified_decisions = 900
    monkeypatch.setattr(balance_sheet, "get_snapshot", lambda: snapshot)

    result = _run(balance_sheet.generate_balance_sheet())

    assert result.epistemic_state_available is False
    assert result.total_verified == 0
    assert all(item.verified_count == 0 for item in result.categories)
    assert all(isinstance(item.epistemic_band, str) for item in result.categories)
    assert "unavailable" in result.summary["recommendation"].lower()


def test_balance_sheet_partial_timeline_interaction(monkeypatch):
    _install_happy_path(monkeypatch)

    async def fail_iks(_graph=None):
        raise RuntimeError("iks down")

    monkeypatch.setattr(balance_sheet, "compute_visible_iks", fail_iks)
    result = _run(balance_sheet.generate_balance_sheet())

    assert result.timeline_available is True
    assert result.iks_available is False


def test_balance_sheet_degraded_timeline_keeps_independent_data(monkeypatch):
    _install_happy_path(monkeypatch)

    async def degraded_timeline(_graph=None):
        return {
            "timeline": [],
            "timeline_available": False,
            "iks_available": False,
            "ceiling_estimate": 0.0,
            "ceiling_available": False,
            "degraded": True,
        }

    monkeypatch.setattr(balance_sheet, "get_evolution_timeline", degraded_timeline)
    result = _run(balance_sheet.generate_balance_sheet())

    assert result.timeline_available is False
    assert result.iks_available is True
    assert result.overall_iks == 72.5
    assert result.epistemic_state_available is True
    assert result.total_verified > 0
    assert any(item.verified_count > 0 for item in result.categories)


def test_balance_sheet_http_retains_bool_flags(monkeypatch):
    from app.main import app

    _install_happy_path(monkeypatch)
    response = TestClient(app).get("/api/soc/learning-balance-sheet")
    assert response.status_code == 200
    body = response.json()
    for field in (
        "iks_available",
        "ceiling_available",
        "centroid_drift_available",
        "auto_approve_available",
        "timeline_available",
        "epistemic_state_available",
        "data_available",
        "degraded",
    ):
        assert isinstance(body[field], bool)
