# VLD With-Without Case Studies — SOC_ASTRA
**Generated from Stage 1 multi-hop scenarios**
**[PLANTED POSITIVE CONTROL — not production data]**

## Summary

| Category | Count | % |
|---|---|---|
| VLD saves (SP wrong, VLD right) | 43 | 96% |
| VLD hurts (SP right, VLD wrong) | 0 | 0% |
| Both correct | 0 | 0% |
| Both wrong | 2 | 4% |
| **Total multi-hop** | **45** | |

## Case Studies: VLD Saves

*Scenarios where single-pass gets it wrong and VLD gets it right.*

### Case 1: SOC-001-v1
**Type:** privilege_chain
**Kind:** score_keyed | **rho:** 0.9

**Description:** A familiar service-account login masks an unauthorized privileged session.

#### WITHOUT VLD (single-pass)
- Action: **suppress** ❌ (ground truth: escalate)
- Based on surface factors only
- Distance to nearest centroid: 0.1816

#### WITH VLD (investigation)
- **Hop 1:** Administrative equivalence is verified through effective grants, not inferred from the account name.
  - Checked: identity_graph
  - Found: SVC-ARCHIVE: nested delegation permits production vault administration; the effective grant is active at alert time.
  - Factor `privileged_identity_context`: 0.214 → 0.995
  - Action after hop 1: **monitor** → (dist: 0.7131)
- **Hop 2:** The account-specific timing conflicts with the authorized execution window.
  - Checked: session_behavior_graph
  - Found: The session-linked behavioral record shows 03:17 Saturday outside the signed weekday backup window; no change exception covers this session.
  - Factor `time_anomaly`: 0.164 → 0.891
  - Action after hop 2: **monitor** → (dist: 0.9000)
- **Hop 3:** Current reachable impact is materially higher than the cached asset label.
  - Checked: asset_data_lineage_graph
  - Found: The grant-scoped resource map confirms the lookup target is the live recovery-key vault, not the low-value backup console.
  - Factor `asset_criticality`: 0.227 → 0.905
  - Action after hop 3: **monitor** → (dist: 1.0336)
- **Hop 4:** Independent device evidence makes the privileged, out-of-window activity an urgent suspected compromise.
  - Checked: device_attestation_graph
  - Found: The originating session endpoint is resolved by certificate fingerprint: the session certificate belongs to an endpoint whose attestation key was revoked before this login.
  - Factor `device_trust`: 0.900 → 0.007
  - Action after hop 4: **escalate** ✅ (dist: 0.7623)

- Action: **escalate** ✅
- Distance to nearest centroid: 0.7623

**Why VLD changed the decision:** The arrival vector is uniquely nearest suppress under the declared reference centroids. The ordered, session-scoped graph reads update privileged_identity_context, time_anomaly, asset_criticality, device_trust. Administrative equivalence is verified through effective grants, not inferred from the account name. The account-specific timing conflicts with the authorized execution window. Current reachable impact is materially higher than the cached asset label. Independent device evidence makes the privileged, out-of-window activity an urgent suspected compromise. The complete enriched vector is uniquely nearest escalate. Every proper subset of these planted factor updates has a different nearest action. This is a synthetic benchmark policy label, not a claim that these six factors exhaust operational SOC judgment.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| asset_criticality | 0.227 | 0.905 | +0.678 ← |
| device_trust | 0.900 | 0.007 | -0.893 ← |
| pattern_history | 0.929 | 0.929 | +0.000 |
| privileged_identity_context | 0.214 | 0.995 | +0.781 ← |
| threat_intel_enrichment | 0.133 | 0.133 | +0.000 |
| time_anomaly | 0.164 | 0.891 | +0.727 ← |

### Case 2: SOC-002-v1
**Type:** privilege_chain
**Kind:** score_keyed | **rho:** 0.7

**Description:** A familiar service-account login masks an unauthorized privileged session.

#### WITHOUT VLD (single-pass)
- Action: **suppress** ❌ (ground truth: escalate)
- Based on surface factors only
- Distance to nearest centroid: 0.2037

#### WITH VLD (investigation)
- **Hop 1:** Administrative equivalence is verified through effective grants, not inferred from the account name.
  - Checked: identity_graph
  - Found: SVC-BUILD: a runner delegation grants release-signing administration; the effective grant is active at alert time.
  - Factor `privileged_identity_context`: 0.217 → 0.985
  - Action after hop 1: **monitor** → (dist: 0.7065)
- **Hop 2:** The account-specific timing conflicts with the authorized execution window.
  - Checked: session_behavior_graph
  - Found: The session-linked behavioral record shows a replay occurred eleven hours after the approved release window closed; no change exception covers this session.
  - Factor `time_anomaly`: 0.165 → 0.921
  - Action after hop 2: **monitor** → (dist: 0.9144)
- **Hop 3:** Current reachable impact is materially higher than the cached asset label.
  - Checked: asset_data_lineage_graph
  - Found: The grant-scoped resource map confirms the discovered signer can authorize every production release.
  - Factor `asset_criticality`: 0.219 → 0.934
  - Action after hop 3: **monitor** → (dist: 1.0600)
- **Hop 4:** Independent device evidence makes the privileged, out-of-window activity an urgent suspected compromise.
  - Checked: device_attestation_graph
  - Found: The originating session endpoint is resolved by certificate fingerprint: the runner image measurement differs from its signed approved image and its device certificate is revoked.
  - Factor `device_trust`: 0.892 → 0.019
  - Action after hop 4: **escalate** ✅ (dist: 0.8060)

- Action: **escalate** ✅
- Distance to nearest centroid: 0.8060

**Why VLD changed the decision:** The arrival vector is uniquely nearest suppress under the declared reference centroids. The ordered, session-scoped graph reads update privileged_identity_context, time_anomaly, asset_criticality, device_trust. Administrative equivalence is verified through effective grants, not inferred from the account name. The account-specific timing conflicts with the authorized execution window. Current reachable impact is materially higher than the cached asset label. Independent device evidence makes the privileged, out-of-window activity an urgent suspected compromise. The complete enriched vector is uniquely nearest escalate. Every proper subset of these planted factor updates has a different nearest action. This is a synthetic benchmark policy label, not a claim that these six factors exhaust operational SOC judgment.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| asset_criticality | 0.219 | 0.934 | +0.715 ← |
| device_trust | 0.892 | 0.019 | -0.873 ← |
| pattern_history | 0.906 | 0.906 | +0.000 |
| privileged_identity_context | 0.217 | 0.985 | +0.768 ← |
| threat_intel_enrichment | 0.077 | 0.077 | +0.000 |
| time_anomaly | 0.165 | 0.921 | +0.756 ← |

### Case 3: SOC-003-v1
**Type:** privilege_chain
**Kind:** score_keyed | **rho:** 0.7

**Description:** A familiar service-account login masks an unauthorized privileged session.

#### WITHOUT VLD (single-pass)
- Action: **suppress** ❌ (ground truth: escalate)
- Based on surface factors only
- Distance to nearest centroid: 0.2039

#### WITH VLD (investigation)
- **Hop 1:** Administrative equivalence is verified through effective grants, not inferred from the account name.
  - Checked: identity_graph
  - Found: SVC-RESTORE: a legacy restore delegation grants tenant-wide recovery administration; the effective grant is active at alert time.
  - Factor `privileged_identity_context`: 0.222 → 0.934
  - Action after hop 1: **monitor** → (dist: 0.7262)
- **Hop 2:** The account-specific timing conflicts with the authorized execution window.
  - Checked: session_behavior_graph
  - Found: The session-linked behavioral record shows the account authenticated during a freeze with no scheduled recovery job; no change exception covers this session.
  - Factor `time_anomaly`: 0.018 → 0.934
  - Action after hop 2: **monitor** → (dist: 0.9017)
- **Hop 3:** Current reachable impact is materially higher than the cached asset label.
  - Checked: asset_data_lineage_graph
  - Found: The grant-scoped resource map confirms the scope includes recovery credentials for the production directory.
  - Factor `asset_criticality`: 0.196 → 0.909
  - Action after hop 3: **monitor** → (dist: 1.0322)
- **Hop 4:** Independent device evidence makes the privileged, out-of-window activity an urgent suspected compromise.
  - Checked: device_attestation_graph
  - Found: The originating session endpoint is resolved by certificate fingerprint: the connection is from an unmanaged clone using a copied managed-host certificate.
  - Factor `device_trust`: 0.970 → 0.057
  - Action after hop 4: **escalate** ✅ (dist: 0.7165)

- Action: **escalate** ✅
- Distance to nearest centroid: 0.7165

**Why VLD changed the decision:** The arrival vector is uniquely nearest suppress under the declared reference centroids. The ordered, session-scoped graph reads update privileged_identity_context, time_anomaly, asset_criticality, device_trust. Administrative equivalence is verified through effective grants, not inferred from the account name. The account-specific timing conflicts with the authorized execution window. Current reachable impact is materially higher than the cached asset label. Independent device evidence makes the privileged, out-of-window activity an urgent suspected compromise. The complete enriched vector is uniquely nearest escalate. Every proper subset of these planted factor updates has a different nearest action. This is a synthetic benchmark policy label, not a claim that these six factors exhaust operational SOC judgment.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| asset_criticality | 0.196 | 0.909 | +0.713 ← |
| device_trust | 0.970 | 0.057 | -0.913 ← |
| pattern_history | 0.834 | 0.834 | +0.000 |
| privileged_identity_context | 0.222 | 0.934 | +0.712 ← |
| threat_intel_enrichment | 0.150 | 0.150 | +0.000 |
| time_anomaly | 0.018 | 0.934 | +0.916 ← |

### Case 4: SOC-004-v1
**Type:** privilege_chain
**Kind:** score_keyed | **rho:** 0.7

**Description:** A familiar service-account login masks an unauthorized privileged session.

#### WITHOUT VLD (single-pass)
- Action: **suppress** ❌ (ground truth: escalate)
- Based on surface factors only
- Distance to nearest centroid: 0.1671

#### WITH VLD (investigation)
- **Hop 1:** Administrative equivalence is verified through effective grants, not inferred from the account name.
  - Checked: identity_graph
  - Found: SVC-CATALOG: nested inherited groups grant identity-directory administration; the effective grant is active at alert time.
  - Factor `privileged_identity_context`: 0.182 → 0.965
  - Action after hop 1: **monitor** → (dist: 0.6889)
- **Hop 2:** The account-specific timing conflicts with the authorized execution window.
  - Checked: session_behavior_graph
  - Found: The session-linked behavioral record shows the login follows the principal-specific schedule by nine hours with no approved exception; no change exception covers this session.
  - Factor `time_anomaly`: 0.124 → 0.876
  - Action after hop 2: **monitor** → (dist: 0.8632)
- **Hop 3:** Current reachable impact is materially higher than the cached asset label.
  - Checked: asset_data_lineage_graph
  - Found: The grant-scoped resource map confirms the resolved resource is the production identity directory rather than its read-only catalog alias.
  - Factor `asset_criticality`: 0.165 → 0.894
  - Action after hop 3: **monitor** → (dist: 0.9847)
- **Hop 4:** Independent device evidence makes the privileged, out-of-window activity an urgent suspected compromise.
  - Checked: device_attestation_graph
  - Found: The originating session endpoint is resolved by certificate fingerprint: the current host has a failed boot attestation and a revoked enrollment identity.
  - Factor `device_trust`: 0.865 → 0.003
  - Action after hop 4: **escalate** ✅ (dist: 0.7123)

- Action: **escalate** ✅
- Distance to nearest centroid: 0.7123

**Why VLD changed the decision:** The arrival vector is uniquely nearest suppress under the declared reference centroids. The ordered, session-scoped graph reads update privileged_identity_context, time_anomaly, asset_criticality, device_trust. Administrative equivalence is verified through effective grants, not inferred from the account name. The account-specific timing conflicts with the authorized execution window. Current reachable impact is materially higher than the cached asset label. Independent device evidence makes the privileged, out-of-window activity an urgent suspected compromise. The complete enriched vector is uniquely nearest escalate. Every proper subset of these planted factor updates has a different nearest action. This is a synthetic benchmark policy label, not a claim that these six factors exhaust operational SOC judgment.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| asset_criticality | 0.165 | 0.894 | +0.729 ← |
| device_trust | 0.865 | 0.003 | -0.862 ← |
| pattern_history | 0.881 | 0.881 | +0.000 |
| privileged_identity_context | 0.182 | 0.965 | +0.783 ← |
| threat_intel_enrichment | 0.158 | 0.158 | +0.000 |
| time_anomaly | 0.124 | 0.876 | +0.752 ← |

### Case 5: SOC-005-v1
**Type:** privilege_chain
**Kind:** score_keyed | **rho:** 0.7

**Description:** A familiar service-account login masks an unauthorized privileged session.

#### WITHOUT VLD (single-pass)
- Action: **suppress** ❌ (ground truth: escalate)
- Based on surface factors only
- Distance to nearest centroid: 0.2867

#### WITH VLD (investigation)
- **Hop 1:** Administrative equivalence is verified through effective grants, not inferred from the account name.
  - Checked: identity_graph
  - Found: SVC-DEPLOY: a deployment delegation grants production cluster administration; the effective grant is active at alert time.
  - Factor `privileged_identity_context`: 0.117 → 0.967
  - Action after hop 1: **monitor** → (dist: 0.7978)
- **Hop 2:** The account-specific timing conflicts with the authorized execution window.
  - Checked: session_behavior_graph
  - Found: The session-linked behavioral record shows authentication occurred after the temporary deployment identity should have expired; no change exception covers this session.
  - Factor `time_anomaly`: 0.027 → 0.992
  - Action after hop 2: **monitor** → (dist: 1.0010)
- **Hop 3:** Current reachable impact is materially higher than the cached asset label.
  - Checked: asset_data_lineage_graph
  - Found: The grant-scoped resource map confirms the reachable control plane administers all production workloads.
  - Factor `asset_criticality`: 0.113 → 0.939
  - Action after hop 3: **monitor** → (dist: 1.1183)
- **Hop 4:** Independent device evidence makes the privileged, out-of-window activity an urgent suspected compromise.
  - Checked: device_attestation_graph
  - Found: The originating session endpoint is resolved by certificate fingerprint: a signed endpoint check reports a cloned device identity and failed hardware binding.
  - Factor `device_trust`: 0.984 → 0.093
  - Action after hop 4: **escalate** ✅ (dist: 0.8470)

- Action: **escalate** ✅
- Distance to nearest centroid: 0.8470

**Why VLD changed the decision:** The arrival vector is uniquely nearest suppress under the declared reference centroids. The ordered, session-scoped graph reads update privileged_identity_context, time_anomaly, asset_criticality, device_trust. Administrative equivalence is verified through effective grants, not inferred from the account name. The account-specific timing conflicts with the authorized execution window. Current reachable impact is materially higher than the cached asset label. Independent device evidence makes the privileged, out-of-window activity an urgent suspected compromise. The complete enriched vector is uniquely nearest escalate. Every proper subset of these planted factor updates has a different nearest action. This is a synthetic benchmark policy label, not a claim that these six factors exhaust operational SOC judgment.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| asset_criticality | 0.113 | 0.939 | +0.826 ← |
| device_trust | 0.984 | 0.093 | -0.891 ← |
| pattern_history | 0.856 | 0.856 | +0.000 |
| privileged_identity_context | 0.117 | 0.967 | +0.850 ← |
| threat_intel_enrichment | 0.037 | 0.037 | +0.000 |
| time_anomaly | 0.027 | 0.992 | +0.965 ← |

### Case 6: SOC-006-v1
**Type:** benign_device_malicious_campaign
**Kind:** score_keyed | **rho:** 0.7

**Description:** Routine activity on an apparently managed device conceals a synthetic campaign-linked session.

#### WITHOUT VLD (single-pass)
- Action: **monitor** ❌ (ground truth: escalate)
- Based on surface factors only
- Distance to nearest centroid: 0.1736

#### WITH VLD (investigation)
- **Hop 1:** Specific session artifacts corroborate a campaign match; no real campaign attribution is claimed.
  - Checked: threat_intelligence_graph
  - Found: Alert-session correlation confirms the exact session redirector certificate matches synthetic campaign SYN-ORCHID and its credential replay chain; this is a planted intelligence record available before arrival.
  - Factor `threat_intel_enrichment`: 0.295 → 0.888
  - Action after hop 1: **monitor** → (dist: 0.6904)
- **Hop 2:** Trust is corrected from current session evidence rather than asset inventory alone.
  - Checked: device_attestation_graph
  - Found: The campaign-linked device fingerprint resolves to a current attestation record: hardware binding failed for the session device although the inventory still lists it as managed.
  - Factor `device_trust`: 0.736 → 0.041
  - Action after hop 2: **escalate** ✅ (dist: 0.7576)
- **Hop 3:** The session has direct access to a high-impact resource.
  - Checked: asset_data_lineage_graph
  - Found: The session resource lineage shows the session can reach the production identity recovery console.
  - Factor `asset_criticality`: 0.320 → 0.766
  - Action after hop 3: **escalate** ✅ (dist: 0.5051)
- **Hop 4:** The combined intelligence, device, impact, and timing facts justify urgent escalation.
  - Checked: session_behavior_graph
  - Found: The resource-scoped schedule shows session refreshes recur at 02:40 outside this principalâ€™s established work interval.
  - Factor `time_anomaly`: 0.236 → 0.763
  - Action after hop 4: **escalate** ✅ (dist: 0.4193)

- Action: **escalate** ✅
- Distance to nearest centroid: 0.4193

**Why VLD changed the decision:** The arrival vector is uniquely nearest monitor under the declared reference centroids. The ordered, session-scoped graph reads update threat_intel_enrichment, device_trust, asset_criticality, time_anomaly. Specific session artifacts corroborate a campaign match; no real campaign attribution is claimed. Trust is corrected from current session evidence rather than asset inventory alone. The session has direct access to a high-impact resource. The combined intelligence, device, impact, and timing facts justify urgent escalation. The complete enriched vector is uniquely nearest escalate. Every proper subset of these planted factor updates has a different nearest action. This is a synthetic benchmark policy label, not a claim that these six factors exhaust operational SOC judgment.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| asset_criticality | 0.320 | 0.766 | +0.446 ← |
| device_trust | 0.736 | 0.041 | -0.695 ← |
| pattern_history | 0.815 | 0.815 | +0.000 |
| privileged_identity_context | 0.429 | 0.429 | +0.000 |
| threat_intel_enrichment | 0.295 | 0.888 | +0.593 ← |
| time_anomaly | 0.236 | 0.763 | +0.527 ← |

### Case 7: SOC-007-v1
**Type:** benign_device_malicious_campaign
**Kind:** score_keyed | **rho:** 1.0

**Description:** Routine activity on an apparently managed device conceals a synthetic campaign-linked session.

#### WITHOUT VLD (single-pass)
- Action: **monitor** ❌ (ground truth: escalate)
- Based on surface factors only
- Distance to nearest centroid: 0.2590

#### WITH VLD (investigation)
- **Hop 1:** Specific session artifacts corroborate a campaign match; no real campaign attribution is claimed.
  - Checked: threat_intelligence_graph
  - Found: Alert-session correlation confirms the destination certificate and service identifier jointly match synthetic campaign SYN-BRIDGE; this is a planted intelligence record available before arrival.
  - Factor `threat_intel_enrichment`: 0.200 → 0.967
  - Action after hop 1: **monitor** → (dist: 0.7952)
- **Hop 2:** Trust is corrected from current session evidence rather than asset inventory alone.
  - Checked: device_attestation_graph
  - Found: The campaign-linked device fingerprint resolves to a current attestation record: endpoint attestation associates the live process with a cloned enrollment identity.
  - Factor `device_trust`: 0.814 → 0.249
  - Action after hop 2: **investigate** → (dist: 0.8029)
- **Hop 3:** The session has direct access to a high-impact resource.
  - Checked: asset_data_lineage_graph
  - Found: The session resource lineage shows the lateral destination is the production orchestration controller.
  - Factor `asset_criticality`: 0.274 → 0.750
  - Action after hop 3: **escalate** ✅ (dist: 0.5935)
- **Hop 4:** The combined intelligence, device, impact, and timing facts justify urgent escalation.
  - Checked: session_behavior_graph
  - Found: The resource-scoped schedule shows the session begins after the signed maintenance window ended.
  - Factor `time_anomaly`: 0.160 → 0.755
  - Action after hop 4: **escalate** ✅ (dist: 0.4611)

- Action: **escalate** ✅
- Distance to nearest centroid: 0.4611

**Why VLD changed the decision:** The arrival vector is uniquely nearest monitor under the declared reference centroids. The ordered, session-scoped graph reads update threat_intel_enrichment, device_trust, asset_criticality, time_anomaly. Specific session artifacts corroborate a campaign match; no real campaign attribution is claimed. Trust is corrected from current session evidence rather than asset inventory alone. The session has direct access to a high-impact resource. The combined intelligence, device, impact, and timing facts justify urgent escalation. The complete enriched vector is uniquely nearest escalate. Every proper subset of these planted factor updates has a different nearest action. This is a synthetic benchmark policy label, not a claim that these six factors exhaust operational SOC judgment.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| asset_criticality | 0.274 | 0.750 | +0.476 ← |
| device_trust | 0.814 | 0.249 | -0.565 ← |
| pattern_history | 0.688 | 0.688 | +0.000 |
| privileged_identity_context | 0.426 | 0.426 | +0.000 |
| threat_intel_enrichment | 0.200 | 0.967 | +0.767 ← |
| time_anomaly | 0.160 | 0.755 | +0.595 ← |

### Case 8: SOC-008-v1
**Type:** benign_device_malicious_campaign
**Kind:** score_keyed | **rho:** 1.0

**Description:** Routine activity on an apparently managed device conceals a synthetic campaign-linked session.

#### WITHOUT VLD (single-pass)
- Action: **monitor** ❌ (ground truth: escalate)
- Based on surface factors only
- Distance to nearest centroid: 0.2027

#### WITH VLD (investigation)
- **Hop 1:** Specific session artifacts corroborate a campaign match; no real campaign attribution is claimed.
  - Checked: threat_intelligence_graph
  - Found: Alert-session correlation confirms the flow destination and payload marker match synthetic campaign SYN-CINDER staging telemetry; this is a planted intelligence record available before arrival.
  - Factor `threat_intel_enrichment`: 0.306 → 0.922
  - Action after hop 1: **monitor** → (dist: 0.7298)
- **Hop 2:** Trust is corrected from current session evidence rather than asset inventory alone.
  - Checked: device_attestation_graph
  - Found: The campaign-linked device fingerprint resolves to a current attestation record: the active host measurement is unapproved and its device certificate has been revoked.
  - Factor `device_trust`: 0.674 → 0.005
  - Action after hop 2: **escalate** ✅ (dist: 0.8063)
- **Hop 3:** The session has direct access to a high-impact resource.
  - Checked: asset_data_lineage_graph
  - Found: The session resource lineage shows the process holds a handle to the protected design archive.
  - Factor `asset_criticality`: 0.318 → 0.775
  - Action after hop 3: **escalate** ✅ (dist: 0.5714)
- **Hop 4:** The combined intelligence, device, impact, and timing facts justify urgent escalation.
  - Checked: session_behavior_graph
  - Found: The resource-scoped schedule shows the transfer starts in a blackout period with no matching export job.
  - Factor `time_anomaly`: 0.154 → 0.648
  - Action after hop 4: **escalate** ✅ (dist: 0.3935)

- Action: **escalate** ✅
- Distance to nearest centroid: 0.3935

**Why VLD changed the decision:** The arrival vector is uniquely nearest monitor under the declared reference centroids. The ordered, session-scoped graph reads update threat_intel_enrichment, device_trust, asset_criticality, time_anomaly. Specific session artifacts corroborate a campaign match; no real campaign attribution is claimed. Trust is corrected from current session evidence rather than asset inventory alone. The session has direct access to a high-impact resource. The combined intelligence, device, impact, and timing facts justify urgent escalation. The complete enriched vector is uniquely nearest escalate. Every proper subset of these planted factor updates has a different nearest action. This is a synthetic benchmark policy label, not a claim that these six factors exhaust operational SOC judgment.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| asset_criticality | 0.318 | 0.775 | +0.457 ← |
| device_trust | 0.674 | 0.005 | -0.669 ← |
| pattern_history | 0.761 | 0.761 | +0.000 |
| privileged_identity_context | 0.428 | 0.428 | +0.000 |
| threat_intel_enrichment | 0.306 | 0.922 | +0.616 ← |
| time_anomaly | 0.154 | 0.648 | +0.494 ← |
