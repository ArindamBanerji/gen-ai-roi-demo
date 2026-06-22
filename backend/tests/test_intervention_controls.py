"""
Tests for P22: InterventionControls (L-12 consolidated oversight panel).

Coverage:
  test_freeze_logged                   -- freeze returns record with type/initiated_by/timestamp
  test_unfreeze_logged                 -- unfreeze returns record with frozen=False
  test_rollback_preview                -- preview mode returns diff without applying changes
  test_threshold_below_minimum_rejected -- threshold < 0.50 rejected with error key
  test_threshold_valid                 -- valid threshold logged with old and new values
  test_current_state_has_fields        -- state returns all required control fields
  test_freeze_category_logged          -- freeze_category logged with category/frozen
  test_disable_auto_approve_logged     -- disable returns auto_approve_enabled flag
  test_category_force_review_logged    -- force_review logged with category/force_review
  test_rollback_preview_not_found      -- preview on missing snapshot returns error+preview=True
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.intervention_controls import InterventionControls
from app.services.composite_gate import CompositeDiscriminant


# ---------------------------------------------------------------------------
# Helper: build controls with all mocked dependencies
# ---------------------------------------------------------------------------

def _make_ctrl():
    """Return (ctrl, scorer_mock, db_mock)."""
    db = MagicMock()
    db.run_query = AsyncMock(return_value=[])

    scorer = MagicMock()
    scorer.frozen = False

    checkpoint_svc = MagicMock()

    # Pass the class itself (fully static gate)
    ctrl = InterventionControls(
        db_client=db,
        scorer=scorer,
        checkpoint_service=checkpoint_svc,
        composite_gate=CompositeDiscriminant,
    )
    return ctrl, scorer, db


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_freeze_logged():
    """Freeze returns intervention record with type and reason."""
    ctrl, scorer, db = _make_ctrl()
    result = asyncio.run(ctrl.freeze_all_learning("admin@firm.com", "Monthly audit"))

    scorer.freeze.assert_called_once()
    assert result["type"] == "freeze_all_learning"
    assert result["initiated_by"] == "admin@firm.com"
    assert "timestamp" in result
    assert result["details"]["frozen"] is True


def test_unfreeze_logged():
    """Unfreeze returns record with frozen=False."""
    ctrl, scorer, db = _make_ctrl()
    result = asyncio.run(ctrl.unfreeze_all_learning("admin", "Resume"))

    scorer.unfreeze.assert_called_once()
    assert result["type"] == "freeze_all_learning"
    assert result["details"]["frozen"] is False


def test_rollback_preview():
    """Preview mode doesn't apply changes and returns preview=True."""
    ctrl, scorer, db = _make_ctrl()
    fake_row = {
        "cp": {
            "decision_count": 42,
            "reason": "pre-rollout",
            "timestamp": "2026-01-01T00:00:00",
        }
    }
    db.run_query = AsyncMock(return_value=[fake_row])

    result = asyncio.run(ctrl.rollback("snap-001", "admin", "test", preview=True))

    assert result["preview"] is True
    assert result["snapshot_id"] == "snap-001"
    assert result["would_restore_decision_count"] == 42
    # Scorer must NOT have been mutated in preview mode
    scorer.freeze.assert_not_called()
    scorer.unfreeze.assert_not_called()


def test_rollback_preview_not_found():
    """Preview on missing snapshot returns error with preview=True."""
    ctrl, scorer, db = _make_ctrl()
    db.run_query = AsyncMock(return_value=[])

    result = asyncio.run(ctrl.rollback("nonexistent", "admin", "test", preview=True))

    assert "error" in result
    assert result["preview"] is True
    scorer.freeze.assert_not_called()


def test_threshold_below_minimum_rejected():
    """Threshold < 0.50 rejected with error key."""
    ctrl, scorer, db = _make_ctrl()
    result = asyncio.run(
        ctrl.adjust_threshold("credential_access", 0.30, "admin", "test")
    )
    assert "error" in result
    # Gate must NOT have been updated
    assert CompositeDiscriminant.CATEGORY_CONFIDENCE_THRESHOLDS.get(
        "credential_access"
    ) != 0.30


def test_threshold_valid():
    """Valid threshold adjustment logged with old and new values."""
    ctrl, scorer, db = _make_ctrl()
    original = CompositeDiscriminant.CATEGORY_CONFIDENCE_THRESHOLDS.get(
        "credential_access", CompositeDiscriminant.CONFIDENCE_THRESHOLD
    )
    try:
        result = asyncio.run(
            ctrl.adjust_threshold("credential_access", 0.75, "admin", "tighten")
        )
        assert result["type"] == "threshold_adjustment"
        assert result["details"]["new_threshold"] == 0.75
        assert result["details"]["old_threshold"] == original
        assert CompositeDiscriminant.CATEGORY_CONFIDENCE_THRESHOLDS["credential_access"] == 0.75
    finally:
        # Restore original value so other tests are unaffected
        CompositeDiscriminant.CATEGORY_CONFIDENCE_THRESHOLDS["credential_access"] = original


def test_current_state_has_fields():
    """State returns all required control fields."""
    ctrl, scorer, db = _make_ctrl()
    state = asyncio.run(ctrl.get_current_state())

    assert "global_freeze" in state
    assert "auto_approve_enabled" in state
    assert "thresholds" in state
    assert "frozen_categories" in state
    assert "force_review_categories" in state


def test_freeze_category_logged():
    """freeze_category logged with category and frozen flag."""
    ctrl, scorer, db = _make_ctrl()
    # Ensure clean state
    CompositeDiscriminant.FROZEN_CATEGORIES.discard("insider_threat")

    result = asyncio.run(
        ctrl.freeze_category("insider_threat", True, "admin", "Unusual spike")
    )

    assert result["type"] == "freeze_category"
    assert result["details"]["category"] == "insider_threat"
    assert result["details"]["frozen"] is True
    assert "insider_threat" in CompositeDiscriminant.FROZEN_CATEGORIES

    # Cleanup
    CompositeDiscriminant.FROZEN_CATEGORIES.discard("insider_threat")


def test_disable_auto_approve_logged():
    """disable_auto_approve returns auto_approve_enabled flag."""
    ctrl, scorer, db = _make_ctrl()
    original = CompositeDiscriminant.AUTO_APPROVE_DISABLED
    try:
        result = asyncio.run(
            ctrl.disable_auto_approve(True, "admin", "Emergency audit")
        )
        assert result["type"] == "disable_auto_approve"
        assert result["details"]["auto_approve_enabled"] is False
        assert CompositeDiscriminant.AUTO_APPROVE_DISABLED is True
    finally:
        CompositeDiscriminant.AUTO_APPROVE_DISABLED = original


def test_category_force_review_logged():
    """category_force_review logged with category and force_review flag."""
    ctrl, scorer, db = _make_ctrl()
    CompositeDiscriminant.FORCE_REVIEW_CATEGORIES.discard("lateral_movement")

    result = asyncio.run(
        ctrl.category_force_review("lateral_movement", True, "admin", "Post-incident")
    )

    assert result["type"] == "category_force_review"
    assert result["details"]["category"] == "lateral_movement"
    assert result["details"]["force_review"] is True
    assert "lateral_movement" in CompositeDiscriminant.FORCE_REVIEW_CATEGORIES

    # Cleanup
    CompositeDiscriminant.FORCE_REVIEW_CATEGORIES.discard("lateral_movement")
