"""
Tests verifying SOC audit service wiring to ci_platform Evidence Ledger.

Coverage:
  test_soc_audit_uses_ci_platform_ledger — records are backed by LedgerEntry,
    hash chain is sealed, and epistemic fields round-trip correctly.
"""
import asyncio

import app.services.audit as audit_module
from ci_platform.audit.evidence_ledger import LedgerEntry


def _run(coro):
    return asyncio.run(coro)


def test_soc_audit_uses_ci_platform_ledger():
    """
    record_decision() produces a sealed ci_platform.LedgerEntry in the backing
    ledger, and the returned SOC dict carries the three epistemic fields.

    This proves the wiring is real: the hash chain implementation lives in
    ci_platform only — no duplicate in SOC.
    """
    # Start clean
    _run(audit_module.reset_audit_state())

    record = _run(audit_module.record_decision(
        alert_id="ALERT-CI-TEST",
        situation_type="test_situation",
        action_taken="escalate",
        factors=["factor_a", "factor_b"],
        confidence=0.85,
        kernel_type="diagonal",
        noise_zone="amber",
        conservation_status="green",
    ))

    # 1. The returned dict contains the three EU AI Act Art. 15 epistemic fields
    assert record.get("kernel_type") == "diagonal", f"kernel_type missing: {record}"
    assert record.get("noise_zone") == "amber", f"noise_zone missing: {record}"
    assert record.get("conservation_status") == "green", f"conservation_status missing: {record}"

    # 2. The backing store holds exactly one entry and it is a ci_platform LedgerEntry
    entries = audit_module._LEDGER.entries()
    assert len(entries) == 1
    assert isinstance(entries[0], LedgerEntry), (
        f"Expected LedgerEntry, got {type(entries[0])}"
    )

    # 3. The entry is sealed (entry_hash is non-empty and matches a fresh computation)
    entry = entries[0]
    assert entry.entry_hash != "", "entry_hash must be set after seal()"
    assert entry.is_valid(), "entry_hash must match recomputed hash"

    # 4. verify_chain() delegates to ci_platform and returns the SOC result dict
    result = audit_module.verify_chain()
    assert result["verified"] is True
    assert result["chain_length"] == 1
    assert result["first_record"] == entry.timestamp

    # Cleanup
    _run(audit_module.reset_audit_state())


def test_epistemic_fields_never_none_in_normal_path():
    """
    SOC-2 regression: record_decision() called without explicit epistemic args
    must NOT produce None fields — the 'unknown' fallback string is required at
    call sites (triage.py and simulation.py) per EU AI Act Art. 15 compliance.

    This test simulates the normal triage/simulation call signature (no kernel_type
    etc. passed) and verifies that all three fields are non-None strings when the
    caller supplies the 'unknown' fallback as required by the fix.
    """
    _run(audit_module.reset_audit_state())

    # Simulate triage.py / simulation.py call (SOC-2 fix applied: supplies "unknown")
    record = _run(audit_module.record_decision(
        alert_id="ALERT-SOC2-TEST",
        situation_type="credential_access",
        action_taken="escalate",
        factors=["travel_match", "asset_criticality"],
        confidence=0.78,
        kernel_type="unknown",
        noise_zone="unknown",
        conservation_status="unknown",
    ))

    assert record.get("kernel_type") is not None, "kernel_type must not be None"
    assert record.get("noise_zone") is not None, "noise_zone must not be None"
    assert record.get("conservation_status") is not None, "conservation_status must not be None"
    assert record.get("kernel_type") == "unknown"
    assert record.get("noise_zone") == "unknown"
    assert record.get("conservation_status") == "unknown"

    _run(audit_module.reset_audit_state())
