# VLD With-Without Case Studies — TRADING
**Generated from Stage 1 multi-hop scenarios**
**[PLANTED POSITIVE CONTROL — not production data]**

## Summary

| Category | Count | % |
|---|---|---|
| VLD saves (SP wrong, VLD right) | 3 | 9% |
| VLD hurts (SP right, VLD wrong) | 1 | 3% |
| Both correct | 16 | 46% |
| Both wrong | 15 | 43% |
| **Total multi-hop** | **35** | |

## Case Studies: VLD Saves

*Scenarios where single-pass gets it wrong and VLD gets it right.*

### Case 1: TRD-MH-001-v1
**Type:** thesis_contradiction
**Kind:** score_keyed | **rho:** 0.7

**Description:** Proposed trade contradicts the sector thesis; the ticket does not say whether the thesis is current.

#### WITHOUT VLD (single-pass)
- Action: **hedge** ❌ (ground truth: execute)
- Based on surface factors only
- Distance to nearest centroid: 0.3559

#### WITH VLD (investigation)
- **Hop 1:** Checked the thesis version: it was revised a fortnight ago and the ticket cites the superseded one.
  - Checked: Thesis -> version, status, effective_from
  - Found: thesis revised to v4 two weeks ago; ticket cites v3
  - Factor `thesis_alignment`: 0.300 → 0.620
  - Action after hop 1: **hedge** → (dist: 0.1336)
- **Hop 2:** Checked the revision: energy moved from underweight to neutral, so the trade now aligns.
  - Checked: Thesis -> direction, revision_note
  - Found: v4 moved energy from underweight to neutral
  - Factor `thesis_alignment`: 0.620 → 0.860
  - Action after hop 2: **execute** ✅ (dist: 0.2095)

- Action: **execute** ✅
- Distance to nearest centroid: 0.2095

**Why VLD changed the decision:** The contradiction is against a superseded thesis version; the trade aligns with the current one.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| correlation_risk | 0.440 | 0.440 | +0.000 |
| fundamental_strength | 0.720 | 0.720 | +0.000 |
| liquidity_risk | 0.300 | 0.300 | +0.000 |
| portfolio_concentration | 0.550 | 0.550 | +0.000 |
| thesis_alignment | 0.300 | 0.860 | +0.560 ← |
| timing_signal | 0.600 | 0.600 | +0.000 |

### Case 2: TRD-MH-001-v5
**Type:** thesis_contradiction
**Kind:** score_keyed | **rho:** 0.3

**Description:** Proposed trade contradicts the sector thesis; the ticket does not say whether the thesis is current.

#### WITHOUT VLD (single-pass)
- Action: **reduce_size** ❌ (ground truth: hedge)
- Based on surface factors only
- Distance to nearest centroid: 0.5146

#### WITH VLD (investigation)
- **Hop 1:** Checked the thesis version: v3 is current and the trade contradicts it.
  - Checked: Thesis -> version, status
  - Found: thesis at v3, current; trade contradicts it
  - Factor `thesis_alignment`: 0.240 → 0.260
  - Action after hop 1: **reduce_size** → (dist: 0.4997)
- **Hop 2:** Checked existing exposure: the portfolio is already over its energy target.
  - Checked: Portfolio -> Position -> IN_SECTOR -> Sector, weight
  - Found: portfolio already 8.4% energy against a 6% target
  - Factor `correlation_risk`: 0.780 → 0.240
  - Action after hop 2: **hedge** ✅ (dist: 0.5303)

- Action: **hedge** ✅
- Distance to nearest centroid: 0.5303

**Why VLD changed the decision:** Rather than add contradicting exposure outright, offset the existing overweight. Note: the surface signal points at position_history_path (misleading) \u2014 low-rho instance.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| correlation_risk | 0.780 | 0.240 | -0.540 ← |
| fundamental_strength | 0.580 | 0.580 | +0.000 |
| liquidity_risk | 0.310 | 0.310 | +0.000 |
| portfolio_concentration | 0.820 | 0.820 | +0.000 |
| thesis_alignment | 0.240 | 0.260 | +0.020 |
| timing_signal | 0.570 | 0.570 | +0.000 |

### Case 3: TRD-MH-003-v2
**Type:** momentum_vs_mean_reversion
**Kind:** score_keyed | **rho:** 0.9

**Description:** Trending name; the price series looks the same under momentum and under stretched mean-reversion.

#### WITHOUT VLD (single-pass)
- Action: **execute** ❌ (ground truth: reject)
- Based on surface factors only
- Distance to nearest centroid: 0.3520

#### WITH VLD (investigation)
- **Hop 1:** Checked the volume profile: participation is contracting as the price advances.
  - Checked: VolumeProfile -> trend, rvol
  - Found: volume contracting into the advance, rvol 0.7
  - Factor `timing_signal`: 0.800 → 0.260
  - Action after hop 1: **reject** ✅ (dist: 0.2923)
- **Hop 2:** Checked sector breadth: only 22% of the sector is participating.
  - Checked: Sector -> breadth_pct, advancing_issues
  - Found: sector breadth 22%, the advance is 2 names
  - Factor `timing_signal`: 0.260 → 0.160
  - Action after hop 2: **reject** ✅ (dist: 0.3412)

- Action: **reject** ✅
- Distance to nearest centroid: 0.3412

**Why VLD changed the decision:** An unsupported advance on contracting volume and narrow breadth \u2014 a reversion setup, not a momentum one.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| correlation_risk | 0.340 | 0.340 | +0.000 |
| fundamental_strength | 0.380 | 0.380 | +0.000 |
| liquidity_risk | 0.320 | 0.320 | +0.000 |
| portfolio_concentration | 0.420 | 0.420 | +0.000 |
| thesis_alignment | 0.640 | 0.640 | +0.000 |
| timing_signal | 0.800 | 0.160 | -0.640 ← |


## Cases Where VLD Hurts

*1 scenarios where SP was right but VLD got it wrong.*

### Hurt Case 1: TRD-MH-001-v3
- SP: **reduce_size** ✅ | VLD: **hedge** ❌ | GT: reduce_size
- Kind: score_keyed | rho: 0.7
- Why: investigation moved factors in wrong direction
