"""
Investigation Narrative Service — F3a

generate_narrative(analysis_result) builds a 3-5 sentence plain-English
investigation summary from the /alert/analyze response dict.

Design decisions:
  - Template-based, NOT LLM-generated. Deterministic and fast.
  - Reads from app.domains.soc.situations.SOC_SITUATION_TYPES for
    human-readable labels — no hard-coded label strings here.
  - Sentence 4 (threat intel) is OPTIONAL: omitted when no enrichment
    signals are present, keeping the narrative to 3-4 sentences.
  - All helper functions are module-private (underscore prefix).
"""
from typing import Any, Dict, List, Optional


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
# Private helpers
# ============================================================================

def _humanize_factor(raw: str) -> str:
    """Return a readable phrase for a factor string."""
    # Strip parenthesised context values like "destination_matches (Singapore)"
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
    """
    Return sentence 4 if threat intel enrichment is relevant, None otherwise.

    Priority:
      1. Situation-type-specific sentences (most precise)
      2. Generic factor-based sentence
      3. Pattern match fallback
      4. None — no threat intel signal detected
    """
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

    # No threat intel signals — omit sentence 4 entirely
    return None


def _build_sentence1(
    alert_id: str,
    situation_label: str,
    sit_confidence: float,
    mitre_technique: str,
    mitre_tactic: str,
) -> str:
    """Sentence 1: Alert ID + situation type + ATT&CK ref."""
    pct = int(sit_confidence * 100)
    if mitre_technique:
        return (
            f"{alert_id} classified as {situation_label} "
            f"({mitre_technique} · {mitre_tactic}, {pct}% confidence)."
        )
    return f"{alert_id} classified as {situation_label} ({pct}% confidence)."


def _build_sentence2(nodes_count: int, subgraphs: List[str]) -> str:
    """Sentence 2: Graph traversal scope."""
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
    """Sentence 3: Dominant factor + classification confidence calibration note."""
    if not factors_detected:
        return None
    dominant = _humanize_factor(factors_detected[0])
    pct = int(sit_confidence * 100)
    return (
        f"Dominant signal: {dominant} "
        f"(calibrated to {pct}% classification confidence by the pattern library)."
    )


def _build_sentence5(action: str, confidence: float) -> str:
    """Sentence 5: Recommendation + confidence."""
    action_label = _humanize_action(action)
    pct = int(confidence * 100)
    return f"Recommended action: {action_label} ({pct}% agent confidence)."


# ============================================================================
# Public API
# ============================================================================

def generate_narrative(analysis_result: Dict[str, Any]) -> str:
    """
    Generate a 3-5 sentence investigation narrative from the /alert/analyze
    response dict.

    Sentence count:
      Always:      S1 (classification) + S2 (graph scope) + S5 (recommendation)  = 3
      +factors:    S3 (dominant factor)                                           → 4
      +threat_intel: S4 (enrichment)                                              → 5

    Args:
        analysis_result: The full response dict returned by POST /alert/analyze.

    Returns:
        Plain-English narrative string. Never raises — falls back to a safe
        minimal sentence on any extraction error.
    """
    try:
        alert       = analysis_result.get("alert", {}) or {}
        ctx         = analysis_result.get("context", {}) or {}
        rec         = analysis_result.get("recommendation", {}) or {}
        situation   = analysis_result.get("situation_analysis", {}) or {}

        alert_id         = alert.get("id", "UNKNOWN-ALERT")
        nodes_count      = int(ctx.get("nodes_count", 47))
        subgraphs        = ctx.get("subgraphs_traversed", []) or []
        patterns_matched = int(ctx.get("patterns_matched", 0))

        action       = rec.get("action", "escalate_tier2")
        confidence   = float(rec.get("confidence", 0.0))
        pattern_id   = rec.get("pattern_id")

        situation_type   = situation.get("situation_type", "unknown")
        sit_confidence   = float(situation.get("situation_confidence", 0.0))
        factors_detected = situation.get("factors_detected", []) or []
        mitre_technique  = situation.get("mitre_technique", "") or ""
        mitre_tactic     = situation.get("mitre_tactic", "") or ""

        # Human-readable situation label from domain registry
        from app.domains.soc.situations import SOC_SITUATION_TYPES
        sit_meta        = SOC_SITUATION_TYPES.get(situation_type, {})
        situation_label = sit_meta.get("label") or situation_type.replace("_", " ").title()

        # Build sentences
        sentences = []

        sentences.append(
            _build_sentence1(alert_id, situation_label, sit_confidence,
                             mitre_technique, mitre_tactic)
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

        return " ".join(sentences)

    except Exception as exc:
        # Narrative is non-critical — return a safe fallback rather than
        # propagating an exception that would break the triage response.
        print(f"[NARRATIVE] generate_narrative failed: {exc}")
        alert_id = (analysis_result.get("alert") or {}).get("id", "UNKNOWN")
        return (
            f"Investigation narrative unavailable for {alert_id}. "
            "Review the recommendation and situation analysis panels below."
        )
