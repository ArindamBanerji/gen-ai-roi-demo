"""
SOC Copilot accuracy constants.
Derived from V-ACC-TRAJ-2 + V-ACC-TRAJ-3 (March 27, 2026).
These are published reference values — not recomputed per deployment.
Platform-validated: SOC + S2P confirmed.
"""

# Universal enriched plateau (SOC + S2P confirmed identical)
ENRICHED_PLATEAU = 0.918

# Cold-start plateau by sigma band (approaches asymptotically)
COLD_START_PLATEAU_BY_SIGMA = {
    "low":    0.890,   # σ≤0.12: gap ~3-4pp
    "medium": 0.847,   # σ=0.13-0.22: gap ~7-7.5pp
    "high":   0.830,   # σ>0.22: gap ~8-9pp
}

# Permanent accuracy gap by sigma band (enriched - cold-start plateau)
PERMANENT_GAP_BY_SIGMA = {
    "low":    0.035,   # 3.5pp
    "medium": 0.075,   # 7.5pp (SOC 7.0pp, S2P 8.0pp — midpoint)
    "high":   0.088,   # 8.8pp
}


def get_sigma_band(sigma: float) -> str:
    """Classify sigma into low/medium/high band."""
    if sigma <= 0.12:
        return "low"
    if sigma <= 0.22:
        return "medium"
    return "high"


def get_permanent_gap_pp(sigma: float) -> float:
    """Expected permanent accuracy gap in pp for this sigma."""
    return round(PERMANENT_GAP_BY_SIGMA[get_sigma_band(sigma)] * 100, 1)


# SOC cold-start reference trajectory (V-ACC-TRAJ-1b-v2, σ=0.18 q̄=0.75)
# Key: decision count. Value: mean accuracy as fraction.
COLD_START_REFERENCE_TRAJECTORY = {
    50:   0.275,
    100:  0.313,
    200:  0.393,
    500:  0.558,
    1000: 0.653,
    1500: 0.720,
    2000: 0.750,
    3000: 0.769,
}

# S2P cold-start reference (V-ACC-TRAJ-3-v3, σ=0.18 q̄=0.75)
S2P_ENRICHED_PLATEAU = 0.781
S2P_COLD_PLATEAU     = 0.701
S2P_PERMANENT_GAP    = 0.080   # 8.0pp at σ=0.18

S2P_COLD_START_REFERENCE = {
    50:   0.275,
    100:  0.319,
    200:  0.401,
    500:  0.571,
    1000: 0.661,
    3000: 0.701,
}
