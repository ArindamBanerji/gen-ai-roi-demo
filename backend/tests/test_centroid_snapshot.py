"""Regression tests for the removal of filesystem centroid snapshots."""

from pathlib import Path


def test_triage_has_no_automatic_filesystem_snapshot_trigger():
    source = Path("app/routers/triage.py").read_text(encoding="utf-8")
    assert "maybe_write_centroid_snapshot" not in source
    assert "centroid_backup" not in source


def test_runtime_centroid_backup_directory_is_not_required_for_source():
    source = Path("app/services/gae_state.py").read_text(encoding="utf-8")
    assert "write_centroid_backup" not in source
    assert "load_centroid_backup" not in source
