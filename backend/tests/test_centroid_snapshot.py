"""
test_centroid_snapshot.py — Unit tests for FEATURE-04 centroid auto-snapshot.

Tests maybe_write_centroid_snapshot() in gae_state.py:
  - snapshot written exactly at SNAPSHOT_INTERVAL boundaries
  - snapshot NOT written before the interval
  - metadata included in backup payload
  - failure is non-blocking (no exception propagated)
  - multiple intervals produce multiple backup files

Run from backend/:
    pytest tests/test_centroid_snapshot.py -v
"""
import importlib
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scorer(shape=(6, 4, 6)) -> MagicMock:
    scorer = MagicMock()
    scorer.centroids = np.random.rand(*shape)
    scorer.decision_count = 42
    return scorer


def _reset_counter(module):
    """Reset module-level _snapshot_decision_count to 0 between tests."""
    module._snapshot_decision_count = 0


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_snapshot_written_at_interval(tmp_path):
    """
    Exactly one backup written after SNAPSHOT_INTERVAL calls.
    File must exist and contain valid JSON.
    """
    import app.services.gae_state as gs
    _reset_counter(gs)

    scorer = _make_scorer()
    with patch.object(gs, "_BACKUP_DIR", tmp_path):
        for i in range(gs.SNAPSHOT_INTERVAL):
            gs.maybe_write_centroid_snapshot(scorer, decision_id=f"D-{i}", category="lateral_movement")

    backups = list(tmp_path.glob("centroid_backup_[0-9]*.json"))
    assert len(backups) == 1, f"Expected 1 backup, got {len(backups)}"

    payload = json.loads(backups[0].read_text())
    assert "mu" in payload
    assert "sha256" in payload


def test_snapshot_not_written_before_interval(tmp_path):
    """
    Zero backups written before SNAPSHOT_INTERVAL is reached.
    """
    import app.services.gae_state as gs
    _reset_counter(gs)

    scorer = _make_scorer()
    calls = gs.SNAPSHOT_INTERVAL - 1
    with patch.object(gs, "_BACKUP_DIR", tmp_path):
        for i in range(calls):
            gs.maybe_write_centroid_snapshot(scorer, decision_id=f"D-{i}", category="malware")

    backups = list(tmp_path.glob("centroid_backup_[0-9]*.json"))
    assert len(backups) == 0, f"Expected 0 backups after {calls} calls, got {len(backups)}"


def test_snapshot_contains_metadata(tmp_path):
    """
    Snapshot payload includes metadata with trigger, decision_id, and category.
    """
    import app.services.gae_state as gs
    _reset_counter(gs)

    scorer = _make_scorer()
    dec_id = "DEC-SNAP-001"
    cat    = "credential_access"

    with patch.object(gs, "_BACKUP_DIR", tmp_path):
        for i in range(gs.SNAPSHOT_INTERVAL):
            gs.maybe_write_centroid_snapshot(scorer, decision_id=dec_id, category=cat)

    backups = list(tmp_path.glob("centroid_backup_[0-9]*.json"))
    assert len(backups) == 1
    payload = json.loads(backups[0].read_text())

    assert "metadata" in payload, "Backup payload missing 'metadata' key"
    meta = payload["metadata"]
    assert meta.get("trigger") == "auto",         f"trigger mismatch: {meta}"
    assert meta.get("decision_id") == dec_id,     f"decision_id mismatch: {meta}"
    assert meta.get("category")    == cat,        f"category mismatch: {meta}"
    assert "decision_count" in meta,              "decision_count missing from metadata"


def test_snapshot_failure_does_not_raise(tmp_path, caplog):
    """
    When write_centroid_backup raises, maybe_write_centroid_snapshot must
    not propagate the exception and must log a warning.
    """
    import app.services.gae_state as gs
    import logging
    _reset_counter(gs)

    scorer = _make_scorer()
    with patch.object(gs, "write_centroid_backup", side_effect=IOError("disk full")):
        with caplog.at_level(logging.WARNING, logger="app.services.gae_state"):
            for i in range(gs.SNAPSHOT_INTERVAL):
                result = gs.maybe_write_centroid_snapshot(scorer)

    # Must not raise — result at the triggering call must be False (failure path)
    assert result is False, "Expected False return on write failure"
    assert any("SNAPSHOT" in r.message for r in caplog.records), (
        "Expected a [SNAPSHOT] warning in logs"
    )


def test_multiple_intervals_create_multiple_snapshots(tmp_path):
    """
    30 calls at SNAPSHOT_INTERVAL=10 must produce exactly 3 backup files.
    """
    import app.services.gae_state as gs
    _reset_counter(gs)

    scorer = _make_scorer()
    total_calls  = gs.SNAPSHOT_INTERVAL * 3
    expected_snaps = 3

    with patch.object(gs, "_BACKUP_DIR", tmp_path):
        for i in range(total_calls):
            gs.maybe_write_centroid_snapshot(scorer, decision_id=f"D-{i}", category="exfiltration")

    backups = list(tmp_path.glob("centroid_backup_[0-9]*.json"))
    assert len(backups) == expected_snaps, (
        f"Expected {expected_snaps} backups after {total_calls} calls, got {len(backups)}"
    )
