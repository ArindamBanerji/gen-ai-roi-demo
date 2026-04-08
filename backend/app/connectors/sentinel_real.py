"""
app/connectors/sentinel_real.py — Block 4.2 Real Sentinel Connector (Inward).

Reads live alerts from Microsoft Sentinel Graph Security API and normalizes
to SituationAnalyzer schema.  Auth via OAuth2 client credentials (msal).

Dependencies (optional — graceful ImportError when absent):
  pip install msal httpx

Credentials come from environment variables only — never hardcoded:
  SENTINEL_TENANT_ID
  SENTINEL_CLIENT_ID
  SENTINEL_CLIENT_SECRET
  SENTINEL_WORKSPACE_ID   (optional — narrows filter to one workspace)

Safe degradation: if credentials absent or msal/httpx not installed,
fetch_alerts() returns [] and get_sentinel_alerts() returns not_configured.
"""

import logging
import os
import time
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Category constants and mapping
# ---------------------------------------------------------------------------

VALID_CATEGORIES = {
    "credential_access", "threat_intel_match", "lateral_movement",
    "data_exfiltration", "insider_threat", "cloud_infrastructure",
}

SENTINEL_CATEGORY_MAP = {
    # Credential / Identity
    "CredentialAccess":   "credential_access",
    "credential-access":  "credential_access",
    "PasswordSpray":      "credential_access",
    "BruteForce":         "credential_access",
    "UnfamiliarSignIn":   "credential_access",
    # Lateral movement
    "LateralMovement":    "lateral_movement",
    "lateral-movement":   "lateral_movement",
    # Data exfiltration
    "Exfiltration":       "data_exfiltration",
    "exfiltration":       "data_exfiltration",
    "DataExfiltration":   "data_exfiltration",
    # Threat intel
    "ThreatIntelligence":  "threat_intel_match",
    "threat-intelligence": "threat_intel_match",
    "MaliciousIP":         "threat_intel_match",
    # Insider
    "InsiderRisk":        "insider_threat",
    "insider-risk":       "insider_threat",
    # Cloud
    "CloudInfrastructure":    "cloud_infrastructure",
    "cloud-infrastructure":   "cloud_infrastructure",
    "AnomalousAzureActivity": "cloud_infrastructure",
}


def _map_sentinel_category(raw_category: str) -> str:
    """Map a Sentinel alert category string to a VALID_CATEGORIES member."""
    if raw_category in VALID_CATEGORIES:
        return raw_category
    mapped = SENTINEL_CATEGORY_MAP.get(raw_category)
    if mapped:
        return mapped
    # Fuzzy substring fallback
    raw_lower = raw_category.lower()
    if "credential" in raw_lower or "password" in raw_lower or "login" in raw_lower:
        return "credential_access"
    if "lateral" in raw_lower or "movement" in raw_lower:
        return "lateral_movement"
    if "exfil" in raw_lower or "data" in raw_lower:
        return "data_exfiltration"
    if "threat" in raw_lower or "intel" in raw_lower or "malicious" in raw_lower:
        return "threat_intel_match"
    if "insider" in raw_lower:
        return "insider_threat"
    if "cloud" in raw_lower or "azure" in raw_lower or "aws" in raw_lower:
        return "cloud_infrastructure"
    logger.warning("[Sentinel] Unknown category %r → credential_access", raw_category)
    return "credential_access"


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

_SEVERITY_MAP = {
    "High":          "HIGH",
    "high":          "HIGH",
    "Medium":        "MEDIUM",
    "medium":        "MEDIUM",
    "Low":           "LOW",
    "low":           "LOW",
    "Informational": "LOW",
    "informational": "LOW",
    "Critical":      "CRITICAL",
    "critical":      "CRITICAL",
}


def _normalize_sentinel_alert(raw: dict) -> dict:
    """
    Normalize a Sentinel alerts_v2 response object to SituationAnalyzer schema.

    Sentinel field          → SituationAnalyzer field
    -------------------------------------------------------
    alertDisplayName/title  → alert_type
    severity                → severity  (HIGH / MEDIUM / LOW / CRITICAL)
    entities[Account].upn   → user
    entities[Host].hostName → asset
    createdDateTime         → timestamp  (epoch ms)
    category / alertType    → category   (via SENTINEL_CATEGORY_MAP)
    entities[Account].isPrivileged → is_executive
    severity HIGH/CRITICAL  → is_critical
    entities[Ip].threatIntel → has_ioc
    incidentId / correlationId → campaign
    """
    raw_severity  = raw.get("severity", "Medium")
    severity      = _SEVERITY_MAP.get(raw_severity, "MEDIUM")

    raw_category  = raw.get("category", "") or raw.get("alertType", "") or ""
    category      = _map_sentinel_category(raw_category)

    # User — prefer top-level field, then Account entity
    user = raw.get("userPrincipalName", "")
    if not user:
        for entity in raw.get("entities", []):
            if entity.get("kind") == "Account":
                user = (entity.get("userPrincipalName")
                        or entity.get("accountName")
                        or "")
                if user:
                    break
    user = user or "unknown"

    # Asset — prefer top-level DNS name, then Host entity
    asset = raw.get("computerDnsName", "")
    if not asset:
        for entity in raw.get("entities", []):
            if entity.get("kind") == "Host":
                asset = (entity.get("hostName")
                         or entity.get("dnsDomain")
                         or "")
                if asset:
                    break
    asset = asset or "unknown"

    # Timestamp
    raw_ts = raw.get("createdDateTime") or raw.get("timeGenerated") or ""
    try:
        if raw_ts:
            dt        = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
            timestamp = int(dt.timestamp() * 1000)
        else:
            timestamp = int(time.time() * 1000)
    except Exception:
        timestamp = int(time.time() * 1000)

    # is_executive: privileged account entity
    is_executive = any(
        e.get("kind") == "Account" and e.get("isPrivileged")
        for e in raw.get("entities", [])
    )

    # is_critical: HIGH or CRITICAL severity
    is_critical = severity in ("HIGH", "CRITICAL")

    # has_ioc: threat intelligence present on any entity
    has_ioc = any(
        e.get("threatIntelligence") or e.get("kind") == "Ip"
        for e in raw.get("entities", [])
    )

    # campaign
    campaign = raw.get("incidentId") or raw.get("correlationId") or ""

    return {
        "id":            raw.get("id") or raw.get("systemAlertId") or "",
        "alert_type":    raw.get("alertDisplayName") or raw.get("title") or raw_category,
        "severity":      severity,
        "user":          user,
        "asset":         asset,
        "timestamp":     timestamp,
        "category":      category,
        "is_executive":  is_executive,
        "is_critical":   is_critical,
        "has_ioc":       has_ioc,
        "campaign":      campaign,
        # Preserve raw for debugging
        "_raw_category": raw_category,
        "_source":       "sentinel_real",
    }


# ---------------------------------------------------------------------------
# Connector class
# ---------------------------------------------------------------------------

class SentinelRealConnector:
    """
    Real Microsoft Sentinel connector via Graph Security API.

    Auth: OAuth2 client_credentials flow (msal).
    Requires: pip install msal httpx
    """

    def __init__(self) -> None:
        self.tenant_id      = os.getenv("SENTINEL_TENANT_ID", "")
        self.client_id      = os.getenv("SENTINEL_CLIENT_ID", "")
        self.client_secret  = os.getenv("SENTINEL_CLIENT_SECRET", "")
        self.workspace_id   = os.getenv("SENTINEL_WORKSPACE_ID", "")
        self._token:        Optional[str]   = None
        self._token_expiry: float           = 0.0

    def is_configured(self) -> bool:
        """True only when all three required credentials are present."""
        return bool(self.tenant_id and self.client_id and self.client_secret)

    async def get_token(self) -> Optional[str]:
        """Acquire (or return cached) OAuth2 access token via msal."""
        if self._token and time.time() < self._token_expiry - 60:
            return self._token
        try:
            import msal  # optional dependency
        except ImportError:
            logger.error("[Sentinel] msal not installed — run: pip install msal")
            return None
        try:
            app    = msal.ConfidentialClientApplication(
                self.client_id,
                authority=f"https://login.microsoftonline.com/{self.tenant_id}",
                client_credential=self.client_secret,
            )
            result = app.acquire_token_for_client(
                scopes=["https://graph.microsoft.com/.default"]
            )
            if "access_token" in result:
                self._token        = result["access_token"]
                self._token_expiry = time.time() + result.get("expires_in", 3600)
                logger.info("[Sentinel] Token acquired (expires in %ds)",
                            result.get("expires_in", 3600))
                return self._token
            logger.error("[Sentinel] Token error: %s",
                         result.get("error_description", "unknown"))
            return None
        except Exception as exc:
            logger.error("[Sentinel] Token acquisition failed: %s", exc)
            return None

    async def push_incident_update(
        self,
        incident_id: str,
        action: str,
        confidence: float,
        decision_id: str,
        campaign_id: Optional[str] = None,
    ) -> dict:
        """
        Write-back a triage decision to a Sentinel incident via Graph Security API.

        PATCH /security/incidents/{incident_id}

        Payload:
          - classification: maps action → Sentinel enum
          - determination:  always "unknown" (Copilot does not set determination)
          - customProperties: action, confidence, decision_id, campaign_id, source

        Returns dict with keys: success (bool), status_code (int|None), error (str|None).
        Never raises — callers fire-and-forget without awaiting result.
        """
        if not self.is_configured():
            logger.warning("[Sentinel-WB] Not configured — write-back skipped for %s", incident_id)
            return {"success": False, "status_code": None, "error": "not_configured"}

        token = await self.get_token()
        if not token:
            return {"success": False, "status_code": None, "error": "no_token"}

        try:
            import httpx
        except ImportError:
            logger.error("[Sentinel-WB] httpx not installed")
            return {"success": False, "status_code": None, "error": "httpx_missing"}

        # Map internal action → Sentinel classification enum
        _CLASSIFICATION_MAP = {
            "escalate":   "truePositive",
            "investigate": "truePositive",
            "suppress":   "falsePositive",
            "monitor":    "benignPositive",
        }
        classification = _CLASSIFICATION_MAP.get(action, "unknown")

        payload = {
            "classification": classification,
            "determination":  "unknown",
            "customProperties": {
                "copilot_action":      action,
                "copilot_confidence":  str(round(confidence, 4)),
                "copilot_decision_id": decision_id,
                "copilot_campaign_id": campaign_id or "",
                "copilot_source":      "soc-copilot-v5",
            },
        }

        try:
            url = f"https://graph.microsoft.com/v1.0/security/incidents/{incident_id}"
            async with httpx.AsyncClient(timeout=15.0) as http:
                resp = await http.patch(
                    url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type":  "application/json",
                    },
                    json=payload,
                )
            if resp.status_code in (200, 204):
                logger.info(
                    "[Sentinel-WB] incident=%s patched — action=%s conf=%.3f",
                    incident_id, action, confidence,
                )
                return {"success": True, "status_code": resp.status_code, "error": None}
            logger.error(
                "[Sentinel-WB] PATCH %s failed — status=%d body=%s",
                incident_id, resp.status_code, resp.text[:200],
            )
            return {"success": False, "status_code": resp.status_code, "error": resp.text[:200]}
        except Exception as exc:
            logger.error("[Sentinel-WB] PATCH exception for incident=%s: %s", incident_id, exc)
            return {"success": False, "status_code": None, "error": str(exc)}

    async def fetch_alerts(self, top: int = 50) -> List[dict]:
        """
        Fetch latest alerts from Graph Security API (alerts_v2).
        Returns list of normalized SituationAnalyzer dicts.
        Returns [] on any failure — never raises.
        """
        if not self.is_configured():
            logger.warning("[Sentinel] Not configured — credentials absent from env")
            return []

        token = await self.get_token()
        if not token:
            return []

        try:
            import httpx  # optional dependency — already in requirements.txt
        except ImportError:
            logger.error("[Sentinel] httpx not installed — run: pip install httpx")
            return []

        try:
            url    = "https://graph.microsoft.com/v1.0/security/alerts_v2"
            params: dict = {
                "$top":     min(top, 999),
                "$orderby": "createdDateTime desc",
            }
            if self.workspace_id:
                params["$filter"] = f"azureTenantId eq '{self.tenant_id}'"

            async with httpx.AsyncClient(timeout=30.0) as http:
                resp = await http.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                    params=params,
                )
                resp.raise_for_status()
                data = resp.json()

            raw_alerts = data.get("value", [])
            normalized = [_normalize_sentinel_alert(a) for a in raw_alerts]
            logger.info("[Sentinel] Fetched %d alerts", len(normalized))
            return normalized

        except Exception as exc:
            logger.error("[Sentinel] Alert fetch failed: %s", exc)
            return []


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_connector: Optional[SentinelRealConnector] = None


def get_sentinel_connector() -> SentinelRealConnector:
    global _connector
    if _connector is None:
        _connector = SentinelRealConnector()
    return _connector
