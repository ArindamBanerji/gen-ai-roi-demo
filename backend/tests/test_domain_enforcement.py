"""Cross-boundary checks for SOC's explicit domain-scoped reads."""

from support.soc_triage_harness import SOCTriageHarness


def test_soc_triage_passes_domain_to_get_decision() -> None:
    """The SOC harness reads Decisions through the required-domain contract."""
    harness = SOCTriageHarness()
    decision_id = harness.add_decision(
        category="credential_access",
        action="escalate",
        factors={"severity": 0.8},
    )

    decision = harness.get_decision(decision_id)

    assert decision is not None
    assert decision["domain"] == "soc"
