"""
tests/test_enrichment_advisor.py — Enrichment advisor (expected_permanent_gap_pp).

4 tests validating ranked_factors and top_opportunity shapes, plus
sigma-scaling invariant.

Run from backend/:
    pytest tests/test_enrichment_advisor.py -v
"""

from app.services.enrichment_advisor import get_enrichment_advice, _ioc_coverage_band
from app.domains.soc.constants import get_permanent_gap_pp


# ============================================================================
# Test 1 — ranked_factors contains expected_permanent_gap_pp
# ============================================================================

def test_ranked_factors_has_expected_permanent_gap_pp():
    """
    Each entry in ranked_factors must contain 'expected_permanent_gap_pp'.
    This is the commercial hook: CISO sees a specific pp number per factor.
    """
    advice = get_enrichment_advice()
    ranked = advice["ranked_factors"]

    assert len(ranked) > 0, "ranked_factors must be non-empty"
    assert "expected_permanent_gap_pp" in ranked[0], (
        f"ranked_factors[0] missing 'expected_permanent_gap_pp': {list(ranked[0].keys())}"
    )


# ============================================================================
# Test 2 — expected_permanent_gap_pp is a float in each ranked factor
# ============================================================================

def test_ranked_factors_gap_pp_is_float():
    """
    expected_permanent_gap_pp must be a float for every factor in ranked_factors.
    """
    advice = get_enrichment_advice()
    for factor in advice["ranked_factors"]:
        gap = factor["expected_permanent_gap_pp"]
        assert isinstance(gap, float), (
            f"expected_permanent_gap_pp must be float for factor "
            f"'{factor['factor_name']}', got {type(gap)}"
        )
        assert gap > 0.0, (
            f"expected_permanent_gap_pp must be positive, got {gap} for "
            f"'{factor['factor_name']}'"
        )


# ============================================================================
# Test 3 — top_opportunity contains expected_permanent_gap_pp
# ============================================================================

def test_top_opportunity_has_expected_permanent_gap_pp():
    """
    top_opportunity must include expected_permanent_gap_pp and must match
    the first element of ranked_factors (highest sigma → highest gap).
    """
    advice = get_enrichment_advice()
    top = advice["top_opportunity"]

    assert "expected_permanent_gap_pp" in top, (
        f"top_opportunity missing 'expected_permanent_gap_pp': {list(top.keys())}"
    )
    # top_opportunity must equal ranked_factors[0]
    assert top["factor_name"] == advice["ranked_factors"][0]["factor_name"], (
        f"top_opportunity.factor_name={top['factor_name']!r} does not match "
        f"ranked_factors[0].factor_name={advice['ranked_factors'][0]['factor_name']!r}"
    )
    assert top["expected_permanent_gap_pp"] == advice["ranked_factors"][0]["expected_permanent_gap_pp"]


# ============================================================================
# Test 4 — expected_permanent_gap_pp scales with sigma
# ============================================================================

def test_permanent_gap_pp_scales_with_sigma():
    """
    High-sigma factor must have higher expected_permanent_gap_pp than low-sigma.
    get_permanent_gap_pp(0.28) > get_permanent_gap_pp(0.07) — invariant.
    """
    high_gap = get_permanent_gap_pp(0.28)
    low_gap  = get_permanent_gap_pp(0.07)

    assert high_gap > low_gap, (
        f"Expected gap to increase with sigma: "
        f"get_permanent_gap_pp(0.28)={high_gap} must be > "
        f"get_permanent_gap_pp(0.07)={low_gap}"
    )


# ============================================================================
# Test 5 — ioc_coverage_band thresholds
# ============================================================================

def test_ioc_coverage_band_assignment():
    """
    Band boundaries: ≥0.40 → strong, ≥0.20 → moderate, else → sparse.
    """
    assert _ioc_coverage_band(0.45) == "strong", "0.45 must be strong"
    assert _ioc_coverage_band(0.40) == "strong", "0.40 boundary must be strong"
    assert _ioc_coverage_band(0.25) == "moderate", "0.25 must be moderate"
    assert _ioc_coverage_band(0.20) == "moderate", "0.20 boundary must be moderate"
    assert _ioc_coverage_band(0.10) == "sparse", "0.10 must be sparse"
    assert _ioc_coverage_band(0.00) == "sparse", "0.00 must be sparse"


# ============================================================================
# Test 6 — ioc_coverage_note varies by band
# ============================================================================

def test_ioc_coverage_note_varies_by_band():
    """
    Strong note mentions '23% faster'; sparse note mentions '40%+'.
    Notes must differ between bands.
    """
    strong_advice = get_enrichment_advice(ioc_coverage=0.45)
    sparse_advice = get_enrichment_advice(ioc_coverage=0.10)

    strong_note = strong_advice["ioc_coverage_note"]
    sparse_note = sparse_advice["ioc_coverage_note"]

    assert strong_note != sparse_note, "Notes must differ between strong and sparse bands"
    assert "23%" in strong_note, (
        f"Strong note must mention '23%'. Got: {strong_note!r}"
    )
    assert "40%" in sparse_note, (
        f"Sparse note must mention '40%'. Got: {sparse_note!r}"
    )
