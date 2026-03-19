# SOC Copilot — Design Document v5.6 (Part 3 of 3)

**Covers:** §§7–9 (v4.1 SOC copilot prompts, end-to-end compounding verification,
v4.5 scope "Make It Real") plus the master section index for all three parts.

**Status of content in §§7–9:** All ✅ COMPLETE — executed and tagged at v4.1 and v4.5.
Preserved for historical record, execution pattern reference, and sprint discipline modeling.
These prompts are not to be re-executed. They are the foundation v5.0 builds on.

**Status of Master Section Index (updated to v5.6 — March 15, 2026):**
v5.0 TAGGED. v5.5 sprint in progress. Section index reflects all changes through v5.6:
ontology verified C=6/A=5; §22.6 η_neg design decision; ProfileScorer.update() bug fix;
PROD-3/4/4b/SHIFT-2/DISC-1 complete; IKS v2 concept; composite discriminant validated.

> **v5.3 annotation note:** Where v5.3 changes touch content in §§7–9
> (e.g., A=5 action count, ProfileScorer shape, refer_to_analyst), annotations are
> added inline in `>` blockquotes. The base content is not rewritten.

---

## 7. v4.1 SOC Copilot Prompts (6 prompts — soc-copilot repo) ✅

> GAE repo prompts (GAE-0 through GAE-2a-protocol, 7 prompts) are in `gae_design_v9`.
> These SOC prompts begin after GAE-2a-protocol is complete.

### 7.1 SOC Prompt Sequence

| Prompt | Scope | Creates/Modifies | Test |
|---|---|---|---|
| GAE-2a-soc | TravelMatch + AssetCriticality + orchestrator + seed | `domains/soc/factors.py`, `orchestrator.py`, `seed_neo4j.py` | Queries traverse relationships. Factor values ∈ [0,1]. |
| GAE-2b | ThreatIntelEnrichment + PatternHistory + seed | `domains/soc/factors.py`, `seed_neo4j.py` | PatternHistory returns 0.5 with <5 decisions. |
| GAE-2c | TimeAnomaly + DeviceTrust (rewrite to use relationships) | `domains/soc/factors.py`, `seed_neo4j.py` | **Must traverse `[:ACTIVE_AT]`, `[:USES_DEVICE]`.** |
| GAE-2d | Wire router + Decision write-back + events | `routers/triage.py`, `config.py`, `services/event_bus.py` | Decision node EXISTS after analyze. f(t) stored. Events emitted. |
| GAE-3a | Feedback → Eq. 4b + outcome write-back + trust gate | `services/feedback.py`, `routers/feedback.py` | f(t) from GRAPH (R4). Decision marked. Re-analyze → scores differ. |
| GAE-3b | Compounding dashboard — real data | `CompoundingTab.tsx`, `routers/gae.py` | Empty on first load. Real curves after 5 decisions. |

> **v5.3 note:** GAE-3a implements Eq. 4b (centroid pull/push with 20:1 asymmetry) — the
> v4.1 version. The v5.0 sprint (GAE-PROF-1 through SOC-PROF-3) replaces the scoring
> mechanism with Eq. 4-final (L2 distance, ProfileScorer). The centroid pull/push
> mechanics of GAE-3a remain correct and are preserved in ProfileScorer.update().

### 7.2 Additional Copilot-Level Prompt

| Prompt | Scope | Creates/Modifies | Test |
|---|---|---|---|
| GAE-3c | Convergence monitoring + failure modes | `routers/gae.py` | Alternating outcomes → instability warning shown. |

**Post-sprint gate:** 10-cycle compounding verification (§8). If it passes → TAG v4.1. ✅

---

## 8. End-to-End Compounding Verification (Post-Sprint Gate) ✅

This is the canonical 10-cycle test that proved the compounding mechanism before the v4.1 tag. Every subsequent sprint uses this as the regression baseline — if this fails after any change, the causal compounding chain is broken.

```
SETUP: Fresh graph seed. Learning state reset to priors.

CYCLE 1 — BASELINE:
  Analyze ALERT-7823 (credential_access).
  Record factors_1, scores_1, confidence_1.
  Verify:
    - Decision node created in Neo4j with f(t) stored
    - PatternHistory factor = 0.5 (symmetric prior — <5 decisions)
    - action_probabilities sum to 1.0

CYCLE 2 — FIRST FEEDBACK:
  Submit outcome: correct.
  Verify:
    - f(t) read from graph (R4 — not recomputed)
    - Centroid updated: μ[credential_access, action, :] has moved toward f(t)
    - Decision node marked correct
    - GraphMutated event emitted

CYCLE 3 — ACCUMULATION:
  Analyze ALERT-7824 (credential_access, different user).
  Verify:
    - PatternHistory finds 1 resolved Decision for credential_access
    - scores_3 ≠ scores_1  ← THE COMPOUNDING PROOF
    - PatternHistory factor > 0.5

CYCLES 4–8: Submit correct outcomes for 5 more credential_access alerts.
  Verify after each:
    - PatternHistory value increases monotonically
    - Centroid drift ‖μ_after − μ_before‖ > 0 each update
    - confidence trend upward for correct-action alerts

CYCLE 9 — COMPOUNDING VISIBLE:
  Analyze ALERT-7823 again (same alert as Cycle 1).
  Verify:
    - PatternHistory ≈ 1.0 (7 correct / 7 total decisions on credential_access)
    - confidence >> Cycle 1 confidence
    - Tab 4 learning curve shows real upward trend (not hardcoded)

CYCLE 10 — TRUST ASYMMETRY:
  Submit outcome: incorrect.
  Verify:
    - Centroid update magnitude >> correct update (20:1 penalty_ratio)
    - action confidence drops noticeably on re-analyze
    - The system treats false suppression as 20× more costly than false escalation
```

**Pass criteria:** All verification assertions hold. Categories learn at different rates
after Cycles 1–8 (because PatternHistory is category-scoped). Trust asymmetry is measurable.

**If this passes, the system compounds. If any step fails, a causal link is broken.**
✅ Passed at v4.1 tag.

> **v5.3 note (ProfileScorer):** From v5.0 onward, the scoring mechanism is ProfileScorer
> (Eq. 4-final, L2 distance). The 10-cycle test still applies with one change:
> Cycle 1 verification reads `profile_scorer.centroids[c, :, :]` instead of W.
> Cycle 2 verification checks `‖μ_after − μ_before‖ > 0` instead of `‖W_after − W_before‖ > 0`.
> All other assertions are identical. The compounding mechanism is unchanged — only the
> geometric representation changes (L2 distance to centroids vs. dot product with W).

> **v5.3 note (random baseline):** Baseline for 5-action system (A=5, v5.3) is 20%,
> not 25%. Chart annotations in Tab 4 should reflect this.

---

## 9. v4.5 Scope — "Make It Real" ✅ TAGGED

### 9.0 Guiding Principle

v4.5 closed the credibility gaps between published blog claims and live product proof.
Three phases executed: Phase A and B completed fully, Phase C deferred to experiment-first
validation. HC-1 added healthcare domain breadth.

**The v4.5 theme:** "After ten thousand decisions — show me how your system got smarter."
Every capability built in v4.5 was chosen to make the learning mechanism *visible* to a
CISO or technical evaluator during a 20-minute live walkthrough.

### 9.1 v4.5 Structure

```
GAE Preamble (2 prompts, GAE repo)    ← CalibrationProfile + per-factor decay
        ↓
Phase A: Simulation Mode (6 prompts)  ← "After ten thousand decisions" proof
        ↓
Phase B: CISO Readability (4 prompts) ← Investigation narrative + Tab 2 rewire
        ↓ [Loom v2 recording — pending]
Phase C: Cross-Graph Discovery        ← PERMANENTLY RETIRED — see §29 (Part 2)
HC-1: Healthcare Domain (1 prompt)    ← Domain extensibility breadth
```

**Phase D from v1 (Docker/VPS) eliminated from v4.5 scope:**
- Docker/VPS deferred to v5.5 (now v5.5-R9 — see §10.6 in Part 1)
- Kept v4.5 focused on product capability, not distribution

### 9.2 GAE Preamble (GAE Repo — 2 prompts) ✅ COMPLETE

See `gae_design_v9` for full prompt specs (GAE-CAL-1, GAE-CAL-2).

**Why this comes first:** Phase A's simulation mode exercises the learning loop 50+ times.
CalibrationProfile and per-factor decay must be in place before simulation makes them
visible. Running 50 decisions through uniform decay and then changing decay semantics
forces re-validation — so preamble runs first.

**SOC copilot impact after GAE preamble:**
- `domains/soc/config.py`: `SOCDomainConfig.get_calibration_profile()` returns calibration profile
- `services/gae_state.py`: LearningState constructed with profile from DomainConfig
- `routers/triage.py`: `score_alert()` reads `temperature` and `penalty_ratio` from CalibrationProfile

### 9.3 Phase A: Simulation Mode + Alert Corpus (6 prompts) ✅ COMPLETE

**Gap closed:** GAP-1 (no simulation mode), GAP-2 (no ATT&CK), GAP-3 (limited alert corpus)

| Prompt | Scope | Creates/Modifies | Gate |
|---|---|---|---|
| **SIM-FIX** | TD-026 fix — atomic reset | `services/state_manager.py`, audit store | Soft reset: GAE + audit + Neo4j outcomes clear atomically |
| **SIM-1** | SimulationOrchestrator backend | `services/simulation.py`, `routers/simulation.py` | 10-decision API test passes |
| **SIM-2** | Frontend simulation panel | `SimulationPanel.tsx` or integration in existing tab | Real-time chart updates during simulation. Category learning curve. |
| **SIM-3a** | Alert pool expansion — 15–20 alerts | `domains/soc/alerts/`, seed data expansion | 5 categories × 3–4 alerts each. Each category activates different dominant factors. |
| **SIM-3b** | Alert pool wiring — orchestrator uses expanded pool | `services/simulation.py`, `routers/simulation.py` | Simulation runs across all categories. PatternHistory differentiates by category. |
| **SIM-4** | ATT&CK technique IDs on all alerts | Alert definitions, Tab 3, Tab 1 | T1078, T1566.001, T1021.001, T1567, T1048 visible in UI |

**Phase A Gate: ✅ PASSED.** 50-decision simulation shows clear learning in charts. Category learning curve shows per-category accuracy divergence across 6 categories (including healthcare). Weight evolution chart shows meaningful progression.

### 9.3a HC-1: Healthcare Domain (1 prompt) ✅ COMPLETE

Added after Phase A to demonstrate domain extensibility beyond cybersecurity.

| Item | What Was Built |
|---|---|
| **5 healthcare alerts** | SIM-HC-001 (PHI access anomaly), SIM-HC-002 (medical device scan), SIM-HC-003 (Health-ISAC IOC match), SIM-HC-004 (credential stuffing), SIM-HC-005 (EHR lateral movement) |
| **Neo4j seed data** | 3 healthcare users, 3 healthcare assets, PHI DataClass, 2 Health-ISAC ThreatIntel nodes |
| **Simulation** | healthcare category added (oracle_rate=0.65), 6th line in category learning curve |
| **ROI** | Healthcare preset: 50 alerts/day, 12 analysts, $95K, HIPAA/PHI note |
| **Verification** | `verify_seed_data.py`: 8 checks, standalone Neo4j verification |

> **v5.3 note:** Healthcare remains a **simulation variant only** — it is not a production
> category and is NOT included in the C=5 production centroid tensor (shape (5,5,6)).
> The 6th simulation category continues to serve its original purpose: demonstrating
> that the architecture is domain-generalizable without code changes. The S2P copilot
> (v6.0-R4) is the production second-domain proof — see §1.6 (Part 1).

### 9.4 Phase B: CISO Readability (4 prompts) ✅ COMPLETE

**Gap closed:** GAP-4 (no investigation narrative), TD-019 (dual decision paths), TD-020 (execute_action events)

| Prompt | Scope | What Was Built | Gate |
|---|---|---|---|
| **NAR-1** ✅ | NarrativeProvider protocol + implementations | `services/narrative.py`: TemplateNarrativeProvider, OllamaNarrativeProvider with graceful degradation. NarrativeContext dataclass. | Template generates for any alert. Calibration line present. |
| **NAR-2** ✅ | Tab 3 narrative panel | 3–5 sentence narrative with "Calibrated from N outcomes" line | Narrative appears with calibration count |
| **TAB2-1** ✅ | Rewire Tab 2 Runtime Evolution to GAE pipeline | `routers/evolution.py`: compute_factor_vector → score_alert → Decision node → events. GAE Scoring panel: 6 factor bars + action probability pills. **TD-019 CLOSED.** | Tab 2 uses GAE end-to-end |
| **TAB2-2** ✅ | AgentEvolver shows real GAE data | `services/evolver.py`: real decision_count, per-action weight norms. `execute_action()` emits DecisionMade + GraphMutated events. Honesty labels applied. **TD-020 CLOSED.** | No dual decision paths remain |

**Honesty labels applied in NAR-2 / TAB2-2 (H7 items 10–13, §28 in Part 2):**
- "Demo Deployment" runtime header
- "Demo data — live tracking in v5.0" in audit timeline
- "Illustrative" on threat landscape section
- "Projected" on economic impact section

**Phase B Gate: ✅ PASSED.** Tab 2 GAE end-to-end. Investigation narrative with calibration line. No dual decision paths. Honesty labels on all hardcoded data.

### 9.5 Phase C: Cross-Graph Discovery → **PERMANENTLY RETIRED**

See §29 (Part 2) for full experiment results. Summary:

- **LLM judge panel** (GPT 5.3, Opus, Grok): unanimous — don't implement Eq. 6 as-is.
- **25 experiments executed.** Root cause (dot product kernel, 61% accuracy) identified and fixed.
- **G (Gating Matrix) falsified** — +0.01pp best case. Not worth implementing.
- **ProfileScorer (L2 distance) confirmed** — 97.89% zero-learning, 98.2% with learning.
- **Phase C prompts (DISC-1 through GATE-B3) permanently retired.** Not deferred.
- **Replacement:** v5.0 implements ProfileScorer (§10–10.6 in Part 1). Discovery → v6.0+.

### 9.6 v4.5 Prompt Totals (Actual)

| Phase | SOC Prompts | GAE Prompts | Status |
|---|---|---|---|
| GAE Preamble | 0 | 2 | ✅ Complete |
| Phase A (Simulation) | 6 | 0 | ✅ Complete |
| Phase B (Narrative) | 4 | 0 | ✅ Complete |
| HC-1 (Healthcare) | 1 | 0 | ✅ Complete |
| Phase C (Discovery) | 0 | 0 | **RESOLVED — see §29 (Part 2)** |
| **v4.5 Executed** | **11** | **2** | **13 total** |

---

## Master Section Index — v5.5 (All Three Parts)

Use this table to locate any section across the three part files.

| Section | Title | Part | Status |
|---|---|---|---|
| §1 | Architecture — Three-Repo Stack | Part 1 | v5.5 |
| §1.4 | Architecture Philosophy — Bridge, Compiled Ontology, Three Computational Levels, **Two Levels of Institutional Judgment (NEW v5.5)** | Part 1 | v5.5 |
| §1.5 | Product Identity | Part 1 | v5.3 |
| §1.6 | S2P Co-Design Constraints | Part 1 | v5.3 (TD-036 CLOSED) |
| §2 | Directory Structure | Part 1 | v5.4 |
| §3 | Imports from GAE | Part 1 | v5.4 |
| §4 | Build History + Canonical Numbers | Part 1 | v5.5 (v5.0 TAGGED, all phases ✅) |
| §5 | SOC Factor Implementations | Part 1 | v5.3 |
| §6 | Decision & Outcome Write-Back | Part 1 | v5.4 |
| **§7** | **v4.1 SOC Copilot Prompts** | **Part 3** | ✅ Complete (v4.1) |
| **§8** | **End-to-End Compounding Verification** | **Part 3** | ✅ Complete (v4.1) |
| **§9** | **v4.5 Scope — "Make It Real"** | **Part 3** | ✅ Complete (v4.5) |
| §10 | v5.0 Scope | Part 1 | v5.5 (v5.0 TAGGED) |
| §10.6 | v5.5 Scope — Fully Specified (R1–R13) | Part 1 | v5.3 |
| §11 | Product Flow | Part 1 | v5.3 |
| §12 | Build Sequence | Part 1 | v5.3 |
| §13 | Claude Code Rules | Part 1 | v5.4 |
| §14 | SOCDomainConfig | Part 1 | v5.6 (shape (6,5,6), categories corrected) |
| **§15** | **Simulation Mode** | **Part 2** | v5.2 preserved |
| **§16** | **NarrativeProvider** | **Part 2** | v5.2 preserved |
| **§17** | **Reset Semantics** | **Part 2** | v5.2 preserved |
| **§17.5** | **Rollback Execution Specification (TD-033)** | **Part 2** | v5.4-final AUTHORITATIVE |
| **§18** | **ATT&CK Integration** | **Part 2** | v5.5 (TD-036 CLOSED) |
| **§19** | **Category Learning Curve** | **Part 2** | v5.2 preserved |
| **§20** | **v4.5 Prompt Specifications** | **Part 2** | ✅ Complete |
| §21 | Shadow Mode — Full Specification | Part 1 | v5.3 |
| §22 | Institutional Knowledge Score (IKS) | Part 1 | v5.3 |
| §22.6 | η_neg Design Decision + SHIFT-2 Validation | Part 1 | v5.6 NEW |
| §23 | NL Template Engine (24 templates) + §23.4 Similar Past Cases + §23.5 LLM Judge Rubric | Part 1 | v5.4-final AUTHORITATIVE |
| §24 | SemanticRegistry — concepts.yaml + queries.yaml | Part 1 | v5.3 |
| §25 | Enterprise Integration Hooks | Part 1 | v5.3 |
| §26 | Feature Gap Closure Map | Part 1 | v5.3 |
| §27 | Experiment Landscape | Part 1 | v5.3 |
| **§28** | **Response Data Realism (H7)** | **Part 2** | v5.2 §21 renumbered |
| **§29** | **Phase C — RESOLVED** | **Part 2** | v5.2 §22 renumbered |
| **§30** | **Feature Gaps F1–F15** | **Part 2** | v5.5 (F2/F4 ✅ COMPLETE) |
| Appendix A | Version History | Part 1 | v5.5 |
| Appendix B | Technical Debt (TD-001 – TD-039) | Part 1 | v5.5 (TD-027/032/036/039 CLOSED) |
| Appendix C | Superseded Documents | Part 1 | v5.3 |

### Key Files by Task

| Task | Read First | Then Read |
|---|---|---|
| **Starting v5.5 sprint** | §13 (rules) in Part 1 | §10.6 (R1–R13 scope), §4 (PROD-3/PROD-4 first actions), §14 (config) in Part 1 |
| Implementing Shadow Mode | §21 in Part 1 | §13 rules, §6 write-back in Part 1 |
| Implementing IKS | §22 in Part 1 | §4 (canonical numbers), §6.4 (ProfileSnapshot hook) in Part 1 |
| Implementing NL templates | §23 in Part 1 | §16 (NarrativeProvider distinction) in Part 2 |
| Building Tab 5 | §24 in Part 1 | §21 (shadow), §22 (IKS), §23 (templates) in Part 1 |
| Enterprise integration | §25 in Part 1 | §13 (enterprise rules) in Part 1 |
| Running experiments | §27 in Part 1 | `experiments_catalog_v8` (Parts 1/2/3, outputs) |
| Understanding feature gaps | §26 (closure map) in Part 1 | §30 (full F-table) in Part 2 |
| Understanding what was built | §7–9 in Part 3 | §20 (v4.5 prompts) in Part 2 |
| Debugging scoring issues | §14 (SOCDomainConfig) in Part 1 | §5 (factors), §6 (write-back) in Part 1 |
| S2P co-design check | §1.6 in Part 1 | s2p_copilot_design_v0.2 §8–9 (TD-036 CLOSED — `by_category` already shipped) |
| Reset / rollback | §17.5 in Part 2 (authoritative) | §6.4 (checkpoint creation), §14 (get_checkpoint_config) in Part 1 |
| Architecture philosophy | `architecture_philosophy_v1_3.md` (outputs) | `compounding_intelligence_v7_part1.md` (Five-Layer), `compounding_intelligence_v7_part3.md` (Bridge, Compiled Ontologies) |
| Two levels of institutional judgment | §1.4 in Part 1 | `gae_design_v9.md` §5 (GAE owns Level 1) |

---

*SOC Copilot — Design Document v5.6 (Part 3 of 3) | March 15, 2026*
*§§7–9: v4.1 prompt sequence, 10-cycle verification, v4.5 "Make It Real" (all ✅ COMPLETE).*
*Master Section Index updated to v5.6: ontology C=6/A=5 verified; §22.6 η_neg settled;*
*ProfileScorer.update() bug fixed (gt_action_index, 251 tests); DISC-1 composite discriminant.*
*"The moat is the graph, not the model. The profiles prove it. The discriminant compounds it."*
