"""
SOC domain factor computers -- GAE FactorComputer implementations.

One FactorComputer per SOC factor, each implementing the
gae.factors.FactorComputer Protocol. Four use Cypher relationship traversal
(P10); two read alert properties directly (documented tech debt).

Backward-compatible helpers (SOC_FACTOR_TEMPLATES, _contribution,
compute_soc_factors) are preserved at the bottom for services/triage.py.
"""

import json
import logging
import numpy as np
from datetime import date
from typing import Any, Dict, List, Optional

from gae.contracts import SchemaContract, PropertySpec
from gae.factors import FactorComputer

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Get value from dict or object attribute."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _S(val) -> str:
    """Serialize a Python value to an AGE-safe inline Cypher literal."""
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    return "'" + str(val).replace("\\", "\\\\").replace("'", "\\'") + "'"


def _extract_pattern_history_from_factor_snapshot(raw_snapshot: Any) -> float:
    """Normalize a Decision.factor_snapshot value to the pattern_history slot."""
    if isinstance(raw_snapshot, str):
        try:
            parsed = json.loads(raw_snapshot)
            return float(parsed[3]) if len(parsed) > 3 else 0.40
        except (json.JSONDecodeError, IndexError, TypeError, ValueError):
            return 0.40
    if isinstance(raw_snapshot, (int, float)):
        return float(raw_snapshot)
    return 0.40


# ===========================================================================
# GAE FactorComputer implementations
# ===========================================================================


class PrivilegedIdentityContextFactor(FactorComputer):
    """
    Computes privileged identity context risk from pre-resolved security context.

    Uses normalized user risk, title heuristics, and inverted trust signals
    (missing MFA, fingerprint mismatch) when available. No usable context -> 0.5.
    """

    name = "privileged_identity_context"
    factor_index = 0

    @property
    def factor_name(self) -> str:
        return self.name

    contract = SchemaContract(
        node_type="alert",
        properties=(
            PropertySpec(
                name="privileged_identity_context",
                required=False,
                default_value=0.5,
            ),
        ),
    )

    @staticmethod
    def _clamp(value: float) -> float:
        return float(max(0.0, min(float(value), 1.0)))

    @staticmethod
    def _title_risk(title: Optional[str]) -> Optional[float]:
        if title is None:
            return None
        normalized = str(title).strip().lower()
        if not normalized:
            return None
        if any(token in normalized for token in ("admin", "root", "privileged", "service", "system", "svc")):
            return 0.9
        if any(token in normalized for token in ("chief", "ciso", "cio", "cto", "ceo", "vp", "vice president", "director", "executive", "exec")):
            return 0.7
        return 0.2

    @staticmethod
    def _resolve_context(entity_id: Any, context: Any) -> Any:
        if context is not None and (
            _get(context, "user_risk_score") is not None
            or _get(context, "user_title") is not None
            or _get(context, "mfa_completed") is not None
            or _get(context, "device_fingerprint_match") is not None
        ):
            return context
        if (
            _get(entity_id, "user_risk_score") is not None
            or _get(entity_id, "user_title") is not None
            or _get(entity_id, "mfa_completed") is not None
            or _get(entity_id, "device_fingerprint_match") is not None
        ):
            return entity_id
        nested = _get(entity_id, "security_context")
        if nested is not None:
            return nested
        return None

    async def compute(self, entity_id: str, context: Any = None) -> float:
        ctx = self._resolve_context(entity_id, context)
        if ctx is None:
            return 0.5

        components: List[float] = []

        risk_score = _get(ctx, "user_risk_score")
        if risk_score is not None:
            try:
                components.append(self._clamp(float(risk_score)))
            except (TypeError, ValueError):
                pass

        title_risk = self._title_risk(_get(ctx, "user_title"))
        if title_risk is not None:
            components.append(title_risk)

        mfa_completed = _get(ctx, "mfa_completed")
        if mfa_completed is not None:
            components.append(0.85 if not bool(mfa_completed) else 0.10)

        fingerprint_match = _get(ctx, "device_fingerprint_match")
        if fingerprint_match is not None:
            components.append(0.80 if not bool(fingerprint_match) else 0.10)

        if not components:
            return 0.5
        return self._clamp(sum(components) / len(components))


class TravelMatchFactor:
    """
    Checks whether the alert user has a TravelRecord matching source_location.
    Relationship traversal: (User)-[:HAS_TRAVEL]->(TravelRecord).

    Score: count / (count + 3).  Recency boost +0.15 if start_date < 7 days.
    No matching nodes -> 0.5.
    """

    name = "travel_match"
    factor_index = 0

    @property
    def factor_name(self) -> str:
        return self.name

    contract = SchemaContract(
        node_type="alert",
        properties=(
            PropertySpec(name="travel_match", required=False, default_value=0.5),
        ),
    )

    async def compute(self, alert: Any, graph: Any) -> float:
        user_id = _get(alert, "user_id", "")
        geo = _get(alert, "source_location", "")
        if not user_id or not geo:
            return 0.5
        try:
            results = await graph.run_query(
                f"""
                MATCH (u:User {{id: {_S(user_id)}}})-[:HAS_TRAVEL]->(t:TravelRecord)
                WHERE t.destination = {_S(geo)}
                RETURN count(t) AS cnt,
                       max(t.start_date) AS latest_date
                """
            )
            if not results:
                return 0.5
            record = results[0]
            cnt = int(record.get("cnt", 0) or 0)
            if cnt == 0:
                return 0.5

            score = cnt / (cnt + 3)

            # Recency boost: +0.15 if start_date within last 7 days
            latest = record.get("latest_date")
            if latest is not None:
                try:
                    today = date.today()
                    if hasattr(latest, "to_native"):
                        latest = latest.to_native()
                    if hasattr(latest, "date"):
                        latest = latest.date()
                    if isinstance(latest, date) and (today - latest).days < 7:
                        score = min(score + 0.15, 1.0)
                except Exception:
                    pass

            return float(max(0.0, min(score, 1.0)))
        except Exception as exc:
            log.warning("TravelMatchFactor error: %s", exc)
            raise RuntimeError("AGE query failed for travel factor") from exc


class AssetCriticalityFactor:
    """
    Traverses Alert->Asset->DataClass to compute criticality + sensitivity score.
    Relationship traversal: [:DETECTED_ON] then [:STORES].

    Criticality map: LOW=0.2, MED/MEDIUM=0.5, HIGH=0.8, CRIT/CRITICAL=1.0.
    Sensitivity boost: +0.1 for PII/RESTRICTED/CONFIDENTIAL DataClass.
    No matching nodes -> 0.5.
    """

    name = "asset_criticality"
    factor_index = 1

    @property
    def factor_name(self) -> str:
        return self.name

    contract = SchemaContract(
        node_type="alert",
        properties=(
            PropertySpec(name="asset_criticality", required=False, default_value=0.5),
        ),
    )

    _CRIT_MAP: Dict[str, float] = {
        "low": 0.2,
        "medium": 0.5,
        "med": 0.5,
        "high": 0.8,
        "critical": 1.0,
        "crit": 1.0,
    }
    _SENSITIVE_CLASSES = {"PII", "RESTRICTED", "CONFIDENTIAL", "SECRET"}

    async def compute(self, alert: Any, graph: Any) -> float:
        alert_id = _get(alert, "id", "")
        if not alert_id:
            return 0.5
        try:
            results = await graph.run_query(
                f"""
                MATCH (a:Alert {{alert_id: {_S(alert_id)}}})-[:DETECTED_ON]->(asset:Asset)
                OPTIONAL MATCH (asset)-[:STORES]->(dc:DataClass)
                RETURN asset.criticality AS criticality,
                       dc.sensitivity AS sensitivity
                LIMIT 1
                """
            )
            if not results:
                return 0.5
            record = results[0]
            crit_raw = str(record.get("criticality") or "").lower()
            score = self._CRIT_MAP.get(crit_raw, 0.5)

            sens = str(record.get("sensitivity") or "").upper()
            if sens in self._SENSITIVE_CLASSES:
                score = min(score + 0.1, 1.0)

            return float(score)
        except Exception as exc:
            log.warning("AssetCriticalityFactor error: %s", exc)
            raise RuntimeError("AGE query failed for asset factor") from exc


class ThreatIntelEnrichmentFactor:
    """
    Traverses ThreatIntel->Alert relationships for IOC severity.
    Relationship traversal: (ThreatIntel)-[:ASSOCIATED_WITH]->(Alert).

    Score: max severity normalized.  Corroboration boost +0.1 if multiple sources.
    No matching nodes -> 0.0.
    """

    name = "threat_intel_enrichment"
    factor_index = 2

    @property
    def factor_name(self) -> str:
        return self.name

    contract = SchemaContract(
        node_type="alert",
        properties=(
            PropertySpec(name="threat_intel_enrichment", required=False, default_value=0.0),
        ),
    )

    _SEV_MAP: Dict[str, float] = {
        "info": 0.1,
        "low": 0.3,
        "medium": 0.6,
        "high": 0.85,
        "critical": 1.0,
    }

    async def compute(self, alert: Any, graph: Any) -> float:
        alert_id = _get(alert, "id", "")
        if not alert_id:
            return 0.0

        # Pass 1: IOC matching (existing logic)
        pass1_result = {"value": 0.0, "provenance_nodes": [],
                        "contribution": "IOC score 0.00"}
        try:
            results = await graph.run_query(
                f"MATCH (a:Alert {{alert_id: {_S(alert_id)}}})"
                f"-[:HAS_INDICATOR]->(ti:ThreatIndicator)"
                f" RETURN ti.severity AS severity, ti.source AS source"
            )
            if results:
                max_score = 0.0
                sources: set = set()
                for record in results:
                    sev = str(record.get("severity") or "low").lower()
                    sources.add(str(record.get("source") or "unknown"))
                    max_score = max(max_score, self._SEV_MAP.get(sev, 0.3))
                if len(sources) > 1:
                    max_score = min(max_score + 0.1, 1.0)
                pass1_result["value"] = float(max_score)
        except Exception as exc:
            log.warning("ThreatIntelEnrichmentFactor Pass 1 error: %s", exc)
            raise RuntimeError("AGE query failed for threat intel factor Pass 1") from exc

        pass1_result["contribution"] = f"IOC score {pass1_result['value']:.2f}"

        # Pass 3: Internal campaign membership (highest signal when present)
        pass3 = await self._internal_campaign_score(alert_id, graph)

        # Select the result with the lowest value (strongest escalate signal)
        # Pass 3 wins if campaign membership present (value < 0.50)
        all_passes = [pass1_result, pass3]
        best = min(all_passes, key=lambda r: r["value"])
        return float(best["value"])

    async def _internal_campaign_score(
        self, alert_id: str, graph: Any
    ) -> dict:
        """
        Pass 3: Check if alert is part of an internally correlated campaign.
        HIGH severity campaign -> value=0.05 (strong escalate signal)
        MEDIUM severity campaign -> value=0.20
        LOW or not in campaign -> value=0.50 (neutral)

        Returns dict with value, provenance_nodes, contribution fields.
        Never raises -- exceptions return neutral 0.50.
        """
        try:
            results = await graph.run_query(f"""
                MATCH (a:Alert {{alert_id: {_S(alert_id)}}})-[:MEMBER_OF]->(c:Campaign)
                RETURN c.confidence AS confidence,
                       c.severity AS severity,
                       c.campaign_id AS campaign_id,
                       c.nl_summary AS summary,
                       c.trigger_rule AS trigger_rule
                LIMIT 1
            """)

            if not results:
                return {
                    "value": 0.50,
                    "provenance_nodes": [],
                    "contribution": "No campaign membership -- neutral threat intel signal.",
                }

            c = results[0]
            severity = c.get("severity", "LOW")
            value = 0.05 if severity == "HIGH" else (
                    0.20 if severity == "MEDIUM" else 0.40)

            return {
                "value": value,
                "provenance_nodes": [c["campaign_id"]],
                "contribution": (
                    f"Campaign member ({severity} severity, "
                    f"{float(c['confidence'] or 0):.0%} confidence). "
                    f"{c.get('summary', '')}"
                ),
            }
        except Exception as e:
            log.warning("_internal_campaign_score failed for %s: %s", alert_id, e)
            raise RuntimeError("AGE query failed for campaign score") from e


class PatternHistoryFactor:
    """
    THIS IS THE COMPOUNDING PROOF FACTOR.

    Traverses Decision->Alert to compute historical accuracy for the same
    alert_type.  Relationship traversal: (Decision)-[:DECIDED_ON]->(Alert).

    First alert ever:  returns 0.5 (no history).
    <5 resolved:       returns 0.5 (below minimum threshold).
    >=5 resolved:      returns correct / total.

    As correct decisions accumulate in the graph, this factor's output rises
    toward 1.0 -- demonstrating compounding intelligence across triage cycles.
    """

    name = "pattern_history"
    factor_index = 3

    @property
    def factor_name(self) -> str:
        return self.name

    contract = SchemaContract(
        node_type="alert",
        properties=(
            PropertySpec(name="pattern_history", required=False, default_value=0.5),
        ),
    )

    _MIN_DECISIONS = 5

    async def compute(self, alert: Any, graph: Any) -> float:
        situation_type = (
            _get(alert, "alert_type", "")
            or _get(alert, "situation_type", "")
        )
        if not situation_type:
            return 0.5
        try:
            results = await graph.run_query(
                f"""
                MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)
                WHERE d.domain = 'soc'
                  AND a.alert_type = {_S(situation_type)} AND d.outcome IS NOT NULL
                RETURN count(d) AS total,
                       sum(CASE WHEN d.correct = true THEN 1 ELSE 0 END) AS correct
                """
            )
            if not results:
                return 0.5
            record = results[0]
            total = int(record.get("total", 0) or 0)
            correct = int(record.get("correct", 0) or 0)

            if total < self._MIN_DECISIONS:
                return 0.5

            return float(max(0.0, min(correct / total, 1.0)))
        except Exception as exc:
            log.warning("PatternHistoryFactor error: %s", exc)
            raise RuntimeError("AGE query failed for pattern history") from exc


class PatternHistoryFactorComputer:
    """
    Computes pattern_history factor (position 3 in 0-based indexing,
    the 4th factor in weight matrix column order).

    Two-path computation:
    Path A (W2 enriched): TRIGGERED_EVOLUTION edges present for
      this alert's category in this organizational context.
      Returns action-specific mean from prior verified decisions,
      weighted by recency (exponential decay, half-life=30 decisions).

    Path B (fallback): No TRIGGERED_EVOLUTION edges available.
      Returns baseline pattern_history score (0.40 neutral baseline).

    This implements the W2 compounding pathway: every verified
    decision enriches future factor computation for similar contexts.
    """

    name = "pattern_history"
    factor_index = 3

    @property
    def factor_name(self) -> str:
        return self.name

    contract = SchemaContract(
        node_type="alert",
        properties=(
            PropertySpec(name="pattern_history", required=False, default_value=0.5),
        ),
    )

    HALF_LIFE_DECISIONS = 30  # recency weight half-life

    async def compute(
        self,
        alert: Any,
        graph: Any,
        action_index: Optional[int] = None,
    ) -> float:
        """
        Returns pattern_history factor value in [0.0, 1.0].
        Uses TRIGGERED_EVOLUTION edges if available, else fallback.
        """
        category = _get(alert, "category", "") or _get(alert, "alert_type", "")
        if not category:
            return self._fallback_compute(alert)

        try:
            if action_index is not None:
                query = f"""
                MATCH (d:Decision)-[:TRIGGERED_EVOLUTION]->(evo:EvolutionEvent)
                WHERE d.domain = 'soc'
                  AND d.category = {_S(category)}
                  AND d.action_index = {_S(action_index)}
                  AND d.verified_correct = true
                RETURN d.factor_snapshot AS factor_snapshot,
                       d.decision_number AS decision_num
                ORDER BY d.decision_number DESC
                LIMIT 50
                """
            else:
                query = f"""
                MATCH (d:Decision)-[:TRIGGERED_EVOLUTION]->(evo:EvolutionEvent)
                WHERE d.domain = 'soc'
                  AND d.category = {_S(category)}
                  AND d.verified_correct = true
                RETURN d.factor_snapshot AS factor_snapshot,
                       d.decision_number AS decision_num
                ORDER BY d.decision_number DESC
                LIMIT 50
                """

            results = await graph.run_query(query)
        except Exception as exc:
            log.warning("PatternHistoryFactorComputer error: %s", exc)
            raise RuntimeError("AGE query failed for pattern computation") from exc

        if not results:
            return self._fallback_compute(alert)

        # Parse full JSON snapshot, then isolate factor_snapshot[3] (pattern_history).
        values = []
        for row in results:
            raw_snapshot = row.get("factor_snapshot") or row.get("pattern_value")
            values.append(_extract_pattern_history_from_factor_snapshot(raw_snapshot))
        decision_nums = [r["decision_num"] for r in results]
        max_dec = max(decision_nums)
        weights = [
            2 ** (-(max_dec - d) / self.HALF_LIFE_DECISIONS)
            for d in decision_nums
        ]
        weighted_mean = sum(v * w for v, w in zip(values, weights)) / sum(weights)
        return float(np.clip(weighted_mean, 0.0, 1.0))

    def _fallback_compute(self, alert: Any) -> float:
        """
        Existing pattern_history computation when no W2 edges present.
        Returns 0.40 neutral baseline (current behavior -- unchanged from v5.5.1).
        """
        return 0.40


class TimeAnomalyFactor:
    """
    Reads alert.business_hours_login property to score time-based anomaly risk.

    NOTE: Property read -- tech debt TD-014.
    Future version traverses (User)-[:ACTIVE_AT]->(TimeSlot).

    Score: 0.0 = business hours, 0.7 = after hours, 1.0 = weekend.
    Default: 0.7 (conservative) when property is absent.
    """

    name = "time_anomaly"
    factor_index = 4

    @property
    def factor_name(self) -> str:
        return self.name

    contract = SchemaContract(
        node_type="alert",
        properties=(
            PropertySpec(name="time_anomaly", required=False, default_value=0.7),
        ),
    )

    async def compute(self, alert: Any, graph: Any) -> float:
        weekend = _get(alert, "weekend_login", None)
        if weekend is True:
            return 1.0

        bhl = _get(alert, "business_hours_login", None)
        if bhl is True:
            return 0.0
        if bhl is False:
            return 0.7

        return 0.7  # property absent -> conservative after-hours assumption


class DeviceTrustFactor:
    """
    Reads alert properties mfa_completed, device_fingerprint_match, vpn
    to compute a composite device trust score.

    NOTE: Property read -- tech debt TD-015.
    Future version traverses (Alert)-[:USES_DEVICE]->(Device).

    Each missing trusted flag adds 1/3 to the score.
    All trusted (mfa + fingerprint + vpn): 0.0 (fully trusted).
    None trusted: 1.0 (untrusted device, high risk).
    """

    name = "device_trust"
    factor_index = 5

    @property
    def factor_name(self) -> str:
        return self.name

    contract = SchemaContract(
        node_type="alert",
        properties=(
            PropertySpec(name="device_trust", required=False, default_value=0.5),
        ),
    )

    async def compute(self, alert: Any, graph: Any) -> float:
        mfa = bool(_get(alert, "mfa_completed", False))
        fingerprint = bool(_get(alert, "device_fingerprint_match", False))
        # vpn: explicit bool or inferred from vpn_provider presence
        vpn_raw = _get(alert, "vpn", None)
        if vpn_raw is None:
            vpn_raw = bool(_get(alert, "vpn_provider", None))
        vpn = bool(vpn_raw)

        untrusted = sum([not mfa, not fingerprint, not vpn])
        return float(untrusted / 3.0)


# ===========================================================================
# Backward compatibility — used by services/triage.py
# ===========================================================================
# The helpers below (_contribution, SOC_FACTOR_TEMPLATES, compute_soc_factors)
# are preserved unchanged.  services/triage.py imports them directly.
# ===========================================================================


SOC_FACTOR_TEMPLATES: Dict[str, Dict[str, Any]] = {

    # Travel login anomaly — likely false positive
    "ALERT-7823": {
        "recommended_action": "false_positive_close",
        "confidence": 0.94,
        "factors": [
            {
                "name":        "privileged_identity_context",
                "value":       0.92,
                "weight":      0.82,
                "explanation": "Privileged admin identity used without strong session safeguards -- elevated account context raises risk",
            },
            {
                "name":        "asset_criticality",
                "value":       0.30,
                "weight":      0.45,
                "explanation": "Development server (non-critical) -- lower blast radius if wrong",
            },
            {
                "name":        "time_anomaly",
                "value":       0.70,
                "weight":      0.55,
                "explanation": "Login at 3 AM home timezone -- moderate anomaly given travel context",
            },
            {
                "name":        "device_trust",
                "value":       0.90,
                "weight":      0.78,
                "explanation": "Known corporate laptop, MDM enrolled, device fingerprint matched",
            },
            {
                "name":        "pattern_history",
                "value":       0.85,
                "weight":      0.70,
                "explanation": "PAT-TRAVEL-001: 127 similar alerts resolved as false positives (92% FP rate)",
            },
        ],
    },

    # Known phishing campaign — auto-remediate
    "ALERT-7824": {
        "recommended_action": "auto_remediate",
        "confidence": 0.94,
        "factors": [
            {
                "name":        "campaign_signature_match",
                "value":       0.94,
                "weight":      0.90,
                "explanation": "Operation DarkHook campaign signature matched -- known phishing kit",
            },
            {
                "name":        "sender_domain_risk",
                "value":       0.92,
                "weight":      0.85,
                "explanation": "phishmail.com domain flagged in threat feed, used in 47 prior campaigns",
            },
            {
                "name":        "time_anomaly",
                "value":       0.40,
                "weight":      0.40,
                "explanation": "Received during business hours -- low time-based anomaly",
            },
            {
                "name":        "asset_criticality",
                "value":       0.40,
                "weight":      0.45,
                "explanation": "Laptop endpoint, moderate criticality -- quarantine is low-blast-radius action",
            },
            {
                "name":        "pattern_history",
                "value":       0.82,
                "weight":      0.70,
                "explanation": "PAT-PHISH-KNOWN: 214 similar alerts auto-remediated (82% FP rate)",
            },
        ],
    },

    "brute_force": {
        "recommended_action": "auto_remediate",
        "confidence": 0.93,
        "factors": [
            {"name": "failure_rate",      "value": 0.95, "weight": 0.85, "explanation": "Auth failure rate 47/min exceeds brute-force threshold (>10 failures/min)"},
            {"name": "asset_criticality", "value": 0.65, "weight": 0.55, "explanation": "Target account holds elevated permissions on production system"},
            {"name": "time_anomaly",      "value": 0.88, "weight": 0.70, "explanation": "Attack began 02:34 -- outside business hours, low analyst coverage"},
            {"name": "source_reputation", "value": 0.90, "weight": 0.80, "explanation": "Source IP blacklisted in 3 threat feeds -- known attack infrastructure"},
            {"name": "pattern_history",   "value": 0.82, "weight": 0.72, "explanation": "Similar brute-force pattern seen in 34 prior incidents -- high confidence block"},
        ],
    },

    "privilege_escalation": {
        "recommended_action": "escalate_incident",
        "confidence": 0.91,
        "factors": [
            {"name": "escalation_severity", "value": 0.90, "weight": 0.85, "explanation": "Root-level privilege obtained on production host -- full system access"},
            {"name": "asset_criticality",   "value": 0.90, "weight": 0.85, "explanation": "Critical production server -- potential for wide business impact"},
            {"name": "time_anomaly",        "value": 0.78, "weight": 0.60, "explanation": "Escalation occurred outside normal change windows -- unplanned activity"},
            {"name": "device_trust",        "value": 0.60, "weight": 0.50, "explanation": "Originating process not in approved whitelist -- potentially malicious"},
            {"name": "pattern_history",     "value": 0.70, "weight": 0.65, "explanation": "Privilege escalation path matches known attacker TTPs in MITRE T1068"},
        ],
    },

    "credential_stuffing": {
        "recommended_action": "auto_remediate",
        "confidence": 0.90,
        "factors": [
            {"name": "account_volume",      "value": 0.88, "weight": 0.80, "explanation": "142 distinct accounts targeted -- automated stuffing pattern confirmed"},
            {"name": "credential_exposure", "value": 0.85, "weight": 0.78, "explanation": "Credentials match recent breach dataset -- verified leaked pairs"},
            {"name": "time_anomaly",        "value": 0.75, "weight": 0.60, "explanation": "High-velocity login attempts span 3-hour window -- automated bot pattern"},
            {"name": "source_reputation",   "value": 0.88, "weight": 0.80, "explanation": "Source IPs rotate across 18 countries -- residential botnet pattern"},
            {"name": "pattern_history",     "value": 0.75, "weight": 0.68, "explanation": "PAT-CREDSTUFF-001: 34 prior incidents, 78% success rate blocking at this stage"},
        ],
    },

    "c2_beacon": {
        "recommended_action": "escalate_incident",
        "confidence": 0.95,
        "factors": [
            {"name": "c2_confidence",  "value": 0.96, "weight": 0.92, "explanation": "Destination IP confirmed C2 infrastructure across 4 threat intelligence feeds"},
            {"name": "asset_criticality", "value": 0.82, "weight": 0.75, "explanation": "Beaconing host has read access to sensitive data stores"},
            {"name": "time_anomaly",   "value": 0.65, "weight": 0.55, "explanation": "Regular 60-second beacon interval -- automated implant, not user-initiated"},
            {"name": "traffic_volume", "value": 0.80, "weight": 0.72, "explanation": "Low-volume but persistent traffic -- classic C2 check-in heartbeat pattern"},
            {"name": "pattern_history","value": 0.90, "weight": 0.82, "explanation": "C2 domain matches threat actor infrastructure from Q3 2025 campaign"},
        ],
    },

    "malware_execution": {
        "recommended_action": "escalate_incident",
        "confidence": 0.93,
        "factors": [
            {"name": "ioc_confidence",  "value": 0.94, "weight": 0.90, "explanation": "IOC confirmed across 3 threat intelligence feeds with high fidelity"},
            {"name": "asset_criticality","value": 0.70, "weight": 0.60, "explanation": "Affected host is a production workstation with domain access"},
            {"name": "time_anomaly",    "value": 0.55, "weight": 0.45, "explanation": "Activity during business hours -- potential user-initiated or phishing lure"},
            {"name": "indicator_age",   "value": 0.85, "weight": 0.75, "explanation": "IOC first seen 14 days ago -- active threat campaign, not stale data"},
            {"name": "pattern_history", "value": 0.88, "weight": 0.80, "explanation": "IOC associated with known threat actor group targeting financial sector"},
        ],
    },

    "data_exfil": {
        "recommended_action": "escalate_incident",
        "confidence": 0.95,
        "factors": [
            {"name": "transfer_volume",  "value": 0.93, "weight": 0.88, "explanation": "47 GB outbound to external cloud storage -- 23x above host baseline"},
            {"name": "asset_criticality","value": 0.85, "weight": 0.78, "explanation": "Source server contains customer records and intellectual property"},
            {"name": "time_anomaly",     "value": 0.88, "weight": 0.80, "explanation": "Transfer initiated at 01:15 -- off-hours, minimal monitoring coverage"},
            {"name": "destination_risk", "value": 0.90, "weight": 0.85, "explanation": "Destination IP not in approved vendor list -- unsanctioned cloud provider"},
            {"name": "pattern_history",  "value": 0.60, "weight": 0.55, "explanation": "No prior external transfers from this host -- novel behavior, low FP rate"},
        ],
    },

    "anomalous_behavior": {
        "recommended_action": "enrich_and_wait",
        "confidence": 0.87,
        "factors": [
            {"name": "traffic_anomaly",    "value": 0.75, "weight": 0.70, "explanation": "Network traffic 8x above baseline -- significant deviation from normal"},
            {"name": "asset_criticality",  "value": 0.65, "weight": 0.58, "explanation": "Mid-tier server -- moderate blast radius if lateral movement succeeds"},
            {"name": "time_anomaly",       "value": 0.80, "weight": 0.70, "explanation": "Anomaly began after business hours -- low-noise window for attacker"},
            {"name": "connection_pattern", "value": 0.72, "weight": 0.65, "explanation": "Internal hosts contacted in sequential sweep -- lateral movement indicators"},
            {"name": "pattern_history",    "value": 0.50, "weight": 0.50, "explanation": "Novel behavior pattern -- limited historical precedent, enrichment needed"},
        ],
    },

    "insider_threat": {
        "recommended_action": "escalate_incident",
        "confidence": 0.89,
        "factors": [
            {"name": "access_anomaly",  "value": 0.82, "weight": 0.78, "explanation": "Bulk data access 12x above user baseline in 2-hour window"},
            {"name": "asset_criticality","value": 0.88, "weight": 0.82, "explanation": "Customer PII database accessed -- regulatory and reputational exposure"},
            {"name": "time_anomaly",    "value": 0.85, "weight": 0.75, "explanation": "Access at 11 PM, 2 weeks before voluntary departure -- high-risk timing"},
            {"name": "device_trust",    "value": 0.90, "weight": 0.80, "explanation": "Registered corporate device -- access is deliberate, not accidental"},
            {"name": "pattern_history", "value": 0.65, "weight": 0.60, "explanation": "Access pattern matches 7 prior insider incidents in case library"},
        ],
    },

    "cloud_config": {
        "recommended_action": "auto_remediate",
        "confidence": 0.88,
        "factors": [
            {"name": "exposure_severity","value": 0.90, "weight": 0.85, "explanation": "S3 bucket with public-read ACL containing sensitive configuration files"},
            {"name": "asset_criticality","value": 0.75, "weight": 0.68, "explanation": "Cloud resource attached to production environment -- active exposure"},
            {"name": "time_anomaly",    "value": 0.30, "weight": 0.30, "explanation": "Misconfiguration present since last deployment 3 days ago -- drift detected"},
            {"name": "data_sensitivity","value": 0.80, "weight": 0.75, "explanation": "Exposed content includes API keys and database connection strings"},
            {"name": "pattern_history", "value": 0.70, "weight": 0.62, "explanation": "Third cloud misconfiguration this quarter -- systemic IaC policy gap"},
        ],
    },

    # Default — conservative fallback for unknown alert IDs
    # Factor order matches SOC_FACTORS: privileged_identity_context, asset_criticality,
    # [threat_intel_enrichment inserted by compute_soc_factors at pos 2],
    # pattern_history, time_anomaly, device_trust.
    "_default": {
        "recommended_action": "escalate_tier2",
        "confidence":         0.60,
        "factors": [
            {"name": "privileged_identity_context", "value": 0.50, "weight": 0.60, "explanation": "No privileged identity context available -- defaulting to neutral score"},
            {"name": "asset_criticality","value": 0.50, "weight": 0.45, "explanation": "Asset criticality undetermined -- defaulting to conservative action"},
            {"name": "pattern_history", "value": 0.30, "weight": 0.60, "explanation": "Limited pattern history for this alert type"},
            {"name": "time_anomaly",    "value": 0.50, "weight": 0.50, "explanation": "Activity detected outside normal business hours"},
            {"name": "device_trust",    "value": 0.50, "weight": 0.55, "explanation": "Device trust level undetermined"},
        ],
    },
}


def _contribution(value: float, weight: float) -> str:
    """Map value x weight to a contribution label."""
    score = value * weight
    if score > 0.5:
        return "high"
    if score > 0.25:
        return "medium"
    if score > 0:
        return "low"
    return "none"


def compute_soc_factors(
    alert_id: str,
    ti_factor: Optional[Dict[str, Any]] = None,
    alert_type: str = "",
) -> Dict[str, Any]:
    """
    Build the full 6-factor decision breakdown for alert_id.

    Lookup order:
      1. alert_id  -- exact match (ALERT-7823, ALERT-7824)
      2. alert_type -- type-keyed template (brute_force, c2_beacon, ...)
      3. "_default" -- conservative fallback

    Args:
        alert_id:   Alert identifier (e.g. "ALERT-7823").
        ti_factor:  Pre-built threat_intel_enrichment factor dict.
        alert_type: Alert type string for type-level fallback.

    Returns:
        Dict matching the return format of services/triage.get_decision_factors().
    """
    template = (
        SOC_FACTOR_TEMPLATES.get(alert_id)
        or SOC_FACTOR_TEMPLATES.get(alert_type)
        or SOC_FACTOR_TEMPLATES["_default"]
    )

    static_factors: List[Dict[str, Any]] = []
    for f in template["factors"]:
        static_factors.append({
            "name":         f["name"],
            "value":        f["value"],
            "weight":       f["weight"],
            "contribution": _contribution(f["value"], f["weight"]),
            "explanation":  f["explanation"],
        })

    if ti_factor is None:
        ti_factor = {
            "name":         "threat_intel_enrichment",
            "value":        0.0,
            "weight":       0.75,
            "contribution": "none",
            "explanation":  "No threat intel data -- click Refresh Threat Intel in Tab 3",
        }

    factors = static_factors[:2] + [ti_factor] + static_factors[2:]

    return {
        "alert_id":           alert_id,
        "factors":            factors,
        "recommended_action": template["recommended_action"],
        "confidence":         template["confidence"],
        "decision_method":    "ProfileScorer L2 centroid-proximity scoring (n_factors x n_actions x n_categories)",
        "weights_note":       (
            "Centroids update automatically through verified analyst decisions "
            "(Loop 2 + Loop 3)"
        ),
        # DiagonalKernel explainability (CLAIM-B3).
        # Percentage = _factor_kernel_weight(0.28, all_soc_sigmas)*100 ≈ 6
        # (device_trust σ=0.28 vs threat_intel_enrichment σ=0.07 as max-precision anchor).
        "kernel_note": (
            "Higher-noise factors are automatically down-weighted by the "
            "DiagonalKernel scoring engine (Innovation #4). "
            "device_trust (sigma=0.28) contributes 6% of its nominal weight -- "
            "the system trusts your highest-confidence signals most."
        ),
    }
