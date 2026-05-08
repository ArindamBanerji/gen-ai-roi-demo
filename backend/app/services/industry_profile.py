"""
industry_profile.py — Block 1.1: Industry profile loader and validator.

Provides per-industry deployment parameters (V, alpha, analyst_hourly_cost,
regulatory_multiplier) and computes derived metrics (theta_min, phase3_minimum,
roi_annual_usd) for the SOC Copilot demo.

Archetypes: healthcare, finserv, manufacturing, generic.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

log = logging.getLogger(__name__)

_PROFILES_PATH = Path(__file__).parent.parent / "data" / "industry_profiles.json"

# Cached at import time — file is static during runtime.
_PROFILES: Optional[Dict] = None


def _load_raw() -> Dict:
    global _PROFILES
    if _PROFILES is None:
        with open(_PROFILES_PATH, encoding="utf-8") as fh:
            _PROFILES = json.load(fh)
    return _PROFILES


def list_industries() -> List[str]:
    """Return sorted list of available industry IDs."""
    return sorted(_load_raw().keys())


def load_industry_profile(industry_id: str) -> Dict:
    """
    Return the full profile dict for *industry_id*, augmented with derived metrics.

    Derived fields added:
      theta_min       — minimum analyst quality for conservation law (23.53 / alpha*V)
      phase3_minimum  — minimum verified decisions for self-calibrating gates
      roi_annual_usd  — estimated annual ROI using industry analyst cost
      decisions_per_day — V * alpha

    Raises KeyError if industry_id is not found.
    """
    from gae.calibration import compute_theta_min
    from app.domains.soc.config import compute_phase3_minimum

    raw = _load_raw()
    if industry_id not in raw:
        raise KeyError(
            f"Unknown industry: {industry_id!r}. "
            f"Available: {sorted(raw.keys())}"
        )

    profile = dict(raw[industry_id])

    V     = float(profile["V"])
    alpha = float(profile["alpha"])
    hourly_cost = float(profile["analyst_hourly_cost"])
    reg_mult    = float(profile.get("regulatory_multiplier", 1.0))

    decisions_per_day = V * alpha
    theta_min         = compute_theta_min(alpha=alpha, V=V)
    phase3_min        = compute_phase3_minimum(V=V, alpha=alpha)

    # ROI: 0.25 analyst-hours saved per decision × industry hourly cost × 365 days
    roi_base      = round(decisions_per_day * 365 * 0.25 * hourly_cost, 2)
    roi_regulated = round(roi_base * reg_mult, 2)

    profile["decisions_per_day"] = round(decisions_per_day, 1)
    profile["theta_min"]         = round(theta_min, 4)
    profile["phase3_minimum"]    = phase3_min
    profile["roi_annual_usd"]    = roi_base
    profile["roi_annual_usd_regulated"] = roi_regulated

    return profile


def validate_profile(profile: Dict) -> List[str]:
    """
    Validate a profile dict for required fields and value ranges.

    Returns a list of error strings (empty list = valid).
    """
    errors: List[str] = []

    required = {"id", "label", "V", "alpha", "analyst_hourly_cost"}
    missing = required - set(profile.keys())
    if missing:
        errors.append(f"Missing required fields: {sorted(missing)}")

    v = profile.get("V")
    if v is not None and not (10 <= float(v) <= 10_000):
        errors.append(f"V={v} out of range [10, 10000]")

    a = profile.get("alpha")
    if a is not None and not (0.01 <= float(a) <= 1.0):
        errors.append(f"alpha={a} out of range [0.01, 1.0]")

    cost = profile.get("analyst_hourly_cost")
    if cost is not None and not (10 <= float(cost) <= 500):
        errors.append(f"analyst_hourly_cost={cost} out of range [10, 500]")

    rm = profile.get("regulatory_multiplier")
    if rm is not None and not (1.0 <= float(rm) <= 5.0):
        errors.append(f"regulatory_multiplier={rm} out of range [1.0, 5.0]")

    return errors
