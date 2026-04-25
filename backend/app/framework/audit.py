"""
SOC Audit Service — thin adapter over ci_platform Evidence Ledger.

Hash-chain implementation lives in ci_platform.audit.evidence_ledger (EvidenceLedger /
LedgerEntry).  SOC-specific wrappers handle session state and demo defaults.

Architecture: SOC is a copilot endpoint; shared audit infrastructure lives in ci-platform.
EU AI Act Art. 15 epistemic fields (kernel_type, noise_zone, conservation_status) are
carried by LedgerEntry and surfaced in the SOC API response.

Two population paths (unchanged from before):
  1. record_decision() — called proactively when the agent decides
  2. reconstruct_from_memory() — reads FEEDBACK_GIVEN from feedback_store to
      back-fill records for decisions already made in the session
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

log = logging.getLogger(__name__)

from ci_platform.audit.evidence_ledger import EvidenceLedger, LedgerEntry, OutcomeEntry


# ── Module-level ledger (in-memory, demo-session scoped) ─────────────────────

_LEDGER: EvidenceLedger = EvidenceLedger()
_ledger_lock = asyncio.Lock()

# situation_type is SOC-specific (not in LedgerEntry); stored in parallel
_SITUATION_TYPES: Dict[str, str] = {}   # decision_id → situation_type

# Epoch archive: each hard-reset snapshot is preserved here so audit history
# survives demo cycling. Indexed by epoch (0 = oldest).
_ARCHIVED_EPOCHS: List[List[LedgerEntry]] = []


# ── SOC demo defaults (used by reconstruct_from_memory) ──────────────────────

_ALERT_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "ALERT-7823": {
        "situation_type": "travel_login_anomaly",
        "action_taken":   "false_positive_close",
        "factors":        [
            "user_traveling",
            "vpn_matches_location",
            "mfa_completed",
            "device_fingerprint_match",
        ],
        "confidence": 0.92,
    },
    "ALERT-7824": {
        "situation_type": "known_phishing_campaign",
        "action_taken":   "auto_remediate",
        "factors":        [
            "known_campaign_signature",
            "pattern_matched",
            "sender_domain_blocked",
        ],
        "confidence": 0.94,
    },
}

_DEFAULT_CTX: Dict[str, Any] = {
    "situation_type": "unknown",
    "action_taken":   "escalate_tier2",
    "factors":        ["manual_review_required"],
    "confidence":     0.60,
}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _entry_to_dict(entry: LedgerEntry) -> Dict[str, Any]:
    """Map a LedgerEntry to the SOC DecisionRecord dict expected by callers."""
    outcome_val = None if entry.outcome in ("pending", "system") else entry.outcome
    return {
        "id":                  entry.decision_id,
        "alert_id":            entry.alert_id,
        "timestamp":           entry.timestamp,
        "situation_type":      _SITUATION_TYPES.get(entry.decision_id, "unknown"),
        "action_taken":        entry.action,
        "factors":             list(entry.factor_breakdown.keys()),
        "confidence":          entry.confidence,
        "outcome":             outcome_val,
        "analyst_confirmed":   entry.analyst_override,
        "hash":                entry.entry_hash,
        "chain_index":         entry.chain_index,
        # EU AI Act Art. 15 epistemic fields from ci_platform LedgerEntry
        "kernel_type":         entry.kernel_type,
        "noise_zone":          entry.noise_zone,
        "conservation_status": entry.conservation_status,
    }


def _outcome_to_dict(entry: OutcomeEntry) -> Dict[str, Any]:
    """Convert OutcomeEntry to API-friendly dict."""
    return {
        "type":                "outcome",
        "decision_id":         entry.decision_id,
        "decision_entry_hash": entry.decision_entry_hash,
        "outcome":             entry.outcome,
        "analyst_override":    entry.analyst_override,
        "timestamp":           entry.timestamp,
        "hash":                entry.entry_hash,
        "chain_index":         entry.chain_index,
    }


# ── Core functions ────────────────────────────────────────────────────────────

async def record_decision(
    alert_id: str,
    situation_type: str,
    action_taken: str,
    factors: List[str],
    confidence: float,
    kernel_type: Optional[str] = None,
    noise_zone: Optional[str] = None,
    conservation_status: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Append a sealed LedgerEntry to the ci_platform ledger and return it as a SOC dict.

    Intended to be called when the agent makes a decision (Tab 3 analysis).
    """
    async with _ledger_lock:
        decision_id = str(uuid4())
        entry = _LEDGER.append(
            decision_id=decision_id,
            alert_id=alert_id,
            factor_breakdown={f: 1.0 for f in factors} if factors else {},
            action=action_taken,
            confidence=confidence,
            outcome="pending",
            analyst_override=False,
            centroid_state_hash="",
            kernel_type=kernel_type,
            noise_zone=noise_zone,
            conservation_status=conservation_status,
        )
        _SITUATION_TYPES[decision_id] = situation_type
    print(f"[AUDIT] Recorded decision {decision_id} for {alert_id} -> {action_taken}")
    return _entry_to_dict(entry)


async def record_outcome(
    decision_id: str,
    outcome: str,
    analyst_override: bool = False,
) -> Optional[Dict[str, Any]]:
    """Record a verified outcome as a separate chain entry."""
    async with _ledger_lock:
        decision_entry = None
        for e in _LEDGER.entries():
            if isinstance(e, LedgerEntry) and e.decision_id == decision_id:
                decision_entry = e
                break

        if decision_entry is None:
            log.warning(f"[AUDIT] No decision entry for {decision_id}")
            return None

        entry = _LEDGER.append_outcome(
            decision_id=decision_id,
            decision_entry_hash=decision_entry.entry_hash,
            outcome=outcome,
            analyst_override=analyst_override,
        )
        return _outcome_to_dict(entry)


def get_decision_rows() -> List[Dict[str, Any]]:
    """Project mixed chain into one-row-per-decision, most recent first."""
    entries = _LEDGER.entries() if _LEDGER else []
    # Build outcome lookup: decision_id → latest OutcomeEntry
    outcomes: Dict[str, OutcomeEntry] = {}
    for e in entries:
        if isinstance(e, OutcomeEntry):
            outcomes[e.decision_id] = e
    # Build rows — one per decision, excluding RESET sentinels
    rows = []
    for e in entries:
        if isinstance(e, LedgerEntry) and e.alert_id != "__RESET__":
            row = _entry_to_dict(e)
            oe = outcomes.get(e.decision_id)
            if oe:
                row["outcome"] = oe.outcome
                row["analyst_confirmed"] = oe.analyst_override
            rows.append(row)
    return list(reversed(rows))


async def reconstruct_from_memory() -> int:
    """Reconstruct outcome events from FEEDBACK_GIVEN."""
    from app.framework.feedback_store import FEEDBACK_GIVEN  # noqa: PLC0415

    async with _ledger_lock:
        added = 0
        for alert_id, fb in FEEDBACK_GIVEN.items():
            did = fb.get("decision_id")
            if not did:
                continue
            has_outcome = any(
                isinstance(e, OutcomeEntry) and e.decision_id == did
                for e in _LEDGER.entries()
            )
            if has_outcome:
                continue
            decision_entry = None
            for e in _LEDGER.entries():
                if isinstance(e, LedgerEntry) and e.decision_id == did:
                    decision_entry = e
                    break
            if decision_entry is None:
                continue
            try:
                _LEDGER.append_outcome(
                    decision_id=did,
                    decision_entry_hash=decision_entry.entry_hash,
                    outcome=fb.get("outcome", "pending"),
                    analyst_override=True,
                    timestamp=fb.get("timestamp"),
                )
                added += 1
            except ValueError:
                pass  # hash mismatch — skip silently

    print(f"[AUDIT] reconstruct_from_memory: +{added} outcome entries ({len(_LEDGER)} total)")
    return added


async def rebuild_chain_from_graph(client: Any) -> int:
    """
    Rehydrate the audit hash-chain from persistent Decision nodes in AGE.

    Called once at startup to restore the chain after a server restart.
    Idempotent: returns 0 immediately if the ledger already has entries.

    Uses _LEDGER.append() DIRECTLY (not record_decision) so existing
    decision_ids are preserved and chronological order is maintained.
    ORDER BY ASC is critical — each append() hashes the previous entry.
    """
    rows = await client.run_query(
        "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) "
        "WHERE d.origin = 'zero_day_synthetic' "
        "RETURN d.decision_id AS decision_id, "
        "       a.alert_id    AS alert_id, "
        "       d.category    AS category, "
        "       d.action      AS action, "
        "       d.confidence  AS confidence, "
        "       d.correct     AS correct, "
        "       d.timestamp_epoch AS ts "
        "ORDER BY d.timestamp_epoch ASC "
        "LIMIT 50"
    )

    async with _ledger_lock:
        if len(_LEDGER._entries) > 0:
            return 0

        n = 0
        for row in rows:
            _LEDGER.append(
                decision_id=str(row.get("decision_id") or ""),
                alert_id=str(row.get("alert_id") or ""),
                factor_breakdown={row.get("category", "unknown"): 1.0},
                action=str(row.get("action") or ""),
                confidence=float(row.get("confidence") or 0.0),
                outcome=row.get("correct", "unknown"),
                analyst_override=False,
                centroid_state_hash="",
            )
            n += 1

    print(f"[STARTUP] Audit chain rebuilt: {n} entries (ascending)")
    return n


async def rebuild_from_age() -> int:
    """Rebuild the audit ledger from Decision nodes in AGE.

    Called once during startup to restore the hash chain after restart.
    Skipped (returns 0) if the ledger already has entries (hot reload).
    """
    from app.db.neo4j import neo4j_client  # noqa: PLC0415

    rows = await neo4j_client.run_query(
        "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) "
        "WHERE d.timestamp_epoch IS NOT NULL "
        "RETURN d.decision_id AS decision_id, "
        "d.action AS action, "
        "d.confidence AS confidence, "
        "d.timestamp_epoch AS ts, "
        "a.alert_id AS alert_id, "
        "d.correct AS correct, "
        "d.outcome AS outcome "
        "ORDER BY d.timestamp_epoch ASC"
    )

    async with _ledger_lock:
        if len(_LEDGER._entries) > 0:
            return 0

        n = 0
        for row in rows:
            correct = row.get("correct")
            outcome_raw = row.get("outcome")
            if correct is True:
                outcome = "correct"
            elif correct is False:
                outcome = "incorrect"
            elif outcome_raw:
                outcome = str(outcome_raw)
            else:
                outcome = "pending"

            ts_ms = row.get("ts")
            ts_iso = (
                datetime.fromtimestamp(float(ts_ms) / 1000, tz=timezone.utc).isoformat()
                if ts_ms is not None
                else datetime.now(timezone.utc).isoformat()
            )

            _LEDGER.append(
                decision_id=str(row.get("decision_id") or ""),
                alert_id=str(row.get("alert_id") or ""),
                factor_breakdown={},
                action=str(row.get("action") or ""),
                confidence=float(row.get("confidence") or 0.0),
                outcome=outcome,
                analyst_override=False,
                centroid_state_hash="",
                timestamp=ts_iso,
            )
            n += 1

    print(f"[AUDIT] Rebuilt {n} entries from AGE")
    return n


async def reset_audit_state() -> None:
    """Archive current epoch then start fresh."""
    async with _ledger_lock:
        if _LEDGER._entries:
            _ARCHIVED_EPOCHS.append(list(_LEDGER._entries))
            print(
                f"[AUDIT] Archived epoch {len(_ARCHIVED_EPOCHS)} "
                f"({len(_ARCHIVED_EPOCHS[-1])} entries)"
            )
        _LEDGER._entries.clear()
        _SITUATION_TYPES.clear()
    print("[AUDIT] Decision ledger cleared")


async def record_reset_marker(mode: str) -> None:
    """
    Write a RESET sentinel after reset_audit_state() so the next real
    decision chains off a known anchor, not a silent genesis.

    The marker uses alert_id='__RESET__' so callers can filter it out.
    Called by StateManager after clearing the ledger.
    """
    async with _ledger_lock:
        _LEDGER.append(
            decision_id=str(uuid4()),
            alert_id="__RESET__",
            factor_breakdown={f"mode={mode}": 1.0},
            action=f"reset_{mode}",
            confidence=1.0,
            outcome="system",
            analyst_override=False,
            centroid_state_hash="",
        )
    print(f"[AUDIT] RESET marker written (mode={mode})")


def verify_chain() -> Dict[str, Any]:
    """
    Verify the SHA-256 hash chain via ci_platform EvidenceLedger.

    Wraps the ci_platform bool result in the SOC response dict shape
    that audit.py router consumers expect:
        {
          "chain_length":    int,
          "verified":        bool,
          "first_record":    ISO timestamp | None,
          "last_record":     ISO timestamp | None,
          "broken_at_index": int   (only present when verified=False)
        }
    """
    entries = _LEDGER.entries()
    chain_len = len(entries)

    if chain_len == 0:
        return {
            "chain_length": 0, "verified": True,
            "first_record": None, "last_record": None,
            "epoch": len(_ARCHIVED_EPOCHS) + 1,
            "archived_epochs": len(_ARCHIVED_EPOCHS),
        }

    verified = _LEDGER.verify_chain()
    result: Dict[str, Any] = {
        "chain_length": chain_len,
        "verified":     verified,
        "first_record": entries[0].timestamp,
        "last_record":  entries[-1].timestamp,
        "epoch":            len(_ARCHIVED_EPOCHS) + 1,
        "archived_epochs":  len(_ARCHIVED_EPOCHS),
    }

    if not verified:
        # Locate the broken link using LedgerEntry.is_valid() from ci_platform
        expected_prev = "0" * 64
        for i, entry in enumerate(entries):
            if not entry.is_valid() or entry.prev_hash != expected_prev:
                result["broken_at_index"] = i
                break
            expected_prev = entry.entry_hash
        print(f"[AUDIT] Chain broken at index {result.get('broken_at_index', '?')}")
    else:
        print(f"[AUDIT] Chain verified - {chain_len} records intact")

    return result
