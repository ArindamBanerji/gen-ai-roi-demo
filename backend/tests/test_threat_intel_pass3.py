"""
tests/test_threat_intel_pass3.py — ThreatIntelEnrichmentFactor Pass 3 tests.

4 tests validating campaign membership scoring, severity mapping,
neutral fallback, and non-raising exception handling.

Run from backend/:
    pytest tests/test_threat_intel_pass3.py -v
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import asyncio
from unittest.mock import AsyncMock

from app.domains.soc.factors import ThreatIntelEnrichmentFactor


def run(coro):
    return asyncio.run(coro)


# ============================================================================
# Test 1 — HIGH severity campaign → value=0.05
# ============================================================================

def test_high_severity_campaign_returns_low_value():
    """
    When alert is member of a HIGH severity campaign, Pass 3 must return
    value=0.05 — the strongest escalate signal (lowest value).
    """
    mock_neo4j = AsyncMock()
    mock_neo4j.run_query.return_value = [{
        "confidence": 0.85,
        "severity": "HIGH",
        "campaign_id": "camp-001",
        "summary": "2 alerts: credential_access → lateral_movement over 6h.",
        "trigger_rule": "technique_sequence",
    }]

    factor = ThreatIntelEnrichmentFactor()
    result = run(factor._internal_campaign_score("alert-1", mock_neo4j))

    assert result["value"] == 0.05, (
        f"HIGH severity campaign must return value=0.05. Got: {result['value']}"
    )
    assert "camp-001" in result["provenance_nodes"], (
        f"campaign_id must be in provenance_nodes. Got: {result['provenance_nodes']}"
    )


# ============================================================================
# Test 2 — MEDIUM severity campaign → value=0.20
# ============================================================================

def test_medium_severity_campaign_returns_medium_value():
    """
    MEDIUM severity campaign → value=0.20 (moderate escalate signal).
    """
    mock_neo4j = AsyncMock()
    mock_neo4j.run_query.return_value = [{
        "confidence": 0.70,
        "severity": "MEDIUM",
        "campaign_id": "camp-002",
        "summary": "Shared entity cluster.",
        "trigger_rule": "shared_entity",
    }]

    factor = ThreatIntelEnrichmentFactor()
    result = run(factor._internal_campaign_score("alert-2", mock_neo4j))

    assert result["value"] == 0.20, (
        f"MEDIUM severity campaign must return value=0.20. Got: {result['value']}"
    )
    assert "camp-002" in result["provenance_nodes"], (
        f"campaign_id must be in provenance_nodes. Got: {result['provenance_nodes']}"
    )


# ============================================================================
# Test 3 — No campaign → neutral value=0.50, empty provenance_nodes
# ============================================================================

def test_no_campaign_returns_neutral():
    """
    When alert is not part of any campaign (Neo4j returns []),
    Pass 3 must return neutral value=0.50 with empty provenance_nodes.
    """
    mock_neo4j = AsyncMock()
    mock_neo4j.run_query.return_value = []

    factor = ThreatIntelEnrichmentFactor()
    result = run(factor._internal_campaign_score("alert-3", mock_neo4j))

    assert result["value"] == 0.50, (
        f"No campaign must return value=0.50 (neutral). Got: {result['value']}"
    )
    assert result["provenance_nodes"] == [], (
        f"provenance_nodes must be empty when no campaign. Got: {result['provenance_nodes']}"
    )


# ============================================================================
# Test 4 — Neo4j failure → neutral fallback, never raises
# ============================================================================

def test_neo4j_failure_returns_neutral_not_exception():
    """
    When Neo4j raises an exception, _internal_campaign_score must catch it
    and return neutral value=0.50. The word 'unavailable' must appear in
    the contribution message (per spec).
    """
    mock_neo4j = AsyncMock()
    mock_neo4j.run_query.side_effect = Exception("connection failed")

    factor = ThreatIntelEnrichmentFactor()
    result = run(factor._internal_campaign_score("alert-x", mock_neo4j))

    assert result["value"] == 0.50, (
        f"Neo4j failure must return neutral 0.50. Got: {result['value']}"
    )
    assert "unavailable" in result["contribution"].lower(), (
        f"contribution must contain 'unavailable'. Got: {result['contribution']!r}"
    )
