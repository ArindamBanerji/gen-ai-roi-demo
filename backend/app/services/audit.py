"""
Decision Audit Service — In-memory decision ledger with SHA-256 hash chain

Stores DecisionRecord dicts for every alert the agent has processed.
Provides JSON and CSV export via the /api/audit/decisions endpoint.
Provides chain verification via verify_chain().

Two population paths:
  1. record_decision() — called proactively when the agent decides
  2. reconstruct_from_memory() — reads FEEDBACK_GIVEN from feedback.py to
     back-fill records for decisions already made in the session, without
     modifying feedback.py or triage.py

Each DecisionRecord schema:
  id               str   — uuid4
  alert_id         str   — e.g. "ALERT-7823"
  timestamp        str   — ISO 8601 UTC
  situation_type   str   — e.g. "travel_login_anomaly"
  action_taken     str   — e.g. "false_positive_close"
  factors          list[str] — context factor names
  confidence       float
  outcome          str | None — "correct" / "incorrect", filled in later
  analyst_confirmed bool
  hash             str   — SHA-256 of (previous_hash + JSON of immutable fields)

Hash chain notes:
  • Only the IMMUTABLE fields (_HASH_FIELDS) are included in the hash input.
    outcome and analyst_confirmed are mutable and intentionally excluded so
    that verify_chain() remains valid after outcome feedback is recorded.
  • The first record chains off _GENESIS_HASH.
  • verify_chain() recomputes each hash from first to last and returns
    verified=True only if every hash matches.
"""
import hashlib
import json
from uuid import uuid4
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ============================================================================
# Module-level ledger (in-memory, demo-session scoped)
# ============================================================================

_DECISIONS: List[Dict[str, Any]] = []

# Seed hash for the first record in the chain
_GENESIS_HASH = "SOC_COPILOT_GENESIS_2026"

# Only these fields are included in the hash input.
# They are set at decision time and never mutated afterwards.
_HASH_FIELDS = (
    "id",
    "alert_id",
    "timestamp",
    "situation_type",
    "action_taken",
    "factors",
    "confidence",
)


# Demo-derived defaults for known alert IDs.
# Used by reconstruct_from_memory() when the ledger doesn't have a record yet.
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


# ============================================================================
# Hash chain helpers (private)
# ============================================================================

def _get_previous_hash() -> str:
    """Return the stored hash of the last record, or the genesis hash."""
    if _DECISIONS:
        return _DECISIONS[-1]["hash"]
    return _GENESIS_HASH


def _compute_hash(previous_hash: str, record: Dict[str, Any]) -> str:
    """
    Compute SHA-256 over (previous_hash + JSON of immutable record fields).

    Only fields listed in _HASH_FIELDS are included so that later mutations
    to outcome / analyst_confirmed do not invalidate the chain.
    """
    record_data = {k: record[k] for k in _HASH_FIELDS if k in record}
    hash_input = previous_hash + json.dumps(record_data, sort_keys=True)
    return hashlib.sha256(hash_input.encode()).hexdigest()


# ============================================================================
# Core functions
# ============================================================================

def record_decision(
    alert_id: str,
    situation_type: str,
    action_taken: str,
    factors: List[str],
    confidence: float,
) -> Dict[str, Any]:
    """
    Create a new DecisionRecord, compute its chain hash, append to the
    ledger, and return it.

    Intended to be called when the agent makes a decision (Tab 3 analysis).
    Does NOT require modifying triage.py now — the reconstruct path covers
    already-processed alerts.
    """
    record: Dict[str, Any] = {
        "id":                str(uuid4()),
        "alert_id":          alert_id,
        "timestamp":         datetime.now(timezone.utc).isoformat(),
        "situation_type":    situation_type,
        "action_taken":      action_taken,
        "factors":           factors,
        "confidence":        confidence,
        "outcome":           None,
        "analyst_confirmed": False,
    }
    # Hash chains off the previous record's hash (or genesis for first record)
    previous_hash = _get_previous_hash()
    record["hash"] = _compute_hash(previous_hash, record)
    _DECISIONS.append(record)
    print(f"[AUDIT] Recorded decision {record['id']} for {alert_id} -> {action_taken}")
    return record


def record_outcome(
    alert_id: str,
    outcome: str,
    analyst_notes: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Find the most recent DecisionRecord for alert_id and update its outcome.

    Mutates outcome and analyst_confirmed; the hash is NOT recomputed because
    it covers only the immutable decision-time fields.

    Returns the updated record, or None if no record exists for that alert.
    """
    for record in reversed(_DECISIONS):
        if record["alert_id"] == alert_id:
            record["outcome"] = outcome
            record["analyst_confirmed"] = True
            if analyst_notes:
                record["analyst_notes"] = analyst_notes
            print(f"[AUDIT] Updated outcome for {alert_id}: {outcome}")
            return record
    print(f"[AUDIT] record_outcome: no record found for {alert_id}")
    return None


def get_decisions() -> List[Dict[str, Any]]:
    """Return all decision records, most recent first."""
    return list(reversed(_DECISIONS))


def reconstruct_from_memory() -> int:
    """
    Back-fill the ledger from existing session state — specifically
    FEEDBACK_GIVEN in feedback.py — without modifying those modules.

    For each alert in FEEDBACK_GIVEN that is not yet in the ledger:
      • Uses demo defaults (or generic defaults) for situation_type,
        action_taken, factors, confidence.
      • Sets outcome and analyst_confirmed from the feedback entry.
      • Computes and stores the chain hash.

    For alerts already in the ledger but without an outcome, fills the
    outcome from FEEDBACK_GIVEN if available (hash is unchanged).

    Returns the number of new records added.
    """
    from app.services.feedback import FEEDBACK_GIVEN  # local import avoids circular deps

    existing_by_alert: Dict[str, Dict[str, Any]] = {
        r["alert_id"]: r for r in _DECISIONS
    }
    added = 0

    for alert_id, fb in FEEDBACK_GIVEN.items():
        if alert_id not in existing_by_alert:
            # New record — derive context from demo defaults
            ctx = _ALERT_DEFAULTS.get(alert_id, _DEFAULT_CTX)
            record: Dict[str, Any] = {
                "id":                str(uuid4()),
                "alert_id":          alert_id,
                "timestamp":         fb.get("timestamp", datetime.now(timezone.utc).isoformat()),
                "situation_type":    ctx["situation_type"],
                "action_taken":      ctx["action_taken"],
                "factors":           list(ctx["factors"]),
                "confidence":        ctx["confidence"],
                "outcome":           fb.get("outcome"),
                "analyst_confirmed": True,
            }
            # Chain hash — appended sequentially so previous hash is correct
            previous_hash = _get_previous_hash()
            record["hash"] = _compute_hash(previous_hash, record)
            _DECISIONS.append(record)
            existing_by_alert[alert_id] = record
            added += 1
        else:
            # Already have a record — back-fill outcome if missing
            existing = existing_by_alert[alert_id]
            if existing["outcome"] is None and fb.get("outcome"):
                existing["outcome"] = fb["outcome"]
                existing["analyst_confirmed"] = True
                # Hash is intentionally NOT recomputed (outcome is mutable)

    print(f"[AUDIT] reconstruct_from_memory: +{added} new records ({len(_DECISIONS)} total)")
    return added


def reset_audit_state() -> None:
    """Clear all decision records (demo reset)."""
    _DECISIONS.clear()
    print("[AUDIT] Decision ledger cleared")


def verify_chain() -> Dict[str, Any]:
    """
    Walk _DECISIONS in chronological order (insertion order = index 0 first)
    and verify the SHA-256 hash chain.

    Returns:
        {
          "chain_length":   int,
          "verified":       bool,
          "first_record":   ISO timestamp or None,
          "last_record":    ISO timestamp or None,
          "broken_at_index": int   (only present when verified=False),
        }
    """
    chain_length = len(_DECISIONS)

    if chain_length == 0:
        return {
            "chain_length": 0,
            "verified":     True,
            "first_record": None,
            "last_record":  None,
        }

    previous_hash = _GENESIS_HASH

    for i, record in enumerate(_DECISIONS):
        expected = _compute_hash(previous_hash, record)
        stored   = record.get("hash", "")

        if expected != stored:
            print(f"[AUDIT] Chain broken at index {i} (alert={record.get('alert_id')})")
            return {
                "chain_length":    chain_length,
                "verified":        False,
                "broken_at_index": i,
                "first_record":    _DECISIONS[0].get("timestamp"),
                "last_record":     _DECISIONS[-1].get("timestamp"),
            }

        previous_hash = stored  # advance chain

    print(f"[AUDIT] Chain verified - {chain_length} records intact")
    return {
        "chain_length": chain_length,
        "verified":     True,
        "first_record": _DECISIONS[0].get("timestamp"),
        "last_record":  _DECISIONS[-1].get("timestamp"),
    }
