import csv
import io
import os
import sys
import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import app.services.governance_report as governance_report
from app.routers import governance_router


async def _stub_learning_health():
    return {
        "status": "GREEN",
        "signal": 0.91,
        "theta_min": 0.25,
        "conservation": {"passed": True, "status": "GREEN", "headroom": 0.66},
        "components": {"alpha": 0.4, "q": 0.9, "V": 12.0, "n": 450},
        "baseline": 0.7,
        "baseline_std": 0.05,
        "red_days": 2,
        "auto_pause_active": False,
        "interpretation": "healthy",
    }


async def _stub_audit():
    return (
        {
            "total": 12,
            "sample": [
                {
                    "id": "d-1",
                    "alert_id": "a-1",
                    "timestamp": "2026-04-25T00:00:00Z",
                    "situation_type": "credential_access",
                    "action_taken": "investigate",
                    "factors": ["pattern_history"],
                    "confidence": 0.82,
                    "outcome": "correct",
                    "hash": "abc123",
                }
            ],
        },
        {
            "chain_length": 12,
            "verified": True,
            "first_record": "2026-04-25T00:00:00Z",
            "last_record": "2026-04-25T01:00:00Z",
            "epoch": 1,
            "archived_epochs": 0,
        },
    )


async def _stub_centroid_export():
    return {
        "export_version": "1.0",
        "generated_at_epoch": 1,
        "gae_version": "0.7.21",
        "tensor_shape": [6, 4, 6],
        "current_mu": [],
        "bootstrap_mu": [],
        "drift_from_bootstrap": 0.12,
        "decision_count": 12,
        "categories": ["credential_access"],
        "actions": ["investigate"],
        "sha256": "sha-a",
    }


async def _stub_tab2():
    return {
        "iks_score": 72.5,
        "iks_interpretation": "learning",
        "category_accuracy_summary": {"trust_coverage": 83.3},
        "drift_alert_summary": "1 of 12 decisions triggered drift detection.",
        "trust_coverage_summary": "83.3% of alert categories have >=100 verified decisions.",
        "override_learning_status": "active (12 examples)",
        "decision_count_glossary": {"verified_decisions": "12"},
        "calibration_note": "Calibration activates after sufficient decisions accumulate.",
    }


async def _stub_exec():
    return {
        "headline": "System processed 20 alerts and learned from 12 verified decisions.",
        "what_changed": {"total_verified": 12, "total_centroid_updates": 8, "top_shifts": [], "iks_delta": 0.0},
        "what_discovered": {"attack_chains_detected": 2, "chain_summaries": ["2 alerts in cluster"], "new_entities": {}, "graph_growth": {}},
        "what_knows": {
            "iks_current": 72.5,
            "categories_calibrated": 3,
            "categories_total": 6,
            "health_status": "GREEN",
            "conservation_narrative": "Conservation law active and full audit trail available for human review.",
        },
    }


async def _stub_auto_approve():
    return {
        "total_decisions": 12,
        "auto_approved": 4,
        "coverage_pct": 33.3,
        "by_category": {"credential_access": {"total": 12, "auto_approved": 4, "coverage_pct": 33.3}},
    }


async def _stub_epistemic():
    return {"categories": {"credential_access": {"count": 12, "band": "novice"}}, "total_verified": 12}


async def _stub_benchmarking():
    return {
        "status": "ready",
        "source": "v_shadow_synthetic_v3",
        "total_decisions": 1500,
        "overall_agreement_rate": 0.64,
        "overall_ai_accuracy": 0.79,
        "lead_finding": "Analyst review highlights lateral movement disagreements.",
        "per_category": {"credential_access": {"verified_decisions": 100, "signal": "review"}},
        "per_archetype": {"tier1": {"override_count": 3, "override_precision": 0.66}},
        "day_variance": {"min_daily_agree": 0.5, "max_daily_agree": 0.8, "trend": "stable"},
    }


def _install_stubs(monkeypatch):
    monkeypatch.setattr(governance_report, "_collect_learning_health", _stub_learning_health)
    monkeypatch.setattr(governance_report, "_collect_audit_evidence", _stub_audit)
    monkeypatch.setattr(governance_report, "_collect_centroid_export", _stub_centroid_export)
    monkeypatch.setattr(governance_report, "_collect_tab2_evidence", _stub_tab2)
    monkeypatch.setattr(governance_report, "_collect_executive_narrative", _stub_exec)
    monkeypatch.setattr(governance_report, "_collect_auto_approve_stats", _stub_auto_approve)
    monkeypatch.setattr(governance_report, "_collect_epistemic_state", _stub_epistemic)
    monkeypatch.setattr(governance_report, "_collect_analyst_benchmarking", _stub_benchmarking)


def _client(monkeypatch):
    _install_stubs(monkeypatch)
    app = FastAPI()
    app.include_router(governance_router.router, prefix="/api", tags=["Governance Evidence"])
    return TestClient(app)


def test_governance_report_structure(monkeypatch):
    _install_stubs(monkeypatch)
    result = asyncio.run(governance_report.generate_governance_report())

    assert result.title == "Evidence supporting human oversight"
    assert result.legal_disclaimer == governance_report.LEGAL_DISCLAIMER
    assert len(result.sections) == 5
    assert all(section.legal_disclaimer == governance_report.LEGAL_DISCLAIMER for section in result.sections)
    assert result.known_risks[0]["title"] == governance_report.N3_RISK_TITLE
    assert result.known_risks[0]["mitigation"] == governance_report.N3_MITIGATION_TEXT
    assert "EU AI Act compliant" not in str(result)


def test_governance_report_evidence_presence(monkeypatch):
    _install_stubs(monkeypatch)
    result = asyncio.run(governance_report.generate_governance_report())

    by_article = {section.article: section for section in result.sections}
    assert by_article["Art 9"].evidence["learning_health"]["conservation"]["status"] == "GREEN"
    assert by_article["Art 9"].evidence["drift_01_note"] == governance_report.DRIFT_01_NOTE
    assert by_article["Art 12"].evidence["chain_integrity"]["verified"] is True
    assert by_article["Art 12"].evidence["centroid_export"]["tensor_shape"] == [6, 4, 6]
    assert by_article["Art 14"].evidence["auto_approve_stats"]["coverage_pct"] == 33.3
    assert by_article["Art 15"].evidence["iks_score"] == 72.5


def test_governance_csv_export(monkeypatch):
    client = _client(monkeypatch)

    response = client.get("/api/governance/report/csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert rows
    assert set(rows[0].keys()) == {"section", "article", "evidence_key", "evidence_value", "status"}


def test_governance_summary(monkeypatch):
    client = _client(monkeypatch)

    response = client.get("/api/governance/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["overall_assessment"] == "Evidence supporting human oversight is available across five sections."
    assert len(payload["sections"]) == 5
    assert all(section["legal_disclaimer"] == governance_report.LEGAL_DISCLAIMER for section in payload["sections"])


def test_governance_endpoints(monkeypatch):
    client = _client(monkeypatch)

    report_response = client.get("/api/governance/report")
    summary_response = client.get("/api/governance/summary")
    csv_response = client.get("/api/governance/report/csv")

    assert report_response.status_code == 200
    assert summary_response.status_code == 200
    assert csv_response.status_code == 200
    report_payload = report_response.json()
    assert report_payload["legal_disclaimer"] == governance_report.LEGAL_DISCLAIMER
    assert report_payload["known_risks"][0]["title"] == governance_report.N3_RISK_TITLE
