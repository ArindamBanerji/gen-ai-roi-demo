from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger(__name__)

SUMMARY_LIMIT = 20
EXPORT_LIMIT = 10000
FORMAT_VERSION = "1.0"
PRODUCT_NAME = "SOC Copilot"
KNOWN_STATUSES = {"GREEN", "AMBER", "RED", "CALIBRATING", "UNKNOWN"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp_rate(value: Any) -> float:
    return max(0.0, min(1.0, _safe_float(value)))


def _truncate(value: Any, length: int = 12) -> str:
    text = "" if value is None else str(value)
    return text[:length]


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "tolist"):
        return _json_safe(value.tolist())
    return str(value)


def _empty_audit_trail() -> dict[str, Any]:
    return {"entries": [], "total": 0}


def _empty_hash_chain() -> dict[str, Any]:
    return {"verified": True, "entries": 0, "status": "VERIFIED"}


def _empty_conservation() -> dict[str, Any]:
    return {
        "status": "UNKNOWN",
        "product": 0.0,
        "threshold": 0.0,
        "verified_decisions": 0,
        "frozen": False,
    }


def _empty_override_analysis() -> dict[str, Any]:
    return {
        "total": 0,
        "overrides": 0,
        "confirmations": 0,
        "override_rate": 0.0,
        "per_category": {},
    }


class EvidenceRoomService:
    async def get_evidence_summary(self) -> dict[str, Any]:
        audit_trail, hash_chain, rows = await self._collect_audit(export=False)
        conservation = await self._collect_conservation()
        override_analysis = await self._collect_override_analysis(rows)
        return _json_safe({
            "generated_at": _now_iso(),
            "audit_trail": audit_trail,
            "conservation": conservation,
            "override_analysis": override_analysis,
            "hash_chain": hash_chain,
        })

    async def export_evidence_pack(self) -> dict[str, Any]:
        audit_trail, hash_chain, rows = await self._collect_audit(export=True)
        conservation = await self._collect_conservation()
        override_analysis = await self._collect_override_analysis(rows)
        return _json_safe({
            "generated_at": _now_iso(),
            "export_metadata": {
                "exported_at": _now_iso(),
                "format_version": FORMAT_VERSION,
                "product": PRODUCT_NAME,
            },
            "audit_trail": audit_trail,
            "conservation": conservation,
            "override_analysis": override_analysis,
            "hash_chain": hash_chain,
        })

    async def _collect_audit(self, export: bool) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
        try:
            from app.framework.audit import get_decision_rows, reconstruct_from_memory, verify_chain

            await reconstruct_from_memory()
            rows = list(get_decision_rows() or [])
            verification = verify_chain() or {}
        except Exception as exc:
            log.warning("[EvidenceRoom] audit collection failed: %s", exc)
            return _empty_audit_trail(), _empty_hash_chain(), []

        limit = EXPORT_LIMIT if export else SUMMARY_LIMIT
        entries = [
            self._format_export_entry(row) if export else self._format_summary_entry(row)
            for row in rows[:limit]
        ]
        verified = bool(verification.get("verified", True))
        chain_entries = _safe_int(verification.get("chain_length"), len(entries))
        return (
            {"entries": entries, "total": len(rows)},
            {
                "verified": verified,
                "entries": chain_entries,
                "status": "VERIFIED" if verified else "BROKEN",
            },
            rows,
        )

    def _format_summary_entry(self, row: dict[str, Any]) -> dict[str, Any]:
        decision_id = row.get("id") or row.get("decision_id") or ""
        entry_hash = row.get("hash") or ""
        return {
            "decision_id": _truncate(decision_id),
            "decision_id_full": str(decision_id),
            "action": row.get("action_taken") or row.get("action") or "",
            "category": row.get("situation_type") or row.get("category") or "unknown",
            "confidence": _safe_float(row.get("confidence")),
            "outcome": row.get("outcome"),
            "timestamp": row.get("timestamp"),
            "hash": _truncate(entry_hash),
        }

    def _format_export_entry(self, row: dict[str, Any]) -> dict[str, Any]:
        decision_id = row.get("id") or row.get("decision_id") or ""
        return {
            "decision_id": str(decision_id),
            "action": row.get("action_taken") or row.get("action") or "",
            "category": row.get("situation_type") or row.get("category") or "unknown",
            "confidence": _safe_float(row.get("confidence")),
            "outcome": row.get("outcome"),
            "timestamp": row.get("timestamp"),
            "hash": row.get("hash") or "",
            "chain_index": row.get("chain_index"),
        }

    async def _collect_conservation(self) -> dict[str, Any]:
        health: dict[str, Any] = {}
        try:
            from app.db.neo4j import neo4j_client
            from app.services.learning_health import LearningHealthMonitor

            health = await LearningHealthMonitor.evaluate(neo4j_client)
        except Exception as exc:
            log.warning("[EvidenceRoom] conservation collection failed: %s", exc)

        status = str(health.get("status", "UNKNOWN")).upper()
        if status not in KNOWN_STATUSES:
            status = "UNKNOWN"

        verified_decisions = 0
        try:
            from app.state.graph_snapshot import get_snapshot

            verified_decisions = _safe_int(get_snapshot().verified_decisions)
        except Exception as exc:
            log.debug("[EvidenceRoom] graph snapshot unavailable for conservation: %s", exc)
            try:
                from app.services.gae_state import get_learning_state

                verified_decisions = _safe_int(get_learning_state().decision_count)
            except Exception as state_exc:
                log.debug("[EvidenceRoom] learning state unavailable for conservation: %s", state_exc)

        return {
            "status": status,
            "product": _safe_float(health.get("signal")),
            "threshold": _safe_float(health.get("theta_min")),
            "verified_decisions": verified_decisions,
            "frozen": bool(health.get("auto_pause_active", False)),
        }

    async def _collect_override_analysis(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(rows)
        overrides = sum(1 for row in rows if bool(row.get("analyst_confirmed")))
        confirmations = sum(1 for row in rows if row.get("outcome") == "correct")
        per_category: dict[str, Any] = {}
        snapshot_rate = None

        try:
            from app.state.graph_snapshot import get_snapshot

            snap = get_snapshot()
            if total == 0:
                total = _safe_int(snap.verified_decisions)
                confirmations = _safe_int(snap.correct_decisions)
                overrides = int(round(_safe_float(snap.override_rate) * total))
            snapshot_rate = _safe_float(snap.override_rate)
            per_category = {
                str(category): {"total": _safe_int(count)}
                for category, count in (snap.category_counts or {}).items()
            }
        except Exception as exc:
            log.debug("[EvidenceRoom] graph snapshot unavailable for override analysis: %s", exc)

        rate = snapshot_rate if snapshot_rate is not None else (overrides / total if total > 0 else 0.0)
        return {
            "total": total,
            "overrides": overrides,
            "confirmations": confirmations,
            "override_rate": _clamp_rate(rate),
            "per_category": per_category,
        }


def dumps_json_safe(payload: dict[str, Any]) -> str:
    return json.dumps(_json_safe(payload), indent=2, sort_keys=True)
