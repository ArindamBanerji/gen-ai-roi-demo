"""
BACKLOG audit-chain contract tests.

Covers the OutcomeEntry architecture: decisions and outcomes are separate
chain entries, sealed once appended, never mutated.

12 tests.
"""
import pytest
from ci_platform.audit.evidence_ledger import EvidenceLedger, LedgerEntry, OutcomeEntry
from app.framework.audit import (
    record_decision, record_outcome, get_decision_rows,
    reconstruct_from_memory, verify_chain, _LEDGER,
    _SITUATION_TYPES,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_ledger():
    """Fresh ledger and side-tables for every test."""
    from app.framework.feedback_store import FEEDBACK_GIVEN
    _LEDGER._entries.clear()
    _SITUATION_TYPES.clear()
    FEEDBACK_GIVEN.clear()
    yield
    _LEDGER._entries.clear()
    _SITUATION_TYPES.clear()
    FEEDBACK_GIVEN.clear()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_decision(alert_id="ALT-001", situation_type="malware_detected",
                   action_taken="escalate", confidence=0.85):
    """Append one LedgerEntry and return the SOC dict."""
    return record_decision(
        alert_id=alert_id,
        situation_type=situation_type,
        action_taken=action_taken,
        factors=["factor_a", "factor_b"],
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_record_decision_returns_chain_index():
    """record_decision result includes a chain_index int."""
    rec = _make_decision()
    assert "chain_index" in rec
    assert isinstance(rec["chain_index"], int)


def test_record_decision_returns_hash():
    """record_decision result includes a non-empty entry hash."""
    rec = _make_decision()
    assert rec.get("hash"), "entry hash must be a non-empty string"
    assert len(rec["hash"]) == 64   # SHA-256 hex


def test_record_outcome_appends_outcome_entry():
    """record_outcome creates an OutcomeEntry, not a mutation of the decision."""
    rec = _make_decision()
    result = record_outcome(rec["id"], "correct")
    assert result is not None
    assert result["type"] == "outcome"
    assert result["outcome"] == "correct"
    types = [type(e).__name__ for e in _LEDGER.entries()]
    assert "OutcomeEntry" in types


def test_record_outcome_missing_decision_returns_none():
    """record_outcome with an unknown decision_id returns None."""
    result = record_outcome("DEC-NONEXISTENT-99", "correct")
    assert result is None


def test_chain_valid_after_outcome():
    """Chain integrity holds after appending an OutcomeEntry."""
    rec = _make_decision()
    record_outcome(rec["id"], "correct")
    result = verify_chain()
    assert result["verified"] is True


def test_outcome_entry_references_decision_hash():
    """OutcomeEntry.decision_entry_hash matches the original decision's hash."""
    rec = _make_decision()
    decision_hash = rec["hash"]
    outcome_rec = record_outcome(rec["id"], "correct")
    assert outcome_rec["decision_entry_hash"] == decision_hash


def test_get_decision_rows_projects_outcome():
    """get_decision_rows merges LedgerEntry + OutcomeEntry into one row."""
    rec = _make_decision()
    record_outcome(rec["id"], "correct")
    rows = get_decision_rows()
    matching = [r for r in rows if r["id"] == rec["id"]]
    assert len(matching) == 1
    assert matching[0]["outcome"] == "correct"


def test_get_decision_rows_pending_without_outcome():
    """A decision without an outcome row shows None or 'pending'."""
    rec = _make_decision()
    rows = get_decision_rows()
    matching = [r for r in rows if r["id"] == rec["id"]]
    assert len(matching) == 1
    assert matching[0]["outcome"] in (None, "pending")


def test_get_decision_rows_uses_latest_outcome():
    """When a decision has multiple OutcomeEntries the last one wins."""
    rec = _make_decision()
    record_outcome(rec["id"], "correct")
    record_outcome(rec["id"], "incorrect")   # later — should win
    rows = get_decision_rows()
    matching = [r for r in rows if r["id"] == rec["id"]]
    assert matching[0]["outcome"] == "incorrect"


def test_reconstruct_from_memory_appends_not_mutates():
    """reconstruct_from_memory adds an OutcomeEntry; sealed entries stay valid."""
    from app.framework.feedback_store import FEEDBACK_GIVEN
    rec = _make_decision()
    FEEDBACK_GIVEN["ALT-RECON"] = {
        "decision_id": rec["id"],
        "outcome": "correct",
        "timestamp": "2026-04-22T12:00:00",
    }
    before = len(_LEDGER.entries())
    reconstruct_from_memory()
    after = len(_LEDGER.entries())
    assert after > before
    for e in _LEDGER.entries():
        assert e.is_valid()


def test_reconstruct_skips_existing_outcome():
    """reconstruct_from_memory does not add a duplicate OutcomeEntry."""
    from app.framework.feedback_store import FEEDBACK_GIVEN
    rec = _make_decision()
    record_outcome(rec["id"], "correct")   # already recorded
    FEEDBACK_GIVEN["ALT-SKIP"] = {
        "decision_id": rec["id"],
        "outcome": "correct",
        "timestamp": "2026-04-22T12:00:00",
    }
    before = len(_LEDGER.entries())
    reconstruct_from_memory()
    after = len(_LEDGER.entries())
    assert after == before


def test_chain_index_monotonic_across_types():
    """chain_index increases across LedgerEntry and OutcomeEntry alike."""
    rec1 = _make_decision()
    out1 = record_outcome(rec1["id"], "correct")
    rec2 = _make_decision(alert_id="ALT-002")
    assert rec1["chain_index"] < out1["chain_index"]
    assert out1["chain_index"] < rec2["chain_index"]
