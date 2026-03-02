# SOC Copilot — MVP Sprint Plan v1

**Date:** March 1, 2026
**Trigger:** INOVA CISO conversation in 2-4 weeks. Live demo on laptop required.
**Context:** INOVA is a healthcare organization. Health-ISAC connectivity directly relevant.
**Goal:** Cross from demo to MVP. No more demo theater.

---

## The INOVA-Specific Opportunity

INOVA is healthcare. This changes three things about what the demo must show:

1. **Health-ISAC data visible in the graph** — not just "the pattern scales" but actual healthcare threat indicators in the knowledge graph. The current Loom script says "plug in your Health-ISAC feed tomorrow." For INOVA, having Health-ISAC data *already in the graph* during the demo is dramatically more powerful.

2. **Healthcare-relevant alert categories** — the current corpus is dominated by travel-login anomalies. A healthcare CISO sees: EHR access anomalies (after-hours patient record access), medical device network anomalies, ransomware precursors (healthcare is the #1 ransomware target), credential abuse across clinical systems, and threat intel matches from Health-ISAC indicators. These are the categories that should populate the expanded alert pool.

3. **HIPAA/compliance framing** — the SHA-256 tamper-evident audit trail and policy conflict resolution are directly relevant to HIPAA compliance requirements. The ROI calculator can reference healthcare-specific metrics (breach cost = $10.93M average for healthcare per IBM 2024, vs $4.88M cross-industry).

---

## What the CISO Must See (Non-Negotiable for the Demo)

| # | What | Why | Current Status |
|---|---|---|---|
| 1 | **50-decision simulation running in real-time** with category learning curves | Proves "after ten thousand decisions" claim. THE moment. | Not built |
| 2 | **Healthcare-relevant alert categories** across 5 types | Shows domain relevance, not generic travel logins | 5 generic alert types exist |
| 3 | **ATT&CK technique IDs** on every alert | Table stakes for any SOC product conversation | Zero ATT&CK references |
| 4 | **Investigation narrative** with "calibrated from N verified outcomes" | CISOs hear their language | Not built |
| 5 | **Health-ISAC indicators** visible in the graph | Direct relevance to INOVA's threat intel stack | Pulsedive live; Health-ISAC not implemented |
| 6 | **Transparent six-factor breakdown** with live threat intel | Already works — this is a strength | ✅ Working |
| 7 | **Policy conflict detection and resolution** | HIPAA relevance, governance chain | ✅ Working |
| 8 | **Tamper-evident audit trail** (SHA-256) | HIPAA compliance proof | ✅ Working |
| 9 | **Compounding charts** (Weight Evolution, Confidence, Trust Curve) | Visual proof of learning | ✅ Working |
| 10 | **ROI calculator** with healthcare-adjusted numbers | CFO conversation enabler | ✅ Working (needs healthcare defaults) |

Items 1-5 must be built. Items 6-10 already work or need minor adjustments.

---

## Sprint Plan: 2-4 Weeks to INOVA Demo

### Week 1: Foundation (GAE Preamble + Simulation Backend)

| Day | Prompt | Repo | What | Gate |
|---|---|---|---|---|
| 1 | **GAE-CAL-1** | GAE | CalibrationProfile dataclass. Refactor LearningState. `soc_calibration_profile()` convenience constructor. | Existing tests + 6 new pass |
| 1-2 | **GAE-CAL-2** | GAE | Per-factor decay: epsilon_vector from decay_class_rates × factor name mapping. Three-layer design. | All prior + 4 new tests pass |
| 2 | **SIM-FIX** | SOC | StateManager with atomic soft/hard reset. POST /api/admin/reset. Fixes TD-026. | Reset returns 200. GAE state at priors after soft reset. |
| 3 | **SIM-1** | SOC | SimulationOrchestrator backend. Batch N alerts through same GAE pipeline. Bernoulli oracle. Track by_category accuracy. | 10-decision API test passes |
| 4 | **/model opus review** | Both | Code review of GAE-CAL-1/2 + SIM-FIX + SIM-1. Fix any issues before frontend work. | Opus passes |

**Week 1 delivers:** CalibrationProfile in GAE, simulation backend running, atomic reset working. 5 prompts + 1 review.

### Week 2: Alert Corpus + Frontend + ATT&CK

| Day | Prompt | Repo | What | Gate |
|---|---|---|---|---|
| 5 | **SIM-3a** | SOC | Healthcare-oriented alert pool: 15-20 alerts across 5 categories (see §Alert Categories below). Each category activates different dominant factors. Health-ISAC indicators in seed data. | 5 categories × 3-4 alerts each |
| 6 | **SIM-3b** | SOC | Wire expanded pool into orchestrator. PatternHistory differentiates by category. | Simulation runs across all categories |
| 7 | **SIM-4** | SOC | ATT&CK technique IDs on all alerts. Tab 3: technique badge. Tab 1: group by tactic. | Technique IDs visible on all alerts |
| 8 | **SIM-2** | SOC | Frontend simulation panel: "Run Simulation" button, progress bar, category learning curve (multi-line Recharts chart), speed control. Poll every 500ms. | Charts update during simulation. Category lines diverge. |
| 9 | **/model opus review** | SOC | Review Phase A. Verify simulation end-to-end. | 50-decision simulation → clear learning in charts |

**Week 2 delivers:** Full simulation mode with healthcare alerts, ATT&CK alignment, category learning curves. 4 prompts + 1 review.

**PHASE A GATE:** Run 50-decision simulation. Capture 60-second screen recording. Category learning curves show per-category accuracy divergence. Weight evolution shows meaningful progression. If this doesn't look convincing, STOP and fix before proceeding to Phase B.

### Week 3: Narrative + Healthcare Polish

| Day | Prompt | Repo | What | Gate |
|---|---|---|---|---|
| 10 | **NAR-1** | SOC | NarrativeProvider protocol + TemplateNarrativeProvider (always works) + OllamaNarrativeProvider (graceful fallback). | Template generates for any alert |
| 11 | **NAR-2** | SOC | Tab 3 narrative panel: 3-5 sentence narrative with "calibrated from N verified outcomes" line. | Narrative appears with calibration line |
| 12 | **HC-1** | SOC | Healthcare polish: (a) ROI calculator healthcare defaults (breach cost $10.93M, HIPAA audit cost), (b) Health-ISAC visible as a data source in Tab 1 Threat Landscape, (c) 1-2 healthcare-specific policy rules (HIPAA minimum necessary, clinical system access). | Health-ISAC badge visible in Tab 1. Healthcare ROI defaults load. |
| 13 | **/model opus review** | SOC | Review Phase B + HC-1. Full demo flow rehearsal. | End-to-end demo runs clean |

**Week 3 delivers:** Investigation narrative with calibration history, healthcare-specific data and policies, Health-ISAC visibility. 3 prompts + 1 review.

### Week 4: Demo Prep + Outreach Materials

| Day | Activity | What |
|---|---|---|
| 14 | **Demo rehearsal** | Full INOVA demo flow. Record Loom v2. Identify any rough edges. |
| 15 | **Leave-behind doc** | 1-page positioning document for INOVA CISO to circulate internally (see §Leave-Behind below) |
| 16 | **Buffer** | Fix any issues from rehearsal. Polish UI rough edges. |
| 17 | **Final rehearsal** | Timed run-through. Practice the healthcare-specific talking points. |

---

## Total Prompt Count

| Phase | Prompts | Reviews | Total |
|---|---|---|---|
| GAE Preamble | 2 | — | 2 |
| Phase A (Simulation) | 5 (SIM-FIX, SIM-1, SIM-3a, SIM-3b, SIM-4) | 1 | 6 |
| Phase A (Frontend) | 1 (SIM-2) | — | 1 |
| Phase B (Narrative) | 2 (NAR-1, NAR-2) | — | 2 |
| Healthcare Polish | 1 (HC-1) | 1 | 2 |
| **Total** | **11** | **3** | **14 execution units** |

This is **11 dev prompts + 3 Opus reviews** in ~13 working days. Achievable at 1-2 prompts/day.

---

## What's Deferred (and Why)

| Item | Original Version | Deferred To | Rationale |
|---|---|---|---|
| TAB2-1/TAB2-2 (Tab 2 GAE rewire) | v4.5 Phase B | **Post-INOVA** (v4.5 still) | Tab 2 works visually. Dual decision paths are internal tech debt, not visible to CISO. Fix after the meeting. |
| Phase C (Cross-graph discovery) | v4.5 Phase C | **Post-INOVA** (v4.5 still) | Hard-gated. Not MVP-blocking. The simulation + narrative are the proof points for this conversation. |
| Full evaluation framework (30-40 scenarios) | v5.0 | v5.0 | Not needed for INOVA demo. Needed for academic credibility. |
| Ablation framework | v5.0 | v5.0 | Same — academic credibility, not CISO demo. |
| Docker/VPS | v5.5 | v5.5 | INOVA demo is laptop-based. |
| Manual alert submission | MVP recommendation (B1) | **Post-INOVA** (v5.0) | Nice to have but simulation proves the point for now. |

### What We're Pulling Forward

| Item | Original Version | Pulled To | Rationale |
|---|---|---|---|
| **HC-1: Healthcare polish** | Not planned | **v4.5 (new prompt)** | INOVA is healthcare. Health-ISAC visibility + healthcare ROI defaults + HIPAA policies directly relevant. |
| **Health-ISAC seed data** | Not planned (connector at v6.0) | **v4.5 SIM-3a** | Seed data (not live API) is sufficient. Having Health-ISAC indicators in the graph during demo is high-impact for INOVA. |

---

## Alert Categories for Healthcare SOC (SIM-3a Design)

These replace the generic travel-login-heavy corpus with categories relevant to a healthcare CISO:

| Category | ATT&CK Technique | Dominant Factors | Example Alert |
|---|---|---|---|
| **Clinical Access Anomaly** | T1078 (Valid Accounts) | pattern_history, time_anomaly, asset_criticality | After-hours EHR access from unusual department. Nurse accessing oncology records when assigned to cardiology. |
| **Medical Device Anomaly** | T1021.001 (Remote Services: RDP) | device_trust, threat_intel_enrichment, time_anomaly | Infusion pump initiating unexpected network connection. MRI system scanning internal subnet. |
| **Credential Abuse** | T1110 (Brute Force) / T1078 | pattern_history, travel_match, threat_intel_enrichment | Multiple failed logins to clinical system from known-bad IP (Health-ISAC indicator). Credential stuffing against patient portal. |
| **Ransomware Precursor** | T1566.001 (Phishing: Attachment) / T1486 (Data Encrypted) | threat_intel_enrichment, asset_criticality, pattern_history | Phishing email with payload matching Health-ISAC ransomware IOC. Anomalous encryption activity on file server. |
| **Data Exfiltration / Privacy** | T1567 (Exfiltration Over Web Service) / T1048 | asset_criticality, pattern_history, time_anomaly | Bulk download of patient records to personal cloud storage. Unusual data transfer volume from EHR server. |

**Each category activates different dominant factors.** This is the key to the category learning curve — the system learns that clinical access anomalies are best predicted by pattern_history + time_anomaly, while ransomware precursors are best predicted by threat_intel + asset_criticality. Different categories, different learned judgment.

**Health-ISAC integration in seed data:** 3-5 Health-ISAC indicators (ransomware IOCs, credential dump indicators, healthcare-targeted phishing domains) seeded as ThreatIntel nodes with `source: "Health-ISAC"` alongside existing Pulsedive indicators. This makes Health-ISAC visible in Tab 1 Threat Landscape without requiring a live API connector.

---

## The Demo Flow for INOVA (Loom v2 Script Adaptation)

### Modified Opening (Healthcare-Specific)

"Before I show you the product, remember one question. Ask your current SOC vendor: after ten thousand alerts — the EHR access anomalies, the medical device events, the phishing campaigns targeting your clinical staff — show me how the system got smarter. Not faster. Not cheaper. Smarter."

### The Five Moments

1. **Tab 1: What the graph knows** — Threat Landscape shows Pulsedive + Health-ISAC indicators. "Your sector ISAC feed is already in the graph. Every indicator enriches every future decision."

2. **Simulation: Watch 50 decisions compound** — "Run Simulation" button. Real-time category learning curves. "Watch. Clinical access anomalies converge fast — your analysts have seen hundreds. Medical device alerts take longer — the system is still building judgment. Just like a new analyst would."

3. **Tab 3: The full decision with narrative** — Select a clinical access anomaly. Six-factor breakdown. Investigation narrative: "This alert was classified based on 6 weighted factors. The pattern_history factor is dominant — calibrated from 23 verified outcomes on similar clinical access events. Confidence: 94%."

4. **Policy conflict** — "Two policies apply. HIPAA minimum necessary says restrict access. Your department policy says allow cross-department consults. The system detects the conflict, resolves by compliance-first priority, and audits the resolution. You have conflicting policies in your SOC right now. You just don't know it."

5. **Tab 4: Evidence + ROI** — Tamper-evident audit trail. "Every decision, SHA-256 chained. Your HIPAA compliance officer can trace every decision the AI ever made." ROI calculator with healthcare defaults: "Average healthcare breach costs $10.93 million. Your current SOC processes 400 alerts a day..."

### The Close

"This system doesn't just automate triage. It develops institutional judgment about *your* threat landscape — your clinical systems, your medical devices, your Health-ISAC indicators. A competitor deploying today starts at zero. You start with every decision you've already made."

---

## Leave-Behind Document Outline (1-Page)

**Title:** Compounding Decision Intelligence for Healthcare Security Operations

**Section 1: The Problem (3 sentences)**
Healthcare SOCs face 400+ alerts/day. Current AI tools make the same quality decision on alert 10,000 as alert 1. Analyst institutional knowledge walks out the door at shift change.

**Section 2: How It Works (3 bullets)**
- Six-factor scoring matrix calibrated from verified outcomes (not static rules)
- 20:1 asymmetric trust — earns confidence slowly, loses it fast
- Every decision writes back to a knowledge graph — the system that triages alert 10,000 is measurably sharper

**Section 3: Healthcare-Specific (3 bullets)**
- Health-ISAC indicators integrated into scoring decisions
- HIPAA-aligned tamper-evident audit trail (SHA-256 hash chain)
- Alert categories tuned to healthcare: clinical access, medical device, ransomware precursor

**Section 4: What We Showed (3 bullets)**
- 50-decision simulation with per-category learning curves
- Investigation narrative with calibration history
- ROI projection: [specific numbers from demo]

**Section 5: Next Steps**
Pilot deployment discussion. Data requirements. Timeline.

---

## Persistence Verification (Pre-Sprint Check)

Before executing any prompts, verify that the learning state persists across backend restarts:

```powershell
# In gen-ai-roi-demo-v4-v45 directory:
# 1. Start backend
cd backend
uvicorn app.main:app --reload --port 8000

# 2. Process 2-3 alerts manually, provide feedback

# 3. Check checkpoint file exists
ls app/data/gae_learning_state.json

# 4. Stop backend (Ctrl+C), restart
uvicorn app.main:app --reload --port 8000

# 5. Check that weights are not at initial priors
# GET http://localhost:8000/api/gae/weights
```

If the weights reset to priors on restart, add a persistence fix to SIM-FIX. If they persist, no action needed.

---

## What This Sprint Does NOT Cover (Explicitly)

| Item | Why Not | When |
|---|---|---|
| Tab 2 GAE rewire | Internal tech debt, not visible to CISO | v4.5 post-INOVA |
| Cross-graph discovery (Phase C) | Hard-gated, not MVP-blocking | v4.5 post-INOVA |
| Full evaluation framework | Academic credibility, not CISO demo | v5.0 |
| Ablation framework | Academic credibility | v5.0 |
| Docker/VPS deployment | Demo is laptop-based | v5.5 |
| GAE open-source release | Needs docs + examples first | v5.5 |
| Live Health-ISAC API connector | Seed data is sufficient for demo | v6.0 |
| Manual alert submission | Simulation proves the point | v5.0 |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Simulation learning curves don't look convincing | MEDIUM | HIGH | Phase A gate catches this. If curves are flat or noisy, adjust alert pool or CalibrationProfile parameters before proceeding. |
| Ollama/Qwen not available on demo laptop | LOW | MEDIUM | TemplateNarrativeProvider is the fallback. Narrative still generates with calibration line. |
| Neo4j connection issues during live demo | LOW | HIGH | Pre-demo checklist: backend + Neo4j running 10 min before meeting. Have Loom v2 recording as backup. |
| INOVA asks about live SIEM integration | HIGH | LOW | "Production deployment connects to your Splunk/QRadar through the same connector pattern you see here with Pulsedive and Health-ISAC. Adding a new source is config, not a project." |
| INOVA asks about Axis 3 / cross-graph discovery | MEDIUM | LOW | "The mathematical foundation is published and peer-reviewable. We're implementing the cross-graph discovery mechanism now. The scoring and calibration you're seeing today is the foundation it builds on." |
| Category learning curves all converge at the same rate | MEDIUM | MEDIUM | Different categories MUST have different factor signatures. If convergence rates are too similar, adjust initial W priors or factor weight distributions in SIM-3a to create visible differentiation. |

---

## Decision Log

| # | Decision | Rationale |
|---|---|---|
| 1 | Pull Health-ISAC seed data into v4.5 | INOVA is healthcare. Seeing their ISAC in the graph is high-impact, low-effort. |
| 2 | Defer Tab 2 rewire to post-INOVA | Internal tech debt. CISO won't inspect Tab 2 deeply enough to notice dual paths. |
| 3 | Defer Phase C to post-INOVA | Hard-gated and not needed for the "compounding works" proof. Simulation is the proof. |
| 4 | Add HC-1 (healthcare polish) as new prompt | Healthcare ROI defaults + HIPAA policies + Health-ISAC visibility are INOVA-specific but broadly useful for healthcare vertical. |
| 5 | Healthcare alert categories in SIM-3a | Domain-relevant alerts are dramatically more convincing than generic travel logins for a healthcare CISO. |
| 6 | 11 dev prompts + 3 Opus reviews | Achievable at 1-2 prompts/day over ~13 working days. Week 4 is pure buffer/prep. |
| 7 | GAE backward compat not required | Per instruction. Simplifies GAE-CAL-1/2 — can refactor freely. |
| 8 | Single blog update after Phase A (not two) | v4.1 charts + simulation + ATT&CK + healthcare categories all at once. More impactful than incremental updates. |

---

## Prompt Execution Order (Summary)

```
WEEK 1 (Foundation):
  1. GAE-CAL-1  (CalibrationProfile)         ← GAE repo
  2. GAE-CAL-2  (per-factor decay)           ← GAE repo
  3. SIM-FIX    (atomic reset + TD-026)      ← SOC repo
  4. SIM-1      (SimulationOrchestrator)     ← SOC repo
  5. /model opus review                       ← Both repos

WEEK 2 (Alerts + Frontend):
  6. SIM-3a     (healthcare alert pool + Health-ISAC seed) ← SOC repo
  7. SIM-3b     (wire to orchestrator)       ← SOC repo
  8. SIM-4      (ATT&CK technique IDs)       ← SOC repo
  9. SIM-2      (frontend simulation panel)  ← SOC repo
  10. /model opus review — PHASE A GATE      ← SOC repo

WEEK 3 (Narrative + Polish):
  11. NAR-1     (NarrativeProvider)           ← SOC repo
  12. NAR-2     (Tab 3 narrative panel)       ← SOC repo
  13. HC-1      (healthcare polish)           ← SOC repo
  14. /model opus review — FULL DEMO REVIEW  ← SOC repo

WEEK 4 (Prep):
  15. Demo rehearsal + Loom v2 recording
  16. Leave-behind document
  17. Buffer / polish
```

---

## Updated Backlog Impact

If this sprint plan is approved, the following documents need version bumps:

| Document | Change |
|---|---|
| `backlog_v21` → `v22` | HC-1 added. SIM-3a spec updated for healthcare. TAB2-1/TAB2-2 deferred to post-INOVA. Priority queue reordered. |
| `session_continuation_v19` → `v20` | Sprint plan added. INOVA timeline noted. Prompt order updated. |
| `soc_copilot_design_v3` → update | §15 Simulation Mode: healthcare categories. §18 ATT&CK: healthcare techniques. New §: Health-ISAC seed data. |
| `gap_analysis_v3` → update | New gap: HC (healthcare vertical readiness). Assigned to v4.5 HC-1. |

---

*MVP Sprint Plan v1 | March 1, 2026*
*INOVA CISO conversation in 2-4 weeks. Live demo on laptop.*
*11 dev prompts + 3 Opus reviews = 14 execution units over 3 weeks + 1 week buffer.*
*"The moat is the graph, not the model. The product proves it — for YOUR threat landscape."*
