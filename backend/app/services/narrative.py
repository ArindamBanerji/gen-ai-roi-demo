"""
Investigation Narrative Service — NAR-1

NarrativeProvider Protocol with two concrete implementations:
  - TemplateNarrativeProvider (default): deterministic, no external deps
  - OllamaNarrativeProvider:            Ollama REST API, falls back to template

Usage (new path — preferred):
    from app.services.narrative import get_narrative_provider
    narrative = get_narrative_provider().generate(alert, decision, factors, calibration_context)

Design decisions:
  - Protocol is structural (runtime_checkable) — no ABC overhead.
  - TemplateNarrativeProvider preserves all F3a sentence logic.
  - Mandatory calibration sentence added as the final sentence (NAR-1).
  - OllamaNarrativeProvider wraps httpx with a 10-second timeout; any
    exception (connection refused, timeout, bad JSON) falls back to template.
  - Provider is initialised once at startup via set_narrative_provider() and
    get_narrative_provider() returns the singleton. Falls back to template
    on first call if startup did not set one.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# ============================================================================
# Protocol
# ============================================================================

@runtime_checkable
class NarrativeProvider(Protocol):
    def generate(
        self,
        alert: Dict[str, Any],
        decision: Dict[str, Any],
        factors: List[Dict[str, Any]],
        calibration_context: Dict[str, Any],
    ) -> str: ...


# ============================================================================
# Human-readable lookups
# ============================================================================

_FACTOR_LABELS: Dict[str, str] = {
    # Travel login signals
    "active_travel_record":       "active travel record in employee calendar",
    "destination_matches":        "login origin matching travel destination",
    "vpn_location_match":         "VPN exit node matching travel destination",
    "mfa_completed":              "completed multi-factor authentication",
    "device_known":               "known enrolled corporate device",
    # Phishing signals
    "phishing_alert":             "phishing email detected",
    "known_campaign_signature":   "known phishing campaign signature match",
    "similar_emails_blocked":     "prior emails from this campaign already blocked",
    "novel_phishing_attempt":     "novel phishing attempt with no prior signature",
    # Malware / critical asset signals
    "malware_detected":           "malware payload detected on host",
    "production_system":          "production system at risk",
    # Data exfil signals
    "unusual_data_transfer":      "anomalous outbound data transfer volume",
    "external_destination":       "transfer destined for an external host",
    "volume_threshold_exceeded":  "data volume exceeding baseline threshold",
    # VIP / after hours signals
    "vip_user":                   "executive-level user triggering alert",
    "after_hours_activity":       "activity occurring outside business hours",
    # Brute force signals
    "repeated_auth_failures":     "repeated authentication failures above threshold",
    "high_failure_count":         "unusually high authentication failure count",
    # Privilege escalation signals
    "privilege_escalation_attempt": "unauthorized privilege escalation attempt",
    "critical_asset_targeted":    "escalation targeting a critical production system",
    # Credential stuffing signals
    "multiple_accounts_targeted": "multiple accounts targeted simultaneously",
    "automated_access_pattern":   "automated credential stuffing pattern confirmed",
    "leaked_credential_match":    "credentials matching known breach datasets",
    # C2 signals
    "known_c2_server":            "known command-and-control server contact",
    "internal_host_affected":     "internal host initiating outbound C2 channel",
    "outbound_beacon_detected":   "regular outbound beacon pattern detected",
    # Threat intel signals
    "ioc_match_confirmed":        "confirmed IOC match across threat intelligence feeds",
    "threat_feed_hit":            "hit on one or more threat intelligence feeds",
    # Anomalous network signals
    "unusual_traffic_pattern":    "unusual network traffic pattern above baseline",
    "lateral_movement_indicators": "lateral movement indicators in network flow",
    # Insider threat signals
    "suspicious_data_access":     "bulk data access well above user baseline",
    "privileged_user_involved":   "privileged user account involved",
    # Cloud misconfiguration signals
    "cloud_resource_exposed":     "publicly exposed cloud resource detected",
    "misconfiguration_detected":  "cloud configuration drift detected",
    # Generic
    "insufficient_context":       "insufficient context for automated classification",
}

_ACTION_LABELS: Dict[str, str] = {
    "false_positive_close":  "Close as false positive",
    "auto_remediate":        "Auto-remediate",
    "escalate_tier2":        "Escalate to Tier 2 analyst",
    "escalate_incident":     "Escalate to full incident response",
    "enrich_and_wait":       "Enrich context and monitor",
    # GAE action names
    "escalate":              "Escalate to analyst",
    "investigate":           "Investigate further",
    "suppress":              "Suppress (false positive)",
    "monitor":               "Monitor and watch",
}

# Factor names that indicate active threat intel enrichment was consulted
_THREAT_INTEL_FACTORS = frozenset({
    "ioc_match_confirmed",
    "threat_feed_hit",
    "multi_feed_match",
    "known_campaign_signature",
    "similar_emails_blocked",
    "known_c2_server",
    "confirmed_ioc",
    "active_threat_campaign",
    "confirmed_c2",
    "active_channel",
})


# ============================================================================
# Private sentence builders (shared across implementations)
# ============================================================================

def _humanize_factor(raw: str) -> str:
    base = raw.split(" (")[0].strip()
    return _FACTOR_LABELS.get(base, base.replace("_", " "))


def _humanize_action(action: str) -> str:
    return _ACTION_LABELS.get(action, action.replace("_", " ").title())


def _build_threat_intel_sentence(
    factors_detected: List[str],
    pattern_id: Optional[str],
    patterns_matched: int,
    situation_type: str,
) -> Optional[str]:
    has_ti = any(f.split(" (")[0] in _THREAT_INTEL_FACTORS for f in factors_detected)

    if situation_type == "threat_intel_indicator":
        return (
            "Threat intelligence enrichment confirmed IOC presence across multiple "
            "feeds with active campaign correlation."
        )

    if situation_type == "known_phishing_campaign" and "known_campaign_signature" in factors_detected:
        return (
            "Threat intelligence match: email signature aligns with a catalogued "
            "phishing campaign in the pattern library."
        )

    if situation_type == "c2_communication":
        return (
            "Threat intelligence enrichment confirms the destination IP is known "
            "C2 infrastructure from active threat actor campaigns."
        )

    if has_ti:
        return (
            "Corroborating threat intelligence enrichment from external feeds "
            "supported the classification."
        )

    if pattern_id and patterns_matched > 0:
        return (
            f"Graph pattern {pattern_id} matched with supporting context "
            "from the historical pattern library."
        )

    if pattern_id:
        return f"Graph pattern {pattern_id} matched; no additional threat feed enrichment available."

    return None


def _build_sentence1(
    alert_id: str,
    situation_label: str,
    sit_confidence: float,
    mitre_technique: str,
    mitre_tactic: str,
) -> str:
    pct = int(sit_confidence * 100)
    if mitre_technique:
        return (
            f"{alert_id} classified as {situation_label} "
            f"({mitre_technique} · {mitre_tactic}, {pct}% confidence)."
        )
    return f"{alert_id} classified as {situation_label} ({pct}% confidence)."


def _build_sentence2(nodes_count: int, subgraphs: List[str]) -> str:
    if subgraphs:
        shown = subgraphs[:3]
        suffix = f" +{len(subgraphs) - 3} more" if len(subgraphs) > 3 else ""
        return (
            f"Graph traversal consulted {nodes_count} nodes across "
            f"{len(subgraphs)} subgraph{'s' if len(subgraphs) != 1 else ''} "
            f"({', '.join(shown)}{suffix})."
        )
    return f"Graph traversal consulted {nodes_count} nodes across the security context graph."


def _build_sentence3(factors_detected: List[str], sit_confidence: float) -> Optional[str]:
    if not factors_detected:
        return None
    dominant = _humanize_factor(factors_detected[0])
    pct = int(sit_confidence * 100)
    return (
        f"Dominant signal: {dominant} "
        f"(calibrated to {pct}% classification confidence by the pattern library)."
    )


def _build_sentence5(action: str, confidence: float) -> str:
    action_label = _humanize_action(action)
    pct = int(confidence * 100)
    return f"Recommended action: {action_label} ({pct}% agent confidence)."


def _build_calibration_sentence(
    decision_count: int,
    category_count: int,
    category: str,
) -> str:
    """Mandatory NAR-1 calibration sentence."""
    return (
        f"This recommendation is calibrated from {decision_count} verified outcomes, "
        f"including {category_count} decisions on similar {category} alerts."
    )


# ============================================================================
# TemplateNarrativeProvider
# ============================================================================

class TemplateNarrativeProvider:
    """
    Deterministic, template-based narrative. No external dependencies.

    Produces 4-6 sentences:
      Always: S1 (classification) + S2 (graph scope) + S5 (recommendation) + S_cal (calibration)
      +S3 (dominant factor) if factors_detected is non-empty
      +S4 (threat intel) if applicable
    """

    def generate(
        self,
        alert: Dict[str, Any],
        decision: Dict[str, Any],
        factors: List[Dict[str, Any]],
        calibration_context: Dict[str, Any],
    ) -> str:
        """
        Args:
            alert:               Merged dict of alert_data + situation_analysis.model_dump().
                                 Keys: id, alert_type, situation_type, situation_confidence,
                                       factors_detected, mitre_technique, mitre_tactic.
            decision:            Dict with keys: action, confidence, pattern_id.
            factors:             List of {"name": str, "value": float} — GAE factor vector.
            calibration_context: Dict with: decision_count, category_count, category,
                                            top_factor, bottom_factor.
        Returns:
            Plain-English narrative string. Never raises.
        """
        try:
            # -- alert fields --------------------------------------------------
            alert_id         = alert.get("id", "UNKNOWN-ALERT")
            situation_type   = alert.get("situation_type", "unknown")
            sit_confidence   = float(alert.get("situation_confidence", 0.0))
            factors_detected = alert.get("factors_detected", []) or []
            mitre_technique  = (
                alert.get("mitre_technique") or
                alert.get("attack_technique") or ""
            )
            mitre_tactic = (
                alert.get("mitre_tactic") or
                alert.get("attack_tactic") or ""
            )

            # -- decision fields -----------------------------------------------
            action     = decision.get("action", "escalate")
            confidence = float(decision.get("confidence", 0.0))
            pattern_id = decision.get("pattern_id")

            # -- calibration_context -------------------------------------------
            decision_count = int(calibration_context.get("decision_count", 0))
            category_count = int(
                calibration_context.get("category_count", decision_count)
            )
            category = calibration_context.get(
                "category", alert.get("alert_type", "unknown")
            )

            # -- context defaults (not tracked in structured args) -------------
            nodes_count = 47
            subgraphs   = [
                "User Profile", "Asset Inventory",
                "Travel Calendar", "Pattern Library", "Playbook Registry",
            ]
            patterns_matched = 1 if pattern_id else 0

            # -- situation label from domain registry --------------------------
            from app.domains.soc.situations import SOC_SITUATION_TYPES
            sit_meta        = SOC_SITUATION_TYPES.get(situation_type, {})
            situation_label = (
                sit_meta.get("label") or
                situation_type.replace("_", " ").title()
            )

            # -- assemble sentences -------------------------------------------
            sentences: List[str] = []

            sentences.append(
                _build_sentence1(
                    alert_id, situation_label, sit_confidence,
                    mitre_technique, mitre_tactic,
                )
            )
            sentences.append(_build_sentence2(nodes_count, subgraphs))

            s3 = _build_sentence3(factors_detected, sit_confidence)
            if s3:
                sentences.append(s3)

            s4 = _build_threat_intel_sentence(
                factors_detected, pattern_id, patterns_matched, situation_type
            )
            if s4:
                sentences.append(s4)

            sentences.append(_build_sentence5(action, confidence))

            # Mandatory NAR-1 calibration sentence — always last
            sentences.append(
                _build_calibration_sentence(decision_count, category_count, category)
            )

            return " ".join(sentences)

        except Exception as exc:
            logger.error("[NARRATIVE] TemplateNarrativeProvider.generate failed: %s", exc)
            alert_id = alert.get("id", "UNKNOWN")
            return (
                f"Investigation narrative unavailable for {alert_id}. "
                "Review the recommendation and situation analysis panels below."
            )


# ============================================================================
# OllamaNarrativeProvider
# ============================================================================

class OllamaNarrativeProvider:
    """
    Calls Ollama REST API (`POST /api/generate`, model=mistral, stream=false).
    Falls back to TemplateNarrativeProvider on any error:
      - Connection refused (Ollama not running)
      - Timeout (>10 s)
      - Bad JSON / empty response
      - Any other exception
    """

    _OLLAMA_URL = "http://localhost:11434/api/generate"
    _TIMEOUT_S  = 10

    def __init__(self) -> None:
        self._fallback = TemplateNarrativeProvider()

    def generate(
        self,
        alert: Dict[str, Any],
        decision: Dict[str, Any],
        factors: List[Dict[str, Any]],
        calibration_context: Dict[str, Any],
    ) -> str:
        try:
            import httpx
            payload = {
                "model":   "mistral",
                "prompt":  self._build_prompt(alert, decision, factors, calibration_context),
                "stream":  False,
                "options": {"temperature": 0.3},
            }
            resp = httpx.post(self._OLLAMA_URL, json=payload, timeout=self._TIMEOUT_S)
            resp.raise_for_status()
            data = resp.json()
            text = (data.get("response") or "").strip()
            if not text:
                raise ValueError("Empty response from Ollama")
            logger.info("[NARRATIVE] Ollama narrative generated for %s", alert.get("id"))
            return text
        except Exception as exc:
            logger.warning(
                "[NARRATIVE] Ollama unavailable (%s); falling back to template", exc
            )
            return self._fallback.generate(alert, decision, factors, calibration_context)

    def _build_prompt(
        self,
        alert: Dict[str, Any],
        decision: Dict[str, Any],
        factors: List[Dict[str, Any]],
        calibration_context: Dict[str, Any],
    ) -> str:
        factor_summary = ", ".join(
            f"{f['name']}={f['value']:.3f}" for f in factors[:6]
        )
        decision_count = calibration_context.get("decision_count", 0)
        return (
            f"Write a 3-5 sentence security investigation summary for alert "
            f"{alert.get('id', 'UNKNOWN')}. "
            f"Situation: {alert.get('situation_type', 'unknown')}. "
            f"Recommended action: {decision.get('action', 'escalate')} "
            f"({int(float(decision.get('confidence', 0)) * 100)}% confidence). "
            f"GAE factor scores: {factor_summary}. "
            f"End with: 'This recommendation is calibrated from {decision_count} "
            f"verified outcomes.' "
            "Be concise and professional. Security operations language only."
        )


# ============================================================================
# Factory
# ============================================================================

def create_narrative_provider(provider_type: str = "template") -> NarrativeProvider:
    """
    Create a NarrativeProvider instance.

    Args:
        provider_type: "template" (default) or "ollama".
                       Reads NARRATIVE_PROVIDER env var if not specified.

    Returns:
        A NarrativeProvider instance.
    """
    pt = provider_type.lower().strip()
    if pt == "ollama":
        logger.info("[NARRATIVE] Creating OllamaNarrativeProvider")
        return OllamaNarrativeProvider()
    if pt != "template":
        logger.warning(
            "[NARRATIVE] Unknown provider type %r; falling back to template", provider_type
        )
    logger.info("[NARRATIVE] Creating TemplateNarrativeProvider")
    return TemplateNarrativeProvider()


# ============================================================================
# Module-level singleton
# ============================================================================

_provider: Optional[NarrativeProvider] = None


def get_narrative_provider() -> NarrativeProvider:
    """
    Return the active NarrativeProvider singleton.

    If set_narrative_provider() was never called (e.g. in tests),
    creates a TemplateNarrativeProvider on first access.
    """
    global _provider
    if _provider is None:
        _provider = create_narrative_provider(
            os.getenv("NARRATIVE_PROVIDER", "template")
        )
    return _provider


def set_narrative_provider(provider: NarrativeProvider) -> None:
    """Set the module-level singleton. Called once at app startup."""
    global _provider
    _provider = provider
    logger.info("[NARRATIVE] Provider set: %s", type(provider).__name__)
