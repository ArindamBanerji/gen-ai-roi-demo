# Compounding Intelligence Platform — Design Document v3

**Date:** February 28 – March 1, 2026
**Version:** 3.0 (v1 + v2 addendum consolidated into single document)
**Status:** No code yet. v5.0 is first real code (extraction from SOC copilot). INOVA deferred to v6.0.
**Repository:** ci-platform (Apache 2.0)
**Companion repos:**
- graph-attention-engine (standalone math library). Design: `gae_design_v7.md`
- soc-copilot (SOC domain expertise, proprietary). Design: `soc_copilot_design_v3.md`
- `design_decisions_v1.md` (rationale for v2 changes)

> **HuggingFace parallel:** This repo is analogous to `hub` + `accelerate` + `datasets` — the infrastructure that connects the math library (GAE ≈ `transformers`) to domain-specific applications (copilots ≈ model repos).

> **This document absorbs and supersedes:**
> - `ci_platform_design_v1.md` — initial three-repo architecture
> - `ci_platform_design_v2.md` — v2 addendum (INOVA deferral, v5.0 extraction strategy)

> **Changes from v1 → v3:**
> (1) INOVA deferred from v4.5 to v6.0. GraphEventBus deferred from v4.5 to v5.5.
> (2) v5.0 is now first real code (was v4.5). Pattern: build concrete in SOC, extract to platform.
> (3) New components: DomainConfig ABC with CalibrationProfile, schema parser, updated ContractChecker.
> (4) New sections: v5.0 Platform Scope (§7), v4.5 Scaffolding (§8), S2P Validation (§9).
> (5) Build timeline completely reworked.

---

## 1. What This Repo Contains

Production infrastructure that is **domain-agnostic** and **shared across all copilots**.

| Component | Purpose | First Version |
|---|---|---|
| `domains/base.py` | DomainConfig ABC + CalibrationProfile integration | **v5.0** |
| `platform/schema/parser.py` | Domain schema YAML parser + validation | **v5.0** |
| `platform/schema/contract_checker.py` | Validates SchemaContracts against domain schema + live graph | **v5.0** |
| `platform/state_manager.py` | Coordinated reset (soft/hard) across all stateful components | **v5.0** |
| `platform/domain_registry.py` | Domain config lookup by name | **v5.0** |
| `platform/events.py` | GraphEventBus (production async dispatch) | **v5.5** |
| `platform/ucl/resolution.py` | INOVA entity resolution | **v6.0** |
| `platform/ucl/ontology.py` | DomainOntology — supply-side governance | **v6.0** |
| `platform/ucl/schema.py` | SchemaValidator — write-path enforcement | **v6.0** |
| `platform/agents/` | Artifact evolution pipeline (Meta-Prompt, Safeguard, R×T×Q) | **v6.0** |

---

## 2. Dependency Graph

```
graph-attention-engine           ← numpy-only, zero external deps
        ↑
ci-platform [THIS REPO]          ← GAE + Neo4j + asyncio
        ↑
soc-copilot                      ← platform + GAE + SOC domain expertise
s2p-copilot (future)             ← platform + GAE + S2P domain expertise
```

**pyproject.toml dependencies:**
```toml
[project]
dependencies = [
    "graph-attention-engine>=0.1.0",
    "neo4j>=5.0",
]
```

---

## 3. Directory Structure

```
ci-platform/
├── platform/
│   ├── __init__.py
│   ├── events.py                # GraphEventBus (v5.5 — production async dispatch)
│   ├── state_manager.py         # Reset coordination (v5.0 — extracted from SOC)
│   ├── domain_registry.py       # Domain lookup (v5.0)
│   ├── schema/                  # Domain schema infrastructure
│   │   ├── __init__.py
│   │   ├── parser.py            # YAML/JSON → DomainSchemaSpec (v5.0)
│   │   └── contract_checker.py  # SchemaContract + schema → validation (v5.0)
│   ├── ucl/
│   │   ├── __init__.py
│   │   ├── resolution.py        # INOVA entity resolution (v6.0)
│   │   ├── ontology.py          # DomainOntology (v6.0)
│   │   └── schema.py            # SchemaValidator — write-path (v6.0)
│   └── agents/                  # Artifact evolution (v6.0)
│       ├── meta_prompt_agent.py
│       ├── safeguard_agent.py
│       └── evaluation_framework.py
├── domains/
│   └── base.py                  # DomainConfig ABC + CalibrationProfile hook (v5.0)
├── tests/
│   ├── test_schema_parser.py
│   ├── test_contract_checker.py
│   ├── test_state_manager.py
│   ├── test_domain_registry.py
│   └── test_events.py
├── pyproject.toml
├── LICENSE                      # Apache 2.0
└── README.md
```

---

## 4. Component Specifications

### 4.1 GraphEventBus (v5.5)

```python
# platform/events.py
from collections import defaultdict
from gae.events import DecisionMade, OutcomeVerified, GraphMutated  # types from GAE

class GraphEventBus:
    """Central event bus for causal propagation across loops.
    
    Uses GAE event types (pure dataclasses) with async dispatch.
    Until v5.5, copilots use a lightweight local bus.
    This is the production replacement.
    """
    def __init__(self):
        self._subscribers = defaultdict(list)

    def subscribe(self, event_type, handler):
        self._subscribers[event_type].append(handler)

    async def emit(self, event):
        for handler in self._subscribers[type(event)]:
            await handler(event)
```

> **Note:** v4.5 SOC copilot uses a lightweight local event bus (`services/event_bus.py`). The production GraphEventBus replaces it at v5.5 when the platform repo has real code.

### 4.2 Contract Validation (v5.0)

```python
# platform/schema/contract_checker.py
from gae.contracts import SchemaContract
from gae.schema import DomainSchemaSpec

class ContractChecker:
    """Validates GAE SchemaContracts against domain schema AND live graph.
    
    Two-level validation:
      Level 1 (schema-only): Does the contract match the schema definition?
                              No Neo4j needed. Run at development time.
      Level 2 (graph): Does the live graph actually have the data?
                        Needs Neo4j. Run at startup.
    """
    
    def validate_against_schema(
        self, contracts: list[SchemaContract], schema: DomainSchemaSpec
    ) -> list[str]:
        """Level 1: Schema consistency check."""
        return schema.validate_against_contracts(contracts)
    
    async def validate_against_graph(
        self, contracts: list[SchemaContract], neo4j
    ) -> dict[str, dict]:
        """Level 2: Live graph check.
        
        Returns per-contract report:
        {
            "travel_match": {
                "labels_present": True,
                "relationships_present": True,
                "min_counts_met": True,
                "property_coverage": 0.95,
                "status": "healthy"
            }
        }
        """
        report = {}
        for contract in contracts:
            result = await self._check_one_contract(contract, neo4j)
            report[contract.factor_name] = result
        return report
    
    async def validate_all(
        self, contracts: list[SchemaContract], 
        schema: DomainSchemaSpec | None, neo4j
    ) -> dict:
        """Full validation: schema + graph."""
        result = {"schema_warnings": [], "graph_report": {}}
        if schema:
            result["schema_warnings"] = self.validate_against_schema(contracts, schema)
        result["graph_report"] = await self.validate_against_graph(contracts, neo4j)
        return result
```

### 4.3 Supply-Side Governance (v6.0)

```python
# platform/ucl/ontology.py
class DomainOntology:
    """Machine-readable ontology: labels, relationships, property schemas, aliases.
    
    This is WRITE-SIDE governance. GAE contracts are READ-SIDE declarations.
    The ontology prevents bad data from entering the graph.
    """
    ...

# platform/ucl/schema.py
class SchemaValidator:
    """Gates the write path: connector → validate_and_transform() → Neo4j.
    
    Rejects writes with invalid labels, unknown relationships, or
    properties that don't match the ontology schema.
    """
    ...
```

### 4.4 Artifact Evolution Pipeline (v6.0)

Tier 6 implementation. Uses GAE scoring primitives for fitness evaluation.

| Component | Source | Status |
|---|---|---|
| Meta-Prompt Agent: variant generation | SC platform | Available |
| Safeguard Agent: constraint gate | SC platform | Available |
| R×T×Q evaluation framework | SC platform | Available |
| Promotion state machine | New engineering | v6.0 |
| Shadow/canary orchestrator | New engineering | v6.0 |

**Connector 6:** Outcomes → Artifact Evaluation → Artifact Mutation. GAE emits events (types). Platform implements the pipeline.

---

## 5. Build Timeline

| Version | Platform Components | Prompts | Notes |
|---|---|---|---|
| v4.5 | **None in this repo** — SOC builds StateManager + DomainConfig locally | 0 | v5.0 extracts from SOC |
| **v5.0** | **DomainConfig ABC, StateManager, domain_registry, schema parser, ContractChecker** | **3-5** | **First real code. Three-repo milestone.** |
| v5.5 | GraphEventBus (production), schema drift detection (C1) | 2 | Replace SOC's local event bus |
| v6.0 | INOVA resolution, DomainOntology, SchemaValidator, agent pipeline | 6-8 | Full UCL + Tier 6 |
| **Total** | | **~11-15** | |

**Key insight:** v4.5 SOC copilot builds StateManager and DomainConfig directly in the SOC repo. At v5.0, we extract and generalize them into ci-platform. This avoids premature abstraction — we build the concrete thing first, then extract the pattern.

---

## 6. Ontology Split — Demand vs Supply

| Concern | Nature | Repo | Why |
|---|---|---|---|
| SchemaContract | Demand — "I need labels X, relationships Y" | **GAE** | Pure Python. Coupled to FactorComputer. |
| EmbeddingContract | Demand — "I need properties Z with coverage" | **GAE** | Pure Python. Coupled to EmbeddingProvider. |
| PropertySpec | Foundation | **GAE** | Building block for both contract types. |
| DomainSchemaSpec | Format — "Schema declares entities, factors, decay classes" | **GAE** | Pure Python dataclass. Schema is data, not infrastructure. |
| ContractChecker | Operational — "Does graph match contracts?" | **Platform** | Needs Neo4j to verify. |
| Schema parser | Infrastructure — "Parse YAML into DomainSchemaSpec" | **Platform** | File I/O + YAML dependency. |
| DomainOntology | Supply — "Graph contains labels A, relationships B" | **Platform** | Governance. Domain-structural. |
| SchemaValidator | Enforcement — "Reject writes violating ontology" | **Platform** | Write-path. Interacts with connectors. |
| Schema drift detection | Monitoring — "Quality degraded since last check" | **Platform** | Runtime monitoring. |

**The principle:** GAE contracts are **declarative** (what computation needs). Platform validation is **operational** (what graph provides). UCL governance is **enforcement** (what writes are allowed).

---

## 7. v5.0 Platform Scope

### 7.1 Extraction Strategy

v5.0 is a three-repo milestone. The ci-platform v0.1.0 release extracts domain-agnostic components from the SOC copilot and combines them with GAE's schema format definitions.

```
SOC copilot (v4.5)          →  ci-platform (v5.0)
─────────────────               ──────────────────
StateManager                →  platform/state_manager.py (generalized)
SOCDomainConfig             →  domains/base.py (DomainConfig ABC)
domain lookup logic         →  platform/domain_registry.py
                            +  platform/schema/parser.py (from GAE schema format)
                            +  platform/schema/contract_checker.py (from GAE contracts)
```

### 7.2 DomainConfig ABC

```python
# domains/base.py
from abc import ABC, abstractmethod
from gae.calibration import CalibrationProfile
from gae.factors import FactorComputer
import numpy as np

class DomainConfig(ABC):
    """Abstract base for all domain copilots.
    
    A copilot implements this to provide:
    - Factor computers (the domain expertise)
    - Initial weight matrix (the expert priors)
    - CalibrationProfile (the learning hyperparameters)
    - Action definitions
    - Schema path (single source of truth for graph structure)
    """
    
    @abstractmethod
    def get_domain_name(self) -> str: ...
    
    @abstractmethod
    def get_actions(self) -> list[str]: ...
    
    @abstractmethod
    def get_factor_computers(self) -> list[FactorComputer]: ...
    
    @abstractmethod
    def get_initial_W(self) -> np.ndarray: ...
    
    @abstractmethod
    def get_calibration_profile(self) -> CalibrationProfile: ...
    
    @abstractmethod
    def get_factor_decay_classes(self) -> dict[str, str]: ...
    
    def get_schema_path(self) -> str | None:
        """Path to domain_schema.yaml. None if schema not yet defined."""
        return None
    
    def validate(self) -> list[str]:
        """Validate internal consistency. Returns list of warnings."""
        warnings = []
        W = self.get_initial_W()
        actions = self.get_actions()
        factors = self.get_factor_computers()
        
        if W.shape[0] != len(actions):
            warnings.append(f"W has {W.shape[0]} rows but {len(actions)} actions")
        if W.shape[1] != len(factors):
            warnings.append(f"W has {W.shape[1]} cols but {len(factors)} factors")
        
        profile = self.get_calibration_profile()
        warnings.extend(profile.validate())
        
        decay_classes = self.get_factor_decay_classes()
        for fc in factors:
            if fc.name not in decay_classes:
                warnings.append(f"Factor {fc.name} has no decay class")
        
        return warnings
```

### 7.3 Schema Parser

```python
# platform/schema/parser.py
import yaml
from gae.schema import DomainSchemaSpec, FactorSpec, EntitySpec, RelationshipSpec

def load_schema(path: str) -> DomainSchemaSpec:
    """Parse domain_schema.yaml into DomainSchemaSpec.
    
    The format is defined by GAE (gae/schema.py).
    This parser is platform infrastructure.
    """
    with open(path) as f:
        raw = yaml.safe_load(f)
    
    entities = [EntitySpec(**e) for e in raw.get("entities", [])]
    relationships = [RelationshipSpec(**r) for r in raw.get("relationships", [])]
    factors = [FactorSpec(**f_raw) for f_raw in raw.get("factors", [])]
    
    return DomainSchemaSpec(
        domain=raw["domain"],
        version=raw["version"],
        description=raw.get("description", ""),
        entities=entities,
        relationships=relationships,
        factors=factors,
        actions=raw.get("actions", []),
        decay_classes=raw.get("decay_classes", {}),
    )
```

### 7.4 StateManager (Extracted from SOC)

```python
# platform/state_manager.py
class StateManager:
    """Coordinated reset across GAE state + audit + graph.
    
    Domain-agnostic. Works with any DomainConfig.
    Extracted from SOC copilot's StateManager at v5.0.
    """
    
    def __init__(self, learning_state, audit_store, neo4j, domain_config):
        self.learning_state = learning_state
        self.audit_store = audit_store
        self.neo4j = neo4j
        self.domain_config = domain_config
    
    async def soft_reset(self):
        """Reset learning to priors. Preserve graph structure."""
        self.learning_state.W = self.domain_config.get_initial_W()
        self.learning_state.decision_count = 0
        self.learning_state.history = []
        self.learning_state.epsilon_vector = self.learning_state._build_epsilon_vector()
        
        await self.neo4j.execute_write(
            "MATCH (d:Decision) SET d.outcome = null, d.correct = null"
        )
        self.audit_store.append_reset_marker("soft")
    
    async def hard_reset(self, reseed_fn=None):
        """Full reset + optional re-seed."""
        await self.soft_reset()
        await self.neo4j.execute_write("MATCH (d:Decision) DETACH DELETE d")
        if reseed_fn:
            await reseed_fn(self.neo4j)
        self.audit_store.append_reset_marker("hard")
```

### 7.5 v5.0 Platform Prompts

| Prompt | Creates | Tests | Depends On |
|---|---|---|---|
| **PLAT-1** | `domains/base.py` (DomainConfig ABC), `platform/domain_registry.py` | SOCDomainConfig passes validate(). Registry resolves "soc". | GAE-CAL-1 |
| **PLAT-2** | `platform/schema/parser.py`, `platform/schema/contract_checker.py` | SOC schema parses. 6 contracts validate. Level 2 graph check runs. | GAE schema format |
| **PLAT-3** | `platform/state_manager.py` (extracted from SOC) | soft_reset preserves graph, clears learning. hard_reset deletes decisions. | PLAT-1 |
| **PLAT-4** (optional) | Startup validation hook | 6 contracts validated at startup, warnings logged | PLAT-2 |

---

## 8. v4.5 Scaffolding

### 8.1 What SOC Builds at v4.5

The SOC copilot at v4.5 builds these components directly in its own repo:

| Component | SOC Location | v5.0 Extraction Target |
|---|---|---|
| StateManager | `backend/app/services/state_manager.py` | `platform/state_manager.py` |
| SOCDomainConfig (with CalibrationProfile) | `backend/app/domains/soc/config.py` | Pattern → `domains/base.py` DomainConfig ABC |
| Alert pool + factor registry | `backend/app/domains/soc/` | Pattern → domain_registry |
| Factor decay class mapping | `backend/app/domains/soc/config.py` | Pattern → schema parser reads from YAML |

### 8.2 Extraction Contract

When building v4.5 SOC components, these conventions ensure clean extraction at v5.0:

1. **StateManager** should not import SOC-specific types. It should accept generic interfaces (learning_state, audit_store, neo4j, domain_config).
2. **SOCDomainConfig** should follow the DomainConfig pattern even though no ABC exists yet.
3. **Factor decay class mapping** should be a dict, not embedded in factor code.
4. **Domain-specific logic** (alert definitions, factor implementations, seed data) should NOT be in files that will be extracted.

---

## 9. S2P Validation Walkthrough

### 9.1 Purpose

Every platform abstraction must work for a second domain. S2P (Source-to-Pay, procurement) is the validation target.

### 9.2 S2P DomainConfig (Design Only)

```python
class S2PDomainConfig(DomainConfig):
    """Source-to-Pay procurement copilot. Design validation only."""
    
    def get_domain_name(self) -> str: return "s2p"
    
    def get_actions(self) -> list[str]:
        return ["approve", "hold_for_review", "reject", "escalate_compliance"]
    
    def get_factor_computers(self) -> list:
        return [
            SupplierReliabilityFactor(),   # Delivery history, quality
            SpendComplianceFactor(),        # Budget, contract terms
            DualSourceFactor(),             # Single-source risk
            GeopoliticalRiskFactor(),       # Supply chain disruption
            HistoricalApprovalFactor(),     # Pattern history equivalent
            PriceVarianceFactor(),          # Deviation from baseline
        ]
    
    def get_calibration_profile(self) -> CalibrationProfile:
        return s2p_calibration_profile()  # penalty_ratio=5.0, temperature=0.4
    
    def get_factor_decay_classes(self) -> dict[str, str]:
        return {
            "supplier_reliability": "permanent",
            "spend_compliance": "standard",
            "dual_source": "permanent",
            "geopolitical_risk": "campaign",
            "historical_approval": "standard",
            "price_variance": "transient",
        }
```

### 9.3 Validation Checklist

| Question | Expected | If Not |
|---|---|---|
| Can S2PDomainConfig extend DomainConfig ABC? | Yes | ABC is too SOC-specific |
| Does CalibrationProfile support penalty_ratio=5.0? | Yes | Profile missing configurable penalty |
| Does S2P's "transient" decay class (0.02) work? | Yes | Decay classes hardcoded |
| Can ContractChecker validate S2P SchemaContracts? | Yes | Checker imports SOC types |
| Can StateManager reset S2P learning state? | Yes | StateManager hardcodes SOC |
| Do EvaluationScenario and AblationConfig work for S2P? | Yes | Evaluation assumes ATT&CK |

**S2P specifics:** technique_id is None (Optional field). Categories are procurement types. FactorComputer stays `compute() → float` — categorical encoding (Gold=1.0, Silver=0.6, Bronze=0.3) is copilot's responsibility.

---

## Appendix: Version History

| Version | Date | Changes |
|---|---|---|
| **1.0** | **Feb 28** | Initial document. Three-repo architecture. Content extracted from gae_design_v4 (platform sections) and open_source_impact_analysis. |
| **2.0** | **Mar 1** | INOVA → v6.0. GraphEventBus → v5.5. v5.0 = first real code. DomainConfig ABC, schema parser, ContractChecker, StateManager. S2P validation. Extraction contract for v4.5 → v5.0. |
| **3.0** | **Mar 1** | v1 + v2 consolidated into single document. All sections current. |

---

*Compounding Intelligence Platform — Design Document v3 | February 28 – March 1, 2026*
*Apache 2.0. Domain-agnostic infrastructure shared across all copilots.*
*v5.0: first real code (DomainConfig + schema + validation + reset). 3-5 prompts.*
*v5.5: production event bus. v6.0: INOVA + agents + governance.*
*Companion: gae_design_v7, soc_copilot_design_v3, design_decisions_v1, gap_analysis_v3*
*"The moat is the graph, not the model. The platform proves it."*
