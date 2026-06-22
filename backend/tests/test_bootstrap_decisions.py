"""
Tests for CORR-3: Bootstrap Decision node writing + native factor_vector storage.

Coverage:
  test_bootstrap_creates_decision_records   -- build_bootstrap_decisions returns records
  test_factor_vector_native_storage         -- factor_vector is a Python list (not str)
  test_bootstrap_decision_has_required_fields -- all required fields present
"""

import pytest
import numpy as np


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_scorer():
    """Real ProfileScorer from SOC config (uses calibrated centroids)."""
    from app.domains.soc.config import SOCDomainConfig
    return SOCDomainConfig().build_profile_scorer()


def _small_decisions_per_category():
    """Small count per category for test speed."""
    from app.domains.soc.config import SOC_CATEGORIES
    return {cat: 5 for cat in SOC_CATEGORIES}


# ---------------------------------------------------------------------------
# Test 1: build_bootstrap_decisions returns the right number of records
# ---------------------------------------------------------------------------

def test_bootstrap_creates_decision_records():
    """
    build_bootstrap_decisions returns one record per decision in the pool.
    With 5 decisions per category x 6 categories = 30 total.
    Each record has source='bootstrap'.
    """
    from app.domains.soc.config import SOC_CATEGORIES
    from app.services.bootstrap_neo4j import build_bootstrap_decisions

    scorer  = _make_scorer()
    d_per_c = _small_decisions_per_category()
    records = build_bootstrap_decisions(scorer, list(SOC_CATEGORIES), d_per_c)

    expected_total = sum(d_per_c.values())  # 5 x 6 = 30
    assert len(records) == expected_total, (
        f"Expected {expected_total} records, got {len(records)}"
    )

    # Every record must declare source='bootstrap'
    for rec in records:
        assert rec.get("source") == "bootstrap", (
            f"Record source must be 'bootstrap', got {rec.get('source')!r}"
        )

    # Actions must all be valid SOC actions
    from app.domains.soc.config import SOC_ACTIONS
    for rec in records:
        assert rec["action"] in SOC_ACTIONS, (
            f"Unknown action {rec['action']!r}"
        )

    # Categories must all be valid SOC categories
    for rec in records:
        assert rec["category"] in SOC_CATEGORIES, (
            f"Unknown category {rec['category']!r}"
        )


# ---------------------------------------------------------------------------
# Test 2: factor_vector is a native Python list, not a JSON string
# ---------------------------------------------------------------------------

def test_factor_vector_native_storage():
    """
    factor_vector in each bootstrap Decision record is a Python list, not
    a JSON-encoded string.  The Neo4j Python driver sends lists as native
    Neo4j arrays; JSON strings would require an extra json.loads() step.
    """
    from app.domains.soc.config import SOC_CATEGORIES
    from app.services.bootstrap_neo4j import build_bootstrap_decisions

    scorer  = _make_scorer()
    d_per_c = {cat: 3 for cat in SOC_CATEGORIES}
    records = build_bootstrap_decisions(scorer, list(SOC_CATEGORIES), d_per_c)

    assert records, "Must have at least one record to test"

    for rec in records:
        fv = rec["factor_vector"]

        # Must be a plain Python list
        assert isinstance(fv, list), (
            f"factor_vector must be a list, got {type(fv).__name__}"
        )

        # Must NOT be a JSON-encoded string
        assert not isinstance(fv, str), (
            "factor_vector must not be a JSON string"
        )

        # Must contain 6 float values (one per SOC factor)
        assert len(fv) == 6, (
            f"Expected 6 factor values, got {len(fv)}"
        )

        # All values must be floats in [0, 1]
        for val in fv:
            assert isinstance(val, float), (
                f"Each factor value must be float, got {type(val).__name__}"
            )
            assert 0.0 <= val <= 1.0, (
                f"Factor value {val} outside [0, 1]"
            )

    # centroid_snapshot must also be a native list
    for rec in records:
        cs = rec["centroid_snapshot"]
        assert isinstance(cs, list), (
            f"centroid_snapshot must be a list, got {type(cs).__name__}"
        )


# ---------------------------------------------------------------------------
# Test 3: Bootstrap Decision records have all required fields
# ---------------------------------------------------------------------------

def test_bootstrap_decision_has_required_fields():
    """
    Each bootstrap Decision record must contain: id, action, confidence,
    factor_vector, category, source.
    (timestamp is set by Neo4j datetime() -- not in the Python dict.)
    """
    from app.domains.soc.config import SOC_CATEGORIES
    from app.services.bootstrap_neo4j import build_bootstrap_decisions

    REQUIRED_FIELDS = {"id", "action", "confidence", "factor_vector", "category", "source"}

    scorer  = _make_scorer()
    d_per_c = {cat: 2 for cat in SOC_CATEGORIES}
    records = build_bootstrap_decisions(scorer, list(SOC_CATEGORIES), d_per_c)

    assert records, "Must have at least one record"

    for i, rec in enumerate(records):
        for field in REQUIRED_FIELDS:
            assert field in rec, (
                f"Record {i} missing required field '{field}'"
            )
            assert rec[field] is not None, (
                f"Record {i} field '{field}' must not be None"
            )

    # Confidence must be a float in (0, 1]
    for rec in records:
        conf = rec["confidence"]
        assert isinstance(conf, float), (
            f"confidence must be float, got {type(conf).__name__}"
        )
        assert 0.0 < conf <= 1.0, (
            f"confidence {conf} outside (0, 1]"
        )

    # id must be a UUID-like non-empty string
    for rec in records:
        assert isinstance(rec["id"], str) and len(rec["id"]) > 0, (
            "id must be a non-empty string"
        )


# ---------------------------------------------------------------------------
# Phase 9 tests: BOOTSTRAP_CATEGORY_WEIGHTS
# ---------------------------------------------------------------------------

def test_bootstrap_weights_sum_to_one():
    """BOOTSTRAP_CATEGORY_WEIGHTS values must sum to exactly 1.0."""
    from app.domains.soc.config import BOOTSTRAP_CATEGORY_WEIGHTS
    total = sum(BOOTSTRAP_CATEGORY_WEIGHTS.values())
    assert abs(total - 1.0) < 1e-9, (
        f"BOOTSTRAP_CATEGORY_WEIGHTS must sum to 1.0, got {total}"
    )


def test_bootstrap_all_categories_present():
    """Every SOC_CATEGORY must have a weight > 0 in BOOTSTRAP_CATEGORY_WEIGHTS."""
    from app.domains.soc.config import SOC_CATEGORIES, BOOTSTRAP_CATEGORY_WEIGHTS
    for cat in SOC_CATEGORIES:
        w = BOOTSTRAP_CATEGORY_WEIGHTS.get(cat)
        assert w is not None, (
            f"Category {cat!r} missing from BOOTSTRAP_CATEGORY_WEIGHTS"
        )
        assert w > 0, (
            f"Category {cat!r} has weight {w} -- must be > 0"
        )


def test_bootstrap_weights_in_config():
    """BOOTSTRAP_CATEGORY_WEIGHTS must be importable from app.domains.soc.config."""
    try:
        from app.domains.soc.config import BOOTSTRAP_CATEGORY_WEIGHTS
    except ImportError as exc:
        pytest.fail(f"Could not import BOOTSTRAP_CATEGORY_WEIGHTS: {exc}")
    assert isinstance(BOOTSTRAP_CATEGORY_WEIGHTS, dict), (
        f"Expected dict, got {type(BOOTSTRAP_CATEGORY_WEIGHTS)}"
    )
    assert len(BOOTSTRAP_CATEGORY_WEIGHTS) == 6, (
        f"Expected 6 entries, got {len(BOOTSTRAP_CATEGORY_WEIGHTS)}"
    )


def test_bootstrap_weighted_distribution():
    """
    build_bootstrap_decisions() with weights=BOOTSTRAP_CATEGORY_WEIGHTS produces
    more decisions for credential_access than for cloud_infrastructure.

    credential_access weight=0.30 vs cloud_infrastructure weight=0.10,
    so credential_access must receive ~3x as many decisions.
    """
    from app.domains.soc.config import (
        SOC_CATEGORIES, BOOTSTRAP_CATEGORY_WEIGHTS, SOCDomainConfig,
    )
    from app.services.bootstrap_neo4j import build_bootstrap_decisions

    scorer  = SOCDomainConfig().build_profile_scorer()
    # Use 100 total decisions (divisible, easy to reason about percentages)
    d_per_c = {cat: round(100 / len(SOC_CATEGORIES)) for cat in SOC_CATEGORIES}

    records = build_bootstrap_decisions(
        scorer,
        list(SOC_CATEGORIES),
        d_per_c,
        weights=BOOTSTRAP_CATEGORY_WEIGHTS,
    )

    # Count per category
    counts: dict = {}
    for rec in records:
        counts[rec["category"]] = counts.get(rec["category"], 0) + 1

    cred  = counts.get("credential_access",    0)
    cloud = counts.get("cloud_infrastructure", 0)

    assert cred > cloud, (
        f"credential_access ({cred}) must exceed cloud_infrastructure ({cloud}) "
        f"when using BOOTSTRAP_CATEGORY_WEIGHTS"
    )
    # credential_access weight (0.30) should be ~3× cloud_infrastructure (0.10)
    assert cred >= cloud * 2, (
        f"credential_access ({cred}) should be at least 2x cloud_infrastructure ({cloud})"
    )
