"""
SOC referral rules R1-R7.

Each rule implements the gae.referral.ReferralRule protocol:
  - rule_id: str property
  - reason: ReferralReason property
  - evaluate(alert_context: dict) -> (bool, dict)

Rules are pure functions — no state, no ML, no side effects.
Missing context keys → rule does not fire (safe degradation, not dangerous).

Validated in EXP-REFER-LAYERED: 72.7% DR, 12% FPR, 978 net min/100 alerts.
Confidence gate REJECTED for referral (14% precision = active harm).
Rules are the primary referral mechanism.

Reference: docs/soc_copilot_design_v1.md §referral; EXP-REFER-LAYERED.
"""

from typing import List, Optional, Tuple

from gae.referral import ReferralReason


# ------------------------------------------------------------------ #
# R1: Executive Account                                               #
# ------------------------------------------------------------------ #

class ExecutiveAccountRule:
    """
    R1: Fires if the alert involves an identity tier requiring human review.

    Executives, board members, and C-suite accounts carry legal and
    reputational risk that automated action cannot adequately address.
    Configurable tiers allow customer override during onboarding.
    """

    def __init__(self, tiers: Optional[List[str]] = None) -> None:
        self._tiers = set(tiers) if tiers else {'executive', 'board', 'c_suite'}

    @property
    def rule_id(self) -> str:
        return "R1"

    @property
    def reason(self) -> ReferralReason:
        return ReferralReason.EXECUTIVE_ACCOUNT

    def evaluate(self, alert_context: dict) -> Tuple[bool, dict]:
        tier = alert_context.get('identity_tier', 'standard')
        fires = tier in self._tiers
        detail = {'identity_tier': tier, 'trigger_tiers': sorted(self._tiers)} if fires else {}
        return fires, detail


# ------------------------------------------------------------------ #
# R2: Rapid Succession                                               #
# ------------------------------------------------------------------ #

class RapidSuccessionRule:
    """
    R2: Fires if the same source entity has generated >= threshold alerts
    within the recent window.

    High-frequency alert generation from a single source is a strong
    indicator of either an active attack or a misconfigured asset —
    both warrant analyst review.
    """

    def __init__(self, threshold: int = 3, window: int = 20) -> None:
        self._threshold = threshold
        self._window = window

    @property
    def rule_id(self) -> str:
        return "R2"

    @property
    def reason(self) -> ReferralReason:
        return ReferralReason.RAPID_SUCCESSION

    def evaluate(self, alert_context: dict) -> Tuple[bool, dict]:
        sequence_count = alert_context.get('sequence_count', 0)
        fires = sequence_count >= self._threshold
        detail = (
            {'sequence_count': sequence_count, 'threshold': self._threshold,
             'window': self._window}
            if fires else {}
        )
        return fires, detail


# ------------------------------------------------------------------ #
# R3: Compliance Mandate                                             #
# ------------------------------------------------------------------ #

class ComplianceMandateRule:
    """
    R3: Fires if the alert category is in the compliance-mandated list
    AND compliance_mode is enabled.

    Some alert categories (e.g. insider_threat) require human sign-off
    under regulatory frameworks (SOX, HIPAA, SOC 2). Compliance mode
    is operator-controlled; when disabled the rule never fires.
    """

    def __init__(self, mandated_categories: Optional[List[str]] = None) -> None:
        self._mandated = set(mandated_categories) if mandated_categories else {'insider_threat'}

    @property
    def rule_id(self) -> str:
        return "R3"

    @property
    def reason(self) -> ReferralReason:
        return ReferralReason.COMPLIANCE_MANDATE

    def evaluate(self, alert_context: dict) -> Tuple[bool, dict]:
        category = alert_context.get('category', '')
        compliance_mode = alert_context.get('compliance_mode', False)
        fires = compliance_mode and category in self._mandated
        detail = (
            {'category': category, 'compliance_mode': compliance_mode,
             'mandated_categories': sorted(self._mandated)}
            if fires else {}
        )
        return fires, detail


# ------------------------------------------------------------------ #
# R4: High Value Data                                                #
# ------------------------------------------------------------------ #

class HighValueDataRule:
    """
    R4: Fires if a high-criticality asset receives a monitor or suppress
    recommendation in a data-sensitive category.

    NOTE: R4 has ~42.6% detection rate (EXP-REFER-COVERAGE) because it
    depends on Stage 1 action prediction. When Stage 1 correctly escalates,
    R4 does not fire — but the alert is already routed to a human. This is
    by design: R4 catches the cases where automation would silently suppress
    or monitor a high-value asset without escalation.

    Criticality threshold and trigger categories are configurable.
    """

    _DEFAULT_TRIGGER_ACTIONS = {'monitor', 'suppress'}
    _DEFAULT_TRIGGER_CATEGORIES = {'data_exfiltration', 'insider_threat'}

    def __init__(
        self,
        criticality_threshold: float = 0.85,
        trigger_actions: Optional[List[str]] = None,
        trigger_categories: Optional[List[str]] = None,
    ) -> None:
        self._threshold = criticality_threshold
        self._trigger_actions = (
            set(trigger_actions) if trigger_actions else self._DEFAULT_TRIGGER_ACTIONS
        )
        self._trigger_categories = (
            set(trigger_categories) if trigger_categories else self._DEFAULT_TRIGGER_CATEGORIES
        )

    @property
    def rule_id(self) -> str:
        return "R4"

    @property
    def reason(self) -> ReferralReason:
        return ReferralReason.HIGH_VALUE_DATA

    def evaluate(self, alert_context: dict) -> Tuple[bool, dict]:
        category = alert_context.get('category', '')
        asset_criticality = float(alert_context.get('asset_criticality', 0.0))
        stage1_action = alert_context.get('stage1_action', '')

        fires = (
            category in self._trigger_categories
            and asset_criticality > self._threshold
            and stage1_action in self._trigger_actions
        )
        detail = (
            {'category': category, 'asset_criticality': asset_criticality,
             'stage1_action': stage1_action, 'criticality_threshold': self._threshold}
            if fires else {}
        )
        return fires, detail


# ------------------------------------------------------------------ #
# R5: Active Incident                                                #
# ------------------------------------------------------------------ #

class ActiveIncidentRule:
    """
    R5: Fires if there is an active incident in progress.

    Alerts arriving during an active incident require analyst judgment
    to determine whether they are part of the same campaign or a
    separate event — a determination automation cannot safely make.
    """

    @property
    def rule_id(self) -> str:
        return "R5"

    @property
    def reason(self) -> ReferralReason:
        return ReferralReason.ACTIVE_INCIDENT

    def evaluate(self, alert_context: dict) -> Tuple[bool, dict]:
        incident_active = alert_context.get('incident_active', False)
        fires = bool(incident_active)
        detail = {'incident_active': incident_active} if fires else {}
        return fires, detail


# ------------------------------------------------------------------ #
# R6: New Asset                                                      #
# ------------------------------------------------------------------ #

class NewAssetRule:
    """
    R6: Fires if the involved asset was created recently (< age_threshold days).

    New assets have no behavioral baseline. Automated decisions about
    them carry higher false-positive risk until a baseline is established.
    Age threshold is configurable per deployment.
    """

    def __init__(self, age_threshold_days: int = 30) -> None:
        self._threshold = age_threshold_days

    @property
    def rule_id(self) -> str:
        return "R6"

    @property
    def reason(self) -> ReferralReason:
        return ReferralReason.NEW_ASSET

    def evaluate(self, alert_context: dict) -> Tuple[bool, dict]:
        asset_age_days = alert_context.get('asset_age_days', 365)
        fires = asset_age_days < self._threshold
        detail = (
            {'asset_age_days': asset_age_days, 'age_threshold_days': self._threshold}
            if fires else {}
        )
        return fires, detail


# ------------------------------------------------------------------ #
# R7: Cross-Category                                                 #
# ------------------------------------------------------------------ #

class CrossCategoryRule:
    """
    R7: Fires if the same user or entity has triggered alerts in multiple
    distinct categories within the recent window.

    Cross-category activity is a strong indicator of coordinated attack
    activity (lateral movement, privilege escalation, data exfiltration
    in sequence) that exceeds automated triage scope.
    """

    def __init__(self, threshold: int = 2) -> None:
        self._threshold = threshold

    @property
    def rule_id(self) -> str:
        return "R7"

    @property
    def reason(self) -> ReferralReason:
        return ReferralReason.CROSS_CATEGORY

    def evaluate(self, alert_context: dict) -> Tuple[bool, dict]:
        cross_category_count = alert_context.get('cross_category_count', 0)
        fires = cross_category_count >= self._threshold
        detail = (
            {'cross_category_count': cross_category_count, 'threshold': self._threshold}
            if fires else {}
        )
        return fires, detail


# ------------------------------------------------------------------ #
# Factory                                                            #
# ------------------------------------------------------------------ #

def get_soc_referral_rules() -> List:
    """
    Return all 7 SOC referral rules with default thresholds.

    Called by SOCDomainConfig.get_referral_rules().
    Customers can override thresholds during onboarding by constructing
    individual rules with custom parameters.

    Returns
    -------
    list
        All 7 rule instances implementing gae.referral.ReferralRule protocol.
    """
    return [
        ExecutiveAccountRule(),
        RapidSuccessionRule(),
        ComplianceMandateRule(),
        HighValueDataRule(),
        ActiveIncidentRule(),
        NewAssetRule(),
        CrossCategoryRule(),
    ]
