# SOC Copilot — Technology Realization Code Analysis

**Date:** February 27, 2026
**Analyst:** Claude (Opus-class analysis)
**Scope:** Complete code trace across all 5 sections requested
**Reference:** `docs/technology_realization_gap_analysis.md` v1.0

---

## SECTION 1: ANALYSIS PATH — POST /api/alert/analyze Data Flow

### 1.1 Entry Point: `backend/app/routers/triage.py:86-188`

```
POST /api/alert/analyze
  → neo4j_client.get_alert(alert_id)           # Step 1: fetch alert props
  → neo4j_client.get_security_context(alert_id) # Step 2: "47 nodes"
  → analyze_situation(alert_type, context)       # Step 3: situation classification
  → agent.decide(alert_type, context)            # Step 4: rule-based decision
  → narrator.generate_reasoning(...)             # Step 4b: LLM narration
  → append_confidence_snapshot(...)              # Step 4c: trajectory tracking
  → get_graph_data(alert_id)                     # Step 5: viz data
  → generate_narrative(response)                 # Step 6: template narrative
  → return response
```

### 1.2 Step 2: `get_security_context()` — `backend/app/db/neo4j.py:54-137`

**What the blog claims:** "47 nodes consulted" from unified semantic layer with embeddings.

**What actually happens:**
- Fixed Cypher query traverses: `Alert → Asset`, `Alert → User`, `Alert → AlertType`, `AlertType → Playbook`, `User → TravelContext`, `Asset → SLA`, `Alert → AttackPattern`
- Node count: `base_nodes + 39` — **the +39 is a hardcoded constant** (line 86: `base_nodes + 39 as nodes_consulted // Fixed at 47 for demo consistency`)
- Returns a flat dictionary of string/float properties extracted from graph node attributes
- **No embeddings.** Context is property extraction, not vector computation.

**Gap:** The "47 nodes" is a display number. The actual traversal hits 5-8 nodes depending on OPTIONAL MATCH results. The padded constant ensures the UI always shows 47.

### 1.3 Step 3: `analyze_situation()` — `backend/app/services/situation.py:193-235`

**What the blog claims:** Situation Analyzer classifies via learned patterns using scoring matrix P(action|alert) = softmax(f · Wᵀ / τ).

**What actually happens:**
1. `classify_situation(alert_type, context)` → delegates to `classify_soc_situation()` in `domains/soc/situations.py:194-372`
2. Classification is a **cascade of if-else rules** checking `alert_type` string and context dict keys:
   - `alert_type == "anomalous_login" and context.get("user_traveling")` → `"travel_login_anomaly"`, confidence=0.94
   - `alert_type == "phishing"` → `"known_phishing_campaign"`, confidence=0.96 or 0.72
   - ... 13 total rules, each returning a **hardcoded confidence float**
3. `evaluate_options(alert_type, context, situation_type)` → delegates to `get_soc_options()` in `domains/soc/situations.py:788-797`
4. Options are **static dictionaries** from `SOC_OPTIONS` — a literal Python dict keyed by situation type string. Each option has hardcoded score, factors list, resolution time, analyst cost, and risk label.
5. `calculate_decision_economics()` — compares the selected option against the most expensive human option. All input numbers (time, cost) come from the hardcoded option dicts. The "monthly projection" uses a fixed 200 alerts/month assumption.

**Gap severity: CRITICAL.** There is no scoring matrix. No factor vector f. No weight matrix W. No softmax. No temperature τ. The "scores" in SOC_OPTIONS (e.g., 0.92, 0.06, 0.02 for travel_login_anomaly) are hardcoded constants, not computed from f · Wᵀ.

### 1.4 Step 4: `agent.decide()` — `backend/app/services/agent.py:45-178`

**What actually happens:**
- Pure if-else cascade on `alert_type` string + context dict keys
- 4 primary rules: anomalous_login (with travel sub-rules), phishing, malware_detection, data_exfiltration
- Returns `DecisionResult(action, confidence, pattern_id, playbook_id)` — all hardcoded values
- Example: travel + vpn + mfa + device → `false_positive_close`, confidence=0.92, pattern="PAT-TRAVEL-001"

**Key observation:** `situation.py` and `agent.py` make **independent decisions** from the same context. The situation analyzer and the agent don't share a scoring pipeline. They happen to agree because both are hardcoded to the same outcomes.

### 1.5 Factor Breakdown: `get_decision_factors()` — `backend/app/services/triage.py:239-268`

**What the blog claims:** 6-factor scoring matrix where factors are COMPUTED from graph traversal.

**What actually happens:**
1. Lookup order: `SOC_FACTOR_TEMPLATES.get(alert_id)` → `SOC_FACTOR_TEMPLATES.get(alert_type)` → `SOC_FACTOR_TEMPLATES["_default"]` — all in `domains/soc/factors.py:37-491`
2. Templates are **literal dictionaries** with hardcoded `value`, `weight`, and `explanation` for 5 factors per alert
3. The 6th factor (threat_intel_enrichment) is the **only computed factor** — it queries Neo4j for `(ThreatIntel)-[:ASSOCIATED_WITH]->(Alert)` nodes written by the Pulsedive connector
4. `_contribution(value, weight)` → `value * weight` → threshold-based label ("high"/"medium"/"low"/"none")
5. The response includes `decision_method: "softmax scoring matrix (6 factors × 4 actions)"` — **this is a string label, not a description of actual computation**

**Gap severity: CRITICAL.** 5 of 6 factors are dictionary lookups, not graph-computed values. The `weights_note` says "Weights calibrate automatically through verified outcomes (Loop 2 + Loop 3)" — but no calibration code exists.

### 1.6 Narrative: `generate_narrative()` — `backend/app/services/narrative.py:219-294`

**What the blog claims:** LLM-powered reasoning over graph context.

**What actually happens:**
- Template-based string construction (line 8: "Template-based, NOT LLM-generated. Deterministic and fast.")
- 5 sentences built from dictionary lookups and string formatting
- `_FACTOR_LABELS`, `_ACTION_LABELS`, `_THREAT_INTEL_FACTORS` are all static dicts
- No LLM call. No Gemini/GPT API usage in this path.

**Note:** The `narrator.generate_reasoning()` call in Step 4 DOES use an LLM (Gemini via Vertex AI), but only for the `reasoning` field in the recommendation panel. The `narrative` field (the investigation summary) is purely template-based.

---

## SECTION 2: FEEDBACK + LEARNING PATH

### 2.1 Feedback Entry: `POST /api/alert/outcome` — `routers/triage.py:385-433`

```
POST /api/alert/outcome {alert_id, decision_id, outcome}
  → get_feedback_status(alert_id)   # idempotency check
  → process_outcome(alert_id, decision_id, outcome)  # core update
  → return OutcomeResponse
```

### 2.2 `process_outcome()` — `backend/app/services/feedback.py:79-234`

**What the blog claims:** Eq. 4b: W[a,:] ← W[a,:] + α · r(t) · f(t) · δ(t) — Hebbian-style weight updates.

**What actually happens:**
1. **Alert → pattern mapping is hardcoded** (lines 96-108): `"7823" in alert_id` → PAT-TRAVEL-001, `"7824"` → PAT-PHISH-001
2. **Correct outcome:**
   - `PATTERN_CONFIDENCE[pattern_id] += 0.003` (cap 0.99)
   - `EDGE_WEIGHTS[edge_key] += 0.02` (cap 0.99)
   - `PRECEDENT_COUNTS[pattern_id] += 1`
3. **Incorrect outcome:**
   - `PATTERN_CONFIDENCE[pattern_id] -= 0.06` (floor 0.50)
   - `EDGE_WEIGHTS[edge_key] -= 0.05` (floor 0.50)
   - Sets `next_alerts_override`: route next 5 to Tier 2
4. **Trust update** (F6a): `update_trust(situation_type, outcome)` — correct: +0.03, incorrect: -0.60

**Gap severity: CRITICAL.**
- No weight matrix W. `PATTERN_CONFIDENCE` and `EDGE_WEIGHTS` are scalar floats in Python dicts, not numpy arrays.
- No factor vector f(t). The update ignores which factors contributed to the decision.
- No actual Hebbian rule. The delta is fixed (+0.003 or -0.06), not proportional to the reward signal r(t) or the feature activation f(t).
- The 20:1 asymmetry EXISTS but only in the trust counter (+0.03 / -0.60), not in the weight matrix.
- `EDGE_WEIGHTS` is a cosmetic state — no downstream code reads these weights to influence future decisions.

### 2.3 Agent Evolver: `backend/app/services/evolver.py`

**What the blog claims:** Loop 2 — smarter ACROSS decisions. Prompt variant evolution with real A/B testing.

**What actually happens:**
1. `PROMPT_STATS` — 4 hardcoded prompt variant entries with pre-seeded success/total/rate
2. `record_decision_outcome(decision_id, prompt_variant, success)`:
   - Increments `stats["total"] += 1`, conditionally `stats["success"] += 1`
   - Recalculates `success_rate = success / total`
   - Appends snapshot to `WEIGHT_HISTORY`
3. `check_for_promotion(alert_type)`:
   - Finds family variants (shared prefix), compares success rates
   - Promotes if >5% improvement AND >10 samples
   - This is a **real A/B promotion mechanism** — one of the few computed behaviors
4. `calculate_operational_impact()`:
   - `improvement_pct = (new_rate - old_rate) * 100`
   - `fewer_escalations = 200 * (new_rate - old_rate)`
   - Dollar savings at $127/review, 45 min/review
   - **Hardcoded assumptions** but math is real

**Partial realization:** The evolver tracks real counts and promotes real variants. But:
- "Prompt variants" don't correspond to actual different prompts — there's no prompt template system
- Success is defined as "eval gates passed" (which almost always passes), not verified outcome
- The variant name (e.g., "TRAVEL_CONTEXT_v2") is a label, not an actual prompt that generated different behavior

### 2.4 Trust Tracking: `backend/app/services/feedback.py:312-486`

**What actually happens:**
- `TRUST_SCORES` dict: situation_type → float (0.0–1.0)
- `update_trust()`: correct +0.03, incorrect -0.60 (20:1 ratio)
- `LOW_TRUST_FLAGS`: set True when trust < 0.3
- `human_review_required` flag per situation type

**Assessment:** This is a legitimate counter-based trust signal. The 20:1 asymmetry is real and produces dramatic visual effects on the Trust Curve chart. But:
- The flag is **never read** by the decision engine. `agent.decide()` and `situation.py` do not check `LOW_TRUST_FLAGS`.
- The trust score doesn't gate automation. Even when trust < 0.3, the agent still makes the same decision.

### 2.5 Reward Summary: `get_reward_summary()` — `feedback.py:281-305`

- `cumulative_r_t = correct * 0.3 + incorrect * (-6.0)`
- Returns `loop3_status: "active" | "insufficient_data"`
- **Display-only.** The cumulative reward does not feed back into any scoring computation.

---

## SECTION 3: PRE-SEEDED DATA INVENTORY

### 3.1 `evolver.py` — Weight History Seeds

**Location:** `seed_weight_history()`, lines 437-485

| # | Data Points | Description |
|---|-------------|-------------|
| 15 | WEIGHT_HISTORY snapshots | TRAVEL_CONTEXT_v2 rises 0.65→0.90 (winner), TC_v1 flat ~0.71, phishing variants 0.68→0.82 |

**Purpose:** Populates the "Weight Evolution" chart in Tab 4 at first load.
**Narrative told:** TC_v2 consistently outperforms TC_v1, justifying the promotion story.

### 3.2 `evolver.py` — Prompt Stats Seeds

**Location:** `PROMPT_STATS` dict, lines 18-23

| Variant | Success | Total | Rate |
|---------|---------|-------|------|
| TRAVEL_CONTEXT_v1 | 24 | 34 | 71% |
| TRAVEL_CONTEXT_v2 | 42 | 47 | 89% |
| PHISHING_RESPONSE_v1 | 31 | 38 | 82% |
| PHISHING_RESPONSE_v2 | 12 | 15 | 80% |

**Purpose:** Pre-seeds the AgentEvolver panel bars in Tab 2.
**Narrative told:** v2 variants generally outperform v1, but promotion threshold (>5% + 10 samples) only met for TRAVEL_CONTEXT.

### 3.3 `triage.py` — Confidence History Seeds

**Location:** `seed_confidence_history()`, lines 78-123

| # | Data Points | Description |
|---|-------------|-------------|
| 15 | CONFIDENCE_HISTORY snapshots | 3 situation types: travel 0.68→0.92, cloud_misconfig 0.55→0.88, data_exfil 0.60→0.85 |

**Purpose:** Populates the "Confidence Trajectory" chart in Tab 4.
**Narrative told:** All situation types improve monotonically — the system learns from every decision.

### 3.4 `feedback.py` — Trust History Seeds

**Location:** `seed_trust_history()`, lines 416-474

| # | Data Points | Description |
|---|-------------|-------------|
| 12 | TRUST_HISTORY snapshots | travel_login_anomaly: 0.50→0.77 (9 correct), crash to 0.17 (1 incorrect), recovery 0.20→0.23 |

**Purpose:** Populates the Trust Curve in Tab 4.
**Narrative told:** "One wrong answer wipes nine right ones." Demonstrates 20:1 asymmetry visually.

### 3.5 `feedback.py` — Pattern/Edge Seeds

**Location:** Module-level constants, lines 20-35

| State | Value |
|-------|-------|
| PATTERN_CONFIDENCE["PAT-TRAVEL-001"] | 0.94 |
| PATTERN_CONFIDENCE["PAT-PHISH-001"] | 0.89 |
| EDGE_WEIGHTS["User→TravelContext"] | 0.91 |
| EDGE_WEIGHTS["User→PhishingCampaign"] | 0.87 |
| PRECEDENT_COUNTS["PAT-TRAVEL-001"] | 127 |
| PRECEDENT_COUNTS["PAT-PHISH-001"] | 89 |

**Purpose:** Display values for outcome feedback narrative. Not used in any scoring computation.

### 3.6 `narrative.py` — Template Strings

**Location:** Full file, 295 lines

All labels and sentence builders are hardcoded dictionaries:
- `_FACTOR_LABELS`: 30+ factor→English-phrase mappings
- `_ACTION_LABELS`: 5 action→English-phrase mappings
- `_THREAT_INTEL_FACTORS`: 10 factor names that trigger sentence 4
- No LLM call. No dynamic generation.

### 3.7 `seed_neo4j.py` — Graph Seeds

**Location:** Full file, ~800+ lines

**Entities seeded:**

| Label | Count | Key Instances |
|-------|-------|---------------|
| User | 8+ | John Smith, Alice Lee, Mike Chen, Mary Chen, Robert Jones, Ana Garcia, Kavita Patel, svc-backup, Mike Wilson |
| Asset | 7+ | LAPTOP-JSMITH, LAPTOP-ALEE, SRV-DB-PROD-01, LAPTOP-MARYCHEN, LAPTOP-RJONES, LAPTOP-AGARCIA, DESKTOP-KPATEL |
| Alert | 10+ | 7819-7824, 7830, 7835, 7841, 7845, plus credential/threat intel alerts |
| AlertType | 7+ | anomalous_login, phishing, malware_detection, brute_force, privilege_escalation, credential_stuffing, c2_beacon, threat_intel_match |
| AttackPattern | 8+ | PAT-TRAVEL-001 through 004, PAT-PHISH-KNOWN, PAT-BRUTE-001, PAT-PRIVESC-001, PAT-CREDSTUFF-001, PAT-C2-001, PAT-APT-001 |
| Playbook | 7+ | PB-LOGIN-FP, PB-PHISH-AUTO, PB-BRUTE-001, PB-ESCALATE-001, PB-CREDSTUFF-001, PB-INCIDENT-001, PB-THREATINTEL-001 |
| TravelContext | 1 | TRAVEL-001 (John Smith → Singapore) |
| SLA | 1 | SLA-MEDIUM |
| PhishingCampaign | 1 | Operation DarkHook |

**Relationships seeded:**
- `DETECTED_ON`, `INVOLVES`, `CLASSIFIED_AS`, `MATCHES`, `HANDLED_BY`, `HAS_TRAVEL`, `SUBJECT_TO`, `PART_OF`, `ASSIGNED_TO`

**Key observation:** All alert properties that control agent decisions are baked into the seed data. For example, ALERT-7823 has `mfa_completed: true`, `device_fingerprint_match: true`, `source_location: 'Singapore'` — these ensure the agent always returns `false_positive_close` with confidence 0.92.

---

## SECTION 4: GRAPH DATA INVENTORY — Connectors

### 4.1 Connector Architecture

**Base class:** `backend/app/connectors/base.py` — `UCLConnector` ABC with `refresh()`, `health_check()`, `get_config_schema()`

**Registry:** `backend/app/connectors/registry.py` — Singleton `ConnectorRegistry` with `register()`, `refresh_all()`, `health_check_all()`

**Router:** `backend/app/routers/graph.py` — Endpoints: `POST /graph/threat-intel/refresh`, `GET /graph/connectors`, `POST /graph/connectors/refresh-all`, `GET /graph/enrichment/aggregate/{indicator}`, `GET /graph/enrichment/summary`, `GET /graph/enrichment/by-alert/{alert_id}`

### 4.2 PulsediveConnector — `backend/app/connectors/pulsedive.py`

**Source type:** threat_intel
**Behavior:**
- If `PULSEDIVE_API_KEY` set: calls Pulsedive live API for 5 curated IOCs
- Per-IOC fallback to `HARDCODED_FALLBACK` dict on API failure
- Full fallback when no key present

**Curated IOC list (5 indicators):**

| IOC | Type | Hardcoded Severity | Context |
|-----|------|--------------------|---------|
| 103.15.42.17 | ip | high | Singapore IP — ties to ALERT-7823 |
| 185.220.101.34 | ip | critical | Known Tor exit node |
| cobaltstrike.github.io | domain | critical | C2 framework domain |
| 45.33.32.156 | ip | medium | Scanning source — reconnaissance |
| malware-traffic-analysis.net | domain | medium | Malware distribution tracker |

**Neo4j writes:**
- MERGE `:ThreatIntel` nodes (idempotent)
- MERGE `(ThreatIntel)-[:ASSOCIATED_WITH]->(Alert)` for `ALERT_IOC_MAP`: `{"ALERT-7823": ["103.15.42.17"]}`

**Live capability:** REAL. If API key is configured, fetches actual Pulsedive data. This is the ONE genuinely live data source in the system.

### 4.3 GreyNoiseConnector — `backend/app/connectors/greynoise.py`

**Source type:** enrichment
**Behavior:** Same pattern as Pulsedive — live API with per-IP fallback.

**Curated IP list (3 IPs — domains excluded, GreyNoise is IP-only):**

| IP | Hardcoded Classification | Noise | Riot |
|----|--------------------------|-------|------|
| 103.15.42.17 | malicious | true | false |
| 185.220.101.34 | benign | true | true (Tor Project) |
| 45.33.32.156 | unknown | true | false |

**Neo4j writes:**
- MERGE `:GreyNoiseEnrichment` nodes
- MERGE `(ThreatIntel)-[:ENRICHED_BY]->(GreyNoiseEnrichment)` cross-references

**Live capability:** REAL. If GREYNOISE_API_KEY set, fetches actual GreyNoise classifications.

### 4.4 CrowdStrikeMockConnector — `backend/app/connectors/crowdstrike_mock.py`

**Source type:** edr
**Behavior:** Pure mock — no API key, no external calls. All data hardcoded.

**Mock device inventory (3 devices):**

| Hostname | Device ID | OS | Prevention Status | Sensor Version |
|----------|-----------|----|--------------------|----------------|
| LAPTOP-JSMITH | CS-001 | Windows 11 | active | 7.14.16804 |
| LAPTOP-MCHEN | CS-002 | Windows 11 | active | 7.14.16804 |
| SRV-WEB-03 | CS-003 | CentOS 8 | reduced | 7.12.15409 |

**Neo4j writes:**
- MERGE `:CrowdStrikeEnrichment` nodes
- MERGE `(Asset)-[:EDR_MANAGED_BY]->(CrowdStrikeEnrichment)` edges

**Live capability:** NONE. Always returns hardcoded data. health_check() always returns healthy.

### 4.5 Multi-Source Aggregation — `graph.py`

The `GET /graph/enrichment/by-alert/{alert_id}` endpoint does REAL graph traversal:
```cypher
MATCH (alert:Alert {id: $alert_id})
OPTIONAL MATCH (ti:ThreatIntel)-[:ASSOCIATED_WITH]->(alert)
OPTIONAL MATCH (ti)-[:ENRICHED_BY]->(gn:GreyNoiseEnrichment)
OPTIONAL MATCH (alert)-[:DETECTED_ON]->(asset:Asset)-[:EDR_MANAGED_BY]->(cs:CrowdStrikeEnrichment)
```

This is one of the few places where data from multiple sources is genuinely fused via graph relationships. `_consensus_severity()` applies a real priority-based aggregation rule across sources.

### 4.6 What's Actually Computed vs. What's Hardcoded

| Component | Computed | Hardcoded |
|-----------|----------|-----------|
| Pulsedive IOC data | Live API (when key present) | Fallback dict (5 entries) |
| GreyNoise IP classification | Live API (when key present) | Fallback dict (3 entries) |
| CrowdStrike EDR | Never | Always (3 devices) |
| Threat intel → alert links | MERGE query (graph relationship) | `ALERT_IOC_MAP` mapping |
| Consensus severity | `_consensus_severity()` priority logic | N/A — always computed |
| Factor values (5 of 6) | Never | `SOC_FACTOR_TEMPLATES` |
| Factor value (threat_intel) | Neo4j query for highest-severity IOC | Fallback "none" |
| Situation classification | Never — if-else cascade | `classify_soc_situation()` |
| Option scores | Never | `SOC_OPTIONS` dict |
| Decision action | Never — if-else cascade | `agent.decide()` |
| Trust score | Real arithmetic (+0.03/-0.60) | Seeded baseline (12 entries) |
| Weight evolution | Real counter arithmetic | Seeded baseline (15 entries) |
| Confidence trajectory | Real append per decision | Seeded baseline (15 entries) |

---

## SECTION 5: CHANGE PLAN — What Stays, What Changes

### 5.1 Architectural Assessment

The demo has three layers of "intelligence":

1. **Display layer** (frontend) — Renders whatever the backend returns. No intelligence here. Stays as-is.
2. **Orchestration layer** (routers) — Calls services in sequence, builds response dicts. Minimal logic. Stays as-is.
3. **Decision layer** (services/) — Where the gap lives. This is what needs to change.

Within the decision layer, there are two categories:

**Category A: Genuine computation (keep and extend)**
- Pulsedive/GreyNoise live API calls → real external data
- Consensus severity aggregation → real priority logic
- Evolver promotion mechanism → real A/B comparison
- Trust score arithmetic → real asymmetric counter
- Graph traversal in `get_security_context()` → real Neo4j queries

**Category B: Simulated computation (replace)**
- Factor values → static dict lookups → need graph-computed values
- Scoring matrix → missing → need f · Wᵀ with real softmax
- Weight updates → ±fixed delta → need Hebbian rule with actual f(t)
- Situation classification → if-else → need scoring-based classification
- Confidence values → hardcoded floats → need computed from scoring matrix
- "47 nodes" → `base_nodes + 39` → need real count

### 5.2 File-by-File Change Plan for v4.1 Sprint (Tiers 1-3)

#### Tier 1: Computed Factors (~200 lines new code)

**Target:** Replace 5 hardcoded factor values per alert with graph-computed values.

| File | Change | Lines |
|------|--------|-------|
| `domains/soc/factors.py` | Add `async compute_factors_from_graph(alert_id)` that queries Neo4j for each factor | ~120 new |
| `services/triage.py` | Replace `SOC_FACTOR_TEMPLATES` lookup with async graph computation | ~30 modified |
| `db/neo4j.py` | Add 5 new Cypher queries (one per factor type) | ~50 new |

Factor computation queries (examples):
```
travel_match: MATCH (alert)-[:INVOLVES]->(u)-[:HAS_TRAVEL]->(t)
              WHERE t.destination = alert.source_location
              RETURN count(t) AS match_count, t.end_date - t.start_date AS trip_duration
              → normalize to 0.0-1.0

asset_criticality: MATCH (alert)-[:DETECTED_ON]->(a:Asset)
                   RETURN a.criticality
                   → map {"critical": 1.0, "high": 0.8, "medium": 0.5, "low": 0.2}

pattern_history: MATCH (alert)-[:CLASSIFIED_AS]->(at:AlertType)<-[:CLASSIFIED_AS]-(prev:Alert)
                 WHERE prev.status = 'resolved'
                 RETURN count(prev) AS total,
                        count(CASE WHEN prev.resolution = 'false_positive' THEN 1 END) AS fp
                 → base_rate = fp / total
```

#### Tier 2: Scoring Matrix (~80 lines new code)

**Target:** Replace hardcoded option scores with real matrix multiplication.

| File | Change | Lines |
|------|--------|-------|
| `services/scoring.py` (NEW) | `ScoringMatrix` class: init W, compute P = softmax(f · Wᵀ / τ) | ~60 new |
| `services/situation.py` | Replace `SOC_OPTIONS` lookup with `ScoringMatrix.score(factors)` | ~20 modified |

Implementation:
```python
import numpy as np

class ScoringMatrix:
    def __init__(self, n_factors=6, n_actions=4, tau=1.0):
        self.W = np.random.randn(n_actions, n_factors) * 0.1  # or load saved
        self.tau = tau

    def score(self, factors: np.ndarray) -> np.ndarray:
        logits = factors @ self.W.T / self.tau
        exp_logits = np.exp(logits - logits.max())
        return exp_logits / exp_logits.sum()
```

~50 lines of NumPy. The gap analysis was right.

#### Tier 3: Weight Updates (~50 lines new code)

**Target:** Replace ±fixed deltas with Hebbian update rule.

| File | Change | Lines |
|------|--------|-------|
| `services/scoring.py` | Add `update(action_idx, factors, reward, delta)` to ScoringMatrix | ~30 new |
| `services/feedback.py` | Replace `PATTERN_CONFIDENCE +=` with `scoring_matrix.update()` | ~20 modified |

Implementation:
```python
def update(self, action_idx: int, factors: np.ndarray, reward: float, alpha: float = 0.01):
    delta = 20.0 if reward < 0 else 1.0  # asymmetry
    self.W[action_idx, :] += alpha * reward * factors * delta
```

~30 lines of NumPy. The gap analysis was right.

### 5.3 What Stays Unchanged

| Component | Reason |
|-----------|--------|
| All frontend code | Consumes API responses — format unchanged |
| `api.ts` | Endpoint URLs unchanged |
| `routers/*.py` | Orchestration layer — calls same functions |
| `agent.py` | Rule-based agent stays for demo reliability; scoring matrix is additive |
| `narrative.py` | Template narratives stay; LLM narratives are Tier 6 |
| `connectors/*` | Working correctly; Pulsedive/GreyNoise are already partially live |
| `seed_neo4j.py` | Graph structure stays; factor queries read from it |
| `evolver.py` | Promotion mechanism works; variant naming stays |
| All seed functions | UI population mechanism stays; live decisions extend from baseline |
| Trust tracking | Already real arithmetic; just needs to gate decisions |

### 5.4 What Changes (Summary)

| Priority | Change | Effort | Impact |
|----------|--------|--------|--------|
| **P0** | Factor computation from graph | Medium | Makes 5/6 factor values real |
| **P0** | ScoringMatrix class | Small | Makes scoring real (Eq. 4) |
| **P0** | Hebbian weight update | Small | Makes learning real (Eq. 4b) |
| **P1** | Trust flag gates automation | Tiny | Connects trust to decisions |
| **P1** | Real node count | Tiny | Replace `+39` with actual count |
| **P2** | Scoring-based classification | Medium | Replace if-else with scoring |
| **P3** | Remove "softmax scoring matrix" label | Tiny | Honest labeling |

### 5.5 Prompt Sequence for v4.1 Sprint

```
Prompt 1: Create services/scoring.py — ScoringMatrix class
          Init W (4 actions × 6 factors), score(), update(), save/load

Prompt 2: Add 5 graph-computed factor queries to db/neo4j.py
          travel_match, asset_criticality, time_anomaly, device_trust, pattern_history

Prompt 3: Wire computed factors into domains/soc/factors.py
          Replace SOC_FACTOR_TEMPLATES lookup with async graph queries
          Keep template as fallback when graph query returns empty

Prompt 4: Wire ScoringMatrix into services/situation.py
          Replace SOC_OPTIONS hardcoded scores with matrix.score(factors)
          Keep option structure (action, factors list, economics)

Prompt 5: Wire Hebbian update into services/feedback.py
          Replace PATTERN_CONFIDENCE ±delta with matrix.update()
          Pass actual factor vector f(t) from the decision context

Prompt 6: Wire trust flag into agent.py
          If LOW_TRUST_FLAGS[situation_type]: override to escalate_tier2
          Simple gate — 3 lines of code

Prompt 7: Fix node count — remove +39 constant in neo4j.py
          Return actual base_nodes as nodes_consulted
```

### 5.6 Risk Assessment

| Risk | Mitigation |
|------|------------|
| Graph queries slow down /alert/analyze | Cache factor results; async parallel queries (already using asyncio.gather in triage.py) |
| Scoring matrix produces surprising results | Keep agent.py rules as fallback; log matrix vs. rule disagreements |
| Hebbian updates don't converge | Cap W values; use small α; log weight drift per session |
| Factor queries return empty on sparse graph | Fall back to SOC_FACTOR_TEMPLATES (current behavior) |
| Breaking change in API response format | Factor dict shape unchanged; scores change from hardcoded to computed |

---

## Summary: The Realization Boundary

| Layer | Blog Claim | Demo Reality (v4.0) | v4.1 Target |
|-------|-----------|---------------------|-------------|
| **Factor Computation** | Graph-traversed signals | Dict lookup | Graph queries |
| **Scoring Matrix** | softmax(f · Wᵀ / τ) | Hardcoded option scores | Real NumPy softmax |
| **Weight Updates** | W += α · r(t) · f(t) · δ(t) | ±fixed scalar delta | Real Hebbian rule |
| **Situation Classification** | Learned patterns | if-else cascade | Keep (scoring-based is P2) |
| **Trust Signal** | Gates automation | Counter (display-only) | Counter → decision gate |
| **Narrative** | LLM over graph context | Template strings | Keep (LLM is Tier 6) |
| **Embeddings** | Entity vectors in Neo4j | Not implemented | v5.5 target |
| **Cross-Graph Attention** | Q · Kᵀ / √d | Not implemented | v5.5 target |

**The gap is structural but closable.** Tiers 1-3 require ~330 lines of new code and ~70 lines of modifications. The architecture (routers, frontend, graph schema) is sound and doesn't need to change. The realization boundary sits between v4.0 (current) and v4.1 (Tiers 1-3 implemented).

---

*SOC Copilot — Technology Realization Code Analysis | February 27, 2026*
*Analyst: Claude (Opus-class) | Files read: 19 | Lines analyzed: ~5,500*
