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

import numpy as np
from gae.profile_scorer import ProfileScorer, build_profile_scorer, KernelType
from gae.calibration import CalibrationProfile

from app.domains.base import (
    DomainConfig, DomainAction, DomainFactor,
    DomainSituationType, DomainPolicy, PromptVariant,
)
from app.domains.soc.factors import (
    TravelMatchFactor, AssetCriticalityFactor, ThreatIntelEnrichmentFactor,
    PatternHistoryFactor, TimeAnomalyFactor, DeviceTrustFactor,
)
from typing import Dict, List


# ── v5.0 ProfileScorer Configuration ────────────────────────────────
# 6 SOC categories (rows), 4 actions (cols), 6 factors (depth)
# Factor order: [travel_match, asset_criticality, threat_intel_enrichment,
#                pattern_history, time_anomaly, device_trust]
# Action order: [escalate, investigate, suppress, monitor]
# Centroid values: what each action looks like for each category.
# Discriminative factors: >0.8 (strong signal) or <0.2 (strong absence)
# Non-discriminative factors: 0.3-0.6 (moderate)
# τ=0.1 (V3B validated ECE=0.036). Never use 0.25.
# ─────────────────────────────────────────────────────────────────────

# refer_to_analyst: 5th action (v5.5). Graduated dispatch — medium-confidence
# situations where the system is not confident enough to act autonomously.
# Activation requires confidence band + margin gate — see ReferralPolicy.
# Centroid values: LLM judge consensus (Opus-derived), March 2026.
SOC_ACTIONS = ["escalate", "investigate", "suppress", "monitor", "refer_to_analyst"]

# Controls whether ProfileScorer.update() is called after verified outcomes.
# Default False (frozen scorer). Set True per-customer after shadow mode
# validates that learning improves outcomes.
LEARNING_ENABLED = False

SOC_CATEGORIES = [
    "credential_access",
    "threat_intel_match",
    "lateral_movement",
    "data_exfiltration",
    "insider_threat",
    "cloud_infrastructure",
]

# Bootstrap category weights — reflects realistic SOC alert distribution.
# credential_access and lateral_movement are most frequent.
# cloud_infrastructure and threat_intel_match are least frequent.
# Weights must sum to 1.0.
BOOTSTRAP_CATEGORY_WEIGHTS = {
    "credential_access":    0.30,
    "lateral_movement":     0.20,
    "data_exfiltration":    0.15,
    "insider_threat":       0.15,
    "cloud_infrastructure": 0.10,
    "threat_intel_match":   0.10,
}

# Shape: (6 categories, 5 actions, 6 factors) = 180 values
# Action index: 0=escalate, 1=investigate, 2=suppress, 3=monitor, 4=refer_to_analyst
# Factor index: 0=travel_match, 1=asset_criticality, 2=threat_intel_enrichment,
#               3=pattern_history, 4=time_anomaly, 5=device_trust
SOC_FACTORS = [
    "travel_match",
    "asset_criticality",
    "threat_intel_enrichment",
    "pattern_history",
    "time_anomaly",
    "device_trust",
]

# Bootstrap calibration parameters (GAE-BOOT-1)
# Used by gae_state.init_learning_state() on cold start or legacy checkpoint.
# Values validated against V3B ECE benchmark.
SOC_BOOTSTRAP_ROUNDS = 10
SOC_BOOTSTRAP_SAMPLES_PER_ACTION = 5
SOC_BOOTSTRAP_SIGMA = 0.08
SOC_BOOTSTRAP_CONVERGENCE_TOL = 0.01
SOC_BOOTSTRAP_SEED = 42

SOC_PROFILE_CENTROIDS = np.array([

  # ── Category 0: credential_access ──────────────────────────────
  [
    # escalate: travel anomaly + high asset + high threat_intel + low device_trust
    [0.72, 0.85, 0.80, 0.60, 0.65, 0.15],
    # investigate: moderate signals, some pattern history
    [0.40, 0.60, 0.55, 0.55, 0.50, 0.40],
    # suppress: low threat, normal hours, trusted device
    [0.20, 0.25, 0.15, 0.20, 0.25, 0.85],
    # monitor: moderate asset, low threat, normal pattern
    [0.30, 0.45, 0.25, 0.35, 0.35, 0.65],
    # refer_to_analyst: moderate travel, moderate asset, weak TI, moderate pattern/time,
    # somewhat trusted device. "Might be VPN login ambiguity — quick analyst glance."
    [0.35, 0.52, 0.35, 0.43, 0.42, 0.55],
  ],

  # ── Category 1: threat_intel_match ─────────────────────────────
  [
    # escalate: high threat_intel + high asset_criticality
    [0.35, 0.80, 0.90, 0.55, 0.60, 0.20],
    # investigate: confirmed intel but lower asset risk
    [0.30, 0.55, 0.75, 0.50, 0.50, 0.40],
    # suppress: false positive intel, trusted device
    [0.20, 0.20, 0.20, 0.15, 0.20, 0.90],
    # monitor: low-confidence intel match
    [0.25, 0.40, 0.45, 0.30, 0.35, 0.70],
    # refer_to_analyst: TI signal present but not strong, weak corroboration,
    # moderate device trust. "IOC correlation exists but context is mixed — analyst validates."
    # NOTE: Activation policy overrides if threat_intel_enrichment > 0.50.
    [0.27, 0.47, 0.53, 0.38, 0.42, 0.58],
  ],

  # ── Category 2: lateral_movement ───────────────────────────────
  [
    # escalate: strong pattern history + high asset
    [0.50, 0.80, 0.70, 0.85, 0.70, 0.20],
    # investigate: some lateral signals, moderate asset
    [0.45, 0.60, 0.50, 0.65, 0.55, 0.40],
    # suppress: travel explains movement, trusted device
    [0.85, 0.25, 0.15, 0.20, 0.25, 0.80],
    # monitor: single hop, low asset, normal hours
    [0.40, 0.40, 0.30, 0.40, 0.35, 0.65],
    # refer_to_analyst: moderate internal traversal, moderate pattern, weak TI,
    # somewhat trusted. "Some east-west movement but no strong indicators — check it."
    [0.43, 0.48, 0.38, 0.50, 0.43, 0.55],
  ],

  # ── Category 3: data_exfiltration ──────────────────────────────
  [
    # escalate: high asset + threat_intel + anomaly
    [0.30, 0.90, 0.75, 0.70, 0.80, 0.15],
    # investigate: high asset but unclear intent
    [0.35, 0.75, 0.50, 0.55, 0.60, 0.45],
    # suppress: authorized transfer, trusted device, normal hours
    [0.20, 0.30, 0.10, 0.15, 0.20, 0.90],
    # monitor: low-value asset, no threat intel
    [0.25, 0.40, 0.25, 0.30, 0.35, 0.70],
    # refer_to_analyst: conservative placement — exfil is highest-consequence category.
    # Moderate asset, low TI, moderate timing. Largest escalate distance (0.810).
    # NOTE: Activation policy overrides if asset_criticality > 0.70 AND time_anomaly > 0.60.
    [0.28, 0.55, 0.35, 0.40, 0.45, 0.55],
  ],

  # ── Category 4: insider_threat ─────────────────────────────────
  [
    # escalate: pattern history + time anomaly + low device_trust
    [0.40, 0.75, 0.65, 0.85, 0.80, 0.15],
    # investigate: behavioral signals, moderate confidence
    [0.45, 0.60, 0.50, 0.70, 0.60, 0.40],
    # suppress: explainable behavior, trusted device
    [0.30, 0.25, 0.15, 0.20, 0.20, 0.85],
    # monitor: weak signals, normal hours
    [0.35, 0.40, 0.30, 0.45, 0.35, 0.65],
    # refer_to_analyst: pattern moderately elevated (insider's defining factor),
    # moderate time anomaly. "Behavioral deviation but not conclusive — human judgment."
    # NOTE: Activation policy overrides if pattern_history > 0.70 AND time_anomaly > 0.70.
    [0.38, 0.48, 0.38, 0.55, 0.45, 0.55],
  ],

  # ── Category 5: cloud_infrastructure ───────────────────────────
  [
    # escalate: high asset + threat_intel + time_anomaly
    [0.25, 0.85, 0.80, 0.60, 0.75, 0.20],
    # investigate: cloud anomaly, moderate signals
    [0.30, 0.65, 0.55, 0.50, 0.55, 0.45],
    # suppress: scheduled maintenance, trusted source
    [0.20, 0.25, 0.10, 0.15, 0.20, 0.90],
    # monitor: low-risk cloud activity
    [0.25, 0.45, 0.30, 0.30, 0.35, 0.70],
    # refer_to_analyst: cloud misconfig with moderate asset, moderate TI,
    # trusted-ish device. "Posture finding on known service account — analyst sanity check."
    [0.27, 0.53, 0.40, 0.38, 0.43, 0.58],
  ],

], dtype=np.float64)

# Auto-approve thresholds (Finding II: monitor excluded permanently)
# escalate:          100.0% accuracy in band — safe at 0.90
# investigate:        92.2% [90.8%, 93.5%] — passes 90% target
# suppress:           99.9% [99.7%, 100%] — exceptionally safe
# monitor:            86.0% — EXCLUDED, never reaches 99% at any threshold
# refer_to_analyst:   EXCLUDED — always routes to human_review by design (v5.5)
SOC_AUTO_APPROVE_THRESHOLDS = {
    "escalate":          0.90,
    "investigate":       0.90,
    "suppress":          0.90,
    "monitor":           None,   # excluded from auto-approve
    "refer_to_analyst":  None,   # excluded — explicit human dispatch (v5.5)
}

# Category confidence floors (Finding LL: credential_access warrants caution)
SOC_CATEGORY_CONFIDENCE_FLOORS = {
    "credential_access": 0.95,
}

# Elevated agent zone categories (62% + 34% of dangerous errors)
SOC_AGENT_ZONE_ELEVATED = {
    "threat_intel_match":   True,
    "cloud_infrastructure": True,
}

# All 19 known alert_types mapped to their correct SOC category.
# Source: CORR-1 diagnostic, March 14, 2026.
# When adding new alert_types: add them HERE, not inline.
ALERT_TYPE_CATEGORY_MAP: dict = {
    # credential_access
    "anomalous_login":              "credential_access",
    "ambiguous_login_location":     "credential_access",
    "brute_force":                  "credential_access",
    "credential_stuffing":          "credential_access",

    # threat_intel_match
    "threat_intel_match":           "threat_intel_match",
    "phishing":                     "threat_intel_match",
    "malware_detection":            "threat_intel_match",
    "c2_beacon":                    "threat_intel_match",

    # lateral_movement
    "privilege_escalation":         "lateral_movement",
    "internal_scan_ambiguous":      "lateral_movement",

    # data_exfiltration
    "data_exfil":                   "data_exfiltration",

    # insider_threat
    "insider_threat":               "insider_threat",
    "anomalous_behavior":           "insider_threat",

    # cloud_infrastructure
    "cloud_config":                      "cloud_infrastructure",
    "cloud_iam_privilege_escalation":    "cloud_infrastructure",
    "cloud_storage_public_exposure":     "cloud_infrastructure",
    "cloud_config_drift":                "cloud_infrastructure",
    "cloud_unused_resource_anomaly":     "cloud_infrastructure",
    "cloud_permission_change_review":    "cloud_infrastructure",
}

DEFAULT_CATEGORY = "credential_access"  # emergency fallback only


def resolve_alert_category(alert_type: str) -> str:
    """Map an alert_type string to its SOC category.

    Uses ALERT_TYPE_CATEGORY_MAP for explicit mapping.
    Falls back to DEFAULT_CATEGORY with ERROR logging if unmapped.

    This function is the SINGLE routing point. Never resolve alert_type
    to category anywhere else in the codebase.
    """
    import logging
    _logger = logging.getLogger(__name__)

    category = ALERT_TYPE_CATEGORY_MAP.get(alert_type)
    if category is None:
        _logger.error(
            "ROUTING_FAILURE: alert_type=%r has no mapping in "
            "ALERT_TYPE_CATEGORY_MAP. Using fallback %r. "
            "Add this alert_type to ALERT_TYPE_CATEGORY_MAP in config.py.",
            alert_type,
            DEFAULT_CATEGORY,
        )
        category = DEFAULT_CATEGORY
    return category


# Category → canonical ATT&CK pattern for outcome feedback
# These are the patterns seeded in the graph (seed_neo4j.py)
CATEGORY_PATTERN_MAP = {
    "credential_access":    "PAT-CRED-001",
    "threat_intel_match":   "PAT-THREAT-001",
    "lateral_movement":     "PAT-LATERAL-001",
    "data_exfiltration":    "PAT-EXFIL-001",
    "insider_threat":       "PAT-INSIDER-001",
    "cloud_infrastructure": "PAT-CLOUD-001",
    # Fallback for unknown categories
    "_default":             "PAT-UNKNOWN-001",
}


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
    # GAE factor computers — all 6 SOC FactorComputer implementations
    # Reference: docs/soc_copilot_design_v1.md §14
    # =========================================================================

    def get_profile_centroids(self) -> np.ndarray:
        """
        Return profile centroids for ProfileScorer.
        Shape: (n_categories, n_actions, n_factors) = (6, 4, 6).
        τ=0.1 validated (V3B ECE=0.036).
        """
        return SOC_PROFILE_CENTROIDS.copy()

    def get_categories(self) -> list:
        """Return ordered category names."""
        return list(SOC_CATEGORIES)

    def get_category_index(self, category: str) -> int:
        """Return index for a category name. Raises ValueError if unknown."""
        try:
            return SOC_CATEGORIES.index(category)
        except ValueError:
            raise ValueError(
                f"Unknown SOC category: {category!r}. "
                f"Valid: {SOC_CATEGORIES}"
            )

    def get_auto_approve_threshold(self, action: str):
        """
        Return auto-approve confidence threshold for action.
        Returns None if action is excluded from auto-approve (monitor).
        """
        return SOC_AUTO_APPROVE_THRESHOLDS.get(action)

    def get_pattern_for_category(self, category: str) -> str:
        """
        Return the canonical ATT&CK pattern ID for an alert category.
        Used by process_outcome() to return category-appropriate patterns.
        Falls back to _default if category unknown.
        """
        return CATEGORY_PATTERN_MAP.get(category,
               CATEGORY_PATTERN_MAP["_default"])

    def build_profile_scorer(self) -> ProfileScorer:
        """
        Build a ProfileScorer from this domain config.
        Uses L2 kernel (EXP-E1 validated), τ=0.1 (V3B validated, default).
        Tensor shape: (6 categories, 5 actions, 6 factors) = 180 values (v5.5).
        """
        return ProfileScorer(
            mu=self.get_profile_centroids(),
            actions=self.get_actions(),
            kernel=KernelType.L2,
            categories=list(SOC_CATEGORIES),
        )

    @staticmethod
    def get_actions() -> List[str]:
        """
        Five GAE action names in W-matrix row order (v5.5).
        Row 0=escalate, 1=investigate, 2=suppress, 3=monitor, 4=refer_to_analyst.
        Must stay in sync with get_initial_W() row order and SOC_PROFILE_CENTROIDS axis 1.
        """
        return list(SOC_ACTIONS)

    @staticmethod
    def get_factor_computers() -> List:
        """Return ordered list of all 6 SOC FactorComputer instances."""
        return [
            TravelMatchFactor(),
            AssetCriticalityFactor(),
            ThreatIntelEnrichmentFactor(),
            PatternHistoryFactor(),
            TimeAnomalyFactor(),
            DeviceTrustFactor(),
        ]

    # =========================================================================
    # GAE weight matrix and temperature
    # Reference: docs/soc_copilot_design_v1.md §14
    # =========================================================================

    @staticmethod
    def get_initial_W():
        """Initial weight matrix (5 actions x 6 factors). Security expert priors (v5.5)."""
        import numpy as np
        return np.array([
            # travel  asset  threat  pattern  time  device
            [ 0.8,   0.9,    0.9,    0.3,    0.4,   0.3],   # escalate
            [ 0.5,   0.5,    0.7,    0.5,    0.6,   0.5],   # investigate
            [-0.3,  -0.2,   -0.5,    0.7,   -0.3,  -0.2],   # suppress
            [ 0.2,   0.3,    0.4,    0.4,    0.3,   0.4],   # monitor
            [ 0.1,   0.4,    0.3,    0.4,    0.3,   0.4],   # refer_to_analyst: conservative moderate
        ], dtype=np.float64)

    # τ=0.1 (V3B validated, ECE=0.036). NEVER return 0.25.
    # Prior value of 0.25 was a pre-V3B default that was never updated after TD-030.
    # This affects simulation scoring — all prior simulation runs used wrong τ.
    @staticmethod
    def get_temperature() -> float:
        return 0.1

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
