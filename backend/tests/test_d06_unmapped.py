import asyncio
import logging
import os
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def test_unmapped_type_returns_unclassified():
    from app.domains.soc.config import DEFAULT_CATEGORY, resolve_alert_category

    assert DEFAULT_CATEGORY != "credential_access"
    assert resolve_alert_category("totally_unknown_xyz") == DEFAULT_CATEGORY


def test_known_types_still_resolve():
    from app.domains.soc.config import resolve_alert_category

    assert resolve_alert_category("anomalous_login") == "credential_access"
    assert resolve_alert_category("phishing") == "malware_execution"
    assert resolve_alert_category("cloud_iam_privilege_escalation") == "cloud_infrastructure"


def test_unmapped_type_logs_warning(caplog):
    from app.domains.soc.config import resolve_alert_category

    with caplog.at_level(logging.WARNING):
        assert resolve_alert_category("new_vendor_alert_type") == "unclassified"

    assert "new_vendor_alert_type" in caplog.text
    assert "unclassified" in caplog.text


def test_empty_string_routes_to_unclassified(caplog):
    from app.domains.soc.config import resolve_alert_category

    with caplog.at_level(logging.WARNING):
        assert resolve_alert_category("") == "unclassified"
        assert resolve_alert_category(None) == "unclassified"

    assert "unclassified" in caplog.text


def test_unclassified_not_in_scorer_categories():
    from app.domains.soc.config import SOC_CATEGORIES, SOCDomainConfig

    assert "unclassified" not in SOC_CATEGORIES
    with pytest.raises(ValueError):
        SOCDomainConfig().get_category_index("unclassified")


def test_unclassified_alert_is_not_scored(monkeypatch):
    from app.models.schemas import ProcessAlertRequest
    from app.routers import triage

    class DummyScorer:
        def score(self, *_args, **_kwargs):
            raise AssertionError("ProfileScorer.score should not be called")

    async def fake_get_alert(_alert_id):
        return {"alert_id": "ALERT-UNKNOWN", "alert_type": "totally_unknown_xyz"}

    async def fake_context(_alert_id):
        return {"alert_type": "totally_unknown_xyz"}

    async def fail_factor_vector(*_args, **_kwargs):
        raise AssertionError("compute_factor_vector should not run for unclassified alert")

    monkeypatch.setattr("app.services.gae_state.get_profile_scorer", lambda: DummyScorer())
    monkeypatch.setattr(triage.neo4j_client, "get_alert", fake_get_alert)
    monkeypatch.setattr(triage.neo4j_client, "get_security_context", fake_context)
    monkeypatch.setattr(triage, "compute_factor_vector", fail_factor_vector)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(triage.analyze_alert(ProcessAlertRequest(alert_id="ALERT-UNKNOWN")))

    assert exc.value.status_code == 422
    assert exc.value.detail["error"] == "unclassified_alert_type"


def test_model_swap_unclassified_alert_is_not_scored():
    from app.services.model_swap import _score_alert

    class DummyScorer:
        def score(self, *_args, **_kwargs):
            raise AssertionError("Model swap scorer should not be called")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            _score_alert(
                {"alert_id": "A-1", "alert_type": "new_vendor_alert_type"},
                DummyScorer(),
                [],
                object(),
            )
        )

    assert exc.value.status_code == 422
    assert exc.value.detail["error"] == "unclassified_alert_type"


def test_tab3_unclassified_alert_skips_live_and_baseline_scorers(monkeypatch):
    from app.routers import soc

    class DummyLiveScorer:
        def score(self, *_args, **_kwargs):
            raise AssertionError("Tab 3 live scorer should not score unclassified alert")

    class FakeNeo4jClient:
        def __init__(self):
            self.queries = []

        async def run_query(self, query, params=None):
            self.queries.append(query)
            if "MATCH (n) RETURN count(n) AS cnt" in query:
                return [{"cnt": 10}]
            if "MATCH (a:Alert {status: 'pending'})" in query:
                return [
                    {
                        "alert_id": "ALERT-UNKNOWN",
                        "category": None,
                        "alert_type": "new_vendor_alert_type",
                    }
                ]
            if "MATCH (d:Decision) WHERE d.outcome IS NOT NULL RETURN count(d) AS cnt" in query:
                return [{"cnt": 0}]
            raise AssertionError(f"Unexpected Tab 3 query for unclassified alert: {query}")

    def fail_baseline_scorer():
        raise AssertionError("Tab 3 baseline scorer should not score unclassified alert")

    fake_client = FakeNeo4jClient()
    monkeypatch.setattr("app.services.gae_state.get_profile_scorer", lambda: DummyLiveScorer())
    monkeypatch.setattr(soc, "_get_baseline_scorer", fail_baseline_scorer)
    monkeypatch.setattr(soc, "neo4j_client", fake_client)

    content = asyncio.run(soc._tab3_content())
    recommendation = content["recommendation"]

    assert recommendation["basis"] == "unclassified_routing"
    assert recommendation["confidence"] == 0.0
    assert recommendation["baseline_confidence"] == 0.0
    assert recommendation["baseline_action"] == "unclassified"
    assert "unclassified alerts" in recommendation["rationale"]
    assert not any("d.category = 'unclassified'" in query for query in fake_client.queries)


def test_soc_router_uses_default_category_for_unknown_sentinel_lookup():
    from app.domains.soc.config import DEFAULT_CATEGORY
    from app.routers import soc

    assert soc.SENTINEL_TO_INTERNAL.get("unknown_vendor_alert_type", DEFAULT_CATEGORY) == DEFAULT_CATEGORY


def test_soc_router_has_no_hardcoded_credential_access_fallbacks():
    source = (Path(__file__).parents[1] / "app" / "routers" / "soc.py").read_text(encoding="utf-8")

    assert 'or "credential_access"' not in source
    assert "or 'credential_access'" not in source
    assert 'get(sentinel_type, "credential_access")' not in source


def test_variant_generator_has_no_hardcoded_credential_access_fallbacks():
    source = (Path(__file__).parents[1] / "app" / "services" / "variant_generator.py").read_text(encoding="utf-8")

    assert 'default="credential_access"' not in source
    assert 'or "credential_access"' not in source
