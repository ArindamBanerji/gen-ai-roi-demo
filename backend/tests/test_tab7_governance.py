import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.main import app
from app.routers import soc


client = TestClient(app)


def test_compliance_returns_200():
    response = client.get("/api/soc/compliance")

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "EU AI Act Evidence Supporting Human Oversight"
    assert "articles" in payload
    assert "summary" in payload


def test_compliance_has_eu_ai_act():
    response = client.get("/api/soc/compliance")

    assert response.status_code == 200
    payload = response.json()
    assert "eu_ai_act" in payload
    assert set(payload["eu_ai_act"]) == {"article_9", "article_15"}


def test_article_9_has_status_title_description():
    article = client.get("/api/soc/compliance").json()["eu_ai_act"]["article_9"]

    assert article["title"]
    assert article["description"]
    assert article["status"] in {"EVIDENCE_SUPPORTING_OVERSIGHT", "INVESTIGATION"}


def test_article_15_has_status_title_description():
    article = client.get("/api/soc/compliance").json()["eu_ai_act"]["article_15"]

    assert article["title"]
    assert article["description"]
    assert article["status"] in {"EVIDENCE_SUPPORTING_OVERSIGHT", "INVESTIGATION"}


def test_article_statuses_are_allowed():
    payload = client.get("/api/soc/compliance").json()["eu_ai_act"]

    statuses = {section["status"] for section in payload.values()}
    assert statuses <= {"EVIDENCE_SUPPORTING_OVERSIGHT", "INVESTIGATION"}


def test_eu_ai_act_no_certification_language():
    payload = client.get("/api/soc/compliance").json()
    rendered = str(payload).upper()
    for forbidden in ("COMPLIANT", "CERTIFIED", "CERTIFICATION", "MEETS REQUIREMENTS"):
        assert forbidden not in rendered
    assert "EVIDENCE" in rendered or "OVERSIGHT" in rendered


def test_non_green_conservation_sets_article_9_investigation():
    payload = soc._build_eu_ai_act_summary(
        conservation_status="AMBER",
        audit_chain_valid=True,
    )

    assert payload["article_9"]["status"] == "INVESTIGATION"
    assert payload["article_15"]["status"] == "EVIDENCE_SUPPORTING_OVERSIGHT"


def test_invalid_audit_chain_sets_article_15_investigation():
    payload = soc._build_eu_ai_act_summary(
        conservation_status="GREEN",
        audit_chain_valid=False,
    )

    assert payload["article_9"]["status"] == "EVIDENCE_SUPPORTING_OVERSIGHT"
    assert payload["article_15"]["status"] == "INVESTIGATION"
