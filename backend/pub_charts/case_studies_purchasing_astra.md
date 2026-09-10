# VLD With-Without Case Studies — PURCHASING_ASTRA
**Generated from Stage 1 multi-hop scenarios**
**[PLANTED POSITIVE CONTROL — not production data]**

## Summary

| Category | Count | % |
|---|---|---|
| VLD saves (SP wrong, VLD right) | 28 | 62% |
| VLD hurts (SP right, VLD wrong) | 0 | 0% |
| Both correct | 17 | 38% |
| Both wrong | 0 | 0% |
| **Total multi-hop** | **45** | |

## Case Studies: VLD Saves

*Scenarios where single-pass gets it wrong and VLD gets it right.*

### Case 1: PUR-001-v1
**Type:** hidden_seasonal_spike
**Kind:** score_keyed | **rho:** 0.7

**Description:** A routine chocolate reorder misses a store-specific holiday reservation cohort.

#### WITHOUT VLD (single-pass)
- Action: **order_reduced** ❌ (ground truth: order_increased)
- Based on surface factors only
- Distance to nearest centroid: 0.3910

#### WITH VLD (investigation)
- **Hop 1:** Resolve the alert-specific demand_forecast record and obtain its scope key before selecting a continuation.
  - Checked: demand_planning_system
  - Found: The store calendar links this SKU to the fictional EV-HARBOR-VAL campaign in five days. Its approved plan calls for 240 boxes versus the normal 80. It returns reservation-cohort key EV-HARBOR-VAL; the plan alone does not prove paid demand.
  - Factor `demand_forecast`: 0.360 → 0.920
  - Action after hop 1: **order_increased** ✅ (dist: 0.4814)
- **Hop 2:** Use the returned scope key to read the matching consumption_rate record; combine it with the first finding.
  - Checked: cohort_consumption_ledger
  - Found: For cohort EV-HARBOR-VAL, paid pickup reservations net of refunds total 216 boxes and recent attributable sales are 2.6 times baseline. The numbers exclude the normal 80-box replenishment forecast; existing stock is 64 boxes and the supplier can deliver within three days.
  - Factor `consumption_rate`: 0.420 → 0.900
  - Action after hop 2: **order_increased** ✅ (dist: 0.0105)

- Action: **order_increased** ✅
- Distance to nearest centroid: 0.0105

**Why VLD changed the decision:** The surface proxy selects order_standard. The calendar identifies the future requirement and the matching paid cohort confirms incremental consumption; a standard 80-box order is inadequate. The complete two-read update selects order_increased; neither singleton factor update selects it. The normal three-day route arrives before the five-day pickup window. Increase that route quantity; expedited delivery adds no service benefit.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| consumption_rate | 0.420 | 0.900 | +0.480 ← |
| cost_efficiency | 0.710 | 0.710 | +0.000 |
| demand_forecast | 0.360 | 0.920 | +0.560 ← |
| quality_score | 0.850 | 0.850 | +0.000 |
| shelf_life | 0.590 | 0.590 | +0.000 |
| supplier_reliability | 0.850 | 0.850 | +0.000 |

### Case 2: PUR-002-v1
**Type:** hidden_seasonal_spike
**Kind:** score_keyed | **rho:** 0.9

**Description:** A weekend kiosk forecast omits a permitted waterfront event and its distinct voucher cohort.

#### WITHOUT VLD (single-pass)
- Action: **order_reduced** ❌ (ground truth: order_increased)
- Based on surface factors only
- Distance to nearest centroid: 0.3843

#### WITH VLD (investigation)
- **Hop 1:** Resolve the alert-specific demand_forecast record and obtain its scope key before selecting a continuation.
  - Checked: demand_planning_system
  - Found: The internal event calendar assigns this kiosk the EV-CANAL-ART service concession four days ahead, with a 1,800-drink capacity allocation versus the routine 600. The allocation returns the vendor voucher cohort, but attendance is still an assumption.
  - Factor `demand_forecast`: 0.340 → 0.920
  - Action after hop 1: **order_increased** ✅ (dist: 0.4913)
- **Hop 2:** Use the returned scope key to read the matching consumption_rate record; combine it with the first finding.
  - Checked: cohort_consumption_ledger
  - Found: Redeemed advance vouchers plus prepaid group drinks for EV-CANAL-ART amount to 1,420 cups after removing duplicates; the same cohort is consuming at 2.4 times baseline. Current cups cover 360 drinks and the usual route arrives in two days.
  - Factor `consumption_rate`: 0.410 → 0.910
  - Action after hop 2: **order_increased** ✅ (dist: 0.0127)

- Action: **order_increased** ✅
- Distance to nearest centroid: 0.0127

**Why VLD changed the decision:** The surface proxy selects order_standard. Concession assignment plus confirmed voucher consumption establishes a larger regular-route requirement. The complete two-read update selects order_increased; neither singleton factor update selects it. Cups are durable and storage space is available. The two-day regular route meets the event deadline.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| consumption_rate | 0.410 | 0.910 | +0.500 ← |
| cost_efficiency | 0.700 | 0.700 | +0.000 |
| demand_forecast | 0.340 | 0.920 | +0.580 ← |
| quality_score | 0.860 | 0.860 | +0.000 |
| shelf_life | 0.600 | 0.600 | +0.000 |
| supplier_reliability | 0.850 | 0.850 | +0.000 |

### Case 3: PUR-003-v1
**Type:** hidden_seasonal_spike
**Kind:** score_keyed | **rho:** 1

**Description:** A normal carton signal excludes prepaid orders associated with a local tournament.

#### WITHOUT VLD (single-pass)
- Action: **order_reduced** ❌ (ground truth: order_increased)
- Based on surface factors only
- Distance to nearest centroid: 0.3874

#### WITH VLD (investigation)
- **Hop 1:** Resolve the alert-specific demand_forecast record and obtain its scope key before selecting a continuation.
  - Checked: demand_planning_system
  - Found: The store demand calendar has an approved EV-NORTH-CUP team-meal event in six days, allocating 310 family pizzas against a usual 100. It returns the team-order cohort for the family-size carton SKU.
  - Factor `demand_forecast`: 0.340 → 0.920
  - Action after hop 1: **order_increased** ✅ (dist: 0.4915)
- **Hop 2:** Use the returned scope key to read the matching consumption_rate record; combine it with the first finding.
  - Checked: cohort_consumption_ledger
  - Found: The EV-NORTH-CUP dispatch ledger contains 284 paid family pizzas, with team-account drawdown at 2.8 times baseline after removing standard-size orders. On hand is 90 matching cartons; the established supplier confirms a three-day regular delivery.
  - Factor `consumption_rate`: 0.410 → 0.900
  - Action after hop 2: **order_increased** ✅ (dist: 0.0154)

- Action: **order_increased** ✅
- Distance to nearest centroid: 0.0154

**Why VLD changed the decision:** The surface proxy selects order_standard. The item-specific event and size-filtered paid meal cohort jointly justify increased cartons. The complete two-read update selects order_increased; neither singleton factor update selects it. Only family-size carton demand is in scope. Storage and normal-route capacity can accommodate the increased quantity.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| consumption_rate | 0.410 | 0.900 | +0.490 ← |
| cost_efficiency | 0.710 | 0.710 | +0.000 |
| demand_forecast | 0.340 | 0.920 | +0.580 ← |
| quality_score | 0.860 | 0.860 | +0.000 |
| shelf_life | 0.590 | 0.590 | +0.000 |
| supplier_reliability | 0.860 | 0.860 | +0.000 |

### Case 4: PUR-004-v1
**Type:** hidden_seasonal_spike
**Kind:** score_keyed | **rho:** 0.9

**Description:** Routine breakfast replenishment misses a prebooked campus orientation wave.

#### WITHOUT VLD (single-pass)
- Action: **order_reduced** ❌ (ground truth: order_increased)
- Based on surface factors only
- Distance to nearest centroid: 0.3842

#### WITH VLD (investigation)
- **Hop 1:** Resolve the alert-specific demand_forecast record and obtain its scope key before selecting a continuation.
  - Checked: demand_planning_system
  - Found: The campus store calendar assigns 1,100 orientation breakfast packs to EV-EAST-ORIENT in five days, compared with a 400-bar normal cycle. The approved pack mapping returns a meal-plan cohort key, pending confirmation of activated plans.
  - Factor `demand_forecast`: 0.350 → 0.920
  - Action after hop 1: **order_increased** ✅ (dist: 0.4814)
- **Hop 2:** Use the returned scope key to read the matching consumption_rate record; combine it with the first finding.
  - Checked: cohort_consumption_ledger
  - Found: Activated prepaid meal plans for EV-EAST-ORIENT require 980 bars; early cohort redemptions run at 2.5 times baseline. Refunds and inactive plans have been removed. There are 270 bars on hand and the normal supplier route takes two days.
  - Factor `consumption_rate`: 0.420 → 0.900
  - Action after hop 2: **order_increased** ✅ (dist: 0.0127)

- Action: **order_increased** ✅
- Distance to nearest centroid: 0.0127

**Why VLD changed the decision:** The surface proxy selects order_standard. Orientation pack mapping and activated-plan consumption expose incremental demand that retail-only averages hide. The complete two-read update selects order_increased; neither singleton factor update selects it. The supplied bar lot has adequate shelf life for the orientation window; a regular route can carry the larger order.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| consumption_rate | 0.420 | 0.900 | +0.480 ← |
| cost_efficiency | 0.710 | 0.710 | +0.000 |
| demand_forecast | 0.350 | 0.920 | +0.570 ← |
| quality_score | 0.860 | 0.860 | +0.000 |
| shelf_life | 0.600 | 0.600 | +0.000 |
| supplier_reliability | 0.850 | 0.850 | +0.000 |

### Case 5: PUR-005-v1
**Type:** hidden_seasonal_spike
**Kind:** score_keyed | **rho:** 0.7

**Description:** A stable gift-shop signal misses a scheduled employer-gifting campaign.

#### WITHOUT VLD (single-pass)
- Action: **order_reduced** ❌ (ground truth: order_increased)
- Based on surface factors only
- Distance to nearest centroid: 0.3960

#### WITH VLD (investigation)
- **Hop 1:** Resolve the alert-specific demand_forecast record and obtain its scope key before selecting a continuation.
  - Checked: demand_planning_system
  - Found: The internal gifting calendar associates the tin SKU with EV-LINDEN-GIFT in seven days and a 460-tin provisional employer allocation versus a routine 150. It exposes the purchase-allocation cohort key.
  - Factor `demand_forecast`: 0.350 → 0.920
  - Action after hop 1: **order_increased** ✅ (dist: 0.4714)
- **Hop 2:** Use the returned scope key to read the matching consumption_rate record; combine it with the first finding.
  - Checked: cohort_consumption_ledger
  - Found: Signed, nonduplicated employer allocations under EV-LINDEN-GIFT now require 412 tins; committed consumption runs at 2.7 times baseline. There are 130 tins on hand; the normal four-day route can supply the increase.
  - Factor `consumption_rate`: 0.430 → 0.900
  - Action after hop 2: **order_increased** ✅ (dist: 0.0136)

- Action: **order_increased** ✅
- Distance to nearest centroid: 0.0136

**Why VLD changed the decision:** The surface proxy selects order_standard. The private campaign mapping and signed allocations together require more than the normal order. The complete two-read update selects order_increased; neither singleton factor update selects it. The seven-day obligation is reachable by the ordinary four-day supplier route and shelf life is ample.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| consumption_rate | 0.430 | 0.900 | +0.470 ← |
| cost_efficiency | 0.700 | 0.700 | +0.000 |
| demand_forecast | 0.350 | 0.920 | +0.570 ← |
| quality_score | 0.840 | 0.840 | +0.000 |
| shelf_life | 0.590 | 0.590 | +0.000 |
| supplier_reliability | 0.850 | 0.850 | +0.000 |

### Case 6: PUR-006-v1
**Type:** reliable_supplier_bad_batch
**Kind:** score_keyed | **rho:** 0.9

**Description:** A strong supplier average hides an unusable allocation for the next yogurt shipment.

#### WITHOUT VLD (single-pass)
- Action: **order_reduced** ❌ (ground truth: switch_supplier)
- Based on surface factors only
- Distance to nearest centroid: 0.3953

#### WITH VLD (investigation)
- **Hop 1:** Resolve the alert-specific supplier_reliability record and obtain its scope key before selecting a continuation.
  - Checked: supplier_allocation_portal
  - Found: The next-allocation record shows only 18 of the 72 ordered cases can be released for this store; the blocked 54 are tied to LOT-DM-412. This revises usable on-time/in-full reliability for the imminent order, but the release reason is stored separately.
  - Factor `supplier_reliability`: 0.850 → 0.210
  - Action after hop 1: **defer_order** → (dist: 0.5684)
- **Hop 2:** Use the returned scope key to read the matching quality_score record; combine it with the first finding.
  - Checked: batch_quality_registry
  - Found: The signed quality report for LOT-DM-412 records failed package-integrity checks and a release prohibition. The lot is already segregated. The approved alternative offers the exact portion size on the same two-day route, before existing stock is exhausted.
  - Factor `quality_score`: 0.850 → 0.250
  - Action after hop 2: **switch_supplier** ✅ (dist: 0.1841)

- Action: **switch_supplier** ✅
- Distance to nearest centroid: 0.1841

**Why VLD changed the decision:** The surface proxy selects order_standard. The allocation identifies a near-term fulfilment failure, and the matching report establishes that an ordinary release delay cannot recover this batch. The complete two-read update selects switch_supplier; neither singleton factor update selects it. The recommendation concerns the uncommitted next purchase. Existing usable stock lasts three days; an approved alternative arrives in two.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| consumption_rate | 0.410 | 0.410 | +0.000 |
| cost_efficiency | 0.690 | 0.690 | +0.000 |
| demand_forecast | 0.400 | 0.400 | +0.000 |
| quality_score | 0.850 | 0.250 | -0.600 ← |
| shelf_life | 0.610 | 0.610 | +0.000 |
| supplier_reliability | 0.850 | 0.210 | -0.640 ← |

### Case 7: PUR-007-v1
**Type:** reliable_supplier_bad_batch
**Kind:** score_keyed | **rho:** 1

**Description:** An apparently dependable coffee route draws from a lot under a sensory quality hold.

#### WITHOUT VLD (single-pass)
- Action: **order_reduced** ❌ (ground truth: switch_supplier)
- Based on surface factors only
- Distance to nearest centroid: 0.3933

#### WITH VLD (investigation)
- **Hop 1:** Resolve the alert-specific supplier_reliability record and obtain its scope key before selecting a continuation.
  - Checked: supplier_allocation_portal
  - Found: The store shipment allocation for LOT-HRC-088 has 46 of 60 bags unavailable for release at the next cutoff. Past punctuality includes all origins and does not measure usable bags from this allocation. The record returns the lot-specific quality key.
  - Factor `supplier_reliability`: 0.850 → 0.190
  - Action after hop 1: **defer_order** → (dist: 0.5843)
- **Hop 2:** Use the returned scope key to read the matching quality_score record; combine it with the first finding.
  - Checked: batch_quality_registry
  - Found: The LOT-HRC-088 panel report confirms pervasive taint outside the fictional shop acceptance specification; the held bags cannot fill the order. An already-approved matching roast from a second supplier can arrive tomorrow, with three days of usable beans remaining.
  - Factor `quality_score`: 0.840 → 0.250
  - Action after hop 2: **switch_supplier** ✅ (dist: 0.2009)

- Action: **switch_supplier** ✅
- Distance to nearest centroid: 0.2009

**Why VLD changed the decision:** The surface proxy selects order_standard. Allocation-specific nonfulfilment combined with confirmed lot-level rejection supports switching the next purchase. The complete two-read update selects switch_supplier; neither singleton factor update selects it. The alternative roast is already approved for this menu and the usual alternative route beats stock depletion.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| consumption_rate | 0.410 | 0.410 | +0.000 |
| cost_efficiency | 0.690 | 0.690 | +0.000 |
| demand_forecast | 0.400 | 0.400 | +0.000 |
| quality_score | 0.840 | 0.250 | -0.590 ← |
| shelf_life | 0.610 | 0.610 | +0.000 |
| supplier_reliability | 0.850 | 0.190 | -0.660 ← |

### Case 8: PUR-008-v1
**Type:** reliable_supplier_bad_batch
**Kind:** score_keyed | **rho:** 0.7

**Description:** A reliable dry-goods supplier has allocated most lentils from a held sack cohort.

#### WITHOUT VLD (single-pass)
- Action: **order_reduced** ❌ (ground truth: switch_supplier)
- Based on surface factors only
- Distance to nearest centroid: 0.3859

#### WITH VLD (investigation)
- **Hop 1:** Resolve the alert-specific supplier_reliability record and obtain its scope key before selecting a continuation.
  - Checked: supplier_allocation_portal
  - Found: The next-order reservation points to LOT-VPS-207, for which only 4 of 22 sacks are currently releasable. The remaining inventory cannot count as on-time/in-full supply until its linked inspection disposition is read.
  - Factor `supplier_reliability`: 0.860 → 0.210
  - Action after hop 1: **defer_order** → (dist: 0.5621)
- **Hop 2:** Use the returned scope key to read the matching quality_score record; combine it with the first finding.
  - Checked: batch_quality_registry
  - Found: The linked LOT-VPS-207 inspection records wet packaging and repeated seal damage across the reserved pallet; that pallet is excluded from purchase fulfilment. A contracted second supplier has intact sacks of the same grade on a two-day route; the site has four days of usable stock.
  - Factor `quality_score`: 0.850 → 0.250
  - Action after hop 2: **switch_supplier** ✅ (dist: 0.1743)

- Action: **switch_supplier** ✅
- Distance to nearest centroid: 0.1743

**Why VLD changed the decision:** The surface proxy selects order_standard. A release shortfall bound to confirmed rejected packaging makes the current allocation unsuitable. The complete two-read update selects switch_supplier; neither singleton factor update selects it. Switching uses the existing approved supplier panel and fits the normal replenishment deadline.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| consumption_rate | 0.400 | 0.400 | +0.000 |
| cost_efficiency | 0.710 | 0.710 | +0.000 |
| demand_forecast | 0.410 | 0.410 | +0.000 |
| quality_score | 0.850 | 0.250 | -0.600 ← |
| shelf_life | 0.610 | 0.610 | +0.000 |
| supplier_reliability | 0.860 | 0.210 | -0.650 ← |
