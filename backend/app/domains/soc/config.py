"""SOC domain configuration. All SOC-specific constants live here.

Constants are extracted from the existing service files — nothing is invented:
  factors        ← services/triage.py  _ALERT_FACTORS factor name list
  actions        ← services/agent.py   ACTION_* constants
                   services/situation.py evaluate_options() economics
  situation_types← services/situation.py SituationType enum
  policies       ← services/policy.py  POLICY_REGISTRY
  asymmetry_ratio← services/feedback.py get_reward_summary() asymmetric_ratio
  prompt_variants← services/evolver.py  PROMPT_STATS keys
  metrics_config ← routers/metrics.py   BusinessImpact values
"""

from app.domains.base import (
    DomainConfig, DomainAction, DomainFactor,
    DomainSituationType, DomainPolicy, PromptVariant,
)
from typing import Dict, List


class SOCDomainConfig(DomainConfig):
    """Security Operations Center domain module."""

    # =========================================================================
    # Identity
    # =========================================================================

    @property
    def name(self) -> str:
        return "soc"

    @property
    def display_name(self) -> str:
        return "SOC Copilot"

    @property
    def trigger_entity(self) -> str:
        return "Alert"

    # =========================================================================
    # Factors
    # Source: services/triage.py — _ALERT_FACTORS["ALERT-7823"] name list +
    #         _build_threat_intel_factor() for the live factor at index 2.
    # Final factor order (from get_decision_factors docstring):
    #   [0] travel_match
    #   [1] asset_criticality
    #   [2] threat_intel_enrichment  (live Neo4j query)
    #   [3] time_anomaly
    #   [4] device_trust
    #   [5] pattern_history
    # =========================================================================

    @property
    def factors(self) -> List[DomainFactor]:
        return [
            DomainFactor(
                id="travel_match",
                label="Travel Match",
                description=(
                    "Employee calendar shows travel — VPN origin matches destination"
                ),
            ),
            DomainFactor(
                id="asset_criticality",
                label="Asset Criticality",
                description=(
                    "Target asset business impact and blast radius if action is wrong"
                ),
            ),
            DomainFactor(
                id="threat_intel_enrichment",
                label="Threat Intel Enrichment",
                description=(
                    "Live IOC match against threat intelligence feeds via Neo4j "
                    "ASSOCIATED_WITH relationship"
                ),
            ),
            DomainFactor(
                id="time_anomaly",
                label="Time Anomaly",
                description=(
                    "Login or activity time deviation from user baseline "
                    "(e.g. 3 AM home timezone)"
                ),
            ),
            DomainFactor(
                id="device_trust",
                label="Device Trust",
                description=(
                    "Device MDM enrollment, fingerprint match, and corporate posture score"
                ),
            ),
            DomainFactor(
                id="pattern_history",
                label="Pattern History",
                description=(
                    "Historical pattern match count and false positive rate "
                    "(e.g. PAT-TRAVEL-001: 127 cases)"
                ),
            ),
        ]

    # =========================================================================
    # Actions
    # Source: services/agent.py ACTION_* constants (5 actions total).
    # time_saved_min and cost_dollars: representative values from
    # services/situation.py evaluate_options() estimated_resolution_time and
    # estimated_analyst_cost fields.
    # =========================================================================

    @property
    def actions(self) -> List[DomainAction]:
        return [
            DomainAction(
                id="false_positive_close",
                label="Close as False Positive",
                time_saved_min=0.05,   # "3 seconds" — TRAVEL_LOGIN_ANOMALY option
                cost_dollars=0.0,
                risk_level="low",
            ),
            DomainAction(
                id="auto_remediate",
                label="Auto-Remediate",
                time_saved_min=0.13,   # "8 seconds" — KNOWN_PHISHING_CAMPAIGN option
                cost_dollars=0.0,
                risk_level="low",
            ),
            DomainAction(
                id="enrich_and_wait",
                label="Enrich and Wait",
                time_saved_min=20.0,   # "20 minutes" — VIP_AFTER_HOURS option
                cost_dollars=62.0,
                risk_level="low",
            ),
            DomainAction(
                id="escalate_tier2",
                label="Escalate to Tier 2",
                time_saved_min=45.0,   # "45 minutes" — TRAVEL_LOGIN_ANOMALY option
                cost_dollars=127.0,
                risk_level="none",
            ),
            DomainAction(
                id="escalate_incident",
                label="Escalate to Incident",
                time_saved_min=120.0,  # "2 hours" — MALWARE_ON_CRITICAL_ASSET option
                cost_dollars=310.0,
                risk_level="none",
            ),
        ]

    # =========================================================================
    # Situation types
    # Source: services/situation.py SituationType enum (6 members).
    # IDs: enum names (uppercase, as used in comparisons throughout the code).
    # Colors: chosen to match Tab 3 badge color coding (CLAUDE.md Wave 4).
    # =========================================================================

    @property
    def situation_types(self) -> List[DomainSituationType]:
        return [
            DomainSituationType(
                id="TRAVEL_LOGIN_ANOMALY",
                label="Travel Login Anomaly",
                description=(
                    "Anomalous login where user travel record and VPN location align — "
                    "likely a false positive"
                ),
                color="#3B82F6",  # blue
            ),
            DomainSituationType(
                id="KNOWN_PHISHING_CAMPAIGN",
                label="Known Phishing Campaign",
                description=(
                    "Email matches a known phishing campaign signature in the pattern library"
                ),
                color="#F97316",  # orange
            ),
            DomainSituationType(
                id="MALWARE_ON_CRITICAL_ASSET",
                label="Malware on Critical Asset",
                description=(
                    "Malware detected on a critical or production system — "
                    "immediate incident response required"
                ),
                color="#EF4444",  # red
            ),
            DomainSituationType(
                id="VIP_AFTER_HOURS",
                label="VIP After Hours",
                description=(
                    "Executive-level user activity outside normal business hours — "
                    "requires careful verification before escalation"
                ),
                color="#EAB308",  # yellow
            ),
            DomainSituationType(
                id="DATA_EXFIL_ATTEMPT",
                label="Data Exfiltration Attempt",
                description=(
                    "Unusual data transfer to an external destination above volume threshold — "
                    "forensics required"
                ),
                color="#DC2626",  # dark red
            ),
            DomainSituationType(
                id="UNKNOWN",
                label="Unknown",
                description=(
                    "Insufficient context for automated classification — "
                    "manual Tier 2 review recommended"
                ),
                color="#6B7280",  # gray
            ),
        ]

    # =========================================================================
    # Policies
    # Source: services/policy.py POLICY_REGISTRY (all 4 entries).
    # rule: maps to PolicyDefinition.description.
    # priority: matches PolicyDefinition.priority (1 = highest).
    # action_override: matches PolicyDefinition.action.
    # =========================================================================

    @property
    def policies(self) -> List[DomainPolicy]:
        return [
            DomainPolicy(
                id="POL-AUTO-CLOSE-TRAVEL",
                name="Auto-Close Travel Anomalies",
                rule=(
                    "Automatically close login anomaly alerts when user is traveling "
                    "and VPN matches travel destination"
                ),
                priority=3,
                action_override="false_positive_close",
            ),
            DomainPolicy(
                id="POL-ESCALATE-HIGH-RISK",
                name="Escalate High-Risk Users",
                rule=(
                    "Escalate all alerts for users with risk score above 0.80 "
                    "to Tier 2 analysts"
                ),
                priority=1,
                action_override="escalate_tier2",
            ),
            DomainPolicy(
                id="POL-REMEDIATE-KNOWN-PHISH",
                name="Auto-Remediate Known Phishing",
                rule=(
                    "Automatically remediate phishing alerts that match "
                    "known campaign signatures"
                ),
                priority=2,
                action_override="auto_remediate",
            ),
            DomainPolicy(
                id="POL-ISOLATE-CRITICAL-ASSETS",
                name="Isolate Critical Assets",
                rule=(
                    "Immediately isolate any malware detection "
                    "on critical infrastructure"
                ),
                priority=1,
                action_override="auto_remediate",
            ),
        ]

    # =========================================================================
    # Asymmetry ratio
    # Source: services/feedback.py get_reward_summary()
    #   "asymmetric_ratio": 20.0
    #   correct → +0.3, incorrect → -6.0  (6.0 / 0.3 = 20.0)
    # =========================================================================

    @property
    def asymmetry_ratio(self) -> float:
        return 20.0

    # =========================================================================
    # Prompt variants
    # Source: services/evolver.py PROMPT_STATS dict keys (4 variants).
    # category: derived from family prefix (TRAVEL_CONTEXT → anomalous_login,
    #           PHISHING_RESPONSE → phishing).
    # version: numeric suffix after _v.
    # =========================================================================

    @property
    def prompt_variants(self) -> List[PromptVariant]:
        return [
            PromptVariant(
                id="TRAVEL_CONTEXT_v1",
                category="anomalous_login",
                version=1,
                description="Base travel context prompt (71% success rate)",
            ),
            PromptVariant(
                id="TRAVEL_CONTEXT_v2",
                category="anomalous_login",
                version=2,
                description="Improved travel context prompt with VPN+calendar correlation (89% success rate)",
            ),
            PromptVariant(
                id="PHISHING_RESPONSE_v1",
                category="phishing",
                version=1,
                description="Base phishing response prompt — active (82% success rate)",
            ),
            PromptVariant(
                id="PHISHING_RESPONSE_v2",
                category="phishing",
                version=2,
                description="Experimental phishing response prompt — monitoring (80% success rate)",
            ),
        ]

    # =========================================================================
    # Metrics config
    # Source: routers/metrics.py BusinessImpact values in generate_compounding_data()
    # =========================================================================

    @property
    def metrics_config(self) -> Dict:
        return {
            "hrs_saved_monthly":       847,    # ~200 auto-closed alerts × 45 min manual review avoided
            "cost_avoided_quarterly":  127000, # analyst_hours × $50/hr × 3 months
            "mttr_reduction_pct":      75,     # MTTR improved from 12.4 min → 3.1 min
            "backlog_eliminated":      2400,   # alerts no longer waiting for human review
        }

    # =========================================================================
    # Stubs — extracted in later prompts
    # =========================================================================

    def get_seed_queries(self) -> List[str]:
        # TODO: Extract from services/seed_neo4j.py in a later prompt
        return []

    def get_graph_query_templates(self) -> Dict[str, str]:
        # TODO: Extract from db/neo4j.py and routers/soc.py in a later prompt
        return {}

    def get_narration_templates(self) -> Dict[str, str]:
        # TODO: Extract from services/reasoning.py in a later prompt
        return {}


# Singleton instance used by domain_registry.py
soc_config = SOCDomainConfig()
