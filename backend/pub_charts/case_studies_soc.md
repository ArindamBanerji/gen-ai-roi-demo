# VLD With-Without Case Studies — SOC
**Generated from Stage 1 multi-hop scenarios**
**[PLANTED POSITIVE CONTROL — not production data]**

## Summary

| Category | Count | % |
|---|---|---|
| VLD saves (SP wrong, VLD right) | 12 | 27% |
| VLD hurts (SP right, VLD wrong) | 2 | 4% |
| Both correct | 19 | 42% |
| Both wrong | 12 | 27% |
| **Total multi-hop** | **45** | |

## Case Studies: VLD Saves

*Scenarios where single-pass gets it wrong and VLD gets it right.*

### Case 1: SOC-MH-001-v3
**Type:** credential_lateral_compound
**Kind:** score_keyed | **rho:** 0.7

**Description:** Credential and process anomalies compete; which is primary determines the action.

#### WITHOUT VLD (single-pass)
- Action: **suppress** ❌ (ground truth: monitor)
- Based on surface factors only
- Distance to nearest centroid: 0.1949

#### WITH VLD (investigation)
- **Hop 1:** Checked auth trail: the burst is single-sign-on token re-issue, not credential stuffing.
  - Checked: User node -> AuthTrail node -> distinct_hosts, sso_reissue
  - Found: SSO token re-issue burst, no failures
  - Factor `privileged_identity_context`: 0.620 → 0.350
  - Action after hop 1: **monitor** ✅ (dist: 0.3051)

- Action: **monitor** ✅
- Distance to nearest centroid: 0.3051

**Why VLD changed the decision:** Credential burst has a benign explanation; no process anomaly to chase.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| asset_criticality | 0.580 | 0.580 | +0.000 |
| device_trust | 0.710 | 0.710 | +0.000 |
| pattern_history | 0.440 | 0.440 | +0.000 |
| privileged_identity_context | 0.620 | 0.350 | -0.270 ← |
| threat_intel_enrichment | 0.090 | 0.090 | +0.000 |
| time_anomaly | 0.310 | 0.310 | +0.000 |

### Case 2: SOC-MH-001-v4
**Type:** credential_lateral_compound
**Kind:** score_keyed | **rho:** 1.0

**Description:** Credential and process anomalies compete; which is primary determines the action.

#### WITHOUT VLD (single-pass)
- Action: **investigate** ❌ (ground truth: suppress)
- Based on surface factors only
- Distance to nearest centroid: 0.5736

#### WITH VLD (investigation)
- **Hop 1:** Checked process tree: the binary is the signed management agent from a managed deployment.
  - Checked: Alert -> Process node -> image, signed, deployment_id
  - Found: signed sccm-agent.exe from managed deployment
  - Factor `pattern_history`: 0.880 → 0.150
  - Action after hop 1: **suppress** ✅ (dist: 0.3463)

- Action: **suppress** ✅
- Distance to nearest centroid: 0.3463

**Why VLD changed the decision:** Sanctioned management tooling; both vectors resolve benign at the first read.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| asset_criticality | 0.550 | 0.550 | +0.000 |
| device_trust | 0.830 | 0.830 | +0.000 |
| pattern_history | 0.880 | 0.150 | -0.730 ← |
| privileged_identity_context | 0.350 | 0.350 | +0.000 |
| threat_intel_enrichment | 0.060 | 0.060 | +0.000 |
| time_anomaly | 0.240 | 0.240 | +0.000 |

### Case 3: SOC-MH-002-v2
**Type:** insider_vs_compromised
**Kind:** score_keyed | **rho:** 0.9

**Description:** Credential anomaly with identical surface indicators under both hypotheses; the branch is not legible in the evidence.

#### WITHOUT VLD (single-pass)
- Action: **monitor** ❌ (ground truth: suppress)
- Based on surface factors only
- Distance to nearest centroid: 0.2228

#### WITH VLD (investigation)
- **Hop 1:** Checked employment context: no employment change on record.
  - Checked: User -> EmploymentContext -> status
  - Found: active, no employment change
  - Factor `pattern_history`: 0.550 → 0.520
  - Action after hop 1: **monitor** → (dist: 0.2127)
- **Hop 2:** Checked peer baseline: the whole cohort is at the same percentile — a team archive migration.
  - Checked: PeerCohort -> subject_percentile, cohort_shift
  - Found: cohort-wide p95 this week — archive migration
  - Factor `pattern_history`: 0.520 → 0.180
  - Action after hop 2: **suppress** ✅ (dist: 0.2543)

- Action: **suppress** ✅
- Distance to nearest centroid: 0.2543

**Why VLD changed the decision:** The volume is normal for the cohort; the anomaly is against a stale baseline.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| asset_criticality | 0.600 | 0.600 | +0.000 |
| device_trust | 0.660 | 0.660 | +0.000 |
| pattern_history | 0.550 | 0.180 | -0.370 ← |
| privileged_identity_context | 0.680 | 0.680 | +0.000 |
| threat_intel_enrichment | 0.080 | 0.080 | +0.000 |
| time_anomaly | 0.500 | 0.500 | +0.000 |

### Case 4: SOC-MH-002-v5
**Type:** insider_vs_compromised
**Kind:** score_keyed | **rho:** 0.3

**Description:** Credential anomaly with identical surface indicators under both hypotheses; the branch is not legible in the evidence.

#### WITHOUT VLD (single-pass)
- Action: **investigate** ❌ (ground truth: escalate)
- Based on surface factors only
- Distance to nearest centroid: 0.4567

#### WITH VLD (investigation)
- **Hop 1:** Checked device session: the token was replayed from an unregistered device.
  - Checked: User -> DeviceSession -> device_registered, token_replay
  - Found: unregistered device, replayed token
  - Factor `device_trust`: 0.220 → 0.090
  - Action after hop 1: **escalate** ✅ (dist: 0.5414)
- **Hop 2:** Checked token provenance: the token was issued to another endpoint six hours earlier.
  - Checked: DeviceSession -> TokenProvenance -> issued_to, issued_at
  - Found: token issued to a different endpoint 6h earlier
  - Factor `device_trust`: 0.090 → 0.050
  - Action after hop 2: **escalate** ✅ (dist: 0.5692)

- Action: **escalate** ✅
- Distance to nearest centroid: 0.5692

**Why VLD changed the decision:** Session hijack, not insider activity — same indicators, security-led route. Note: the surface signal points at asset_scope_path (misleading) — low-rho instance where the routing signal is wrong.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| asset_criticality | 0.640 | 0.640 | +0.000 |
| device_trust | 0.220 | 0.050 | -0.170 ← |
| pattern_history | 0.350 | 0.350 | +0.000 |
| privileged_identity_context | 0.700 | 0.700 | +0.000 |
| threat_intel_enrichment | 0.140 | 0.140 | +0.000 |
| time_anomaly | 0.580 | 0.580 | +0.000 |

### Case 5: SOC-MH-008-v2
**Type:** cloud_misconfig_vs_attack
**Kind:** score_keyed | **rho:** 0.9

**Description:** Identical CloudTrail policy-modification event; deployment or attack is not stated in the evidence.

#### WITHOUT VLD (single-pass)
- Action: **monitor** ❌ (ground truth: suppress)
- Based on surface factors only
- Distance to nearest centroid: 0.6177

#### WITH VLD (investigation)
- **Hop 1:** Checked API sequence: the calls match a Terraform apply with a matching deploy record.
  - Checked: ApiSequence -> signature, deploy_record_id
  - Found: terraform_apply signature, deploy DEP-2291
  - Factor `pattern_history`: 0.860 → 0.120
  - Action after hop 1: **suppress** ✅ (dist: 0.4568)

- Action: **suppress** ✅
- Distance to nearest centroid: 0.4568

**Why VLD changed the decision:** Infrastructure-as-code deployment with a matching deploy record.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| asset_criticality | 0.900 | 0.900 | +0.000 |
| device_trust | 0.780 | 0.780 | +0.000 |
| pattern_history | 0.860 | 0.120 | -0.740 ← |
| privileged_identity_context | 0.800 | 0.800 | +0.000 |
| threat_intel_enrichment | 0.040 | 0.040 | +0.000 |
| time_anomaly | 0.620 | 0.620 | +0.000 |

### Case 6: SOC-MH-013-v2
**Type:** service_account_automated_vs_hijacked
**Kind:** score_keyed | **rho:** 0.9

**Description:** Elevated service account with no human identity; automation and hijack present the same surface.

#### WITHOUT VLD (single-pass)
- Action: **monitor** ❌ (ground truth: suppress)
- Based on surface factors only
- Distance to nearest centroid: 0.5718

#### WITH VLD (investigation)
- **Hop 1:** Checked the scheduler: the activity falls inside the nightly ETL window.
  - Checked: ServiceAccount -> ScheduledJob -> cron, matches_activity
  - Found: matches the 02:00 nightly ETL window
  - Factor `pattern_history`: 0.850 → 0.100
  - Action after hop 1: **suppress** ✅ (dist: 0.3528)

- Action: **suppress** ✅
- Distance to nearest centroid: 0.3528

**Why VLD changed the decision:** The activity is the scheduled automation.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| asset_criticality | 0.680 | 0.680 | +0.000 |
| device_trust | 0.800 | 0.800 | +0.000 |
| pattern_history | 0.850 | 0.100 | -0.750 ← |
| privileged_identity_context | 0.880 | 0.880 | +0.000 |
| threat_intel_enrichment | 0.030 | 0.030 | +0.000 |
| time_anomaly | 0.300 | 0.300 | +0.000 |

### Case 7: SOC-MH-013-v3
**Type:** service_account_automated_vs_hijacked
**Kind:** score_keyed | **rho:** 0.7

**Description:** Elevated service account with no human identity; automation and hijack present the same surface.

#### WITHOUT VLD (single-pass)
- Action: **monitor** ❌ (ground truth: investigate)
- Based on surface factors only
- Distance to nearest centroid: 0.4199

#### WITH VLD (investigation)
- **Hop 1:** Checked the scheduler: the job ran four hours outside its window.
  - Checked: ServiceAccount -> ScheduledJob -> cron, last_run_at
  - Found: job exists but ran 4h outside its window
  - Factor `pattern_history`: 0.600 → 0.620
  - Action after hop 1: **monitor** → (dist: 0.4268)
- **Hop 2:** Checked the command profile: the commands are the usual ETL batch.
  - Checked: ServiceAccount -> CommandProfile -> profile
  - Found: normal batch ETL commands
  - Factor `privileged_identity_context`: 0.890 → 0.450
  - Action after hop 2: **investigate** ✅ (dist: 0.3047)

- Action: **investigate** ✅
- Distance to nearest centroid: 0.3047

**Why VLD changed the decision:** Right work at the wrong time — likely a scheduler fault, but out-of-band execution needs confirming.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| asset_criticality | 0.690 | 0.690 | +0.000 |
| device_trust | 0.660 | 0.660 | +0.000 |
| pattern_history | 0.600 | 0.620 | +0.020 |
| privileged_identity_context | 0.890 | 0.450 | -0.440 ← |
| threat_intel_enrichment | 0.060 | 0.060 | +0.000 |
| time_anomaly | 0.580 | 0.580 | +0.000 |

### Case 8: SOC-MH-004-v1
**Type:** maintenance_window_false_positive
**Kind:** content_keyed | **rho:** 1.0

**Description:** Off-hours privileged configuration change; change-management state decides the action.

#### WITHOUT VLD (single-pass)
- Action: **monitor** ❌ (ground truth: suppress)
- Based on surface factors only
- Distance to nearest centroid: 0.5945

#### WITH VLD (investigation)
- **Hop 1:** Checked change management: CR-2026-0912 active 02:00-04:00, scope matches.
  - Checked: CloudResource -> ChangeRequest -> status, window_start, window_end, approver
  - Found: CR-2026-0912 active 02:00-04:00, scope matches
  - Factor `time_anomaly`: 0.880 → 0.120
  - Action after hop 1: **suppress** ✅ (dist: 0.3005)

- Action: **suppress** ✅
- Distance to nearest centroid: 0.3005

**Why VLD changed the decision:** Off-hours config change inside an approved maintenance window with a named approver.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| asset_criticality | 0.770 | 0.770 | +0.000 |
| device_trust | 0.700 | 0.700 | +0.000 |
| pattern_history | 0.300 | 0.300 | +0.000 |
| privileged_identity_context | 0.810 | 0.810 | +0.000 |
| threat_intel_enrichment | 0.050 | 0.050 | +0.000 |
| time_anomaly | 0.880 | 0.120 | -0.760 ← |


## Cases Where VLD Hurts

*2 scenarios where SP was right but VLD got it wrong.*

### Hurt Case 1: SOC-MH-002-v3
- SP: **monitor** ✅ | VLD: **suppress** ❌ | GT: monitor
- Kind: score_keyed | rho: 0.7
- Why: investigation moved factors in wrong direction

### Hurt Case 2: SOC-MH-004-v4
- SP: **monitor** ✅ | VLD: **suppress** ❌ | GT: monitor
- Kind: content_keyed | rho: 1.0
- Why: investigation moved factors in wrong direction
