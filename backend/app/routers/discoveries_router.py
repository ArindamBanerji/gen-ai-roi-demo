"""FEATURE-07 Cross-Graph Discovery API routes."""

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.db.graph_client import graph_client
from app.domains.soc.config import SOC_CATEGORIES, resolve_alert_category
from app.services.cross_graph_discovery import discovery_service


router = APIRouter()


class CrossCorrelateRequest(BaseModel):
    alert_ids: list[str] = Field(min_length=2, max_length=2)


_KILL_CHAIN_PATTERNS: dict[tuple[str, str], str] = {
    ("credential_access", "lateral_movement"): "credential_access → lateral_movement",
    ("malware_execution", "credential_access"): "malware_execution → credential_access",
    ("credential_access", "data_exfiltration"): "credential_access → data_exfiltration",
    ("cloud_infrastructure", "insider_threat"): "cloud_infrastructure → insider_threat",
}


def _alert_category(alert: dict[str, Any]) -> str:
    category = str(alert.get("category") or "").strip()
    if category in SOC_CATEGORIES:
        return category
    return resolve_alert_category(str(alert.get("alert_type") or ""))


def _action_alone(alert: dict[str, Any]) -> str:
    action = alert.get("action") or alert.get("recommended_action")
    if isinstance(action, dict):
        action = action.get("action")
    if isinstance(action, str) and action.strip():
        return action
    severity = str(alert.get("severity") or "low").lower()
    return "escalate" if severity in {"high", "critical"} else "monitor"


def _shared_entities(first: dict[str, Any], second: dict[str, Any]) -> list[str]:
    shared: list[str] = []
    for field in ("user_id", "asset_id", "source_ip", "destination_ip"):
        first_value = first.get(field)
        second_value = second.get(field)
        if first_value and second_value and str(first_value) == str(second_value):
            shared.append(str(first_value))
    return shared


def _correlation_alert(alert: dict[str, Any], category: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "alert_id": str(alert.get("alert_id") or alert.get("id") or ""),
        "category": category,
        "severity_alone": str(alert.get("severity") or "low"),
        "action_alone": _action_alone(alert),
    }
    for field in ("planted", "sample", "origin", "source", "provenance"):
        if field in alert:
            payload[field] = alert[field]
    return payload


class DiscoveryCacheModel(BaseModel):
    hit: bool = False
    stale: bool = False
    ttl_seconds: int | None = None


class DiscoveryItemModel(BaseModel):
    discovery_id: str
    domain: str
    source_domains: list[str] = Field(default_factory=list)
    type: str
    severity: str
    title: str
    description: str
    score: float
    discovered_at: str
    involved_entity_ids: list[str] = Field(default_factory=list)
    involved_alert_ids: list[str] = Field(default_factory=list)
    involved_decision_ids: list[str] = Field(default_factory=list)
    threat_indicator_ids: list[str] = Field(default_factory=list)
    entity_summary: str = ""
    category_summary: str = ""
    temporal_summary: str = ""
    factor_summary: str = ""


class DiscoveryEnvelopeModel(BaseModel):
    domain: str
    source_domains: list[str] = Field(default_factory=list)
    generated_at: str | None = None
    as_of_epoch_ms: int | None = None
    cache: DiscoveryCacheModel
    discoveries: list[DiscoveryItemModel] = Field(default_factory=list)
    total: int
    errors: list[str] = Field(default_factory=list)


class DiscoverySummaryModel(BaseModel):
    domain: str
    source_domains: list[str] = Field(default_factory=list)
    total: int
    high_count: int
    medium_count: int
    low_count: int
    top_discoveries: list[DiscoveryItemModel] = Field(default_factory=list)
    cache: DiscoveryCacheModel
    errors: list[str] = Field(default_factory=list)


def _validate_domain(domain: str) -> str:
    try:
        return discovery_service.validate_domain(domain)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/discoveries", response_model=DiscoveryEnvelopeModel)
async def get_discoveries(domain: str = Query("soc")):
    domain = _validate_domain(domain)
    cached = discovery_service.get_discoveries(domain)
    if cached is not None:
        return cached
    try:
        return await discovery_service.refresh(domain, graph_client)
    except Exception as exc:
        return {
            "domain": domain,
            "source_domains": [domain],
            "generated_at": None,
            "as_of_epoch_ms": None,
            "cache": {
                "hit": False,
                "stale": False,
                "ttl_seconds": discovery_service.ttl_seconds,
            },
            "discoveries": [],
            "total": 0,
            "errors": [str(exc)],
        }


@router.post("/discoveries/refresh", response_model=DiscoveryEnvelopeModel)
async def refresh_discoveries(domain: str = Query("soc")):
    domain = _validate_domain(domain)
    try:
        return await discovery_service.refresh(domain, graph_client)
    except Exception as exc:
        return {
            "domain": domain,
            "source_domains": [domain],
            "generated_at": None,
            "as_of_epoch_ms": None,
            "cache": {
                "hit": False,
                "stale": False,
                "ttl_seconds": discovery_service.ttl_seconds,
            },
            "discoveries": [],
            "total": 0,
            "errors": [str(exc)],
        }


@router.get("/discoveries/summary", response_model=DiscoverySummaryModel)
async def get_discoveries_summary(domain: str = Query("soc")):
    domain = _validate_domain(domain)
    try:
        return await discovery_service.get_summary(domain, graph_client)
    except Exception as exc:
        return {
            "domain": domain,
            "source_domains": [domain],
            "total": 0,
            "high_count": 0,
            "medium_count": 0,
            "low_count": 0,
            "top_discoveries": [],
            "cache": {
                "hit": False,
                "stale": False,
                "ttl_seconds": discovery_service.ttl_seconds,
            },
            "errors": [str(exc)],
        }


@router.post("/alert/cross-correlate")
async def cross_correlate_alerts(request: CrossCorrelateRequest) -> dict[str, Any]:
    """Detect a known two-alert kill chain using categories and shared entities."""

    alerts: list[dict[str, Any]] = []
    for alert_id in request.alert_ids:
        alert = await graph_client.get_alert(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
        alerts.append(dict(alert))

    first, second = alerts
    first_category = _alert_category(first)
    second_category = _alert_category(second)
    shared_entities = _shared_entities(first, second)
    pattern = _KILL_CHAIN_PATTERNS.get((first_category, second_category)) or _KILL_CHAIN_PATTERNS.get(
        (second_category, first_category)
    )
    pattern_direction = (
        "forward"
        if (first_category, second_category) in _KILL_CHAIN_PATTERNS
        else "reverse"
        if pattern
        else None
    )
    detected = bool(pattern and shared_entities)
    confidence = min(1.0, len(shared_entities) / 4.0) if detected else 0.0

    correlation: dict[str, Any] = {
        "alert_1": _correlation_alert(first, first_category),
        "alert_2": _correlation_alert(second, second_category),
        "kill_chain_detected": detected,
        "kill_chain_pattern": pattern if detected else None,
        "pattern_direction": pattern_direction if detected else None,
        "shared_entities": shared_entities,
        "combined_severity": "critical" if detected else None,
        "recommendation": "Escalate as coordinated attack" if detected else None,
        "confidence": confidence,
        "evidence_tier": "T_H" if detected else None,
    }
    return {
        "correlation": correlation,
        "discovery_note": (
            "Individually benign. Together: kill chain."
            if detected
            else "No known kill chain pattern detected."
        ),
    }
