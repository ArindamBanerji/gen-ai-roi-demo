"""Supply Chain / Source-to-Pay (S2P) domain configuration.

Smoke-test stub for the v3.2 domain-agnostic architecture validation.
Demonstrates that a second domain can implement DomainConfig without
touching core/ or domains/soc/.

What is fully defined (smoke-test scope):
  factors         — 6 scoring dimensions
  actions         — 5 possible PO dispositions
  situation_types — 6 situation classifications
  policies        — 4 policies with one priority-1 conflict pair
  asymmetry_ratio — 12.0  (procurement mistakes less catastrophic than SOC)
  prompt_variants — 4 evolver-tracked variants
  metrics_config  — 4 business impact numbers

What is NOT yet implemented (raises NotImplementedError):
  classify_situation() — supply_chain/situations.py not yet created
  compute_factors()    — supply_chain/factors.py not yet created
  get_seed_queries()   — supply_chain/seed_neo4j.py not yet created
  get_graph_query_templates() — supply_chain Cypher templates not yet created
  get_narration_templates()   — supply_chain LLM prompts not yet created
"""

from app.domains.base import (
    DomainConfig, DomainAction, DomainFactor,
    DomainSituationType, DomainPolicy, PromptVariant,
)
from typing import Any, Dict, List


class S2PDomainConfig(DomainConfig):
    """Source-to-Pay / Procurement Copilot domain module."""

    # =========================================================================
    # Identity
    # =========================================================================

    @property
    def name(self) -> str:
        return "supply_chain"

    @property
    def display_name(self) -> str:
        return "Procurement Copilot"

    @property
    def trigger_entity(self) -> str:
        return "Purchase Order"

    # =========================================================================
    # Factors (6)
    # The decision vector dimensions for PO triage.
    # =========================================================================

    @property
    def factors(self) -> List[DomainFactor]:
        return [
            DomainFactor(
                id="price_variance",
                label="Price Variance",
                description=(
                    "Unit price deviation from contract benchmark — positive means "
                    "above contracted rate, triggers cost policy at >10%"
                ),
            ),
            DomainFactor(
                id="demand_urgency",
                label="Demand Urgency",
                description=(
                    "Business urgency score derived from lead times, current "
                    "inventory levels, and production schedule dependencies"
                ),
            ),
            DomainFactor(
                id="supplier_reliability",
                label="Supplier Reliability",
                description=(
                    "Composite of on-time delivery rate, quality rejection rate, "
                    "and credit risk Z-score over trailing 12 months"
                ),
            ),
            DomainFactor(
                id="geopolitical_risk",
                label="Geopolitical Risk",
                description=(
                    "Country/region risk index for supplier origin — covers "
                    "trade sanctions, tariff exposure, and political instability"
                ),
            ),
            DomainFactor(
                id="alternative_availability",
                label="Alternative Availability",
                description=(
                    "Count and qualification status of alternative suppliers for "
                    "this SKU — single-source items score 0.0"
                ),
            ),
            DomainFactor(
                id="spend_pattern_history",
                label="Spend Pattern History",
                description=(
                    "Historical spend patterns, seasonal baselines, and anomaly "
                    "detection signal from prior POs for this supplier/category"
                ),
            ),
        ]

    # =========================================================================
    # Actions (5)
    # Possible dispositions for a Purchase Order.
    # time_saved_min: manual processing time avoided.
    # cost_dollars:   incremental cost of the action vs auto-approve.
    # =========================================================================

    @property
    def actions(self) -> List[DomainAction]:
        return [
            DomainAction(
                id="auto_approve_po",
                label="Auto-Approve PO",
                time_saved_min=30.0,   # ~30 min manual review avoided per PO
                cost_dollars=0.0,
                risk_level="low",
            ),
            DomainAction(
                id="flag_for_review",
                label="Flag for Review",
                time_saved_min=0.0,    # no time saved — adds a review step
                cost_dollars=95.0,     # ~$95 procurement analyst time (30 min × $190/hr)
                risk_level="low",
            ),
            DomainAction(
                id="trigger_dual_sourcing",
                label="Trigger Dual-Sourcing",
                time_saved_min=0.0,
                cost_dollars=250.0,    # sourcing event setup cost
                risk_level="medium",
            ),
            DomainAction(
                id="escalate_to_procurement_lead",
                label="Escalate to Procurement Lead",
                time_saved_min=0.0,
                cost_dollars=190.0,    # lead-level review time
                risk_level="none",
            ),
            DomainAction(
                id="hold_pending_compliance",
                label="Hold Pending Compliance",
                time_saved_min=0.0,
                cost_dollars=140.0,    # compliance review cost + delay exposure
                risk_level="none",
            ),
        ]

    # =========================================================================
    # Situation types (6)
    # =========================================================================

    @property
    def situation_types(self) -> List[DomainSituationType]:
        return [
            DomainSituationType(
                id="ROUTINE_REORDER",
                label="Routine Reorder",
                description=(
                    "Standard replenishment PO from an approved tier-1 supplier "
                    "within contracted price — auto-approve eligible"
                ),
                color="#3B82F6",   # blue
            ),
            DomainSituationType(
                id="PRICE_ANOMALY",
                label="Price Anomaly",
                description=(
                    "Unit price exceeds contract benchmark by >10% — "
                    "cost policy review required"
                ),
                color="#F97316",   # orange
            ),
            DomainSituationType(
                id="SUPPLY_RISK",
                label="Supply Risk",
                description=(
                    "Supplier Z-score below threshold or active geopolitical "
                    "event affecting supply origin — risk escalation required"
                ),
                color="#EF4444",   # red
            ),
            DomainSituationType(
                id="DEMAND_SPIKE",
                label="Demand Spike",
                description=(
                    "PO quantity >2σ above baseline for this SKU/period — "
                    "may indicate hoarding, error, or genuine demand surge"
                ),
                color="#EAB308",   # yellow
            ),
            DomainSituationType(
                id="SINGLE_SOURCE_DEPENDENCY",
                label="Single Source Dependency",
                description=(
                    "No qualified alternative supplier exists for this item and "
                    "single-source share exceeds 70% — dual-sourcing trigger"
                ),
                color="#A855F7",   # purple
            ),
            DomainSituationType(
                id="COMPLIANCE_FLAG",
                label="Compliance Flag",
                description=(
                    "PO involves a restricted supplier, sanctioned entity, or "
                    "requires additional trade-compliance documentation"
                ),
                color="#DC2626",   # dark red
            ),
        ]

    # =========================================================================
    # Policies (4)
    # Conflict scenario: POLICY-RISK-003 (priority 1, flag_for_review) conflicts
    # with POLICY-DUAL-004 (priority 1, trigger_dual_sourcing) when a PO has
    # both a low Z-score supplier AND single-source dependency >70%.
    # Both have priority=1 — tie-breaking order depends on list position here,
    # which is a known limitation of the current services/policy.py resolver.
    # See smoke-test report flag RF-3.
    # =========================================================================

    @property
    def policies(self) -> List[DomainPolicy]:
        return [
            DomainPolicy(
                id="POLICY-PROC-001",
                name="Auto-Approve Tier-1 POs Under $150K",
                rule=(
                    "Automatically approve purchase orders under $150,000 "
                    "from tier-1 approved suppliers with no price variance"
                ),
                priority=3,
                action_override="auto_approve_po",
            ),
            DomainPolicy(
                id="POLICY-COST-002",
                name="Flag Price Above Contract",
                rule=(
                    "Flag for manual review if unit price is more than 10% "
                    "above the contracted benchmark price"
                ),
                priority=2,
                action_override="flag_for_review",
            ),
            DomainPolicy(
                id="POLICY-RISK-003",
                name="Review Risky Suppliers",
                rule=(
                    "Require manual review if supplier credit Z-score "
                    "is below 2.5 — indicates elevated default/disruption risk"
                ),
                priority=1,              # ← priority 1 (ties with POLICY-DUAL-004)
                action_override="flag_for_review",
            ),
            DomainPolicy(
                id="POLICY-DUAL-004",
                name="Require Dual-Source for Concentrated Supply",
                rule=(
                    "Trigger dual-sourcing process if single-supplier "
                    "dependency share exceeds 70% for any item"
                ),
                priority=1,              # ← priority 1 (ties with POLICY-RISK-003)
                action_override="trigger_dual_sourcing",
            ),
        ]

    # =========================================================================
    # Asymmetry ratio
    # 12.0 — procurement errors (wrong auto-approve) are costly but recoverable;
    # lower than SOC's 20.0 because procurement has audit trails and reversals.
    # =========================================================================

    @property
    def asymmetry_ratio(self) -> float:
        return 12.0

    # =========================================================================
    # Prompt variants (4)
    # Tracked by AgentEvolver. Two families: PO_APPROVAL, RISK_ASSESSMENT.
    # =========================================================================

    @property
    def prompt_variants(self) -> List[PromptVariant]:
        return [
            PromptVariant(
                id="PO_APPROVAL_v1",
                category="routine_reorder",
                version=1,
                description="Base PO approval prompt — price and supplier tier only",
            ),
            PromptVariant(
                id="PO_APPROVAL_v2",
                category="routine_reorder",
                version=2,
                description="Enhanced PO approval with spend history and seasonality context",
            ),
            PromptVariant(
                id="RISK_ASSESSMENT_v1",
                category="supply_risk",
                version=1,
                description="Base supplier risk assessment prompt — Z-score and delivery rate",
            ),
            PromptVariant(
                id="RISK_ASSESSMENT_v2",
                category="supply_risk",
                version=2,
                description="Enhanced risk assessment with geopolitical and alternative-supplier context",
            ),
        ]

    # =========================================================================
    # Metrics config
    # NOTE: base.py DomainConfig.metrics_config docstring lists SOC-specific
    # keys (hrs_saved_monthly, mttr_reduction_pct, backlog_eliminated).
    # S2P uses domain-appropriate keys. The interface allows any Dict — the
    # SOC-specific key names in the docstring are documentation debt (RF-1).
    # =========================================================================

    @property
    def metrics_config(self) -> Dict:
        return {
            "po_auto_approved_monthly": 340,    # POs processed without human touch
            "cost_avoided_quarterly":   210000, # contract savings + overpay prevention
            "cycle_time_reduction_pct": 65,     # PO cycle time: 4.2 days → 1.5 days
            "supplier_risk_mitigated":  47,     # at-risk single-source items resolved
        }

    # =========================================================================
    # Stubs — not yet implemented
    # These would live in supply_chain/situations.py, supply_chain/factors.py,
    # supply_chain/seed_neo4j.py, etc. in a future prompt.
    # =========================================================================

    def classify_situation(self, po_type: str, context: Dict[str, Any]) -> str:
        """Classify a PO situation into one of the 6 S2P situation types."""
        raise NotImplementedError(
            "S2P situation classification not yet implemented. "
            "Create domains/supply_chain/situations.py."
        )

    def compute_factors(self, po_id: str, context: Dict[str, Any]) -> List[Dict]:
        """Compute the 6-dimensional factor vector for a Purchase Order."""
        raise NotImplementedError(
            "S2P factor computation not yet implemented. "
            "Create domains/supply_chain/factors.py."
        )

    def get_seed_queries(self) -> List[str]:
        # TODO: Create domains/supply_chain/seed_neo4j.py in a future prompt
        return []

    def get_graph_query_templates(self) -> Dict[str, str]:
        # TODO: Create S2P Cypher templates in a future prompt
        return {}

    def get_narration_templates(self) -> Dict[str, str]:
        # TODO: Create S2P LLM prompt templates in a future prompt
        return {}


# Singleton instance used by domain_registry.py
s2p_config = S2PDomainConfig()
