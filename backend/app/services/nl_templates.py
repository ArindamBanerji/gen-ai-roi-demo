"""
NLTemplateEngine — 24 deterministic NL templates across 3 layers (§23.3).

Layer 1 (L1): per-decision explanations — Tab 3 and shadow disagreements.
Layer 2 (L2): CISO-level summaries — Tab 5 Section 1 and Tab 2 narrative.
Layer 3 (L3): compliance records — evidence export, audit reports.

All templates are rendered deterministically via format_map — no LLM calls.
Missing context keys are rendered as "[N/A]" via _SafeMap so the output
never contains unresolved "{...}" placeholders.

Reference: docs/soc_copilot_design_v5_6_part1.md §23.3
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# _SafeMap: safe context wrapper — missing keys render as "[N/A]"
# ---------------------------------------------------------------------------

class _SafeMap(dict):
    """dict subclass that returns a safe sentinel for missing keys.

    When format_map encounters a missing key it calls __missing__, which
    returns self.  Python then calls self.__format__(spec) to apply the
    format specifier, which we override to always return "[N/A]".
    This means every {field} and {field:.2f} with a missing key renders
    cleanly as "[N/A]" instead of raising KeyError.
    """

    def __missing__(self, key: str) -> "_SafeMap":
        return self  # returned object receives the format spec call below

    def __format__(self, spec: str) -> str:  # noqa: D105
        return "[N/A]"


# ---------------------------------------------------------------------------
# NLTemplateEngine
# ---------------------------------------------------------------------------

class NLTemplateEngine:
    """24 deterministic NL templates across 3 layers.

    Usage
    -----
    engine = NLTemplateEngine()
    text = engine.render_l1("credential_access", context_dict)
    """

    # ── LAYER 1: Per-Decision (Tab 3) ────────────────────────────────────────

    # Legacy alias — kept for backward compatibility; render_l1 uses
    # L1_CREDENTIAL_ACCESS for the "credential_access" category key.
    L1_TRAVEL_ANOMALY = (
        "{user_display} accessed from {location}. "
        "{travel_context}. "
        "{device_context}. "
        "{threat_context}. "
        "{action_display} at {confidence:.0%} confidence. "
        "Calibrated from {calibration_count} verified outcomes on {category} alerts."
    )

    L1_CREDENTIAL_ACCESS = (
        "{user_display} triggered {alert_type_display} on {asset_name} ({asset_criticality} criticality). "
        "{alert_description}. "
        "{time_context}. "
        "{pattern_context}. "
        "{threat_context}. "
        "{action_display} at {confidence:.0%} confidence. "
        "Calibrated from {calibration_count} verified outcomes."
    )

    L1_THREAT_INTEL_MATCH = (
        "Alert matches {indicator_type} from {source_name}. "
        "{ioc_context}. "
        "{asset_context}. "
        "{pattern_context}. "
        "{action_display} at {confidence:.0%} confidence. "
        "Calibrated from {calibration_count} verified outcomes."
    )

    L1_LATERAL_MOVEMENT = (
        "{user_display} traversing from {source_host} to {destination_host}. "
        "{pattern_context}. {threat_context}. "
        "{action_display} at {confidence:.0%} confidence. "
        "Calibrated from {calibration_count} verified outcomes."
    )

    L1_DATA_EXFILTRATION = (
        "{user_display} transferring data from {asset_name} "
        "({asset_criticality} criticality). "
        "{volume_context}. {time_context}. {threat_context}. "
        "{action_display} at {confidence:.0%} confidence. "
        "Calibrated from {calibration_count} verified outcomes."
    )

    L1_INSIDER_THREAT = (
        "{user_display} ({user_role}) performed: {action_description}. "
        "{access_context}. "
        "{pattern_context}. "
        "{asset_context}. "
        "{action_display} at {confidence:.0%} confidence. "
        "Calibrated from {calibration_count} verified outcomes."
    )

    # Alias — kept for backward compatibility
    L1_INSIDER_BEHAVIORAL = L1_INSIDER_THREAT

    L1_CLOUD_INFRASTRUCTURE = (
        "{cloud_operation} from {device_description}. "
        "{device_context}. "
        "{threat_context}. "
        "{pattern_context}. "
        "{action_display} at {confidence:.0%} confidence. "
        "Calibrated from {calibration_count} verified outcomes."
    )

    L1_REFER_TO_ANALYST = (
        "Confidence {confidence:.0%} — below {category} threshold ({threshold:.0%}). "
        "Dominant signal: {dominant_factor_explanation}. "
        "Refer to tier-1 analyst for 3-minute pre-analyzed review. "
        "Pre-analysis: {rationale}."
    )

    L1_LEARNING_UPDATE = (
        "Your feedback updated the {category} profile. "
        "Centroid drift: {delta_norm:.4f}. "
        "The system now weights {shifted_factor} {direction} ({before:.2f}\u2192{after:.2f}) "
        "for {action} decisions in {category} alerts."
    )

    L1_GENERIC = (
        "{situation_type}: {dominant_factors_description}. "
        "{action_display} at {confidence:.0%} confidence. "
        "Calibrated from {calibration_count} verified outcomes on similar alerts."
    )

    # ── LAYER 2: CISO Weekly (Tab 5 Section 1 + Tab 2) ───────────────────────

    L2_WEEKLY_SUMMARY = (
        "This week: {total_alerts} alerts processed — "
        "{auto_approved} auto-approved ({auto_approve_rate:.1%}), "
        "{escalated} escalated, "
        "{human_review} required analyst override."
    )

    L2_ACCURACY_TREND = (
        "System accuracy: {current_week:.1%} this week | "
        "{last_week:.1%} last week | "
        "{at_deployment:.1%} at deployment."
    )

    L2_LEARNING_SUMMARY = (
        "What your system learned: {shift_1}. "
        "{shift_2}. "
        "Institutional Knowledge Score: {iks:.1f} (+{iks_delta:.1f} since last week)."
    )

    L2_RISK_POSTURE = (
        "Risk posture: {open_escalations} open escalations, "
        "{active_campaigns} active threat campaigns, "
        "{cisa_kev_matches} CISA KEV matches in your asset inventory."
    )

    L2_AUTO_APPROVE_BREAKDOWN = (
        "Autonomy envelope by category: "
        "cloud infrastructure {cloud_rate:.0%} (routine scans), "
        "threat intel matches {threat_rate:.0%} (known-benign), "
        "credential access {cred_rate:.0%}. "
        "High-risk categories (insider, lateral movement) held at <3% by design."
    )

    L2_IKS_NARRATIVE = (
        "Institutional Knowledge Score: {iks:.1f}. "
        "Your system has adapted {iks:.0f}% of the way from "
        "'no operational experience' to 'full environment adaptation' "
        "based on {decision_count} verified decisions."
    )

    L2_SHADOW_STATUS = (
        "Shadow mode: {days_active} days active, {decisions_recorded} decisions observed. "
        "Agreement rate: {agreement_rate:.1%}. "
        "Shadow report ready — review before activating live mode."
    )

    L2_THREAT_GRAPH = (
        "Your firm's threat graph: {ioc_count} unique indicators observed "
        "in YOUR environment. {cisa_kev_active} from active CISA KEV advisories. "
        "This intelligence accumulates over time and belongs exclusively to your firm."
    )

    # ── LAYER 3: Audit / Compliance Records ──────────────────────────────────

    L3_DECISION_RECORD = (
        "Decision ID:        {decision_id}\n"
        "Timestamp:          {timestamp}\n"
        "Alert:              {alert_id} (type: {alert_type}, ATT&CK: {technique_id})\n"
        "Category:           {category} (index: {category_idx})\n"
        "Action:             {action} (index: {action_idx}, confidence: {confidence:.4f})\n"
        "Factor vector:      {factor_vector}\n"
        "All distances:      {all_distances}\n"
        "Centroid snapshot:  {centroid_snapshot_id}\n"
        "Kernel:             {kernel}\n"
        "Shadow mode:        {shadow_mode}\n"
        "Human override:     {analyst_override}\n"
        "Outcome:            {outcome}\n"
        "Evidence hash:      {evidence_hash}"
    )

    L3_LEARNING_EVENT = (
        "Learning Event\n"
        "Decision:           {decision_id}\n"
        "Outcome:            {outcome} (verified by: {analyst_id})\n"
        "Category/Action:    {category} / {action}\n"
        "Factor vector used: {factor_vector}\n"
        "Centroid update:    ||delta_mu|| = {delta_norm:.4f}\n"
        "Learning rate:      {learning_rate:.4f}\n"
        "Penalty applied:    {penalty_applied} (ratio: {penalty_ratio})\n"
        "Clip enforced:      {clipped} (all values in [0.0, 1.0])"
    )

    L3_CENTROID_STATE = (
        "Centroid Export\n"
        "Domain:             SOC\n"
        "Snapshot ID:        {snapshot_id}\n"
        "Timestamp:          {timestamp}\n"
        "t_decision:         {t_decision}\n"
        "Trigger:            {trigger}\n"
        "IKS at export:      {iks:.1f}\n"
        "Mean drift:         {mean_drift:.4f}\n"
        "Values in [0,1]:    {values_valid}\n"
        "Observation counts: {obs_counts}\n"
        "[centroid_array follows in next block]"
    )

    L3_DRIFT_ALERT = (
        "Drift Alert\n"
        "Alert type:         {alert_type}\n"
        "Category / Action:  mu[{category_idx}, {action_idx}, :] "
        "-- {category} / {action}\n"
        "Observed drift:     {drift:.4f} (threshold: {threshold:.4f})\n"
        "Triggered at:       {timestamp}\n"
        "Available checkpoint: {checkpoint_id}\n"
        "Recommended action: Review recent feedback for potential bias in this category.\n"
        "Admin action required -- system did NOT auto-revert."
    )

    L3_RESET_EVENT = (
        "System Event: {event_type}\n"
        "Timestamp:          {timestamp}\n"
        "Performed by:       {performed_by}\n"
        "Mode:               {mode}\n"
        "Centroid state before: {snapshot_id_before}\n"
        "Centroid state after:  {snapshot_id_after}\n"
        "Evidence chain hash:   {evidence_hash}"
    )

    L3_OVERRIDE_RECORD = (
        "Analyst Override\n"
        "Decision ID:        {decision_id}\n"
        "System:             {system_action} ({system_confidence:.4f})\n"
        "Analyst action:     {analyst_action}\n"
        "Analyst ID:         {analyst_id}\n"
        "Override timestamp: {timestamp}\n"
        "Reason:             {reason}\n"
        "Learning impact:    centroid updated with analyst action as correct outcome"
    )

    L3_WEEKLY_AUDIT = (
        "Audit Summary -- Week {week_id}\n"
        "Total decisions:    {total_decisions}\n"
        "Auto-approved:      {auto_approved} ({auto_approve_rate:.1%})\n"
        "Analyst overrides:  {overrides}\n"
        "Centroid snapshots: {checkpoint_count}\n"
        "IKS start/end:      {iks_start:.1f} -> {iks_end:.1f}\n"
        "Drift alerts:       {drift_alerts}\n"
        "Snapshot IDs:       {snapshot_ids}"
    )

    L3_MODEL_CARD = (
        "System Model Card\n"
        "Version:            {version}\n"
        "Scoring:            ProfileScorer, L2 distance, tau={tau:.3f}\n"
        "Categories (C):     {n_categories} ({categories})\n"
        "Actions (A):        {n_actions} ({actions})\n"
        "Factors (d):        {n_factors} ({factors})\n"
        "Bootstrap decisions:{bootstrap_count}\n"
        "Live decisions:     {live_count}\n"
        "Evaluation result:  {eval_accuracy:.1%} on {eval_scenarios} scenarios\n"
        "Calibration ECE:    {ece:.4f} at tau={tau:.3f}\n"
        "Last recalibration: {last_recalibration}\n"
        "IKS at export:      {iks:.1f}"
    )

    # ── Template map (keys MUST match SOC_CATEGORIES exactly) ────────────────

    _L1_MAP: dict[str, str] = {
        "credential_access":    L1_CREDENTIAL_ACCESS,
        "malware_execution":    L1_THREAT_INTEL_MATCH,
        "lateral_movement":     L1_LATERAL_MOVEMENT,
        "data_exfiltration":    L1_DATA_EXFILTRATION,
        "insider_threat":       L1_INSIDER_THREAT,
        "cloud_infrastructure": L1_CLOUD_INFRASTRUCTURE,
    }

    # ── Rendering Methods ─────────────────────────────────────────────────────

    @staticmethod
    def _safe(context: dict) -> _SafeMap:
        """Wrap context in _SafeMap so missing keys render as [N/A]."""
        return _SafeMap(context)

    def render_l1(self, category: str, context: dict) -> str:
        """Render the L1 per-decision template for *category*.

        Falls back to L1_GENERIC for unrecognised categories.
        Missing context keys render as "[N/A]" — never raises KeyError.
        """
        template = self._L1_MAP.get(category, self.L1_GENERIC)
        return template.format_map(self._safe(context))

    def render_l1_refer(self, context: dict) -> str:
        """Render the refer-to-analyst L1 template."""
        return self.L1_REFER_TO_ANALYST.format_map(self._safe(context))

    def render_l1_learning_update(self, context: dict) -> str:
        """Render the learning-update L1 template."""
        return self.L1_LEARNING_UPDATE.format_map(self._safe(context))

    def render_l2(self, template_name: str, context: dict) -> str:
        """Render a named L2 template.

        *template_name* is case-insensitive (e.g. "weekly_summary" or
        "WEEKLY_SUMMARY").  Raises ValueError for unknown names.
        """
        attr = f"L2_{template_name.upper()}"
        template = getattr(self, attr, None)
        if template is None:
            raise ValueError(
                f"Unknown L2 template: {template_name!r}. "
                f"Valid names: WEEKLY_SUMMARY, ACCURACY_TREND, LEARNING_SUMMARY, "
                f"RISK_POSTURE, AUTO_APPROVE_BREAKDOWN, IKS_NARRATIVE, "
                f"SHADOW_STATUS, THREAT_GRAPH"
            )
        return template.format_map(self._safe(context))

    def render_l3(self, template_name: str, context: dict) -> str:
        """Render a named L3 template.

        Raises ValueError for unknown names.
        """
        attr = f"L3_{template_name.upper()}"
        template = getattr(self, attr, None)
        if template is None:
            raise ValueError(
                f"Unknown L3 template: {template_name!r}. "
                f"Valid names: DECISION_RECORD, LEARNING_EVENT, CENTROID_STATE, "
                f"DRIFT_ALERT, RESET_EVENT, OVERRIDE_RECORD, WEEKLY_AUDIT, MODEL_CARD"
            )
        return template.format_map(self._safe(context))

    def render_shadow_disagreement(self, decision: dict, alert: dict) -> str:
        """Generate an explanation for a shadow-mode disagreement entry."""
        factor_names = [
            "travel_match", "asset_criticality", "threat_intel_enrichment",
            "pattern_history", "time_anomaly", "device_trust",
        ]
        fv = decision.get("factor_vector") or [0.5] * 6
        factors = dict(zip(factor_names, fv))
        dominant_name, dominant_val = max(factors.items(), key=lambda x: abs(x[1] - 0.5))
        return (
            f"{dominant_name}={dominant_val:.2f}. "
            f"System: {decision.get('action', '[unknown]')} "
            f"({decision.get('confidence', 0.0):.0%}). "
            f"Analyst: {decision.get('analyst_action', '[unknown]')}. "
            f"Likely: analyst applied context outside the 6 factors."
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

nl_engine = NLTemplateEngine()
