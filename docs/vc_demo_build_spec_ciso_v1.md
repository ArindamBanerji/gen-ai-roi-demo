# SOC Copilot Demo: VC Demo Build Specification v1

**Design Principle:** Balance immediate SOC value (sellable today) with the compounding moat (VC story). **Tab 2 (Runtime Evolution) is THE key differentiator.**

**Domain:** Security Operations Center (SOC) — AI-powered alert triage and response

**Architecture Note:** This is the Invoice Exception demo with a cybersecurity domain veneer. ~80% of the codebase is identical. The architecture (two-loop compounding, TRIGGERED_EVOLUTION, eval gates) is domain-agnostic.

**Key Decisions:**
- Simplified agent architecture — rule-based decision engine with LLM narration (~200 lines total)
- Schema compatible with Neo4j's context-graph-demo patterns (CAUSED, PRECEDENT_FOR relationships)
- NVL recommended for graph visualization
- The demo proves the ARCHITECTURE, not agent sophistication

---

## Executive Summary

### The Two Stories This Demo Tells

| Story | Audience | Demo Focus | Key Tabs |
|-------|----------|------------|----------|
| **"SOC Efficiency"** | CISOs / Security Leaders | Alert triage + Governance | Tab 1 (SOC Analytics) |
| **"Compounding Moat"** | VCs | Runtime Evolution + Two Loops | Tabs 2-4 |

### Tab Energy Allocation

| Tab | Name | Energy | Duration (15-min) | Why |
|-----|------|--------|-------------------|-----|
| 1 | SOC Analytics | **20%** | 2-3 min | Immediate value — governed security metrics |
| 2 | Runtime Evolution | **35%** | 4-5 min | **THE DIFFERENTIATOR** — what SIEMs don't show |
| 3 | Alert Triage | 30% | 3-4 min | Shows closed-loop execution beyond "detect" |
| 4 | Compounding | 15% | 2 min | Two-loop visual is the hero |

### The SIEM Contrast

| What Traditional SIEMs Show | What We Show (Our Addition) |
|-----------------------------|----------------------------|
| Alerts accumulate in queue | Alerts accumulate **AND feed runtime evolution** |
| Detection rules fire | Detection rules fire **AND agent self-tunes** |
| Decisions are logged | Decisions **trigger pattern learning** |
| One loop: Alert → Detect → Log → Manual Tuning | **Two loops:** Alert → Decide → Graph → Better Triage AND Better Agent |

**Soundbite:** "Your SIEM gets better detection rules. Our SOC Copilot gets **smarter**."

### Technology Stack

```yaml
data:
  analytics: BigQuery          # SOC metrics, SLAs, detection rule performance
  operational: Firestore       # Alerts, decisions, deployments, real-time state
  semantic: Neo4j Aura         # Security graph, patterns, decision traces

ai:
  reasoning: Gemini 1.5 Pro    # Via Vertex AI — NARRATION ONLY (not decision-making)
  agent: Rule-based engine     # Simple if/else logic — predictable, auditable, demo-reliable

frontend:
  framework: React 18 + TypeScript
  styling: Tailwind CSS
  components: shadcn/ui
  charts: Recharts
  graph_viz: NVL (preferred) or React Force Graph
  state: useState only         # No Redux/Zustand — minimal complexity

backend:
  framework: FastAPI (Python 3.11+)
  validation: Pydantic v2
  agent: ~200 lines total      # agent.py + reasoning.py

infrastructure:
  compute: GCP Cloud Run
  region: us-central1
```

---

## Part 1: Agent Architecture

### Core Insight

**The demo proves the ARCHITECTURE, not agent sophistication.**

The value proposition lives in:
- The graph schema (TRIGGERED_EVOLUTION)
- The two-loop data flow
- The closed-loop verification
- The visual representation

The agent itself is **intentionally simple** because:
1. **Demo reliability** — Rule-based = same decision every time
2. **Auditability** — CISOs need to explain decisions to auditors
3. **Faster build** — ~200 lines vs ~1000+ lines
4. **Clear separation** — Architecture proves the thesis, not AI magic

### The Simple Agent (2 Files, ~200 Lines)

```
backend/app/services/
├── agent.py       # ~150 lines — Decision engine + trace writer
└── reasoning.py   # ~50 lines  — LLM prompt templates for narration
```

### Decision Logic: 4 Primary Rules

```python
# agent.py — The entire decision engine

from dataclasses import dataclass
from typing import Optional
from enum import Enum

class Action(Enum):
    FALSE_POSITIVE_CLOSE = "false_positive_close"
    AUTO_REMEDIATE = "auto_remediate"
    ENRICH_AND_WAIT = "enrich_and_wait"
    ESCALATE_TIER2 = "escalate_tier2"
    ESCALATE_INCIDENT = "escalate_incident"

@dataclass
class Decision:
    action: Action
    confidence: float
    pattern_id: Optional[str]
    reasoning_context: dict

def decide(alert: Alert, context: SecurityContext) -> Decision:
    """
    Rule-based decision logic. Intentionally simple.
    The demo proves architecture, not agent sophistication.
    """
    
    # ═══════════════════════════════════════════════════════════════════════
    # RULE 1: Anomalous Login
    # ═══════════════════════════════════════════════════════════════════════
    if alert.alert_type == "anomalous_login":
        # Check travel context first
        if context.user_traveling and context.vpn_matches_location:
            if context.mfa_completed and context.device_fingerprint_match:
                return Decision(
                    action=Action.FALSE_POSITIVE_CLOSE,
                    confidence=0.92,
                    pattern_id="PAT-TRAVEL-001",
                    reasoning_context={
                        "template": "travel_false_positive",
                        "travel_dest": context.travel_destination,
                        "vpn_provider": context.vpn_provider
                    }
                )
        # High-value target without travel context
        if context.user_risk_score > 0.8:
            return Decision(
                action=Action.ESCALATE_INCIDENT,
                confidence=0.95,
                pattern_id=None,
                reasoning_context={
                    "template": "high_value_target",
                    "risk_score": context.user_risk_score,
                    "user_title": context.user_title
                }
            )
        # Default for anomalous login
        return Decision(
            action=Action.ESCALATE_TIER2,
            confidence=0.78,
            pattern_id=None,
            reasoning_context={"template": "default_escalate"}
        )
    
    # ═══════════════════════════════════════════════════════════════════════
    # RULE 2: Phishing
    # ═══════════════════════════════════════════════════════════════════════
    elif alert.alert_type == "phishing":
        if context.known_campaign_signature:
            return Decision(
                action=Action.AUTO_REMEDIATE,
                confidence=0.94,
                pattern_id="PAT-PHISH-KNOWN",
                reasoning_context={
                    "template": "known_phishing",
                    "campaign_id": context.campaign_id,
                    "auto_action": "quarantine_email"
                }
            )
        return Decision(
            action=Action.ESCALATE_TIER2,
            confidence=0.85,
            pattern_id=None,
            reasoning_context={"template": "unknown_phishing"}
        )
    
    # ═══════════════════════════════════════════════════════════════════════
    # RULE 3: Malware Detection
    # ═══════════════════════════════════════════════════════════════════════
    elif alert.alert_type == "malware_detection":
        if context.asset_criticality == "critical":
            return Decision(
                action=Action.ESCALATE_INCIDENT,
                confidence=0.96,
                pattern_id=None,
                reasoning_context={
                    "template": "critical_malware",
                    "asset_criticality": "critical"
                }
            )
        return Decision(
            action=Action.AUTO_REMEDIATE,
            confidence=0.89,
            pattern_id="PAT-MALWARE-ISOLATE",
            reasoning_context={
                "template": "standard_malware",
                "auto_action": "isolate_endpoint"
            }
        )
    
    # ═══════════════════════════════════════════════════════════════════════
    # RULE 4: Data Exfiltration (DLP)
    # ═══════════════════════════════════════════════════════════════════════
    elif alert.alert_type == "data_exfiltration":
        # DLP alerts always escalate — too risky to auto-close
        return Decision(
            action=Action.ESCALATE_INCIDENT,
            confidence=0.97,
            pattern_id=None,
            reasoning_context={
                "template": "data_exfil",
                "classification": alert.dlp_classification
            }
        )
    
    # ═══════════════════════════════════════════════════════════════════════
    # DEFAULT: Unknown alert type
    # ═══════════════════════════════════════════════════════════════════════
    return Decision(
        action=Action.ESCALATE_TIER2,
        confidence=0.60,
        pattern_id=None,
        reasoning_context={"template": "unknown_type"}
    )
```

### LLM Role: Narration Only

```python
# reasoning.py — LLM generates impressive-sounding justification

TEMPLATES = {
    "travel_false_positive": """
        Write a 2-sentence SOC analyst justification for closing this alert as false positive.
        
        Alert: Anomalous login from {location}
        User: {user_name} ({user_title})
        Context: Active travel to {travel_destination}, VPN from {vpn_provider}, MFA completed
        Pattern: PAT-TRAVEL-001 ({pattern_count} similar cases, {fp_rate}% FP rate)
        
        Be specific. Reference the travel context. Sound authoritative.
    """,
    
    "high_value_target": """
        Write a 2-sentence SOC analyst justification for escalating this alert to IR.
        
        Alert: Anomalous login on {asset_hostname}
        User: {user_name} — HIGH VALUE TARGET (risk score: {risk_score})
        Context: No travel record, unusual location/time
        
        Be direct. Explain urgency. Sound authoritative.
    """,
    
    "known_phishing": """
        Write a 2-sentence SOC analyst justification for auto-quarantining this email.
        
        Alert: Phishing email detected
        Campaign: {campaign_id} (known campaign)
        Action: {auto_action}
        
        Reference the known campaign. Confirm automated action.
    """,
    
    "critical_malware": """
        Write a 2-sentence SOC analyst justification for immediate IR escalation.
        
        Alert: Malware detected on {asset_hostname}
        Asset criticality: CRITICAL
        Impact: Potential production system compromise
        
        Be urgent. Reference critical asset status.
    """,
    
    "data_exfil": """
        Write a 2-sentence SOC analyst justification for IR escalation.
        
        Alert: Potential data exfiltration
        Data classification: {classification}
        Volume: {volume_mb} MB
        
        Emphasize data protection. Always escalate DLP alerts.
    """
}

async def generate_reasoning(alert: Alert, decision: Decision, context: SecurityContext) -> str:
    """
    LLM makes the rule-based decision sound like expert security analysis.
    This is 'intelligence theater' — the decision was already made.
    """
    
    template_key = decision.reasoning_context.get("template", "default")
    template = TEMPLATES.get(template_key, TEMPLATES["default"])
    
    prompt = template.format(
        **decision.reasoning_context,
        location=alert.source_location,
        user_name=context.user_name,
        user_title=context.user_title,
        asset_hostname=alert.asset_hostname,
        pattern_count=context.pattern_count if context.pattern else 0,
        fp_rate=context.pattern_fp_rate if context.pattern else 0
    )
    
    return await gemini.generate(prompt, max_tokens=150)
```

### Process Flow

```python
# agent.py — Main process function

async def process_alert(alert_id: str) -> ProcessResult:
    """
    The complete agent flow. Simple, testable, reliable.
    """
    
    # 1. Load alert and context from graph
    alert = await firestore.get_alert(alert_id)
    context = await neo4j.get_security_context(alert)
    
    # 2. Make decision (rule-based, deterministic)
    decision = decide(alert, context)
    
    # 3. Run eval gate (deterministic checks)
    eval_result = run_eval_gate(decision, context)
    if not eval_result.passed:
        return ProcessResult(blocked=True, reason=eval_result.failure_reason)
    
    # 4. Generate reasoning (LLM narration)
    reasoning = await generate_reasoning(alert, decision, context)
    
    # 5. Write decision trace to Neo4j
    trace_id = await write_decision_trace(alert, decision, context, reasoning)
    
    # 6. Maybe trigger evolution (deterministic rule)
    evolution = await maybe_trigger_evolution(decision, context)
    
    # 7. Execute action in target system
    receipt = await execute_action(decision, alert)
    
    return ProcessResult(
        decision=decision,
        trace_id=trace_id,
        evolution=evolution,
        receipt=receipt
    )
```

### Eval Gate (Deterministic)

```python
def run_eval_gate(decision: Decision, context: SecurityContext) -> EvalResult:
    """
    4 deterministic checks. No LLM involved.
    """
    checks = []
    
    # Check 1: Faithfulness — decision matches context
    faithfulness = 0.92 if decision.pattern_id else 0.85
    checks.append(EvalCheck("faithfulness", faithfulness, 0.85))
    
    # Check 2: Safe Action — no dangerous auto-actions
    safe_action = 1.0 if decision.action not in [Action.AUTO_REMEDIATE] or context.asset_criticality != "critical" else 0.0
    checks.append(EvalCheck("safe_action", safe_action, 1.0))
    
    # Check 3: Playbook Match — action aligns with playbook
    playbook_match = 0.94 if context.playbook_allows(decision.action) else 0.70
    checks.append(EvalCheck("playbook_match", playbook_match, 0.80))
    
    # Check 4: SLA Compliance — within response time
    sla_compliance = 0.98 if context.within_sla() else 0.75
    checks.append(EvalCheck("sla_compliance", sla_compliance, 0.90))
    
    passed = all(c.score >= c.threshold for c in checks)
    return EvalResult(checks=checks, passed=passed)
```

### Evolution Trigger (Deterministic)

```python
async def maybe_trigger_evolution(decision: Decision, context: SecurityContext) -> Optional[EvolutionEvent]:
    """
    Fires on pattern occurrence count crossing thresholds.
    Ensures TRIGGERED_EVOLUTION is visible in demo.
    """
    
    if decision.pattern_id is None:
        return None
    
    pattern = await get_pattern(decision.pattern_id)
    new_count = pattern.occurrence_count + 1
    
    # Fire at specific counts for demo predictability
    if new_count % 25 == 0 or new_count == 5:
        new_confidence = min(0.99, pattern.confidence + 0.02)
        
        evolution = EvolutionEvent(
            id=f"EVO-{generate_id()}",
            event_type="pattern_confidence",
            before_state={"confidence": pattern.confidence, "count": pattern.occurrence_count},
            after_state={"confidence": new_confidence, "count": new_count},
            description=f"Pattern {pattern.id} confidence increased"
        )
        
        await neo4j.run("""
            MATCH (d:Decision {id: $decision_id})
            CREATE (evo:EvolutionEvent $props)
            CREATE (d)-[:TRIGGERED_EVOLUTION {
                impact: 'pattern_confidence_increase',
                magnitude: 0.02,
                timestamp: datetime()
            }]->(evo)
            
            MATCH (p:AttackPattern {id: $pattern_id})
            SET p.confidence = $new_confidence, p.occurrence_count = $new_count
        """, decision_id=decision.id, props=evolution.to_dict(),
            pattern_id=pattern.id, new_confidence=new_confidence, new_count=new_count)
        
        return evolution
    
    return None
```

### Context Retrieval (Fixed Cypher Query)

```cypher
// neo4j.get_security_context() — Always returns predictable structure
MATCH (alert:Alert {id: $alert_id})-[:DETECTED_ON]->(asset:Asset)
MATCH (alert)-[:INVOLVES]->(user:User)
OPTIONAL MATCH (user)-[:HAS_TRAVEL]->(travel:TravelContext)
  WHERE travel.start_date <= date() AND travel.end_date >= date()
OPTIONAL MATCH (alert)-[:CLASSIFIED_AS]->(atype:AlertType)-[:HANDLED_BY]->(playbook:Playbook)
OPTIONAL MATCH (asset)-[:SUBJECT_TO]->(sla:SLA)
OPTIONAL MATCH (alert)-[:MATCHES]->(pattern:AttackPattern)
OPTIONAL MATCH (prev:Decision)-[:FOR_ALERT]->(:Alert)-[:CLASSIFIED_AS]->(atype)
  WHERE prev.timestamp > datetime() - duration('P30D')
RETURN alert, asset, user, travel, atype, playbook, sla, pattern,
       count(prev) as precedent_count,
       collect(prev)[0..5] as recent_precedents
```

### Why This Works

| Demo Requirement | How Simple Agent Delivers |
|------------------|---------------------------|
| "47 nodes consulted" | Fixed Cypher returns predictable count |
| Graph animation | Real Neo4j queries, NVL visualizes results |
| Decision reasoning | LLM generates justification after decision |
| TRIGGERED_EVOLUTION | Deterministic rule ensures it fires |
| Predictable demo | Same input → same decision every time |
| Audit trail | CISOs can inspect rule logic |

### Complexity Comparison

| Aspect | Original Design | Simplified Design |
|--------|-----------------|-------------------|
| Backend services | 6 (router, analyzer, orchestrator, etc.) | 2 (agent.py, reasoning.py) |
| Lines of code | ~1,200 | ~200 |
| LLM calls per decision | 3-4 | 1 (narration only) |
| Decision reliability | Variable | 100% deterministic |
| Build time | 4 weeks | 2 weeks |
| Test complexity | High (LLM mocking) | Low (pure functions) |

---

## Part 2: Application Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SOC COPILOT DEMO                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │   TAB 1     │ │   TAB 2     │ │   TAB 3     │ │   TAB 4     │           │
│  │SOC Analytics│ │  Runtime    │ │   Alert     │ │ Compounding │           │
│  │             │ │  Evolution  │ │   Triage    │ │  Dashboard  │           │
│  │ ─────────── │ │ ─────────── │ │ ─────────── │ │ ─────────── │           │
│  │ IMMEDIATE   │ │ ★ THE KEY   │ │ MOAT IN     │ │ MOAT        │           │
│  │ VALUE       │ │ DIFFERENTIA-│ │ ACTION      │ │ GROWING     │           │
│  │ (20%)       │ │ TOR (35%)   │ │ (30%)       │ │ (15%)       │           │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘           │
│         │               │               │               │                   │
│         └───────────────┴───────┬───────┴───────────────┘                   │
│                                 │                                           │
│                    ┌────────────┴────────────┐                             │
│                    │  SIMPLE AGENT LAYER     │                             │
│                    │  agent.py + reasoning.py│                             │
│                    │  (~200 lines total)     │                             │
│                    └────────────┬────────────┘                             │
│                                 │                                           │
│         ┌───────────────────────┼───────────────────────┐                  │
│         ▼                       ▼                       ▼                  │
│   ┌───────────┐          ┌───────────┐          ┌───────────┐             │
│   │ BigQuery  │          │ Firestore │          │  Neo4j    │             │
│   │ • Metrics │          │ • Alerts  │          │ • Assets  │             │
│   │ • SLAs    │          │ • Receipts│          │ • Users   │             │
│   │ • Rules   │          │ • Deploy  │          │ • Patterns│             │
│   │           │          │           │          │ • Traces  │             │
│   └───────────┘          └───────────┘          └───────────┘             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### The Two-Loop Architecture (The VC Story)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     DUAL INPUT STREAMS                                      │
│                                                                             │
│   ┌─────────────────────┐              ┌─────────────────────┐             │
│   │  Security Context   │              │   SOC Operations    │             │
│   │   (Structure)       │              │   (Runtime)         │             │
│   │                     │              │                     │             │
│   │ • Asset inventory   │              │ • Triage decisions  │             │
│   │ • User directory    │              │ • Pattern matches   │             │
│   │ • Playbooks/SLAs    │              │ • Analyst feedback  │             │
│   │ • MITRE mappings    │              │ • Outcome tracking  │             │
│   └──────────┬──────────┘              └──────────┬──────────┘             │
│              │                                    │                         │
│              └────────────────┬───────────────────┘                         │
│                               ▼                                             │
│                ┌─────────────────────────────────┐                         │
│                │       SECURITY GRAPH            │                         │
│                │          (Neo4j)                │                         │
│                │                                 │                         │
│                │  (:Decision)-[:TRIGGERED_EVOLUTION]->(:EvolutionEvent)   │
│                │              ↑                                            │
│                │     THE KEY RELATIONSHIP                                  │
│                │     (What SIEMs don't have)                               │
│                └─────────────────────────────────┘                         │
│                               │                                             │
│              ┌────────────────┴────────────────┐                           │
│              ▼                                 ▼                           │
│   ┌─────────────────────┐         ┌─────────────────────┐                 │
│   │   Alert Triage      │         │   Runtime Evolution │                 │
│   │     (Loop 1)        │         │     (Loop 2)        │                 │
│   │                     │         │                     │                 │
│   │ • Better context    │         │ • Better agent      │                 │
│   │ • Better precedents │         │ • Self-tuning       │                 │
│   │ • SIEM has this ✓   │         │ • SIEM LACKS ✗      │                 │
│   └──────────┬──────────┘         └──────────┬──────────┘                 │
│              │                                │                            │
│              └────────────────┬───────────────┘                            │
│                               │ FEEDBACK                                   │
│                               ▼                                            │
│                ┌─────────────────────────┐                                 │
│                │   Back to Graph         │                                 │
│                │   (COMPOUNDING)         │                                 │
│                └─────────────────────────┘                                 │
│                                                                             │
│   "Splunk gets better rules. Our copilot becomes a better copilot."        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Part 3: Tab Specifications

### Tab 1: SOC Analytics — "Governed Security Metrics"

**Purpose:** Prove immediate value — governed security metrics with provenance.
**Energy:** 20%

**CISO Pitch:**
> "Your SOC spends hours building dashboards that answer the same questions. Watch this: 'What was our MTTR last week?' Instant answer — with provenance showing exactly where the data came from."

#### UI Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  SOC ANALYTICS — "Ask Anything About Your Security Posture"                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Ask a security question:                                             │   │
│  │ ┌─────────────────────────────────────────────────────────────────┐ │   │
│  │ │ What was MTTR last week by alert severity?                  [⏎] │ │   │
│  │ └─────────────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌──────────────────────────────┬──────────────────────────────────────┐   │
│  │         ANSWER               │       GOVERNANCE                     │   │
│  ├──────────────────────────────┼──────────────────────────────────────┤   │
│  │                              │                                      │   │
│  │  Matched: mttr_by_severity   │  📋 METRIC CONTRACT                  │   │
│  │  Confidence: 96%             │  ├─ Name: MTTR by Severity (v2)     │   │
│  │                              │  ├─ Owner: soc_analytics@...        │   │
│  │  ┌────────────────────────┐  │  └─ Status: Active ✓                │   │
│  │  │   [BAR CHART]          │  │                                      │   │
│  │  │   Critical: 8.2 min    │  │  📊 PROVENANCE                       │   │
│  │  │   High:     14.7 min   │  │  ├─ Sources: Splunk, ServiceNow    │   │
│  │  │   Medium:   45.3 min   │  │  ├─ Freshness: 1h ago ✓             │   │
│  │  │   Low:      4.2 hours  │  │  └─ [View Query]                    │   │
│  │  └────────────────────────┘  │                                      │   │
│  └──────────────────────────────┴──────────────────────────────────────┘   │
│                                                                             │
│  ⚠️ DETECTION RULE SPRAWL DETECTED                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Duplicate rule: "anomalous_login_legacy" (deprecated Dec 2025)     │   │
│  │  Still active in 3 SIEM correlation rules.                          │   │
│  │  Impact: 2,400 duplicate alerts/month. Est. analyst cost: $18K/mo   │   │
│  │  [View Details]  [Deprecate Now]                                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Components

- `SOCQueryInput` — Natural language input with example suggestions
- `MetricResult` — Bar/line chart with matched metric info
- `GovernancePanel` — Contract details, provenance, freshness indicator
- `RuleSprawlAlert` — Detection rule duplicate warning with cost impact

#### API Endpoints

```yaml
POST /api/soc/query
request:
  question: string
  
response:
  matched_metric:
    id: string
    name: string
    owner: string
    definition: string
    
  result:
    data: array of { label: string, value: number }
    chart_type: "bar" | "line" | "number"
    
  provenance:
    sources: string[]
    freshness_hours: number
    query_preview: string
    
  sprawl_alert:  # null if no sprawl detected
    duplicate_rule: string
    active_in_pipelines: number
    monthly_alert_impact: number
    estimated_cost: number
```

#### Sample Security Metrics

| Metric ID | Name | Definition |
|-----------|------|------------|
| `mttr_by_severity` | MTTR by Severity | Mean time to respond by alert severity |
| `mttd_by_source` | MTTD by Source | Mean time to detect by alert source |
| `auto_close_rate` | Auto-Close Rate | % alerts closed without human intervention |
| `fp_rate_by_rule` | FP Rate by Rule | False positive rate by detection rule |
| `escalation_rate` | Escalation Rate | % alerts escalated to IR |
| `analyst_efficiency` | Analyst Efficiency | Alerts resolved per analyst per day |

---

### Tab 2: Runtime Evolution — "The Agent Gets Smarter" ★ THE DIFFERENTIATOR

**Purpose:** Prove THE key differentiator — decisions trigger agent evolution.
**Energy:** 35%

**VC Pitch:**
> "Watch what happens when we process this alert. See the eval gate? Four checks before any action. Now watch the purple panel — TRIGGERED EVOLUTION. The pattern confidence just increased. **Your SIEM gets better rules. Our copilot gets smarter.**"

#### UI Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  SOC COPILOT EVOLUTION — "The Agent That Gets Smarter"                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ DEPLOYMENT REGISTRY                                                  │   │
│  ├──────────┬─────────┬──────────┬──────────┬───────────────────────────┤   │
│  │ Agent    │ Version │ Traffic  │ Status   │ Auto-Close Rate (7d)      │   │
│  ├──────────┼─────────┼──────────┼──────────┼───────────────────────────┤   │
│  │ soc      │ v3.1    │ ████████ │ ● active │ 73.2% (n=4,847)           │   │
│  │ copilot  │ v3.2    │ █        │ ○ canary │ 71.8% (n=253)             │   │
│  └──────────┴─────────┴──────────┴──────────┴───────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────┬───────────────────────────────────────┐   │
│  │ CANARY COMPARISON           │ EVAL GATE — ALERT-7823                │   │
│  ├─────────────────────────────┼───────────────────────────────────────┤   │
│  │                             │                                       │   │
│  │  v3.1 (Active)   v3.2 (C)   │  CHECK           SCORE   THRESH STATUS│   │
│  │  ┌──────────┐ ┌──────────┐  │  ─────────────────────────────────────│   │
│  │  │"Check    │ │"Full     │  │  Faithfulness    0.92   > 0.85  ✓ PASS│   │
│  │  │ travel   │ │ context  │  │  Safe Action     1.00   = 1.00  ✓ PASS│   │
│  │  │ first"   │ │ analysis"│  │  Playbook Match  0.94   > 0.80  ✓ PASS│   │
│  │  └──────────┘ └──────────┘  │  SLA Compliance  0.98   > 0.90  ✓ PASS│   │
│  │                             │                                       │   │
│  │  Confidence: 92%     89%    │  VERDICT: ✓ ALL GATES PASSED          │   │
│  │  Latency:    0.8s    1.2s   │  Action authorized                    │   │
│  └─────────────────────────────┴───────────────────────────────────────┘   │
│                                                                             │
│  [Process Next Alert]  [Simulate Failed Gate]                               │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ DECISION TRACE — DEC-7823                                [Export]   │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                      │   │
│  │  Input:        ALERT-7823 (anomalous_login, Singapore, 3:47 AM)     │   │
│  │  Context:      47 graph nodes from security graph                   │   │
│  │  Decision:     false_positive_close (92% confidence)                │   │
│  │  Verification: ✓ Alert status updated in SIEM                       │   │
│  │                                                                      │   │
│  │  ┌───────────────────────────────────────────────────────────────┐  │   │
│  │  │ 🔗 TRIGGERED EVOLUTION (What SIEMs don't have)                 │  │   │
│  │  │                                                                │  │   │
│  │  │ This decision trace triggered:                                 │  │   │
│  │  │ • Pattern PAT-TRAVEL-001 confidence: 91% → 94% (+3 pts)       │  │   │
│  │  │ • Auto-close threshold for travel alerts: 88% → 90%           │  │   │
│  │  │ • Evolution event: EVO-0891 created                            │  │   │
│  │  │                                                                │  │   │
│  │  │ "Splunk gets better rules. Our copilot gets SMARTER."         │  │   │
│  │  └───────────────────────────────────────────────────────────────┘  │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ BLOCKING DEMO (Optional)                                             │   │
│  │                                                                      │   │
│  │  Click "Simulate Failed Gate" to show what happens when             │   │
│  │  Safe Action check fails (e.g., auto-remediate critical asset).     │   │
│  │                                                                      │   │
│  │  VERDICT: ✗ BLOCKED — Action not authorized                         │   │
│  │  Reason: Safe Action check failed (0.0 < 1.0)                       │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Components

- `DeploymentRegistry` — Table showing active/canary versions with metrics
- `CanaryComparison` — Side-by-side prompt/config comparison
- `EvalGatePanel` — Four checks with scores, thresholds, pass/fail
- `DecisionTrace` — Full trace with TRIGGERED_EVOLUTION highlight
- `ProcessButton` — "Process Next Alert" triggers the flow
- `FailGateButton` — "Simulate Failed Gate" for demo blocking scenario

#### API Endpoints

```yaml
GET /api/deployments
response:
  deployments:
    - agent_name: string
      version: string
      status: "active" | "canary" | "inactive"
      traffic_pct: number
      auto_close_rate_7d: number
      sample_count_7d: number
      config_preview: string

POST /api/alert/process
request:
  alert_id: string
  deployment_version: string  # optional, for canary routing
  
response:
  alert_id: string
  routed_to: string  # which version handled it
  
  eval_gate:
    checks:
      - name: string
        score: number
        threshold: number
        passed: boolean
    overall_passed: boolean
    
  execution:
    status: "executed" | "blocked"
    reason: string  # if blocked
    
  decision_trace:
    id: string
    type: string
    reasoning: string
    confidence: number
    action_taken: string
    nodes_consulted: number
    
  triggered_evolution:
    occurred: boolean
    event_id: string  # if occurred
    changes:
      - type: string
        before: any
        after: any

POST /api/eval/simulate-failure
response:
  simulated_check: "safe_action"
  score: 0.0
  threshold: 1.0
  overall_passed: false
  block_reason: "Auto-remediate action not allowed on critical asset"
```

---

### Tab 3: Alert Triage — "Watch the Security Graph Think"

**Purpose:** Show the graph "thinking" + closed-loop execution.
**Energy:** 30%

**CISO Pitch:**
> "See the graph lighting up? 47 nodes consulted: user profile, travel calendar, VPN records, device fingerprint, historical patterns. This isn't just detection — it's contextual decision-making. And watch the closed loop: decision made, action taken, outcome verified, KPI attributed."

#### UI Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ALERT TRIAGE — "Watch the Security Graph Think"                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────┬─────────────────────────────────────────┐   │
│  │ ALERT QUEUE          [12] │ SECURITY CONTEXT GRAPH (NVL)            │   │
│  ├───────────────────────────┤                                         │   │
│  │                           │    ┌──────────┐      ┌──────────┐      │   │
│  │ ● ALERT-7823│Login│ Med  │    │ JSMITH   │──────│SINGAPORE │      │   │
│  │   ALERT-7822│Phish│ High │    │ (VP Fin) │      │(travel)  │      │   │
│  │   ALERT-7821│Malwr│ Crit │    └────┬─────┘      └────┬─────┘      │   │
│  │   ALERT-7820│DLP  │ High │         │                  │           │   │
│  │   ALERT-7819│Login│ Low  │    ┌────┴────┐       ┌────┴─────┐     │   │
│  │   ALERT-7818│Login│ Med  │    │LAPTOP-JS│       │HOTEL VPN │     │   │
│  │   ALERT-7817│Phish│ Med  │    │(high)   │       │(known)   │     │   │
│  │                           │    └────┬────┘       └──────────┘     │   │
│  ├───────────────────────────┤         │                              │   │
│  │                           │    ┌────┴────┐                         │   │
│  │ Selected: ALERT-7823      │    │PAT-TRAV │                         │   │
│  │ Type: Anomalous Login     │    │n=127    │                         │   │
│  │ Source: Singapore 3:47 AM │    │94% FP   │                         │   │
│  │ Asset: LAPTOP-JSMITH      │    └─────────┘                         │   │
│  │ User: John Smith (VP Fin) │                                         │   │
│  │ Risk Score: 0.85          │ [47 nodes] [5 subgraphs] [3 patterns]   │   │
│  │                           │                                         │   │
│  └───────────────────────────┴─────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ RECOMMENDATION                                      Confidence: 92% │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                      │   │
│  │ ✓ FALSE POSITIVE — AUTO-CLOSE                                       │   │
│  │                                                                      │   │
│  │ "User John Smith has active travel to Singapore (flight DL-847).   │   │
│  │  Login from hotel VPN IP matches known Marriott provider. MFA      │   │
│  │  completed successfully. Pattern PAT-TRAVEL-001 matched (127 cases,│   │
│  │  94% false positive rate)."                                         │   │
│  │                                                                      │   │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐           │   │
│  │  │AUTO-CLOSE │ │ TIER 2    │ │  ENRICH   │ │ INCIDENT  │           │   │
│  │  └───────────┘ └───────────┘ └───────────┘ └───────────┘           │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ ✓ CLOSED LOOP (What SIEMs don't do)                                 │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                      │   │
│  │  1. EXECUTED    → Alert closed in Splunk SIEM                       │   │
│  │  2. VERIFIED    → No follow-up ticket created                       │   │
│  │  3. EVIDENCE    → Decision trace DEC-7823 captured                  │   │
│  │  4. KPI IMPACT  → This resolution: MTTR ↓4.2 minutes                │   │
│  │                                                                      │   │
│  │  "A SIEM stops at detect. We close the loop."                       │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Components

- `AlertQueue` — Selectable list of pending alerts with type/severity badges
- `SecurityGraph` — NVL visualization with animation on node selection
- `AlertDetails` — Selected alert properties
- `Recommendation` — Decision with reasoning + action buttons
- `ClosedLoop` — 4-step execution panel with sequential animation

#### API Endpoints

```yaml
GET /api/alerts/queue
response:
  alerts:
    - id: string
      alert_type: string
      severity: "low" | "medium" | "high" | "critical"
      asset_hostname: string
      user_name: string
      timestamp: datetime
      status: "pending" | "resolved"

POST /api/alert/analyze
request:
  alert_id: string
  
response:
  alert: full alert object
  
  analysis:
    root_cause: string
    severity_assessment: string
    
  context:
    nodes_count: number
    subgraphs_traversed: string[]
    patterns_matched: number
    key_facts:
      - source: string
        fact: string
    
  recommendation:
    action: string
    confidence: number
    reasoning: string  # LLM-generated narration
    
  graph_data:  # For NVL visualization
    nodes: array of { id, label, type, properties }
    relationships: array of { source, target, type, properties }

POST /api/action/execute
request:
  alert_id: string
  action: string
  
response:
  receipt:
    id: string
    action: string
    timestamp: datetime
    target_system: string
    target_system_response: string
    
  verification:
    verified: boolean
    verification_method: string
    
  kpi_impact:
    metric: string
    contribution: string
```

---

### Tab 4: Compounding Dashboard — "The Moat in Motion"

**Purpose:** Prove the compounding effect. Graph growth + learning metrics + Two-Loop Visual.
**Energy:** 15%

**VC Pitch:**
> "Week 1: 23 patterns, 68% auto-close. Week 4: 127 patterns, 89% auto-close. Same model, same rules. The difference? Accumulated intelligence. **When a competitor deploys at a new customer, they start at zero. We start at 127 patterns.**"

#### The Two-Loop Visual (Hero Visual)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│        Traditional SIEM                Our SOC Copilot                      │
│        (One Loop)                      (Two Loops)                          │
│        ────────────────                ────────────────                     │
│                                                                             │
│   Alert → Detect → Log            Alert → Detect → Graph                   │
│                 │                               │                           │
│                 ▼                    ┌──────────┴──────────┐               │
│          Manual Tuning              ▼                      ▼               │
│                                  Better Triage        Better Agent         │
│                                  (Context)            (Runtime             │
│                                                        Evolution)          │
│                                       │                      │              │
│                                       └──────────┬───────────┘              │
│                                                  │                          │
│                                                  ▼                          │
│                                           COMPOUNDING                       │
│                                                                             │
│   "Their SIEM gets                    "Our copilot BECOMES                 │
│    better rules."                      a better copilot."                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### UI Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  SOC COMPOUNDING — "Watch the Moat Grow"                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ THE HEADLINE                                                         │   │
│  │                                                                      │   │
│  │        WEEK 1                             WEEK 4                     │   │
│  │     ┌─────────┐                        ┌─────────┐                   │   │
│  │     │  ○──○   │                        │ ○─○─○─○ │                   │   │
│  │     │  │  │   │      ───────────▶      │ │╲│╱│╲││                   │   │
│  │     │  ○──○   │                        │ ○─○─○─○ │                   │   │
│  │     │         │                        │ │╱│╲│╱│ │                   │   │
│  │     │ 23 nodes│                        │127 nodes│                   │   │
│  │     └─────────┘                        └─────────┘                   │   │
│  │                                                                      │   │
│  │  Auto-Close Rate:   68% → 89%           (+21 pts)                   │   │
│  │  MTTR:              12.4 min → 3.1 min  (-75%)                      │   │
│  │  FP Investigations: 4,200/wk → 980/wk   (-77%)                      │   │
│  │                                                                      │   │
│  │  Same model. Same rules. More intelligence.                         │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌──────────────────────────────┬──────────────────────────────────────┐   │
│  │ WEEKLY TREND                 │ TWO-LOOP VISUAL (Hero)               │   │
│  ├──────────────────────────────┼──────────────────────────────────────┤   │
│  │                              │                                      │   │
│  │ ┌──────────────────────────┐ │         [Two-Loop Diagram]           │   │
│  │ │       [LINE CHART]       │ │                                      │   │
│  │ │                          │ │    Traditional     Our SOC           │   │
│  │ │  Auto-Close ────         │ │    SIEM            Copilot           │   │
│  │ │  MTTR       - - -        │ │    ─────────       ─────────         │   │
│  │ │  FP Rate    ····         │ │                                      │   │
│  │ │                          │ │    Alert           Alert             │   │
│  │ │  Wk1  Wk2  Wk3  Wk4      │ │      │               │               │   │
│  │ │                          │ │      ▼               ▼               │   │
│  │ └──────────────────────────┘ │    Detect         Context           │   │
│  │                              │      │               │               │   │
│  │                              │      ▼          ┌────┴────┐         │   │
│  │                              │    Log          ▼         ▼         │   │
│  │                              │      │       Better    Better       │   │
│  │                              │      ▼       Triage    Agent        │   │
│  │                              │   (manual       │         │         │   │
│  │                              │    tuning)      └────┬────┘         │   │
│  │                              │                      ▼              │   │
│  │                              │                 COMPOUNDING         │   │
│  └──────────────────────────────┴──────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ RECENT EVOLUTION EVENTS                                              │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                      │   │
│  │  EVO-0891 │ Pattern confidence │ PAT-TRAVEL: 91% → 94%  │ 2h ago   │   │
│  │  EVO-0890 │ Auto-close thresh  │ Travel: 88% → 90%      │ 1d ago   │   │
│  │  EVO-0889 │ New pattern        │ PAT-PHISH-Q4-CAMPAIGN  │ 2d ago   │   │
│  │  EVO-0888 │ Playbook tuned     │ DLP escalation path    │ 3d ago   │   │
│  │                                                                      │   │
│  │  [Reset Demo Data]                                                   │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  "When a competitor deploys at a new customer, they start at zero.         │
│   We start at 127 patterns. That's the moat."                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Components

- `HeadlineComparison` — Week 1 vs Week 4 with graph size visual
- `WeeklyTrend` — Multi-line chart showing metric improvements
- `TwoLoopVisual` — The hero diagram (can be animated)
- `EvolutionEvents` — Recent system improvements list
- `ResetButton` — Reset demo data for repeated demos

#### API Endpoints

```yaml
GET /api/metrics/compounding?weeks=4
response:
  period:
    start: datetime
    end: datetime
    
  headline:
    nodes_start: number
    nodes_end: number
    auto_close_start: number
    auto_close_end: number
    mttr_start: number
    mttr_end: number
    fp_investigations_start: number
    fp_investigations_end: number
    
  weekly_trend:
    - week: number
      auto_close_rate: number
      mttr_minutes: number
      fp_rate: number
      pattern_count: number
      
  evolution_events:
    - id: string
      event_type: string
      description: string
      timestamp: datetime
      triggered_by: string

POST /api/demo/reset
response:
  status: "reset_complete"
  message: string
```

---

## Part 4: Neo4j Schema

### Node Types

```cypher
// ═══════════════════════════════════════════════════════════════════════════
// CORE SECURITY ENTITIES
// ═══════════════════════════════════════════════════════════════════════════

(:Asset {
    id: string,              // "LAPTOP-JSMITH", "SRV-DB-PROD-01"
    hostname: string,
    type: string,            // "endpoint", "server", "network", "cloud"
    criticality: string,     // "low", "medium", "high", "critical"
    business_unit: string,
    os: string,
    owner_id: string
})

(:User {
    id: string,              // "jsmith@company.com"
    name: string,
    department: string,
    title: string,
    risk_score: float,       // 0.0 - 1.0
    is_privileged: boolean
})

(:AlertType {
    id: string,              // "anomalous_login", "phishing", "malware"
    name: string,
    description: string,
    severity: string,
    mitre_technique: string
})

(:AttackPattern {
    id: string,              // "PAT-TRAVEL-001"
    name: string,
    description: string,
    fp_rate: float,
    occurrence_count: int,
    confidence: float
})

(:Playbook {
    id: string,
    name: string,
    description: string,
    steps: string[],
    auto_actions: string[],
    sla_minutes: int
})

(:SLA {
    id: string,
    name: string,
    response_time_minutes: int,
    severity: string
})

(:TravelContext {
    id: string,
    user_id: string,
    destination: string,
    start_date: date,
    end_date: date,
    vpn_expected: string[]
})

// ═══════════════════════════════════════════════════════════════════════════
// DECISION TRACE ENTITIES (THE KEY DIFFERENTIATOR)
// ═══════════════════════════════════════════════════════════════════════════

(:Decision {
    id: string,              // "DEC-7823"
    type: string,
    reasoning: string,
    confidence: float,
    timestamp: datetime,
    alert_id: string,
    action_taken: string
})

(:DecisionContext {
    id: string,
    decision_id: string,
    user_snapshot: string,   // JSON
    asset_snapshot: string,  // JSON
    patterns_matched: string[],
    nodes_consulted: int
})

(:EvolutionEvent {
    id: string,              // "EVO-0891"
    event_type: string,      // "pattern_confidence", "threshold_adjustment"
    triggered_by: string,
    before_state: string,    // JSON
    after_state: string,     // JSON
    description: string,
    timestamp: datetime
})
```

### Relationships

```cypher
// ═══════════════════════════════════════════════════════════════════════════
// SECURITY CONTEXT RELATIONSHIPS
// ═══════════════════════════════════════════════════════════════════════════

(:User)-[:ASSIGNED_TO]->(:Asset)
(:User)-[:HAS_TRAVEL]->(:TravelContext)
(:Asset)-[:SUBJECT_TO]->(:SLA)
(:Alert)-[:DETECTED_ON]->(:Asset)
(:Alert)-[:INVOLVES]->(:User)
(:Alert)-[:CLASSIFIED_AS]->(:AlertType)
(:AlertType)-[:HANDLED_BY]->(:Playbook)
(:Alert)-[:MATCHES]->(:AttackPattern)

// ═══════════════════════════════════════════════════════════════════════════
// DECISION TRACE RELATIONSHIPS
// ═══════════════════════════════════════════════════════════════════════════

(:Decision)-[:HAD_CONTEXT]->(:DecisionContext)
(:Decision)-[:FOR_ALERT]->(:Alert)
(:Decision)-[:APPLIED_PLAYBOOK]->(:Playbook)
(:Decision)-[:USED_PRECEDENT {similarity: float}]->(:Decision)

// Causal chain (Neo4j compatible)
(:Decision)-[:CAUSED {reason: string, timestamp: datetime}]->(:Decision)
(:Decision)-[:PRECEDENT_FOR {similarity: float, cited_in_reasoning: boolean}]->(:Decision)

// ═══════════════════════════════════════════════════════════════════════════
// THE KEY DIFFERENTIATOR
// ═══════════════════════════════════════════════════════════════════════════

(:Decision)-[:TRIGGERED_EVOLUTION {
    impact: string,
    magnitude: float,
    timestamp: datetime
}]->(:EvolutionEvent)
```

### Expected Counts (After Setup)

| Node Type | Count | Notes |
|-----------|-------|-------|
| Asset | 5 | Mix of endpoints and servers |
| User | 5 | Various risk levels |
| AlertType | 4 | anomalous_login, phishing, malware, data_exfil |
| AttackPattern | 5 | Learned patterns |
| Playbook | 4 | Response procedures |
| SLA | 3 | By severity |
| TravelContext | 2 | Active travel records |
| Alert | 5 | Sample alerts for demo |
| Decision | 5 | Sample decisions |
| DecisionContext | 5 | Context snapshots |
| EvolutionEvent | 3 | Agent improvements |
| **Total** | **~46** | Decision Trace entities are key addition |

| Relationship Type | Count | Notes |
|-------------------|-------|-------|
| ASSIGNED_TO | 5 | User → Asset |
| HAS_TRAVEL | 2 | User → TravelContext |
| SUBJECT_TO | 5 | Asset → SLA |
| DETECTED_ON | 5 | Alert → Asset |
| INVOLVES | 5 | Alert → User |
| CLASSIFIED_AS | 5 | Alert → AlertType |
| HANDLED_BY | 4 | AlertType → Playbook |
| MATCHES | 3 | Alert → AttackPattern |
| HAD_CONTEXT | 5 | Decision → DecisionContext |
| FOR_ALERT | 5 | Decision → Alert |
| TRIGGERED_EVOLUTION | 3 | **THE KEY** |
| CAUSED | 2 | Causal chain |
| PRECEDENT_FOR | 2 | Precedent chain |
| **Total** | **~51** | |

---

## Part 5: Project Structure

```
soc-copilot-demo/
├── CLAUDE.md                           # Claude Code instructions
├── README.md                           # Quick start
├── docs/
│   └── vc_demo_build_spec_ciso_v1.md   # This document
│
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx                     # Main app with tab routing
│   │   ├── components/
│   │   │   ├── tabs/
│   │   │   │   ├── SOCAnalyticsTab.tsx
│   │   │   │   ├── RuntimeEvolutionTab.tsx
│   │   │   │   ├── AlertTriageTab.tsx
│   │   │   │   └── CompoundingTab.tsx
│   │   │   ├── common/
│   │   │   │   ├── AlertQueue.tsx
│   │   │   │   ├── SecurityGraph.tsx    # NVL wrapper
│   │   │   │   ├── EvalGatePanel.tsx
│   │   │   │   └── ClosedLoop.tsx
│   │   │   └── ui/                     # shadcn components
│   │   └── lib/
│   │       └── api.ts                  # API client
│   └── tailwind.config.js
│
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py                     # FastAPI app
│   │   ├── routers/
│   │   │   ├── soc.py                  # Tab 1 endpoints
│   │   │   ├── evolution.py            # Tab 2 endpoints
│   │   │   ├── triage.py               # Tab 3 endpoints
│   │   │   └── metrics.py              # Tab 4 endpoints
│   │   ├── services/
│   │   │   ├── agent.py                # ~150 lines — Decision engine
│   │   │   └── reasoning.py            # ~50 lines — LLM narration
│   │   ├── models/
│   │   │   └── schemas.py              # Pydantic models
│   │   └── db/
│   │       ├── bigquery.py
│   │       ├── firestore.py
│   │       └── neo4j.py
│   └── tests/
│
└── infrastructure/
    ├── ciso_setup_notebook_v1.py       # Colab setup notebook
    └── .env.example
```

### Code Size Estimates

| Component | Files | Lines |
|-----------|-------|-------|
| Frontend (4 tabs + components) | ~15 | ~800 |
| Backend (agent + routers) | ~10 | ~500 |
| Total | ~25 | ~1,300 |

---

## Part 6: Build Schedule (2 Weeks)

### Week 1: Core Demo

| Day | Focus | Deliverable |
|-----|-------|-------------|
| 1 | Project setup + Tab 2 start | Skeleton with routing, agent.py stub |
| 2 | Tab 2: Runtime Evolution | Deployment registry, eval gate, TRIGGERED_EVOLUTION |
| 3 | Tab 3: Alert Triage | Alert queue, graph viz, recommendation panel |
| 4 | Tab 1: SOC Analytics | Query input, metric matching, sprawl alert |
| 5 | Tab 4: Compounding | Week comparison, trend chart, evolution list |

### Week 2: Polish + Demo Prep

| Day | Focus | Deliverable |
|-----|-------|-------------|
| 6 | Integration testing | All tabs working end-to-end |
| 7 | Animation polish | Graph animations, closed loop steps |
| 8 | Error handling | Edge cases, loading states |
| 9 | Demo rehearsal | Full 15-minute run-through |
| 10 | Buffer | Final fixes, backup prep |

### Build Verification Gates

| Gate | Day | Criteria |
|------|-----|----------|
| Tab 2 Working | 2 | Eval gate + TRIGGERED_EVOLUTION visible |
| All Tabs Basic | 5 | Can click through all 4 tabs |
| End-to-End | 6 | Full flow: alert → decision → trace → evolution |
| Demo Ready | 9 | Full rehearsal, no console errors |

### Why 2 Weeks Instead of 4?

| Simplification | Time Saved |
|----------------|------------|
| Rule-based agent (no LLM orchestration) | 3-4 days |
| Fixed Cypher queries (no dynamic generation) | 2 days |
| Deterministic eval gate (no LLM scoring) | 1-2 days |
| Simpler testing (no LLM mocking) | 2 days |

---

## Part 7: Competitive Positioning

### vs. Traditional SIEMs (Splunk, Microsoft Sentinel)

| What SIEM Shows | What We Add |
|-----------------|-------------|
| Alert detected | Alert detected **AND contextualized** |
| Rules fire | Rules fire **AND self-tune** |
| Logs accumulated | Decisions **trigger evolution** |
| Manual tuning | **Automatic pattern learning** |

### vs. SOAR (Palo Alto XSOAR, Swimlane)

| What SOAR Shows | What We Add |
|-----------------|-------------|
| Playbook execution | Playbook execution **AND feedback loop** |
| Orchestration | Orchestration **AND learning** |
| Case management | Decision traces **that compound** |

### vs. AI Security Vendors (Darktrace, Vectra)

| What AI Vendors Show | What We Add |
|----------------------|-------------|
| Anomaly detection | Anomaly detection **AND context** |
| ML-based alerting | Alerts **AND audit trail** |
| Black box decisions | **Transparent, explainable decisions** |

### The Counter-Pitch

When prospects mention competitors:

> "Splunk is great at search. CrowdStrike is great at detection. What they don't show is how your SOC gets smarter over time.
>
> Every alert your analysts investigate today? That knowledge is trapped. In their heads. In tickets nobody reads.
>
> We capture that knowledge in a graph. Every decision feeds two loops: better context AND better agent. Week 1, you're at 68% auto-close. Week 4, you're at 89%.
>
> When your current vendor comes back next year, ask them: 'Show me how my SOC learned from last year's investigations.' They can't. We can."

---

## Part 8: Success Criteria

### Must Work in Demo

| Criterion | Tab | How to Verify |
|-----------|-----|---------------|
| SOC metric query returns chart + provenance | 1 | Type "MTTR by severity" |
| Detection rule sprawl alert appears | 1 | Duplicate rule flagged |
| Canary comparison shows two versions | 2 | Side-by-side configs |
| Eval gate shows 4 checks with scores | 2 | All pass with percentages |
| TRIGGERED_EVOLUTION fires and displays | 2 | Purple panel appears with changes |
| "Simulate Failed Gate" blocks decision | 2 | Red verdict, blocked reason |
| Graph animates on alert select | 3 | Nodes highlight progressively |
| "47 nodes consulted" counter accurate | 3 | Number matches query |
| Closed loop executes 4 steps sequentially | 3 | Steps appear one by one |
| Week 1 vs Week 4 shows improvement | 4 | Numbers are clearly different |
| Evolution events list populated | 4 | Recent events with timestamps |
| Two-loop diagram renders clearly | 4 | Hero visual is prominent |

### Performance Targets

| Metric | Target |
|--------|--------|
| Tab switch latency | < 500ms |
| Alert process time | < 3 seconds |
| Graph render time | < 2 seconds |
| Page load time | < 3 seconds |
| No console errors | 0 |

---

## Appendix A: Sample Seed Data

### Sample Alerts

| ID | Type | Severity | Asset | User | Status |
|----|------|----------|-------|------|--------|
| ALERT-7823 | anomalous_login | medium | LAPTOP-JSMITH | John Smith | pending |
| ALERT-7822 | phishing | high | MAIL-GW-01 | Finance Team | pending |
| ALERT-7821 | malware_detection | critical | SRV-DB-PROD | system | pending |
| ALERT-7820 | data_exfiltration | high | LAPTOP-MCHEN | Mary Chen | pending |
| ALERT-7819 | anomalous_login | low | LAPTOP-AGARCIA | Ana Garcia | pending |

### Sample Attack Patterns

| ID | Name | FP Rate | Occurrences | Confidence |
|----|------|---------|-------------|------------|
| PAT-TRAVEL-001 | Travel login false positive | 94% | 127 | 0.92 |
| PAT-PHISH-KNOWN | Known phishing campaign | 2% | 89 | 0.96 |
| PAT-MALWARE-ISOLATE | Malware auto-isolate | 8% | 34 | 0.91 |
| PAT-VPN-KNOWN | Known VPN provider | 96% | 245 | 0.94 |
| PAT-LOGIN-NORMAL | Normal location login | 98% | 2,847 | 0.97 |

### Sample Users

| ID | Name | Title | Risk Score | Travel Status |
|----|------|-------|------------|---------------|
| jsmith@co.com | John Smith | VP Finance | 0.85 | Singapore |
| mchen@co.com | Mary Chen | Director Eng | 0.72 | Office |
| agarcia@co.com | Ana Garcia | Developer | 0.35 | Denver |
| cjohnson@co.com | Chris Johnson | CEO | 0.95 | Office |
| blee@co.com | Bob Lee | SOC Analyst | 0.25 | Office |

---

## Appendix B: Domain Mapping from Invoice Demo

| Invoice Domain | CISO Domain | Notes |
|----------------|-------------|-------|
| Invoice Exception | Security Alert | Core entity being processed |
| Vendor | Asset | Context entity |
| Contract | SLA | Agreement/policy entity |
| Policy | Playbook | Response procedure |
| Pattern | Attack Pattern | Learned behavior |
| OTIF, DPO | MTTD, MTTR | Key metrics |
| AP Analyst | SOC Analyst | User persona |
| Invoice Copilot | SOC Copilot | Agent name |
| three_way_match | anomalous_login | Primary exception/alert type |
| duplicate | phishing | Secondary type |
| missing_gr | malware_detection | Tertiary type |
| price_variance | data_exfiltration | Quaternary type |

---

*SOC Copilot Demo Build Specification v1 | January 2026*
*Domain: Security Operations Center*
*Key differentiator: TRIGGERED_EVOLUTION — the SOC that learns*
*Core principle: The demo proves the ARCHITECTURE, not agent sophistication. Tab 2 is THE differentiator.*
