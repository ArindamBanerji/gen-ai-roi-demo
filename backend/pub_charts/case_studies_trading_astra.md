# VLD With-Without Case Studies — TRADING_ASTRA
**Generated from Stage 1 multi-hop scenarios**
**[PLANTED POSITIVE CONTROL — not production data]**

## Summary

| Category | Count | % |
|---|---|---|
| VLD saves (SP wrong, VLD right) | 23 | 51% |
| VLD hurts (SP right, VLD wrong) | 0 | 0% |
| Both correct | 20 | 44% |
| Both wrong | 2 | 4% |
| **Total multi-hop** | **45** | |

## Case Studies: VLD Saves

*Scenarios where single-pass gets it wrong and VLD gets it right.*

### Case 1: TRD-001-v1
**Type:** hidden_thesis_reversal
**Kind:** score_keyed | **rho:** 0.7

**Description:** Aster Sensorworks (industrial automation). A favorable buy signal references an outdated sector thesis; look-through sizing, current issuer financials and exit capacity complete the review.

#### WITHOUT VLD (single-pass)
- Action: **defer** ❌ (ground truth: reject)
- Based on surface factors only
- Distance to nearest centroid: 0.7036

#### WITH VLD (investigation)
- **Hop 1:** The governing synthetic record changes thesis_alignment from 0.93 to 0.01; the score is an authored fixture value, not an empirically calibrated estimate.
  - Checked: thesis_registry
  - Found: Approved thesis revision R17, effective September 4, replaced the automation overweight with an underweight after a customer-capex reversal. The signal still joins to R16; R17 identifies the applicable portfolio sleeve.
  - Factor `thesis_alignment`: 0.930 → 0.010
  - Action after hop 1: **defer** → (dist: 0.9872)
- **Hop 2:** The governing synthetic record changes portfolio_concentration from 0.08 to 0.97; the score is an authored fixture value, not an empirically calibrated estimate.
  - Checked: portfolio_analytics
  - Found: The linked sleeve contains direct shares and delta-equivalent exposure through two baskets. The proposal raises automation exposure from 24% to 33% of NAV against a 25% allocation cap; the cap can be met by resizing, so this record alone does not dictate rejection.
  - Factor `portfolio_concentration`: 0.080 → 0.970
  - Action after hop 2: **execute** → (dist: 0.9417)
- **Hop 3:** The governing synthetic record changes fundamental_strength from 0.90 to 0.08; the score is an authored fixture value, not an empirically calibrated estimate.
  - Checked: issuer_fundamental_registry
  - Found: The current public issuer-model revision incorporates cancellation of its largest customer order and an interest-coverage estimate of 0.9x. The 2025 profitability snapshot in the alert has been superseded.
  - Factor `fundamental_strength`: 0.900 → 0.080
  - Action after hop 3: **reject** ✅ (dist: 0.7823)
- **Hop 4:** The governing synthetic record changes liquidity_risk from 0.20 to 0.93; the score is an authored fixture value, not an empirically calibrated estimate.
  - Checked: liquidity_analytics
  - Found: The proposed 18,000-share lot and current 15,000-share daily volume permit only 1,500 shares per day at the mandate's 10% participation cap: 12 trading days to exit, exceeding the five-day horizon.
  - Factor `liquidity_risk`: 0.200 → 0.930
  - Action after hop 4: **reject** ✅ (dist: 0.2539)

- Action: **reject** ✅
- Distance to nearest centroid: 0.2539

**Why VLD changed the decision:** The six initial factors are uniquely nearest execute; their squared distance is 0.054900. Applying the 4 different-factor evidence updates makes reject the unique nearest action, with squared distance 0.607900 and runner-up gap 0.429500. Every proper subset of the designated evidence updates fails to reach that final label under this classifier. The full combination of withdrawn thesis or severe issuer weakness, exposure or common-factor risk, and poor exit feasibility makes this proposed addition unsuitable in the fixture.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| correlation_risk | 0.200 | 0.200 | +0.000 |
| fundamental_strength | 0.900 | 0.080 | -0.820 ← |
| liquidity_risk | 0.200 | 0.930 | +0.730 ← |
| portfolio_concentration | 0.080 | 0.970 | +0.890 ← |
| thesis_alignment | 0.930 | 0.010 | -0.920 ← |
| timing_signal | 0.610 | 0.610 | +0.000 |

### Case 2: TRD-002-v1
**Type:** hidden_thesis_reversal
**Kind:** score_keyed | **rho:** 0.9

**Description:** Bracken Memory Systems (memory hardware). A favorable buy signal references an outdated sector thesis; look-through sizing, current issuer financials and exit capacity complete the review.

#### WITHOUT VLD (single-pass)
- Action: **defer** ❌ (ground truth: reject)
- Based on surface factors only
- Distance to nearest centroid: 0.5836

#### WITH VLD (investigation)
- **Hop 1:** The governing synthetic record changes thesis_alignment from 0.81 to 0.02; the score is an authored fixture value, not an empirically calibrated estimate.
  - Checked: thesis_registry
  - Found: Thesis revision R24 removes the memory-cycle recovery premise after published distributor inventory revisions; the trading signal still uses R23. R24 names the portfolio exposure snapshot that governs this order.
  - Factor `thesis_alignment`: 0.810 → 0.020
  - Action after hop 1: **defer** → (dist: 0.9161)
- **Hop 2:** The governing synthetic record changes portfolio_concentration from 0.04 to 0.97; the score is an authored fixture value, not an empirically calibrated estimate.
  - Checked: portfolio_analytics
  - Found: Look-through holdings include a semiconductor basket omitted from the direct-equity screen. The order takes the common semiconductor bucket from 23% to 34% of NAV against a 25% cap; smaller sizing remains a possible remedy pending the other reads.
  - Factor `portfolio_concentration`: 0.040 → 0.970
  - Action after hop 2: **execute** → (dist: 1.0081)
- **Hop 3:** The governing synthetic record changes fundamental_strength from 0.75 to 0.01; the score is an authored fixture value, not an empirically calibrated estimate.
  - Checked: issuer_fundamental_registry
  - Found: The linked public financial update records inventory write-downs and projected negative operating cash flow for the next four quarters. The original strength score came from a prior model without those charges.
  - Factor `fundamental_strength`: 0.750 → 0.010
  - Action after hop 3: **reject** ✅ (dist: 0.9508)
- **Hop 4:** The governing synthetic record changes liquidity_risk from 0.03 to 0.94; the score is an authored fixture value, not an empirically calibrated estimate.
  - Checked: liquidity_analytics
  - Found: The 24,000-share proposal faces 20,000 shares of current daily volume. At 10% participation, disposal requires 12 trading days; the portfolio's maximum planning horizon is five days.
  - Factor `liquidity_risk`: 0.030 → 0.940
  - Action after hop 4: **reject** ✅ (dist: 0.2756)

- Action: **reject** ✅
- Distance to nearest centroid: 0.2756

**Why VLD changed the decision:** The six initial factors are uniquely nearest execute; their squared distance is 0.074300. Applying the 4 different-factor evidence updates makes reject the unique nearest action, with squared distance 0.679200 and runner-up gap 0.466500. Every proper subset of the designated evidence updates fails to reach that final label under this classifier. The full combination of withdrawn thesis or severe issuer weakness, exposure or common-factor risk, and poor exit feasibility makes this proposed addition unsuitable in the fixture.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| correlation_risk | 0.160 | 0.160 | +0.000 |
| fundamental_strength | 0.750 | 0.010 | -0.740 ← |
| liquidity_risk | 0.030 | 0.940 | +0.910 ← |
| portfolio_concentration | 0.040 | 0.970 | +0.930 ← |
| thesis_alignment | 0.810 | 0.020 | -0.790 ← |
| timing_signal | 0.610 | 0.610 | +0.000 |

### Case 3: TRD-003-v1
**Type:** hidden_thesis_reversal
**Kind:** score_keyed | **rho:** 1.0

**Description:** Cedarline Process Tools (process equipment). A favorable buy signal references an outdated sector thesis; look-through sizing, current issuer financials and exit capacity complete the review.

#### WITHOUT VLD (single-pass)
- Action: **defer** ❌ (ground truth: reject)
- Based on surface factors only
- Distance to nearest centroid: 0.5336

#### WITH VLD (investigation)
- **Hop 1:** The governing synthetic record changes thesis_alignment from 0.76 to 0.02; the score is an authored fixture value, not an empirically calibrated estimate.
  - Checked: thesis_registry
  - Found: Approved sector revision R09 replaces the backlog-growth thesis with an underweight after disclosed plant-project cancellations. The buy signal was created against R08; R09 links the relevant mandate holdings.
  - Factor `thesis_alignment`: 0.760 → 0.020
  - Action after hop 1: **defer** → (dist: 0.8881)
- **Hop 2:** The governing synthetic record changes portfolio_concentration from 0.12 to 0.97; the score is an authored fixture value, not an empirically calibrated estimate.
  - Checked: portfolio_analytics
  - Found: The holdings link adds the same equipment exposure in a managed account. After the buy, combined equipment exposure is 32% of NAV versus a 25% cap, up from 22%; resizing could repair this component.
  - Factor `portfolio_concentration`: 0.120 → 0.970
  - Action after hop 2: **execute** → (dist: 0.9293)
- **Hop 3:** The governing synthetic record changes fundamental_strength from 0.70 to 0.00; the score is an authored fixture value, not an empirically calibrated estimate.
  - Checked: issuer_fundamental_registry
  - Found: A public amendment in the linked issuer-model record shows a covenant breach and an unresolved refinancing shortfall. The prior model's unrestricted-cash assumption is no longer supported.
  - Factor `fundamental_strength`: 0.700 → 0.000
  - Action after hop 3: **reject** ✅ (dist: 0.8355)
- **Hop 4:** The governing synthetic record changes liquidity_risk from 0.16 to 0.89; the score is an authored fixture value, not an empirically calibrated estimate.
  - Checked: liquidity_analytics
  - Found: The proposed 30,000 shares exceed the executable exit envelope: 25,000 shares of daily volume at a 10% participation limit supports 2,500 shares per day, requiring 12 trading days rather than five.
  - Factor `liquidity_risk`: 0.160 → 0.890
  - Action after hop 4: **reject** ✅ (dist: 0.3035)

- Action: **reject** ✅
- Distance to nearest centroid: 0.3035

**Why VLD changed the decision:** The six initial factors are uniquely nearest execute; their squared distance is 0.072000. Applying the 4 different-factor evidence updates makes reject the unique nearest action, with squared distance 0.702800 and runner-up gap 0.433000. Every proper subset of the designated evidence updates fails to reach that final label under this classifier. The full combination of withdrawn thesis or severe issuer weakness, exposure or common-factor risk, and poor exit feasibility makes this proposed addition unsuitable in the fixture.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| correlation_risk | 0.130 | 0.130 | +0.000 |
| fundamental_strength | 0.700 | 0.000 | -0.700 ← |
| liquidity_risk | 0.160 | 0.890 | +0.730 ← |
| portfolio_concentration | 0.120 | 0.970 | +0.850 ← |
| thesis_alignment | 0.760 | 0.020 | -0.740 ← |
| timing_signal | 0.600 | 0.600 | +0.000 |

### Case 4: TRD-004-v1
**Type:** hidden_thesis_reversal
**Kind:** score_keyed | **rho:** 0.9

**Description:** Dovetail Optics (optical components). A favorable buy signal references an outdated sector thesis; look-through sizing, current issuer financials and exit capacity complete the review.

#### WITHOUT VLD (single-pass)
- Action: **defer** ❌ (ground truth: reject)
- Based on surface factors only
- Distance to nearest centroid: 0.7201

#### WITH VLD (investigation)
- **Hop 1:** The governing synthetic record changes thesis_alignment from 0.96 to 0.02; the score is an authored fixture value, not an empirically calibrated estimate.
  - Checked: thesis_registry
  - Found: Sector revision R31 withdraws the hyperscale-buildout thesis after a disclosed procurement cut; the signal retains R30. The approved revision specifies the affected portfolio and exposure date.
  - Factor `thesis_alignment`: 0.960 → 0.020
  - Action after hop 1: **defer** → (dist: 0.9853)
- **Hop 2:** The governing synthetic record changes portfolio_concentration from 0.09 to 0.95; the score is an authored fixture value, not an empirically calibrated estimate.
  - Checked: portfolio_analytics
  - Found: The linked portfolio includes optical-component exposure through structured notes. The new lot moves sector exposure from 24% to 36% of NAV against a 25% cap; the sizing breach is repairable in isolation.
  - Factor `portfolio_concentration`: 0.090 → 0.950
  - Action after hop 2: **execute** → (dist: 0.9366)
- **Hop 3:** The governing synthetic record changes fundamental_strength from 0.91 to 0.01; the score is an authored fixture value, not an empirically calibrated estimate.
  - Checked: issuer_fundamental_registry
  - Found: The current public issuer update removes two major programs from backlog and reduces unrestricted liquidity below twelve months of modeled cash burn. A superseded annual report supplied the favorable surface score.
  - Factor `fundamental_strength`: 0.910 → 0.010
  - Action after hop 3: **reject** ✅ (dist: 0.7758)
- **Hop 4:** The governing synthetic record changes liquidity_risk from 0.20 to 0.92; the score is an authored fixture value, not an empirically calibrated estimate.
  - Checked: liquidity_analytics
  - Found: For the proposed 36,000 shares, 30,000-share daily volume and a 10% participation cap imply 3,000 executable shares per day and a 12-trading-day exit. The required liquidation horizon is five days.
  - Factor `liquidity_risk`: 0.200 → 0.920
  - Action after hop 4: **reject** ✅ (dist: 0.2338)

- Action: **reject** ✅
- Distance to nearest centroid: 0.2338

**Why VLD changed the decision:** The six initial factors are uniquely nearest execute; their squared distance is 0.060400. Applying the 4 different-factor evidence updates makes reject the unique nearest action, with squared distance 0.618000 and runner-up gap 0.450500. Every proper subset of the designated evidence updates fails to reach that final label under this classifier. The full combination of withdrawn thesis or severe issuer weakness, exposure or common-factor risk, and poor exit feasibility makes this proposed addition unsuitable in the fixture.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| correlation_risk | 0.200 | 0.200 | +0.000 |
| fundamental_strength | 0.910 | 0.010 | -0.900 ← |
| liquidity_risk | 0.200 | 0.920 | +0.720 ← |
| portfolio_concentration | 0.090 | 0.950 | +0.860 ← |
| thesis_alignment | 0.960 | 0.020 | -0.940 ← |
| timing_signal | 0.610 | 0.610 | +0.000 |

### Case 5: TRD-005-v1
**Type:** hidden_thesis_reversal
**Kind:** score_keyed | **rho:** 0.7

**Description:** Emberbridge Instruments (test equipment). A favorable buy signal references an outdated sector thesis; look-through sizing, current issuer financials and exit capacity complete the review.

#### WITHOUT VLD (single-pass)
- Action: **defer** ❌ (ground truth: reject)
- Based on surface factors only
- Distance to nearest centroid: 0.6551

#### WITH VLD (investigation)
- **Hop 1:** The governing synthetic record changes thesis_alignment from 0.71 to 0.05; the score is an authored fixture value, not an empirically calibrated estimate.
  - Checked: thesis_registry
  - Found: Revision R12 formally ends the test-equipment expansion thesis after customer spending deferrals; the order still points to R11. R12 carries the governing portfolio-sleeve identifier.
  - Factor `thesis_alignment`: 0.710 → 0.050
  - Action after hop 1: **defer** → (dist: 0.9445)
- **Hop 2:** The governing synthetic record changes portfolio_concentration from 0.01 to 0.97; the score is an authored fixture value, not an empirically calibrated estimate.
  - Checked: portfolio_analytics
  - Found: The sleeve identifier reveals overlapping holdings in a small-cap equipment fund. The buy increases total equipment exposure from 21% to 31% of NAV, above its 25% cap; position reduction alone remains possible until the other evidence is read.
  - Factor `portfolio_concentration`: 0.010 → 0.970
  - Action after hop 2: **execute** → (dist: 0.9347)
- **Hop 3:** The governing synthetic record changes fundamental_strength from 0.87 to 0.02; the score is an authored fixture value, not an empirically calibrated estimate.
  - Checked: issuer_fundamental_registry
  - Found: The issuer's public updated forecast removes a critical license stream and shows negative free cash flow with no committed replacement financing. The alert reused the pre-update financial model.
  - Factor `fundamental_strength`: 0.870 → 0.020
  - Action after hop 3: **reject** ✅ (dist: 0.8629)
- **Hop 4:** The governing synthetic record changes liquidity_risk from 0.10 to 0.94; the score is an authored fixture value, not an empirically calibrated estimate.
  - Checked: liquidity_analytics
  - Found: The 42,000-share proposal meets only 35,000 shares of daily volume. With a 10% participation cap, the 3,500-share daily exit capacity requires 12 trading days, beyond the five-day mandate horizon.
  - Factor `liquidity_risk`: 0.100 → 0.940
  - Action after hop 4: **reject** ✅ (dist: 0.1977)

- Action: **reject** ✅
- Distance to nearest centroid: 0.1977

**Why VLD changed the decision:** The six initial factors are uniquely nearest execute; their squared distance is 0.100700. Applying the 4 different-factor evidence updates makes reject the unique nearest action, with squared distance 0.509000 and runner-up gap 0.456500. Every proper subset of the designated evidence updates fails to reach that final label under this classifier. The full combination of withdrawn thesis or severe issuer weakness, exposure or common-factor risk, and poor exit feasibility makes this proposed addition unsuitable in the fixture.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| correlation_risk | 0.300 | 0.300 | +0.000 |
| fundamental_strength | 0.870 | 0.020 | -0.850 ← |
| liquidity_risk | 0.100 | 0.940 | +0.840 ← |
| portfolio_concentration | 0.010 | 0.970 | +0.960 ← |
| thesis_alignment | 0.710 | 0.050 | -0.660 ← |
| timing_signal | 0.610 | 0.610 | +0.000 |

### Case 6: TRD-006-v1
**Type:** masked_correlated_positions
**Kind:** score_keyed | **rho:** 0.7

**Description:** Fallowgrid Power (regulated utilities). A low-correlation signal omits a common factor shared by three existing positions and its joint exit constraint.

#### WITHOUT VLD (single-pass)
- Action: **defer** ❌ (ground truth: hedge)
- Based on surface factors only
- Distance to nearest centroid: 0.7099

#### WITH VLD (investigation)
- **Hop 1:** The governing synthetic record changes correlation_risk from 0.15 to 0.99; the score is an authored fixture value, not an empirically calibrated estimate.
  - Checked: correlation_analytics
  - Found: Look-through factor map C14 links existing positions SYN-FP1, SYN-FP2 and SYN-FP3 to the same long-duration utility factor. In the planted stress window, correlations to the proposed stock are 0.82, 0.86 and 0.88; the ordinary-window screen omitted this common factor.
  - Factor `correlation_risk`: 0.150 → 0.990
  - Action after hop 1: **hedge** ✅ (dist: 0.5714)
- **Hop 2:** The governing synthetic record changes liquidity_risk from 0.17 to 0.82; the score is an authored fixture value, not an empirically calibrated estimate.
  - Checked: liquidity_analytics
  - Found: The linked common-factor liquidity profile assumes a simultaneous unwind of the four-name sleeve and quotes 160 basis points of slippage for the target lot. Its approved index-futures hedge has separately verified capacity and costs 12 basis points; the policy retains the alpha position with this hedge.
  - Factor `liquidity_risk`: 0.170 → 0.820
  - Action after hop 2: **hedge** ✅ (dist: 0.3657)

- Action: **hedge** ✅
- Distance to nearest centroid: 0.3657

**Why VLD changed the decision:** The six initial factors are uniquely nearest execute; their squared distance is 0.059300. Applying the 2 different-factor evidence updates makes hedge the unique nearest action, with squared distance 0.701900 and runner-up gap 0.205500. Every proper subset of the designated evidence updates fails to reach that final label under this classifier. The fixture retains the position while using the approved feasible instrument identified in the evidence to mitigate the shared factor.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| correlation_risk | 0.150 | 0.990 | +0.840 ← |
| fundamental_strength | 0.710 | 0.710 | +0.000 |
| liquidity_risk | 0.170 | 0.820 | +0.650 ← |
| portfolio_concentration | 0.010 | 0.010 | +0.000 |
| thesis_alignment | 0.710 | 0.710 | +0.000 |
| timing_signal | 0.810 | 0.810 | +0.000 |

### Case 7: TRD-008-v1
**Type:** masked_correlated_positions
**Kind:** score_keyed | **rho:** 1.0

**Description:** Harborcoil Components (electrical components). A low-correlation signal omits a common factor shared by three existing positions and its joint exit constraint.

#### WITHOUT VLD (single-pass)
- Action: **defer** ❌ (ground truth: hedge)
- Based on surface factors only
- Distance to nearest centroid: 0.6150

#### WITH VLD (investigation)
- **Hop 1:** The governing synthetic record changes correlation_risk from 0.00 to 0.99; the score is an authored fixture value, not an empirically calibrated estimate.
  - Checked: correlation_analytics
  - Found: Cluster C07 identifies SYN-HC1, SYN-HC2 and SYN-HC3 as indirect holdings in one electrification theme. Planted stress-window correlations of 0.85, 0.87 and 0.90 replace the sparse pairwise surface estimate.
  - Factor `correlation_risk`: 0.000 → 0.990
  - Action after hop 1: **hedge** ✅ (dist: 0.6307)
- **Hop 2:** The governing synthetic record changes liquidity_risk from 0.03 to 0.82; the score is an authored fixture value, not an empirically calibrated estimate.
  - Checked: liquidity_analytics
  - Found: The cluster's unwind profile shows 175 basis points of expected slippage in a coordinated exit. A preapproved sector-index future has adequate capacity and 15-basis-point modeled implementation cost, allowing the mandate to hedge the common factor while retaining the stock selection.
  - Factor `liquidity_risk`: 0.030 → 0.820
  - Action after hop 2: **hedge** ✅ (dist: 0.2299)

- Action: **hedge** ✅
- Distance to nearest centroid: 0.2299

**Why VLD changed the decision:** The six initial factors are uniquely nearest execute; their squared distance is 0.113400. Applying the 2 different-factor evidence updates makes hedge the unique nearest action, with squared distance 0.621500 and runner-up gap 0.209500. Every proper subset of the designated evidence updates fails to reach that final label under this classifier. The fixture retains the position while using the approved feasible instrument identified in the evidence to mitigate the shared factor.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| correlation_risk | 0.000 | 0.990 | +0.990 ← |
| fundamental_strength | 0.730 | 0.730 | +0.000 |
| liquidity_risk | 0.030 | 0.820 | +0.790 ← |
| portfolio_concentration | 0.010 | 0.010 | +0.000 |
| thesis_alignment | 0.770 | 0.770 | +0.000 |
| timing_signal | 0.610 | 0.610 | +0.000 |

### Case 8: TRD-010-v1
**Type:** masked_correlated_positions
**Kind:** score_keyed | **rho:** 0.7

**Description:** Juniperwave Telecom (telecom infrastructure). A low-correlation signal omits a common factor shared by three existing positions and its joint exit constraint.

#### WITHOUT VLD (single-pass)
- Action: **defer** ❌ (ground truth: hedge)
- Based on surface factors only
- Distance to nearest centroid: 0.6088

#### WITH VLD (investigation)
- **Hop 1:** The governing synthetic record changes correlation_risk from 0.15 to 0.98; the score is an authored fixture value, not an empirically calibrated estimate.
  - Checked: correlation_analytics
  - Found: Cluster C33 reveals SYN-JT1, SYN-JT2 and SYN-JT3 as exposures to a common telecom-capex factor. Planted stress-window correlations of 0.83, 0.86 and 0.89 were absent from the ordinary-window screening matrix.
  - Factor `correlation_risk`: 0.150 → 0.980
  - Action after hop 1: **hedge** ✅ (dist: 0.5799)
- **Hop 2:** The governing synthetic record changes liquidity_risk from 0.10 to 0.83; the score is an authored fixture value, not an empirically calibrated estimate.
  - Checked: liquidity_analytics
  - Found: The linked crowded-exit profile quotes 155 basis points of slippage for a coordinated cash liquidation. A permitted liquid sector basket is available at 14-basis-point modeled cost and within collateral limits, supporting a hedge of the shared factor.
  - Factor `liquidity_risk`: 0.100 → 0.830
  - Action after hop 2: **hedge** ✅ (dist: 0.2755)

- Action: **hedge** ✅
- Distance to nearest centroid: 0.2755

**Why VLD changed the decision:** The six initial factors are uniquely nearest execute; their squared distance is 0.056700. Applying the 2 different-factor evidence updates makes hedge the unique nearest action, with squared distance 0.626000 and runner-up gap 0.201500. Every proper subset of the designated evidence updates fails to reach that final label under this classifier. The fixture retains the position while using the approved feasible instrument identified in the evidence to mitigate the shared factor.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| correlation_risk | 0.150 | 0.980 | +0.830 ← |
| fundamental_strength | 0.710 | 0.710 | +0.000 |
| liquidity_risk | 0.100 | 0.830 | +0.730 ← |
| portfolio_concentration | 0.030 | 0.030 | +0.000 |
| thesis_alignment | 0.760 | 0.760 | +0.000 |
| timing_signal | 0.690 | 0.690 | +0.000 |
