# Technology Portfolio Map v1.4: Capability-to-Source Traceability

**Date:** March 1, 2026
**Version:** 1.4
**Purpose:** For every capability claimed by the compounding intelligence architecture, traces: (1) the published source, (2) the design document, (3) the implementation location, (4) the version where it becomes real, and (5) ENGINE vs PRODUCT scope.

**Changes from v1.3:** Three-repo file paths (gae/ not core/). Version numbers corrected to actual roadmap. New capabilities from design session (CalibrationProfile, evaluation, ablation, institutional judgment, NarrativeProvider). INOVA → v6.0. Design doc references updated (GAE Design v6, SOC Copilot Design v2, ci-platform Design v2).

---

## How to Read This Map

- **Published Source** — blog post or paper where the capability is described.
- **Design Source** — internal design document that specifies how to build it.
- **Implementation** — file(s) in the codebase, tagged to the correct repo.
- **Scope** — ENGINE (open-source GAE, Apache 2.0), PLATFORM (open-source ci-platform, Apache 2.0), or PRODUCT (proprietary soc-copilot).

**Three repos:**
```
graph-attention-engine/gae/     ← ENGINE (numpy-only, pip-installable)
ci-platform/platform/           ← PLATFORM (domain-agnostic infrastructure)
soc-copilot/                    ← PRODUCT (SOC domain expertise, proprietary)
```

---

## Layer 1: UCL — Unified Context Layer

| Capability | Published Source | Design Source | Implementation | Version | Scope |
|---|---|---|---|---|---|
| **Schema contracts (read-side)** | CI 4.0 §Layer 1 | GAE Design v6 §12 | `gae/contracts.py` — SchemaContract | **v4.1 ✅** | ENGINE |
| **Embedding data quality contracts** | Math Blog §4 | GAE Design v6 §12 | `gae/contracts.py` — EmbeddingContract, PropertySpec | **v4.1 ✅** | ENGINE |
| **Domain schema format** | Design Decisions v1 §D3 | GAE Design v6 §18 | `gae/schema.py` — DomainSchemaSpec | **v5.0** | ENGINE |
| **Contract validation at startup** | CI 4.0 §Layer 1 | ci-platform Design v2 §7.4 | `platform/schema/contract_checker.py` | **v5.0** | PLATFORM |
| **Entity resolution (INOVA)** | CI 4.0 §Layer 1 | ci-platform Design v2 §1 | `platform/ucl/resolution.py` | **v6.0** | PLATFORM |
| **Governed write-path validation** | CI 4.0 §Layer 1 | ci-platform Design v2 §4.3 | `platform/ucl/schema.py`, `platform/ucl/ontology.py` | **v6.0** | PLATFORM |

---

## Layer 2: Agent Engineering Stack

| Capability | Published Source | Design Source | Implementation | Version | Scope |
|---|---|---|---|---|---|
| **Weight matrix evolution (Eq. 4b)** | Math Blog §3 | GAE Design v6 §8 | `gae/learning.py` — LearningState.update() | **v4.1 ✅** | ENGINE |
| **Asymmetric reinforcement (20:1)** | Math Blog §3 | GAE Design v6 §8 | `gae/learning.py` — δ(t) via CalibrationProfile.penalty_ratio | **v4.1 ✅** | ENGINE |
| **Weight decay (Eq. 4c)** | Math Blog §3 | GAE Design v6 §8, §16.5 | `gae/learning.py` — per-factor decay via CalibrationProfile | **v4.1 ✅** (uniform), **v4.5** (per-factor) | ENGINE |
| **CalibrationProfile** | Design Decisions v1 §1 | GAE Design v6 §16 | `gae/calibration.py` — CalibrationProfile dataclass | **v4.5** | ENGINE |
| **Convergence monitoring** | Math Blog §Exp 1 | GAE Design v6 §8 | `gae/convergence.py` — three failure modes | **v4.1 ✅** | ENGINE |
| **Confirmation bias mitigation (A1)** | Design Decisions v1 §4 | GAE Design v6 §16 | `gae/calibration.py` — discount_strength field | **v4.5** (field), **v5.0** (tuned) | ENGINE |
| **Evaluation framework** | Design Decisions v1 §3 | GAE Design v6 §17 | `gae/evaluation.py` — EvaluationScenario, run_evaluation | **v5.0** | ENGINE |
| **Ablation framework** | Design Decisions v1 §8a | GAE Design v6 §20 | `gae/ablation.py` — AblationConfig, run_ablation | **v5.0** | ENGINE |
| **Institutional judgment metrics** | Design Decisions v1 §8b | GAE Design v6 §19 | `gae/judgment.py` — InstitutionalJudgmentMetrics | **v5.0** | ENGINE |
| **Candidate artifact generation** | CI 4.0 §Layer 2 | ci-platform Design v2 §4.4 | `platform/agents/meta_prompt_agent.py` | **v6.0** | PLATFORM |
| **Binding eval gates** | CI 4.0 §Layer 2 | ci-platform Design v2 §4.4 | `platform/agents/safeguard_agent.py` + `evaluation_framework.py` | **v6.0** | PLATFORM |

---

## Layer 3: ACCP — Agentic Cognitive Control Plane

| Capability | Published Source | Design Source | Implementation | Version | Scope |
|---|---|---|---|---|---|
| **Scoring matrix (Eq. 4)** | Math Blog §3 | GAE Design v6 §7 | `gae/scoring.py` — score_alert() | **v4.1 ✅** | ENGINE |
| **Factor computation from graph** | Math Blog §3 + CI 4.0 | GAE Design v6 §6 | `gae/factors.py` (protocol, ENGINE) + `soc-copilot/domains/soc/factors.py` (PRODUCT) | **v4.1 ✅** | ENGINE + PRODUCT |
| **Simulation mode** | Demo Blurb + Design Decisions v1 | SOC Copilot Design v2 §15 | `soc-copilot/services/simulation.py` — SimulationOrchestrator | **v4.5** | PRODUCT |
| **Situation classification (learned)** | CI 4.0 §Layer 3 | SOC Copilot Design v2 §10.2 (SIT-1/2) | Scoring-based — framework ENGINE, situation types PRODUCT | **v5.0** | ENGINE + PRODUCT |
| **RL reward signal r(t)** | CI 4.0 §Layer 3 | GAE Design v6 §8 | `gae/learning.py` — Eq. 4b update | **v4.1 ✅** | ENGINE |

---

## Layer 4: Domain Copilots

| Capability | Published Source | Design Source | Implementation | Version | Scope |
|---|---|---|---|---|---|
| **Investigation narratives (NarrativeProvider)** | CI 4.0 §Layer 4 | SOC Copilot Design v2 §16 | `soc-copilot/services/narrative.py` — protocol + Ollama/Qwen default | **v4.5** | PRODUCT |
| **ATT&CK technique labeling** | Industry standard | SOC Copilot Design v2 §18 | Alert definitions + Tab 3 display | **v4.5** | PRODUCT |
| **Category learning curve** | Design Decisions v1 §8b | SOC Copilot Design v2 §19 | Frontend chart — Tab 4 | **v4.5** | PRODUCT |
| **Verified outcomes → weight calibration** | CI 4.0 §Layer 4 | GAE Design v6 §8 | `gae/learning.py` feedback pathway | **v4.1 ✅** | ENGINE |
| **ROI dashboard** | Design Decisions v1 §H4 | SOC Copilot Design v2 §10.2 (ECON-1) | `soc-copilot/routers/dashboard.py` | **v5.0** | PRODUCT |
| **Ground truth evaluation (30-40 scenarios)** | Design Decisions v1 §3 | SOC Copilot Design v2 §10.2 (EVAL-1/2-SOC) | `soc-copilot/domains/soc/evaluation_scenarios.json` | **v5.0** | PRODUCT |
| **Realistic seed data (200+ users)** | Design Decisions v1 §H5 | SOC Copilot Design v2 §10.2 (SEED-2) | `soc-copilot/seed_realistic.py` | **v5.0** | PRODUCT |
| **Autonomous operation** | CI 4.0 §Layer 4 | Deferred | Confidence gates (ENGINE) + execution (PRODUCT) | **v6.0** | ENGINE + PRODUCT |

---

## Cross-Cutting: Computation Stack (Math Blog Equations)

| Equation | Published Source | Design Source | Implementation | Version | Scope |
|---|---|---|---|---|---|
| **Eq. 4** — Scoring | Math Blog §3 | GAE Design v6 §7 | `gae/scoring.py` | **v4.1 ✅** | ENGINE |
| **Eq. 4b** — Weight Update | Math Blog §3 | GAE Design v6 §8 | `gae/learning.py` | **v4.1 ✅** | ENGINE |
| **Eq. 4c** — Weight Decay | Math Blog §3 | GAE Design v6 §16.5 | `gae/learning.py` (per-factor via CalibrationProfile) | **v4.5** (per-factor) | ENGINE |
| **Eq. 5** — Entity Embeddings | Math Blog §4 | GAE Design v6 §9 | `gae/embeddings.py` — EmbeddingProvider protocol | **v4.5 Phase C** (test), **v5.5** (production) | ENGINE |
| **Eq. 6** — Cross-Graph Attention | Math Blog §4 | GAE Design v6 §10 | `gae/attention.py` | **v4.5 Phase C** (test) | ENGINE |
| **Eq. 7a/7b** — Logit/Attention Matrix | Math Blog §4 | GAE Design v6 §10 | `gae/primitives.py` | **v4.1 ✅** | ENGINE |
| **Eq. 8a-8c** — Discovery Extraction | Math Blog §4 | GAE Design v6 §10.4 | `gae/discovery.py` | **v4.5 Phase C** (test) | ENGINE |
| **Eq. 9** — Multi-Domain Attention | Math Blog §5 | GAE Design v6 §10 | `gae/attention.py` | **v5.5** | ENGINE |

---

## Cross-Cutting: Causal Architecture (Six Connectors)

| Connector | Published Source | Design Source | Implementation | Version | Scope |
|---|---|---|---|---|---|
| **C1: Graph → Factors** | CI 4.0 + Math Blog §3 | GAE Design v6 §5 | `gae/factors.py` | **v4.1 ✅** | ENGINE |
| **C2: Factors × W → Decision** | Math Blog §3 | GAE Design v6 §5 | `gae/scoring.py` | **v4.1 ✅** | ENGINE |
| **C3: Decision + Outcome → W Update** | Math Blog §3 | GAE Design v6 §5 | `gae/learning.py` | **v4.1 ✅** | ENGINE |
| **C4: Graph → Embeddings → Discoveries** | Math Blog §4-5 | GAE Design v6 §5 | `gae/embeddings.py` → `attention.py` → `discovery.py` | **v4.5 Phase C** | ENGINE |
| **C5: Discovery → Factor Expansion** | Math Blog §5 | GAE Design v6 §8.3 | `gae/learning.py` — expand_weight_matrix() | **v4.5 Phase C** | ENGINE |
| **C6: Outcomes → Artifact Mutation** | CI 4.0 + ARC + SC | ci-platform Design v2 §4.4 | `platform/agents/` | **v6.0** | PLATFORM |

---

## Platform Infrastructure

| Capability | Published Source | Design Source | Implementation | Version | Scope |
|---|---|---|---|---|---|
| **DomainConfig ABC** | Design Decisions v1 | ci-platform Design v2 §7.2 | `platform/domains/base.py` | **v5.0** | PLATFORM |
| **StateManager (atomic reset)** | Design Decisions v1 §5 | ci-platform Design v2 §7.5 | `platform/state_manager.py` | **v5.0** | PLATFORM |
| **Domain registry** | Design Decisions v1 | ci-platform Design v2 §7.1 | `platform/domain_registry.py` | **v5.0** | PLATFORM |
| **GraphEventBus (production)** | CI 4.0 | ci-platform Design v2 §4.1 | `platform/events.py` | **v5.5** | PLATFORM |
| **Meta-Prompt Agent** | SC Blog §2 + §9 | ci-platform Design v2 §4.4 | `platform/agents/meta_prompt_agent.py` | **v6.0** | PLATFORM |
| **R×T×Q Evaluation Framework** | SC Blog §10 | ci-platform Design v2 §4.4 | `platform/agents/evaluation_framework.py` | **v6.0** | PLATFORM |
| **Safeguard Agent** | SC Blog §2 | ci-platform Design v2 §4.4 | `platform/agents/safeguard_agent.py` | **v6.0** | PLATFORM |

---

## Encoding & Representation Theory (from Visual Alpha)

*Unchanged from v1.3. Visual Alpha informs future ENGINE evolution (v7.0+): GNN embeddings, self-supervised pre-training, multi-scale factors, cross-domain transfer.*

---

## Published Source Index

| Short Name | Full Title | URL |
|---|---|---|
| **Math Blog** | Cross-Graph Attention: Mathematical Foundation with Experimental Validation | dakshineshwari.net/post/cross-graph-attention... |
| **CI 4.0** | Compounding Intelligence 4.0: How Enterprise AI Develops Self-Improving Judgment | dakshineshwari.net/post/compounding-intelligence-4-0... |
| **Demo Blurb** | After Ten Thousand Decisions, Show Me How Your System Got Smarter (v3.1) | dakshineshwari.net/post/after-ten-thousand-decisions... |
| **Loom v1** | SOC Copilot Demo Video (v1) | loom.com/share/b45444f85a32... |
| **ARC Abstract** | Agentic React Copilot | (internal document) |
| **SC Blog** | Supply Chain ERP AI: Multi-Agent LLM App | dakshineshwari.net/post/llms-for-supply-chain... |
| **Visual Alpha** | Visual Alpha: Harnessing Computer Vision for Financial Predictions | dakshineshwari.net/post/visual-alpha... |

## Design Document Index — UPDATED

| Short Name | Full Title | Key Scope |
|---|---|---|
| **GAE Design v6** | GAE Design v5 + v6 Addendum | Tiers 1-5, CalibrationProfile, evaluation, ablation, judgment, schema |
| **SOC Copilot Design v2** | SOC Copilot Design v1 + v2 Addendum | v4.5 phases, NarrativeProvider, reset, ATT&CK |
| **ci-platform Design v2** | CI Platform Design v1 + v2 Addendum | v5.0 first code, DomainConfig ABC, schema, S2P validation |
| **Design Decisions v1** | Design Decisions — v4.5/v5.0 Planning Session | 8 decisions, 7 new gaps, gap registry |

---

## Coverage Summary

```
Published claims:           ~35 distinct capabilities across 7 sources
Design-specified:           32 (91%) — mapped to specific files and functions

ENGINE scope (GAE):         20 capabilities
PLATFORM scope:             8 capabilities
ENGINE + PRODUCT split:     4 capabilities
PRODUCT only:               3 capabilities

Implemented at v4.1:        14 capabilities ✅
Implemented at v4.5:        22 capabilities (+ simulation, narrative, discovery test,
                            CalibrationProfile, ATT&CK, category learning curve)
Implemented at v5.0:        30 capabilities (+ evaluation, ablation, judgment,
                            platform extraction, realistic data, ROI)
Implemented at v5.5:        32 capabilities (+ production embeddings, event bus)
Implemented at v6.0:        35 capabilities (+ evolution, autonomy, INOVA, governance)

Future paths (v7.0+):       GNN, self-supervised pre-training, multi-scale factors,
                            cross-domain transfer (Visual Alpha encoding theory)
```

---

*Technology Portfolio Map v1.4 | March 1, 2026*
*~35 capabilities → 20 ENGINE + 8 PLATFORM + 4 split + 3 PRODUCT-only.*
*v4.1: 14 ✅. v4.5: 22. v5.0: 30. v6.0: 35.*
