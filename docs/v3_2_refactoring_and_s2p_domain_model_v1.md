# SOC Copilot Demo — v3.2 Refactoring Design + S2P Domain Model

**Version:** 1.0
**Date:** February 25, 2026
**Status:** Design document. Prerequisite for v4.0 build.
**Scope:** (1) Deep analysis of S2P supply chain use case to validate domain-agnostic claims, (2) v3.2 refactoring plan that extracts domain-agnostic core from SOC-specific content, (3) bridge to v4.0.
**Acceptance test:** v3.2 demo works identically to v3.1.1. Code is structured so a second domain module can plug in without touching the core.

---

## SECTION 0: Why This Document Exists

The SOC Copilot has evolved through v1 → v2 → v2.5 → v3 → v3.1 without an architecture review. Each version added features additively. The codebase works — the Opus code review confirmed "demo-ready with caveats" — but the architecture has accumulated domain-specific hardcoding throughout every layer.

The CI blog and math blog claim the architecture is domain-agnostic: "same four-layer architecture, same knowledge graph, same loops — one for security, one for ITSM, one for procurement." The v4 design document's vision section describes a platform thesis with multi-domain copilots. But the current codebase can't deliver on that claim without surgery.

Two things happened simultaneously:
1. Customer conversations validated the platform thesis — buyers want to see this applied beyond SOC
2. The v3.1.1 codebase hit the point where additive development creates diminishing returns

The right move is to refactor before adding features. v3.2 is that refactoring: same demo, clean architecture, ready for domain two.

**The S2P use case in this document is NOT a build plan.** It's a validation test. If the refactored architecture can cleanly accommodate an S2P procurement copilot, the refactoring went deep enough. If it can't, we missed something.

---

## SECTION 1: S2P Supply Chain Domain Model (Deep Dive)

### 1.1 Why Source-to-Pay

Source-to-Pay (S2P) is the full procurement lifecycle: from identifying a need, through sourcing and purchasing, to receiving goods and paying the invoice. It maps structurally to SOC alert triage because:

- **Repeated decisions over structured context** — purchase order approvals, supplier selections, invoice matches happen hundreds of times per week
- **Multiple data sources that nobody fuses** — ERP, supplier scorecards, commodity indices, geopolitical feeds, contract databases, demand forecasts — each consulted independently, fusion in the buyer's head
- **High-cost errors are asymmetric** — approving a bad supplier is catastrophically more expensive than over-scrutinizing a good one (production shutdown vs. 2-day delay)
- **Institutional knowledge walks out the door** — "Maria knows that MFG-ASIA-017 always ships late in monsoon season" isn't in any system

The parallel to SOC is precise:

| SOC Pattern | S2P Equivalent |
|---|---|
| Alert fires → analyst triages | PO request arrives → buyer approves/rejects |
| 5 browser tabs for IOC checks | 5 tabs for supplier checks (D&B, compliance, commodity price, ERP history, contract terms) |
| Analyst holds fusion in their head | Buyer holds supplier risk assessment in their head |
| Shift change loses context | Team rotation loses supplier history |
| SIEM doesn't learn from closures | ERP doesn't learn from approval outcomes |

### 1.2 The Decision Point: PO Approval / Risk Assessment

We focus on one high-frequency decision within S2P: **should this Purchase Order be approved, flagged for review, dual-sourced, or escalated?**

This is the "alert triage" of procurement. It happens on every PO. It's where the graph makes the biggest difference. And it's where compounding intelligence has the clearest ROI story.

**The scenario (equivalent to the jsmith Singapore login):**

A purchase order arrives: PO-2026-4471. Material: titanium fasteners, 50,000 units. Supplier: MFG-ASIA-017 (Shenzhen, China). Amount: $142,000. Requested by: Plant Manager, Austin facility. Delivery needed: 14 days.

**What the buyer checks today (the "five tabs" equivalent):**

1. **ERP history** — MFG-ASIA-017's last 20 POs. On-time rate. Defect rate. Price trend.
2. **Supplier scorecard** — D&B financial health. Compliance certifications (ISO, conflict minerals). ESG rating.
3. **Commodity index** — current titanium spot price vs. contract price. Is $2.84/unit reasonable?
4. **Geopolitical risk** — trade tensions, tariffs, logistics disruptions in the Shenzhen corridor
5. **Contract terms** — is this within the frame agreement? Volume commitments? Penalty clauses?
6. **Alternative suppliers** — who else can provide titanium fasteners at comparable quality? Lead time?

Each source returns an independent assessment. The buyer fuses them mentally. No record. No audit trail. The assessment walks out when the buyer goes on vacation.

**What the graph knows (the compounding version):**

The context graph holds all six data sources as connected entities. When PO-2026-4471 arrives, the Situation Analyzer traverses:

- MFG-ASIA-017's delivery history (23 POs, 87% on-time, 2 quality holds in Q3)
- The titanium price curve (contract: $2.70/unit, spot: $3.12/unit — the PO at $2.84 is 5.2% above contract)
- A Reuters geopolitical feed flagging Shenzhen port congestion (3-day average delays this week)
- The Austin plant's inventory position (12 days of titanium fastener stock remaining — delivery needed in 14, buffer = 0 with congestion)
- MFG-ASIA-017's financial health (Z-score dropped from 2.8 to 2.1 in last quarter — still solvent but trending)
- Alternative suppliers: SUPPLY-EU-003 (Hamburg) can deliver in 21 days at $3.10/unit; SUPPLY-MX-009 (Monterrey) can deliver in 10 days at $2.95/unit

**The cross-graph discovery moment (equivalent to Singapore credential stuffing × jsmith promotion):**

The weekly sweep discovers: "MFG-ASIA-017's financial Z-score decline correlates with their recent quality holds. Suppliers whose Z-score drops below 2.0 historically show a 4× increase in delivery failures within 6 months. Simultaneously, Shenzhen port congestion is seasonal — it peaks in Q1 monsoon and again in Q3 typhoon season. The system's 87% on-time score for MFG-ASIA-017 is INFLATED because all historical POs were in Q2/Q4. Adjusted for seasonal risk, the effective on-time estimate is 71%."

Nobody programmed that rule. The graph discovered it from the intersection of financial health data, delivery history, and geopolitical feeds. The next PO from MFG-ASIA-017 is evaluated with different criteria.

### 1.3 S2P Graph Schema

**Node types (6 domains — maps to SOC's 6 domains):**

| SOC Domain | S2P Domain | Node Types |
|---|---|---|
| Security Context | Supplier Performance | :Supplier, :SupplierScore, :QualityHold |
| Decision History | Procurement Decision History | :PurchaseOrder, :PODecision, :POOutcome |
| Threat Intelligence | Market & Geopolitical Intelligence | :CommodityPrice, :GeopoliticalEvent, :TradeAlert |
| Organizational | Demand & Operations | :Plant, :Material, :InventoryPosition, :DemandForecast |
| Behavioral Baseline | Logistics & Carrier Data | :Carrier, :ShipmentRoute, :DeliveryRecord |
| Compliance & Policy | Financial Health & Contracts | :Contract, :FrameAgreement, :ComplianceCheck, :FinancialHealth |

**Key relationships:**

```
(:Supplier)-[:DELIVERS]->(:Material)
(:Supplier)-[:HAS_SCORE]->(:SupplierScore)
(:Supplier)-[:HAS_FINANCIAL_HEALTH]->(:FinancialHealth)
(:Supplier)-[:LOCATED_IN]->(:Region)
(:PurchaseOrder)-[:SOURCES_FROM]->(:Supplier)
(:PurchaseOrder)-[:FOR_MATERIAL]->(:Material)
(:PurchaseOrder)-[:REQUESTED_BY]->(:Plant)
(:PurchaseOrder)-[:TRIGGERED_DECISION]->(:PODecision)
(:PODecision)-[:TRIGGERED_EVOLUTION]->(:EvolutionEvent)   # same pattern!
(:PODecision)-[:HAD_OUTCOME]->(:POOutcome)
(:GeopoliticalEvent)-[:AFFECTS_REGION]->(:Region)
(:CommodityPrice)-[:FOR_MATERIAL]->(:Material)
(:Contract)-[:WITH_SUPPLIER]->(:Supplier)
(:Contract)-[:FOR_MATERIAL]->(:Material)
(:InventoryPosition)-[:AT_PLANT]->(:Plant)
(:InventoryPosition)-[:OF_MATERIAL]->(:Material)
```

### 1.4 S2P Situation Types (6 types — maps to SOC's 6)

| SOC Situation | S2P Situation | Classification Signal |
|---|---|---|
| TRAVEL_LOGIN_ANOMALY | ROUTINE_REORDER | PO within contract terms, supplier healthy, adequate inventory |
| KNOWN_PHISHING_CAMPAIGN | PRICE_ANOMALY | Unit price deviates >5% from contract or >10% from commodity index |
| SUSPICIOUS_PATTERN | SUPPLY_RISK | Supplier Z-score declining, quality holds increasing, or region flagged |
| KNOWN_BENIGN | DEMAND_SPIKE | Requested quantity >2× historical average for this material/plant |
| ESCALATION_REQUIRED | SINGLE_SOURCE_DEPENDENCY | No alternative supplier available; concentration risk >70% |
| POLICY_VIOLATION | COMPLIANCE_FLAG | Supplier missing required certification; ESG score below threshold |

### 1.5 S2P Factor Vector (6 dimensions — maps to SOC's 6)

| SOC Factor | S2P Factor | How It's Computed |
|---|---|---|
| travel_match | price_variance | |contract_price - PO_price| / contract_price |
| asset_criticality | demand_urgency | days_of_stock_remaining / lead_time_days (ratio <1.0 = urgent) |
| VIP_status | supplier_reliability | weighted(on_time_pct, quality_hold_count, Z_score_trend) |
| time_anomaly | geopolitical_risk | region_risk_score from market intelligence feed |
| device_trust | alternative_availability | count of qualified alternative suppliers / total qualified |
| pattern_history | spend_pattern_history | historical approval rate for this supplier × material combo |

### 1.6 S2P Action Set (4 actions — maps to SOC's 4)

| SOC Action | S2P Action | When |
|---|---|---|
| false_positive_close | auto_approve_po | All factors green; within contract; supplier healthy |
| enrich_and_wait | flag_for_review | One or more yellow flags; needs buyer attention |
| escalate_to_tier2 | trigger_dual_sourcing | Supply risk high; proactively split order across suppliers |
| escalate_as_incident | escalate_to_procurement_lead | Multiple red flags; policy conflict; above delegation authority |

### 1.7 S2P Policy Conflicts (maps to SOC's POLICY-SOC-003 vs POLICY-SEC-007)

**Example conflict:**

- POLICY-PROC-001: Auto-approve POs under $150K from tier-1 suppliers with frame agreements (priority 3)
- POLICY-RISK-003: Manual review required for any supplier with financial health Z-score below 2.5 (priority 1)
- **Conflict:** MFG-ASIA-017 is tier-1 with a frame agreement ($142K PO qualifies for auto-approve) BUT their Z-score just dropped to 2.1 (requires manual review). Risk policy wins — priority 1 overrides priority 3.

This is structurally identical to the SOC demo's policy conflict beat.

### 1.8 S2P Asymmetry Ratio

SOC uses 20:1 because a missed threat is catastrophically worse than an unnecessary escalation. S2P uses a different ratio:

- **Penalty for wrong approval (approved a bad PO that caused supply disruption):** High — production stoppage costs $50K-$500K/day
- **Penalty for unnecessary escalation (flagged a good PO for review):** Low — 2-day delay, $200 in buyer time
- **Ratio:** ~10:1 to 15:1 depending on material criticality

For critical materials (production line components), ratio is 15:1. For indirect materials (office supplies), ratio is 3:1. The asymmetry ratio is **parameterized per material category** — this is a domain-specific decision that the framework must support.

### 1.9 S2P Decision Economics (maps to SOC's time/cost/risk per option)

| Action | Time Saved | Cost | Residual Risk |
|---|---|---|---|
| auto_approve_po | 45 min buyer time | $0 (no intervention) | Low — if scoring is calibrated |
| flag_for_review | 0 (buyer reviews) | $127 (buyer time) | Medium — depends on buyer judgment |
| trigger_dual_sourcing | -2 days (split logistics) | +15-25% unit cost premium | Low — supply continuity protected |
| escalate_to_procurement_lead | -3 days (escalation delay) | $340 (senior buyer + meetings) | Very low — maximum oversight |

### 1.10 What This Analysis Reveals About Refactoring

**Everything that's the same (domain-agnostic core):**
- The scoring matrix mechanism: P(action|trigger) = softmax(f · W^T / τ)
- The weight update rule: W[a,:] ← W[a,:] + α · r(t) · f(t) · δ(t)
- The three-loop architecture (Situation Analyzer, AgentEvolver, RL Reward/Penalty)
- The eval gate pattern (pass/fail before action)
- TRIGGERED_EVOLUTION relationship creation
- The evidence ledger (SHA-256 chain)
- The ROI calculator framework
- The compounding metrics structure (week-over-week)
- The policy conflict detection/resolution mechanism
- The outcome feedback mechanism
- The decision explainer (factor breakdown with visual weights)
- The four-tab demo structure

**Everything that's different (domain-specific content):**
- Graph schema (node types, relationship types, seed data)
- Situation types (6 per domain)
- Factor vector (6 dimensions per domain, different computations)
- Action set (4 actions per domain, different labels and economics)
- Policy registry (different policies, different priorities)
- Asymmetry ratio (different per domain, potentially parameterized within domain)
- External data connectors (Pulsedive/GreyNoise for SOC; D&B/commodity feeds for S2P)
- UI labels, narratives, demo queries
- LLM narration templates

**The ratio:** roughly 55% of the codebase is domain-specific content, 25% is domain-agnostic core, and 20% is infrastructure. The refactoring extracts the 25% as reusable core and makes the 55% pluggable.

---

## SECTION 2: Current Architecture Analysis

### 2.1 Where Domain-Specific Code Lives Today

Based on the Opus code review (Pass 1 + Pass 2) and full codebase analysis:

| File | Lines | Domain-Specific Content | Refactoring Action |
|---|---|---|---|
| **Backend** |
| services/agent.py | ~250 | Scoring rules, factor computation, action set | Extract factor/action config; parameterize scoring |
| services/situation.py | ~250 | 6 situation types, classification logic, option evaluation | Extract situation type registry; parameterize classification |
| services/triage.py | ~284 | Factor templates per alert, _analyzed_alerts state | Extract factor computation interface; domain provides templates |
| services/feedback.py | ~284 | Asymmetry ratio (20:1 hardcoded), SOC-specific narratives | Parameterize ratio; extract narrative templates |
| services/policy.py | ~440 | POLICY-SOC-003, POLICY-SEC-007, SOC-specific conflict scenarios | Extract policy registry; domain provides policies |
| services/audit.py | ~293 | Mostly domain-agnostic already | Minor: parameterize field names |
| services/evolver.py | ~200 | Prompt variant names (TRAVEL_CONTEXT_v1), SOC-specific stats | Extract variant registry; domain provides variants |
| services/reasoning.py | ~200 | LLM narration with SOC-specific templates | Extract template interface |
| services/threat_intel.py | ~200 | Pulsedive-specific API calls | Already being refactored to connector pattern in v4 |
| routers/triage.py | ~764 | ALERT-7823/7824 hardcoded paths, SOC-specific endpoints | Extract decision flow; parameterize per domain |
| routers/evolution.py | ~400 | SOC-specific deployment data, alert processing | Extract evolution flow; parameterize |
| routers/soc.py | ~637 | Metric registry, cross-context queries, threat landscape | Domain-specific Tab 1 — stays in domain module |
| routers/metrics.py | ~300 | Business impact numbers ($127K, 847 hrs) | Parameterize; domain provides its own metrics |
| db/neo4j.py | ~300 | Cypher queries reference :Alert, :User, :Pattern | Abstract query templates; domain provides node types |
| seed_neo4j.py | ~600 | All SOC-specific seed data | Domain provides its own seed data |
| **Frontend** |
| AlertTriageTab.tsx | ~1037 | SOC labels, alert-specific UI flows | Largest refactoring target — extract decision flow component |
| RuntimeEvolutionTab.tsx | ~700 | SOC deployment labels, alert type names | Extract evolution view component; parameterize labels |
| SOCAnalyticsTab.tsx | ~626 | SOC queries, threat landscape | Domain-specific Tab 1 — stays in domain module |
| CompoundingTab.tsx | ~600 | SOC-specific metrics, business impact numbers | Parameterize impact numbers; extract compounding view |

### 2.2 Structural Issues from Code Review

The Opus review (Pass 2: Architecture) surfaced these cross-cutting issues:

1. **A1 — Incomplete reset:** 4 of 10 state stores aren't cleared on reset. Root cause: scattered in-memory state with no unified manager.
2. **A2 — Audit chain integrity:** Chain computes correctly but doesn't handle reset boundaries.
3. **A3 — Decision factor inconsistency:** Factor computation is hardcoded per alert_id in triage.py — doesn't scale to new alert types, let alone new domains.
4. **A4 — Threat intel data flow:** End-to-end works for ALERT-7823 only; ALERT-7824 has no IOC mapping.
5. **A6 — Pydantic v2 deprecation:** 4 files use .dict() instead of .model_dump().

These aren't just bugs — they're symptoms of architectural decisions that need to change for multi-domain support.

### 2.3 The State Management Problem

Current state is scattered across 6 modules:

```
audit.py:     _DECISIONS (list)
evolver.py:   PROMPT_STATS, ACTIVE_PROMPTS, RECENT_PROMOTIONS (dicts)
feedback.py:  FEEDBACK_GIVEN, PATTERN_CONFIDENCE (dicts)
policy.py:    CONFLICTS_RESOLVED (dict)
situation.py: (stateless — good)
triage.py:    _analyzed_alerts (dict)
```

The reset flow has to know about all of these individually. Adding a second domain doubles the state surface. The fix: a unified DemoStateManager that each service registers with.

---

## SECTION 3: v3.2 Refactoring Plan

### 3.1 Design Principles

1. **Same demo, different code.** v3.2 produces byte-for-byte identical demo output as v3.1.1 for the happy path. The user sees nothing different.
2. **Domain config, not domain code.** SOC-specific content moves into configuration/registry files that a second domain could duplicate and modify.
3. **Framework calls domain, not the reverse.** The core decision flow (analyze → score → decide → execute → verify → evolve) is framework code. It calls into domain-specific registries for content.
4. **Fix code review findings.** The HIGH findings from the Opus review get fixed as part of the refactoring, not as separate patches.
5. **No new features.** v3.2 adds zero new capabilities. ACCP stays at 14/21.

### 3.2 Target Directory Structure

```
gen-ai-roi-demo-v3/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app — registers domain + core routes
│   │   │
│   │   ├── core/                      # Domain-agnostic framework (NEW)
│   │   │   ├── __init__.py
│   │   │   ├── domain_registry.py     # Registry: which domain is active, its config
│   │   │   ├── state_manager.py       # Unified demo state management + reset
│   │   │   ├── scoring.py             # Eq. 4: softmax(f · W^T / τ) — parameterized
│   │   │   ├── evolution.py           # Eq. 4b: weight update — parameterized
│   │   │   ├── feedback.py            # Outcome feedback — parameterized asymmetry ratio
│   │   │   ├── policy_engine.py       # Policy conflict detection/resolution — generic
│   │   │   ├── audit_engine.py        # Evidence ledger + SHA-256 chain — generic
│   │   │   ├── eval_gates.py          # Structural quality gates — generic
│   │   │   └── decision_flow.py       # Orchestrator: analyze → score → decide → execute → verify
│   │   │
│   │   ├── domains/                   # Domain-specific content (NEW)
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # Abstract DomainConfig interface
│   │   │   └── soc/                   # SOC domain module
│   │   │       ├── __init__.py
│   │   │       ├── config.py          # SOC domain config: factors, actions, asymmetry, etc.
│   │   │       ├── situations.py      # 6 SOC situation types + classification logic
│   │   │       ├── factors.py         # 6 SOC factor computations
│   │   │       ├── policies.py        # SOC policy registry
│   │   │       ├── narratives.py      # LLM narration templates for SOC
│   │   │       ├── seed_data.py       # Neo4j seed data for SOC demo
│   │   │       ├── queries.py         # SOC-specific graph queries (Tab 1 metrics, cross-context)
│   │   │       └── connectors.py      # SOC external sources (Pulsedive, GreyNoise — prep for v4)
│   │   │
│   │   ├── routers/                   # Slimmed down — calls core + domain
│   │   │   ├── __init__.py
│   │   │   ├── decision.py            # Replaces triage.py — generic decision flow endpoints
│   │   │   ├── evolution.py           # Runtime evolution — parameterized
│   │   │   ├── analytics.py           # Replaces soc.py — delegates to domain queries
│   │   │   ├── metrics.py             # Compounding metrics — parameterized
│   │   │   ├── audit.py               # Evidence ledger endpoints (already mostly generic)
│   │   │   └── demo.py                # Reset/seed endpoints — uses state_manager
│   │   │
│   │   ├── services/                  # Thin wrappers that call core (transitional)
│   │   │   ├── __init__.py
│   │   │   ├── reasoning.py           # LLM narration — calls domain.narratives
│   │   │   └── threat_intel.py        # Stays for now — becomes connector in v4
│   │   │
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   └── neo4j.py               # Neo4j client — query templates parameterized
│   │   │
│   │   └── models/
│   │       ├── __init__.py
│   │       └── schemas.py             # Pydantic models — .dict() → .model_dump()
│   │
│   ├── seed_neo4j.py                  # Delegates to active domain's seed_data
│   └── requirements.txt
│
├── frontend/
│   └── src/
│       ├── main.tsx
│       ├── App.tsx                     # v3.2 version label; domain name in header
│       ├── lib/
│       │   ├── api.ts                  # API client — endpoint URLs unchanged
│       │   └── domain.ts              # Domain config for frontend (labels, colors, etc.)
│       └── components/
│           ├── tabs/
│           │   ├── AnalyticsTab.tsx     # Renamed from SOCAnalyticsTab — uses domain config
│           │   ├── DecisionTab.tsx      # Renamed from AlertTriageTab — generic decision flow
│           │   ├── EvolutionTab.tsx     # Renamed from RuntimeEvolutionTab — parameterized
│           │   └── CompoundingTab.tsx   # Parameterized metrics/labels
│           └── shared/                 # Extracted reusable components (NEW)
│               ├── FactorChart.tsx      # Factor breakdown bar chart
│               ├── SituationPanel.tsx   # Situation classification display
│               ├── PolicyConflict.tsx   # Already exists — move here
│               ├── OutcomeFeedback.tsx  # Already exists — move here
│               └── EvidenceLedger.tsx   # Extract from CompoundingTab
```

### 3.3 The Domain Config Interface

This is the key abstraction. Every domain implements this interface:

```python
# backend/app/domains/base.py

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple
from dataclasses import dataclass

@dataclass
class DomainAction:
    id: str              # "auto_approve_po", "false_positive_close"
    label: str           # "Auto-Approve PO", "Close as False Positive"
    time_saved_min: float
    cost_dollars: float
    risk_level: str      # "low", "medium", "high", "critical"

@dataclass
class DomainFactor:
    id: str              # "price_variance", "travel_match"
    label: str           # "Price Variance", "Travel Match"
    description: str

@dataclass  
class DomainSituationType:
    id: str              # "SUPPLY_RISK", "TRAVEL_LOGIN_ANOMALY"
    label: str
    description: str
    color: str           # for UI badge

@dataclass
class DomainPolicy:
    id: str              # "POLICY-PROC-001"
    name: str
    rule: str            # human-readable rule description
    priority: int        # lower = higher priority
    action_override: str # which action this policy forces

class DomainConfig(ABC):
    """Every domain implements this interface."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """e.g., 'soc', 'supply_chain'"""
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """e.g., 'SOC Copilot', 'Procurement Copilot'"""
    
    @property
    @abstractmethod
    def trigger_entity(self) -> str:
        """Primary entity type that triggers decisions. 'Alert' for SOC, 'PurchaseOrder' for S2P"""
    
    @property
    @abstractmethod
    def factors(self) -> List[DomainFactor]:
        """The 6 (or N) factors in the scoring vector"""
    
    @property
    @abstractmethod
    def actions(self) -> List[DomainAction]:
        """The 4 (or N) possible actions"""
    
    @property
    @abstractmethod
    def situation_types(self) -> List[DomainSituationType]:
        """The 6 (or N) situation classifications"""
    
    @property
    @abstractmethod
    def policies(self) -> List[DomainPolicy]:
        """Domain policy registry"""
    
    @property
    @abstractmethod
    def asymmetry_ratio(self) -> float:
        """Penalty multiplier for incorrect decisions. 20.0 for SOC, 10.0-15.0 for S2P"""
    
    @abstractmethod
    def classify_situation(self, context: Dict) -> Tuple[str, float]:
        """Given graph context, return (situation_type_id, confidence)"""
    
    @abstractmethod
    def compute_factors(self, context: Dict) -> List[Dict]:
        """Given graph context, return factor values for scoring"""
    
    @abstractmethod
    def get_seed_queries(self) -> List[str]:
        """Cypher queries to seed the demo graph"""
    
    @abstractmethod
    def get_graph_queries(self) -> Dict[str, str]:
        """Named Cypher query templates for this domain"""
    
    @abstractmethod
    def get_narration_templates(self) -> Dict[str, str]:
        """LLM prompt templates for reasoning narration"""
```

### 3.4 The SOC Domain Config (What Currently Exists, Reorganized)

```python
# backend/app/domains/soc/config.py

from app.domains.base import DomainConfig, DomainAction, DomainFactor, ...

class SOCDomainConfig(DomainConfig):
    
    name = "soc"
    display_name = "SOC Copilot"
    trigger_entity = "Alert"
    
    factors = [
        DomainFactor("travel_match", "Travel Match", "Calendar confirms travel to login location"),
        DomainFactor("asset_criticality", "Asset Criticality", "Sensitivity level of accessed asset"),
        DomainFactor("vip_status", "VIP Status", "Executive or high-privilege user"),
        DomainFactor("time_anomaly", "Time Anomaly", "Login outside normal working hours"),
        DomainFactor("device_trust", "Device Trust", "Known corporate device with MDM enrollment"),
        DomainFactor("pattern_history", "Pattern History", "Historical pattern for similar alerts"),
    ]
    
    actions = [
        DomainAction("false_positive_close", "Close as False Positive", 45.0, 0.0, "low"),
        DomainAction("enrich_and_wait", "Enrich and Wait", 15.0, 42.0, "medium"),
        DomainAction("escalate_tier2", "Escalate to Tier 2", 0.0, 127.0, "medium"),
        DomainAction("escalate_incident", "Escalate as Incident", -30.0, 340.0, "high"),
    ]
    
    situation_types = [
        DomainSituationType("TRAVEL_LOGIN_ANOMALY", "Travel Login Anomaly", "...", "#3B82F6"),
        DomainSituationType("KNOWN_PHISHING_CAMPAIGN", "Known Phishing Campaign", "...", "#EF4444"),
        DomainSituationType("SUSPICIOUS_PATTERN", "Suspicious Pattern", "...", "#F59E0B"),
        DomainSituationType("KNOWN_BENIGN", "Known Benign", "...", "#10B981"),
        DomainSituationType("ESCALATION_REQUIRED", "Escalation Required", "...", "#EF4444"),
        DomainSituationType("POLICY_VIOLATION", "Policy Violation", "...", "#8B5CF6"),
    ]
    
    asymmetry_ratio = 20.0
    
    # ... methods delegate to existing logic in services/
```

### 3.5 Unified State Manager

Fixes the A1 finding (incomplete reset) while enabling multi-domain state:

```python
# backend/app/core/state_manager.py

class DemoStateManager:
    """Unified state management for all in-memory demo state."""
    
    _stores: Dict[str, Any] = {}  # name -> state object
    _reset_handlers: List[Callable] = []
    
    def register(self, name: str, initial_state: Any, reset_handler: Callable):
        """Each service registers its state at startup."""
        self._stores[name] = initial_state
        self._reset_handlers.append(reset_handler)
    
    def reset_all(self):
        """Single call resets ALL registered state. No more missed stores."""
        for handler in self._reset_handlers:
            handler()
        print(f"[STATE] Reset {len(self._reset_handlers)} state stores")

# Global instance
state_manager = DemoStateManager()
```

Each service registers at import time:
```python
# In audit.py:
from app.core.state_manager import state_manager

_DECISIONS = []
state_manager.register("audit", _DECISIONS, lambda: _DECISIONS.clear())
```

### 3.6 Refactoring Sequence (Claude Code Prompts)

The refactoring must be done in a specific order to avoid breaking the demo mid-refactor. Each prompt produces working code.

**Phase 1: Backend Core Extraction (5 prompts)**

| Prompt | What | Files Touched | Acceptance Test |
|---|---|---|---|
| R1 | Create core/ directory + state_manager.py + domain_registry.py | New: 3 files. Modify: main.py | Backend starts. State manager has 0 stores. |
| R2 | Create domains/base.py + domains/soc/config.py (populate from existing) | New: 3 files | `from app.domains.soc.config import SOCDomainConfig` works |
| R3 | Extract scoring into core/scoring.py; refactor agent.py to use domain config | New: 1 file. Modify: agent.py, evolution.py router | Tab 2: Process Alert works identically |
| R4 | Extract situation classification into core; refactor situation.py to delegate to domain | Modify: situation.py → core/situation.py wrapper. New: domains/soc/situations.py | Tab 3: Situation Analyzer works identically |
| R5 | Wire state_manager into audit.py, evolver.py, feedback.py, policy.py, triage.py. Wire reset endpoints. | Modify: 5 service files + 2 router files | Reset clears ALL state (fixes H-1, H-3). Tab 3→Tab 4 flow works. |

**Phase 2: Backend Services Cleanup (4 prompts)**

| Prompt | What | Files Touched | Acceptance Test |
|---|---|---|---|
| R6 | Extract factor computation into domains/soc/factors.py; refactor triage.py | New: 1 file. Modify: triage.py, services/triage.py | Tab 3: Decision Explainer shows correct 6 factors |
| R7 | Extract policies into domains/soc/policies.py; refactor policy.py to core/policy_engine.py | New: 1 file. Move: policy.py → core/. Modify: router | Tab 3: Policy conflict works identically |
| R8 | Extract narratives into domains/soc/narratives.py; refactor reasoning.py | New: 1 file. Modify: reasoning.py | Tab 2/3: LLM narration works (or fallback works) |
| R9 | Fix code review findings: .dict()→.model_dump(), dead code, version label, missing analysis clear | Modify: schemas.py, soc.py, metrics.py, feedback.py, triage.py router, App.tsx | No deprecation warnings. Version shows v3.2. Reset clears analysis (fixes H-2). |

**Phase 3: Frontend Parameterization (3 prompts)**

| Prompt | What | Files Touched | Acceptance Test |
|---|---|---|---|
| R10 | Create lib/domain.ts (frontend domain config). Parameterize App.tsx header + tab names. | New: 1 file. Modify: App.tsx | Header shows "SOC Copilot v3.2". Tab names use domain config. |
| R11 | Parameterize AlertTriageTab → DecisionTab: factor labels, action labels, situation types from domain config | Rename + modify: 1 file | Tab 3 works identically with labels from config |
| R12 | Parameterize RuntimeEvolutionTab + CompoundingTab: metric labels, business impact numbers from domain config | Modify: 2 files | Tab 2 + Tab 4 work identically with labels from config |

**Total: 12 prompts, estimated 3-4 sessions.**

### 3.7 What v3.2 Does NOT Do

- Does NOT build the S2P domain module (that's a future task)
- Does NOT add UCL Connectors (that's v4)
- Does NOT add Docker (that's v4)
- Does NOT change API endpoints or URL paths (frontend backward compatibility)
- Does NOT change Neo4j schema or seed data
- Does NOT touch the experiments repo

### 3.8 Verification: The "Second Domain Smoke Test"

After v3.2 is complete, we verify the refactoring by creating a minimal stub:

```python
# backend/app/domains/supply_chain/__init__.py (test only — not shipped)

class S2PDomainConfig(DomainConfig):
    name = "supply_chain"
    display_name = "Procurement Copilot"
    trigger_entity = "PurchaseOrder"
    factors = [...]  # 6 S2P factors from Section 1.5
    actions = [...]  # 4 S2P actions from Section 1.6
    # ... minimal implementation
```

If we can swap `ACTIVE_DOMAIN = "supply_chain"` in domain_registry.py and the backend starts without errors (even if the demo shows empty data because there's no seed data), the refactoring is complete. If it crashes — we missed something.

---

## SECTION 4: How This Feeds Into v4.0

### 4.1 v4.0 Phase 0 Is Gone

With v3.2 handling the refactoring, v4.0 no longer needs a "Phase 0." The v4 design document's 20 prompts across 8 sessions can proceed as written, with these adjustments:

| v4 Prompt | Original Target | v3.2 Impact |
|---|---|---|
| C1 (UCL Connector base class) | New directory + base class | Builds on core/ directory. Connector interface extends DomainConfig's source pattern. |
| C3 (Refactor Pulsedive) | Wrap threat_intel.py in connector | threat_intel.py is already cleaner; domains/soc/connectors.py is ready. |
| C5 (CrowdStrike mock) | New connector | Straightforward — implements UCLConnector interface. |
| D1-D5 (Docker) | No change | Unchanged — works on v3.2 directory structure. |
| LG1-LG4 (Live Graph) | Move in-memory to Neo4j | state_manager.py provides the inventory of what needs migration. Much cleaner. |

### 4.2 Updated Version Roadmap

| Version | Theme | ACCP | Status |
|---|---|---|---|
| v1.0 | Context graph | 1/21 | ✅ Done |
| v2.0 | Two loops + eval gates | 7/21 | ✅ Done |
| v2.5 | Interactivity + governance | 10/21 | ✅ Done |
| v3.0 | Three loops. Auditable. Connected. Transparent. | 14/21 | ✅ Done |
| v3.1.1 | Tab 1 + cross-context + customer feedback | 14/21 | ✅ Done |
| **v3.2** | **Refactoring: domain-agnostic core + SOC module** | **14/21** | **BUILD** |
| v4.0 | Your tools, our decisions. (UCL Connectors + Docker + Live Graph) | 18/21 | Design ready |
| v4.5 | S2P domain module (procurement copilot) | 18/21 + S2P | Future |
| v5.0 | Platform thesis (Control Tower + cross-graph attention) | 21/21 | Vision |

### 4.3 The Refactoring-to-v4 Bridge

v3.2's core/ directory is designed to be the foundation that v4 builds on:

- **core/scoring.py** → v4 doesn't touch it; just works with richer graph data
- **core/state_manager.py** → v4's Live Graph phase (LG1-LG4) replaces in-memory stores with Neo4j reads, registered through the same state_manager
- **domains/soc/connectors.py** → v4's UCL Connector pattern extends this to multi-source
- **core/domain_registry.py** → v4.5 registers the S2P domain alongside SOC

---

## SECTION 5: Claude Code Session Openers

### Session Opener: v3.2 Phase 1 (Core Extraction)

```
This is a continuing thread for the SOC Copilot demo.
Status: v3.1.1 complete and tagged. ACCP progress: 14/21.
Repository: gen-ai-roi-demo-v3
Ports: 8000 (backend) / 5173 (frontend)

RULES:
1. No git commands. No debugger. Read before write.
2. Do not start dev servers.
3. Add, don't rewrite. Show before/after.
4. This is a REFACTORING — the demo must work identically after each prompt.

CONTEXT: We're doing v3.2 — extracting a domain-agnostic core from the SOC-specific code.
Goal: same demo behavior, cleaner architecture, ready for a second domain.

TASK: Prompt R1 — Create core/ directory structure.
1. Read: backend/app/main.py, backend/app/services/audit.py, backend/app/services/evolver.py, backend/app/services/feedback.py
2. Create: backend/app/core/__init__.py
3. Create: backend/app/core/state_manager.py — DemoStateManager class with register() and reset_all()
4. Create: backend/app/core/domain_registry.py — stores active domain name, returns domain config
5. Modify: backend/app/main.py — import state_manager at startup

Do NOT modify any service files yet — that's R5.
Show the exact files created and lines changed.
```

### Session Opener: v3.2 Phase 2 (Services Cleanup)

```
This is a continuing thread for the SOC Copilot demo.
Status: v3.2 Phase 1 complete (core/ directory + domains/soc/ structure).
Repository: gen-ai-roi-demo-v3

RULES:
1. No git commands. No debugger. Read before write.
2. Do not start dev servers.
3. Add, don't rewrite. Show before/after.
4. This is a REFACTORING — demo must work identically.

TASK: [Prompt R6/R7/R8/R9 as applicable]
```

---

## SECTION 6: Risk and Open Questions

| Question | Impact | When to Resolve |
|---|---|---|
| Does the refactoring break any of the 20 TypeScript errors that already exist? | Low | Test after R10-R12 |
| How does frontend get domain config — API call or build-time injection? | Architecture | Decide during R10. Recommendation: simple import from lib/domain.ts |
| Should the DomainConfig interface use pydantic models or dataclasses? | Code style | Decide during R2. Recommendation: dataclasses (lighter, no validation needed for config) |
| Will the file renames (AlertTriageTab → DecisionTab) break anything? | Build risk | Likely fine — Vite handles it. But test. |
| Is 12 prompts realistic for 3-4 sessions? | Schedule | Yes, if each prompt is focused. The v3.0 build was 12 prompts in 5 sessions with MORE complexity. |
| S2P asymmetry ratio — should it be fixed or parameterized per material category? | Domain design | Resolve when building S2P module. For now, DomainConfig.asymmetry_ratio is a single float. |

---

## Appendix A: The Mapping Table (SOC ↔ S2P ↔ Framework)

This is the master reference for how concepts map across domains. The "Framework" column is what goes into core/.

| Concept | SOC | S2P | Framework Abstraction |
|---|---|---|---|
| Trigger entity | Alert | PurchaseOrder | `domain.trigger_entity` |
| Trigger action | "Alert fires" | "PO submitted" | Event type string |
| Factor 1 | travel_match | price_variance | `domain.factors[0]` |
| Factor 2 | asset_criticality | demand_urgency | `domain.factors[1]` |
| Factor 3 | VIP_status | supplier_reliability | `domain.factors[2]` |
| Factor 4 | time_anomaly | geopolitical_risk | `domain.factors[3]` |
| Factor 5 | device_trust | alternative_availability | `domain.factors[4]` |
| Factor 6 | pattern_history | spend_pattern_history | `domain.factors[5]` |
| Action 1 (safe) | false_positive_close | auto_approve_po | `domain.actions[0]` |
| Action 2 (wait) | enrich_and_wait | flag_for_review | `domain.actions[1]` |
| Action 3 (escalate) | escalate_tier2 | trigger_dual_sourcing | `domain.actions[2]` |
| Action 4 (critical) | escalate_incident | escalate_to_procurement_lead | `domain.actions[3]` |
| Situation types | 6 SOC types | 6 S2P types | `domain.situation_types` (list) |
| Asymmetry ratio | 20:1 | 10:1 to 15:1 | `domain.asymmetry_ratio` (float) |
| Policy conflict | SOC-003 vs SEC-007 | PROC-001 vs RISK-003 | `domain.policies` (list) + core/policy_engine |
| External sources | Pulsedive, GreyNoise | D&B, commodity feeds | UCL Connector pattern (v4) |
| TRIGGERED_EVOLUTION | Same | Same | core/evolution.py |
| Evidence Ledger | Same | Same | core/audit_engine.py |
| Scoring equation | Eq. 4 (identical) | Eq. 4 (identical) | core/scoring.py |
| Weight update | Eq. 4b (identical) | Eq. 4b (identical) | core/evolution.py |
| Graph attention | Eq. 6 (identical) | Eq. 6 (identical) | Future: core/discovery.py |

---

*SOC Copilot Demo — v3.2 Refactoring Design + S2P Domain Model v1 | February 25, 2026*
*Status: Design document. 12 refactoring prompts. 3-4 sessions. Zero new features. Same demo, clean architecture.*
*Validation: If a stub S2P domain module can register without touching core/, the refactoring is complete.*
