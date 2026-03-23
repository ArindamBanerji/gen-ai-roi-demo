"""
Tests verifying SOC audit service wiring to ci_platform Evidence Ledger.

Coverage:
  test_soc_audit_uses_ci_platform_ledger — records are backed by LedgerEntry,
    hash chain is sealed, and epistemic fields round-trip correctly.
"""
import app.services.audit as audit_module
from ci_platform.audit.evidence_ledger import LedgerEntry


def test_soc_audit_uses_ci_platform_ledger():
    """
    record_decision() produces a sealed ci_platform.LedgerEntry in the backing
    ledger, and the returned SOC dict carries the three epistemic fields.

    This proves the wiring is real: the hash chain implementation lives in
    ci_platform only — no duplicate in SOC.
    """
    # Start clean
    audit_module.reset_audit_state()

    record = audit_module.record_decision(
        alert_id="ALERT-CI-TEST",
        situation_type="test_situation",
        action_taken="escalate",
        factors=["factor_a", "factor_b"],
        confidence=0.85,
        kernel_type="diagonal",
        noise_zone="amber",
        conservation_status="green",
    )

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
    audit_module.reset_audit_state()
