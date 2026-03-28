"""
app/services/enrichment_advisor.py — Enrichment opportunity advisor.

Ranks SOC factors by enrichment priority. For each factor, computes:
  expected_permanent_gap_pp — the permanent accuracy gap (in pp) that
  persists when this factor is NOT enriched, derived from its sigma profile.

Sigma values are empirical estimates from V-S2P-CONVERGENCE experiments,
reflecting each factor's observed variance across SOC alert populations.

Output shape:
  {
    "ranked_factors":  [FactorAdvisory, ...],  # sorted by sigma desc
    "top_opportunity": FactorAdvisory,          # highest-gap factor
  }

  FactorAdvisory keys:
    factor_name              str
    sigma                    float
    sigma_band               str   — low / medium / high
    expected_permanent_gap_pp float — pp gap if not enriched
    enrichment_priority      int   — 1 = highest priority
    recommendation           str
"""

from __future__ import annotations

from app.domains.soc.constants import get_sigma_band, get_permanent_gap_pp

# ---------------------------------------------------------------------------
# Per-factor sigma estimates — empirical from V-S2P-CONVERGENCE experiments.
# Sigma measures the inter-alert variance in each factor's output value.
# High sigma → factor is noisy → more to gain from structured enrichment.
# ---------------------------------------------------------------------------
FACTOR_SIGMA: dict[str, float] = {
    "threat_intel_enrichment": 0.28,   # high — source quality varies widely
    "pattern_history":         0.18,   # medium — history volume-dependent
    "time_anomaly":            0.15,   # medium — discrete windows, partial signal
    "asset_criticality":       0.12,   # low — discrete tiers, mostly stable
    "device_trust":            0.10,   # low — stable per device profile
    "travel_match":            0.07,   # low — largely binary match
}

# Human-readable enrichment recommendations per sigma band
_RECS: dict[str, str] = {
    "high": (
        "High-sigma factor — structured enrichment reduces variance most here. "
        "Connect external threat intel or CMDB APIs to stabilize this signal."
    ),
    "medium": (
        "Medium-sigma factor — moderate enrichment gain available. "
        "Analyst feedback and verified outcomes will drive centroid convergence."
    ),
    "low": (
        "Low-sigma factor — already well-calibrated. "
        "Enrichment will have limited impact; focus effort on higher-sigma factors."
    ),
}


def _build_factor_advisory(factor_name: str, sigma: float, rank: int) -> dict:
    """Build a single FactorAdvisory dict."""
    band = get_sigma_band(sigma)
    gap_pp = get_permanent_gap_pp(sigma)
    return {
        "factor_name":              factor_name,
        "sigma":                    sigma,
        "sigma_band":               band,
        "expected_permanent_gap_pp": gap_pp,
        "enrichment_priority":      rank,
        "recommendation":           _RECS[band],
    }


def get_enrichment_advice() -> dict:
    """
    Return ranked enrichment opportunities for all SOC factors.

    ranked_factors is sorted descending by sigma (highest gap first).
    top_opportunity is the first element (highest expected_permanent_gap_pp).
    """
    sorted_factors = sorted(
        FACTOR_SIGMA.items(), key=lambda x: x[1], reverse=True
    )
    ranked_factors = [
        _build_factor_advisory(name, sigma, rank=i + 1)
        for i, (name, sigma) in enumerate(sorted_factors)
    ]
    return {
        "ranked_factors":  ranked_factors,
        "top_opportunity": ranked_factors[0],
    }
