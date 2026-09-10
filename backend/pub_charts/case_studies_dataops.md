# VLD With-Without Case Studies — DATAOPS
**Generated from Stage 1 multi-hop scenarios**
**[PLANTED POSITIVE CONTROL — not production data]**

## Summary

| Category | Count | % |
|---|---|---|
| VLD saves (SP wrong, VLD right) | 3 | 7% |
| VLD hurts (SP right, VLD wrong) | 1 | 2% |
| Both correct | 18 | 40% |
| Both wrong | 23 | 51% |
| **Total multi-hop** | **45** | |

## Case Studies: VLD Saves

*Scenarios where single-pass gets it wrong and VLD gets it right.*

### Case 1: DO-MH-005-v2
**Type:** recurring_vs_novel
**Kind:** score_keyed | **rho:** 0.9

**Description:** Alert matches a familiar recurring signature; whether the underlying cause is the same is not legible in the evidence.

#### WITHOUT VLD (single-pass)
- Action: **monitor** ❌ (ground truth: escalate_to_owner)
- Based on surface factors only
- Distance to nearest centroid: 0.4026

#### WITH VLD (investigation)
- **Hop 1:** Checked upstream timing: the feed was on time, but the job started fifty minutes late.
  - Checked: BatchJob -> upstream_arrival_times, dependency_count
  - Found: upstream on time; the job itself started 50 minutes late
  - Factor `pattern_familiarity`: 0.880 → 0.440
  - Action after hop 1: **monitor** → (dist: 0.2893)
- **Hop 2:** Checked dependencies: a dependency added on Friday now makes the job wait on a partner feed.
  - Checked: PipelineSystem -> DEPENDS_ON -> DependencyEdge -> added
  - Found: DEP-NEW-0904 added Friday, serialises against a partner feed
  - Factor `source_reliability`: 0.500 → 0.280
  - Action after hop 2: **escalate_to_owner** ✅ (dist: 0.3324)

- Action: **escalate_to_owner** ✅
- Distance to nearest centroid: 0.3324

**Why VLD changed the decision:** Familiar signature, novel cause — a new cross-team dependency needs its owner.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| data_quality | 0.680 | 0.680 | +0.000 |
| impact_scope | 0.580 | 0.580 | +0.000 |
| pattern_familiarity | 0.880 | 0.440 | -0.440 ← |
| schema_stability | 0.780 | 0.780 | +0.000 |
| source_reliability | 0.500 | 0.280 | -0.220 ← |
| transformation_health | 0.720 | 0.720 | +0.000 |

### Case 2: DO-MH-014-v5
**Type:** lakehouse_partition_issue
**Kind:** score_keyed | **rho:** 0.3

**Description:** Reported as pipeline slowness; the fault is on the read side and the alert does not say so.

#### WITHOUT VLD (single-pass)
- Action: **manual_fix** ❌ (ground truth: rollback)
- Based on surface factors only
- Distance to nearest centroid: 0.2952

#### WITH VLD (investigation)
- **Hop 1:** Checked partition layout: the partition key was changed in Tuesday's deploy.
  - Checked: PartitionLayout -> partition_key, changed_at; BatchRun -> finished_within_sla
  - Found: partition key changed in Tuesday's deploy; pipeline on time
  - Factor `schema_stability`: 0.400 → 0.240
  - Action after hop 1: **rollback** ✅ (dist: 0.3661)
- **Hop 2:** Checked prior layout: the previous partitioning is retained and can be switched back.
  - Checked: PartitionLayout -> prior_version, retained
  - Found: prior layout retained and switchable
  - Factor `schema_stability`: 0.240 → 0.320
  - Action after hop 2: **rollback** ✅ (dist: 0.3232)

- Action: **rollback** ✅
- Distance to nearest centroid: 0.3232

**Why VLD changed the decision:** Revert the partition-key change from Tuesday's deploy. Note: the surface signal points at pipeline_runtime_path (misleading) — low-rho instance, and this is the template's canonical wrong direction.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| data_quality | 0.620 | 0.620 | +0.000 |
| impact_scope | 0.540 | 0.540 | +0.000 |
| pattern_familiarity | 0.440 | 0.440 | +0.000 |
| schema_stability | 0.400 | 0.320 | -0.080 ← |
| source_reliability | 0.700 | 0.700 | +0.000 |
| transformation_health | 0.560 | 0.560 | +0.000 |

### Case 3: DO-MH-009-v5
**Type:** schema_migration_window
**Kind:** content_keyed | **rho:** 1.0

**Description:** Validation errors during a schema migration; migration state decides the action.

#### WITHOUT VLD (single-pass)
- Action: **rollback** ❌ (ground truth: auto_fix)
- Based on surface factors only
- Distance to nearest centroid: 0.4224

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


## Cases Where VLD Hurts

*1 scenarios where SP was right but VLD got it wrong.*

### Hurt Case 1: DO-MH-001-v2
- SP: **manual_fix** ✅ | VLD: **rollback** ❌ | GT: manual_fix
- Kind: prerequisite | rho: 1.0
- Why: investigation moved factors in wrong direction
