"""
Admin router -- privileged operations.

POST /api/admin/reset     Atomic soft or hard reset via StateManager.
POST /api/admin/ingest    Ingest alerts from connector or CSV upload.
"""

import dataclasses
import json
import logging
import re
from importlib import util as importlib_util
from datetime import datetime
from typing import Any, Dict, List, Optional, cast

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()
log = logging.getLogger(__name__)

_VALID_MODES = {"soft", "hard"}
_VALID_ONBOARD_MODES = {"csv", "sentinel"}
_VALID_NODE_LABELS = {"User", "Asset", "Alert", "AlertType"}
_VALID_REL_TYPES = {"CLASSIFIED_AS", "INVOLVES", "DETECTED_ON"}
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _sanitize_sentinel_health_error(message: str, connector: Any) -> str:
    """Remove connector secrets from a Sentinel health-check error string."""
    sanitized = message or "token acquisition failed"
    for attr in ("client_secret", "client_id", "tenant_id"):
        value = getattr(connector, attr, None)
        if value:
            sanitized = sanitized.replace(str(value), "[redacted]")
    return sanitized


class ResetRequest(BaseModel):
    mode:    str  = "soft"   # "soft" | "hard"
    confirm: bool = False    # must be set to true explicitly -- no default allow


class OnboardRequest(BaseModel):
    mode: str
    alerts: Optional[List[Dict[str, Any]]] = None
    sentinel_config: Optional[Dict[str, Any]] = None
    days_back: int = 30
    limit: int = 10000
    write_graph: bool = True


class _CsvConnector:
    """In-memory onboarding connector for MVP CSV/JSON alert batches."""

    def __init__(self, alerts: List[Dict[str, Any]]):
        self._alerts = list(alerts)

    async def fetch_alerts(
        self,
        since: datetime,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        return self._alerts[:max(limit, 0)]

    async def write_disposition(
        self,
        alert_id: str,
        disposition: Dict[str, Any],
    ) -> bool:
        return False

    async def health_check(self) -> Dict[str, Any]:
        return {
            "read": True,
            "write": False,
            "source": "csv",
            "alerts": len(self._alerts),
        }


@router.post("/admin/reset")
async def admin_reset(body: ResetRequest):
    """
    Atomically reset GAE learning state, audit chain, and AGE.

    - **soft**: reset W -> priors, clear Decision outcomes (keep nodes), fresh audit chain.
    - **hard**: same as soft, plus delete Decision nodes and re-seed graph.

    `confirm` must be `true` -- acts as an explicit safety acknowledgement.

    Returns
    -------
    {
      "status": "reset_complete",
      "mode":   "soft" | "hard",
      "learning_state": {"W_shape": [n_a, n_f], "decision_count": 0}
    }
    """
    if not body.confirm:
        raise HTTPException(
            status_code=400,
            detail="confirm must be true to execute a reset",
        )

    if body.mode not in _VALID_MODES:
        raise HTTPException(
            status_code=400,
            detail=f"mode must be one of {sorted(_VALID_MODES)}",
        )

    from app.services.state_manager import StateManager, ResetError
    from app.services import gae_state, audit as audit_store
    from app.db.graph_client import graph_client
    from app.core.domain_registry import get_domain_config

    sm = StateManager(
        learning_state_service=gae_state,
        audit_store=audit_store,
        graph_service=graph_client,
        domain_config=get_domain_config(),
    )

    try:
        if body.mode == "soft":
            learning_state = await sm.soft_reset()
        else:
            learning_state = await sm.hard_reset()
    except ResetError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "status":         "reset_complete",
        "mode":           body.mode,
        "learning_state": learning_state,
    }


def _safe_identifier(value: str, allowed: set[str], kind: str) -> str:
    if value not in allowed or not _IDENT_RE.match(value):
        raise ValueError(f"unsupported {kind}: {value!r}")
    return value


def _age_literal(value: Any) -> str:
    from app.graph_schema import _S

    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (list, tuple, dict)):
        return cast(str, _S(json.dumps(value)))
    return cast(str, _S(value))


def _props_clause(props: Dict[str, Any]) -> str:
    safe_items = [
        (key, value)
        for key, value in props.items()
        if _IDENT_RE.match(str(key))
    ]
    return ", ".join(
        f"{key}: {_age_literal(value)}" for key, value in safe_items
    )


def _set_clause(alias: str, props: Dict[str, Any]) -> str:
    safe_items = [
        (key, value)
        for key, value in props.items()
        if key != "id" and _IDENT_RE.match(str(key))
    ]
    return ", ".join(
        f"{alias}.{key} = {_age_literal(value)}" for key, value in safe_items
    )


async def _write_manifest_to_graph(
    manifest: Any,
    graph_client: Any = None,
) -> Dict[str, Any]:
    if graph_client is None:
        from app.db.graph_client import graph_client

        graph_client = graph_client

    nodes = list(getattr(manifest, "nodes", []) or [])
    relationships = list(getattr(manifest, "relationships", []) or [])
    summary: dict[str, Any] = {
        "nodes_attempted": len(nodes),
        "nodes_written": 0,
        "relationships_attempted": len(relationships),
        "relationships_written": 0,
        "errors": [],
    }
    id_to_label: Dict[str, str] = {}

    for node in nodes:
        try:
            label = _safe_identifier(str(node.get("type", "")), _VALID_NODE_LABELS, "node label")
            node_id = str(node.get("id", ""))
            if not node_id:
                raise ValueError("node missing id")
            id_to_label[node_id] = label
            props = dict(node)
            props.setdefault("id", node_id)
            id_s = _age_literal(node_id)
            existing = await graph_client.run_query(
                f"MATCH (n:{label} {{id: {id_s}}}) RETURN n LIMIT 1"
            )
            set_clause = _set_clause("n", props)
            if existing:
                if set_clause:
                    await graph_client.run_query(
                        f"MATCH (n:{label} {{id: {id_s}}}) SET {set_clause} RETURN n"
                    )
            else:
                await graph_client.run_query(
                    f"CREATE (n:{label} {{{_props_clause(props)}}}) RETURN n"
                )
            summary["nodes_written"] += 1
        except Exception as exc:
            log.warning("Onboarding node write failed: %s", exc)
            summary["errors"].append({"kind": "node", "error": str(exc)})

    for rel in relationships:
        try:
            rel_type = _safe_identifier(
                str(rel.get("type", "")),
                _VALID_REL_TYPES,
                "relationship type",
            )
            from_id = str(rel.get("from", ""))
            to_id = str(rel.get("to", ""))
            from_label = id_to_label.get(from_id)
            to_label = id_to_label.get(to_id)
            if not from_label or not to_label:
                raise ValueError("relationship endpoint missing from manifest nodes")
            from_s = _age_literal(from_id)
            to_s = _age_literal(to_id)
            existing = await graph_client.run_query(
                f"MATCH (src:{from_label} {{id: {from_s}}})"
                f"-[r:{rel_type}]->"
                f"(dst:{to_label} {{id: {to_s}}}) RETURN r LIMIT 1"
            )
            if not existing:
                await graph_client.run_query(
                    f"MATCH (src:{from_label} {{id: {from_s}}}) "
                    f"MATCH (dst:{to_label} {{id: {to_s}}}) "
                    f"CREATE (src)-[:{rel_type}]->(dst)"
                )
            summary["relationships_written"] += 1
        except Exception as exc:
            log.warning("Onboarding relationship write failed: %s", exc)
            summary["errors"].append({"kind": "relationship", "error": str(exc)})

    summary["errors_count"] = len(summary["errors"])
    return summary


def _stage_dict(stage: Any) -> Dict[str, Any]:
    if dataclasses.is_dataclass(stage):
        return dataclasses.asdict(stage)
    if isinstance(stage, dict):
        return dict(stage)
    return {
        "stage": getattr(stage, "stage", None),
        "success": getattr(stage, "success", None),
        "duration_seconds": getattr(stage, "duration_seconds", None),
        "records_in": getattr(stage, "records_in", None),
        "records_out": getattr(stage, "records_out", None),
        "details": getattr(stage, "details", None),
    }


def _manifest_summary(manifest: Any) -> Dict[str, Any]:
    if manifest is None:
        return {
            "node_count": 0,
            "relationship_count": 0,
            "stats": {},
        }
    nodes = list(getattr(manifest, "nodes", []) or [])
    relationships = list(getattr(manifest, "relationships", []) or [])
    return {
        "node_count": len(nodes),
        "relationship_count": len(relationships),
        "stats": dict(getattr(manifest, "stats", {}) or {}),
    }


def _recommended_config(config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    config = dict(config or {})
    return {
        "learning_recommended": config.get("learning_recommended"),
        "sigma_mean": config.get("sigma_mean"),
        "tau_initial": config.get("tau_initial"),
        "noise_classification": config.get("noise_classification"),
        "qualification_entry": config.get("qualification_entry"),
        **config,
    }


def _result_payload(
    body: OnboardRequest,
    result: Any,
    graph_write: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "success": bool(getattr(result, "success", False)),
        "mode": body.mode,
        "stages": [_stage_dict(stage) for stage in (getattr(result, "stages", []) or [])],
        "alerts_imported": getattr(result, "alerts_imported", 0),
        "entities_resolved": getattr(result, "entities_resolved", 0),
        "redactions_applied": getattr(result, "redactions_applied", 0),
        "manifest": _manifest_summary(getattr(result, "load_manifest", None)),
        "graph_write": graph_write,
        "recommended_config": _recommended_config(
            getattr(result, "recommended_config", None)
        ),
        "total_duration_seconds": getattr(result, "total_duration_seconds", None),
    }


def _variant_dict(record: Any) -> Dict[str, Any]:
    from app.services.variant_registry import variant_to_dict

    if hasattr(record, "variant_id"):
        return variant_to_dict(record)
    if isinstance(record, dict):
        return dict(record)
    return {
        "variant_id": str(record),
    }


def _build_connector(body: OnboardRequest) -> Any:
    if body.mode == "csv":
        return _CsvConnector(body.alerts or [])

    if body.mode == "sentinel":
        if not body.sentinel_config:
            raise HTTPException(
                status_code=400,
                detail="sentinel_config is required for sentinel mode",
            )
        from ci_platform.connectors.sentinel import SentinelConfig, SentinelConnector

        allowed_fields = set(SentinelConfig.__dataclass_fields__.keys())
        unknown = sorted(set(body.sentinel_config) - allowed_fields)
        if unknown:
            raise HTTPException(
                status_code=400,
                detail=f"unknown sentinel_config fields: {unknown}",
            )
        config = SentinelConfig(**body.sentinel_config)
        connector = SentinelConnector(config)
        if hasattr(connector, "is_configured") and not connector.is_configured():
            raise HTTPException(
                status_code=400,
                detail=(
                    "sentinel_config must include tenant_id, client_id, "
                    "client_secret, and workspace_id"
                ),
            )
        return connector

    raise HTTPException(
        status_code=400,
        detail=f"mode must be one of {sorted(_VALID_ONBOARD_MODES)}",
    )


@router.post("/admin/ingest")
async def admin_ingest(body: OnboardRequest):
    """
    Ingest alerts from connector or CSV upload.
    """
    if body.mode not in _VALID_ONBOARD_MODES:
        raise HTTPException(
            status_code=400,
            detail=f"mode must be one of {sorted(_VALID_ONBOARD_MODES)}",
        )
    if body.days_back < 1:
        raise HTTPException(status_code=400, detail="days_back must be >= 1")
    if body.limit < 0:
        raise HTTPException(status_code=400, detail="limit must be >= 0")

    from ci_platform.onboarding.pipeline import OnboardingPipeline

    connector = _build_connector(body)
    pipeline = OnboardingPipeline(connector)
    try:
        result = await pipeline.run(days_back=body.days_back, limit=body.limit)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    graph_write = {
        "nodes_attempted": 0,
        "nodes_written": 0,
        "relationships_attempted": 0,
        "relationships_written": 0,
        "errors": [],
        "errors_count": 0,
        "skipped": not body.write_graph,
    }
    if body.write_graph and getattr(result, "load_manifest", None) is not None:
        graph_write = await _write_manifest_to_graph(result.load_manifest)
        graph_write["skipped"] = False

    return _result_payload(body, result, graph_write)


@router.post("/admin/evolution-scan")
async def admin_evolution_scan():
    """Run a manual AgentEvolver scan for graph-driven variant opportunities."""
    from app.db.graph_client import graph_client
    from app.services.variant_generator import VariantGenerator

    try:
        variants = await VariantGenerator().scan_for_opportunities(graph_client)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "success": True,
        "count": len(variants),
        "variants": [_variant_dict(record) for record in variants],
    }


@router.post("/admin/shadow-start")
async def admin_shadow_start(variant_id: str):
    """Start MVP automated shadow evaluation for a candidate AE variant."""
    from app.db.graph_client import graph_client
    from gae.evolution import SHADOW_STARTED, record_evolution_event
    from app.services.shadow_runner import SHADOW_TESTABLE_ARTIFACTS
    from app.services.variant_registry import CANDIDATE, SHADOW, get_variant, transition_status

    variant = get_variant(variant_id)
    if variant is None:
        raise HTTPException(status_code=404, detail=f"Variant {variant_id} not found")
    if variant.status != CANDIDATE:
        raise HTTPException(status_code=400, detail="variant must be candidate to start shadow")
    if variant.artifact_type not in SHADOW_TESTABLE_ARTIFACTS:
        raise HTTPException(
            status_code=400,
            detail=f"artifact_type {variant.artifact_type} is not MVP shadow-testable",
        )

    try:
        await record_evolution_event(
            graph_client=graph_client,
            event_type=SHADOW_STARTED,
            variant_id=variant_id,
            artifact_type=variant.artifact_type,
            description=f"Shadow started for {variant_id}",
            before_state={"status": CANDIDATE},
            after_state={"status": SHADOW},
            graph_context=variant.graph_trigger or {},
            metadata={"trigger_key": variant.trigger_key},
            impact="operational",
            magnitude=0.0,
        )
        transition_status(variant_id, SHADOW)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {"success": True, "variant_id": variant_id, "status": SHADOW}


@router.post("/admin/promote-evaluate")
async def admin_promote_evaluate(variant_id: Optional[str] = None):
    """Evaluate and apply AE-03 promotion gate decision for a shadow variant."""
    if not variant_id:
        raise HTTPException(status_code=400, detail="variant_id is required")

    from app.db.graph_client import graph_client
    from app.services.promotion_gate import (
        evaluate_promotion,
        execute_promotion,
        execute_rejection,
    )
    from app.services.variant_registry import get_variant

    variant = get_variant(variant_id)
    if variant is None:
        raise HTTPException(status_code=404, detail=f"Variant {variant_id} not found")

    try:
        result = await evaluate_promotion(variant_id, graph_client)
        if result.verdict == "promote":
            await execute_promotion(variant_id, result.gate_evidence or {}, graph_client)
        elif result.verdict == "reject":
            await execute_rejection(variant_id, result.reason, graph_client)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "variant_id": variant_id,
        "verdict": result.verdict,
        "reason": result.reason,
        "gate_evidence": result.gate_evidence,
    }


@router.get("/admin/sentinel-health")
async def sentinel_health():
    """
    Validate Microsoft Sentinel credential wiring without running data queries.

    Uses the SOC Sentinel connector's token path only. It intentionally avoids
    fetch_alerts/KQL so the endpoint is safe for admin health checks.
    """
    from app.connectors.sentinel_real import get_sentinel_connector

    connector = get_sentinel_connector()
    if not connector.is_configured():
        return {
            "status": "not_configured",
            "token_valid": False,
            "details": "Sentinel credentials are not configured",
        }

    if importlib_util.find_spec("msal") is None:
        return {
            "status": "auth_error",
            "token_valid": False,
            "error": "msal not installed",
        }

    try:
        token = await connector.get_token()
    except Exception as exc:
        return {
            "status": "auth_error",
            "token_valid": False,
            "error": _sanitize_sentinel_health_error(str(exc), connector),
        }

    if token:
        return {
            "status": "configured",
            "token_valid": True,
        }

    return {
        "status": "auth_error",
        "token_valid": False,
        "error": "token acquisition failed",
    }
