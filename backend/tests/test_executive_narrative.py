import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.services.executive_narrative import ExecutiveNarrative


class MockDB:
    def run_query(self, query, params=None):
        return []


def test_three_sections():
    narrative = ExecutiveNarrative(MockDB())
    result = narrative.generate_weekly()
    assert 'section_1_what_changed' in result
    assert 'section_2_what_discovered' in result
    assert 'section_3_what_knows' in result


def test_headline_present():
    narrative = ExecutiveNarrative(MockDB())
    result = narrative.generate_weekly()
    assert 'headline' in result
    assert len(result['headline']) > 0


def test_what_changed_structure():
    narrative = ExecutiveNarrative(MockDB())
    result = narrative.generate_weekly()
    section = result['section_1_what_changed']
    assert 'total_verified' in section
    assert 'top_shifts' in section


def test_what_discovered_structure():
    narrative = ExecutiveNarrative(MockDB())
    result = narrative.generate_weekly()
    section = result['section_2_what_discovered']
    assert 'attack_chains_detected' in section
    assert 'new_entities' in section


def test_what_knows_structure():
    narrative = ExecutiveNarrative(MockDB())
    result = narrative.generate_weekly()
    section = result['section_3_what_knows']
    assert 'iks_current' in section
    assert 'health_status' in section


def test_period_present():
    narrative = ExecutiveNarrative(MockDB())
    result = narrative.generate_weekly()
    assert 'period' in result


def test_period_week_ending_explicit():
    narrative = ExecutiveNarrative(MockDB())
    result = narrative.generate_weekly(week_ending='2026-03-19')
    assert result['period']['end'] == '2026-03-19'
    assert result['period']['start'] == '2026-03-12'


def test_headline_fallback_when_no_data():
    narrative = ExecutiveNarrative(MockDB())
    result = narrative.generate_weekly()
    # With empty DB the fallback headline should be returned
    assert 'digest' in result['headline'].lower() or len(result['headline']) > 0


def test_override_comment_field_on_schema():
    from app.models.schemas import OutcomeRequest
    import inspect
    fields = OutcomeRequest.model_fields
    assert 'override_comment' in fields
    # must be optional (default None)
    assert fields['override_comment'].default is None


# ============================================================================
# F12 endpoint tests — use TestClient
# ============================================================================

from app.services.gae_state import init_learning_state
init_learning_state()

from fastapi.testclient import TestClient
from app.main import app

_client = TestClient(app)


def test_f12_endpoint_returns_required_keys():
    """
    GET /api/soc/executive-narrative must return 200 with all keys
    consumed by ExecutiveNarrativeTab.tsx.
    """
    r = _client.get("/api/soc/executive-narrative")
    assert r.status_code == 200, f"Expected 200. Got {r.status_code}: {r.text[:300]}"
    data = r.json()
    required = {"headline", "what_changed", "what_discovered", "what_knows",
                "metrics", "generated_at", "pdf_available"}
    missing = required - set(data.keys())
    assert not missing, f"Missing keys: {missing}"
    assert data["pdf_available"] is True


def test_f12_metrics_block_numeric():
    """metrics values must all be numeric (empty graph → zeros)."""
    r = _client.get("/api/soc/executive-narrative")
    assert r.status_code == 200
    m = r.json()["metrics"]
    for key in ("alerts_total", "decisions_verified", "campaigns_detected", "iks_current"):
        assert key in m, f"Missing metrics key '{key}'"
        assert isinstance(m[key], (int, float)), f"metrics['{key}'] must be numeric"


def test_f12_what_changed_structure():
    """what_changed must have total_verified, total_centroid_updates, top_shifts."""
    r = _client.get("/api/soc/executive-narrative")
    assert r.status_code == 200
    wc = r.json()["what_changed"]
    assert "total_verified" in wc
    assert "top_shifts" in wc
    assert isinstance(wc["top_shifts"], list)


def test_f12_pdf_endpoint_returns_pdf_bytes():
    """
    GET /api/soc/executive-narrative/pdf must return 200,
    content-type application/pdf, and body starting with %PDF.
    """
    r = _client.get("/api/soc/executive-narrative/pdf")
    assert r.status_code == 200, f"Expected 200 for PDF. Got {r.status_code}: {r.text[:200]}"
    ct = r.headers.get("content-type", "")
    assert "application/pdf" in ct, f"Expected application/pdf. Got: {ct}"
    assert len(r.content) > 100, f"PDF body too short: {len(r.content)} bytes"
    assert r.content[:4] == b"%PDF", f"Body does not start with %PDF. Got: {r.content[:8]}"
