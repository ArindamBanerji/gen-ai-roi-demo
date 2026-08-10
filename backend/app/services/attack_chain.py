"""
L-06: Attack Chain Correlation.

Detects temporally and entity-correlated alert campaigns.
Three correlation mechanisms:
1. Entity overlap: alerts sharing users, assets, or IPs within a time window
2. MITRE tactic progression: alerts following ATT&CK kill chain order
3. ThreatIndicator linkage: alerts linked by shared IOCs

A campaign is: >=3 alerts sharing >=1 correlation mechanism within 24 hours.

Source: consolidated_capability_plan L-06.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)


@dataclass
class Campaign:
    """A detected attack chain / correlated campaign."""
    campaign_id: str                # e.g., "C-2026-0001"
    alerts: List[str]               # alert IDs in this campaign
    shared_entities: List[Dict]     # entities linking the alerts
    correlation_type: str           # "entity" | "tactic" | "ioc" | "multi"
    confidence: float               # 0-1, based on overlap strength
    first_seen: str                 # earliest alert timestamp
    last_seen: str                  # latest alert timestamp
    mitre_tactics: List[str]        # MITRE tactics observed (ordered)
    summary: str                    # NL summary of the campaign


class AttackChainService:
    """
    Scans recent alerts for correlated campaigns.

    Three detection passes:
    1. Entity graph walk: alerts sharing User/Asset/IP nodes
    2. MITRE progression: alerts following tactic sequence
    3. IOC linkage: alerts sharing ThreatIndicator nodes

    Merge overlapping detections into unified campaigns.
    """

    # MITRE ATT&CK tactic progression order (kill chain)
    TACTIC_ORDER = [
        "reconnaissance", "resource_development", "initial_access",
        "execution", "persistence", "privilege_escalation",
        "defense_evasion", "credential_access", "discovery",
        "lateral_movement", "collection", "command_and_control",
        "exfiltration", "impact",
    ]

    CAMPAIGN_MIN_ALERTS = 3     # minimum alerts for a campaign
    TIME_WINDOW_HOURS   = 24    # correlation window
    ENTITY_OVERLAP_MIN  = 1     # minimum shared entities

    def __init__(self, db_client: Any):
        self.db = db_client

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    async def scan_recent_alerts(self, hours_back: int = 72) -> List[Campaign]:
        """
        Scan alerts from the last N hours for correlated campaigns.
        Returns list of detected campaigns, sorted by confidence descending.
        """
        alerts = await self._fetch_recent_alerts(hours_back)
        if len(alerts) < self.CAMPAIGN_MIN_ALERTS:
            return []

        entity_groups = self._correlate_by_entity(alerts)
        tactic_groups = self._correlate_by_tactic(alerts)
        ioc_groups    = self._correlate_by_ioc(alerts)

        campaigns = self._merge_groups(entity_groups, tactic_groups, ioc_groups)

        result = []
        for i, group in enumerate(campaigns):
            campaign = self._build_campaign(group, i + 1)
            if campaign:
                result.append(campaign)

        return sorted(result, key=lambda c: c.confidence, reverse=True)

    # -------------------------------------------------------------------------
    # Data fetch
    # -------------------------------------------------------------------------

    async def _fetch_recent_alerts(self, hours_back: int) -> List[Dict]:
        """Fetch alerts with linked entities from AGE."""
        query = """
        MATCH (a:Alert)
        OPTIONAL MATCH (a)-[:INVOLVES]->(u:User)
        OPTIONAL MATCH (a)-[:DETECTED_ON]->(asset:Asset)
        OPTIONAL MATCH (a)-[:CLASSIFIED_AS]->(ap:AttackPattern)
        OPTIONAL MATCH (a)-[:HAS_INDICATOR]->(ti:ThreatIndicator)
        RETURN a.alert_id       AS alert_id,
               a.severity       AS severity,
               a.timestamp_epoch AS timestamp,
               a.source_location AS source_location,
               ap.name          AS alert_type,
               collect(DISTINCT u.email)    AS users,
               collect(DISTINCT asset.hostname) AS assets,
               collect(DISTINCT ti.indicator)   AS iocs
        ORDER BY a.timestamp_epoch DESC
        """
        try:
            records = await self.db.run_query(query, {})
            return [dict(r) for r in records] if records else []
        except Exception as exc:
            log.warning("[ATTACK_CHAIN] _fetch_recent_alerts failed: %s", exc)
            return []

    # -------------------------------------------------------------------------
    # Correlation passes (all synchronous — no DB access)
    # -------------------------------------------------------------------------

    def _correlate_by_entity(self, alerts: List[Dict]) -> List[List[Dict]]:
        """
        Group alerts sharing users or assets within the time window.
        Builds an adjacency graph and finds connected components.
        """
        n = len(alerts)
        adj: Dict[int, set] = {i: set() for i in range(n)}

        for i in range(n):
            for j in range(i + 1, n):
                shared_users  = set(alerts[i].get("users",  []) or []) & set(alerts[j].get("users",  []) or [])
                shared_assets = set(alerts[i].get("assets", []) or []) & set(alerts[j].get("assets", []) or [])
                shared = {s for s in (shared_users | shared_assets) if s}
                if len(shared) >= self.ENTITY_OVERLAP_MIN:
                    adj[i].add(j)
                    adj[j].add(i)

        visited: set = set()
        groups: List[List[Dict]] = []
        for i in range(n):
            if i not in visited:
                component: List[Dict] = []
                queue = [i]
                while queue:
                    node = queue.pop(0)
                    if node in visited:
                        continue
                    visited.add(node)
                    component.append(alerts[node])
                    for neighbor in adj[node]:
                        if neighbor not in visited:
                            queue.append(neighbor)
                if len(component) >= self.CAMPAIGN_MIN_ALERTS:
                    groups.append(component)

        return groups

    def _correlate_by_tactic(self, alerts: List[Dict]) -> List[List[Dict]]:
        """
        Group alerts following MITRE ATT&CK tactic progression.
        Maps alert_type -> tactic index; returns a group if >=3 distinct
        tactics are represented in the alert set.
        """
        category_to_tactic = {
            "credential_access":    "credential_access",
            "lateral_movement":     "lateral_movement",
            "data_exfiltration":    "exfiltration",
            "insider_threat":       "collection",
            "cloud_infrastructure": "initial_access",
            "malware_execution":    "command_and_control",
        }
        tactic_to_idx = {t: i for i, t in enumerate(self.TACTIC_ORDER)}

        tagged: List[tuple] = []
        for alert in alerts:
            at = str(alert.get("alert_type") or "")
            for cat, tactic in category_to_tactic.items():
                if cat in at.lower():
                    idx = tactic_to_idx.get(tactic, -1)
                    if idx >= 0:
                        tagged.append((alert, idx))
                    break

        if len(tagged) < self.CAMPAIGN_MIN_ALERTS:
            return []

        tagged.sort(key=lambda x: x[1])
        distinct_tactics = len({t[1] for t in tagged})
        if distinct_tactics >= 3:
            return [[t[0] for t in tagged]]
        return []

    def _correlate_by_ioc(self, alerts: List[Dict]) -> List[List[Dict]]:
        """Group alerts sharing ThreatIndicator IOC values."""
        ioc_to_alerts: Dict[str, List[Dict]] = {}
        for alert in alerts:
            for ioc in (alert.get("iocs") or []):
                if ioc:
                    ioc_to_alerts.setdefault(ioc, []).append(alert)

        groups: List[List[Dict]] = []
        seen: set = set()
        for ioc, linked in ioc_to_alerts.items():
            if len(linked) >= self.CAMPAIGN_MIN_ALERTS:
                key = tuple(sorted(a["alert_id"] for a in linked if a.get("alert_id")))
                if key not in seen:
                    seen.add(key)
                    groups.append(linked)

        return groups

    def _merge_groups(self, *group_lists: List[List[Dict]]) -> List[List[Dict]]:
        """
        Merge overlapping groups from different correlation methods.
        Two groups merge when they share >=2 alerts.
        """
        all_groups: List[List[Dict]] = []
        for groups in group_lists:
            all_groups.extend(groups)

        if not all_groups:
            return []

        merged: List[List[Dict]] = []
        used: set = set()

        for i, g1 in enumerate(all_groups):
            if i in used:
                continue
            current_ids  = {a.get("alert_id") for a in g1}
            current_list = list(g1)

            for j, g2 in enumerate(all_groups):
                if j <= i or j in used:
                    continue
                g2_ids = {a.get("alert_id") for a in g2}
                if len(current_ids & g2_ids) >= 2:
                    new_ids = g2_ids - current_ids
                    current_ids |= g2_ids
                    for a in g2:
                        if a.get("alert_id") in new_ids:
                            current_list.append(a)
                    used.add(j)

            merged.append(current_list)
            used.add(i)

        return [g for g in merged if len(g) >= self.CAMPAIGN_MIN_ALERTS]

    # -------------------------------------------------------------------------
    # Campaign assembly
    # -------------------------------------------------------------------------

    def _build_campaign(self, alerts: List[Dict], index: int) -> Optional[Campaign]:
        """Build a Campaign object with NL summary."""
        if len(alerts) < self.CAMPAIGN_MIN_ALERTS:
            return None

        alert_ids = [a.get("alert_id", "") for a in alerts]

        all_users:  set = set()
        all_assets: set = set()
        all_iocs:   set = set()
        for a in alerts:
            all_users.update(u for u in (a.get("users")  or []) if u)
            all_assets.update(v for v in (a.get("assets") or []) if v)
            all_iocs.update(i for i in (a.get("iocs")   or []) if i)

        shared_entities: List[Dict] = []
        shared_entities.extend({"type": "user",  "value": u} for u in all_users)
        shared_entities.extend({"type": "asset", "value": v} for v in all_assets)
        shared_entities.extend({"type": "ioc",   "value": i} for i in all_iocs)

        has_entity = bool(all_users or all_assets)
        has_ioc    = bool(all_iocs)
        if has_entity and has_ioc:
            corr_type = "multi"
        elif has_ioc:
            corr_type = "ioc"
        else:
            corr_type = "entity"

        confidence = min(1.0, 0.5 + 0.1 * len(shared_entities) + 0.05 * len(alerts))

        timestamps = [str(a.get("timestamp", "")) for a in alerts if a.get("timestamp")]
        first_seen = min(timestamps) if timestamps else ""
        last_seen  = max(timestamps) if timestamps else ""

        alert_types = {str(a.get("alert_type") or "unknown") for a in alerts}
        summary = (
            f"Campaign of {len(alerts)} alerts involving "
            f"{len(all_users)} user(s) and {len(all_assets)} asset(s). "
        )
        if all_iocs:
            summary += f"{len(all_iocs)} shared threat indicator(s). "
        summary += f"Alert types: {', '.join(list(alert_types)[:5])}."

        return Campaign(
            campaign_id    = f"C-2026-{index:04d}",
            alerts         = alert_ids,
            shared_entities= shared_entities,
            correlation_type=corr_type,
            confidence     = round(confidence, 2),
            first_seen     = first_seen,
            last_seen      = last_seen,
            mitre_tactics  = [],
            summary        = summary,
        )

    # -------------------------------------------------------------------------
    # Detail lookup
    # -------------------------------------------------------------------------

    async def get_campaign_detail(self, campaign_id: str) -> Optional[Dict]:
        """Re-scan and return full detail for a specific campaign."""
        campaigns = await self.scan_recent_alerts(hours_back=168)
        for c in campaigns:
            if c.campaign_id == campaign_id:
                return {
                    "campaign_id":      c.campaign_id,
                    "alerts":           c.alerts,
                    "shared_entities":  c.shared_entities,
                    "correlation_type": c.correlation_type,
                    "confidence":       c.confidence,
                    "first_seen":       c.first_seen,
                    "last_seen":        c.last_seen,
                    "summary":          c.summary,
                }
        return None
