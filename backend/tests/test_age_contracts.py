"""
test_age_contracts.py -- AGE serialization and shape boundary contracts.

Verifies that the backend correctly handles Apache AGE's quirks:
  1. List properties are returned as JSON strings from AGE -> backend must decode.
  2. Decision nodes use `decision_id`, Alert nodes use `alert_id` (not generic `id`).
  3. SOC_PROFILE_CENTROIDS shape (6,4,6) matches the live ProfileScorer.
  4. API response fields have the correct Python types (int, list, etc.).

Run from backend/:
    pytest tests/test_age_contracts.py -v
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ============================================================================
# GROUP 1 — AGE list → string serialization boundary
# ============================================================================

def test_campaign_categories_is_list_not_string():
    """
    GET /api/soc/campaigns -> category_sequence must be a Python list, never a
    raw JSON string.  AGE serializes list properties as strings; _format_campaign()
    must json.loads() them before returning.
    """
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/soc/campaigns")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    campaigns = data.get("campaigns", [])
    for c in campaigns:
        seq = c.get("category_sequence")
        assert isinstance(seq, list), (
            f"campaign {c.get('campaign_id')}: category_sequence is {type(seq).__name__!r}, "
            f"expected list. AGE may be returning a raw JSON string."
        )
        ents = c.get("shared_entities")
        assert isinstance(ents, list), (
            f"campaign {c.get('campaign_id')}: shared_entities is {type(ents).__name__!r}, "
            f"expected list. AGE may be returning a raw JSON string."
        )


def test_campaign_categories_already_list_not_double_parsed():
    """
    _format_campaign() with an already-parsed list must NOT double-parse.
    Protects against a future regression where the guard parses a string
    like '["a","b"]' twice, turning it into a string of chars.
    """
    from app.routers.soc import _format_campaign

    raw = {
        "category_sequence": ["credential_access", "lateral_movement"],
        "shared_entities": ["user@corp.com"],
        "id": "CMP-001",
        "alert_count": 3,
        "confidence": 0.85,
        "severity": "HIGH",
        "trigger_rule": "test",
        "nl_summary": "test campaign",
    }
    result = _format_campaign(raw)
    assert result["category_sequence"] == ["credential_access", "lateral_movement"], (
        f"Double-parse bug: category_sequence became {result['category_sequence']!r}"
    )
    assert result["shared_entities"] == ["user@corp.com"], (
        f"Double-parse bug: shared_entities became {result['shared_entities']!r}"
    )


def test_campaign_json_string_input_parsed_to_list():
    """
    _format_campaign() with an AGE JSON string for category_sequence must
    return a proper list, not a string.
    """
    from app.routers.soc import _format_campaign

    raw = {
        "category_sequence": '["credential_access", "lateral_movement"]',
        "shared_entities": '["user@corp.com"]',
        "id": "CMP-002",
        "alert_count": 2,
        "confidence": 0.70,
        "severity": "MEDIUM",
        "trigger_rule": "test",
        "nl_summary": "",
    }
    result = _format_campaign(raw)
    assert isinstance(result["category_sequence"], list), (
        f"JSON string not parsed: category_sequence is {type(result['category_sequence']).__name__!r}"
    )
    assert result["category_sequence"] == ["credential_access", "lateral_movement"], (
        f"Wrong parse result: {result['category_sequence']!r}"
    )
    assert isinstance(result["shared_entities"], list), (
        f"JSON string not parsed: shared_entities is {type(result['shared_entities']).__name__!r}"
    )


# ============================================================================
# GROUP 2 — AGE property name contracts (decision_id / alert_id, not id)
# ============================================================================

def test_evolution_events_endpoint_uses_decision_id():
    """
    GET /api/metrics/evolution-events must use d.decision_id (not d.id) in its
    Cypher query.  AGE Decision nodes store the identifier in decision_id;
    querying d.id always returns null -> 'DEC-None' duplicate keys.

    This test inspects the source of the standalone endpoint (H7-FIX-4) to
    confirm the correct property name is used.
    """
    import ast
    import pathlib

    src = pathlib.Path("app/routers/metrics.py").read_text(encoding="utf-8")
    # The standalone /metrics/evolution-events endpoint must reference decision_id
    assert "d.decision_id AS id" in src, (
        "metrics.py: evolution-events query must use d.decision_id AS id, not d.id. "
        "AGE Decision nodes have no generic 'id' property."
    )


def test_compounding_evolution_uses_correct_property():
    """
    The /compounding endpoint's inline evolution_events query ALSO reads decision
    nodes.  It should use d.decision_id -- not d.id -- to avoid 'DEC-None' duplicates.

    NOTE: If this test fails it reveals a remaining bug in the inline compounding
    query (line ~246 in metrics.py).  Do not fix it here -- report only.
    """
    import pathlib

    src = pathlib.Path("app/routers/metrics.py").read_text(encoding="utf-8")
    # Count occurrences of the old bad pattern vs the correct one
    bad_pattern  = "d.id AS id"
    good_pattern = "d.decision_id AS id"

    bad_count  = src.count(bad_pattern)
    good_count = src.count(good_pattern)

    assert bad_count == 0, (
        f"metrics.py still contains {bad_count} occurrence(s) of 'd.id AS id'. "
        f"These should all be 'd.decision_id AS id'. "
        f"This causes 'DEC-None' duplicate keys in the compounding endpoint. "
        f"BUG REPORT -- do not fix in this file."
    )
    assert good_count >= 1, (
        f"metrics.py has no occurrences of 'd.decision_id AS id' -- "
        f"evolution-events Cypher may be using the wrong property name."
    )


def test_alert_id_property_in_evolution_events_query():
    """
    The evolution-events Cypher must traverse DECIDED_ON and select a.alert_id.
    alert_id is a property of Alert nodes, not Decision nodes.
    Decision nodes carry no denormalized alert_id field -- the relationship is
    the canonical reference: (d:Decision)-[:DECIDED_ON]->(a:Alert).
    """
    import pathlib

    src = pathlib.Path("app/routers/metrics.py").read_text(encoding="utf-8")
    assert "a.alert_id AS alert_id" in src, (
        "metrics.py evolution-events query must select a.alert_id AS alert_id "
        "via DECIDED_ON relationship. Decision nodes do not store alert_id directly."
    )


# ============================================================================
# GROUP 3 — SOC_PROFILE_CENTROIDS shape contracts
# ============================================================================

def test_soc_profile_centroids_shape():
    """
    SOC_PROFILE_CENTROIDS must have shape (6, 4, 6):
      6 categories x 4 SCORER_ACTIONS x 6 factors.
    refer_to_analyst is excluded (it's a routing gate, not a centroid action).
    """
    from app.domains.soc.config import SOC_PROFILE_CENTROIDS

    assert SOC_PROFILE_CENTROIDS.shape == (6, 4, 6), (
        f"SOC_PROFILE_CENTROIDS shape {SOC_PROFILE_CENTROIDS.shape} != (6, 4, 6). "
        f"Axis-1 must equal len(SCORER_ACTIONS)=4, not len(SOC_ACTIONS)=5."
    )


def test_scorer_actions_excludes_refer_to_analyst():
    """
    SCORER_ACTIONS must have exactly 4 entries and must NOT include
    'refer_to_analyst'.  Mixing SCORER_ACTIONS with SOC_ACTIONS causes a
    ProfileScorer shape error (A=4 vs A=5 broadcast failure).
    """
    from app.domains.soc.config import SCORER_ACTIONS

    assert len(SCORER_ACTIONS) == 4, (
        f"SCORER_ACTIONS has {len(SCORER_ACTIONS)} items, expected 4. "
        f"Actions: {SCORER_ACTIONS}"
    )
    assert "refer_to_analyst" not in SCORER_ACTIONS, (
        "SCORER_ACTIONS must not contain 'refer_to_analyst'. "
        "That action is handled by the confidence gate in triage.py."
    )


def test_scorer_profile_centroids_is_same_as_soc_profile_centroids():
    """
    SCORER_PROFILE_CENTROIDS must be identical to SOC_PROFILE_CENTROIDS
    (same object or identical values) now that refer_to_analyst has been removed.
    """
    import numpy as np
    from app.domains.soc.config import SOC_PROFILE_CENTROIDS, SCORER_PROFILE_CENTROIDS

    np.testing.assert_array_equal(
        SCORER_PROFILE_CENTROIDS, SOC_PROFILE_CENTROIDS,
        err_msg=(
            "SCORER_PROFILE_CENTROIDS differs from SOC_PROFILE_CENTROIDS. "
            "They should be identical after refer_to_analyst removal."
        )
    )


def test_detection_engineering_endpoint_no_shape_error():
    """
    GET /api/soc/detection-engineering must return 200 (no shape broadcast error).
    A (6,5,6) vs (6,4,6) mismatch between SOC_PROFILE_CENTROIDS and scorer.centroids
    caused this endpoint to crash with a 500 before the root-cause fix.
    """
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/soc/detection-engineering")
    assert resp.status_code == 200, (
        f"detection-engineering returned {resp.status_code}. "
        f"Possible shape mismatch between SOC_PROFILE_CENTROIDS and scorer.centroids. "
        f"Response: {resp.text[:500]}"
    )


# ============================================================================
# GROUP 4 — Response type contracts
# ============================================================================

def test_analytics_correct_decisions_is_integer():
    """
    GET /api/soc/analytics -> correct_decisions must be a Python int, not a
    string or None.  The Cypher query returns an AGE integer; the backend
    casts with int() before returning.
    """
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/soc/analytics")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    cd = data.get("correct_decisions")
    assert isinstance(cd, int), (
        f"correct_decisions is {type(cd).__name__!r} (value={cd!r}), expected int. "
        f"AGE may have returned a string or null."
    )


def test_analytics_total_alerts_is_integer():
    """
    GET /api/soc/analytics -> total_alerts must be int.
    """
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/soc/analytics")
    assert resp.status_code == 200
    data = resp.json()
    ta = data.get("total_alerts")
    assert isinstance(ta, int), (
        f"total_alerts is {type(ta).__name__!r} (value={ta!r}), expected int."
    )


def test_executive_narrative_top_shifts_is_list():
    """
    GET /api/soc/executive-narrative -> what_changed.top_shifts must be a list.
    It is built by appending dicts in executive_narrative.py; if the AGE query
    fails the list falls back to [] -- still a list, never None or a string.
    """
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/soc/executive-narrative")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    what_changed = data.get("what_changed", {})
    top_shifts = what_changed.get("top_shifts")
    assert isinstance(top_shifts, list), (
        f"what_changed.top_shifts is {type(top_shifts).__name__!r} (value={top_shifts!r}), "
        f"expected list."
    )


def test_threat_landscape_nodes_is_integer():
    """
    GET /api/soc/threat-landscape -> graph_coverage.nodes must be int.
    The Cypher COUNT() returns a numeric; backend wraps in int().
    """
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/soc/threat-landscape")
    assert resp.status_code in (200, 503), f"Expected 200 with live AGE or 503, got {resp.status_code}"
    if resp.status_code == 503:
        return
    data = resp.json()
    nodes = data.get("graph_coverage", {}).get("nodes")
    assert data.get("source") == "age", "A 200 response must identify live AGE as its source"
    assert isinstance(nodes, int), (
        f"graph_coverage.nodes is {type(nodes).__name__!r} (value={nodes!r}), expected int."
    )


def test_threat_landscape_source_field_present():
    """
    GET /api/soc/threat-landscape -> source field must be present.
    AGE unavailability is an explicit 503 rather than a synthetic payload.
    """
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/soc/threat-landscape")
    assert resp.status_code in (200, 503), f"Expected 200 with live AGE or 503, got {resp.status_code}"
    if resp.status_code == 503:
        return
    data = resp.json()
    assert data.get("source") == "age", "A 200 response must identify live AGE as its source"
