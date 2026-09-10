# VLD With-Without Case Studies — DATAOPS_ASTRA
**Generated from Stage 1 multi-hop scenarios**
**[PLANTED POSITIVE CONTROL — not production data]**

## Summary

| Category | Count | % |
|---|---|---|
| VLD saves (SP wrong, VLD right) | 38 | 84% |
| VLD hurts (SP right, VLD wrong) | 0 | 0% |
| Both correct | 4 | 9% |
| Both wrong | 3 | 7% |
| **Total multi-hop** | **45** | |

## Case Studies: VLD Saves

*Scenarios where single-pass gets it wrong and VLD gets it right.*

### Case 1: DO-001-v1
**Type:** hidden_cascade
**Kind:** score_keyed | **rho:** 0.7

**Description:** ERP material classification cascade: the cached alert suggests auto_fix; partition-scoped evidence supports escalate_to_owner.

#### WITHOUT VLD (single-pass)
- Action: **auto_fix** ❌ (ground truth: escalate_to_owner)
- Based on surface factors only
- Distance to nearest centroid: 0.2859

#### WITH VLD (investigation)
- **Hop 1:** The current partition record corrects the cached schema_stability estimate from 0.83 to 0.15.
  - Checked: schema_registry
  - Found: Synthetic record do-001_rec_362: Active producer/consumer contract: material_group string codes replaced by versioned category objects. The cached surface schema summary refers to the prior contract. The planted fixture maps this record to schema_stability=0.15; this value is not a calibrated or measured customer metric.
  - Factor `schema_stability`: 0.830 → 0.150
  - Action after hop 1: **rollback** → (dist: 0.5578)
- **Hop 2:** The current partition record corrects the cached impact_scope estimate from 0.29 to 0.82.
  - Checked: dependency_graph
  - Found: Synthetic record do-001_rec_607: The partition-scoped dependency inventory enumerates 6 affected consumer systems: invoice_enrichment, billing_tax, inventory_valuation, purchase_matching, margin_reporting, cost_allocation. All have current dependency records for this data version. The planted fixture maps this record to impact_scope=0.82; this value is not a calibrated or measured customer metric.
  - Factor `impact_scope`: 0.290 → 0.820
  - Action after hop 2: **escalate_to_owner** ✅ (dist: 0.8027)
- **Hop 3:** The current partition record corrects the cached pattern_familiarity estimate from 0.89 to 0.15.
  - Checked: pattern_database
  - Found: Synthetic record do-001_rec_728: Exact comparison criterion: same pipeline, active schema version, transform artifact, error fingerprint, and partition mode. Earlier missing-code incidents used the scalar category contract. The root-cause signature therefore differs from the apparently familiar historical case. The planted fixture maps this record to pattern_familiarity=0.15; this value is not a calibrated or measured customer metric. Action-context records retained before the alert: Current ownership record assigns the affected producer and downstream services to ERP schema and billing platform owners. The investigation concerns a live multi-owner contract or transformation dependency; the generic local retry cannot restore downstream consistency. No single locally authorized rollback covers all active consumer contracts. Coordinate containment and remediation through the owners; escalation does not mean passively waiting.
  - Factor `pattern_familiarity`: 0.890 → 0.150
  - Action after hop 3: **escalate_to_owner** ✅ (dist: 0.4431)

- Action: **escalate_to_owner** ✅
- Distance to nearest centroid: 0.4431

**Why VLD changed the decision:** The explicitly defined synthetic centroid scorer selects auto_fix from the surface factors and escalate_to_owner after all 3 relevant reads. The old category extractor drops the new version discriminator. Current ownership record assigns the affected producer and downstream services to ERP schema and billing platform owners. The investigation concerns a live multi-owner contract or transformation dependency; the generic local retry cannot restore downstream consistency. No single locally authorized rollback covers all active consumer contracts. Coordinate containment and remediation through the owners; escalation does not mean passively waiting.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| data_quality | 0.550 | 0.550 | +0.000 |
| impact_scope | 0.290 | 0.820 | +0.530 ← |
| pattern_familiarity | 0.890 | 0.150 | -0.740 ← |
| schema_stability | 0.830 | 0.150 | -0.680 ← |
| source_reliability | 0.720 | 0.720 | +0.000 |
| transformation_health | 0.740 | 0.740 | +0.000 |

### Case 2: DO-002-v1
**Type:** hidden_cascade
**Kind:** score_keyed | **rho:** 0.9

**Description:** Customer identifier cascade: the cached alert suggests auto_fix; partition-scoped evidence supports escalate_to_owner.

#### WITHOUT VLD (single-pass)
- Action: **auto_fix** ❌ (ground truth: escalate_to_owner)
- Based on surface factors only
- Distance to nearest centroid: 0.2242

#### WITH VLD (investigation)
- **Hop 1:** The current partition record corrects the cached schema_stability estimate from 0.81 to 0.26.
  - Checked: schema_registry
  - Found: Synthetic record do-002_rec_154: Active producer/consumer contract: account_id changed from a numeric field to a UUID object. The cached surface schema summary refers to the prior contract. The planted fixture maps this record to schema_stability=0.26; this value is not a calibrated or measured customer metric.
  - Factor `schema_stability`: 0.810 → 0.260
  - Action after hop 1: **rollback** → (dist: 0.5608)
- **Hop 2:** The current partition record corrects the cached impact_scope estimate from 0.22 to 0.83.
  - Checked: dependency_graph
  - Found: Synthetic record do-002_rec_162: The partition-scoped dependency inventory enumerates 6 affected consumer systems: invoice_addressing, payment_allocation, account_balances, renewal_billing, support_entitlements, customer_finance. All have current dependency records for this data version. The planted fixture maps this record to impact_scope=0.83; this value is not a calibrated or measured customer metric.
  - Factor `impact_scope`: 0.220 → 0.830
  - Action after hop 2: **escalate_to_owner** ✅ (dist: 0.7618)
- **Hop 3:** The current partition record corrects the cached pattern_familiarity estimate from 0.91 to 0.11.
  - Checked: pattern_database
  - Found: Synthetic record do-002_rec_934: Exact comparison criterion: same pipeline, active schema version, transform artifact, error fingerprint, and partition mode. Earlier null identifiers came from a retryable export gap. The root-cause signature therefore differs from the apparently familiar historical case. The planted fixture maps this record to pattern_familiarity=0.11; this value is not a calibrated or measured customer metric. Action-context records retained before the alert: Current ownership record assigns the affected producer and downstream services to Customer platform and billing owners. The investigation concerns a live multi-owner contract or transformation dependency; the generic local retry cannot restore downstream consistency. No single locally authorized rollback covers all active consumer contracts. Coordinate containment and remediation through the owners; escalation does not mean passively waiting.
  - Factor `pattern_familiarity`: 0.910 → 0.110
  - Action after hop 3: **escalate_to_owner** ✅ (dist: 0.3346)

- Action: **escalate_to_owner** ✅
- Distance to nearest centroid: 0.3346

**Why VLD changed the decision:** The explicitly defined synthetic centroid scorer selects auto_fix from the surface factors and escalate_to_owner after all 3 relevant reads. The existing mapper cannot retain the uuid namespace. Current ownership record assigns the affected producer and downstream services to Customer platform and billing owners. The investigation concerns a live multi-owner contract or transformation dependency; the generic local retry cannot restore downstream consistency. No single locally authorized rollback covers all active consumer contracts. Coordinate containment and remediation through the owners; escalation does not mean passively waiting.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| data_quality | 0.570 | 0.570 | +0.000 |
| impact_scope | 0.220 | 0.830 | +0.610 ← |
| pattern_familiarity | 0.910 | 0.110 | -0.800 ← |
| schema_stability | 0.810 | 0.260 | -0.550 ← |
| source_reliability | 0.780 | 0.780 | +0.000 |
| transformation_health | 0.680 | 0.680 | +0.000 |

### Case 3: DO-003-v1
**Type:** hidden_cascade
**Kind:** score_keyed | **rho:** 1.0

**Description:** Invoice amount unit cascade: the cached alert suggests auto_fix; partition-scoped evidence supports escalate_to_owner.

#### WITHOUT VLD (single-pass)
- Action: **auto_fix** ❌ (ground truth: escalate_to_owner)
- Based on surface factors only
- Distance to nearest centroid: 0.2506

#### WITH VLD (investigation)
- **Hop 1:** The current partition record corrects the cached schema_stability estimate from 0.83 to 0.22.
  - Checked: schema_registry
  - Found: Synthetic record do-003_rec_354: Active producer/consumer contract: amount_cents integer was replaced by amount decimal plus currency_scale. The cached surface schema summary refers to the prior contract. The planted fixture maps this record to schema_stability=0.22; this value is not a calibrated or measured customer metric.
  - Factor `schema_stability`: 0.830 → 0.220
  - Action after hop 1: **rollback** → (dist: 0.5555)
- **Hop 2:** The current partition record corrects the cached impact_scope estimate from 0.25 to 0.92.
  - Checked: dependency_graph
  - Found: Synthetic record do-003_rec_434: The partition-scoped dependency inventory enumerates 6 affected consumer systems: billing_ledger, tax_calculation, payment_requests, receivables_aging, credit_notes, revenue_reports. All have current dependency records for this data version. The planted fixture maps this record to impact_scope=0.92; this value is not a calibrated or measured customer metric.
  - Factor `impact_scope`: 0.250 → 0.920
  - Action after hop 2: **escalate_to_owner** ✅ (dist: 0.7797)
- **Hop 3:** The current partition record corrects the cached pattern_familiarity estimate from 0.91 to 0.31.
  - Checked: pattern_database
  - Found: Synthetic record do-003_rec_541: Exact comparison criterion: same pipeline, active schema version, transform artifact, error fingerprint, and partition mode. Earlier amount gaps were transient missing export pages. The root-cause signature therefore differs from the apparently familiar historical case. The planted fixture maps this record to pattern_familiarity=0.31; this value is not a calibrated or measured customer metric. Action-context records retained before the alert: Current ownership record assigns the affected producer and downstream services to Invoice producer and finance data owners. The investigation concerns a live multi-owner contract or transformation dependency; the generic local retry cannot restore downstream consistency. No single locally authorized rollback covers all active consumer contracts. Coordinate containment and remediation through the owners; escalation does not mean passively waiting.
  - Factor `pattern_familiarity`: 0.910 → 0.310
  - Action after hop 3: **escalate_to_owner** ✅ (dist: 0.3696)

- Action: **escalate_to_owner** ✅
- Distance to nearest centroid: 0.3696

**Why VLD changed the decision:** The explicitly defined synthetic centroid scorer selects auto_fix from the surface factors and escalate_to_owner after all 3 relevant reads. The normalization rule ignores the new currency_scale field. Current ownership record assigns the affected producer and downstream services to Invoice producer and finance data owners. The investigation concerns a live multi-owner contract or transformation dependency; the generic local retry cannot restore downstream consistency. No single locally authorized rollback covers all active consumer contracts. Coordinate containment and remediation through the owners; escalation does not mean passively waiting.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| data_quality | 0.590 | 0.590 | +0.000 |
| impact_scope | 0.250 | 0.920 | +0.670 ← |
| pattern_familiarity | 0.910 | 0.310 | -0.600 ← |
| schema_stability | 0.830 | 0.220 | -0.610 ← |
| source_reliability | 0.710 | 0.710 | +0.000 |
| transformation_health | 0.710 | 0.710 | +0.000 |

### Case 4: DO-004-v1
**Type:** hidden_cascade
**Kind:** score_keyed | **rho:** 0.9

**Description:** Shipment event time cascade: the cached alert suggests auto_fix; partition-scoped evidence supports escalate_to_owner.

#### WITHOUT VLD (single-pass)
- Action: **auto_fix** ❌ (ground truth: escalate_to_owner)
- Based on surface factors only
- Distance to nearest centroid: 0.2043

#### WITH VLD (investigation)
- **Hop 1:** The current partition record corrects the cached schema_stability estimate from 0.85 to 0.12.
  - Checked: schema_registry
  - Found: Synthetic record do-004_rec_727: Active producer/consumer contract: event_time local string was replaced by UTC timestamp plus offset_minutes. The cached surface schema summary refers to the prior contract. The planted fixture maps this record to schema_stability=0.12; this value is not a calibrated or measured customer metric.
  - Factor `schema_stability`: 0.850 → 0.120
  - Action after hop 1: **rollback** → (dist: 0.4912)
- **Hop 2:** The current partition record corrects the cached impact_scope estimate from 0.21 to 0.82.
  - Checked: dependency_graph
  - Found: Synthetic record do-004_rec_970: The partition-scoped dependency inventory enumerates 6 affected consumer systems: freight_billing, delivery_sla, inventory_arrivals, carrier_settlement, customer_tracking, shipping_costs. All have current dependency records for this data version. The planted fixture maps this record to impact_scope=0.82; this value is not a calibrated or measured customer metric.
  - Factor `impact_scope`: 0.210 → 0.820
  - Action after hop 2: **escalate_to_owner** ✅ (dist: 0.7224)
- **Hop 3:** The current partition record corrects the cached pattern_familiarity estimate from 0.82 to 0.27.
  - Checked: pattern_database
  - Found: Synthetic record do-004_rec_375: Exact comparison criterion: same pipeline, active schema version, transform artifact, error fingerprint, and partition mode. Earlier late-arrival alerts were transport jitter on the old time contract. The root-cause signature therefore differs from the apparently familiar historical case. The planted fixture maps this record to pattern_familiarity=0.27; this value is not a calibrated or measured customer metric. Action-context records retained before the alert: Current ownership record assigns the affected producer and downstream services to Carrier integration and freight billing owners. The investigation concerns a live multi-owner contract or transformation dependency; the generic local retry cannot restore downstream consistency. No single locally authorized rollback covers all active consumer contracts. Coordinate containment and remediation through the owners; escalation does not mean passively waiting.
  - Factor `pattern_familiarity`: 0.820 → 0.270
  - Action after hop 3: **escalate_to_owner** ✅ (dist: 0.4017)

- Action: **escalate_to_owner** ✅
- Distance to nearest centroid: 0.4017

**Why VLD changed the decision:** The explicitly defined synthetic centroid scorer selects auto_fix from the surface factors and escalate_to_owner after all 3 relevant reads. The mapper still interprets the value in warehouse local time. Current ownership record assigns the affected producer and downstream services to Carrier integration and freight billing owners. The investigation concerns a live multi-owner contract or transformation dependency; the generic local retry cannot restore downstream consistency. No single locally authorized rollback covers all active consumer contracts. Coordinate containment and remediation through the owners; escalation does not mean passively waiting.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| data_quality | 0.610 | 0.610 | +0.000 |
| impact_scope | 0.210 | 0.820 | +0.610 ← |
| pattern_familiarity | 0.820 | 0.270 | -0.550 ← |
| schema_stability | 0.850 | 0.120 | -0.730 ← |
| source_reliability | 0.720 | 0.720 | +0.000 |
| transformation_health | 0.630 | 0.630 | +0.000 |

### Case 5: DO-005-v1
**Type:** hidden_cascade
**Kind:** score_keyed | **rho:** 0.7

**Description:** Subscription entitlement cascade: the cached alert suggests auto_fix; partition-scoped evidence supports escalate_to_owner.

#### WITHOUT VLD (single-pass)
- Action: **auto_fix** ❌ (ground truth: escalate_to_owner)
- Based on surface factors only
- Distance to nearest centroid: 0.2022

#### WITH VLD (investigation)
- **Hop 1:** The current partition record corrects the cached schema_stability estimate from 0.85 to 0.21.
  - Checked: schema_registry
  - Found: Synthetic record do-005_rec_780: Active producer/consumer contract: plan_code scalar was replaced by plan_code plus entitlement_version. The cached surface schema summary refers to the prior contract. The planted fixture maps this record to schema_stability=0.21; this value is not a calibrated or measured customer metric.
  - Factor `schema_stability`: 0.850 → 0.210
  - Action after hop 1: **monitor** → (dist: 0.6579)
- **Hop 2:** The current partition record corrects the cached impact_scope estimate from 0.12 to 0.95.
  - Checked: dependency_graph
  - Found: Synthetic record do-005_rec_723: The partition-scoped dependency inventory enumerates 6 affected consumer systems: usage_billing, subscription_invoices, service_entitlements, renewal_quotes, revenue_deferral, account_portal. All have current dependency records for this data version. The planted fixture maps this record to impact_scope=0.95; this value is not a calibrated or measured customer metric.
  - Factor `impact_scope`: 0.120 → 0.950
  - Action after hop 2: **escalate_to_owner** ✅ (dist: 0.8648)
- **Hop 3:** The current partition record corrects the cached pattern_familiarity estimate from 0.98 to 0.24.
  - Checked: pattern_database
  - Found: Synthetic record do-005_rec_222: Exact comparison criterion: same pipeline, active schema version, transform artifact, error fingerprint, and partition mode. Earlier unknown-plan alerts were fixed by refreshing a scalar lookup. The root-cause signature therefore differs from the apparently familiar historical case. The planted fixture maps this record to pattern_familiarity=0.24; this value is not a calibrated or measured customer metric. Action-context records retained before the alert: Current ownership record assigns the affected producer and downstream services to Subscription schema and billing owners. The investigation concerns a live multi-owner contract or transformation dependency; the generic local retry cannot restore downstream consistency. No single locally authorized rollback covers all active consumer contracts. Coordinate containment and remediation through the owners; escalation does not mean passively waiting.
  - Factor `pattern_familiarity`: 0.980 → 0.240
  - Action after hop 3: **escalate_to_owner** ✅ (dist: 0.4082)

- Action: **escalate_to_owner** ✅
- Distance to nearest centroid: 0.4082

**Why VLD changed the decision:** The explicitly defined synthetic centroid scorer selects auto_fix from the surface factors and escalate_to_owner after all 3 relevant reads. The mapper joins without the entitlement_version key. Current ownership record assigns the affected producer and downstream services to Subscription schema and billing owners. The investigation concerns a live multi-owner contract or transformation dependency; the generic local retry cannot restore downstream consistency. No single locally authorized rollback covers all active consumer contracts. Coordinate containment and remediation through the owners; escalation does not mean passively waiting.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| data_quality | 0.690 | 0.690 | +0.000 |
| impact_scope | 0.120 | 0.950 | +0.830 ← |
| pattern_familiarity | 0.980 | 0.240 | -0.740 ← |
| schema_stability | 0.850 | 0.210 | -0.640 ← |
| source_reliability | 0.740 | 0.740 | +0.000 |
| transformation_health | 0.750 | 0.750 | +0.000 |

### Case 6: DO-006-v1
**Type:** familiar_pattern_unfamiliar_cause
**Kind:** score_keyed | **rho:** 0.9

**Description:** Familiar timeout from checkpoint epoch mismatch: the cached alert suggests auto_fix; partition-scoped evidence supports manual_fix.

#### WITHOUT VLD (single-pass)
- Action: **auto_fix** ❌ (ground truth: manual_fix)
- Based on surface factors only
- Distance to nearest centroid: 0.2587

#### WITH VLD (investigation)
- **Hop 1:** The current partition record corrects the cached pattern_familiarity estimate from 0.99 to 0.54.
  - Checked: pattern_database
  - Found: Synthetic record do-006_rec_563: Exact comparison criterion: same pipeline, active schema version, transform artifact, error fingerprint, and partition mode. Prior timeouts had unchanged checkpoint epochs and were safe to retry. The root-cause signature therefore differs from the apparently familiar historical case. The planted fixture maps this record to pattern_familiarity=0.54; this value is not a calibrated or measured customer metric.
  - Factor `pattern_familiarity`: 0.990 → 0.540
  - Action after hop 1: **auto_fix** → (dist: 0.3208)
- **Hop 2:** The current partition record corrects the cached source_reliability estimate from 0.78 to 0.39.
  - Checked: source_partition_manifest
  - Found: Synthetic record do-006_rec_424: the current feed repeats one offset interval and omits its successor. The planted fixture maps this record to source_reliability=0.39; this value is not a calibrated or measured customer metric. Action-context records retained before the alert: The current source/contract mismatch in orders_cdc_ingest needs the owning engineer to correct the specific parser, source partition, checkpoint, or join contract described by the evidence. No preauthorized automatic recipe matches the active cause. A code rollback alone would not restore the current external contract or repair the upstream source inconsistency. Affected output is held in a staging validation gate. The local owner can apply a targeted repair and reconcile the bounded affected partition.
  - Factor `source_reliability`: 0.780 → 0.390
  - Action after hop 2: **manual_fix** ✅ (dist: 0.2212)

- Action: **manual_fix** ✅
- Distance to nearest centroid: 0.2212

**Why VLD changed the decision:** The explicitly defined synthetic centroid scorer selects auto_fix from the surface factors and manual_fix after all 2 relevant reads. A failover changed the checkpoint epoch and the stored resume token refers to its predecessor. The current source/contract mismatch in orders_cdc_ingest needs the owning engineer to correct the specific parser, source partition, checkpoint, or join contract described by the evidence. No preauthorized automatic recipe matches the active cause. A code rollback alone would not restore the current external contract or repair the upstream source inconsistency. Affected output is held in a staging validation gate. The local owner can apply a targeted repair and reconcile the bounded affected partition.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| data_quality | 0.660 | 0.660 | +0.000 |
| impact_scope | 0.260 | 0.260 | +0.000 |
| pattern_familiarity | 0.990 | 0.540 | -0.450 ← |
| schema_stability | 0.820 | 0.820 | +0.000 |
| source_reliability | 0.780 | 0.390 | -0.390 ← |
| transformation_health | 0.740 | 0.740 | +0.000 |

### Case 7: DO-007-v1
**Type:** familiar_pattern_unfamiliar_cause
**Kind:** score_keyed | **rho:** 1.0

**Description:** Familiar empty batch from cursor format change: the cached alert suggests auto_fix; partition-scoped evidence supports manual_fix.

#### WITHOUT VLD (single-pass)
- Action: **auto_fix** ❌ (ground truth: manual_fix)
- Based on surface factors only
- Distance to nearest centroid: 0.2150

#### WITH VLD (investigation)
- **Hop 1:** The current partition record corrects the cached pattern_familiarity estimate from 0.96 to 0.56.
  - Checked: pattern_database
  - Found: Synthetic record do-007_rec_742: Exact comparison criterion: same pipeline, active schema version, transform artifact, error fingerprint, and partition mode. Prior empty batches were brief rate-limit windows with intact pagination. The root-cause signature therefore differs from the apparently familiar historical case. The planted fixture maps this record to pattern_familiarity=0.56; this value is not a calibrated or measured customer metric.
  - Factor `pattern_familiarity`: 0.960 → 0.560
  - Action after hop 1: **auto_fix** → (dist: 0.2868)
- **Hop 2:** The current partition record corrects the cached source_reliability estimate from 0.72 to 0.17.
  - Checked: source_partition_manifest
  - Found: Synthetic record do-007_rec_642: the current feed repeats the first page while omitting later pages. The planted fixture maps this record to source_reliability=0.17; this value is not a calibrated or measured customer metric. Action-context records retained before the alert: The current source/contract mismatch in catalog_api_ingest needs the owning engineer to correct the specific parser, source partition, checkpoint, or join contract described by the evidence. No preauthorized automatic recipe matches the active cause. A code rollback alone would not restore the current external contract or repair the upstream source inconsistency. Affected output is held in a staging validation gate. The local owner can apply a targeted repair and reconcile the bounded affected partition.
  - Factor `source_reliability`: 0.720 → 0.170
  - Action after hop 2: **manual_fix** ✅ (dist: 0.3430)

- Action: **manual_fix** ✅
- Distance to nearest centroid: 0.3430

**Why VLD changed the decision:** The explicitly defined synthetic centroid scorer selects auto_fix from the surface factors and manual_fix after all 2 relevant reads. The reader treats the continuation token as a numeric offset. The current source/contract mismatch in catalog_api_ingest needs the owning engineer to correct the specific parser, source partition, checkpoint, or join contract described by the evidence. No preauthorized automatic recipe matches the active cause. A code rollback alone would not restore the current external contract or repair the upstream source inconsistency. Affected output is held in a staging validation gate. The local owner can apply a targeted repair and reconcile the bounded affected partition.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| data_quality | 0.640 | 0.640 | +0.000 |
| impact_scope | 0.150 | 0.150 | +0.000 |
| pattern_familiarity | 0.960 | 0.560 | -0.400 ← |
| schema_stability | 0.860 | 0.860 | +0.000 |
| source_reliability | 0.720 | 0.170 | -0.550 ← |
| transformation_health | 0.770 | 0.770 | +0.000 |

### Case 8: DO-008-v1
**Type:** familiar_pattern_unfamiliar_cause
**Kind:** score_keyed | **rho:** 0.9

**Description:** Familiar stale snapshot from object version mismatch: the cached alert suggests auto_fix; partition-scoped evidence supports manual_fix.

#### WITHOUT VLD (single-pass)
- Action: **monitor** ❌ (ground truth: manual_fix)
- Based on surface factors only
- Distance to nearest centroid: 0.2078

#### WITH VLD (investigation)
- **Hop 1:** The current partition record corrects the cached pattern_familiarity estimate from 0.99 to 0.53.
  - Checked: pattern_database
  - Found: Synthetic record do-008_rec_997: Exact comparison criterion: same pipeline, active schema version, transform artifact, error fingerprint, and partition mode. Prior stale snapshots were delayed uploads with matching manifest digests. The root-cause signature therefore differs from the apparently familiar historical case. The planted fixture maps this record to pattern_familiarity=0.53; this value is not a calibrated or measured customer metric.
  - Factor `pattern_familiarity`: 0.990 → 0.530
  - Action after hop 1: **auto_fix** → (dist: 0.3633)
- **Hop 2:** The current partition record corrects the cached source_reliability estimate from 0.86 to 0.23.
  - Checked: source_partition_manifest
  - Found: Synthetic record do-008_rec_167: the served snapshot differs from the version promised by the current manifest. The planted fixture maps this record to source_reliability=0.23; this value is not a calibrated or measured customer metric. Action-context records retained before the alert: The current source/contract mismatch in inventory_snapshot_ingest needs the owning engineer to correct the specific parser, source partition, checkpoint, or join contract described by the evidence. No preauthorized automatic recipe matches the active cause. A code rollback alone would not restore the current external contract or repair the upstream source inconsistency. Affected output is held in a staging validation gate. The local owner can apply a targeted repair and reconcile the bounded affected partition.
  - Factor `source_reliability`: 0.860 → 0.230
  - Action after hop 2: **manual_fix** ✅ (dist: 0.3001)

- Action: **manual_fix** ✅
- Distance to nearest centroid: 0.3001

**Why VLD changed the decision:** The explicitly defined synthetic centroid scorer selects auto_fix from the surface factors and manual_fix after all 2 relevant reads. The reader resolves an unversioned alias instead of the manifest version. The current source/contract mismatch in inventory_snapshot_ingest needs the owning engineer to correct the specific parser, source partition, checkpoint, or join contract described by the evidence. No preauthorized automatic recipe matches the active cause. A code rollback alone would not restore the current external contract or repair the upstream source inconsistency. Affected output is held in a staging validation gate. The local owner can apply a targeted repair and reconcile the bounded affected partition.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| data_quality | 0.660 | 0.660 | +0.000 |
| impact_scope | 0.280 | 0.280 | +0.000 |
| pattern_familiarity | 0.990 | 0.530 | -0.460 ← |
| schema_stability | 0.740 | 0.740 | +0.000 |
| source_reliability | 0.860 | 0.230 | -0.630 ← |
| transformation_health | 0.800 | 0.800 | +0.000 |
