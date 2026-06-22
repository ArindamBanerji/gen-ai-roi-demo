"""
Tests for Phase 6: ProvenanceService and provenance endpoint.

Coverage:
  test_provenance_builds_6_factors        -- build_provenance returns 6 FactorProvenance entries
  test_provenance_factor_names            -- all 6 SOC factor names present
  test_provenance_privileged_identity_context_high -- privileged_identity_context=0.9 -> User, Identity, Device in nodes
  test_provenance_device_trust_fully_trusted -- device_trust=0.0 -> "fully trusted" in explanation
  test_provenance_endpoint_not_found      -- GET /api/soc/provenance/{id} returns 404 when missing
  test_provenance_threat_intel_nodes      -- threat_intel_enrichment -> ThreatIntel, Alert in nodes
"""

import asyncio
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.services.provenance import ProvenanceService, FactorProvenance, DecisionProvenance
from app.domains.soc.config import SOC_FACTORS


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_DECISION_ID = "prov-test-001"
_FACTOR_VALUES = [0.9, 0.8, 0.0, 0.5, 0.7, 0.0]   # privileged_identity_context...device_trust


def _build():
    """Build a DecisionProvenance with standard test values."""
    return ProvenanceService.build_provenance(
        decision_id=_DECISION_ID,
        factor_names=list(SOC_FACTORS),
        factor_values=_FACTOR_VALUES,
        category="credential_access",
        action="escalate",
    )


# ---------------------------------------------------------------------------
# Test 1: 6 factors returned
# ---------------------------------------------------------------------------

def test_provenance_builds_6_factors():
    """build_provenance returns exactly 6 FactorProvenance entries."""
    prov = _build()
    assert isinstance(prov, DecisionProvenance), type(prov)
    assert len(prov.factors) == 6, (
        f"Expected 6 factors, got {len(prov.factors)}: "
        f"{[fp.factor_name for fp in prov.factors]}"
    )


# ---------------------------------------------------------------------------
# Test 2: all 6 SOC factor names present
# ---------------------------------------------------------------------------

def test_provenance_factor_names():
    """All 6 SOC factor names are present in the provenance."""
    prov = _build()
    names = {fp.factor_name for fp in prov.factors}
    for expected in SOC_FACTORS:
        assert expected in names, f"Factor {expected!r} missing from provenance: {names}"


# ---------------------------------------------------------------------------
# Test 3: privileged_identity_context high value → correct graph nodes
# ---------------------------------------------------------------------------

def test_provenance_privileged_identity_context_high():
    """privileged_identity_context=0.9 -> graph_nodes_consulted includes User, Identity, Device."""
    prov = _build()
    identity = next(fp for fp in prov.factors if fp.factor_name == "privileged_identity_context")
    assert identity.factor_value == pytest.approx(0.9, abs=1e-3)
    assert "User" in identity.graph_nodes_consulted, (
        f"User not in nodes: {identity.graph_nodes_consulted}"
    )
    assert "Identity" in identity.graph_nodes_consulted, (
        f"Identity not in nodes: {identity.graph_nodes_consulted}"
    )
    assert "Device" in identity.graph_nodes_consulted, (
        f"Device not in nodes: {identity.graph_nodes_consulted}"
    )
    assert "identity" in identity.explanation.lower(), identity.explanation


# ---------------------------------------------------------------------------
# Test 4: device_trust=0.0 → "fully trusted" explanation
# ---------------------------------------------------------------------------

def test_provenance_device_trust_fully_trusted():
    """device_trust=0.0 -> explanation mentions fully trusted device."""
    prov = _build()
    dt = next(fp for fp in prov.factors if fp.factor_name == "device_trust")
    assert dt.factor_value == pytest.approx(0.0, abs=1e-3)
    assert "fully trusted" in dt.explanation.lower(), (
        f"Expected 'fully trusted' in explanation: {dt.explanation!r}"
    )


# ---------------------------------------------------------------------------
# Test 5: endpoint returns 404 when decision not found
# ---------------------------------------------------------------------------

def test_provenance_endpoint_not_found():
    """GET /api/soc/provenance/{id} returns 404 when decision not in Neo4j."""
    from app.main import app

    async def fake_run_query(query, params=None):
        return []   # empty -> decision not found

    with patch("app.routers.soc.neo4j_client") as mock_neo4j:
        mock_neo4j.run_query = fake_run_query
        client = TestClient(app)
        resp = client.get("/api/soc/provenance/nonexistent-id-xyz")

    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# Test 6: threat_intel_enrichment → correct graph nodes
# ---------------------------------------------------------------------------

def test_provenance_threat_intel_nodes():
    """threat_intel_enrichment factor has ThreatIntel and Alert in graph nodes."""
    prov = _build()
    ti = next(fp for fp in prov.factors if fp.factor_name == "threat_intel_enrichment")
    assert "ThreatIntel" in ti.graph_nodes_consulted, (
        f"ThreatIntel not in nodes: {ti.graph_nodes_consulted}"
    )
    assert "Alert" in ti.graph_nodes_consulted, (
        f"Alert not in nodes: {ti.graph_nodes_consulted}"
    )
    # value=0.0 → no match explanation
    assert ti.factor_value == pytest.approx(0.0, abs=1e-3)
    assert "no threat intelligence" in ti.explanation.lower(), ti.explanation
