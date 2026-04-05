"""
Block 1.1 — Industry profile tests.
No live Neo4j required.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.services.industry_profile import (
    list_industries,
    load_industry_profile,
    validate_profile,
)


# ---------------------------------------------------------------------------
# Test 1 — list_industries returns all 4 archetypes
# ---------------------------------------------------------------------------

def test_list_industries_returns_all_archetypes():
    """list_industries() must return exactly the 4 expected IDs."""
    ids = list_industries()
    assert set(ids) == {"healthcare", "finserv", "manufacturing", "generic"}, (
        f"Expected 4 archetypes, got: {ids}"
    )
    assert ids == sorted(ids), "list_industries() must return sorted IDs"


# ---------------------------------------------------------------------------
# Test 2 — load_industry_profile returns required fields for all archetypes
# ---------------------------------------------------------------------------

def test_load_all_profiles_have_required_fields():
    """Every profile must contain all required raw and derived fields."""
    required_raw = {"id", "label", "V", "alpha", "analyst_hourly_cost",
                    "regulatory_multiplier", "notes", "typical_alert_categories"}
    required_derived = {"decisions_per_day", "theta_min", "phase3_minimum",
                        "roi_annual_usd", "roi_annual_usd_regulated"}

    for industry_id in list_industries():
        profile = load_industry_profile(industry_id)
        missing_raw     = required_raw     - set(profile.keys())
        missing_derived = required_derived - set(profile.keys())
        assert not missing_raw,     f"{industry_id}: missing raw fields {missing_raw}"
        assert not missing_derived, f"{industry_id}: missing derived fields {missing_derived}"


# ---------------------------------------------------------------------------
# Test 3 — derived metrics are computed correctly for generic (validated values)
# ---------------------------------------------------------------------------

def test_generic_derived_metrics():
    """
    Generic archetype: V=200, alpha=0.25.
    Validated: theta_min = 23.53/(0.25*200) = 0.4706
               phase3_minimum = max(1000, 20*200*0.25) = 1000
               decisions_per_day = 50.0
               roi_annual_usd = 50 * 365 * 0.25 * 75 = 342,187.50
    """
    p = load_industry_profile("generic")

    assert p["decisions_per_day"] == pytest.approx(50.0,       abs=0.1)
    assert p["theta_min"]         == pytest.approx(0.4706,     abs=0.001)
    assert p["phase3_minimum"]    == 1000
    assert p["roi_annual_usd"]    == pytest.approx(342_187.50, rel=1e-4)
    # regulatory_multiplier = 1.0 → regulated == base
    assert p["roi_annual_usd_regulated"] == pytest.approx(p["roi_annual_usd"], rel=1e-6)


# ---------------------------------------------------------------------------
# Test 4 — validate_profile catches invalid values
# ---------------------------------------------------------------------------

def test_validate_profile_catches_errors():
    """validate_profile() must return errors for out-of-range values."""
    bad = {
        "id": "test",
        "label": "Test",
        "V": 5,           # below minimum 10
        "alpha": 2.0,     # above maximum 1.0
        "analyst_hourly_cost": 600,  # above maximum 500
        "regulatory_multiplier": 0.5,  # below minimum 1.0
    }
    errors = validate_profile(bad)
    assert len(errors) >= 3, f"Expected ≥3 errors for bad profile, got: {errors}"

    # A valid profile must produce no errors
    good = {
        "id": "test_good",
        "label": "Good Profile",
        "V": 200,
        "alpha": 0.25,
        "analyst_hourly_cost": 75,
        "regulatory_multiplier": 1.0,
    }
    assert validate_profile(good) == [], f"Expected no errors for valid profile, got errors"


# ---------------------------------------------------------------------------
# Test 5 — GET /api/soc/industry-profile endpoint returns 200 and 404
# ---------------------------------------------------------------------------

def test_industry_profile_endpoint():
    """GET /api/soc/industry-profile?industry=healthcare returns 200 with theta_min.
       GET /api/soc/industry-profile?industry=unknown returns 404."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    # Valid industry
    resp = client.get("/api/soc/industry-profile?industry=healthcare")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["id"]             == "healthcare"
    assert "theta_min"            in body, "Missing theta_min"
    assert "phase3_minimum"       in body, "Missing phase3_minimum"
    assert "roi_annual_usd"       in body, "Missing roi_annual_usd"
    assert isinstance(body["theta_min"], float)
    assert body["theta_min"] > 0

    # Invalid industry
    resp404 = client.get("/api/soc/industry-profile?industry=unknown_xyz")
    assert resp404.status_code == 404, (
        f"Expected 404 for unknown industry, got {resp404.status_code}"
    )
    assert "unknown_xyz" in resp404.json().get("detail", ""), (
        "404 detail should mention the bad industry ID"
    )

    # List endpoint
    resp_list = client.get("/api/soc/industry-profiles")
    assert resp_list.status_code == 200
    industries = resp_list.json()["industries"]
    ids = {i["id"] for i in industries}
    assert ids == {"healthcare", "finserv", "manufacturing", "generic"}, (
        f"List endpoint returned unexpected IDs: {ids}"
    )
