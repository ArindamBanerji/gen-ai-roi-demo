# Session Continuation Package v20

**Date:** March 1, 2026
**Status:** v4.1 TAGGED. Product management session COMPLETE. v4.5 prompts finalized. GAE-CAL-1 is NEXT.
**Repos:**
- graph-attention-engine: v0.1.0 tagged (177 tests, Opus-reviewed)
- gen-ai-roi-demo-v4: v4.1 tagged (live GAE charts, 19/19 smoke tests)

**Directories (v4.5 clones):**
- GAE: `C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\graph-attention-engine-v45`
- SOC: `C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v45`

**Environment:** Windows 11, PowerShell. Firefox private window for frontend (avoid caching).

> **Changes from v19:**
> (1) Product management session complete — MVP strategy, INOVA context, math quality as critical success factor.
> (2) **Data collection instrumentation** added to SIM-1, SIM-2, SIM-3a, NAR-2 prompts. Simulation is both feature and experimentation platform.
> (3) **HC-1 (healthcare polish)** added as new prompt — deprioritized below core math/simulation work.
> (4) **TAB2-1/TAB2-2 deferred** within v4.5 — still v4.5 but after simulation + narrative are solid. Not INOVA-blocking.
> (5) **Three new research gaps** identified: convergence ≠ correctness (R1), math-algorithm integration (R2), error-driven discovery (R3).
> (6) **Phase C** remains hard-gated and deferred until Phase A+B are clean. Error-driven discovery design work needed before DISC prompts.
> (7) **GAE backward compatibility NOT required** for v4.5. Simplifies GAE-CAL-1/2.
> (8) **INOVA context captured** — healthcare, Health-ISAC, live laptop demo. But INOVA does NOT drive architecture. Math quality drives architecture.

---

## PART 1: What Just Happened

### v4.1 Sprint (Complete — recap)
- GAE library: 177 tests, 9 modules, Opus-reviewed, Apache 2.0
- SOC copilot: 6 FactorComputers, full pipeline, 10-cycle compounding gate PASSED (28.6x)
- 4 live charts: Weight Evolution, Confidence Trajectory, Before/After, Trust Curve
- Bugs fixed: decision_id, cold-start, convergence threshold, history persistence

### Design Decisions Session (Complete — from v19)
Eight architectural issues resolved. See design_decisions_v1.md.

### Product Management Session (Complete — NEW)
Key conclusions:

**1. Math quality is the critical success factor.** The GAE math must produce demonstrably better decisions than a system without it. Everything else is presentation on top of a foundation that must be rock-solid.

**2. Three loops + math = two layers of intelligence.** The system has formalized math (GAE, Eq. 1-9) and algorithmic loops (SituationAnalyzer, AgentEvolver, ReinforcementGovernor). These currently operate independently. The math scores and learns weights; the loops route alerts, evolve strategies, and verify outcomes. Neither layer models the other. Whether the right path forward is more loops, more math abstractions, or a unified framework is an open research question.

**3. v4.5 simulation is both feature and experimentation platform.** Design it to collect structured data that informs the math-vs-algorithm question at v5.0. Every decision logged with full context. Ground truth embedded in alert pool.

**4. INOVA context.** Healthcare org (Health-ISAC relevant), live laptop demo in 2-4 weeks. But: (a) we ship fast (2-3 days per release), (b) we'll be at v6.0+ before critical discussions, (c) INOVA is not a sophisticated buyer — good IOC ingestion may be sufficient. INOVA does NOT drive architecture.

**5. Healthcare customization kept but deprioritized.** HC-1 prompt added for healthcare alert categories, Health-ISAC seed data, healthcare ROI defaults. But it runs AFTER core simulation + narrative, not before.

**6. GAE as open-source foundation.** Like HuggingFace transformers — the credibility play. Academic engagement requires: reproducible experiments (evaluation framework at v5.0), an open-source engine researchers can run (GAE v0.2.0 at v5.0), and extensibility for experimentation. This informs v5.0 GAE-ENG priorities.

---

## PART 2: Gap Analysis Summary (Updated)

Full analysis in gap_analysis_v4.md. **~50 tracked items** (was 47 in v3).

### Five Critical Gaps — All Have Prompt Assignments (unchanged)

| Gap | v4.5 Phase | Prompts | Status |
|---|---|---|---|
| 1. No simulation mode | Phase A | SIM-FIX through SIM-4 | Prompt ready |
| 2. No ATT&CK | Phase A | SIM-4 | Designed |
| 3. Limited alert corpus | Phase A | SIM-3a/3b | Designed |
| 4. No investigation narrative | Phase B | NAR-1/NAR-2 | Designed |
| 5. No cross-graph discovery | Phase C | DISC-1 through GATE-B3 | HARD GATED — needs error-driven discovery design first |

### Three New Research Gaps (from PM session)

| ID | Gap | Severity | Description | Target |
|---|---|---|---|---|
| R1 | Convergence ≠ correctness | HIGH | Hebbian update converges (proved at v4.1) but we don't know if it converges to the RIGHT weights. Need ground truth measurement. | v4.5 (lightweight: golden scenarios in SIM-3a) + v5.0 (full: EVAL-1) |
| R2 | Math-algorithm integration | RESEARCH | Math (GAE) and algorithmic loops (3 loops) are independent layers. Math can't quantify loop contributions. Ablation at v5.0 will produce first data. | v5.0 (GAE-ABL-1) + ongoing |
| R3 | Error-driven discovery | RESEARCH | Current Eq. 6 finds similar entities (similarity in embedding space). What's needed: entities that would have changed wrong decisions (relevance to decision quality). The error signal from Eq. 4b should drive discovery targeting. | Design work before Phase C. Implementation at v5.5+. |

---

## PART 3: v4.5 Plan — "Make It Real" (Revised)

```
GAE Preamble (2 prompts, GAE repo)        ← CalibrationProfile + per-factor decay
        ↓
Phase A: Simulation Mode (6 prompts)       ← "After ten thousand decisions" proof + instrumentation
        ↓ [PHASE A GATE: 50-decision simulation with clear learning]
Phase B: CISO Readability (2 prompts)      ← Narrative only. Tab 2 rewire deferred.
        ↓
HC-1: Healthcare Polish (1 prompt)         ← For INOVA context. Deprioritized.
        ↓ [Loom v2 recording]
Tab 2 Rewire (2 prompts)                  ← TD-019/TD-020. Not demo-blocking.
        ↓
Phase C: Cross-Graph Discovery (6 prompts, HARD GATED)
        ↓ [TAG v4.5]
```

**Key changes from v19:**
- NAR-1/NAR-2 separated from TAB2-1/TAB2-2. Narrative lands early; Tab 2 rewire deferred.
- HC-1 added after Phase B (healthcare alert categories, Health-ISAC seed data, healthcare ROI).
- Data collection instrumentation on SIM-1, SIM-2, SIM-3a, NAR-2.
- Phase C deferred until Phase A+B clean AND error-driven discovery design work done.
- GAE backward compat not required. Simplifies GAE-CAL-1/2.
- Total: 13 prompts to Loom v2 readiness + 2 for Tab 2 cleanup + 6 for Phase C = 19-21 prompts.

### GAE Preamble (GAE repo — 2 prompts)

| Prompt | What | Gate |
|---|---|---|
| **GAE-CAL-1** | CalibrationProfile dataclass + LearningState refactor. `soc_calibration_profile()`. Backward compat NOT required — can refactor freely. | All 177 tests pass (refactored) + 6 new tests |
| **GAE-CAL-2** | Per-factor decay: epsilon_vector from decay_class_rates × factor name mapping. Three-layer design. | All prior + 4 new tests pass |

GAE-CAL-3 (domain schema) deferred to v5.0.

### Phase A: Simulation Mode + Alert Corpus (6 prompts, SOC repo)

| Prompt | What | Data Collection Addition | Gate |
|---|---|---|---|
| **SIM-FIX** | StateManager with atomic soft/hard reset. POST /api/admin/reset. | — | Reset returns 200. GAE at priors after soft reset. |
| **SIM-1** | SimulationOrchestrator backend. Batch N alerts, same GAE pipeline, Bernoulli oracle, by_category accuracy. | **Structured experiment log**: each decision → `{alert_id, category, situation_type, factor_vector, W_snapshot, predicted_action, confidence, oracle_outcome, correct, timestamp}` | 10-decision API test passes |
| **SIM-2** | Frontend: simulation panel, "Run Simulation" button, progress bar, category learning curve (multi-line), speed control. | **"Download Experiment Log" button** (JSON/CSV export after run) | Charts update during simulation. Category lines diverge. |
| **SIM-3a** | Alert pool: 15-20 alerts across 5 categories. Each activates different dominant factors. | **`ground_truth_action` field** on each alert + **`dominant_factors` metadata**. Enables accuracy measurement against known-correct answers. | 5 categories × 3-4 alerts each |
| **SIM-3b** | Wire expanded pool into orchestrator. PatternHistory differentiates by category. | — | Simulation runs across all categories |
| **SIM-4** | ATT&CK technique IDs on all alerts. Tab 3: technique badge. Tab 1: group by tactic. | — | Technique IDs visible on all alerts |

**Phase A Gate:** 50-decision simulation → clear learning in charts. Category learning curve shows per-category accuracy divergence. Weight evolution shows meaningful progression. Accuracy against ground_truth_action reported. Record 60-second screen capture.

### Phase B: CISO Readability (2 prompts, SOC repo — was 4)

| Prompt | What | Data Collection Addition | Gate |
|---|---|---|---|
| **NAR-1** | NarrativeProvider protocol + TemplateNarrativeProvider + OllamaNarrativeProvider. Graceful degradation. NARRATIVE_PROVIDER env config. | — | Template generates for any alert. Ollama if available. |
| **NAR-2** | Tab 3 narrative panel: 3-5 sentence narrative with "calibrated from N outcomes" line. | **Factor attribution in narrative**: which factors contributed most/least. | Narrative appears with calibration line |

**Phase B Gate:** Narrative with calibration line. **Record Loom v2** (simulation + narrative + charts).

### HC-1: Healthcare Polish (1 prompt, SOC repo — NEW, DEPRIORITIZED)

| Prompt | What | Gate |
|---|---|---|
| **HC-1** | (a) Healthcare-oriented alert categories in SIM-3a pool (clinical access, medical device, ransomware, credential abuse, data exfil). (b) 3-5 Health-ISAC indicators as seed ThreatIntel nodes. (c) Healthcare ROI defaults. (d) 1-2 HIPAA policy rules. | Health-ISAC badge visible in Tab 1. Healthcare ROI defaults load. |

**Note:** HC-1 can be done anytime after Phase A. It's additive, not structural. If SIM-3a already uses healthcare categories (recommended), HC-1 shrinks to just the Health-ISAC seed data + ROI + policy additions.

### Tab 2 Rewire (2 prompts, SOC repo — DEFERRED within v4.5)

| Prompt | What | Gate |
|---|---|---|
| **TAB2-1** | Rewire Tab 2 to GAE pipeline. Remove old agent.decide() path. Close TD-019. | Tab 2 Process Alert uses GAE end-to-end |
| **TAB2-2** | AgentEvolver shows real GAE data. execute_action events fire. Close TD-020. | No dual decision paths remain |

These are tech debt cleanup. Important for product integrity but not visible in CISO conversations.

### Phase C: Cross-Graph Discovery (6 prompts, SOC repo, HARD GATED)

**PREREQUISITE:** Error-driven discovery design work. Current Eq. 6 finds similarity in embedding space. We may need: objective function that finds entities relevant to decision quality, not just similar entities. This design work should happen between Phase B and Phase C execution.

| Prompt | What | Gate |
|---|---|---|
| **DISC-1** | EmbeddingProvider implementations. PropertyEmbeddingProvider (numpy-only). | Embeddings produced |
| **DISC-2** | Cross-graph attention sweep (Eq. 6 — possibly revised after design work). | Sweep runs. Candidates extracted. |
| **DISC-3** | Discovery → expand_weight_matrix integration. New factor registered. | Discovery triggers W expansion |
| **DISC-4** | Scenario seed data: 5 planted discovery patterns. | Patterns in graph |
| **DISC-5** | Tab 4 discovery panel. | UI shows discovery |
| **GATE-B3** | F1 > 0.2 against planted patterns. | Pass or document honestly |

---

## PART 4: Ready-to-Paste Prompts

### Development Rules (EVERY PROMPT)
- Claude Code Sonnet for dev, `/model opus` for code reviews
- Each prompt in a **separate code block**
- Do NOT start the debugger
- Do NOT use git directly
- GAE library: NumPy only, no async, zero domain knowledge
- GAE backward compatibility NOT required for v4.5
- SOC copilot: import from GAE library, factor Cypher queries MUST traverse relationships
- Every prompt includes verification tests
- Language: "product" not "demo" in all comments, docstrings, UI text
- Firefox private window for frontend testing

### GAE-CAL-1 (FIRST prompt — GAE repo)

```
REFERENCE: Read gae/learning.py. Read gae/scoring.py. Read gae/__init__.py.
Read tests/test_learning.py. Read tests/test_scoring.py.

TASK [GAE-CAL-1]: Create CalibrationProfile dataclass. Refactor LearningState 
and score_alert to use it. Backward compatibility is NOT required — refactor freely.

1. Create gae/calibration.py:

   from dataclasses import dataclass, field

   @dataclass
   class CalibrationProfile:
       """Domain-configurable learning hyperparameters.
       
       Replaces hardcoded constants (ALPHA, LAMBDA_NEG, EPSILON_DEFAULT).
       Each domain provides its own profile via DomainConfig.
       """
       learning_rate: float = 0.02        # Was ALPHA
       penalty_ratio: float = 20.0        # Was LAMBDA_NEG
       temperature: float = 0.25          # Was tau parameter
       epsilon_default: float = 0.001     # Was EPSILON_DEFAULT
       discount_strength: float = 0.0     # A1 confirmation bias (0.0 = disabled)
       decay_class_rates: dict = field(default_factory=lambda: {
           "permanent": 0.0001,
           "standard": 0.001,
           "campaign": 0.005,
           "transient": 0.02,
       })
       extensions: dict = field(default_factory=dict)
       
       def validate(self) -> list[str]:
           """Return list of warnings if parameters are out of expected range."""
           warnings = []
           if not (0.001 <= self.learning_rate <= 0.5):
               warnings.append(f"learning_rate {self.learning_rate} outside [0.001, 0.5]")
           if not (1.0 <= self.penalty_ratio <= 100.0):
               warnings.append(f"penalty_ratio {self.penalty_ratio} outside [1.0, 100.0]")
           if not (0.05 <= self.temperature <= 2.0):
               warnings.append(f"temperature {self.temperature} outside [0.05, 2.0]")
           if not (0.0 <= self.discount_strength <= 1.0):
               warnings.append(f"discount_strength {self.discount_strength} outside [0.0, 1.0]")
           return warnings

   def soc_calibration_profile() -> CalibrationProfile:
       """SOC domain defaults. 20:1 penalty, sharp temperature."""
       return CalibrationProfile(
           learning_rate=0.02,
           penalty_ratio=20.0,
           temperature=0.25,
       )

   def s2p_calibration_profile() -> CalibrationProfile:
       """S2P domain defaults. 5:1 penalty, softer temperature."""
       return CalibrationProfile(
           learning_rate=0.01,
           penalty_ratio=5.0,
           temperature=0.4,
       )

2. Refactor gae/learning.py:
   - LearningState.__init__ REQUIRES `profile: CalibrationProfile` (no backward compat needed)
   - Replace self.alpha with self.profile.learning_rate
   - Replace self.lambda_neg with self.profile.penalty_ratio
   - Replace hardcoded epsilon with self.profile.epsilon_default
   - Store self.profile on the instance

3. Refactor gae/scoring.py:
   - score_alert() and score_entity(): accept temperature from CalibrationProfile
   - Get temperature from learning_state.profile.temperature

4. Update gae/__init__.py:
   - Add CalibrationProfile, soc_calibration_profile, s2p_calibration_profile to exports

5. Refactor ALL existing tests to pass CalibrationProfile where LearningState is constructed.
   Since backward compat is not required, every LearningState() call must now include profile=.
   Use default CalibrationProfile() where no specific values needed.

6. Create tests/test_calibration.py:

   Test 1: Default CalibrationProfile creates valid parameters
   Test 2: soc_calibration_profile() has penalty_ratio=20.0
   Test 3: s2p_calibration_profile() has penalty_ratio=5.0
   Test 4: validate() warns on out-of-range parameters
   Test 5: LearningState with soc profile uses profile.learning_rate
   Test 6: score_entity uses profile temperature

GATE: All existing tests pass (refactored to use CalibrationProfile).
Plus 6 new tests in test_calibration.py.
Run: cd C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\graph-attention-engine-v45 && python -m pytest tests/ -v

Do NOT start the debugger. Do NOT use git directly.
```

### GAE-CAL-2 (SECOND prompt — GAE repo)

```
REFERENCE: Read gae/calibration.py (just created in GAE-CAL-1).
Read gae/learning.py (just refactored). Read tests/test_calibration.py.

TASK [GAE-CAL-2]: Add per-factor temporal decay to the learning loop.
Three-layer design: schema declares decay class → profile maps class to rate → learning applies.

1. In gae/calibration.py, add to CalibrationProfile:

   factor_decay_classes: dict = field(default_factory=dict)
   # Maps factor_name → decay_class_name
   # Example: {"threat_intel_enrichment": "campaign", "device_trust": "permanent"}
   # If a factor is not listed, uses "standard" class

2. In gae/learning.py, add method to LearningState:

   def build_epsilon_vector(self) -> np.ndarray:
       """Build per-factor decay vector from profile.
       
       For each factor (by index in factor_names):
         1. Look up decay class from profile.factor_decay_classes (default: "standard")
         2. Look up rate from profile.decay_class_rates
         3. Set epsilon[i] = rate
       Returns: np.ndarray of shape (n_factors,)
       """

3. In the weight update method (update_weights or equivalent):
   - Call build_epsilon_vector() to get per-factor epsilon
   - Replace scalar epsilon with vector epsilon in the decay term
   - W_new[a, i] = W[a, i] + alpha * delta * f[i] - epsilon[i] * W[a, i]
   (instead of uniform epsilon for all factors)

4. Update soc_calibration_profile() in gae/calibration.py:
   Add factor_decay_classes for the 6 SOC factors:
   - pattern_history: "standard"
   - travel_match: "standard"  
   - time_anomaly: "standard"
   - device_trust: "permanent"
   - threat_intel_enrichment: "campaign"
   - asset_criticality: "permanent"

5. Create tests in test_calibration.py (append):

   Test 7: build_epsilon_vector returns correct per-factor rates
   Test 8: Unmapped factor defaults to "standard" rate
   Test 9: campaign-class factor decays faster than permanent-class
   Test 10: With default CalibrationProfile (no factor_decay_classes), all factors get "standard" rate

GATE: All existing tests still pass. Plus 4 new tests.
Run: cd C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\graph-attention-engine-v45 && python -m pytest tests/ -v

Do NOT start the debugger. Do NOT use git directly.
```

### OPUS REVIEW 1 (after GAE-CAL-1 + GAE-CAL-2)

```
/model opus

CODE REVIEW: GAE CalibrationProfile + Per-Factor Decay

Review the following files for correctness, design quality, and test coverage:

1. gae/calibration.py — CalibrationProfile dataclass, convenience constructors
2. gae/learning.py — LearningState refactored to use profile, build_epsilon_vector, per-factor decay
3. gae/scoring.py — temperature from profile
4. tests/test_calibration.py — all new tests
5. gae/__init__.py — exports

Check for:
- Mathematical correctness of per-factor decay in weight update
- Edge cases: empty factor_decay_classes, unknown decay class, zero-length factor vector
- Whether CalibrationProfile.validate() catches all dangerous parameter combinations
- Clean separation: CalibrationProfile has zero domain knowledge (no "SOC" or "S2P" in the dataclass itself)
- Test coverage gaps

Do NOT start the debugger. Do NOT use git directly.
Report findings as: PASS (clean) / PASS WITH NOTES (minor) / NEEDS FIXES (blocking).
```

### SIM-FIX (FIRST SOC prompt — after GAE preamble)

```
REFERENCE: Read CLAUDE.md. Read backend/app/services/gae_state.py.
Read backend/app/routers/demo_api.py (find existing reset-all endpoint).
Read backend/app/services/event_bus.py.

TASK [SIM-FIX]: Fix TD-026 — make reset atomic across GAE state, audit, and Neo4j.

1. Create backend/app/services/state_manager.py:

   class StateManager:
       def __init__(self, learning_state_service, audit_store, neo4j_service, domain_config):
           # Accept generic interfaces — no SOC-specific imports
       
       async def soft_reset(self):
           """Reset learning state to priors. Clear outcomes. Keep graph structure."""
           # 1. W → priors from domain_config
           # 2. history/decision_count cleared
           # 3. Neo4j: clear outcomes on Decision nodes (keep nodes)
           # 4. Audit: RESET marker + new chain
           # If any step fails: raise ResetError (no partial state)
       
       async def hard_reset(self):
           """Full reset. Delete decisions. Re-seed graph."""
           # Steps 1-4 from soft_reset
           # + Neo4j: delete Decision nodes
           # + Re-seed graph

2. Create backend/app/routers/admin.py:
   POST /api/admin/reset  Body: {"mode": "soft"|"hard", "confirm": true}
   - Requires confirm=true (safety check)
   - Returns: {"status": "reset_complete", "mode": "soft|hard", "learning_state": {W_shape, decision_count}}
   Register in main.py.

3. Update existing reset-all endpoint in demo_api.py to delegate to StateManager.hard_reset().
   Do not break existing frontend reset button.

TESTS:
   # Test 1: Import
   cd backend && python -c "
   from app.services.state_manager import StateManager
   print('StateManager imported OK')
   print('TEST 1 PASS')
   "

   # Test 2: Soft reset API (server must be running)
   curl -s -X POST http://localhost:8000/api/admin/reset -H "Content-Type: application/json" -d "{\"mode\": \"soft\", \"confirm\": true}"
   # Should return 200 with reset_complete status

   # Test 3: Hard reset API
   curl -s -X POST http://localhost:8000/api/admin/reset -H "Content-Type: application/json" -d "{\"mode\": \"hard\", \"confirm\": true}"
   # Should return 200

   # Test 4: Reject without confirm
   curl -s -X POST http://localhost:8000/api/admin/reset -H "Content-Type: application/json" -d "{\"mode\": \"soft\", \"confirm\": false}"
   # Should return 400

Do NOT start the debugger. Do NOT use git directly.
```

### SIM-1 (SimulationOrchestrator — with data collection instrumentation)

```
REFERENCE: Read CLAUDE.md. Read backend/app/routers/triage.py (the real GAE pipeline).
Read backend/app/services/gae_state.py. Read backend/app/services/state_manager.py (just created).
Read backend/app/domains/soc/config.py (SOCDomainConfig).

TASK [SIM-1]: Create SimulationOrchestrator — batch N alerts through the SAME GAE pipeline.

CRITICAL: The simulation must use the EXACT same code path as manual triage.
No separate scoring logic. No shortcuts. The simulation is the triage pipeline on auto-pilot.

1. Create backend/app/services/simulation.py:

   class SimulationOrchestrator:
       """Runs batch simulation through the real GAE pipeline.
       
       Each simulated decision follows the same path as a manual triage:
       alert → classify_situation → compute_factors → score_entity → decide → outcome → update_weights
       """
       
       def __init__(self, state_manager, triage_service, domain_config):
           self.experiment_log = []  # Structured data collection
       
       async def run(self, n_decisions: int, alert_pool, speed_ms: int = 200) -> SimulationResult:
           """Run n_decisions through the GAE pipeline.
           
           For each decision:
             1. Pick alert from pool (round-robin across categories)
             2. Run through SAME pipeline as POST /api/triage/analyze
             3. Select action from GAE scoring (highest score)
             4. Generate outcome: Bernoulli oracle with category-specific success rates
             5. Feed outcome back through SAME pipeline as POST /api/triage/feedback
             6. Log structured experiment record
             7. Emit progress event
           """
       
       def _log_decision(self, alert, situation, factor_vector, W_snapshot, 
                         action, confidence, outcome, correct):
           """Append structured record to experiment_log.
           
           Record: {
               step: int,
               timestamp: iso8601,
               alert_id: str,
               category: str,
               situation_type: str,
               attack_technique: str,
               factor_vector: list[float],
               W_snapshot: list[list[float]],  # Full weight matrix at decision time
               predicted_action: str,
               confidence: float,
               oracle_outcome: int,  # 1 or -1
               correct: bool,
               cumulative_accuracy: float,
               category_accuracy: dict[str, float],
           }
           """

   @dataclass
   class SimulationResult:
       n_decisions: int
       overall_accuracy: float
       category_accuracy: dict  # {category: accuracy}
       weight_trajectory: list  # W snapshots at each step
       experiment_log: list     # Full structured log
       duration_seconds: float

2. Create backend/app/routers/simulation.py:
   
   POST /api/simulation/start  Body: {"n_decisions": 50, "speed_ms": 200}
   - Calls state_manager.soft_reset() first
   - Starts simulation in background task
   - Returns: {"simulation_id": uuid, "status": "running"}
   
   GET /api/simulation/progress/{simulation_id}
   - Returns: {"step": N, "total": 50, "status": "running"|"complete",
              "current_accuracy": 0.72, "category_accuracy": {...},
              "latest_weight_snapshot": [...]}
   
   GET /api/simulation/result/{simulation_id}
   - Returns full SimulationResult (only when complete)
   
   GET /api/simulation/experiment-log/{simulation_id}
   - Returns experiment_log as JSON array (for download)
   
   Register in main.py.

3. Alert pool: For now, use existing alerts from SOCDomainConfig. 
   SIM-3a will expand this later. The orchestrator accepts any alert pool 
   that provides alerts with {alert_id, alert_type, category, context}.

TESTS:
   # Test 1: Import
   cd backend && python -c "
   from app.services.simulation import SimulationOrchestrator, SimulationResult
   print('SimulationOrchestrator imported OK')
   print('TEST 1 PASS')
   "

   # Test 2: Start simulation API (server running, 5 decisions for speed)
   curl -s -X POST http://localhost:8000/api/simulation/start -H "Content-Type: application/json" -d "{\"n_decisions\": 5, \"speed_ms\": 100}"
   # Should return 200 with simulation_id

   # Test 3: Check progress (use simulation_id from Test 2)
   # Wait 2 seconds, then:
   curl -s http://localhost:8000/api/simulation/progress/{simulation_id}
   # Should show step > 0

   # Test 4: Get result (wait for completion)
   curl -s http://localhost:8000/api/simulation/result/{simulation_id}
   # Should show overall_accuracy and category_accuracy

   # Test 5: Get experiment log
   curl -s http://localhost:8000/api/simulation/experiment-log/{simulation_id}
   # Should return JSON array with structured records

Do NOT start the debugger. Do NOT use git directly.
```

### SIM-2 (Frontend simulation panel)

```
REFERENCE: Read the frontend source. Find the Tab 4 (Compounding Metrics) component.
Read backend/app/routers/simulation.py (just created).

TASK [SIM-2]: Add simulation panel to the frontend with real-time chart updates.

1. Create a SimulationPanel component (can go in Tab 4 or as a new section):

   - "Run Simulation" button with configurable N (dropdown: 10, 25, 50, 100)
   - Speed control (slider: 100ms to 1000ms per decision)
   - Progress bar showing step/total
   - Status indicator: "Running..." / "Complete"
   
2. Category Learning Curve chart (multi-line Recharts LineChart):
   - X-axis: decision number (1 to N)
   - Y-axis: accuracy (0% to 100%)
   - One line per alert category (5 lines, different colors)
   - Updates in real-time as simulation progresses
   - Poll GET /api/simulation/progress/{id} every 500ms while running
   
3. After simulation completes:
   - Show summary: overall accuracy, per-category accuracy, duration
   - "Download Experiment Log" button → GET /api/simulation/experiment-log/{id}
     Download as JSON file (simulation_log_{timestamp}.json)
   - Existing Weight Evolution / Confidence / Trust Curve charts should
     reflect the simulation results (they read from GAE state which was updated)

4. While simulation is running:
   - Disable manual triage (prevent concurrent modification)
   - Show which alert is currently being processed

TESTS:
   # Test 1: Start frontend, navigate to simulation panel
   # "Run Simulation" button should be visible
   
   # Test 2: Run 10-decision simulation
   # Progress bar should advance. Category learning curve should show lines appearing.
   
   # Test 3: After completion, click "Download Experiment Log"
   # JSON file should download with structured records.
   
   # Test 4: Check that Weight Evolution chart (existing) reflects simulation results
   # Weights should NOT be at initial priors.

Frontend testing: Use Firefox private window to avoid caching.
Do NOT start the debugger. Do NOT use git directly.
```

### SIM-3a (Alert pool expansion — with ground truth)

```
REFERENCE: Read backend/app/domains/soc/config.py. Read backend/app/domains/soc/situations.py.
Read the existing alert seed data in backend/app/data/ or wherever alerts are defined.

TASK [SIM-3a]: Expand alert pool to 15-20 alerts across 5 categories.
Each alert includes ground_truth_action and dominant_factors metadata.

1. Define 5 alert categories with 3-4 alerts each:

   Category 1: Credential/Access Anomaly (ATT&CK: T1078 Valid Accounts)
   - Dominant factors: pattern_history, time_anomaly
   - Examples: After-hours access from unusual location, privilege escalation attempt,
     shared credential detected
   - ground_truth: escalate (most), investigate (if pattern is new)

   Category 2: Threat Intel Match (ATT&CK: T1566.001 Phishing)
   - Dominant factors: threat_intel_enrichment, asset_criticality
   - Examples: Phishing email with known-bad URL, malware hash match from feed,
     C2 beacon pattern detected
   - ground_truth: escalate (high confidence match), investigate (partial match)

   Category 3: Lateral Movement (ATT&CK: T1021.001 Remote Services)
   - Dominant factors: device_trust, pattern_history, asset_criticality
   - Examples: Unusual RDP to critical server, service account pivoting,
     admin tool used from non-admin workstation
   - ground_truth: escalate (critical asset), investigate (standard asset)

   Category 4: Data Exfiltration (ATT&CK: T1567 Exfil Over Web Service)
   - Dominant factors: asset_criticality, time_anomaly, pattern_history
   - Examples: Large upload to cloud storage, DNS tunneling detected,
     bulk database query from unusual source
   - ground_truth: escalate (all — data loss is high-impact)

   Category 5: Insider/Behavioral (ATT&CK: T1048 Exfil Over Alternative Protocol)
   - Dominant factors: pattern_history, time_anomaly, travel_match
   - Examples: Access pattern change after HR event, off-hours bulk access,
     travel-impossible login
   - ground_truth: investigate (most — insider cases need human judgment)

2. Each alert is a dict with:
   {
     "alert_id": "ALT-001",
     "alert_type": "after_hours_access",
     "category": "credential_access",
     "description": "User jsmith accessed EHR system at 2:47 AM from VPN",
     "severity": "high",
     "attack_technique": "T1078",
     "attack_tactic": "Initial Access",
     "dominant_factors": ["pattern_history", "time_anomaly"],
     "ground_truth_action": "escalate",
     "context": { ... Neo4j-relevant fields ... }
   }

3. Create backend/app/data/alert_pool.py (or .json):
   - Export ALERT_POOL: list of all 15-20 alerts
   - Export ALERT_CATEGORIES: dict mapping category → list of alert_ids
   - Each category has distinct dominant_factors (this is what makes learning curves diverge)

4. Wire into SimulationOrchestrator:
   - SimulationOrchestrator accepts alert_pool parameter
   - Default: load from alert_pool.py
   - Round-robin across categories (not random — ensures balanced exposure)

5. Ensure each alert has enough Neo4j context for FactorComputers to work:
   - Seed data must include the entities, relationships, and properties
     that the 6 FactorComputers need to produce non-zero values
   - Each category should produce DIFFERENT factor vectors (this is key)

TESTS:
   # Test 1: Import alert pool
   cd backend && python -c "
   from app.data.alert_pool import ALERT_POOL, ALERT_CATEGORIES
   print(f'Total alerts: {len(ALERT_POOL)}')
   print(f'Categories: {list(ALERT_CATEGORIES.keys())}')
   for cat, ids in ALERT_CATEGORIES.items():
       print(f'  {cat}: {len(ids)} alerts')
   assert len(ALERT_POOL) >= 15
   assert len(ALERT_CATEGORIES) == 5
   print('TEST 1 PASS')
   "

   # Test 2: Every alert has required fields
   cd backend && python -c "
   from app.data.alert_pool import ALERT_POOL
   required = ['alert_id', 'category', 'attack_technique', 'dominant_factors', 'ground_truth_action']
   for alert in ALERT_POOL:
       for field in required:
           assert field in alert, f'{alert[\"alert_id\"]} missing {field}'
   print('All alerts have required fields')
   print('TEST 2 PASS')
   "

   # Test 3: Categories have distinct dominant factors
   cd backend && python -c "
   from app.data.alert_pool import ALERT_POOL, ALERT_CATEGORIES
   cat_factors = {}
   for alert in ALERT_POOL:
       cat = alert['category']
       if cat not in cat_factors:
           cat_factors[cat] = set()
       cat_factors[cat].update(alert['dominant_factors'])
   # At least some categories should differ
   factor_sets = list(cat_factors.values())
   unique_sets = len(set(frozenset(s) for s in factor_sets))
   print(f'Unique factor signatures: {unique_sets} across {len(factor_sets)} categories')
   assert unique_sets >= 3, 'Need at least 3 distinct factor signatures'
   print('TEST 3 PASS')
   "

Do NOT start the debugger. Do NOT use git directly.
```

### SIM-3b (Wire alert pool to orchestrator)

```
REFERENCE: Read backend/app/services/simulation.py (SimulationOrchestrator).
Read backend/app/data/alert_pool.py (just created).
Read backend/app/domains/soc/situations.py (situation classifier).

TASK [SIM-3b]: Wire expanded alert pool into SimulationOrchestrator.
PatternHistory must differentiate by category.

1. Update SimulationOrchestrator.run():
   - Load ALERT_POOL as default pool
   - Round-robin across categories: cycle through categories, pick next alert from each
   - Pass alert context to situation classifier → factor computers → scoring
   - The simulation pipeline must produce DIFFERENT factor vectors for different categories

2. Update Bernoulli oracle:
   - Category-specific base rates (some categories are "easier" to learn):
     credential_access: 0.75 (clear patterns)
     threat_intel: 0.80 (strong signal from IOC match)  
     lateral_movement: 0.60 (harder to classify)
     data_exfil: 0.70
     insider_behavioral: 0.55 (hardest — requires judgment)
   - These rates make the learning curves diverge naturally

3. After simulation, report:
   - accuracy_vs_ground_truth: compare predicted action to ground_truth_action
   - This is separate from oracle accuracy — it measures whether GAE converges
     to the RIGHT answer, not just whether it converges

4. Update progress endpoint to include category_accuracy breakdown:
   GET /api/simulation/progress returns category_accuracy as it evolves

TESTS:
   # Test 1: Run 25-decision simulation and verify all categories appear
   curl -s -X POST http://localhost:8000/api/simulation/start -H "Content-Type: application/json" -d "{\"n_decisions\": 25, \"speed_ms\": 50}"
   # Wait for completion, then check result:
   # category_accuracy should have entries for all 5 categories

   # Test 2: Verify category accuracy divergence
   # After 50 decisions, categories with higher base rates should show higher accuracy
   
   # Test 3: Verify ground_truth comparison in experiment log
   # Each record should have "correct_vs_ground_truth" field

Do NOT start the debugger. Do NOT use git directly.
```

### SIM-4 (ATT&CK technique IDs)

```
REFERENCE: Read backend/app/data/alert_pool.py (has attack_technique on each alert).
Read backend/app/domains/soc/situations.py (has MITRE_ATTACK_MAP).
Read frontend Tab 3 component. Read frontend Tab 1 component.

TASK [SIM-4]: Make ATT&CK technique IDs visible throughout the UI.

1. Backend: Ensure triage response includes attack_technique and attack_tactic
   from the alert pool data. The data is already there from SIM-3a — 
   just pass it through to the API response.

2. Tab 3 (Situation Analyzer / Decision Panel):
   - Add technique badge: "T1078 — Valid Accounts" next to alert header
   - Small colored badge, not intrusive. Just factual.

3. Tab 1 (Threat Landscape):
   - Add "By ATT&CK Tactic" grouping option or section
   - Show: Initial Access (3 alerts), Lateral Movement (2), Exfiltration (4), etc.
   - This uses the attack_tactic field from alert pool

4. Tab 4 (if simulation panel is there):
   - Category learning curve legend should show ATT&CK technique alongside category name
   - Example: "Credential Access (T1078)" as the legend label

TESTS:
   # Test 1: Triage an alert, verify technique in response
   # Process an alert via Tab 3, check that technique badge appears

   # Test 2: Tab 1 shows ATT&CK grouping
   # Navigate to Tab 1, verify tactic grouping is visible

   # Test 3: Simulation category labels include technique IDs
   # Run simulation, check that legend shows technique IDs

Frontend testing: Use Firefox private window.
Do NOT start the debugger. Do NOT use git directly.
```

### NAR-1 (NarrativeProvider)

```
REFERENCE: Read backend/app/domains/soc/config.py.
Read backend/app/services/gae_state.py.

TASK [NAR-1]: Create NarrativeProvider protocol with two implementations.

1. Create backend/app/services/narrative.py:

   from typing import Protocol

   class NarrativeProvider(Protocol):
       async def generate(self, alert, decision, factors, calibration_context) -> str:
           """Generate investigation narrative for a triage decision."""
           ...

   class TemplateNarrativeProvider:
       """Always works. No external dependencies. Fallback."""
       
       async def generate(self, alert, decision, factors, calibration_context) -> str:
           """Template-based narrative.
           
           Example output:
           'This {alert_type} alert was evaluated using {n_factors} weighted factors.
           The dominant factor was {top_factor} (weight: {top_weight:.2f}), which
           reflects {factor_description}. The recommended action is {action} with
           {confidence:.0%} confidence. This recommendation is calibrated from
           {decision_count} verified outcomes on similar alerts.'
           
           calibration_context includes:
           - decision_count: total verified outcomes
           - category_count: outcomes for this specific category
           - weight_trajectory: how weights have changed
           """

   class OllamaNarrativeProvider:
       """Uses local Ollama (Qwen) for richer narratives. Graceful fallback."""
       
       def __init__(self, model="qwen2.5:3b", fallback=None):
           self.fallback = fallback or TemplateNarrativeProvider()
       
       async def generate(self, alert, decision, factors, calibration_context) -> str:
           try:
               # Call Ollama API (localhost:11434)
               # System prompt: "You are a SOC analyst writing an investigation summary..."
               # Include factor breakdown and calibration context in prompt
               # Response must include the calibration line
               ...
           except Exception:
               return await self.fallback.generate(alert, decision, factors, calibration_context)

2. Configuration via environment variable:
   NARRATIVE_PROVIDER=template  (default, always works)
   NARRATIVE_PROVIDER=ollama    (uses Ollama with template fallback)

3. Register in app startup (main.py or config):
   narrative_provider = create_narrative_provider(os.getenv("NARRATIVE_PROVIDER", "template"))

TESTS:
   # Test 1: Import
   cd backend && python -c "
   from app.services.narrative import TemplateNarrativeProvider, OllamaNarrativeProvider
   print('NarrativeProvider imported OK')
   print('TEST 1 PASS')
   "

   # Test 2: Template generates narrative
   cd backend && python -c "
   import asyncio
   from app.services.narrative import TemplateNarrativeProvider
   provider = TemplateNarrativeProvider()
   result = asyncio.run(provider.generate(
       alert={'alert_type': 'suspicious_login', 'category': 'credential_access'},
       decision={'action': 'escalate', 'confidence': 0.87},
       factors={'pattern_history': 0.82, 'time_anomaly': 0.65, 'device_trust': 0.3},
       calibration_context={'decision_count': 23, 'category_count': 8}
   ))
   print(result)
   assert 'calibrated' in result.lower() or 'verified' in result.lower()
   assert '23' in result or '8' in result
   print('TEST 2 PASS')
   "

   # Test 3: Ollama falls back to template if Ollama not running
   cd backend && python -c "
   import asyncio
   from app.services.narrative import OllamaNarrativeProvider
   provider = OllamaNarrativeProvider()
   result = asyncio.run(provider.generate(
       alert={'alert_type': 'suspicious_login', 'category': 'credential_access'},
       decision={'action': 'escalate', 'confidence': 0.87},
       factors={'pattern_history': 0.82},
       calibration_context={'decision_count': 23, 'category_count': 8}
   ))
   print(result)
   print('TEST 3 PASS (graceful fallback)')
   "

Do NOT start the debugger. Do NOT use git directly.
```

### NAR-2 (Tab 3 narrative panel)

```
REFERENCE: Read frontend Tab 3 component (Situation Analyzer / Decision Panel).
Read backend/app/routers/triage.py (triage response structure).
Read backend/app/services/narrative.py (just created).

TASK [NAR-2]: Add investigation narrative to Tab 3 with factor attribution.

1. Backend: After triage scoring, call narrative_provider.generate() with:
   - The alert data
   - The decision (action + confidence)
   - The factor breakdown (all 6 factors with values)
   - Calibration context: {decision_count, category_count from history}
   Add narrative field to triage response JSON.

2. Frontend Tab 3: Add narrative panel below the factor breakdown:
   - Card/section titled "Investigation Summary"
   - Display the 3-5 sentence narrative
   - The "calibrated from N verified outcomes" line should be visually distinct
     (slightly different styling — not bold, but noticeable)
   - Below narrative: factor attribution summary
     "Dominant factor: pattern_history (0.82). Least influential: device_trust (0.12)."
   
3. Factor attribution data: Include in narrative response
   - top_factor: name and value of highest-weight factor
   - bottom_factor: name and value of lowest-weight factor
   - This is qualitative data useful for understanding algorithm behavior

TESTS:
   # Test 1: Triage an alert via API, check narrative in response
   # Response should include "narrative" field with calibration line

   # Test 2: View Tab 3 in browser after analyzing an alert
   # "Investigation Summary" section should appear with narrative text
   # Calibration line should be visible

   # Test 3: Factor attribution visible
   # Dominant and least influential factors shown

Frontend testing: Use Firefox private window.
Do NOT start the debugger. Do NOT use git directly.
```

---

## PART 5: Published Assets (unchanged from v19)

### Live Blog Posts
| Post | URL | Update Needed |
|---|---|---|
| Demo blurb (v3.1) | https://www.dakshineshwari.net/post/after-ten-thousand-decisions-show-me-how-your-system-got-smarter-v3-1 | After Phase A: simulation screenshots |
| CI blog (v4.0) | https://www.dakshineshwari.net/post/compounding-intelligence-4-0-how-enterprise-ai-develops-self-improving-judgment | After Phase C (if gate passes) |
| Math blog | https://www.dakshineshwari.net/post/cross-graph-attention-mathematical-foundation-with-experimental-validation | No update needed |
| Loom v1 | https://www.loom.com/share/b45444f85a3241128d685d0eaeb59379 | Record v2 after Phase B |

---

## PART 6: Open Research Questions (NEW)

These are not bugs or gaps with known solutions. They are open questions that require experimentation to answer. They inform the v5.0+ roadmap.

**RQ1: Does the Hebbian update converge to correct decisions, or just stable ones?**
- First data: v4.5 Phase A (ground_truth_action comparison in simulation)
- Full answer: v5.0 evaluation framework (30-40 scenarios with planted correct answers)
- If convergence ≠ correctness: may need augmented learning rule at v5.5

**RQ2: How much do the three loops contribute vs. the math?**
- First data: v5.0 ablation (full system vs. no-loops vs. no-math vs. static)
- The ablation tells us: is the math the dominant factor, or is situation classification doing most of the work?
- If loops dominate: the math needs strengthening. If math dominates: the loops need tighter integration.

**RQ3: Should discovery be error-driven rather than similarity-driven?**
- Current design: Eq. 6 finds similar entities in embedding space
- Alternative: find entities that would have changed high-confidence wrong decisions
- This changes the objective function for cross-graph attention
- Design work needed before Phase C. May result in revised Eq. 6.
- If error-driven discovery works better: update the math blog.

---

## PART 7: Execution Order Summary (REVISED)

```
GAE PREAMBLE (GAE repo):
  1. GAE-CAL-1 (CalibrationProfile)           ← NEXT PROMPT
  2. GAE-CAL-2 (per-factor decay)
  3. /model opus review

PHASE A — SIMULATION (SOC repo):
  4. SIM-FIX (atomic reset + TD-026)
  5. SIM-1 (SimulationOrchestrator + experiment log)
  6. SIM-3a (alert pool + ground truth)
  7. SIM-3b (wire pool to orchestrator)
  8. SIM-4 (ATT&CK technique IDs)
  9. SIM-2 (frontend simulation panel + download)
  10. /model opus review — PHASE A GATE

PHASE B — NARRATIVE (SOC repo):
  11. NAR-1 (NarrativeProvider)
  12. NAR-2 (Tab 3 narrative panel + factor attribution)
  [LOOM V2 RECORDING — simulation + narrative + charts]

HEALTHCARE POLISH (SOC repo, deprioritized):
  13. HC-1 (healthcare alerts, Health-ISAC seed, ROI, HIPAA policies)

TAB 2 CLEANUP (SOC repo, deferred):
  14. TAB2-1 (Tab 2 GAE rewire, close TD-019)
  15. TAB2-2 (AgentEvolver GAE data, close TD-020)

PHASE C — DISCOVERY (SOC repo, HARD GATED):
  [Error-driven discovery design session first]
  16-21. DISC-1 through GATE-B3
  [TAG v4.5]

PARALLEL TRACK (outreach):
  - Demo blurb update (after Phase A)
  - LinkedIn post: simulation proof (after Phase A)
  - Outreach emails v7 (after Phase A)
  - Loom v2 (after Phase B)
```

---

*Session Continuation Package v20 | March 1, 2026*
*Product management complete. Math quality is the critical success factor.*
*GAE-CAL-1 is the next prompt to paste. 10 prompts to Loom v2 readiness.*
*"The moat is the graph, not the model. The math must prove it."*
