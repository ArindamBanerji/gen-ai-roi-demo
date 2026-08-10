"""
Tests for NLTemplateEngine (Sec.23.3) and SimilarCasesService (Sec.23.4).

Coverage:
  test_render_l1_all_categories         -- all 6 L1 templates render cleanly
  test_render_l1_refer                  -- refer-to-analyst template renders
  test_render_l1_generic_fallback       -- unknown category falls back to L1_GENERIC
  test_similar_cases_cosine             -- cosine_similarity correctness
  test_similar_cases_category_filter    -- cross-category isolation
  test_similar_cases_min_prior_suppression -- fewer than MIN_PRIOR -> empty result
"""

import asyncio
import pytest
import numpy as np
from unittest.mock import AsyncMock, patch

from app.services.nl_templates import NLTemplateEngine, nl_engine
from app.services.similar_cases import (
    SimilarCasesService,
    similar_cases_svc,
    SIMILAR_CASES_MIN_PRIOR,
    SIMILAR_CASES_THETA,
)
from app.domains.soc.config import SOC_CATEGORIES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_context(**extra) -> dict:
    """Return a minimal context that satisfies common L1 template fields."""
    ctx = {
        "action_display":      "Escalate",
        "confidence":          0.87,
        "calibration_count":   42,
        "category":            "credential_access",
        "user_display":        "alice@corp.com",
        "asset_name":          "finance-server-01",
        "asset_criticality":   "high",
        "time_context":        "Login at 02:47 UTC -- 3.8 SD above baseline",
        "pattern_context":     "Matches 2 prior escalations this month",
        "threat_context":      "No IOC matches in 412 checked indicators",
        "travel_context":      "No travel record to Singapore in past 90 days",
        "device_context":      "MDM-enrolled, last seen 6h ago",
        "ioc_context":         "Source IP in APT29 IOC list",
        "asset_context":       "finance-server-01 (CRITICAL, stores PII)",
        "indicator_type":      "IP address",
        "source_name":         "CISA KEV",
        "source_host":         "ws-112",
        "destination_host":    "finance-server-01",
        "volume_context":      "4.2 GB transferred in 8 min (7x baseline)",
        "user_role":           "Finance Analyst",
        "action_description":  "bulk export from DataClass=PCI_SCOPE",
        "access_context":      "47% above role baseline data volume",
        "cloud_operation":     "IAM policy modified: GrantFullAccess",
        "device_description":  "Device not in CMDB -- unregistered",
        "situation_type":      "Anomalous Login",
        "dominant_factors_description": "travel_match=0.82, asset_criticality=0.91",
    }
    ctx.update(extra)
    return ctx


# ---------------------------------------------------------------------------
# Test 1: render_l1 for all 6 SOC categories
# ---------------------------------------------------------------------------

def test_render_l1_all_categories():
    """
    Each of the 6 production categories must render to a non-empty string
    with no unresolved template placeholders (no literal '{' in output).
    """
    engine = NLTemplateEngine()

    for category in SOC_CATEGORIES:
        ctx    = _minimal_context(category=category)
        result = engine.render_l1(category, ctx)

        assert isinstance(result, str), (
            f"render_l1({category!r}) must return str, got {type(result)}"
        )
        assert len(result) > 20, (
            f"render_l1({category!r}) output too short: {result!r}"
        )
        assert "{" not in result, (
            f"render_l1({category!r}) has unresolved template vars: {result!r}"
        )


# ---------------------------------------------------------------------------
# Test 2: render_l1_refer
# ---------------------------------------------------------------------------

def test_render_l1_refer():
    """
    render_l1_refer must return a string mentioning analyst or tier-1 review,
    with no unresolved template placeholders.
    """
    engine = NLTemplateEngine()
    ctx = {
        "confidence":                 0.52,
        "category":                   "insider_threat",
        "threshold":                  0.65,
        "dominant_factor_explanation": "pattern_history=0.78 above action threshold",
        "rationale":                  "Behavioral anomaly outside 3-factor confidence band",
    }
    result = engine.render_l1_refer(ctx)

    assert isinstance(result, str)
    assert len(result) > 20
    assert "{" not in result, f"Unresolved vars in refer template: {result!r}"
    # Must mention either "analyst" or "Refer" (case-insensitive)
    assert "analyst" in result.lower() or "refer" in result.lower(), (
        f"render_l1_refer output should mention analyst/refer: {result!r}"
    )


# ---------------------------------------------------------------------------
# Test 3: unknown category falls back to L1_GENERIC
# ---------------------------------------------------------------------------

def test_render_l1_generic_fallback():
    """
    An unrecognised category key must silently fall back to L1_GENERIC
    and still produce a clean, non-empty string.
    """
    engine = NLTemplateEngine()
    ctx    = _minimal_context()
    result = engine.render_l1("unknown_category_xyz", ctx)

    assert isinstance(result, str)
    assert len(result) > 20
    assert "{" not in result, (
        f"L1_GENERIC fallback has unresolved vars: {result!r}"
    )


# ---------------------------------------------------------------------------
# Test 4: cosine_similarity correctness
# ---------------------------------------------------------------------------

def test_similar_cases_cosine():
    """
    cosine_similarity must be 1.0 for identical vectors, 0.0 for orthogonal,
    and > 0 for similar-direction vectors.
    """
    svc = SimilarCasesService()

    f1 = [0.8, 0.2, 0.9, 0.1, 0.7, 0.3]
    f2 = [0.8, 0.2, 0.9, 0.1, 0.7, 0.3]   # identical
    f3 = [0.0, 0.0, 0.0, 0.0, 0.0, 1.0]   # orthogonal to f4
    f4 = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]   # orthogonal to f3

    # Identical → 1.0
    assert abs(svc.cosine_similarity(f1, f2) - 1.0) < 1e-6, (
        "Identical vectors must have cosine similarity 1.0"
    )

    # Orthogonal → 0.0
    assert abs(svc.cosine_similarity(f3, f4) - 0.0) < 1e-6, (
        "Orthogonal vectors must have cosine similarity 0.0"
    )

    # Same direction, different magnitude → still 1.0
    f5 = [x * 2 for x in f1]
    assert abs(svc.cosine_similarity(f1, f5) - 1.0) < 1e-6, (
        "Scaled identical direction must have cosine similarity 1.0"
    )

    # Zero vector → 0.0 (not an error)
    f_zero = [0.0] * 6
    assert svc.cosine_similarity(f_zero, f1) == 0.0, (
        "Zero vector should yield cosine similarity 0.0 (no error)"
    )


# ---------------------------------------------------------------------------
# Test 5: category filter — get_similar_cases never crosses categories
# ---------------------------------------------------------------------------

def test_similar_cases_category_filter():
    """
    get_similar_cases retrieves decisions filtered by category.
    If the mock AGE returns decisions from a different category,
    they must not be returned (the Cypher WHERE clause enforces this,
    and the Python layer trusts the DB filter).

    We verify via the Cypher parameter: category is passed correctly,
    not swapped or omitted.
    """
    svc = SimilarCasesService()

    # Build enough fake decisions to pass MIN_PRIOR threshold
    fake_decisions = [
        {
            "decision_id": f"DEC-{i:04d}",
            "action":      "escalate",
            "confidence":  0.88,
            "outcome":     "correct",
            "factor_vector": [0.7, 0.8, 0.6, 0.5, 0.4, 0.2],
            "timestamp":   f"2026-03-{i+1:02d}T10:00:00Z",
        }
        for i in range(SIMILAR_CASES_MIN_PRIOR + 2)
    ]

    captured_params = {}

    async def mock_run_query(query, params=None):
        captured_params.update(params or {})
        return [
            {
                "decision_id": d["decision_id"],
                "action":      d["action"],
                "confidence":  d["confidence"],
                "outcome":     d["outcome"],
                "factor_vector": d["factor_vector"],
                "timestamp":   d["timestamp"],
            }
            for d in fake_decisions
        ]

    class FakeAGE:
        run_query = staticmethod(mock_run_query)

    f = [0.7, 0.8, 0.6, 0.5, 0.4, 0.2]
    target_category = "credential_access"

    result = asyncio.run(
        svc.get_similar_cases(f, target_category, FakeAGE())
    )

    # The query MUST filter by the requested category
    assert captured_params.get("category") == target_category, (
        f"AGE query must filter by category={target_category!r}, "
        f"got category={captured_params.get('category')!r}"
    )


# ---------------------------------------------------------------------------
# Test 6: fewer than MIN_PRIOR decisions → empty list returned
# ---------------------------------------------------------------------------

def test_similar_cases_min_prior_suppression():
    """
    When fewer than SIMILAR_CASES_MIN_PRIOR (5) verified decisions exist
    in the category, get_similar_cases must return [] (sidebar suppressed).
    """
    svc = SimilarCasesService()

    # Only 3 decisions — below MIN_PRIOR=5
    few_decisions = [
        {
            "decision_id": f"DEC-FEW-{i}",
            "action":      "investigate",
            "confidence":  0.75,
            "outcome":     "correct",
            "factor_vector": [0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
            "timestamp":   "2026-03-01T10:00:00Z",
        }
        for i in range(SIMILAR_CASES_MIN_PRIOR - 2)  # 3 decisions
    ]

    assert len(few_decisions) < SIMILAR_CASES_MIN_PRIOR, (
        "Test setup error: few_decisions must be below MIN_PRIOR"
    )

    async def mock_run_query(query, params=None):
        return [
            {
                "decision_id": d["decision_id"],
                "action":      d["action"],
                "confidence":  d["confidence"],
                "outcome":     d["outcome"],
                "factor_vector": d["factor_vector"],
                "timestamp":   d["timestamp"],
            }
            for d in few_decisions
        ]

    class FakeAGE:
        run_query = staticmethod(mock_run_query)

    f = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
    result = asyncio.run(
        svc.get_similar_cases(f, "credential_access", FakeAGE())
    )

    assert result == [], (
        f"Expected [] when fewer than MIN_PRIOR ({SIMILAR_CASES_MIN_PRIOR}) "
        f"decisions in category; got {len(result)} results"
    )

    # Also verify agreement_pct returns None for empty list
    pct = svc.get_agreement_pct([], "escalate")
    assert pct is None, (
        f"get_agreement_pct must return None for empty similar_cases, got {pct!r}"
    )
