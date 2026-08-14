from app.services.shadow_promotion import evaluate_shadow_promotion


def _shadow(**overrides):
    record = {
        "decision_id": "shadow-test-001",
        "source": "test-shadow-fixture",
        "category": "malware",
        "ai_confidence": 0.92,
        "analyst_action": "escalate",
        "analyst_correct": True,
    }
    record.update(overrides)
    return record


def test_filled_shadow_requires_explicit_approval():
    result = evaluate_shadow_promotion(_shadow(), sample_count=25)
    assert result.status == "hold"
    assert "approval" in result.reason


def test_approved_qualified_shadow_can_be_promoted():
    result = evaluate_shadow_promotion(
        _shadow(),
        manual_approval=True,
        approval_token="approval-test-001",
        actor="test-analyst",
        sample_count=25,
    )
    assert result.status == "promote"
    assert result.evidence["rule_version"] == "shadow-to-observation-v1"


def test_low_confidence_and_missing_outcome_are_not_promotable():
    assert evaluate_shadow_promotion(
        _shadow(ai_confidence=0.49),
        manual_approval=True,
        approval_token="token",
        actor="analyst",
        sample_count=25,
    ).status == "reject"
    assert evaluate_shadow_promotion(
        _shadow(analyst_action=None, analyst_correct=None),
        manual_approval=True,
        approval_token="token",
        actor="analyst",
        sample_count=25,
    ).status == "hold"


def test_safety_pause_blocks_even_explicit_approval():
    result = evaluate_shadow_promotion(
        _shadow(),
        manual_approval=True,
        approval_token="token",
        actor="analyst",
        sample_count=25,
        safety_paused=True,
    )
    assert result.status == "hold"
