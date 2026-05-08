# RL Design v4.1 — Phase 0 Corrections Applied
**Date:** May 6, 2026
**Version:** 4.1 (Phase 0 findings applied: eta field names, headroom ratio, exploration formula)
**Authority:** MAP v5.65 · Framework v4 · Phase 0 findings: `docs/implementation_plans/rl_phase0_findings.md`
**Supersedes:** rl_design_v4.md

---

## §0 — Change Summary (v4.0 → v4.1)

| Change | Source | Impact |
|---|---|---|
| `scorer.calibration.eta_confirm` → `scorer.eta` | Phase 0 P1/P2/P2b: CalibrationProfile values copied into scorer attrs at construction. No `scorer.calibration` exists. | All eta pseudocode corrected. |
| `scorer.calibration.eta_override` → `scorer.eta_override` | Same finding. `eta_override` IS a scorer attribute (profile_scorer.py:164, 273-274). | Already correct name, wrong access path. |
| Added `scorer.eta_neg` to eta modulation | Phase 0 finding: scorer has THREE eta fields: `eta`, `eta_neg`, `eta_override`. All must be temporarily modified. | Existing triage pattern only changes `eta_override`. Phase 4 changes all three — larger scope. |
| Conservation margin → headroom RATIO | Phase 0 P5: `check_conservation()` returns `headroom = signal / theta_min` (ratio), NOT `signal - theta_min` (additive). | Exploration formula corrected. Threshold is 1.0 (ratio), not 0 (additive). |
| `target_headroom` semantics corrected | Ratio-based: `target_headroom = 10.0` means full exploration when signal is 10× theta_min. | Formula and comments updated. |
| Synthetic bandit validated | Phase 0: regret 24.5 (bound 176.8), zero exploration at margin≤0, correlation 0.97. | Design is empirically validated. |

**All other sections from v4.0 remain unchanged.** Only §3.4, §5.2, §5.3, and §10
are modified. This document repeats those sections with corrections and marks all
other sections as "unchanged from v4.0 — see rl_design_v4.md."

---

## §3.4 — η Modulation (CORRECTED)

### Live ProfileScorer Eta Fields

```
scorer.eta           ← correct-path learning rate (default 0.05)
scorer.eta_neg       ← secondary learning rate (default 0.05)
scorer.eta_override  ← override/incorrect path (default 0.01 for SOC)
```

These are copied from `CalibrationProfile.extensions` during `ProfileScorer.__init__()`.
Mutating CalibrationProfile AFTER construction has zero effect on the scorer.
The mutable attributes are on the scorer instance directly.

There is NO `scorer.calibration` attribute. Phase 0 eta contract tests verified this.

### Corrected Temporary Multiplier Pattern

```python
# Phase 4: Inside triage.py report_decision_outcome(), LEARNING_ENABLED branch:

async with acquire_scorer() as scorer:
    # Save ALL THREE eta fields
    original_eta = scorer.eta
    original_eta_neg = scorer.eta_neg
    original_eta_override = scorer.eta_override
    try:
        # Apply reward weight multiplier to ALL paths
        scorer.eta = original_eta * reward_result.reward_weight
        scorer.eta_neg = original_eta_neg * reward_result.reward_weight
        scorer.eta_override = original_eta_override * reward_result.reward_weight
        guarded_update(scorer, f, cat_idx, act_idx, correct)
    finally:
        # ALWAYS restore — even on exception
        scorer.eta = original_eta
        scorer.eta_neg = original_eta_neg
        scorer.eta_override = original_eta_override
```

### Difference from Existing Triage Pattern

The existing pattern at triage.py:1104-1124 only modifies `scorer.eta_override`
(the override/incorrect path for per-analyst η weighting). It does NOT modify
`scorer.eta` or `scorer.eta_neg`.

The RL η modulation modifies ALL THREE because graded rewards should affect both
correct-confirmation updates (via `scorer.eta`) and override updates (via
`scorer.eta_override`). This is a larger scope than the existing pattern.

Phase 0 test T2/T3/T4/T6 verified this works correctly with all three fields.

### Effective Ranges (with clip [0.1, 3.0])

| Field | Default (SOC) | Min effective | Max effective |
|---|---|---|---|
| scorer.eta | 0.05 | 0.005 | 0.15 |
| scorer.eta_neg | 0.05 | 0.005 | 0.15 |
| scorer.eta_override | 0.01 | 0.001 | 0.03 |

All within the validated 24-persona sweep envelope.

---

## §5.2 — Beta Posterior (UNCHANGED except import)

Uses `random.betavariate(alpha, beta)` from stdlib. No scipy.
All other §5.2 content unchanged from v4.0.

---

## §5.3 — Conservation-Bounded Exploration Rate (CORRECTED)

### Headroom Is a RATIO, Not Additive Margin

`LearningHealthMonitor.evaluate()` returns:
```python
{
    "signal": alpha * q * V,          # e.g., 13.2
    "theta_min": theta_min,           # e.g., 0.467
    "conservation": {
        "passed": True,
        "headroom": signal / theta_min  # e.g., 28.3 (ratio)
    }
}
```

`headroom = signal / theta_min` is computed by `check_conservation()` in
`gae/calibration.py:257-258`. It is a RATIO: headroom=1.0 means exactly at
the conservation floor. headroom=10.0 means signal is 10× the floor.

### Corrected Exploration Rate Formula

```python
def _compute_rate(self, headroom_ratio: float) -> float:
    """
    headroom_ratio = signal / theta_min (from conservation.headroom)
    
    headroom ≤ 1.0: conservation violated or tight → exploration = 0
    headroom ≥ target_headroom: healthy → full exploration = ε_base
    Linear interpolation between 1.0 and target_headroom.
    
    target_headroom = 10.0 means full exploration when signal is 10×
    the conservation floor.
    """
    if headroom_ratio <= 1.0:
        return 0.0
    normalized = min(
        (headroom_ratio - 1.0) / (self.target_headroom - 1.0),
        1.0
    )
    return self.epsilon_base * normalized
```

### Reference Values (SOC)

| Condition | headroom_ratio | Exploration rate |
|---|---|---|
| Healthy (α=0.1, q=0.88, V=150) | ~28.3 | 5.0% (full) |
| Moderate stress (q=0.55) | ~17.7 | 5.0% (full, above target) |
| Under pressure (q=0.15) | ~4.8 | 2.1% |
| Conservation tight (headroom=1.5) | 1.5 | 0.3% |
| AMBER (headroom≤1.0) | ≤1.0 | 0% |

### Synthetic Bandit Validation (Phase 0 Result)

```
Steps: 5000
Cumulative regret: 24.5 (bound: 176.8) — PASS
Optimal selection: 100% — PASS
Exploration during margin≤0: 0 — PASS
Margin-rate correlation: 0.97 — PASS
```

---

## §10 — Resolved Decisions (UPDATED)

| # | Question | Decision | Rationale |
|---|---|---|---|
| Q1 | target_headroom | 10.0 (ratio) | Conservative. Full exploration at 10× floor. |
| Q2 | CHAIN_DISCOUNT | 0.5 | Meaningful for display without double-counting. |
| Q3 | Posterior reset vs decay | Reset to (2,2) | Simpler. Decay preserves stale posteriors. |
| Q4 | η clip range | [0.1, 3.0] | Max eta=0.15, eta_override=0.03. Validated. |
| Q5 | Exploration in demo | Proposals LOGGED, not acted on | Conservative. |
| Q6 | Eta integration | Temporary multiplier on scorer.eta/eta_neg/eta_override | Phase 0 verified. No GAE API change. |
| Q7 | Persistence backend | PostgreSQL (existing) | Zero new dependency. |
| Q8 | Thompson sampling | random.betavariate (stdlib) | Zero new dependency. |
| Q9 | S2P timing | Design intent only. SOC-first. | supply_chain domain is stub. |
| Q10 | Action-space scope | SCORER_ACTIONS only (4 for SOC) | Never refer_to_analyst. |
| **Q11** | **Headroom semantics** | **Ratio (signal/theta_min), threshold at 1.0** | **Phase 0 finding. calibration.py:257-258.** |
| **Q12** | **Eta field names** | **scorer.eta, scorer.eta_neg, scorer.eta_override** | **Phase 0 finding. No scorer.calibration.** |

---

## §8 — Feature Flags (CLARIFICATION)

The v4.0 feature-flag list includes `RL_FORCE_NO_EXPLORE_PRE_ACTIVATION`.
That flag is **design-only and not implemented**. Do not add it as a runtime
flag without a separate design review.

Implemented RL flags remain:

```python
RL_REWARD_LEDGER_ENABLED = False
RL_EXPLORATION_ENABLED = False
RL_ETA_MODULATION_ENABLED = False
RL_CHAIN_CREDIT_ENABLED = False
```

Pre-activation safety is enforced by existing triage integration gates, referral
authority, exploration metadata, and the default `LEARNING_ENABLED = False`
centroid-mutation gate. Exploration remains controlled by
`RL_EXPLORATION_ENABLED` plus conservation headroom ratio.

---

## All Other Sections — Unchanged from v4.0

§1 (What CI's RL Is), §2 (Architecture), §3.1-3.3 (RewardComputer formulas),
§3.5-3.9 (LEARNING_ENABLED, RewardResult, severity weights, validation),
§4 (CreditAssigner), §5.1 (design), §5.4-5.8 (posterior update rules, reset,
ExplorationDecision, LEARNING_ENABLED interaction), §6 (PosteriorStore),
§7 (RewardLedger), §9 (Phased plan + schedule),
§10 invariants, §12 (Codex guidance) — all unchanged.

Refer to `docs/implementation_plans/rl_design_v4.md` for those sections.

---

## §12 — Codex Review Verification (UPDATED)

```
VERIFY (updated items marked with *):
1. RewardComputer returns BOTH graded_reward AND binary_outcome
2. Conservation q is NEVER computed from graded rewards
3.* η_effective uses temporary multiplier on scorer.eta, scorer.eta_neg, scorer.eta_override
4.* Temporary eta is ALWAYS restored in finally — all THREE fields
5. CreditAssigner reads Decision nodes (d.), not EvolutionEvent (e.)
6. Chain credit sum ≤ 0.5 × abs(direct_reward)
7.* Exploration rate = 0 when headroom_ratio ≤ 1.0 (ratio, not additive)
8. Referral veto fires AFTER exploration proposal
9. Referral-vetoed explorations do NOT update posteriors
10. All AGE queries use _S(), no $param
11. Factor attribution calls score() only, never update()
12. RewardComputer fires regardless of LEARNING_ENABLED
13. Posterior updates require RL_EXPLORATION_ENABLED + explored + not referred
14. PosteriorStore uses existing PostgreSQL (port 5433)
15. Thompson sampling uses random.betavariate (stdlib)
16. No new dependencies beyond numpy + psycopg + random
17. Feature flags default False
18. Exploration metadata written via post-write SET

FLAG IF:
- Any reference to scorer.calibration.eta_confirm (does not exist)
- Any reference to scorer.calibration.eta_override via calibration (wrong path)
- Any headroom treated as additive margin instead of ratio
- Any graded_reward → conservation q path
- Any exploration at headroom ≤ 1.0
- Any ProfileScorer.update() receiving unknown kwargs
```

---

*RL Design v4.1 · May 6, 2026*
*Phase 0 corrections: scorer.eta (not calibration.eta_confirm),*
*headroom ratio (not additive margin), all three eta fields modulated.*
*Synthetic bandit validated: regret 24.5, correlation 0.97, zero violations.*
