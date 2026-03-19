# S2P Copilot — Lightweight Design (Validation Only)

**Date:** March 1, 2026
**Version:** 0.1 (design validation — no implementation planned before v7.0)
**Purpose:** Validate that GAE, ci-platform, and evaluation framework abstractions are genuinely domain-agnostic by designing a second copilot in detail. Surface any design flaws before GAE-CAL-1 gets coded.
**Status:** Design only. No code. No repo. No prompts.

---

## 1. The S2P Decision Problem

### 1.1 What Is Being Triaged?

A Source-to-Pay (S2P) copilot triages **purchase requisitions** (PRs) — the point where a business need becomes a financial commitment. Every PR that enters the system must be approved, held for review, rejected, or escalated to compliance. Today this is done by procurement analysts manually reviewing each PR against policies, supplier history, market conditions, and compliance requirements.

The compounding intelligence claim is the same as SOC: after 1,000 PR decisions with verified outcomes, the system develops firm-specific procurement judgment. It learns that Supplier X's delivery reliability dropped last quarter, that single-source risk on Category Y was flagged by compliance, that the CFO's budget threshold shifted in Q3.

### 1.2 Why This Is a Good Validation Target

S2P differs from SOC in ways that stress-test the GAE abstractions:

| Dimension | SOC | S2P | Design Stress |
|---|---|---|---|
| Time pressure | Seconds (active threat) | Hours/days (procurement cycle) | CalibrationProfile.temperature must support softer distributions |
| Penalty asymmetry | 20:1 (missed threat = breach) | 5:1 (bad approval = overspend) | CalibrationProfile.penalty_ratio must be configurable |
| Factor semantics | Security signals (travel, threat intel) | Business signals (spend, supplier, geo) | FactorComputer protocol must be domain-free |
| Decay classes | campaign/standard/permanent | transient/standard/permanent | "transient" decay class (0.02) must work in CalibrationProfile |
| ATT&CK | T1078, T1566, etc. | N/A | EvaluationScenario.technique_id must be Optional |
| Graph structure | Users, Alerts, ThreatIntel, Devices | Suppliers, PurchaseOrders, Contracts, Commodities | DomainSchemaSpec must accept different entity/relationship sets |
| Categorical factors | Binary/continuous (travel: yes/no, score: 0.82) | Ordinal (Gold/Silver/Bronze → 1.0/0.6/0.3) | compute() → float must handle categorical encoding |

### 1.3 S2P Domain Context (from blog posts)

The published supply chain blogs describe a multi-agent architecture with 5 agents (Planner, Meta-prompt, Execution, Safeguard, Interpretation), tool integration (SAP, Oracle, Dynamics), and an R×T×Q evaluation framework. The S2P copilot in the compounding intelligence architecture uses a different approach: instead of multi-agent LLM orchestration, it uses **graph attention + learning loops** for decision quality that compounds. The blog's multi-agent architecture informs Tier 6 (artifact evolution pipeline at v6.0+), but the S2P copilot's core loop is the same GAE pipeline as SOC: factors → scoring → decision → outcome → learning.

---

## 2. S2P Graph Schema

### 2.1 Entities

| Label | Description | Key Properties | Analogous SOC Entity |
|---|---|---|---|
| **Supplier** | Vendor in supplier master | name, tier (Gold/Silver/Bronze), country, risk_rating, onboarded_date | User |
| **PurchaseRequisition** | The "alert" — the thing being triaged | pr_id, requester, category, amount, currency, urgency, created_at | Alert |
| **Contract** | Active agreement with supplier | contract_id, start_date, end_date, spend_limit, compliance_status | (no direct analog) |
| **Commodity** | Material/service category | commodity_code, name, market_volatility, strategic_flag | ThreatIntel (domain-specific context) |
| **BudgetCenter** | Cost center with spend limits | center_id, annual_budget, ytd_spend, approver | Asset |
| **ComplianceRule** | Regulatory or policy constraint | rule_id, type (SOX/FCPA/internal), threshold, active | (no direct analog) |
| **Decision** | GAE decision node (same as SOC) | decision_id, action, confidence, f_vector, timestamp, outcome | Decision |

### 2.2 Relationships

| Source | Relationship | Target | Purpose |
|---|---|---|---|
| PurchaseRequisition | SUBMITTED_BY | Supplier | Who's supplying this PR |
| PurchaseRequisition | CHARGES_TO | BudgetCenter | Where the money comes from |
| PurchaseRequisition | REQUIRES | Commodity | What's being bought |
| Supplier | HAS_CONTRACT | Contract | Active agreements |
| Supplier | DELIVERS | Commodity | What they can supply |
| Supplier | LOCATED_IN | Country/Region | Geographic risk |
| Contract | GOVERNS | BudgetCenter | Spend limits |
| ComplianceRule | APPLIES_TO | Commodity | Regulatory coverage |
| Decision | DECIDED_ON | PurchaseRequisition | GAE decision linkage |
| Decision | CALIBRATED_BY | Decision | Discovery provenance |

### 2.3 domain_schema.yaml (Design)

```yaml
domain: s2p
version: "0.1"
description: "Source-to-Pay procurement copilot"

entities:
  - label: Supplier
    properties: [name, tier, country, risk_rating, onboarded_date]
  - label: PurchaseRequisition
    properties: [pr_id, requester, category, amount, currency, urgency, created_at]
  - label: Contract
    properties: [contract_id, start_date, end_date, spend_limit, compliance_status]
  - label: Commodity
    properties: [commodity_code, name, market_volatility, strategic_flag]
  - label: BudgetCenter
    properties: [center_id, annual_budget, ytd_spend, approver]
  - label: ComplianceRule
    properties: [rule_id, type, threshold, active]
  - label: Decision
    properties: [decision_id, action, confidence, f_vector, timestamp, outcome]

relationships:
  - source: PurchaseRequisition
    type: SUBMITTED_BY
    target: Supplier
  - source: PurchaseRequisition
    type: CHARGES_TO
    target: BudgetCenter
  - source: PurchaseRequisition
    type: REQUIRES
    target: Commodity
  - source: Supplier
    type: HAS_CONTRACT
    target: Contract
  - source: Supplier
    type: DELIVERS
    target: Commodity
  - source: ComplianceRule
    type: APPLIES_TO
    target: Commodity
  - source: Decision
    type: DECIDED_ON
    target: PurchaseRequisition
  - source: Decision
    type: CALIBRATED_BY
    target: Decision

factors:
  - name: supplier_reliability
    decay_class: permanent
    description: "Supplier tier + delivery history + quality scores"
    required_labels: [Supplier, Contract]
    required_relationships: [HAS_CONTRACT, DELIVERS]
  - name: spend_compliance
    decay_class: standard
    description: "PR amount vs budget remaining vs contract limits"
    required_labels: [BudgetCenter, Contract]
    required_relationships: [CHARGES_TO, GOVERNS]
  - name: dual_source
    decay_class: permanent
    description: "Single-source risk — how many suppliers for this commodity"
    required_labels: [Supplier, Commodity]
    required_relationships: [DELIVERS, REQUIRES]
  - name: geopolitical_risk
    decay_class: campaign
    description: "Supply chain disruption risk from supplier geography"
    required_labels: [Supplier]
    required_relationships: [LOCATED_IN]
  - name: historical_approval
    decay_class: standard
    description: "Prior decisions on similar PRs (PatternHistory analog)"
    required_labels: [Decision, PurchaseRequisition]
    required_relationships: [DECIDED_ON]
  - name: price_variance
    decay_class: transient
    description: "Deviation from baseline/historical pricing for commodity"
    required_labels: [Commodity, PurchaseRequisition]
    required_relationships: [REQUIRES]

actions: [approve, hold_for_review, reject, escalate_compliance]

decay_classes:
  permanent: 0.0001
  standard: 0.001
  campaign: 0.005
  transient: 0.02
```

---

## 3. S2P Factor Implementations (Design)

### 3.1 SupplierReliabilityFactor

```python
class SupplierReliabilityFactor(FactorComputer):
    """Supplier tier + delivery history + quality scores.
    
    Graph traversal: (pr)-[:SUBMITTED_BY]->(s:Supplier)-[:HAS_CONTRACT]->(c:Contract)
    
    Categorical encoding:
      Gold tier + active contract + on-time > 95% → 1.0
      Silver tier + active contract                → 0.6
      Bronze tier or no contract                   → 0.3
      No supplier found                            → 0.0
    
    DESIGN NOTE: This validates that compute() → float handles categorical
    encoding at the copilot level, not the GAE level. GAE sees 0.6, not "Silver."
    """
    name = "supplier_reliability"
    
    async def compute(self, entity_id: str, context: dict) -> float:
        # Cypher: MATCH (pr {id: $entity_id})-[:SUBMITTED_BY]->(s:Supplier)
        #         -[:HAS_CONTRACT]->(c:Contract)
        #         RETURN s.tier, s.risk_rating, c.compliance_status
        # Encode: Gold=1.0, Silver=0.6, Bronze=0.3
        # Adjust for contract status, delivery history
        ...
```

### 3.2 SpendComplianceFactor

```python
class SpendComplianceFactor(FactorComputer):
    """PR amount vs budget remaining vs contract spending limits.
    
    Graph traversal: (pr)-[:CHARGES_TO]->(bc:BudgetCenter)<-[:GOVERNS]-(c:Contract)
    
    Returns: 1.0 if well within limits, 0.0 if exceeds both budget and contract.
    Continuous, not categorical.
    """
    name = "spend_compliance"
    
    async def compute(self, entity_id: str, context: dict) -> float:
        # ratio = pr.amount / (bc.annual_budget - bc.ytd_spend)
        # If ratio < 0.5: return 1.0 (well within budget)
        # If ratio < 0.8: return 0.7 (approaching limit)
        # If ratio < 1.0: return 0.3 (near limit)
        # If ratio >= 1.0: return 0.0 (exceeds budget)
        # Also check contract spend_limit
        ...
```

### 3.3 DualSourceFactor

```python
class DualSourceFactor(FactorComputer):
    """Single-source risk assessment.
    
    Graph traversal: (pr)-[:REQUIRES]->(com:Commodity)<-[:DELIVERS]-(s:Supplier)
    
    Returns: 1.0 if 3+ suppliers deliver this commodity (low risk).
             0.5 if 2 suppliers (moderate risk).
             0.0 if single source (high risk — compliance escalation likely).
    
    DESIGN NOTE: This is a COUNT-based factor. The graph traversal
    finds all suppliers for the commodity, not just the PR's supplier.
    """
    name = "dual_source"
    
    async def compute(self, entity_id: str, context: dict) -> float:
        # MATCH (pr {id: $entity_id})-[:REQUIRES]->(com:Commodity)
        #       <-[:DELIVERS]-(s:Supplier)
        # RETURN count(DISTINCT s) as supplier_count
        ...
```

### 3.4 GeopoliticalRiskFactor

```python
class GeopoliticalRiskFactor(FactorComputer):
    """Supply chain disruption risk from supplier geography.
    
    Graph traversal: (pr)-[:SUBMITTED_BY]->(s:Supplier)-[:LOCATED_IN]->(region)
    
    Returns: 0.0 if high-risk region + active sanctions/disruption.
             0.5 if moderate-risk region.
             1.0 if low-risk region.
    
    Decay class: campaign (geopolitical situations evolve, 0.005 rate).
    A sanctions regime change should shift weights within weeks.
    """
    name = "geopolitical_risk"
    
    async def compute(self, entity_id: str, context: dict) -> float:
        # Risk lookup from supplier country
        # Could be enriched from external data (analogous to ThreatIntel)
        ...
```

### 3.5 HistoricalApprovalFactor

```python
class HistoricalApprovalFactor(FactorComputer):
    """Prior decisions on similar PRs. PatternHistory analog for S2P.
    
    Graph traversal: (pr)-[:REQUIRES]->(com:Commodity)<-[:REQUIRES]-(prev_pr)
                     <-[:DECIDED_ON]-(d:Decision {correct: true})
    
    Returns: confidence from prior correct decisions on same commodity.
    THIS IS WHERE COMPOUNDING HAPPENS — more decisions = better signal.
    """
    name = "historical_approval"
    
    async def compute(self, entity_id: str, context: dict) -> float:
        # Count prior correct decisions on same commodity
        # Weighted by recency (recent decisions count more)
        # More decisions → higher confidence in historical signal
        ...
```

### 3.6 PriceVarianceFactor

```python
class PriceVarianceFactor(FactorComputer):
    """Deviation from baseline pricing for the commodity.
    
    Graph traversal: (pr)-[:REQUIRES]->(com:Commodity)
                     + property read: pr.amount vs com.baseline_price
    
    Returns: 1.0 if price within 10% of baseline.
             0.5 if 10-25% deviation.
             0.0 if >50% deviation (price spike or error).
    
    Decay class: transient (0.02) — commodity prices are volatile.
    A price spike should affect weights immediately but fade quickly
    if the market normalizes.
    
    DESIGN NOTE: This is the fastest-decaying factor. Tests that
    "transient" decay_class (0.02) works correctly in CalibrationProfile.
    """
    name = "price_variance"
    
    async def compute(self, entity_id: str, context: dict) -> float:
        # Compare pr.amount / com.baseline_price
        ...
```

---

## 4. S2P Actions + W₀

### 4.1 Actions

| Action | Meaning | SOC Analog |
|---|---|---|
| **approve** | Auto-approve the PR | suppress (both are "this is fine") |
| **hold_for_review** | Queue for analyst review | investigate |
| **reject** | Reject the PR | (no analog — SOC doesn't reject alerts) |
| **escalate_compliance** | Route to compliance team | escalate |

### 4.2 Initial Weight Matrix (W₀)

```python
W_0 = np.array([
    # supplier  spend  dual   geo    history  price
    [ 0.7,     0.3,   0.2,   0.1,   0.6,     0.3],   # approve
    [ 0.3,     0.6,   0.5,   0.4,   0.3,     0.5],   # hold_for_review
    [-0.2,     0.8,   0.3,   0.6,  -0.3,     0.7],   # reject
    [ 0.1,     0.4,   0.7,   0.8,   0.1,     0.4],   # escalate_compliance
])
```

**Rationale:**
- **approve** loads heavily on supplier_reliability (0.7) and historical_approval (0.6) — trust the supplier, trust the pattern.
- **hold_for_review** loads on spend_compliance (0.6), dual_source (0.5), price_variance (0.5) — financial signals trigger review.
- **reject** loads on spend_compliance (0.8) and price_variance (0.7) — clear budget/price violations.
- **escalate_compliance** loads on geopolitical_risk (0.8) and dual_source (0.7) — regulatory/supply chain risk signals.

### 4.3 CalibrationProfile

```python
s2p_calibration_profile = CalibrationProfile(
    learning_rate=0.01,       # Slower than SOC — procurement decisions are less frequent
    penalty_ratio=5.0,        # Wrong approval costs money but not $4.44M breach
    temperature=0.4,          # Softer than SOC — procurement allows more deliberation
    epsilon_default=0.001,
    discount_strength=0.0,    # Same as SOC — measure first, fix later
    decay_class_rates={
        "permanent": 0.0001,  # Supplier master data changes slowly
        "standard": 0.001,    # Normal procurement patterns
        "campaign": 0.005,    # Geopolitical situations, sanctions regimes
        "transient": 0.02,    # Commodity prices are volatile
    },
)
```

**Key difference from SOC:** penalty_ratio=5.0 (not 20.0). A wrong PR approval costs the company money (overspend, compliance fine), but it's not an existential threat like a missed security breach. The system still learns faster from mistakes than successes, just less asymmetrically.

---

## 5. Evaluation Scenarios (3-4 examples)

### 5.1 S2P-DUAL-SOURCE-01: Single-source escalation

```python
EvaluationScenario(
    scenario_id="S2P-DUAL-SOURCE-01",
    domain="s2p",
    category="supply_risk",
    technique_id=None,           # No ATT&CK for S2P — validates Optional
    confidence_tier="high",
    graph_context={
        "commodity": "titanium_alloy",
        "supplier_count": 1,     # SINGLE SOURCE
        "supplier_tier": "Silver",
        "pr_amount": 250000,
        "budget_remaining": 800000,
    },
    alert={...},                  # PR for titanium from single supplier
    expected_action="escalate_compliance",
    expected_dominant_factors=["dual_source", "geopolitical_risk"],
    planted_relationship=None,
    learning_prerequisite=None,
)
```

**Why escalate:** Single-source commodity at $250K. Even if supplier is reliable and budget is fine, compliance rules require dual-source review for strategic commodities.

### 5.2 S2P-PRICE-SPIKE-01: Price variance rejection

```python
EvaluationScenario(
    scenario_id="S2P-PRICE-SPIKE-01",
    domain="s2p",
    category="price_anomaly",
    technique_id=None,
    confidence_tier="high",
    graph_context={
        "commodity": "steel_plate",
        "pr_amount": 180000,
        "baseline_price": 90000,   # 2x price spike
        "supplier_tier": "Gold",
        "budget_remaining": 500000,
    },
    alert={...},
    expected_action="hold_for_review",
    expected_dominant_factors=["price_variance", "spend_compliance"],
    planted_relationship=None,
    learning_prerequisite=None,
)
```

**Why hold (not reject):** Gold supplier, budget available. But 2x price spike needs human review — could be market movement or error. After 10 similar decisions where analyst confirms market movement, the system should learn to approve faster.

### 5.3 S2P-LEARN-01: Learning prerequisite scenario

```python
EvaluationScenario(
    scenario_id="S2P-LEARN-01",
    domain="s2p",
    category="routine_approval",
    technique_id=None,
    confidence_tier="medium",     # Only correct after learning
    graph_context={
        "commodity": "office_supplies",
        "pr_amount": 1500,
        "supplier_tier": "Gold",
        "budget_remaining": 200000,
        "prior_correct_decisions": 15,  # Good history
    },
    alert={...},
    expected_action="approve",
    expected_dominant_factors=["historical_approval", "supplier_reliability"],
    planted_relationship=None,
    learning_prerequisite="15 correct approve decisions on office_supplies from Gold suppliers",
)
```

**Why this tests learning:** At decision #1, the system might hold_for_review (cautious). After 15 correct approvals on similar PRs, historical_approval factor is high and the system should auto-approve. The learning_prerequisite documents this — the scenario is only expected to pass AFTER the prerequisite history exists.

### 5.4 S2P-DISCOVERY-01: Cross-graph discovery (design only)

```python
EvaluationScenario(
    scenario_id="S2P-DISCOVERY-01",
    domain="s2p",
    category="supply_chain_disruption",
    technique_id=None,
    confidence_tier="discovery",
    graph_context={
        "supplier": "AcmeMfg",
        "supplier_country": "Taiwan",
        "commodity": "semiconductor_wafers",
        "active_disruption": "taiwan_strait_tensions_2026",
    },
    alert={...},
    expected_action="escalate_compliance",
    expected_dominant_factors=["geopolitical_risk", "dual_source"],
    planted_relationship={
        "type": "DISRUPTED_BY",
        "source": "semiconductor_wafers",
        "target": "taiwan_strait_tensions_2026",
    },
    learning_prerequisite=None,
)
```

**Discovery test:** The system should discover that AcmeMfg's semiconductor supply is threatened by the geopolitical event — even though no explicit DISRUPTED_BY relationship was pre-programmed. This is the S2P analog of SOC's "Singapore + CFO + threat spike" scenario.

---

## 6. Design Validation Checklist

### 6.1 GAE Interface Validation

| Interface | S2P Requirement | Works? | Issue if Not |
|---|---|---|---|
| `FactorComputer.compute(entity_id, context) → float` | Categorical encoding (Gold=1.0, Silver=0.6) done in copilot, GAE sees float | ✅ | — |
| `CalibrationProfile(penalty_ratio=5.0)` | Lower asymmetry than SOC | ✅ | penalty_ratio field exists, no SOC-specific validation |
| `CalibrationProfile(temperature=0.4)` | Softer softmax | ✅ | temperature field exists, range [0.05, 2.0] |
| `decay_class_rates["transient"] = 0.02` | Fast-decaying commodity prices | ✅ | decay_class_rates is a dict, any string key works |
| `score_entity(f, W, actions, tau)` | 4 actions × 6 factors | ✅ | No hardcoded action/factor counts |
| `LearningState.update(action_index, outcome, f)` | Same interface regardless of domain | ✅ | — |
| `expand_weight_matrix(new_factor_name)` | Discovery adds new procurement factor | ✅ | — |

### 6.2 Evaluation Framework Validation

| Interface | S2P Requirement | Works? | Issue if Not |
|---|---|---|---|
| `EvaluationScenario.technique_id` | Must be Optional (no ATT&CK) | ✅ | Field is `Optional[str]` |
| `EvaluationScenario.category` | "supply_risk", "price_anomaly" etc. | ✅ | Free string field |
| `EvaluationScenario.planted_relationship` | DISRUPTED_BY (S2P discovery) | ✅ | Generic dict, no SOC assumptions |
| `EvaluationReport.by_technique` | Should be "by_category" for S2P | ⚠️ | Field name assumes ATT&CK. **Rename to `by_category` or make generic.** |
| `AblationConfig` | Same 4 baselines work for S2P | ✅ | Domain-agnostic by design |
| `InstitutionalJudgmentMetrics` | "CPO language" not "CISO language" | ✅ | GAE computes metrics; copilot translates to domain language |

### 6.3 Platform Validation

| Interface | S2P Requirement | Works? | Issue if Not |
|---|---|---|---|
| `DomainConfig ABC` | S2PDomainConfig extends it | ✅ | All abstract methods are domain-generic |
| `StateManager.soft_reset()` | Reset S2P learning state | ✅ | No SOC imports; uses generic DomainConfig |
| `DomainSchemaSpec` | Different entities/relationships | ✅ | Schema format is domain-agnostic |
| `ContractChecker` | Validate S2P SchemaContracts | ✅ | No SOC-specific Cypher |
| `domain_registry.resolve("s2p")` | Find S2P config at runtime | ✅ | Registration by name string |

### 6.4 NarrativeProvider Validation

| Interface | S2P Requirement | Works? | Issue if Not |
|---|---|---|---|
| `NarrativeContext.technique_id` | None for S2P | ✅ | Optional field |
| `NarrativeContext.factors` | S2P factor names | ✅ | Generic dict[str, float] |
| `TemplateNarrativeProvider` | Template works for S2P alerts | ✅ | Uses context fields, no SOC assumptions |

---

## 7. Issues Found

### 7.1 ISSUE: EvaluationReport.by_technique assumes ATT&CK

**In:** gae_design_v6 §17 (EvaluationReport dataclass)
**Field:** `by_technique: dict[str, float]`
**Problem:** S2P has no techniques. The field name implies ATT&CK.
**Fix:** Rename to `by_category: dict[str, float]` — generic across all domains. SOC categories are ATT&CK techniques, S2P categories are procurement types, both map to the same field.
**Impact:** Low. GAE-EVAL-1 hasn't been coded yet. Change the design doc before coding.

### 7.2 NON-ISSUE: Categorical factors

S2P's SupplierReliabilityFactor encodes Gold/Silver/Bronze as 1.0/0.6/0.3. This is the copilot's responsibility — GAE sees a float. No interface change needed. The encoding rationale should be documented in the copilot's factor implementation, not in GAE.

### 7.3 NON-ISSUE: "transient" decay class

The decay_class_rates dict in CalibrationProfile accepts any string key with a float rate. "transient" at 0.02 works. No change needed. The only question is whether 0.02 is the right rate for commodity price volatility — that's a tuning question for the S2P copilot, not a design question for GAE.

### 7.4 WATCH: Cross-graph discovery across S2P domains

S2P's discovery scenario (semiconductor + geopolitical event) requires entity embeddings that can compare Commodity nodes with GeopoliticalEvent nodes. This is the same cross-domain comparison challenge as SOC (User ↔ ThreatCampaign). The EmbeddingProvider protocol handles this — PropertyEmbeddingProvider extracts properties from both node types and computes similarity. Whether property-based embeddings have sufficient quality for S2P's cross-domain comparison is the same open question as SOC's GATE-B3. If B3 passes for SOC, it's likely to work for S2P. If it fails, both domains have the same limitation.

---

## 8. Summary of Design Impact

| Finding | Impact | Action | When |
|---|---|---|---|
| EvaluationReport.by_technique → by_category | LOW — field rename before coding | Update gae_design_v6 §17 | Before GAE-EVAL-1 |
| All other GAE interfaces | None — work correctly for S2P | — | — |
| All platform interfaces | None — genuinely domain-agnostic | — | — |
| NarrativeProvider | None — Optional fields handle S2P | — | — |
| CalibrationProfile | None — configurable fields cover S2P needs | — | — |
| Categorical encoding | Copilot responsibility, not GAE | Document in S2P factor implementations | S2P implementation (v7.0) |
| Cross-domain discovery quality | Same open question as SOC (B3 gate) | Watch SOC Phase C results | v4.5 Phase C |

**Bottom line:** One field rename (by_technique → by_category) before GAE-EVAL-1 is coded. Everything else validates cleanly. The three-repo architecture is genuinely domain-agnostic.

---

*S2P Copilot — Lightweight Design v0.1 | March 1, 2026*
*Design validation only. No code. One interface fix found (by_technique → by_category).*
*"Same engine, different domain, different judgment. That's the platform claim."*
