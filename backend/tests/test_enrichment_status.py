"""
Tests for GET /api/soc/enrichment-status (Block 5.2).

Verifies enrichment source status: sources list, health field,
required per-source fields, and total node count.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Test 1 — endpoint returns 200
# ---------------------------------------------------------------------------

def test_enrichment_status_returns_200():
    resp = client.get("/api/soc/enrichment-status")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Test 2 — sources list present with at least one entry
# ---------------------------------------------------------------------------

def test_enrichment_status_has_sources():
    data = client.get("/api/soc/enrichment-status").json()
    assert "sources" in data
    assert len(data["sources"]) >= 1


# ---------------------------------------------------------------------------
# Test 3 — enrichment_health is one of the allowed values
# ---------------------------------------------------------------------------

def test_enrichment_status_health_field():
    data = client.get("/api/soc/enrichment-status").json()
    assert data["enrichment_health"] in ["GREEN", "AMBER", "RED"]


# ---------------------------------------------------------------------------
# Test 4 — each source has the required fields
# ---------------------------------------------------------------------------

def test_enrichment_status_source_has_required_fields():
    data = client.get("/api/soc/enrichment-status").json()
    required = ["source_name", "record_count", "trust_level",
                "status", "affects_factor"]
    for source in data["sources"]:
        for field in required:
            assert field in source, \
                f"Source '{source.get('source_name', '?')}' missing field: {field}"


# ---------------------------------------------------------------------------
# Test 5 — total_enrichment_nodes is a non-negative integer
# ---------------------------------------------------------------------------

def test_enrichment_status_total_nodes_positive():
    data = client.get("/api/soc/enrichment-status").json()
    assert data["total_enrichment_nodes"] >= 0
