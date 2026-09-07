import json
from pathlib import Path

import pytest

from app.domains.soc.config import SOC_FACTORS, SOCDomainConfig
from app.domains.soc.factors import ThreatIntelEnrichmentFactor
from app.domains.soc.orchestrator import compute_factor_vector_with_provenance


class FakeAGE:
    def __init__(self, responses=None):
        self.responses = responses or []
        self.queries = []

    async def run_query(self, query, *args, **kwargs):
        self.queries.append(query)
        if self.responses:
            return self.responses.pop(0)
        return []


@pytest.mark.asyncio
async def test_threat_intel_fallback_labeled_fixture_fallback():
    alert = {"id": "ALERT-NO-LIVE"}
    vector, provenance = await compute_factor_vector_with_provenance(
        alert,
        [ThreatIntelEnrichmentFactor()],
        FakeAGE(),
    )

    assert vector.shape == (1,)
    assert provenance["threat_intel_enrichment"]["source"] == "fixture_fallback"
    assert provenance["threat_intel_enrichment"]["value"] == pytest.approx(
        float(vector[0])
    )


@pytest.mark.asyncio
async def test_factor_provenance_has_all_six_soc_factors():
    alert = {
        "id": "ALERT-ALL-FACTORS",
        "category": "credential_access",
        "user_risk_score": 0.8,
        "business_hours_login": False,
        "mfa_completed": False,
        "device_fingerprint_match": False,
        "vpn": False,
    }
    vector, provenance = await compute_factor_vector_with_provenance(
        alert,
        SOCDomainConfig.get_factor_computers(),
        FakeAGE(),
    )

    assert vector.shape == (6,)
    assert set(provenance) == set(SOC_FACTORS)
    assert provenance["privileged_identity_context"]["source"] == "alert_field"
    assert provenance["time_anomaly"]["source"] == "alert_field"
    assert provenance["device_trust"]["source"] == "alert_field"


def test_triage_persists_factor_provenance_to_decision_node():
    src = Path("app/routers/triage.py").read_text(encoding="utf-8")

    assert "factor_vector_provider.compute(" in src
    assert "factor_provenance:" in src
    assert "json.dumps(factor_provenance" in src


def test_factor_provenance_is_json_serializable():
    provenance = {
        "threat_intel_enrichment": {
            "value": 0.0,
            "source": "fixture_fallback",
            "detail": "no threat-intel match",
        }
    }

    encoded = json.dumps(provenance, sort_keys=True)
    decoded = json.loads(encoded)
    assert decoded["threat_intel_enrichment"]["source"] == "fixture_fallback"
