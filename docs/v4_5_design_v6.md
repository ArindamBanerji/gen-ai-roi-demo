# SOC Copilot — v4.5 Design Document

**Version:** 6.0
**Date:** February 26, 2026
**Status:** Design ready — sequential, begins after v4.0 complete and tagged
**Replaces:** v4_5_design_v5.md (v5.0)
**Parent document:** `v4_design_document_v4.md`
**Prerequisite:** v4.0 complete and tagged (includes all v4 connectors, Docker, Live Graph, Polish, ATT&CK alignment, alert corpus with demo_priority, compounding proof, trust curve)

> **Changes from v5.0:**
> (1) Parent document updated to v4_design_document_v4.md (v4.0 design v4).
> (2) Prerequisite note expanded: v4.0 alert corpus now has 17 alerts with demo_priority
> field and explicit factor profiles — INOVA-4a discovery sweep benefits from richer entity set.
> (3) F5a seed data note: jsmith travel alerts in v4.0 corpus already establish the baseline
> pattern that the discovery sweep disrupts. No additional travel alerts needed in F5a.
> (4) All prompt specs unchanged from v5.0.

---

## Section 0: Scope of v4.5

v4.5 has two workstreams, both beginning after v4.0 is complete and tagged:

| Workstream | What | Prompts |
|---|---|---|
| INOVA MVP | UCL resolution, write-back relationships, healthcare connectors, discovery sweep, **cross-domain demo moment**, HIPAA framing, UI surface | 14 prompts (INOVA-1a through INOVA-6 + F5a/F5b/F5c) |
| Flash Tier Mimic | Synthetic feed, forensic scorer, UCL handoff, dashboard | 4 prompts (FT-MIMIC-1 through FT-MIMIC-4) |

**Total: 18 prompts across 7 sessions (INOVA Sessions A–E + Flash Tier Session F + expanded Session D).**

---

## Section 1: What v3.2 and v4.0 Already Provide

### From v4.0 (complete and tagged — ALL capabilities available)

*(Same as v4.0 table, plus:)*

| v4.0 Artifact | Used By |
|---|---|
| F1a/F1b (ATT&CK alignment) | All INOVA prompts — alerts carry technique IDs |
| F2a/F2b/F2c (realistic alert corpus — 17 alerts with demo_priority) | INOVA-4a (discovery sweep has more entities to discover across). F5a seed data supplements the existing 5 jsmith travel alerts. |
| F3a/F3b (investigation narrative) | Available — narratives reference calibration history |
| F4a-F4d (compounding proof) | INOVA-5/6 (Tab 4 compounding panel already exists; INOVA orders and extends it) |
| F6a/F6b (trust curve) | Available — trust scores persist through Live Graph |

**Note on v4.0 corpus and F5a:** The v4.0 corpus includes 5 travel/VPN alerts for jsmith (ALERT-7823, 7830, 7835, 7841, 7845). These establish a strong historical pattern of benign Singapore logins — exactly the baseline that the F5a discovery scenario disrupts when it discovers the role-change × threat-spike correlation. The deep path demo in v4.0 already builds this pattern through sequential processing with feedback. F5a adds the organizational role change and threat campaign data that enables the discovery — it does not need to add more travel alerts.

---

## Section 2: INOVA Sessions A–C

*(INOVA-1a, INOVA-1b, INOVA-2, INOVA-3a, INOVA-3b — unchanged from v5.0)*

---

## Section 3: INOVA Session D — Discovery Sweep + Cross-Domain Demo Moment (EXPANDED)

Session D now has 6 prompts: the original INOVA-4a/4b/4c plus 3 new F5 prompts.

*(INOVA-4a, INOVA-4b, INOVA-4c — unchanged from v5.0)*

---

#### Prompt F5a — Backend: Cross-Domain Discovery Demo Scenario — Seed Data

**Scope:** Seed the graph with the specific entities that enable the Singapore + CFO + threat spike discovery
**Files touched:**
- `backend/seed_neo4j.py` (modify — add discovery scenario entities)

**What to build:**

Add the following to the seed script (supplemental to existing v4.0 seed data):

**Organizational graph additions:**
```
(:User {name: "jsmith", role: "CFO", role_change_date: "2026-02-05",
        previous_role: "VP_Finance", access_level: "executive",
        risk_profile_change: true})
```
Update existing jsmith node with role change properties.

**Threat intel graph additions:**
```
(:ThreatCampaign {name: "SG-CRED-STORM-2026", type: "credential_stuffing",
                  region: "singapore", increase_pct: 340,
                  first_seen: "2026-02-20", active: true,
                  mitre_technique: "T1110.004"})
-[:TARGETS_REGION]->(:Region {name: "APAC-SG"})
```

**Decision history additions:**
```
14 prior (:ProcessedAlert) nodes for jsmith Singapore logins,
all with outcome: "false_positive_close", confidence: 0.89
Creating a strong historical pattern of benign travel logins.
```

**Note:** The v4.0 corpus already includes 5 jsmith travel alerts. The 14 ProcessedAlert nodes here represent *past decisions* (not new alert definitions) — they simulate 14 prior triage outcomes that establish the strong historical benign pattern.

**Verification test:**
```
1. Run seed_neo4j.py
2. Neo4j: MATCH (u:User {name: "jsmith"}) RETURN u → shows role_change_date
3. Neo4j: MATCH (t:ThreatCampaign {region: "singapore"}) RETURN t → shows 340% increase
4. Neo4j: MATCH (p:ProcessedAlert) WHERE p.user = "jsmith" RETURN count(p) → 14
```

---

#### Prompt F5b — Frontend: Discovery Panel in Tab 4

**Scope:** Visualize cross-domain discoveries with graph domain highlighting
**Files touched:**
- `frontend/src/components/tabs/CompoundingTab.tsx` (modify — add discovery panel)
- `frontend/src/lib/api.ts` (add discovery endpoint call)

**What to build:**

New "Cross-Domain Discoveries" panel in Tab 4 (between Compounding Proof and Evidence Ledger):

**Discovery card layout:**
```
┌─────────────────────────────────────────────┐
│ 🔍 DISCOVERY: Role-Change × Threat-Spike    │
│                                              │
│ Domains: Organizational ↔ Threat Intel ↔     │
│          Decision History                     │
│                                              │
│ Finding: jsmith promoted to CFO (Feb 5).     │
│ Singapore credential campaign +340% (Feb 20).│
│ 14 prior Singapore logins resolved benign.    │
│                                              │
│ Impact: New scoring dimension added:          │
│ role_recency_risk (weight: 0.31)             │
│                                              │
│ Confidence adjustment: 89% → 34%             │
│ "Re-evaluate — context has changed"          │
│                                              │
│ ⚠️ Nobody programmed this rule.              │
│   The system discovered it.                  │
└─────────────────────────────────────────────┘
```

- Show which graph domains were involved (color-coded to match POS-01 graphic)
- Show the new scoring dimension that was created
- Show the confidence impact
- The tagline: "Nobody programmed this rule. The system discovered it."

**Verification test:**
```
1. After discovery sweep runs (INOVA-4a/4b/4c)
2. Tab 4 shows discovery panel with the role-change × threat-spike finding
3. Three graph domains highlighted
4. New scoring dimension visible
5. Confidence adjustment shown
```

---

#### Prompt F5c — Backend: Wire Discovery Back to Scoring Matrix

**Scope:** Discovered dimensions feed back into the triage scoring for subsequent alerts
**Files touched:**
- `backend/app/services/triage.py` (modify — check for discovered dimensions before scoring)
- `backend/app/services/situation.py` (modify — incorporate discovered factors)

**What to build:**

When a cross-graph discovery creates a new scoring dimension:
1. Store it as a `:DiscoveredFactor` node in Neo4j with properties: name, weight, source_domains, discovery_date
2. When analyzing a new alert of a matching type, the situation analyzer checks for relevant `:DiscoveredFactor` nodes
3. If found, include the discovered factor in the scoring matrix (extends the 6-factor vector to 7+)
4. The confidence computation uses the expanded factor set

**The demo flow:**
1. Process jsmith Singapore login BEFORE the discovery → confidence 89% (historical pattern says benign)
2. Discovery sweep runs, finds the role-change × threat-spike correlation
3. Process jsmith Singapore login AFTER the discovery → confidence drops to 34% (new dimension: role_recency_risk)
4. The system has extended its own evaluation criteria

**Verification test:**
```
1. Analyze jsmith travel alert before discovery → confidence ~89%
2. Run discovery sweep (INOVA-4a)
3. Analyze same type of jsmith alert after discovery → confidence ~34%
4. Factor breakdown shows 7 factors (original 6 + role_recency_risk)
5. Narrative references the discovered dimension
```

---

## Section 4: INOVA Sessions E–F

*(INOVA-5, INOVA-6, FT-MIMIC-1 through FT-MIMIC-4 — unchanged from v5.0)*

### F9 Note: Compliance Framing in INOVA-6

INOVA-6 already includes HIPAA evidence ledger framing. Ensure the prompt spec includes:
- HIPAA §164.530(j) export format option in the evidence ledger CSV export
- Configurable retention period labels (default: 6 years per HIPAA)
- "Compliance Verified" badge on Tab 4 when all decisions have complete audit chains
- No additional prompts needed — this is a requirement on the existing INOVA-6 spec.

---

## Section 5: Build Sequence (Updated)

```
PREREQUISITE: v4.0 complete and tagged (all 5 phases including compounding proof,
              17-alert corpus with demo_priority, trust curve)

SESSION A: UCL Entity Resolution (2 prompts)
  INOVA-1a (resolution service) + INOVA-1b (opt connectors in)
  TEST: Entity resolution working for Pulsedive + GreyNoise

SESSION B: Write-Back Relationships (1 prompt)
  INOVA-2 (TRIGGERED_EVOLUTION + CALIBRATED_BY)
  TEST: Feedback creates traversable relationships

SESSION C: Healthcare Connectors (2 prompts)
  INOVA-3a (CISA KEV live) + INOVA-3b (Health-ISAC mock)
  TEST: Healthcare-specific TI in graph

SESSION D-1: Discovery Sweep Infrastructure (3 prompts)
  INOVA-4a (sweep service) + INOVA-4b (UI panel) + INOVA-4c (scheduler)
  TEST: Sweep discovers Royal × APAC pattern

SESSION D-2: Cross-Domain Demo Moment (3 prompts)
  F5a (discovery scenario seed data) + F5b (discovery panel UI) + F5c (wire to scoring)
  TEST: jsmith confidence drops from 89% to 34% after discovery. New scoring dimension visible.

SESSION E: Loop 3 + HIPAA (2 prompts)
  INOVA-5 (governing signal labels) + INOVA-6 (HIPAA framing + compliance badge)
  TEST: Evidence ledger with HIPAA export. Compliance badge.

SESSION F: Flash Tier Mimic (4 prompts)
  FT-MIMIC-1 (synthetic feed) + FT-MIMIC-2 (scorer) + FT-MIMIC-3 (handoff) + FT-MIMIC-4 (dashboard)
  TEST: 60-70% volume reduction. Write-backs to graph.

TAG: v4.5 — "INOVA MVP + Flash Tier validated. Cross-domain discovery proved."
```

**Total: 18 prompts across 7 sessions.**

---

## Appendix: Version History

| Version | Date | Changes |
|---|---|---|
| **1.0** | **Feb 24, 2026** | Initial v4.5 design (parallel with v4). |
| **2.0** | **Feb 25, 2026** | INOVA-4a discovery seed fix. Flash Tier added. File paths for v3.2. |
| **3.0** | **Feb 25, 2026** | Parallel → sequential execution. |
| **4.0** | **Feb 26, 2026** | v4.0 prerequisite expanded. Sequential build confirmed. |
| **5.0** | **Feb 26, 2026** | F5 (Cross-Domain Discovery Moment) added: 3 prompts in expanded Session D. F9 confirmed in INOVA-6. 18 prompts, 7 sessions. |
| **6.0** | **Feb 26, 2026** | **Parent doc updated to v4_design_document_v4.md. Prerequisite note: v4.0 corpus now 17 alerts with demo_priority. F5a note clarified: 5 jsmith travel alerts from v4.0 establish the baseline pattern; F5a adds role-change + threat-campaign data, not more travel alerts.** |

---

*SOC Copilot — v4.5 Design Document v6 | February 26, 2026*
*Theme: "INOVA MVP + Flash Tier + Cross-Domain Discovery." | 18 prompts, 7 sessions | Prerequisite: v4.0 complete*
