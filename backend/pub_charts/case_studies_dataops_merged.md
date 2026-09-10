# VLD With-Without Case Studies — DATAOPS_MERGED
**Generated from Stage 1 multi-hop scenarios**
**[PLANTED POSITIVE CONTROL — not production data]**

## Summary

| Category | Count | % |
|---|---|---|
| VLD saves (SP wrong, VLD right) | 19 | 27% |
| VLD hurts (SP right, VLD wrong) | 0 | 0% |
| Both correct | 15 | 21% |
| Both wrong | 36 | 51% |
| **Total multi-hop** | **70** | |

## Case Studies: VLD Saves

*Scenarios where single-pass gets it wrong and VLD gets it right.*

### Case 1: DO-MH-005-v3
**Type:** recurring_vs_novel
**Kind:** score_keyed | **rho:** 0.7

**Description:** Alert matches a familiar recurring signature; whether the underlying cause is the same is not legible in the evidence.

#### WITHOUT VLD (single-pass)
- Action: **monitor** ❌ (ground truth: manual_fix)
- Based on surface factors only
- Distance to nearest centroid: 0.3836

#### WITH VLD (investigation)
- **Hop 1:** Checked resource profile: the cluster's worker ceiling was halved on Saturday.
  - Checked: ResourceProfile -> autoscale_changed, max_workers
  - Found: cluster max_workers reduced from 16 to 8 on Saturday
  - Factor `transformation_health`: 0.550 → 0.350
  - Action after hop 1: **manual_fix** ✅ (dist: 0.4522)
- **Hop 2:** Checked run profile: volume has grown 22% since the capacity change.
  - Checked: BatchRun -> volume, worker_minutes
  - Found: volume grew 22% since the ceiling change
  - Factor `impact_scope`: 0.520 → 0.660
  - Action after hop 2: **manual_fix** ✅ (dist: 0.4977)

- Action: **manual_fix** ✅
- Distance to nearest centroid: 0.4977

**Why VLD changed the decision:** A capacity change plus volume growth — needs a sizing decision, not an automated retry.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| data_quality | 0.720 | 0.720 | +0.000 |
| impact_scope | 0.520 | 0.660 | +0.140 ← |
| pattern_familiarity | 0.850 | 0.850 | +0.000 |
| schema_stability | 0.820 | 0.820 | +0.000 |
| source_reliability | 0.600 | 0.600 | +0.000 |
| transformation_health | 0.550 | 0.350 | -0.200 ← |

### Case 2: DO-MH-007-v2
**Type:** quality_vs_infrastructure
**Kind:** score_keyed | **rho:** 0.9

**Description:** Identical latency symptom; bad input data and slow storage are indistinguishable at the surface.

#### WITHOUT VLD (single-pass)
- Action: **auto_fix** ❌ (ground truth: escalate_to_owner)
- Based on surface factors only
- Distance to nearest centroid: 0.5386

#### WITH VLD (investigation)
- **Hop 1:** Checked storage metrics: p99 disk latency is twelve times baseline while the input is clean.
  - Checked: StorageMetric -> disk_latency_p99_ms, iops_saturation; DataSource -> null_rate
  - Found: disk p99 540ms against a 45ms baseline, input clean
  - Factor `source_reliability`: 0.200 → 0.160
  - Action after hop 1: **auto_fix** → (dist: 0.5686)
- **Hop 2:** Checked the volume group: three other systems on the same storage are also slow.
  - Checked: StorageMetric -> volume_group, co_tenants
  - Found: shared volume group, three co-tenant systems affected
  - Factor `impact_scope`: 0.820 → 0.880
  - Action after hop 2: **escalate_to_owner** ✅ (dist: 0.5982)

- Action: **escalate_to_owner** ✅
- Distance to nearest centroid: 0.5982

**Why VLD changed the decision:** Shared storage degradation affecting multiple tenants — platform owner's call.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| data_quality | 0.620 | 0.620 | +0.000 |
| impact_scope | 0.820 | 0.880 | +0.060 ← |
| pattern_familiarity | 0.460 | 0.460 | +0.000 |
| schema_stability | 0.700 | 0.700 | +0.000 |
| source_reliability | 0.200 | 0.160 | -0.040 |
| transformation_health | 0.640 | 0.640 | +0.000 |

### Case 3: DO-MH-014-v3
**Type:** lakehouse_partition_issue
**Kind:** score_keyed | **rho:** 0.7

**Description:** Reported as pipeline slowness; the fault is on the read side and the alert does not say so.

#### WITHOUT VLD (single-pass)
- Action: **auto_fix** ❌ (ground truth: escalate_to_owner)
- Based on surface factors only
- Distance to nearest centroid: 0.3867

#### WITH VLD (investigation)
- **Hop 1:** Checked partition layout: the table is partitioned by a 4.1-million-value identifier.
  - Checked: PartitionLayout -> partition_key, cardinality
  - Found: partitioned by order_id, cardinality 4.1M
  - Factor `impact_scope`: 0.700 → 0.780
  - Action after hop 1: **escalate_to_owner** ✅ (dist: 0.4099)
- **Hop 2:** Checked remediation options: compaction will not help and a full rewrite would take nine hours.
  - Checked: PartitionLayout -> compaction_eligible, rewrite_cost_hours
  - Found: compaction ineffective; full rewrite estimated 9 hours
  - Factor `transformation_health`: 0.580 → 0.300
  - Action after hop 2: **escalate_to_owner** ✅ (dist: 0.3333)

- Action: **escalate_to_owner** ✅
- Distance to nearest centroid: 0.3333

**Why VLD changed the decision:** The partitioning scheme is wrong by design; the table owner must decide on a rewrite.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| data_quality | 0.640 | 0.640 | +0.000 |
| impact_scope | 0.700 | 0.780 | +0.080 ← |
| pattern_familiarity | 0.360 | 0.360 | +0.000 |
| schema_stability | 0.550 | 0.550 | +0.000 |
| source_reliability | 0.720 | 0.720 | +0.000 |
| transformation_health | 0.580 | 0.300 | -0.280 ← |

### Case 4: DO-MH-009-v5
**Type:** schema_migration_window
**Kind:** content_keyed | **rho:** 1.0

**Description:** Validation errors during a schema migration; migration state decides the action.

#### WITHOUT VLD (single-pass)
- Action: **rollback** ❌ (ground truth: auto_fix)
- Based on surface factors only
- Distance to nearest centroid: 0.4776

#### WITH VLD (investigation)
- **Hop 1:** Checked the migration window: window still flagged active but the migration is marked complete; residual errors have a documented repair.
  - Checked: PipelineSystem <- MIGRATION_COVERS <- MigrationWindow -> active, expected_error_classes, error_ceiling_pct
  - Found: window still flagged active but the migration is marked complete; residual errors have a documented repair
  - Factor `schema_stability`: 0.210 → 0.620
  - Action after hop 1: **auto_fix** ✅ (dist: 0.2122)

- Action: **auto_fix** ✅
- Distance to nearest centroid: 0.2122

**Why VLD changed the decision:** SPECIAL CASE: the evidence points away from the expected 'monitor' — the migration is finished, so the residual records take their documented automated repair rather than being waited out.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| data_quality | 0.320 | 0.320 | +0.000 |
| impact_scope | 0.580 | 0.580 | +0.000 |
| pattern_familiarity | 0.500 | 0.500 | +0.000 |
| schema_stability | 0.210 | 0.620 | +0.410 ← |
| source_reliability | 0.670 | 0.670 | +0.000 |
| transformation_health | 0.710 | 0.710 | +0.000 |

### Case 5: DATAOPS-SUP-001-v1
**Type:** hidden_cascade
**Kind:** score_keyed | **rho:** 0.9

**Description:** A familiar invoice-ingest retry appears isolated; a decimal contract migration reaches five consumers with incompatible money conversions.

#### WITHOUT VLD (single-pass)
- Action: **monitor** ❌ (ground truth: escalate_to_owner)
- Based on surface factors only
- Distance to nearest centroid: 0.3916

#### WITH VLD (investigation)
- **Hop 1:** The current contract, rather than the cached version, determines which consumers must be inspected.
  - Checked: schema_registry
  - Found: The active writer fingerprint resolves to a decimal-scale revision absent from the cached alert summary; its deployment binding identifies the live invoice consumer set. Follow-up lookup key: lookup_sup_001_132719.
  - Factor `schema_stability`: 0.770 → 0.050
  - Action after hop 1: **monitor** → (dist: 0.7434)
- **Hop 2:** The failure is a shared-contract cascade, not a single ingest task.
  - Checked: dependency_graph
  - Found: The deployment binding reaches five active consumers, including billing allocation; the affected decoder build is recorded on these lineage edges. Follow-up lookup key: lookup_sup_001_976251.
  - Factor `impact_scope`: 0.250 → 0.990
  - Action after hop 2: **escalate_to_owner** ✅ (dist: 0.6623)
- **Hop 3:** The build evidence rules out a safe local rollback or automated retry.
  - Checked: transformation_lineage
  - Found: The bound build has pre-alert shadow comparisons showing three consumers double-scale amounts and two reject them. Writes span independent checkpoints; no atomic previous-version recovery exists.
  - Factor `transformation_health`: 0.800 → 0.040
  - Action after hop 3: **escalate_to_owner** ✅ (dist: 0.5608)

- Action: **escalate_to_owner** ✅
- Distance to nearest centroid: 0.5608

**Why VLD changed the decision:** The reference midpoint-centroid scorer selects auto_fix for the surface vector. The ordered investigation updates schema_stability from 0.77 to 0.05, impact_scope from 0.25 to 0.99, transformation_health from 0.80 to 0.04, after which it selects escalate_to_owner. Escalate to the data platform owner: five live consumers require coordinated repair, and their incompatible decimal conversions make a unilateral retry or rollback unsafe. No coordinated rollback is approved. These are planted synthetic observations available at alert arrival, not observed outcomes of an analyst action.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| data_quality | 0.680 | 0.680 | +0.000 |
| impact_scope | 0.250 | 0.990 | +0.740 ← |
| pattern_familiarity | 0.810 | 0.810 | +0.000 |
| schema_stability | 0.770 | 0.050 | -0.720 ← |
| source_reliability | 0.710 | 0.710 | +0.000 |
| transformation_health | 0.800 | 0.040 | -0.760 ← |

### Case 6: DATAOPS-SUP-004-v4
**Type:** hidden_cascade
**Kind:** score_keyed | **rho:** 1.0

**Description:** A familiar event retry masks a route-key migration spanning six logistics consumers.

#### WITHOUT VLD (single-pass)
- Action: **monitor** ❌ (ground truth: escalate_to_owner)
- Based on surface factors only
- Distance to nearest centroid: 0.3693

#### WITH VLD (investigation)
- **Hop 1:** The correct lineage lookup must use the new route-key binding.
  - Checked: schema_registry
  - Found: The active revision replaced the route join key without a compatibility alias; it supplies the deployment binding used by the current shipment run. Follow-up lookup key: lookup_sup_004_638691.
  - Factor `schema_stability`: 0.790 → 0.100
  - Action after hop 1: **monitor** → (dist: 0.6861)
- **Hop 2:** The apparent local retry is a multi-owner propagation event.
  - Checked: dependency_graph
  - Found: Six live consumers carry this binding and use independently checkpointed materializations. Their edges identify the route-normalizer build. Follow-up lookup key: lookup_sup_004_488953.
  - Factor `impact_scope`: 0.280 → 0.990
  - Action after hop 2: **escalate_to_owner** ✅ (dist: 0.6151)
- **Hop 3:** Independent state changes require an owner-led recovery plan.
  - Checked: transformation_lineage
  - Found: Captured pre-alert comparisons show unmatched and duplicated joins in the bound build. Carrier handoff and freight accrual have advanced different checkpoints, invalidating a unilateral rollback.
  - Factor `transformation_health`: 0.770 → 0.030
  - Action after hop 3: **escalate_to_owner** ✅ (dist: 0.5358)

- Action: **escalate_to_owner** ✅
- Distance to nearest centroid: 0.5358

**Why VLD changed the decision:** The reference midpoint-centroid scorer selects auto_fix for the surface vector. The ordered investigation updates schema_stability from 0.79 to 0.10, impact_scope from 0.28 to 0.99, transformation_health from 0.77 to 0.03, after which it selects escalate_to_owner. Escalate to the platform owner: the changed join key has produced divergent materializations across independent checkpoints, and replay or rollback requires cross-owner reconciliation. These are planted synthetic observations available at alert arrival, not observed outcomes of an analyst action.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| data_quality | 0.680 | 0.680 | +0.000 |
| impact_scope | 0.280 | 0.990 | +0.710 ← |
| pattern_familiarity | 0.800 | 0.800 | +0.000 |
| schema_stability | 0.790 | 0.100 | -0.690 ← |
| source_reliability | 0.720 | 0.720 | +0.000 |
| transformation_health | 0.770 | 0.030 | -0.740 ← |

### Case 7: DATAOPS-SUP-005-v5
**Type:** hidden_cascade
**Kind:** score_keyed | **rho:** 0.7

**Description:** A familiar consent-code drift alert hides a semantic contract change with widespread policy-sensitive effects.

#### WITHOUT VLD (single-pass)
- Action: **monitor** ❌ (ground truth: escalate_to_owner)
- Based on surface factors only
- Distance to nearest centroid: 0.3916

#### WITH VLD (investigation)
- **Hop 1:** Schema stability includes semantic contract changes, even with an unchanged field type.
  - Checked: schema_registry
  - Found: The active contract changed the meaning of the consent enum while preserving its wire type; the recorded deployment binding identifies the purpose-specific projections. Follow-up lookup key: lookup_sup_005_944117.
  - Factor `schema_stability`: 0.830 → 0.050
  - Action after hop 1: **monitor** → (dist: 0.7342)
- **Hop 2:** The true business scope is much wider than the initial code-drift alert.
  - Checked: dependency_graph
  - Found: Seven active projections use the binding, including partner export filtering and the audit mart. Their edges point to a shared purpose-mapper build. Follow-up lookup key: lookup_sup_005_641377.
  - Factor `impact_scope`: 0.290 → 0.990
  - Action after hop 2: **escalate_to_owner** ✅ (dist: 0.6576)
- **Hop 3:** A routine retry cannot repair inconsistent semantics across independently advanced projections.
  - Checked: transformation_lineage
  - Found: Captured mapping checks show inconsistent allow and suppress results across purpose-specific projections. Their checkpoints differ, and recovery approval belongs to the consent data owner.
  - Factor `transformation_health`: 0.790 → 0.030
  - Action after hop 3: **escalate_to_owner** ✅ (dist: 0.5687)

- Action: **escalate_to_owner** ✅
- Distance to nearest centroid: 0.5687

**Why VLD changed the decision:** The reference midpoint-centroid scorer selects auto_fix for the surface vector. The ordered investigation updates schema_stability from 0.83 to 0.05, impact_scope from 0.29 to 0.99, transformation_health from 0.79 to 0.03, after which it selects escalate_to_owner. Escalate to the consent data owner: incompatible purpose-specific projections have already advanced separately, and the local pipeline has no authority to redefine consent semantics or approve coordinated recovery. These are planted synthetic observations available at alert arrival, not observed outcomes of an analyst action.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| data_quality | 0.660 | 0.660 | +0.000 |
| impact_scope | 0.290 | 0.990 | +0.700 ← |
| pattern_familiarity | 0.830 | 0.830 | +0.000 |
| schema_stability | 0.830 | 0.050 | -0.780 ← |
| source_reliability | 0.700 | 0.700 | +0.000 |
| transformation_health | 0.790 | 0.030 | -0.760 ← |

### Case 8: DATAOPS-SUP-007-v2
**Type:** familiar_pattern_unfamiliar_cause
**Kind:** score_keyed | **rho:** 0.9

**Description:** A familiar retryable batch-gap alert actually originates in a new provider acknowledgment protocol.

#### WITHOUT VLD (single-pass)
- Action: **monitor** ❌ (ground truth: escalate_to_owner)
- Based on surface factors only
- Distance to nearest centroid: 0.5154

#### WITH VLD (investigation)
- **Hop 1:** The familiar batch-gap symptom has a different and unvalidated cause.
  - Checked: pattern_database
  - Found: Historical gaps followed explicit retryable failures. Current captures show success acknowledgments with missing sequence members; the trace supplies the new provider session identifier. Follow-up lookup key: lookup_sup_007_201471.
  - Factor `pattern_familiarity`: 0.960 → 0.050
  - Action after hop 1: **monitor** → (dist: 0.6209)
- **Hop 2:** The source contract cannot be repaired by a local retry policy.
  - Checked: source_health_registry
  - Found: The selected session has incomplete batches marked complete, so source completeness cannot be trusted. Its published consumer binding identifies where these acknowledgments are used. Follow-up lookup key: lookup_sup_007_234956.
  - Factor `source_reliability`: 0.850 → 0.040
  - Action after hop 2: **monitor** → (dist: 0.7998)
- **Hop 3:** The broad settlement exposure and external dependency require the integration owner.
  - Checked: dependency_graph
  - Found: Five active settlement consumers depend on this binding. The integration policy requires provider reconciliation before any replay, and there is no approved local protocol fallback.
  - Factor `impact_scope`: 0.270 → 0.980
  - Action after hop 3: **escalate_to_owner** ✅ (dist: 0.8550)

- Action: **escalate_to_owner** ✅
- Distance to nearest centroid: 0.8550

**Why VLD changed the decision:** The reference midpoint-centroid scorer selects auto_fix for the surface vector. The ordered investigation updates pattern_familiarity from 0.96 to 0.05, source_reliability from 0.85 to 0.04, impact_scope from 0.27 to 0.98, after which it selects escalate_to_owner. Escalate to the integration owner: the new provider is acknowledging incomplete batches across settlement consumers, the adapter has no safe local repair, and replay requires provider-side confirmation of batch completeness. These are planted synthetic observations available at alert arrival, not observed outcomes of an analyst action.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| data_quality | 0.690 | 0.690 | +0.000 |
| impact_scope | 0.270 | 0.980 | +0.710 ← |
| pattern_familiarity | 0.960 | 0.050 | -0.910 ← |
| schema_stability | 0.700 | 0.700 | +0.000 |
| source_reliability | 0.850 | 0.040 | -0.810 ← |
| transformation_health | 0.610 | 0.610 | +0.000 |
