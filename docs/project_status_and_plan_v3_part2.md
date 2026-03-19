# Compounding Intelligence Platform
# Project Status & Plan v3 — Part 2: v5.5 Sprint, v6.0 Design & Success Criteria

**Version:** 3.1 · Part 2 of 2 · March 15, 2026
**Companion:** Part 1 (Foundation, Current State, Pre-Sprint Closure)
**Authority:** Read Part 1 §4 (Pre-Sprint Closure) before executing any prompt in this document.
Prompts in Phase 2 (EXP-*) require §23.5 + §23.4 written (Part 1 §4.1 items 0b + 4).
Prompts in Phase 4 (TRUST-*) require §17.5 written (Part 1 §4.1 item 0a).
Prompts in Phase 5 (AUTO-*) require PROD-4 result (DONE March 14-15) + DISC-1 result (DONE March 15).

---

## 1. v5.5 Overview

### 1.1 Theme

**v5.5 is the product. v5.0 is the foundation.**

v5.0 proved the math is correct (97.89% centroidal, 71.7% realistic 50-seed). It does not yet
prove compounding is visible, decisions are explainable, or a CISO can evaluate it in 10
minutes. v5.5 closes all five CISO demo questions. Every phase is ordered by demo conversion
impact — the features a CISO sees first and uses to decide whether to continue are built first.

### 1.2 The Five CISO Demo Questions (v5.5 Test)

v5.5 ships when a CISO can be given a URL, click around for 10 minutes, and answer all five:

| Question | v5.0 Answer | v5.5 Target |
|---|---|---|
| **Q1:** "Does it work?" | Factor numbers only | NL explanation + factor provenance + similar past cases |
| **Q2:** "Is it getting smarter?" | Cannot answer | IKS score + weekly delta + centroid drift chart |
| **Q3:** "What's the ROI?" | Projected estimate only | Shadow mode realized numbers + three-tier dispatch economics |
| **Q4:** "What if it's wrong?" | Architecture answer only | Shadow report + checkpoint/rollback UI controls |
| **Q5:** "Why not Security Copilot?" | Positioning argument | Firm-specific threat graph + IOC count (Tab 1 header, v5.5) + Graph Explorer (Tab 1 Panel B, v5.5). Full exec learning narrative (Tab 5, v6.0). |

**v5.5 ships when all five are answerable with real product data, not design arguments.**

### 1.3 COTS Delegation Principle

Build only where absence directly blocks a CISO demo question or a first enterprise contract.
Delegate to COTS (Docker, Let's Encrypt, Neo4j, Nginx) everywhere else. Do not build
infrastructure that COTS provides.

| Category | Build | Delegate |
|---|---|---|
| Scoring and learning | ProfileScorer, centroid updates, IKS | NumPy (already in place) |
| NL explanations (Layer 1) | Deterministic templates (no LLM) | Graph provides all data |
| NL explanations (Layer 2) | Deterministic (NarrativeProvider optional) | Ollama for prose variant |
| Deployment | seed.py, health checks | Docker Compose, Nginx, Let's Encrypt |
| Compliance evidence | Audit trail format, N3 disclosure | PDF generation library |
| Open-source release | README, examples, CONTRIBUTING | GitHub Actions, PyPI |

---

## 2. Execution Constraints (All Prompts)

```
CONSTRAINTS — ALL v5.5 PROMPTS:

[Repository discipline]
- Do NOT use git directly. User handles all git operations.
- Do NOT start the debugger. Log-based debugging only.
- Read before write. One concern per prompt.
- Each prompt creates or modifies files in ONE repo only.
  Cross-repo changes require separate prompts in sequence.

[GAE repo rules]
- Zero SOC-specific code in GAE. Domain config via protocol only.
- ProfileScorer IS the scoring mechanism. ScoringMatrix DEPRECATED (TD-029).
- All τ defaults = 0.1 (V3B validated ECE=0.036). Never use 0.25.
- All centroid updates MUST clip to [0.0, 1.0]. V2 validated.
- ProfileScorer.update() has NO synthesis parameter. σ NEVER flows in.
- numpy-only for GAE core. Type hints everywhere. Python 3.11+.
- Public API must remain backward-compatible within 0.x.

[SOC repo rules]
- Import from GAE: from gae.profile_scorer import ProfileScorer, build_profile_scorer
- Import hooks: from gae.hooks import DecisionRecord, OutcomeRecord, ProfileSnapshot
- Import NL: from app.services.nl_templates import NLTemplateEngine
- Import similar cases: from app.services.similar_cases import SimilarCasesService
- Language: "product" not "demo" in all comments, docstrings, UI text.
- EvaluationReport.by_category — never by_technique (S2P co-design fix).
- ProfileScorer shape: (C=6, A=5, d=6) = 180 values. Never hardcode A=4. A=5 includes refer_to_analyst.
- C=6 (ORDER IS PERMANENT): credential_access(0), threat_intel_match(1), lateral_movement(2),
  data_exfiltration(3), insider_threat(4), cloud_infrastructure(5).
- refer_to_analyst is a first-class production action with its own centroid profile μ[c,4,:].
  Never treat it as a fallback or exception handler.
- confidence floor: PROD-4b calibrated values (March 14): cred=0.93, TI=0.95, lat=0.97,
  exfil=0.95, insider=0.96, cloud=0.95. These REPLACE the 0.70 design estimate.
- η_neg = 0.05 CANONICAL. NEVER use η_neg=1.0 in experiments or production (ECE=0.49).
- Alert routing: use resolve_alert_category(alert_type) from config.py. NEVER treat alert_type as category.

[Data preservation — mandatory hooks]
- DecisionRecord on EVERY score() call (including shadow mode decisions).
- OutcomeRecord on EVERY update() call.
- ProfileSnapshot EVERY 50 decisions AND on every operator start.
- These are the Level 2/3 substrate. Skipping them prevents GATE-R, IKS, TD-033.

[Shadow mode]
- shadow_mode=True in Decision node. Recommendation NOT shown in UI.
- analyst_action recorded separately. agreement flag computed on record.
- Shadow report generated ONLY after N decisions threshold met.
- NEVER auto-activates live mode. Explicit [ACTIVATE LIVE MODE] click required.
  Any auto-activation is a design violation.

[Intelligence layer — synthesis boundary]
- λ operative window: λ ∈ [0.5, 0.6] with Loop 2 running. Never deploy λ > 0.6.
- λ = 0 for any deployment where GATE-M has not passed.
- get_domain_constraint_spec() returns {} until GATE-M passes.
- Loop 2/Loop 4 firewall is permanent. update() never receives σ.

[Test requirements]
- Run all existing tests before declaring any prompt done.
- New code requires new tests. Minimum 4 tests per new service class.
- Acceptance criterion is the last thing checked before moving to the next prompt.
```

---

## 3. v5.5 Milestones

| Milestone | Phases Complete | CISO Demo State | External Trigger |
|---|---|---|---|
| **v5.5-alpha** | Phases 1–3 | Q1+Q2 answerable (explainability + compounding visible) | Internal review only |
| **v5.5-beta** | + Phases 4–5 | Q1–Q4 answerable (trust mechanisms + autonomy) | Staged access to SOC architects |
| **v5.5** | + Phases 6–9 | All 5 questions answerable; Docker deploy; PyPI | CISO demo URL live; outreach begins |

**v5.5 release gate (hard — all must be true):**
1. All five CISO demo questions answerable with real product data.
2. GATE-R has run (routing accuracy measured — even if composite claim not yet statable).
3. Docker Compose deployment produces running system on clean VPS in < 5 minutes.
4. `pip install graph-attention-engine` installs and runs the quick-start example.
5. N3 endogenous loop disclosure present in EU AI Act Article 9 risk log template.
6. PROD-3 calibration table in shadow mode documentation.
7. Shadow mode agreement rate expectation statable (from PROD-3 result).
8. Confidence floors replaced with PROD-4b-derived values (cred=0.93, TI=0.95, lat=0.97, exfil=0.95, insider=0.96, cloud=0.95). ✅ DONE March 15.

---

## 4. v5.5 Sprint Phases

Phases are ordered by demo conversion impact. Phase 1 (correctness) is a prerequisite for
every other phase — wrong routing corrupts all downstream metrics. Phase 2 (explainability)
is the first thing a CISO sees on Tab 3 (Q1). Phases 3 and 4 (IKS, shadow) answer Q2 and Q4.
Phase 5 (autonomy) answers Q3 with realized numbers.

---

### Phase 1: Correctness Foundation
**Goal:** Fix the three silent data quality bugs before any product metrics are exposed to a CISO.
**Q closed:** None directly — but every other demo answer depends on correct routing, correct
bootstrap records, and correct factor vector storage.
**GATE-R trigger:** Phase 1 completion is the trigger for running GATE-R.
After CORR-1 ships and is verified, run GATE-R immediately.

---

#### CORR-1: Alert Type → Category Mapping Completion (v5.5-R6 / G-L1-1)

```
Repo: soc-copilot
Design spec: soc_copilot_design_v5_4 §14 — get_alert_category_mapping()

READ FIRST:
  backend/app/config/soc_domain_config.py → find get_alert_category_mapping()
  backend/app/services/triage.py → find where alert_type is resolved to category
  backend/app/services/simulation.py → same resolution path
  List all unique alert_type values currently in the alert pool (25+ healthcare-domain
  alerts + v5.0 realistic alerts). Every one must map to one of the 5 canonical categories.

CREATE / MODIFY:
  1. In SOCDomainConfig.get_alert_category_mapping() — complete the mapping dict:
     - Map EVERY alert_type string from the simulation pool to one of:
       {credential_access, lateral_movement, insider_threat, data_exfiltration, cloud_infrastructure}
     - Use ATT&CK technique context to guide ambiguous mappings (e.g., T1078 → credential_access)
     - No alert_type should map to a default/fallback category after this prompt

  2. In the category resolution function (wherever alert_type → category occurs):
     - Replace silent default with explicit ERROR logging:
       if category not in canonical_categories:
           logger.error(f"ROUTING_FAILURE: alert_type='{alert_type}' produced unknown "
                        f"category='{category}'. Check get_alert_category_mapping(). "
                        f"Alert routed to '{default_category}' as emergency fallback.")
     - Never suppress this error. Never set log level < ERROR.

  3. Add mapping table as a constant in soc_domain_config.py so it is auditable:
     ALERT_TYPE_CATEGORY_MAP: dict[str, str] = {
         "brute_force_login": "credential_access",
         "anomalous_login": "credential_access",
         ... (complete for all 20+ types)
     }

TESTS (new file: tests/test_alert_type_routing.py):
  - test_all_simulation_pool_alert_types_route_to_known_category():
      For every alert in alert_pool: assert resolved category in canonical_categories
  - test_unrecognized_alert_type_emits_error_log():
      Pass "unknown_type_xyz" → verify ERROR logged, not silent
  - test_no_default_category_in_normal_operation():
      Run 50 simulation decisions → assert zero "ROUTING_FAILURE" log lines
  - test_mapping_dict_coverage():
      Assert len(ALERT_TYPE_CATEGORY_MAP) >= 20

Acceptance: Zero "ROUTING_FAILURE" log lines during a 50-decision simulation run.
Every alert_type in pool has explicit mapping. Tests pass.

→ AFTER THIS SHIPS: Run GATE-R immediately.
  Location: cross-graph-experiments/experiments/gate_r/
  Prompt: experiments_catalog_v8 Part 2 §7
  Do not wait for any other Phase 1 items before running GATE-R.
```

---

#### CORR-2: Bootstrap Decisions to Neo4j (G-L2-3)

```
Repo: soc-copilot
Design spec: soc_copilot_design_v5_4 §6.2 + §22 (IKS requires bootstrap as distinct source)

READ FIRST:
  backend/app/services/simulation.py → find bootstrap/warmup decision path
  backend/app/services/triage.py → find DecisionRecord write path
  Check: does startup/seed write bootstrap decisions to Neo4j? Expected: NO (this is G-L2-3).

PROBLEM: Bootstrap decisions (1,200 synthetic, seed=42) ran in-memory at startup.
Their effect on centroids is visible; their decision records are NOT in Neo4j.
This means:
  (a) IKS baseline comparison (μ vs μ₀) works, but
  (b) PatternHistoryFactor has no prior decisions to count for any category until
      real operational decisions arrive (incorrect — bootstrap should count),
  (c) Chart A shows no decisions before the first live/simulation decision, and
  (d) GATE-R cannot distinguish "correct bootstrap" from "no learning" in the metrics.

SOLUTION: Write bootstrap DecisionRecords to Neo4j during startup, clearly labeled.

MODIFY:
  1. In the bootstrap/seed pathway (wherever 1,200 synthetic decisions are generated):
     - Write a DecisionRecord for each bootstrap decision with:
         source: "bootstrap"           # NEW field — distinguish from operational decisions
         shadow_mode: False
         analyst_action: oracle_action # bootstrap uses oracle as ground truth
         analyst_agreed: True          # bootstrap decisions are oracle-correct by design
         confidence: scorer_confidence
         factor_vector: factor_vector  # the actual factor vector used
     - Use MERGE not CREATE — bootstrap is idempotent (safe to re-run)

  2. Add DecisionRecord.source field (string, optional, default="operational"):
     Valid values: "bootstrap" | "simulation" | "operational" | "shadow"
     This field enables IKS baseline queries, GATE-R routing queries, and PatternHistory
     to correctly count prior decisions by source type.

  3. In PatternHistoryFactor.compute():
     - Count prior decisions by: source IN ["bootstrap", "simulation", "operational"]
     - Do NOT count shadow decisions in PatternHistory (shadow is observation-only)

  4. In IKSService (to be built in Phase 3 — note here for when it's built):
     - μ₀ baseline is the centroid state AFTER bootstrap completes, BEFORE first
       operational decision. This is already correct in the formula. Just verify
       that ProfileSnapshot for t_decision=0 (post-bootstrap state) is written.
     - Add a ProfileSnapshot at the end of bootstrap run with:
         t_decision: 0
         source: "bootstrap_complete"

TESTS:
  - test_bootstrap_decisions_written_to_neo4j():
      After startup, query Neo4j: count Decision WHERE source='bootstrap' → assert ≥ 1200
  - test_bootstrap_decisions_have_factor_vectors():
      Sample 10 bootstrap DecisionRecords → assert factor_vector is not null
  - test_pattern_history_counts_bootstrap_decisions():
      PatternHistoryFactor.compute() for a category → assert count > 0 after bootstrap
  - test_shadow_decisions_not_counted_in_pattern_history():
      Write shadow decision → assert PatternHistory count unchanged

Acceptance: Query Neo4j after startup → ≥ 1200 Decision nodes with source='bootstrap'.
PatternHistoryFactor returns non-zero prior count for all 5 categories from day 1.
```

---

#### CORR-3: factor_vector Native Neo4j Storage (G-L4-2)

```
Repo: soc-copilot
Design spec: soc_copilot_design_v5_4 §6.1 (DecisionRecord write-back)

READ FIRST:
  Search codebase for json.loads and json.dumps on factor_vector — list every occurrence.
  Check the Cypher query that writes DecisionRecord — find how factor_vector is stored.
  Expected: factor_vector stored as JSON string (e.g., "[0.87, 0.92, 0.45, 0.63, 0.71, 0.58]")
  and every read path does json.loads() to recover the list.

PROBLEM: Neo4j stores factor_vector as a string, not as a native list.
This is fragile: json.loads() fails silently on malformed strings, makes
Cypher-level math on factor_vector impossible, and prevents cosine similarity
queries from running natively in Cypher (needed by SimilarCasesService in Phase 2).

FIX:
  1. In DecisionRecord write Cypher — change factor_vector storage:
     BEFORE: factor_vector: $factor_vector_json  (a JSON string)
     AFTER:  factor_vector: $factor_vector        (a Python list → Neo4j native list)

  2. Remove ALL json.loads() and json.dumps() calls on factor_vector throughout the codebase.
     After this fix: factor_vector is always a Python list[float] at the application layer
     and a native list at the Neo4j layer.

  3. Migration: If the product has existing Decision nodes with factor_vector as string,
     write a one-time migration Cypher:
       MATCH (d:Decision) WHERE d.factor_vector STARTS WITH '['
       SET d.factor_vector = apoc.convert.fromJsonList(d.factor_vector)
     If APOC is not available: Python migration script that reads all Decision nodes,
     parses factor_vector, writes back as list.
     Log: "CORR-3 migration: N Decision nodes updated from JSON string to native list."

  4. Verify that SimilarCasesService (Phase 2) can execute this Cypher correctly:
       MATCH (d:Decision {category: $cat})
       WHERE d.factor_vector IS NOT NULL
       RETURN d.factor_vector, d.action, d.confidence
     This must return Python lists, not strings.

TESTS:
  - test_factor_vector_stored_as_native_list():
      Write a DecisionRecord with factor_vector=[0.8, 0.3, 0.6, 0.9, 0.4, 0.7]
      Read it back via Cypher → assert result is list, not str
  - test_no_json_loads_in_read_path():
      Grep codebase: assert zero occurrences of json.loads on factor_vector
      (This is a code quality test — run grep as part of test suite)
  - test_cosine_similarity_query_runs_on_native_list():
      Write 5 DecisionRecords with factor_vectors
      Execute cosine similarity Cypher → assert returns float results, not errors
  - test_migration_idempotent():
      If migration script exists: run twice → assert same result

Acceptance: Zero json.loads() calls on factor_vector in codebase.
Read path returns Python list[float] directly. Cosine query runs without errors.
```

---

### Phase 2: Explainability
**Goal:** Tab 3 shows plain-English explanation for every recommendation.
**Q closed:** Q1 ("Does it work?") — for all three customer roles.
**Prerequisites:** §23.5 NL judge rubric written (Part 1 §4.1 item A-2). §23.4 similar cases
spec written with PROD-3 θ values (Part 1 §4.1 item A-3 + Part 1 §4.4 step 4).
CORR-3 must be complete (cosine similarity requires native list storage).

---

#### EXP-1: NL Template Engine — Layer 1 (v5.5-R5, analyst explainability)

```
Repo: soc-copilot
Design spec: soc_copilot_design_v5_4 §23 (NLTemplateEngine)

READ FIRST:
  soc_copilot_design_v5_4 §23.1–23.4 — full template engine spec
  soc_copilot_design_v5_4 §23.5 — judge rubric (must exist before building)
  Current Tab 3 render: find where factor_vector is displayed as numbers
  The 30 template slots needed: 6 categories × 5 actions = 30 (but refer_to_analyst templates
  can share structure across categories — 5 per category minimum)

CREATE: backend/app/services/nl_templates.py

class NLTemplateEngine:
    """Deterministic NL explanations. No LLM. Graph provides all data; templates provide language.
    Same inputs always produce same output — compliance-safe.
    Three layers: L1 (analyst), L2 (CISO weekly), L3 (auditor record).
    """

    def render_l1(
        self,
        category: str,         # e.g. "credential_access"
        action: str,           # e.g. "escalate"
        confidence: float,     # e.g. 0.913
        factor_values: dict[str, float],     # {"travel_match": 0.87, ...}
        provenance_nodes: list[dict],         # from FactorComputerResult.provenance_nodes
        similar_cases_summary: dict | None,  # from SimilarCasesService (None if < 5 decisions)
        graph_context: dict,                 # Neo4j-resolved entities: user, asset, alert_type
    ) -> str:
        """Per-decision analyst explanation. Used in Tab 3 recommendation block.

        Output contract:
          - Starts with action + confidence: "ESCALATE recommended (89% confidence)."
          - Names the 2-3 most influential factors with their provenance in plain English.
          - If similar_cases_summary is not None: adds "Your analysts have [actioned] X
            comparable alerts in the past Y days — this recommendation aligns with Z%."
          - Never more than 4 sentences. Never tautological. Must name ≥ 1 real graph entity
            (user ID, asset name, IOC value, alert type string).
        """

    def render_l2(self, weekly_data: dict) -> str:
        """CISO weekly summary line. Used in Tab 5 Section 1 (What Changed Since Last Time).
        Output: "847 alerts this week. 347 auto-approved (41%). IKS: 47.3 (+2.1). ..."
        """

    def render_l3(self, decision_record: dict) -> str:
        """Formal audit record. Used in compliance export and Tab 4 evidence ledger.
        Output: "Decision 7a3f-91c2: Alert ALERT-7823 (credential_access / T1078).
                Action: ESCALATE (0.910). Centroid snapshot: ps-0047. ..."
        """

    def render_shadow_disagreement(self, decision: dict, alert: dict) -> str:
        """NL explanation for shadow mode report disagreement block.
        Output: "System recommended ESCALATE (87%); analyst chose CLOSE_FALSE_POSITIVE.
                Key factor difference: travel_match=0.87 (Singapore, unconfirmed). ..."
        """

    def render_centroid_shift(self, category: str, action: str,
                               delta: np.ndarray, direction: str) -> str:
        """Plain-English centroid shift for 'what your system learned this week'.
        Used in Tab 5 Section 1 (What Changed Since Last Time) at v6.0;
        also used in Tab 2 narrative at v5.5.
        Output: "credential_access escalation profile shifted toward higher travel_match
                weighting. 3 verified escalations this week reinforced this pattern."
        direction: "toward" | "away_from"
        """

Template implementation notes:
  - Define TEMPLATES: dict[str, dict[str, str]] — outer key is category, inner key is action.
  - Each template is an f-string with named slots: {action_display}, {confidence_pct},
    {top_factor_name}, {top_factor_provenance}, {entity_name}, {similar_pct}, {similar_count}.
  - Factor importance order: highest factor value drives the first sentence.
  - Entity resolution from graph_context: user display name, asset criticality label,
    IOC type, alert type in human language.
  - If a provenance node is available for the top factor, use it in the explanation.
    If not available (< v5.5-R2 data), fall back to factor value only.

TESTS (tests/test_nl_templates.py — minimum 8 tests):
  - test_render_l1_returns_string_for_all_30_template_slots():
      For every (category, action) pair: render_l1 with mock data → assert isinstance(str)
      Assert len > 20 chars. Assert str(confidence) appears in output.
  - test_render_l1_names_real_entity_when_provenance_available():
      Provide provenance_node with key_value="Singapore" → assert "Singapore" in output
  - test_render_l1_no_tautological_phrases():
      Assert output does NOT contain: "this is a security alert", "this alert was triggered"
      (pattern match on known bad phrases)
  - test_render_l1_with_similar_cases():
      Provide similar_cases_summary → assert similar_cases language in output
  - test_render_l1_without_similar_cases_graceful():
      similar_cases_summary=None → render_l1 succeeds, no similar-cases language
  - test_render_l2_contains_volume_and_iks():
      weekly_data with alerts=847, iks=47.3 → assert "847" in output, "47.3" in output
  - test_render_l3_contains_decision_id():
      decision_record with id="7a3f-91c2" → assert "7a3f-91c2" in output
  - test_render_shadow_disagreement_names_both_actions():
      system_action="escalate", analyst_action="close_false_positive" →
      assert both action names appear in output

Acceptance: All 30 template slots render without error.
Every L1 output names ≥ 1 real entity when provenance_nodes is provided.
render_l3 output is suitable as-is for an audit log entry.
```

---

#### EXP-2: Similar Cases Service + Tab 3 Integration (v5.5-R5, similar past cases)

```
Repo: soc-copilot
Design spec: soc_copilot_design_v5_4 §23.4 (must exist and contain θ value before this prompt runs)

READ FIRST:
  soc_copilot_design_v5_4 §23.4 — get θ value from PROD-3 result.
  If PROD-3 has NOT run yet: use SIMILAR_CASES_MIN_SIM = 0.85 as design estimate,
  log a WARNING on every query: "PROD-3 not yet run — using design estimate θ=0.85".
  Set a TODO comment: "Replace 0.85 with PROD-3 p25 cosine distance after PROD-3 runs."
  CORR-3 must be complete (factor_vector must be stored as native list).

CREATE: backend/app/services/similar_cases.py

SIMILAR_CASES_MIN_SIM: float = 0.85      # DESIGN ESTIMATE — update after PROD-3
SIMILAR_CASES_MIN_DECISIONS: int = 5     # suppress sidebar below this count
SIMILAR_CASES_K: int = 3                 # top-k results
SIMILAR_CASES_CATEGORY_FILTER: bool = True  # NON-NEGOTIABLE

class SimilarCasesService:
    """Find the top-k most similar past decisions to the current alert factor vector.
    Uses cosine similarity on d=6 factor vectors within the same category.
    SIMILAR_CASES_CATEGORY_FILTER is non-negotiable: never retrieve cross-category cases.
    """

    def __init__(self, neo4j_service, domain_config):
        ...

    async def get_similar_cases(
        self,
        factor_vector: list[float],  # current alert's factor vector, d=6
        category: str,               # current alert category — filter applied
        current_alert_id: str | None = None,  # exclude current alert from results
    ) -> list[dict] | None:
        """Returns top-k similar cases, or None if < SIMILAR_CASES_MIN_DECISIONS exist.
        
        Never returns cross-category results (SIMILAR_CASES_CATEGORY_FILTER enforced).
        Never returns the current alert itself (filtered by current_alert_id if provided).
        
        Each result dict:
            {
                "alert_id": str,
                "action": str,
                "confidence": float,
                "similarity": float,         # cosine similarity [0.0, 1.0]
                "similarity_pct": int,        # round(similarity * 100)
                "outcome_verified": bool,
                "outcome_action": str | None,
                "days_ago": int,
                "factor_vector": list[float],
            }
        """
        # 1. Count prior decisions in this category (excluding bootstrap if desired)
        count_result = await self.neo4j.execute_read("""
            MATCH (d:Decision)
            WHERE d.category = $category
              AND d.factor_vector IS NOT NULL
              AND ($exclude_id IS NULL OR d.alert_id <> $exclude_id)
            RETURN count(d) AS n
        """, category=category, exclude_id=current_alert_id)

        if count_result["n"] < SIMILAR_CASES_MIN_DECISIONS:
            return None  # suppress sidebar

        # 2. Retrieve all decisions in category with factor_vector
        # Cosine similarity computed in Python (not in Cypher — list comprehension is safer)
        rows = await self.neo4j.execute_read("""
            MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)
            WHERE d.category = $category
              AND d.factor_vector IS NOT NULL
              AND ($exclude_id IS NULL OR a.id <> $exclude_id)
            RETURN d.factor_vector AS fv, d.action AS action,
                   d.confidence AS confidence,
                   d.outcome_verified AS outcome_verified,
                   d.analyst_action AS analyst_action,
                   a.id AS alert_id,
                   duration.between(d.timestamp, datetime()).days AS days_ago
            ORDER BY d.timestamp DESC
            LIMIT 500
        """, category=category, exclude_id=current_alert_id)

        # 3. Cosine similarity computation
        f = np.array(factor_vector, dtype=float)
        f_norm = np.linalg.norm(f)
        results = []
        for row in rows:
            fv = np.array(row["fv"], dtype=float)
            fv_norm = np.linalg.norm(fv)
            if f_norm < 1e-9 or fv_norm < 1e-9:
                continue
            sim = float(np.dot(f, fv) / (f_norm * fv_norm))
            if sim >= SIMILAR_CASES_MIN_SIM:
                results.append({**row, "similarity": sim, "similarity_pct": round(sim * 100)})

        results.sort(key=lambda x: (-x["similarity"], x["days_ago"]))
        return results[:SIMILAR_CASES_K] if results else None

    def summarize(self, similar_cases: list[dict] | None, current_action: str) -> dict | None:
        """Produce summary for NLTemplateEngine.render_l1 similar_cases_summary parameter."""
        if not similar_cases:
            return None
        same_action = [c for c in similar_cases if c["action"] == current_action]
        return {
            "total_cases": len(similar_cases),
            "same_action_count": len(same_action),
            "agreement_pct": round(100 * len(same_action) / len(similar_cases)),
            "days_range": f"{similar_cases[-1]['days_ago']}–{similar_cases[0]['days_ago']}",
        }

MODIFY: Tab 3 backend endpoint (wherever recommendation is returned):
  - Call SimilarCasesService.get_similar_cases(factor_vector, category, alert_id)
  - Call summarize() → pass to NLTemplateEngine.render_l1(similar_cases_summary=...)
  - Include similar_cases list in API response for frontend rendering

MODIFY: Tab 3 frontend (wherever recommendation is displayed):
  - Add "Similar Past Cases" sidebar below recommendation block
  - If similar_cases is not None: render top-3 as cards with:
      action badge, similarity %, confidence %, "N days ago", outcome if verified
  - If similar_cases is None: render nothing (no "not enough data" message — just absent)

TESTS (tests/test_similar_cases.py — minimum 6 tests):
  - test_returns_none_below_min_decisions():
      < 5 decisions in Neo4j for category → assert returns None
  - test_category_filter_enforced():
      Write decisions in category A and B → query for category A → assert only A decisions
  - test_similarity_threshold_enforced():
      Write 10 decisions with varying similarities → assert only those above θ returned
  - test_returns_top_k_at_most():
      Write 20 similar decisions → assert len(result) <= SIMILAR_CASES_K
  - test_cosine_identity():
      Query with same factor_vector as an existing decision → assert similarity = 1.0
  - test_summarize_agreement_pct():
      3 similar cases, 2 with same action as current → summarize() → agreement_pct = 67

Acceptance: Tab 3 recommendation block includes plain-English explanation (from EXP-1)
and similar past cases sidebar when ≥ 5 decisions exist in the category.
SIMILAR_CASES_CATEGORY_FILTER = True is enforced and tested.
```

---

#### EXP-3: NL Template Layers 2–3 + Tab 3 Full Integration

```
Repo: soc-copilot
Design spec: soc_copilot_design_v5_4 §23.2 (L2 CISO + L3 auditor layers)

READ FIRST:
  backend/app/services/nl_templates.py (from EXP-1) — render_l2, render_l3,
  render_shadow_disagreement, render_centroid_shift must exist.
  Current Tab 3 layout — find the recommendation display block.
  EXP-1 and EXP-2 must be complete.

MODIFY: backend/app/services/nl_templates.py
  Verify render_l2, render_l3, render_shadow_disagreement, render_centroid_shift
  are fully implemented (EXP-1 may have left stubs). Implement any stubs.

  L2 template — weekly CISO briefing line (one paragraph, < 80 words):
    "This week: {total} alerts processed. {auto_approved} ({auto_pct}%) auto-approved
    at {auto_accuracy:.0f}% accuracy. {escalated} escalated. {human_review} required
    human review. Institutional Knowledge Score: {iks} ({iks_delta:+.1f} vs last week).
    Top centroid shift: {top_shift_text}."

  L3 template — formal audit record (structured, compliance-safe):
    "Decision {decision_id}: Alert {alert_id} ({category} / {technique_id}).
    Action: {action_display} ({confidence:.3f}). Factor vector: [{fv_str}].
    Provenance hash: {provenance_hash}. Centroid snapshot: {snapshot_id}.
    Analyst override: {analyst_action if override else 'None'}.
    Outcome: {outcome if verified else 'Pending verification'}.
    Generated by NLTemplateEngine v{version}."

MODIFY: Tab 3 frontend — full integration:
  Replace current factor number display with the explainability block:
  
  Layout:
    ┌─────────────────────────────────────────────┐
    │ ESCALATE  89% confidence                    │
    │                                             │
    │ [NL explanation from render_l1]             │
    │                                             │
    │ Factor Breakdown                            │
    │  travel_match: 0.87 ──────────── [provenance│
    │  asset_criticality: 0.92 ───────  expand ▼]│
    │  ...                                        │
    │                                             │
    │ Similar Past Cases (when available)         │
    │  ESCALATE  94% similar  3 days ago         │
    │  ESCALATE  89% similar  8 days ago         │
    │  ESCALATE  87% similar  12 days ago        │
    └─────────────────────────────────────────────┘

  Notes:
    - Provenance expand/collapse per factor (from v5.5-R2 data, built in Phase 6)
      If provenance not yet available: factor number only, no expand control.
    - Action display name in human language: escalate → "ESCALATE",
      close_false_positive → "CLOSE — FALSE POSITIVE", etc.
    - Confidence as percentage (89%), not raw float (0.891).

TESTS:
  - test_render_l2_word_count():
      render_l2(weekly_data) → assert len(output.split()) <= 80
  - test_render_l3_contains_required_fields():
      render_l3(decision_record) → assert all: decision_id, action, confidence, category
  - test_render_centroid_shift_readable():
      render_centroid_shift("credential_access", "escalate", delta, "toward") →
      assert "credential_access" in output, "escalate" in output

Acceptance: Tab 3 recommendation block renders NL explanation from render_l1.
L2 and L3 templates produce output. Tests pass.
Q1 ("Does it work?") is fully answerable after this phase for all three customer roles.
```

---

### Phase 3: Compounding Visibility
**Goal:** Make learning visible with IKS and correct centroid drift chart.
**Q closed:** Q2 ("Is it getting smarter?")
**Prerequisites:** PROD-1 ideally run before shipping (κ* calibrated). If PROD-1 has not
run yet: use D_MAX=0.30 placeholder and document clearly. Ship IKS with placeholder; run
PROD-1 immediately; update D_MAX and κ* in the same code session.

---

#### VIS-1: Institutional Knowledge Score Service + Tab 2 Display (v5.5-R4)

```
Repo: soc-copilot
Design spec: soc_copilot_design_v5_4 §22 (full IKS spec)

READ FIRST:
  soc_copilot_design_v5_4 §22.1–22.4 — formula, service, display locations
  PROD-1 result if available — get κ* / D_MAX value.
  If PROD-1 has not run: use D_MAX = 0.30 with a flag:
    IKS_D_MAX_CALIBRATED: bool = False  # Set True after PROD-1 runs and D_MAX updated
  Current Tab 2 layout — find where to add IKS header.
  Hook 3 (ProfileSnapshot) write path — verify it is active.

CREATE: backend/app/services/iks.py

D_MAX: float = 0.30  # DESIGN DEFAULT — update after PROD-1 runs
IKS_D_MAX_CALIBRATED: bool = False  # Flag: False until PROD-1 result incorporated

@dataclass
class IKSDataPoint:
    t_decision: int
    timestamp: datetime
    iks: float
    mean_drift: float

class InstitutionalKnowledgeScoreService:
    """Computes and tracks Institutional Knowledge Score (IKS).
    
    Data source: ProfileSnapshot nodes (Hook 3 writes). If Hook 3 writes are missing,
    get_iks_trend() returns empty — intentional, not a bug.
    
    Formula: IKS(t) = 100 × min(mean_L2_drift(t) / D_MAX, 1.0)
      mean_L2_drift(t) = mean over (c,a) of ‖μ(t)[c,a,:] − μ₀[c,a,:]‖₂
      μ₀ = bootstrap centroid state (get_profile_centroids() at deployment, t=0)
    """

    def __init__(self, domain_config):
        self.baseline = np.array(domain_config.get_profile_centroids())  # μ₀, shape (5,5,6)

    def compute_iks(self, current_centroids: np.ndarray) -> float:
        assert current_centroids.shape == self.baseline.shape
        diffs = current_centroids - self.baseline
        per_cell_dist = np.linalg.norm(diffs, axis=-1)  # (C, A)
        mean_drift = float(per_cell_dist.mean())
        return round(100.0 * min(mean_drift / D_MAX, 1.0), 1)

    async def get_current_iks(self, profile_scorer) -> float:
        return self.compute_iks(profile_scorer.centroids)

    async def get_iks_trend(self, neo4j, lookback_days: int = 90) -> list[IKSDataPoint]:
        """IKS trend from ProfileSnapshot history. Returns empty if no snapshots."""
        snapshots = await neo4j.execute_read("""
            MATCH (ps:ProfileSnapshot)
            WHERE ps.created_at > datetime() - duration({days: $days})
            RETURN ps.centroid_array AS centroids,
                   ps.t_decision AS t_decision,
                   ps.created_at AS ts
            ORDER BY ps.created_at
        """, days=lookback_days)
        result = []
        for snap in snapshots:
            try:
                mu = np.array(snap["centroids"])
                if mu.shape != self.baseline.shape:
                    continue
                mean_drift = float(np.linalg.norm(mu - self.baseline, axis=-1).mean())
                iks = round(100.0 * min(mean_drift / D_MAX, 1.0), 1)
                result.append(IKSDataPoint(t_decision=snap["t_decision"],
                                           timestamp=snap["ts"], iks=iks,
                                           mean_drift=round(mean_drift, 4)))
            except Exception as e:
                logger.warning(f"IKS trend: skipping malformed snapshot: {e}")
        return result

    async def get_weekly_delta(self, neo4j) -> float | None:
        """IKS change in last 7 days. Returns None if < 2 data points in window."""
        trend = await self.get_iks_trend(neo4j, lookback_days=14)
        if len(trend) < 2:
            return None
        week_ago = [p for p in trend if p.timestamp <= datetime.utcnow() - timedelta(days=7)]
        if not week_ago:
            return None
        return round(trend[-1].iks - week_ago[-1].iks, 1)

    def interpret(self, iks: float) -> str:
        """Plain-English interpretation for UI (Tab 2 caption)."""
        if iks < 5:
            return "Using expert-configured priors. Operational learning not yet started."
        elif iks < 20:
            return f"IKS {iks}: Early adaptation. System has begun learning from your environment."
        elif iks < 50:
            return (f"IKS {iks}: Meaningful adaptation. "
                    f"Profile centroids reflect ~{iks:.0f}% of expected operational drift.")
        elif iks < 75:
            return (f"IKS {iks}: Deep adaptation. Your system knows your environment "
                    f"significantly better than at deployment.")
        else:
            return (f"IKS {iks}: Full adaptation. Replicating this requires "
                    f"running every one of your decisions again.")

MODIFY: Tab 2 frontend — add IKS block above the simulation controls:

  Layout:
    ┌──────────────────────────────────────┐
    │ Institutional Knowledge Score        │
    │            47.3                      │
    │      ↑ +2.1 this week                │
    │                                      │
    │ [90-day IKS trend line chart]        │
    │                                      │
    │ "IKS 47.3: Deep adaptation. ..."    │
    │                                      │
    │ IKS_D_MAX_CALIBRATED indicator:      │
    │ [Yellow badge "Calibration pending"] │
    │  if IKS_D_MAX_CALIBRATED == False    │
    └──────────────────────────────────────┘

  Empty state (no ProfileSnapshots yet):
    "IKS: — (Collecting baseline data. First score available after 50 decisions.)"

MODIFY: GET /api/soc/metrics endpoint — add iks fields:
  { ..., "iks": 47.3, "iks_weekly_delta": 2.1, "iks_interpretation": "...",
    "iks_d_max_calibrated": false }

TESTS (tests/test_iks.py — minimum 6 tests):
  - test_iks_zero_at_baseline():
      compute_iks(centroids = self.baseline) → assert iks == 0.0
  - test_iks_increases_with_drift():
      centroids = baseline + 0.10 (uniform) → assert iks > 0
  - test_iks_caps_at_100():
      centroids = baseline + 2.0 (beyond D_MAX) → assert iks == 100.0
  - test_iks_shape_mismatch_raises():
      compute_iks(np.zeros((4,4,6))) → assert raises AssertionError
  - test_interpret_returns_string_for_all_bands():
      For iks in [0, 4, 10, 30, 60, 90]: assert isinstance(interpret(iks), str)
  - test_get_iks_trend_empty_on_no_snapshots():
      Empty Neo4j → get_iks_trend() → assert returns []

Acceptance: Tab 2 shows IKS score, weekly delta, trend chart, and interpret() text.
Empty state handled gracefully. D_MAX placeholder flagged in UI until PROD-1 runs.
→ AFTER THIS SHIPS: Run PROD-1 immediately. Update D_MAX and IKS_D_MAX_CALIBRATED.
```

---

#### VIS-2: Chart A — Centroid Drift Metric Fix (v5.5-R3)

```
Repo: soc-copilot
Design spec: soc_copilot_design_v5_4 §v5.5-R3

READ FIRST:
  Current Tab 2 Chart A implementation — it shows delta_norm ≈ 0.0 because it was
  designed for ScoringMatrix.W delta, which ProfileScorer does not update.
  Find: where OutcomeRecord is written after ProfileScorer.update().
  Check: does OutcomeRecord contain centroid_delta_norm? Expected: NO (this is G-L2-1).

FIX:
  1. In ProfileScorer.update() (GAE repo):
     After computing the centroid update (pull/push), compute:
       centroid_delta_norm = float(np.linalg.norm(delta_vector))
     Return centroid_delta_norm from update() (add to return value or pass to caller).

  2. In SOC triage.py / outcome write-back path:
     Write centroid_delta_norm to OutcomeRecord:
       MERGE (or SET) o.centroid_delta_norm = $centroid_delta_norm

  3. In Tab 2 Chart A frontend:
     Replace the W delta query with:
       MATCH (o:OutcomeRecord)
       WHERE o.centroid_delta_norm IS NOT NULL
       RETURN o.t_decision, o.centroid_delta_norm, o.correct
       ORDER BY o.t_decision
     Chart: bar chart, one bar per OutcomeRecord.
       Bar color: green if correct=True (pull — learning toward correct),
                  red if correct=False (push — penalty for wrong decision)
     X-axis: decision count. Y-axis: drift magnitude.
     Title: "Centroid Learning Events — ‖Δμ‖ per verified decision"
     Tooltip: "Decision {t}: ‖Δμ‖ = {drift:.4f}. {'Reinforced' if correct else 'Corrected'}."

NOTE: ProfileScorer.update() is in the GAE repo. The centroid_delta_norm return
value change is a GAE repo change. Create a new test in GAE tests:
  test_update_returns_centroid_delta_norm(): call update() → assert returns float > 0.0

TESTS:
  - test_centroid_delta_norm_written_to_outcome_record() [soc-copilot]:
      Call triage.handle_outcome() → query Neo4j OutcomeRecord →
      assert centroid_delta_norm IS NOT NULL and > 0.0
  - test_chart_a_query_returns_real_data() [soc-copilot]:
      Write 5 OutcomeRecords with centroid_delta_norm → execute Chart A query →
      assert 5 rows returned
  - test_update_returns_delta_norm() [GAE]:
      ProfileScorer.update() → assert return value includes centroid_delta_norm as float

Acceptance: Chart A on Tab 2 shows non-zero bars after verified decisions.
Green bars for correct decisions, red for incorrect. No ≈0.0 flat chart.
```

---

### Phase 4: Trust Mechanisms
**Goal:** Shadow mode + checkpoint/rollback — the on-ramp for skeptical first customers.
**Q closed:** Q4 ("What if it's wrong?") and Q3 partial (realized ROI from shadow data).
**Prerequisites:** §17.5 written (Part 1 §4.1 item A-1).
PROD-3 calibration table must be in documentation before shadow mode ships.

---

#### TRUST-1: Checkpoint/Rollback Infrastructure (TD-033)

```
Repo: soc-copilot (primarily) + GAE (minor — checkpoint() method)
Design spec: soc_copilot_design_v5_4 §17.5 (MUST EXIST before running this prompt)

READ FIRST:
  soc_copilot_design_v5_4 §17.5 — ALL five subsections:
    (1) trigger conditions, (2) rollback-and-resume semantics, (3) Hook 2/3 interaction,
    (4) what rollback does NOT do, (5) checkpoint schedule.
  gae_design_v9 §16 — checkpoint every 50 decisions is a hard production constraint.
  Current Hook 3 write path — verify ProfileSnapshot written every 50 decisions.
  Current ProfileScorer.update() — understand the update cycle before modifying.

IMPLEMENT per §17.5 exactly:

  GAE repo — add ProfileScorer.checkpoint() method:
    def checkpoint(self) -> dict:
        """Serialize μ + counts + timestamp. Returns checkpoint dict."""
        return {
            "centroids": self.centroids.tolist(),
            "counts": self.counts.tolist() if hasattr(self, "counts") else None,
            "timestamp": datetime.utcnow().isoformat(),
            "n_decisions": self.n_decisions,
        }

  SOC repo — RollbackService:
    class RollbackService:
        async def create_checkpoint(self, neo4j, profile_scorer) → str:
            """Write ProfileSnapshot with checkpoint_id. Returns checkpoint_id."""
        
        async def trigger_rollback(self, neo4j, profile_scorer,
                                   target_checkpoint_id: str,
                                   trigger_reason: str,
                                   operator_id: str) → None:
            """Execute rollback per §17.5 spec:
            1. Restore μ from checkpoint.
            2. Set frozen=True on LearningState.
            3. Write RollbackEvent node to Neo4j.
            4. Emit CENTROID_ROLLED_BACK audit event.
            """
        
        async def resume_learning(self, neo4j, profile_scorer,
                                   confirmed_by: str) → None:
            """Resume centroid updates.
            Requires explicit operator confirmation (confirmed_by must be non-empty).
            Writes LEARNING_RESUMED audit event.
            Writes post-rollback ProfileSnapshot with resumed=True, post_rollback=True.
            """
        
        def is_frozen(self) -> bool:
            return self.learning_state.frozen

  Hook 2 suspension: In outcome write-back path:
    if rollback_service.is_frozen():
        logger.info("LEARNING_FROZEN: ProfileScorer.update() skipped during rollback window.")
        # Write a SKIPPED_ROLLBACK_FROZEN record (separate Neo4j node, not OutcomeRecord)
        return  # Do not call profile_scorer.update()

  Hook 3 enhancement: ProfileSnapshot during frozen window gets frozen=True flag.
  First ProfileSnapshot after LEARNING_RESUMED gets resumed=True, post_rollback=True.

  API endpoints:
    GET  /api/soc/checkpoints
      Returns: list of {checkpoint_id, t_decision, created_at, centroid_drift_since_prior}
      Sorted: newest first. Max 20 returned (configurable).
    
    POST /api/soc/rollback
      Body: {target_checkpoint_id: str, reason_code: str, operator_id: str}
      Validation: all three fields required and non-empty
      Returns: {rolled_back: true, checkpoint_restored: str, timestamp: str}
    
    POST /api/soc/resume-learning
      Body: {confirmed_by: str}
      Validation: confirmed_by non-empty; system must currently be frozen
      Returns: {resumed: true, timestamp: str}

  Tab 2 UI additions:
    - "Checkpoints" section: list of last 10 checkpoints with decision count and drift
    - "Freeze learning" toggle button (calls /api/soc/rollback with current as target)
    - "Rollback to [checkpoint date]" button per checkpoint row
    - "Resume learning" button (only visible when frozen=True)
    - Frozen state banner: "LEARNING FROZEN — system scoring normally, not updating centroids."

TESTS (tests/test_rollback.py — minimum 8 tests):
  - test_checkpoint_written_to_neo4j():
      create_checkpoint() → query ProfileSnapshot → assert exists with checkpoint_id
  - test_rollback_restores_centroids():
      Save checkpoint → run 10 updates → rollback → assert centroids == checkpoint state
  - test_hook2_suspended_when_frozen():
      trigger_rollback() → call handle_outcome() → assert ProfileScorer.update() NOT called
  - test_hook3_frozen_flag_set():
      trigger_rollback() → write ProfileSnapshot → assert frozen=True on snapshot
  - test_resume_requires_confirmed_by():
      resume_learning(confirmed_by="") → assert raises ValueError
  - test_rollback_does_not_delete_decision_records():
      Write 5 DecisionRecords → rollback → query Decision nodes → assert 5 still exist
  - test_rollback_does_not_affect_sigma():
      (Stub for synthesis layer — assert no synthesis state changed by rollback)
  - test_max_checkpoints_retained():
      Create 25 checkpoints → query → assert <= 20 returned

Acceptance: Rollback restores μ to checkpoint state exactly.
Hook 2 suspended during frozen window. LEARNING_FROZEN banner visible in Tab 2.
§17.5 trigger conditions all tested. Tests pass.
→ AFTER THIS SHIPS: Run ARCH-3 immediately.
  ARCH-3 tests hook reliability under rollback conditions.
```

---

#### TRUST-2: Shadow Mode Service (v5.5-R8)

```
Repo: soc-copilot
Design spec: soc_copilot_design_v5_4 §21 (full shadow mode spec)

READ FIRST:
  soc_copilot_design_v5_4 §21.1–21.4 — ShadowModeService, ShadowReport, API, UI
  PROD-3 calibration table (from Part 1 §4.2 item B-1) — include in shadow mode docs.
  If PROD-3 has not run: include a placeholder: "Baseline calibration pending PROD-3.
  Expected agreement rate: [run PROD-3 before first customer deployment]."
  Never ship shadow mode to first customer without PROD-3 calibration table.
  Current triage.py — find where decisions are scored and outcomes recorded.

CREATE: backend/app/services/shadow_mode.py

Implement ShadowModeService exactly per soc_copilot_design_v5_4 §21:
  - is_active() → bool
  - get_progress() → dict {active, decisions_recorded, target, pct_complete, report_ready}
  - generate_shadow_report() → ShadowReport
  - activate_live_mode(confirmed_by: str, neo4j) → None

Key constraints:
  - shadow_mode_active stored in SOCDomainConfig.get_shadow_config()["shadow_mode_active"]
  - shadow_decision_count_target from get_shadow_config() (default: 300 decisions)
  - DecisionRecord.shadow_mode = True for all shadow decisions
  - analyst_action and analyst_agreed fields: ALWAYS recorded on shadow decisions
  - NEVER auto-activates live mode. confirmed_by must be non-empty analyst ID.
  - ShadowReport.by_category: computed from Cypher query (per soc_copilot_design_v5_4 §21.2)
  - Top 20 disagreements sorted by confidence DESC (highest-confidence disagreements first)
    Rationale: those are the most actionable — system was confident but wrong.

MODIFY: triage.py — shadow decision write path:
  When shadow_mode is active:
    - Score alert normally (profile scorer runs)
    - Write DecisionRecord with shadow_mode=True, action=scorer_recommendation
    - DO NOT show recommendation to analyst in UI response
    - Record analyst_action from analyst's actual decision (require as API input)
    - Compute analyst_agreed = (scorer_recommendation == analyst_action)
    - Write OutcomeRecord ONLY if analyst_action provided and verified=True
      (Outcome write-back still happens in shadow mode — it's how centroids learn.
       Only the UI recommendation is hidden, not the learning.)

API endpoints per §21.3:
  GET  /api/shadow/status
  GET  /api/shadow/report  (404 if < target decisions)
  POST /api/shadow/activate  (body: {confirm: true, confirmed_by: "analyst_id"})

PROD-3 calibration table integration:
  In ShadowReport: add prod3_baseline field:
    {
      "prod3_baseline": {
        "overall_agreement_rate": 0.XX,  # from PROD-3 result
        "per_category": {...},           # from PROD-3 result
        "note": "Simulation baseline — warm-start centroids, 50-seed validated."
      }
    }
  If PROD-3 has not run: prod3_baseline = None with warning.

TESTS (tests/test_shadow_mode.py — minimum 7 tests):
  - test_shadow_decision_not_shown_in_api_response():
      shadow_mode active → score alert → API response → assert action NOT in response body
  - test_analyst_action_recorded_on_shadow_decision():
      shadow_mode active → record analyst_action="escalate" → query Decision → assert stored
  - test_generate_report_requires_target_threshold():
      < target decisions → generate_shadow_report() → assert raises or returns None
  - test_activate_requires_confirmed_by():
      activate_live_mode(confirmed_by="") → assert raises ValueError
  - test_activate_writes_audit_event():
      activate_live_mode(confirmed_by="analyst_001") → query AuditEvent → assert exists
  - test_progress_pct_correct():
      Write 150 of 300 target decisions → get_progress()["pct_complete"] == 50
  - test_top_disagreements_sorted_by_confidence():
      Write 5 disagreements with varying confidence → report → assert descending order

Acceptance: Shadow mode active = recommendation hidden from UI.
Analyst actions recorded. Shadow report generated after threshold.
ACTIVATE LIVE MODE requires explicit confirmed_by. Audit event written.
```

---

#### TRUST-3: Shadow Mode UI + Report View

```
Repo: soc-copilot
Design spec: soc_copilot_design_v5_4 §21.4 (UI components)

READ FIRST:
  soc_copilot_design_v5_4 §21.4 — ShadowModeBanner, ShadowReportView, ActivateButton
  TRUST-2 must be complete.
  All tab header components — find where to inject the banner.

IMPLEMENT frontend components per §21.4:

  1. ShadowModeBanner — rendered in ALL tab headers when shadow_mode active:
     Visual: dark amber banner across tab top.
     Text: "SHADOW MODE — System observing, not influencing decisions"
     Sub-text: progress bar + "{decisions_recorded} / {target} decisions ({pct_complete}%)"
     "Shadow report will be available at {target} decisions."

  2. ShadowReportView — renders when report_ready = true:
     Sections:
       a. Overall Agreement Score — large number display: "74.3% agreement with analysts"
          Sub-line: "Simulation baseline: {prod3_baseline.overall_agreement_rate:.1%}
                    (warm-start centroids, 50-seed validated)"
          if prod3_baseline is None: "Baseline pending (PROD-3 not yet run)"
       b. Agreement by Category — horizontal bar chart, 5 categories
          Color: green if above baseline, amber if within 5pp, red if below
       c. Top Disagreements table — 20 rows:
          | Alert ID | Category | System Recommended | Analyst Chose | Confidence |
          Each row expandable → shows NL explanation from render_shadow_disagreement()
       d. Recommendation text block (from ShadowReport.recommendation)
       e. ACTIVATE LIVE MODE button:
          - Red border, requires confirmation modal
          - Modal text: "Activating live mode will enable system recommendations
            for all analysts. This cannot be undone without admin intervention.
            Enter your analyst ID to confirm:"
          - Requires typed analyst ID (not just a checkbox)
          - On confirm: POST /api/shadow/activate with {confirm: true, confirmed_by}

  3. After activation:
     - Remove ShadowModeBanner from all tabs
     - Show "LIVE MODE ACTIVE" green badge in Tab 2 header (permanent until next shadow)

TESTS:
  - test_shadow_banner_shows_on_all_tabs():
      shadow_mode=True → render all 5 tabs → assert ShadowModeBanner present in each
  - test_activate_button_requires_typed_id():
      Render ActivateButton → assert confirmation modal has text input → assert empty
      string does not trigger POST

Acceptance: Shadow banner visible across all tabs when active.
Shadow report renders with agreement scores and PROD-3 baseline comparison.
ACTIVATE LIVE MODE requires typed analyst ID in modal. Tests pass.
Q3 partial (agreement rate) and Q4 ("What if it's wrong?") both answerable.
```

---

### Phase 5 [AUTO-APPROVE + COMPOSITE DISCRIMINANT]

**Prereqs:** PROD-4 final complete. DISC-1 complete. ProfileScorer.update()
bug fixed (gt_action_index). Frozen scorer baseline verified.

**What changed from original Phase 5 design:**
Original design used per-category confidence thresholds from PROD-4 targeting
40% coverage. Three findings changed the design:
- PROD-4b: η_neg=1.0 produced catastrophic miscalibration (ECE=0.49).
  All prior PROD-4 threshold values were invalid.
- SHIFT-1/2: ProfileScorer.update() bug found. correct=False pushed ALL
  centroids including ground truth. Fixed: dual push/pull with gt_action_index.
  Post-fix: learning lift +2.7% (was -9%).
- DISC-1: Composite discriminant on frozen scorer outputs achieves 70.4%
  coverage at 85% precision vs 62.6% confidence-only (+7.8pp lift).
  rolling_accuracy is the key compounding signal.

**Architecture:**

```
Alert -> FactorComputers -> f in [0,1]^6
     -> Frozen ProfileScorer(mu_0) -> {probabilities, distances, confidence, margin}
     -> CompositeDiscriminant(
           scorer_features,              <- stable (frozen centroids)
           graph_context_features,       <- compounding (rolling_accuracy, cat_count)
       ) -> P(correct)
     -> if P(correct) >= 0.85 -> AUTO-APPROVE
     -> if ReferralPolicy fires -> REFER TO ANALYST
     -> else -> HUMAN REVIEW
```

**Builds (4 components):**

1. CompositeDiscriminant service (`backend/app/services/composite_gate.py`):
   Accepts ProfileScorer.score() result + category + decision history.
   Computes 13 features: confidence, margin, entropy, top3_mass, prob_std,
   dist_ratio, dist_gap, factor_extremity, factor_norm, factor_center_dist,
   cat_count, rolling_accuracy, decision_position.
   Applies pre-fitted logistic regression weights (from DISC-1 validation),
   OR rule-based conjunction as fallback:
   confidence >= 0.70 AND margin >= 0.30 AND cat_count >= 50.
   Returns: `{auto_approve: bool, approval_score: float, reason_codes: list}`.
   Asymmetric safety: action == suppress requires approval_score >= 0.95.

2. DecisionHistory service (`backend/app/services/decision_history.py`):
   Tracks per-category decision count and rolling accuracy (last 100 decisions).
   Provides cat_count and rolling_accuracy for CompositeDiscriminant.
   Reads from Neo4j DecisionRecord nodes (already exist from Hook 1).
   rolling_accuracy is the strongest orthogonal signal (DISC-1: coef=5.06,
   corr with confidence=0.09).

3. Auto-approve routing in `triage.py`:
   After ProfileScorer.score(), call CompositeDiscriminant.evaluate().
   If auto_approve=True AND (action != suppress OR approval_score >= 0.95):
   write Decision with auto_approved=true, skip analyst queue.
   Else if ReferralPolicy.should_refer(): route to refer_to_analyst.
   Else: HUMAN REVIEW (full analyst investigation).

4. Dashboard integration:
   Tab 4: auto-approve coverage % by category (live counter).
   Tab 4: approval_score distribution histogram.
   Tab 2 Section D: composite gate health (rolling_accuracy per category).

**Calibration numbers (DISC-1, frozen scorer, synthetic):**

| Gate | Coverage 85% prec | Coverage 90% prec | AUC |
|---|---|---|---|
| Confidence only (A) | 62.6% | 0.0% | 0.721 |
| Confidence+margin (B) | 63.4% | 0.2% | 0.720 |
| 7 scorer features (C) | 66.2% | 0.1% | 0.726 |
| +factor features (D) | 66.0% | 2.0% | 0.726 |
| All 13 features (E) | 70.4% | 33.0% | 0.745 |

Per-category coverage (Model E, 85% precision):
data_exfiltration 77.9%, credential_access 74.9%, lateral_movement 70.7%,
cloud_infrastructure 70.0%, threat_intel_match 67.4%, insider_threat 61.5%.

**Learning integration (post-bug-fix, optional per-customer):**
Ship with frozen scorer (μ₀) by default. Shadow mode collects verified
outcomes for composite gate recalibration. If shadow mode shows prior
mismatch (δ>0), enable centroid learning with corrected update rule
(gt_action_index, dual push/pull). Learning adds +1.5% to +2.7% accuracy
lift when prior mismatch exists. Decision to enable learning is per-customer,
after shadow validation.

**IKS v2 (replaces centroid-drift IKS):**

```
IKS_v2(t) = w1*GraphRichness(t) + w2*DecisionMaturity(t)
           + w3*TrustCoverage(t) + w4*FactorQuality(t)
```

Each component monotonically increasing under normal operation.
Validated trajectory (DISC-1): 43 at 50 decisions, 82 at 1000 decisions.

**Acceptance criteria:**
- CompositeDiscriminant service exists and returns approval decisions
- DecisionHistory service tracks per-category rolling accuracy
- Auto-approve routing works end-to-end in triage
- Tab 4 shows per-category auto-approve coverage
- Asymmetric safety gate: suppress requires approval_score >= 0.95
- IKS v2 computation replaces or supplements centroid-drift IKS
- pytest passes (>=111 SOC tests + new tests for composite gate)

**CISO story:**
"The system auto-approves routine alerts where it has proven reliability,
driven by a multi-signal gate that considers confidence, decisiveness, and
the system's track record in each category. Coverage starts conservative
and grows as the system accumulates verified decisions."

**What v5.5 does NOT claim:**
- No "the system learns from every decision" (learning disabled by default)
- No comparison to analyst accuracy without head-to-head data
- No coverage growth promises beyond what shadow mode validates
- No synthetic numbers presented as production performance

---

### Phase 6: Factor Provenance + Threat Graph
**Goal:** Every factor score traces to a specific Neo4j node. IOC memory persists.
**Q closed:** Q5 partial ("Why not Security Copilot?") — firm-specific IOC graph.

---

#### PROV-1: Factor Provenance Nodes (v5.5-R2)

```
Repo: soc-copilot
Design spec: soc_copilot_design_v5_4 §v5.5-R2 (FactorComputerResult + ProvenanceNode)

READ FIRST:
  soc_copilot_design_v5_4 §5.2 — FactorComputer protocol
  All 6 FactorComputer implementations — current return signatures
  EXP-3 must be complete (Tab 3 layout ready for provenance expand/collapse)

MODIFY: backend/app/models/factor_result.py (or wherever FactorComputerResult is defined):

  @dataclass
  class ProvenanceNode:
      node_type: str    # "TravelRecord", "ThreatIndicator", "Decision", "UserNode", "AssetNode"
      node_id: str
      key_property: str # "destination_city"
      key_value: str    # "Singapore"
      contribution: str # "Unconfirmed travel to Singapore — no TravelRecord found in 90 days"

  @dataclass
  class FactorComputerResult:
      value: float
      provenance_nodes: list[ProvenanceNode] = field(default_factory=list)

MODIFY: All 6 FactorComputers — add provenance_nodes to return value:
  For each Cypher query result: build ProvenanceNode from the returned graph nodes.
  Minimum: 1 ProvenanceNode per FactorComputerResult where source nodes are available.
  If no source nodes found: provenance_nodes=[] is acceptable (not an error).

  travel_match FactorComputer:
    ProvenanceNode(node_type="TravelRecord",
                   node_id=travel_record.id if found else "none",
                   key_property="destination_city",
                   key_value=alert.destination_city,
                   contribution="No prior travel record" if score < 0.5 else
                               f"Confirmed travel to {destination} (within 7 days)")

  asset_criticality FactorComputer:
    ProvenanceNode(node_type="AssetNode",
                   node_id=asset.id,
                   key_property="criticality_tier",
                   key_value=asset.criticality_tier,
                   contribution=f"Asset classified as {asset.criticality_tier} criticality")

  (Similarly for threat_intel_enrichment, pattern_history, time_anomaly, device_trust)

MODIFY: Tab 3 factor breakdown — add expand/collapse per factor:
  Each factor row: factor_name + value_bar + ▼ expand button
  Expanded: shows list of ProvenanceNode cards:
    node_type badge | node_id (truncated) | contribution text

TESTS (tests/test_factor_provenance.py — minimum 5 tests):
  - test_all_6_computers_return_provenance_nodes_field():
      Run each FactorComputer → assert result has provenance_nodes attribute
  - test_provenance_nodes_is_list():
      Any FactorComputerResult → assert isinstance(provenance_nodes, list)
  - test_travel_match_names_destination_when_available():
      Alert with destination_city="Singapore" + TravelRecord exists →
      assert "Singapore" in travel_match provenance_nodes[0].key_value
  - test_asset_criticality_names_tier():
      Asset with criticality_tier="critical" → assert "critical" in contribution
  - test_tab3_renders_expand_button_per_factor():
      Tab 3 response → assert expand trigger present for each of 6 factors

Acceptance: All 6 FactorComputers return FactorComputerResult with provenance_nodes.
Tab 3 shows expandable provenance per factor. Tests pass.
```

---

#### PROV-2: ThreatIndicator Persistence (v5.5-R7)

```
Repo: soc-copilot
Design spec: soc_copilot_design_v5_4 §v5.5-R7 + §5.3 (ThreatIntelEnrichmentFactor)

READ FIRST:
  Current ThreatIntelEnrichmentFactor.compute() — find the Pulsedive API call path.
  Check: is ThreatIndicator node created after query? Expected: NO (this is G-L4-3).
  soc_copilot_design_v5_4 §5.3 — threat intel enrichment factor design.

MODIFY: ThreatIntelEnrichmentFactor.compute():

  Pattern: MERGE ThreatIndicator on first query; read on subsequent queries.

  1. Before any API call:
     await neo4j.execute_read("""
       MATCH (ti:ThreatIndicator {ioc_value: $ioc, ioc_type: $type})
       WHERE ti.updated_at > datetime() - duration({hours: 24})
       RETURN ti
     """)
     If found and fresh: use cached node, skip API call.
     Log: "TI_CACHE_HIT: {ioc_value} served from graph (age: {hours}h)"

  2. If not found or stale: call Pulsedive API, then:
     await neo4j.execute_write("""
       MERGE (ti:ThreatIndicator {ioc_value: $ioc, ioc_type: $type})
       SET ti.score = $score,
           ti.last_seen = $last_seen,
           ti.campaigns = $campaigns,
           ti.source = 'pulsedive',
           ti.updated_at = datetime()
       RETURN ti
     """)
     Log: "TI_WRITTEN: {ioc_value} → ThreatIndicator node created/updated"

  3. ProvenanceNode for threat_intel_enrichment:
     ProvenanceNode(node_type="ThreatIndicator",
                    node_id=ti.id,
                    key_property="score",
                    key_value=str(ti.score),
                    contribution=f"IOC {ioc_value} seen in {len(campaigns)} campaigns. "
                                 f"Last active: {last_seen}. Source: Pulsedive.")

MODIFY: Tab 1 header stat block — add IOC count (persistent across all Tab 1 panels):
  Query: MATCH (ti:ThreatIndicator) RETURN count(ti) AS total_iocs,
               count(CASE WHEN ti.updated_at > datetime() - duration({days: 7})
                          THEN 1 END) AS recent_iocs
  Display: "Threat graph: {total_iocs} IOCs. {recent_iocs} seen this week."
  Note: This same query is reused by Tab 5 Section 1 at v6.0 — no rework required.

TESTS (tests/test_threat_indicator.py — minimum 5 tests):
  - test_first_query_writes_threat_indicator_node():
      Fresh Neo4j → compute() with real/mock Pulsedive response →
      query ThreatIndicator → assert node exists
  - test_second_query_uses_cache_no_api_call():
      Write ThreatIndicator fresh → compute() again →
      assert Pulsedive API was NOT called (mock call count = 1)
  - test_stale_node_refreshed():
      Write ThreatIndicator with updated_at > 24h ago → compute() →
      assert Pulsedive API called, node updated_at is fresh
  - test_provenance_node_references_threat_indicator():
      compute() → result.provenance_nodes → assert any node_type=="ThreatIndicator"
  - test_merge_idempotent():
      Call compute() twice for same IOC → query ThreatIndicator →
      assert exactly 1 node (MERGE is idempotent)

Acceptance: Second alert with same IOC reads from graph (no API call).
ThreatIndicator nodes visible in Neo4j browser.
Tab 1 header shows IOC count from graph.
Q5 ("Why not Security Copilot?") partly answerable: "Our threat graph contains X IOCs."
```

---

### Phase 7: Graph Explorer (F14-basic) + SemanticRegistry
**Goal:** Tab 1 Panel B — the analyst Graph Explorer (20+ structured queries, domain-agnostic endpoint, inline decision path). SemanticRegistry and QueryCatalog infrastructure ships here.
**Q closed:** Q5 partial at v5.5 ("Why not Security Copilot?") — threat graph is queryable, IOC count visible.
**Note:** Tab 5 exec learning narrative (three sections) launches at v6.0 — NOT v5.5. The SemanticRegistry concepts and QueryCatalog queries built in BRIEF-1 are the direct data infrastructure for Tab 5 Section 1 at v6.0. No rework required when Tab 5 ships.

---

#### BRIEF-1: Tab 1 Graph Explorer — F14-basic (v5.5-R10)

```
Repo: soc-copilot
Design spec: soc_copilot_design_v5_3 §24 (SemanticRegistry + QueryCatalog + Tab 1 Panel B)

READ FIRST:
  soc_copilot_design_v5_3 §24.0 — Tab 5 vs Tab 1 Panel B distinction
  soc_copilot_design_v5_3 §24.1 — concepts.yaml (20 SOC concepts)
  soc_copilot_design_v5_3 §24.2 — queries.yaml (15 pre-built queries)
  PROV-2 must be complete (IOC count stat needed in Tab 1 header)
  VIS-1 must be complete (IKS stat needed in Tab 1 header)

IMPLEMENT: backend/app/services/semantic_registry.py

  class SemanticRegistry:
      """Domain-agnostic registry for named graph concepts.
      Loaded from soc-copilot/semantics/concepts.yaml at startup.
      Powers Tab 1 Panel B query resolution at v5.5.
      Powers Tab 5 Section 1 data pulls at v6.0 — no rework."""
      
      def resolve(self, concept_name: str, neo4j, params: dict = {}) -> dict:
          """Execute the Cypher template for a named concept. Returns typed result."""

IMPLEMENT: backend/app/services/query_catalog.py

  class QueryCatalog:
      """Loads queries.yaml. Each query has nl_patterns for fast-path routing."""
      
      def find_best_match(self, analyst_query: str) -> str | None:
          """Return query name with highest nl_pattern overlap, or None."""
      
      def execute(self, query_name: str, neo4j, semantic_registry) -> dict:
          """Resolve concept_dependencies via SemanticRegistry, assemble result."""

IMPLEMENT: backend/app/routers/graph_explorer.py

  POST /api/{domain}/query
    Body: {"query": "What is my threat posture on ransomware?"}
    Flow: QueryCatalog.find_best_match() → if match: execute()
          else: return top-3 closest matches with "Did you mean?" prompt
    Returns: {
      "query_name": "threat_posture_this_week",
      "result": { ... },          # structured data
      "nl_summary": str,          # render_l2() or template string
      "decision_path": [          # 2-3 hop mini-graph for provenance
        {"node": "ThreatIndicator", "id": "ti-0047", "label": "CVE-2026-1234"},
        ...
      ],
      "explore_in_bloom_url": "http://localhost:7474/browser/?query=..."
    }
    Cache: per-query TTL from queries.yaml (default: 300 seconds)

  GET /api/{domain}/queries
    Returns: list of available query names + nl_patterns + descriptions
    Used by frontend to populate query suggestion chips.

IMPLEMENT: frontend/src/components/GraphExplorerPanel.tsx
  Tab 1 Panel B — analyst query surface. Information-only tab.
  No shared alert state with Tab 2/Tab 3.
  
  Layout:
    - Search input: "Ask about your threat graph..."
    - Suggestion chips: 6 most common queries (from GET /api/{domain}/queries)
    - Result card: nl_summary + structured data table/chart per output_type
    - Decision path mini-graph (2-3 hop inline, 300px wide)
    - "Explore in Bloom →" deep-link for full graph traversal
    - "No match" state: top-3 suggestions + "Did you mean?" prompt

MODIFY: frontend/src/components/SOCAnalyticsTab.tsx
  Add Panel B section below existing Panel A (Threat Landscape) and Panel C (Factor Detail).
  Panel B heading: "Graph Explorer"
  Renders: <GraphExplorerPanel domain="soc" />

NOTE ON TAB 5 (v6.0):
  The Tab 5 exec learning narrative (three sections: What Changed / What Was Discovered /
  What the System Now Knows) launches at v6.0. BRIEF-1 builds the infrastructure it needs:
  - SemanticRegistry resolves the concepts for Section 1 (IKS delta, centroid drift, volumes)
  - QueryCatalog query results feed Section 1 stat blocks
  - render_centroid_shift() NL output feeds Section 1 "judgment shifts" bullets
  - DiscoveryRule protocol (ci-platform) feeds Section 2 — implemented separately at v6.0
  No rework of BRIEF-1 code is required when Tab 5 ships.

TESTS (tests/test_graph_explorer.py — minimum 6 tests):
  - test_known_query_resolves_correctly():
      POST /api/soc/query with "threat posture this week" →
      assert query_name == "threat_posture_this_week", result non-empty
  - test_unknown_query_returns_suggestions():
      POST /api/soc/query with "random gibberish xyz" →
      assert response contains "suggestions" list, len >= 1
  - test_decision_path_present_in_result():
      POST /api/soc/query → assert "decision_path" list non-empty
  - test_explore_in_bloom_url_valid():
      POST /api/soc/query → assert "explore_in_bloom_url" starts with "http://localhost:7474"
  - test_domain_agnostic_endpoint():
      POST /api/soc/query and POST /api/s2p/query both route correctly
      (s2p may return 404 until s2p copilot ships — that is acceptable)
  - test_query_catalog_loads_15_queries():
      QueryCatalog() → assert len(catalog.queries) == 15

Acceptance: Analyst can type a query in Tab 1 Panel B and receive a structured result
with a decision path mini-graph and "Explore in Bloom" link.
GET /api/{domain}/queries returns all 15 SOC queries.
POST /api/{domain}/query resolves at least 12 of 15 query names correctly by NL pattern.
Tab 1 is information-only — no alert selection state shared with Tab 2/Tab 3.
```

---

### Phase 8: Deployment & Compliance
**Goal:** Docker VPS deployment + compliance export + GAE open-source release.
**External trigger:** v5.5 demo URL goes live. Outreach (Track D) can begin.

---

#### PLAT-1: Docker Compose VPS Deployment (v5.5-R9)

```
Repo: soc-copilot (docker files) + GAE (health endpoint)

READ FIRST:
  product_strategy_v2 §Docker Compose VPS Deployment spec
  Current backend entrypoint — find FastAPI startup path
  Current frontend build — find Vite build output
  Any hardcoded localhost values in backend config (enumerate before creating docker files)

CREATE: docker-compose.yml in soc-copilot root:

version: "3.9"
services:
  backend:
    build: ./backend
    environment:
      - NEO4J_URI=${NEO4J_URI:-bolt://neo4j:7687}
      - NEO4J_USER=${NEO4J_USER:-neo4j}
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
      - FRONTEND_ORIGIN=${FRONTEND_ORIGIN:-https://your-domain.com}
      - PULSEDIVE_API_KEY=${PULSEDIVE_API_KEY:-}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    volumes:
      - ./data/learning_state:/app/learning_state
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    depends_on:
      neo4j:
        condition: service_healthy

  frontend:
    build: ./frontend
    environment:
      - VITE_API_BASE_URL=${VITE_API_BASE_URL:-/api}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000"]
      interval: 30s

  neo4j:
    image: neo4j:5.15
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
      - NEO4J_PLUGINS=["apoc"]
    volumes:
      - neo4j_data:/data
    healthcheck:
      test: ["CMD", "wget", "-q", "-O", "-", "http://localhost:7474"]
      interval: 10s
      retries: 5

  proxy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data

volumes:
  neo4j_data:
  caddy_data:

CREATE: Caddyfile:
  {your-domain.com} {
    reverse_proxy /api/* backend:8000
    reverse_proxy frontend:3000
  }

CREATE: scripts/seed_and_verify.sh:
  #!/bin/bash
  echo "Seeding database..."
  docker compose exec backend python seed.py
  echo "Verifying health..."
  curl -f http://localhost/health && echo "Backend OK"
  curl -f http://localhost && echo "Frontend OK"
  echo "Seed and verify complete."

ADD: GET /health endpoint in backend (if not present):
  Returns: {"status": "ok", "version": "5.5.0", "neo4j": "connected" | "disconnected"}

AUDIT: Remove ALL hardcoded localhost values:
  Search for: localhost:8000, localhost:7687, localhost:3000, 127.0.0.1
  Replace each with: os.getenv("SERVICE_URL", "default") pattern
  Log any remaining hardcoded URLs as a WARNING on startup.

TESTS:
  - test_health_endpoint_returns_200():
      GET /health → assert status_code 200 and "ok" in body
  - test_no_hardcoded_localhost_in_config():
      Grep backend/app/config/ for hardcoded localhost → assert zero hits
  - test_docker_compose_valid_yaml():
      Parse docker-compose.yml → assert valid YAML (yaml.safe_load succeeds)

Acceptance: `docker compose up -d && ./scripts/seed_and_verify.sh` on a clean VPS
produces a running system accessible via HTTPS within 5 minutes.
All service URLs from environment variables.
```

---

#### PLAT-2: Evidence Export (v5.5-R13 + EU AI Act Compliance)

```
Repo: soc-copilot
Design spec: soc_copilot_design_v5_4 §v5.5-R13 + §v5.5-R13 EU AI Act disclosure

READ FIRST:
  soc_copilot_design_v5_4 §v5.5-R13 — N3 endogenous loop disclosure (MANDATORY)
  The August 2026 EU AI Act enforcement deadline.
  Current Tab 4 Evidence Ledger — find where to add export button.

IMPLEMENT: backend/app/services/evidence_export.py

  class EvidenceExportService:
      async def export_decisions(self, neo4j, format: str,
                                  start_date: datetime | None = None,
                                  end_date: datetime | None = None) -> bytes:
          """Export decisions as PDF or CSV. Format: 'pdf' | 'csv'."""

      def _build_compliance_row(self, decision: dict) -> dict:
          """One row per decision for CSV/PDF. Fields per EU AI Act Article 12-13:
          decision_id, timestamp, alert_id, alert_type, category,
          factor_vector, factor_breakdown, action, confidence,
          dispatch_tier, analyst_override (null if none),
          outcome (null if not yet verified), centroid_state_hash (ProfileSnapshot id)
          """

CREATE: docs/eu_ai_act_compliance_template.md

  The following template is included with every v5.5 deployment package.
  Fill in organization name, deployment date, and contact details before submission.

  ## EU AI Act Compliance Evidence — SOC Copilot v5.5

  ### Article 9: Risk Management System

  #### Known Risk: N3 Endogenous Feedback Loop

  > Description: The system's calibration state may influence which decisions are
  > selected for analyst verification (e.g., high-confidence decisions are less
  > likely to be reviewed). If verification selection is systematically biased,
  > Loop 2 (centroid learning) learns from a biased sample of outcomes, which may
  > gradually degrade calibration, which further biases verification selection.
  > This is a self-reinforcing loop with no currently designed intervention point.
  >
  > Current mitigation: Shadow mode deployment (v5.5-R8) provides a 30-day baseline
  > measurement period during which the system's recommendations are compared against
  > analyst decisions on ALL alerts — not just verified ones. Analysis of the shadow
  > report will indicate whether verification selection is systematically biased before
  > live mode is activated.
  >
  > Residual risk level: MEDIUM. Full characterization pending real analyst decision
  > data (EXP-S8, planned for v6.0).

  [... remaining sections: Article 12 logging, Article 13 transparency notice,
  Article 14 human oversight measures, Article 15 robustness measures ...]

  ### Article 12: Logging

  The system maintains an append-only audit log of all decisions. Each log entry contains:
  decision_id, timestamp, alert_id, category, factor_vector, action, confidence,
  analyst_override (if any), outcome (if verified), centroid_state_hash.
  Log format: exportable as CSV or PDF via Tab 4 Evidence Ledger.

  ### Article 13: Transparency Notice

  [PLACEHOLDER — add before first enterprise deployment: contact info, purpose of processing,
  data retention policy, right-to-erasure procedure (v6.0 scope)]

  ### Article 14: Human Oversight Measures

  - Shadow mode provides 30-day observation period before live mode activation.
  - ACTIVATE LIVE MODE requires explicit analyst identity confirmation.
  - Checkpoint/rollback mechanism (TD-033) allows centroid state restoration.
  - All decisions auditable and exportable. No black box.

  ### Article 15: Accuracy and Robustness

  - System accuracy: 71.7% static, 78.9% at 1,000 decisions (50-seed validated).
    Context: SOC analyst agreement rate on identical alerts is 60-70% (consistency, not
    accuracy, is the primary value proposition).
  - Robustness: Centroid clipping [0,1] enforced. Checkpoint/rollback available.
    Synthesis layer disabled by default (λ=0). Requires explicit gate passage to activate.

MODIFY: Tab 4 — add Export Evidence button:
  "Export Evidence Ledger" → opens date range picker → produces PDF/CSV download
  Include: all fields from _build_compliance_row() plus NL explanation from render_l3()

TESTS:
  - test_compliance_template_contains_n3_disclosure():
      Read eu_ai_act_compliance_template.md → assert "N3 Endogenous Feedback Loop" in text
  - test_csv_export_contains_all_required_fields():
      Write 3 decisions → export CSV → parse CSV → assert all required fields present
  - test_export_date_range_filter():
      Write decisions on day 1 and day 10 → export for day 5-10 → assert only day 10 rows

Acceptance: Evidence export button on Tab 4 produces CSV/CSV with all required fields.
EU AI Act compliance template exists with N3 disclosure. Tests pass.
```

---

#### PLAT-3: GAE Open-Source Release (v0.6.0 / PyPI)

```
Repo: GAE (graph-attention-engine)
Design spec: gae_design_v9 §15 (full open-source release spec)

READ FIRST:
  gae_design_v9 §15.1–15.5 — all open-source prep requirements
  gae_design_v9 §15.3 — README required sections (exact spec)
  gae_design_v9 §15.4 — procurement_approval example domain
  gae_design_v9 §15.5 — version 0.6.0 target (v0.5.0 → v0.6.0)
  Current README.md — assess what exists vs what §15.3 requires.
  Current examples/minimal_domain/ — this is the helpdesk example to keep.

CREATE/MODIFY (one concern per file — this prompt covers the complete open-source package):

  1. README.md — complete rewrite per §15.3 spec:
     Sections: tagline, what this is, 30-second quick start, why not dot product,
     validated numbers table (both regimes, labeled), building a new domain, architecture,
     license. Serve three audiences simultaneously (developer, ML practitioner, evaluator).

  2. CONTRIBUTING.md — standard contribution guide:
     How to run tests: pytest -x. How to submit a PR. Code style (black + mypy).
     New domain example as contribution type. CLA not required (Apache 2.0).

  3. CODE_OF_CONDUCT.md — Contributor Covenant (standard text, v2.1).

  4. SECURITY.md — vulnerability reporting:
     Contact: GitHub Security Advisory. No public issue for vulnerabilities.
     Scope: GAE library only (not SOC copilot — that is proprietary).

  5. CHANGELOG.md — from v0.1.0 through v0.5.0:
     Group by version: Added / Changed / Fixed / Removed.
     v0.5.0 entry: ProfileScorer, OracleProvider, Evaluation, Judgment, Ablation. 243 tests.

  6. .github/workflows/ci.yml — GitHub Actions:
     Trigger: push + pull_request on main + dev branches
     Jobs:
       test:   python-version: [3.11, 3.12], runs: pip install -e ".[dev]" && pytest
       lint:   pip install black flake8 mypy && black --check . && flake8 && mypy gae/
     Cache: pip cache between runs.

  7. examples/procurement_approval/ — S2P platform proof (per §15.4):
     3 categories: price_variance, vendor_risk, contract_compliance
     3 actions: approve, escalate, flag
     4 factors: vendor_history, price_deviation, contract_compliance_score, approval_authority
     File: examples/procurement_approval/run.py — runnable demo showing GAE generalizes
     File: examples/procurement_approval/README.md — domain setup walkthrough

  8. Docstring audit — all public classes in gae/__init__.py:
     ProfileScorer, KernelType, ScoringResult, DomainProfileConfig, CalibrationProfile,
     build_profile_scorer, save_profile_state, load_profile_state, OracleProvider,
     run_evaluation, compute_judgment, run_ablation.
     Each must have: purpose, Args, Returns, Example (runnable).

  9. py.typed marker — touch gae/py.typed (PEP 561 compliance).

  10. Setup for PyPI publish:
      Update pyproject.toml: version = "0.6.0", description, keywords, classifiers
      GitHub Topics: machine-learning, knowledge-graph, decision-intelligence, numpy,
                     enterprise-ai, online-learning
      PyPI publish: build + twine upload (user handles the actual publish command —
      this prompt creates the package structure; user runs: python -m build && twine upload)

  11. GitHub Issues templates (.github/ISSUE_TEMPLATE/):
      bug_report.md, feature_request.md, new_domain.md (with domain config template)

TESTS:
  - test_procurement_example_runs_end_to_end():
      python examples/procurement_approval/run.py → assert exits 0, no exceptions
  - test_pyproject_version_is_060():
      Read pyproject.toml → assert version == "0.6.0"
  - test_all_public_symbols_have_docstrings():
      For each symbol in gae/__init__.py.__all__: assert __doc__ is not None
  - test_ci_yaml_valid():
      Parse .github/workflows/ci.yml → assert valid YAML, jobs.test and jobs.lint present

Acceptance: `pip install graph-attention-engine` installs and runs minimal_domain example.
procurement_approval example runs end-to-end.
README serves three audiences as specified in §15.3.
CI passes on push. py.typed present.
```

---

### Phase 9: Tech Debt & Polish
**Goal:** Remove deprecated code, add missing stubs, fix S2P generalization issue.
**Run:** Parallel with Phases 7–8 where possible. All items are independent.

---

#### TD-BATCH: Tech Debt Resolution

```
Repo: GAE + soc-copilot (two separate prompts — one per repo)

--- GAE PROMPT (TD-GAE) ---

READ FIRST: gae_design_v9 §17 (what's built + v5.5 next steps), §16 (hard constraints)

  1. TD-029: Remove ScoringMatrix class from deprecated gae/scoring.py.
     The deprecation warning has been in place since v5.0 (GAE-PROF-4).
     BEFORE removing: grep entire soc-copilot repo for ScoringMatrix imports.
     If any found: STOP. Fix the import in soc-copilot first (in a separate prompt).
     After confirming no external usage: delete gae/scoring.py ScoringMatrix class.
     Keep gae/scoring.py if it contains any non-deprecated utilities; delete file if empty.

  2. TD-031: LayerNorm stub for Level 2 preparation.
     CREATE: gae/layer_norm.py
       class LayerNorm:
           """Layer normalization for embedding vectors. Required for Level 2
           (GraphAttentionBridge) per V1B constraint — 2.9M× norm explosion
           without LayerNorm after 5 sweeps.
           This stub exists to: (a) ensure the import path is reserved,
           (b) allow Level 2 development to begin without changing gae/__init__.py,
           (c) verify that τ_modifier is NOT present (τ_modifier REJECTED per OP series).
           Full implementation deferred to v0.7.0 (GraphAttentionBridge prerequisite).
           """
           def __init__(self, normalized_shape: int):
               # Stub — raises NotImplementedError until v0.7.0
               raise NotImplementedError(
                   "LayerNorm is not implemented in v0.6.0. "
                   "Required for Level 2 (GraphAttentionBridge). "
                   "Implement in v0.7.0 before any cross-domain enrichment.")
     
     ADD test: test_layer_norm_raises_not_implemented_in_v060():
       from gae.layer_norm import LayerNorm
       with pytest.raises(NotImplementedError):
           LayerNorm(64)
     
     ADD test: test_tau_modifier_not_in_gae_public_api():
       import gae
       assert not hasattr(gae, "tau_modifier")
       assert "tau_modifier" not in dir(gae)

  3. EvaluationReport.by_technique → by_category (S2P co-design fix):
     In gae/evaluation.py: rename field by_technique to by_category everywhere.
     In tests: update field name.
     This is a breaking change within 0.x: add to CHANGELOG as "Changed".
     Add backward-compat alias with deprecation warning:
       @property
       def by_technique(self):
           warnings.warn("by_technique is deprecated; use by_category", DeprecationWarning)
           return self.by_category

TESTS (in addition to above):
  - test_scoring_matrix_import_raises():
      try: from gae.scoring import ScoringMatrix → assert ImportError
      (after TD-029 removal)
  - test_evaluation_report_has_by_category():
      run_evaluation() → assert hasattr(report, "by_category")
  - test_evaluation_report_by_technique_deprecated_warning():
      access report.by_technique → assert DeprecationWarning raised

--- SOC PROMPT (TD-SOC) ---

READ FIRST: issue_calibration_table_v3 §1, current soc-copilot codebase

  1. TD-014/015: TimeAnomaly/DeviceTrust property reads (Cypher traversal fix):
     Find: TimeAnomalyFactor and DeviceTrustFactor — check if they read properties
     directly (P10 anti-pattern) instead of traversing relationships.
     Fix any property reads that should be relationship traversals.
     Add test: factor computation traverses relationship, not raw property.

  2. Centroid write access controls:
     Add RBAC check before any centroid update call:
       if not operator.has_permission("centroid_write"):
           logger.error(f"CENTROID_WRITE_DENIED: operator {operator.id}")
           raise PermissionError("Centroid write requires centroid_write permission")
     Add audit log entry on every permitted centroid write:
       AuditEvent: centroid_write, operator_id, category, action, delta_norm, timestamp
     Default permission: SOC admins and system (automatic) have centroid_write.
     Analysts do NOT (they influence centroids via feedback, not direct write).

  3. G-L1-2: Bootstrap distribution uniform (non-uniform in real SOC):
     Current: bootstrap uses equal frequency across all categories.
     Fix: Make bootstrap_category_weights configurable in SOCDomainConfig.
       get_bootstrap_config() returns {"category_weights": {...}, "n_decisions": 1200}
       Default weights: uniform (no behavior change by default).
       Enterprise deployment: override with actual SOC alert distribution.
     Document: "Bootstrap category weights should be calibrated to the firm's
     alert distribution if known. Default uniform weights create an equal prior
     across categories. A firm with 60% credential_access alerts should set
     credential_access weight to 0.6."

Acceptance: All TD items resolved. Tests pass. No regressions in existing test suite.
```

---

## 5. v5.5 Success Criteria

### 5.1 Primary Gate — Five CISO Questions

v5.5 ships when all five are answerable with real product data (not design arguments):

| Question | Evidence Required in Product | Sprint Phase |
|---|---|---|
| Q1: "Does it work?" | NL explanation on every Tab 3 recommendation naming ≥1 real entity. Factor provenance expandable. Similar past cases sidebar when ≥5 prior decisions. | Phase 2 + 6 |
| Q2: "Is it getting smarter?" | IKS score in Tab 2 header with weekly delta and 90-day trend chart. Chart A shows centroid drift events (not ≈0.0). | Phase 3 |
| Q3: "What's the ROI?" | Three-tier dispatch economics in Tab 4 (auto_pct%, refer_pct%, review_pct%, hours_saved/week). Shadow mode realized agreement rate post-activation. | Phase 4 + 5 |
| Q4: "What if it's wrong?" | Shadow report with disagreements and NL explanations. Checkpoint/rollback controls visible in Tab 2 with LEARNING FROZEN banner. | Phase 4 |
| Q5: "Why not Security Copilot?" | IOC count in Tab 1 header ("Your threat graph: X IOCs"). Graph Explorer (Tab 1 Panel B) queryable with 15 pre-built queries. Exec learning narrative (Tab 5 three-section) at v6.0. | Phase 6 + 7 (v5.5 partial) / v6.0 (full) |

### 5.2 Quantitative Targets

| Metric | Target | Source |
|---|---|---|
| Auto-approve coverage | ≥ PROD-4 result (design target: 40%) at ≥85% per-category accuracy | PROD-4 |
| Shadow mode agreement rate | Statable with 95% CI from PROD-3 calibration table | PROD-3 |
| Routing accuracy | Measured by GATE-R (value unknown pre-sprint; must be measured) | GATE-R |
| IKS at first display | ≥ 0 (formula correct); D_MAX calibrated from PROD-1 | PROD-1 |
| Docker VPS deploy time | < 5 minutes on clean VPS | PLAT-1 |
| Graph Explorer query response time | < 2 seconds (P95) | BRIEF-1 |
| NL explanation judge score | Mean Factual Accuracy ≥ 4.0/5.0 (from §23.5 study) | PROD-2 |

### 5.3 Experiment Gates

| Gate | When to Run | Product Impact |
|---|---|---|
| **GATE-R** | Immediately after CORR-1 ships | Routing accuracy measured; CLAIM-01 qualifier becomes precise |
| **PROD-1** | Immediately after VIS-1 ships | D_MAX calibrated; IKS_D_MAX_CALIBRATED flag set to True |
| **PROD-3** | Before first customer sees shadow report | Agreement rate baseline in shadow docs |
| **PROD-4** | Before AUTO-1 prompt runs | Per-category thresholds (not design estimates) |
| **ARCH-3** | After TRUST-1 ships | Hook reliability under rollback verified |

### 5.4 EU AI Act Compliance Gate (August 2026 deadline)

All five EU AI Act article requirements must be in the compliance template before v5.5 ships:
- Article 9: N3 disclosure present (MANDATORY — PLAT-2)
- Article 12: Audit trail exportable (PLAT-2 evidence export)
- Article 13: Transparency notice stub (PLAT-2 — full version v6.0)
- Article 14: Human oversight mechanisms documented (shadow mode + checkpoint/rollback)
- Article 15: Accuracy and robustness documentation (both accuracy regimes, clipping, checkpoint)

---

## 6. v5.5 → Product Strategy Coverage Map

| Sprint Item | Demo Q | Customer Role | product_strategy_v2 Gap | Status After |
|---|---|---|---|---|
| CORR-1 (routing fix, v5.5-R6) | Enables all | All | G-L1-1 (BLOCKING) | GATE-R runnable |
| CORR-2 (bootstrap records) | Q2 substrate | Role 3 | G-L2-3 | IKS baseline accurate |
| CORR-3 (factor_vector native) | Q1 substrate | Role 3 | G-L4-2 | Cosine similarity enabled |
| EXP-1/2/3 (NL template + similar cases, v5.5-R5) | Q1 | Role 1 + 3 | Offering Gap 3 | Q1 answerable |
| VIS-1 (IKS, v5.5-R4) | Q2 | Role 2 | G-L2-2 | Q2 answerable |
| VIS-2 (Chart A fix, v5.5-R3) | Q2 | Role 1 + 2 | G-L2-1 | Compounding visible |
| TRUST-1 (rollback, TD-033) | Q4 | Role 2 + 3 | G-L5, Demo Q4 | Safety visible |
| TRUST-2/3 (shadow mode, v5.5-R8) | Q3 + Q4 | Role 2 | Offering Gap 1 + 2 | Q3 + Q4 answerable |
| AUTO-1 (thresholds, v5.5-R1) | Q3 | Role 2 | G-L5-4 | 40%+ auto-approve |
| AUTO-2 (graduated review) | Q3 | Role 1 | Role 1 critical gap | Analyst relief visible |
| PROV-1 (factor provenance, v5.5-R2) | Q1 | Role 1 + 3 | G-L4-1 | "Show your work" done |
| PROV-2 (ThreatIndicator, v5.5-R7) | Q5 | Role 2 | G-L4-3 + 4 | IOC memory starts |
| BRIEF-1 (Tab 1 Graph Explorer, F14-basic, v5.5-R10) | Q5 | Role 1 + 2 | Offering Gap 2 | Q5 partially answerable (full at v6.0 Tab 5) |
| PLAT-1 (Docker, v5.5-R9) | Q3 deployment | All | Offering Gap 1 | Demo URL live |
| PLAT-2 (compliance, v5.5-R13) | Q4 regulatory | Role 3 | Offering Gap 5 | EU AI Act partial |
| PLAT-3 (PyPI) | Q5 open-source | External dev | Discoverability | Open-source live |
| TD-BATCH | — | Role 3 | TD-029, 031, 014/015 | Code hygiene |

---

## 7. v6.0 Architecture — Gate Matrix

v6.0 design is CONDITIONAL. Sprint prompts are concept-level. Concrete implementations
are written after gate outcomes are known. Gate outcomes determine which of four products ships.

### 7.1 Four Possible Outcomes

| GATE-M | GATE-D | GATE-V | Product | Pricing Tier |
|---|---|---|---|---|
| PASS | PASS | PASS | **Full four-loop intelligence platform.** σ in scoring. Tab 5 fully active (all three sections). σ contribution visible in Section 3 alongside μ. "The system adjusts triage posture based on current threat intelligence." | Enterprise ($500K+/year) |
| PASS | PASS | FAIL | **Enrichment dashboard.** σ computed but display-only in Tab 5 Section 3. Awareness intelligence visible; scoring unchanged. Different ICP: firms wanting intelligence visibility without adaptive triage. | Standard ($200K–400K/year) |
| PASS | FAIL | N/A | **σ validated mathematically, pipeline broken.** Fix EXP-S5a/S5b pipeline issues. Tab 5 launches with Section 1 + Section 2 (no σ display). σ shown as "awareness intelligence" metric once pipeline fixed. | Standard |
| FAIL | N/A | N/A | **Strong institutional memory platform.** Tab 5 launches with Section 1 + Section 2 (learning narrative, no σ). IOC memory + compounding learning arc are the Q5 answer. Reposition: Loop 4 as "future capability in validation." | Standard |

> **"Tab 5 has value at every gate outcome. GATE-M failure is not a product failure."**
>
> The exec learning narrative (Tab 5 three sections), IOC memory, threat graph queryable
> via Tab 1 Graph Explorer, and compounding proof via IKS all ship regardless of GATE-M
> outcome. Only σ's role in the scoring pipeline and its visibility in Tab 5 Section 3
> changes between outcomes.

### 7.2 Gate Conditions (Hard)

**GATE-M passes when ALL FOUR conditions hold:**
1. EXP-S1: Δ_accuracy(λ*) ≥ 3pp, p < 0.0083 (Bonferroni k=6), ECE degradation ≤ +0.02
2. EXP-S2-REPRO Arm A: poisoning ≤ 2pp degradation at 20% bad claims, λ=0.5, Loop 2 running
3. EXP-S2-REPRO Arm B: realistic-AUAC arm passes domain expert review
4. EXP-S3: centroid divergence from Loop 4 contamination ≤ 5%
5. EXP-S4: λ plateau ≥ 0.05 wide

**GATE-D passes when ALL hold:**
1. EXP-S5a: ≥3 σ cells updated from CISA KEV in <60 seconds
2. EXP-S5b: LLM extraction F1 ≥ 0.70 on work artifacts
3. EXP-S5: full pipeline latency < 200ms P95
4. EXP-S6: INTSUM-quality briefing with LLM judge ≥80% claim coverage

**GATE-V passes when:**
- EXP-S8: treatment group ≥3pp improvement over control, overall ≥2pp improvement,
  irrelevant category degradation ≤1pp. Real analyst decision data required.

---

## 8. v6.0 Requirements (Concept Level)

These are design-intent specifications. Concrete sprint prompts will be written after
gate outcomes are known. Sprint sketches are provided where the design is gate-independent.

### v6-R1: Synthesis Layer (GATE-M + GATE-D required)

**Design intent:**
- If GATE-M passes: Eq. 4-synthesis live in scoring pipeline.
  `score(f, category_index, synthesis=sigma[category_index])` uses σ in the distance metric.
  λ parameter configurable in CalibrationProfile. Default at deployment: λ=0.5 (operative window).
- σ tensor updated from: CISA KEV feed (via EXP-S5a pipeline) + vendor advisories +
  ContextConnectors (email/Slack/docs — if EXP-S5b passes) + CISO directives.
- SynthesisProjector: RuleBasedProjector (v6.0, deterministic) → LLMProjector (v6.5, flexible).
- σ_max from FX-1-PROXY-REAL empirical result (p10 of L2 margin distribution). Never hardcode.
- Tab 5 Section 1 enriched with σ: σ contribution to top-3 centroid-relevant claims shown alongside centroid drift summary.
- Tab 1 Graph Explorer (Tab 1 Panel B, F14-full at v6.0): LLM-powered NL → Cypher → NL routing replaces structured-only templates. Synthesis context available in answers.
- If GATE-M fails: σ tensor still computed, stored, displayed in Tab 5 Section 3 as awareness intelligence alongside μ. Does not enter scoring. ProfileScorer.score() signature unchanged (no σ parameter).

**Loop 4 invariants (permanent, regardless of gate):**
- ProfileScorer.update() has NO σ parameter. Ever. Loop 2 + Loop 4 firewall is permanent.
- μ learns ONLY from verified analyst outcomes. σ biases ONLY current scoring.
- σ decays with age (TTL-based, reuses CalibrationProfile decay infrastructure).

**Sprint sketch (if GATE-M passes):**
Phase A (GAE): add optional `synthesis: float | None = None` parameter to ProfileScorer.score().
  When synthesis=None: exact Eq. 4-final (zero regression). When synthesis=sigma: Eq. 4-synthesis.
Phase B (SOC): SynthesisProjectorService, SigmaTensor dataclass, σ update API endpoints.
Phase C (SOC): ContextConnector protocol (if EXP-S5b passed), email/Slack/doc extraction.
Phase D (SOC): Tab 1 Graph Explorer F14-full — LLM NL→Cypher→NL upgrade (upgrades BRIEF-1 endpoint).

---

### v6-R2: Attack Chain Correlation — Blast Radius (always ships)

**Design intent:**
- "If this alert is real, what else is at risk?"
- Multi-hop graph query from alert → affected assets → known CVEs → CISA KEV status.
- Alert dependency graph (G-L4-5) must be built as prerequisite (v5.5 or v6.0 Phase A).
- UI: "Blast radius estimate" in Tab 3 alert detail for escalate-dispatched alerts.
  Shows: affected assets (count), open CVEs, CISA KEV matches, severity distribution.
- No ML component — pure graph traversal. Domain-agnostic (S2P: blast radius = spend exposure).

**Sprint sketch:**
Phase A: Write alert dependency edges to Neo4j: `(alert)-[:MAY_AFFECT]->(asset)`.
Phase B: Implement blast_radius Cypher query from any alert node.
Phase C: Tab 3 "Blast Radius" card on escalation-dispatched alerts.

---

### v6-R3: First Production Customer (hosted deployment)

**Design intent:**
- Customer journey: signs up → shadow mode 30 days → reviews shadow report →
  activates live → 90 days later: auto-approves ~40% at ~87% accuracy.
- Requirements before first customer:
  - v5.5 shadow mode delivered and PROD-3 baseline calibration in docs.
  - Hosted instance on VPS (PLAT-1 Docker complete).
  - Data Processing Agreement (DPA) with customer signed.
  - EU AI Act compliance template (PLAT-2) reviewed by customer's legal team.
  - GATE-R has run (routing accuracy known — customer needs to understand this number).
- The 90-day shadow report from first customer becomes the demo artifact for subsequent customers.

---

### v6-R4: S2P Domain (platform proof)

**Design intent:**
- S2PDomainConfig: procurement categories (price_variance, vendor_risk,
  compliance_exception, contract_violation), actions (approve, escalate, reject, flag,
  refer_to_analyst), factors (vendor_history, price_deviation, contract_compliance,
  approval_authority, risk_score, spend_velocity).
- 10 seed scenarios. Basic Tab UI (Tab 1: procurement alerts, Tab 2: learning, Tab 3: decision).
- Demo goal: "Same learning engine. Different domain. Same accuracy trajectory."
  Show IKS starting at 0 and rising for both SOC and S2P in the same demo session.
- Implementation path: 80% of work is S2PDomainConfig + 6 S2P FactorComputers.
  GAE, ci-platform, and shell infrastructure are already domain-agnostic.
  No changes to GAE. No changes to scoring math. Only DomainConfig + FactorComputers + UI.

**Sprint sketch:**
Phase A: S2PDomainConfig.py with S2P categories, actions, factors, centroid priors.
Phase B: 6 S2P FactorComputers (vendor_history, price_deviation, etc.).
Phase C: Basic S2P tab UI (Tab 1, 2, 3 — reuse SOC tab structure).
Phase D: S2P seed data (10 procurement scenarios).

---

### v6-R5: Multi-SIEM Connector

**Design intent:**
- SourceConnectorProtocol implementations: Splunk, Microsoft Sentinel.
- Alert normalization: vendor-specific format → canonical AlertNode schema.
  Key challenge: different SIEMs use different field names for the same concept.
  Solution: per-SIEM normalization adapter (AlterNormalizationAdapter protocol in ci-platform).
- Entity resolution: same user across two SIEMs → same UserNode in graph.
  Key: normalize user identity (UPN, email, SAM account) to a canonical UserNode.id.
- Gates on: ci-platform SourceConnectorProtocol (Phase 8-9 of v5.0 sprint, already complete).

---

## 9. v6.0 Experiment Track

Experiments that determine what ships at v6.0, and when they run.

### 9.1 GATE-M Timing

GATE-M can be formally declared only after ALL of the following complete:
1. EXP-S2-REPRO Arm 0 (replication check) — can start now
2. FX-1-PROXY-REAL (σ_max derivation) — can start now
3. EXP-S2-REPRO Arm A (operative λ, Loop 2 ON) — after FX-1-PROXY-REAL
4. EXP-S2-REPRO Arm B (realistic-AUAC) + domain expert review — after Arm A
5. EXP-S1 (Δ_accuracy ≥ 3pp) — can start after FX-1-PROXY-REAL (parallel with Arm A)
6. EXP-S3 (μ independence ≤ 5%) — can start now (no FX-1 dependency)
7. EXP-S4 (λ plateau ≥ 0.05 wide) — can start now

Realistic GATE-M timeline: 6–10 weeks after FX-1-PROXY-REAL runs.
GATE-M decision should be made 2–3 months before v6.0 sprint start.
GATE-M decision governs the v6-R1 sprint design — do not write synthesis prompts
before GATE-M is declared.

### 9.2 GATE-D Timing

GATE-D requires v5.5 infrastructure (Tab 1 Graph Explorer live, ContextConnector protocol
built). Run EXP-S5a and EXP-S5b during v5.5 deployment window (parallel with first
customer shadow period). GATE-D decision governs Tab 5 launch depth (full three sections
vs Section 1 + Section 2 only) and F14-full LLM routing implementation.

### 9.3 GATE-V Timing

GATE-V requires first production customer in live mode with real analyst decisions.
Timeline: v6.0 + 3–6 months of production operation. GATE-V is the last gate.

### 9.4 Additional v6.0 Experiments

| Experiment | What It Produces | When to Run |
|---|---|---|
| EXP-G1 (γ validation) | Temporal compounding exponent γ — if γ > 1.0, compounding claim becomes external-facing | After Level 2 pipeline available (v7.0 prerequisite) |
| EXP-L2-1 (cross-domain enrichment) | Does cross-domain enrichment improve SOC scoring? Gate before Level 2 ships. | v7.0 design phase |
| EXP-L2-2 (entity embeddings quality) | Do entity embeddings encode meaningful cross-domain signal? | v7.0 design phase |
| EXP-OP3 (residual tracker) | Early-warning system for centroid drift anomalies | After TD-033 ships (TRUST-1) |
| FX-2 (analyst bias patterns) | Centroid drift bounds under real usage patterns | v5.5 deployment window |
| EXP-OP2-N100 (never-recover CI) | 35% CI too wide at N=20; N=100 narrows the CI | Now (Part 1 §6.1) |

---

## 10. v6.0 Success Criteria

A paying customer has been in production for 90 days. At the 90-day review, all four are true:

| Criterion | Evidence | Gate Required |
|---|---|---|
| Realized ROI | Tab 4: analyst hours saved, auto-approve rate, accuracy today vs deployment | None — from production data |
| Compounding demonstrated | IKS > 20 (meaningful adaptation). At least one category shows accuracy improvement > 3pp vs deployment baseline. | None — from production data |
| Platform claim demonstrated | S2P copilot demo: same IKS trajectory, same learning mechanism, different domain. | v6-R4 ships |
| Synthesis decision made | GATE-M declared with formal outcome. If PASS: σ active in v6.0. If FAIL: Tab 5 Section 3 shows σ as awareness display, repositioned. | GATE-M declared |

**v6.0 release gate:**
1. First production customer in live mode (not shadow) for ≥ 30 days.
2. S2P copilot demo runnable with ≥ 10 procurement scenarios.
3. GATE-M declared (pass or fail — either is acceptable, neither blocks release).
4. Docker deployment stable on customer VPS (no manual intervention for 30 days).
5. EU AI Act Article 13 transparency notice complete (not just a stub).

---

## 11. v6.0 → Product Strategy Coverage Map

| v6.0 Item | Conditional? | Gate | What It Closes |
|---|---|---|---|
| Synthesis layer active in scoring | GATE-M PASS | GATE-M | "System adjusts triage posture from current intelligence" claim |
| Synthesis display-only | GATE-M FAIL | — | "Awareness intelligence" visible in Tab 5 Section 3. Learning narrative (Sections 1 + 2) still ships. Still valuable. |
| ContextConnectors (email/Slack/docs) | GATE-D-EARLY PASS | EXP-S5b | Work artifact → σ pipeline. F13. |
| Tab 1 Graph Explorer F14-full (LLM NL→Cypher→NL) | GATE-D PASS | GATE-D | "Ask your threat graph in natural language." F14. Upgrades BRIEF-1 endpoint. |
| SynthesisNode computational artifact | GATE-V PASS | GATE-V | Full four-loop claim. F15. |
| Attack chain / blast radius | Unconditional | None | Q5 reinforcement. F6. |
| S2P domain | Unconditional | None | Platform claim. "Same engine, different domain." |
| First production customer | Unconditional | None | v6.0 Success Criterion 1. Enables GATE-V. |
| Multi-SIEM connector | Unconditional | None | F5. Enterprise evaluator gap closed. |

**Coverage reminder:** product_strategy_v2 Part 11 maps all five CISO questions to v6.0.
v6.0 adds Q5 ("Why not Security Copilot?") — the full answer requires IOC memory
(v5.5 PROV-2) + threat graph briefing (v5.5 BRIEF-1) + firm-specific learning proof
(IKS > 20 in production). The synthesis story (if GATE-M passes) is the competitive moat
narrative, not the primary Q5 answer.

---

## 12. ICP & Pricing (For Developer Reference)

Every feature decision is filtered through this profile. Keep it in front of mind
when choosing what to build, how to scope, and what to defer.

### Ideal Customer Profile

| Dimension | Target |
|---|---|
| **Size** | 2,000–50,000 employees. Enough alert volume (500+/day) for compounding, not CrowdStrike managed detection scale. |
| **Industry** | Regulated: financial services, healthcare, critical infrastructure, government contractors. Auditability is a compliance requirement, not a nice-to-have. |
| **SOC team** | 10–100 analysts. Inconsistency is visibly a problem. Volume generates learning in 90 days. |
| **SIEM maturity** | 2–5 years post-deployment. Rules tuned for known patterns. Alert fatigue is real. |
| **Trigger event** | Visible incident in past 18 months where post-incident review found "inconsistent triage." Without a recent incident: nice-to-have. With one: addresses a live organizational wound. |

**Anti-ICP (avoid):** CrowdStrike Falcon Complete customers. < 500 alerts/day.
Greenfield SIEM. Academic or research org.

### Pricing

| Tier | Size | Mode | Price |
|---|---|---|---|
| Pilot | < 50 analysts | Shadow mode only, 90 days | $75K–150K/year |
| Standard | 50–200 analysts | Full deployment + Tab 1 Graph Explorer + Tab 5 (v6.0) | $200K–400K/year |
| Enterprise | > 200 analysts or multi-domain | Full + custom integration | $500K+/year |

**Contract commitment:** Customer owns their centroid tensor. Can export it. Can deploy
on alternate infrastructure. This is the "you own the intelligence" commitment made
operationally concrete — and it is the switching cost that differentiates from SaaS.

### The Strategic Bet

> "The moat is the graph, not the model. After 1,000 decisions, the system knows what
> YOUR firm has learned about YOUR environment. Microsoft knows what Microsoft knows.
> CrowdStrike knows what its population knows. We know what you know."

This bet only wins if the accumulation is visible. The IKS is not a vanity metric —
it is proof of the strategic bet. The executive briefing is not a nice-to-have — it is
the mechanism by which the CISO justifies the purchase to their board every quarter.

**The design filter for every v5.5 feature decision:**

> "Is this feature making the compounding more visible, or making the decisions more
> accurate? Both matter. Visibility first — because without it, accuracy improvement
> doesn't close contracts."

---

*Project Status & Plan v3.0 · Part 2 of 2 · March 10, 2026*
*v5.5 Sprint: 9 phases, 18 prompts. Ordered by demo conversion impact.*
*Phase 1 (correctness) → Phase 2 (explainability, Q1) → Phase 3 (IKS, Q2) →*
*Phase 4 (trust, Q4) → Phase 5 (autonomy, Q3) → Phase 6 (provenance) →*
*Phase 7 (Graph Explorer F14-basic, Q5 partial) → Phase 8 (deployment) → Phase 9 (tech debt).*
*v6.0: four gate outcomes, all viable. Tab 5 exec learning narrative has value at every outcome.*
*"v5.5 closes all five questions. v6.0 launches Tab 5 and deepens the moat."*
*Part 1 companion: project_status_and_plan_v3_part1.md*
