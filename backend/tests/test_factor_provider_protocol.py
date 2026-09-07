import numpy as np
import pytest

from app.domains.soc.config import SOC_FACTORS, SOCDomainConfig
from app.domains.soc.orchestrator import compute_factor_vector_with_provenance
from app.services.triage_providers import (
    FactorVectorProvider,
    get_factor_vector_provider,
)


class FakeAGE:
    def __init__(self):
        self.queries = []

    async def run_query(self, query, *args, **kwargs):
        self.queries.append(query)
        return []


@pytest.mark.asyncio
async def test_real_factor_provider_returns_vector_and_provenance_structure():
    provider = get_factor_vector_provider()
    alert = {
        "id": "ALERT-PROVIDER-1",
        "alert_type": "anomalous_login",
        "category": "credential_access",
        "user_risk_score": 0.8,
        "asset_criticality": "high",
        "business_hours_login": False,
        "mfa_completed": False,
        "device_fingerprint_match": False,
        "vpn": False,
    }

    vector, provenance = await provider.compute(alert, FakeAGE())

    assert isinstance(provider, FactorVectorProvider)
    assert isinstance(vector, np.ndarray)
    assert vector.shape == (len(SOC_FACTORS),)
    assert set(provenance) == set(SOC_FACTORS)
    for factor_name, item in provenance.items():
        assert item["value"] == pytest.approx(float(vector[SOC_FACTORS.index(factor_name)]))
        assert isinstance(item["source"], str)
        assert item["source"] != "test_override"


@pytest.mark.asyncio
async def test_real_factor_provider_matches_production_orchestrator_output():
    alert = {
        "id": "ALERT-PROVIDER-2",
        "alert_type": "anomalous_login",
        "category": "credential_access",
        "user_risk_score": 0.8,
        "business_hours_login": False,
        "mfa_completed": False,
        "device_fingerprint_match": False,
        "vpn": False,
    }
    graph = FakeAGE()

    provider_vector, provider_provenance = await get_factor_vector_provider().compute(
        alert,
        graph,
    )
    direct_vector, direct_provenance = await compute_factor_vector_with_provenance(
        alert,
        SOCDomainConfig.get_factor_computers(),
        graph,
    )

    np.testing.assert_allclose(provider_vector, direct_vector)
    assert provider_provenance == direct_provenance
