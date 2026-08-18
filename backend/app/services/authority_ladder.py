"""Persisted SOC authority ladder and decision-path conservation veto."""

from __future__ import annotations

import os
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any, Mapping

from copilot_sdk.promotion import (
    PromotionEngine,
    PromotionRecord,
    PromotionStage,
    PromotionStore,
    SOCPromotionPolicy,
)


logger = logging.getLogger(__name__)


SOC_ALERT_CATEGORIES: tuple[str, ...] = (
    "malware_delivery",
    "phishing",
    "lateral_movement",
    "credential_access",
    "data_exfiltration",
    "insider_threat",
)

_RUNG_BY_STAGE = {
    PromotionStage.DISCOVERED: "observed",
    PromotionStage.SHADOWING: "assisted",
    PromotionStage.PROMOTED: "shadow-qualified",
    PromotionStage.KEPT: "auto-approved",
    PromotionStage.ROLLED_BACK: "circuit-broken",
}


@dataclass(frozen=True)
class AuthorityDecision:
    category: str
    authority: str
    conservation: str
    allowed: bool
    reason: str | None
    would_have_action: str
    audit_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "authority": self.authority,
            "conservation": self.conservation,
            "allowed": self.allowed,
            "reason": self.reason,
            "would_have_action": self.would_have_action,
            "audit_id": self.audit_id,
        }


class AuthorityManager:
    """SOC's per-alert-class authority facade over the shared state machine."""

    def __init__(
        self,
        db_path: str | os.PathLike[str] | None = None,
        conservation_provider: Any | None = None,
        store: PromotionStore | None = None,
    ) -> None:
        configured = db_path or os.environ.get("SOC_AUTHORITY_DB_PATH")
        if configured is None:
            configured = Path(__file__).resolve().parents[2] / "data" / "soc_authority.sqlite3"
        self.db_path = str(configured)
        if store is None and self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.store = store or PromotionStore(self.db_path)
        self.engine = PromotionEngine(
            SOCPromotionPolicy(),
            store=self.store,
            conservation_provider=conservation_provider,
        )
        self._lock = RLock()
        self._audit = sqlite3.connect(self.db_path, check_same_thread=False)
        self._audit.execute(
            """CREATE TABLE IF NOT EXISTS authority_veto_audit (
                audit_id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                authority TEXT NOT NULL,
                conservation TEXT NOT NULL,
                reason TEXT NOT NULL,
                would_have_action TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        self._audit.commit()
        self.initialize()

    def initialize(self) -> None:
        """Create missing category records without overwriting persisted state."""
        with self._lock:
            for category in SOC_ALERT_CATEGORIES:
                if self.store.load_by_class("soc", category) is None:
                    self.engine.create("soc", category, record_id=f"soc-authority-{category}")

    def get_record(self, category: str) -> PromotionRecord:
        if not self._validate_category(category):
            raise ValueError(f"Unknown SOC alert category: {category}")
        record = self.store.load_by_class("soc", category)
        if record is None:
            self.initialize()
            record = self.store.load_by_class("soc", category)
        if record is None:  # pragma: no cover - defensive after initialize
            raise RuntimeError(f"Authority record unavailable for {category}")
        return record

    def get_authority(self, category: str) -> str:
        return _RUNG_BY_STAGE[self.get_record(category).current_stage]

    def get_all(self) -> list[dict[str, Any]]:
        return [self._record_payload(self.get_record(category)) for category in SOC_ALERT_CATEGORIES]

    def get_detail(self, category: str) -> dict[str, Any]:
        record = self.get_record(category)
        payload = self._record_payload(record)
        payload["veto_audit"] = self.list_veto_audit(category)
        return payload

    def advance(self, category: str, evidence: Mapping[str, Any] | None = None) -> dict[str, Any]:
        record = self.get_record(category)
        evidence_map = dict(evidence or {})
        current = _status(evidence_map.get("conservation_state"))
        if current == "UNKNOWN" and self.engine.conservation_provider is not None:
            provider = self.engine.conservation_provider
            raw = provider.get_state() if callable(getattr(provider, "get_state", None)) else provider()
            current = _status(raw)
        if current == "RED":
            return {
                "advanced": False,
                "new_stage": record.current_stage.value,
                "authority": _RUNG_BY_STAGE[record.current_stage],
                "reason": "conservation_red",
                "record": self._record_payload(record),
            }
        result = self.engine.advance(record.record_id, evidence_map)
        return {
            "advanced": result.advanced,
            "new_stage": result.new_stage.value,
            "authority": _RUNG_BY_STAGE[result.new_stage],
            "reason": result.reason,
            "record": self._record_payload(result.record or self.get_record(category)),
        }

    def circuit_break(self, category: str, reason: str = "manual_circuit_break") -> dict[str, Any]:
        record = self.get_record(category)
        result = self.engine.rollback(record.record_id, reason)
        return {
            "advanced": result.advanced,
            "new_stage": result.new_stage.value,
            "authority": _RUNG_BY_STAGE[result.new_stage],
            "reason": result.reason,
            "record": self._record_payload(result.record or self.get_record(category)),
        }

    def evaluate(
        self,
        category: str,
        proposed_action: str,
        conservation: str | Mapping[str, Any] | None = None,
        decision_id: str | None = None,
    ) -> AuthorityDecision:
        if not self._validate_category(category):
            # Unknown alert types are valid inputs to the SOC triage surface,
            # but have no promoted authority policy. Fail safe to observation
            # and force analyst referral instead of crashing the pipeline.
            conservation_status = _status(conservation)
            return AuthorityDecision(
                category=category,
                authority="observed",
                conservation=conservation_status,
                allowed=False,
                reason="unknown_category",
                would_have_action=proposed_action,
            )
        record = self.get_record(category)
        authority = _RUNG_BY_STAGE[record.current_stage]
        conservation_status = _status(conservation)
        reason: str | None = None
        if conservation_status == "RED":
            reason = "conservation_red"
        elif authority == "circuit-broken":
            reason = "circuit_broken"
        elif proposed_action != "refer_to_analyst" and authority != "auto-approved":
            reason = "authority_not_auto_approved"

        if reason is None:
            return AuthorityDecision(
                category, authority, conservation_status, True, None, proposed_action
            )

        # Use a unique ID without adding a dependency.
        import uuid

        audit_id = f"authority-veto-{uuid.uuid4().hex}"
        from datetime import datetime, timezone

        with self._lock:
            self._audit.execute(
                "INSERT INTO authority_veto_audit VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    audit_id,
                    category,
                    authority,
                    conservation_status,
                    reason,
                    proposed_action,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            self._audit.commit()
        return AuthorityDecision(
            category,
            authority,
            conservation_status,
            False,
            reason,
            proposed_action,
            audit_id,
        )

    def list_veto_audit(self, category: str) -> list[dict[str, Any]]:
        self._validate_category(category)
        rows = self._audit.execute(
            "SELECT audit_id, category, authority, conservation, reason, "
            "would_have_action, created_at FROM authority_veto_audit "
            "WHERE category = ? ORDER BY created_at DESC",
            (category,),
        ).fetchall()
        keys = ("audit_id", "category", "authority", "conservation", "reason", "would_have_action", "created_at")
        return [dict(zip(keys, row)) for row in rows]

    @staticmethod
    def _record_payload(record: PromotionRecord) -> dict[str, Any]:
        payload: dict[str, Any] = dict(record.to_dict())
        payload["authority"] = _RUNG_BY_STAGE[record.current_stage]
        return payload

    @staticmethod
    def _validate_category(category: str) -> bool:
        if category not in SOC_ALERT_CATEGORIES:
            logger.warning("Unknown category '%s', defaulting to OBSERVED", category)
            return False
        return True


def _status(raw: str | Mapping[str, Any] | None) -> str:
    if isinstance(raw, Mapping):
        raw = raw.get("status", raw.get("state"))
    value = str(raw or "UNKNOWN").strip().upper()
    return value if value in {"GREEN", "AMBER", "RED"} else "UNKNOWN"


_AUTHORITY_MANAGER = AuthorityManager()


def get_authority_manager() -> AuthorityManager:
    return _AUTHORITY_MANAGER
