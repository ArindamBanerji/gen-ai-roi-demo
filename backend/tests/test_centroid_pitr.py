"""
Block 2.1 — Centroid tensor PITR backup tests.
"""
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.services.gae_state import (
    init_learning_state,
    get_profile_scorer,
    serialize_centroid_tensor,
    write_centroid_backup,
    list_centroid_backups,
    load_centroid_backup,
    restore_centroid_from_backup,
    _BACKUP_DIR,
)

# ---------------------------------------------------------------------------
# Shared setup — ensure scorer is available for all tests
# ---------------------------------------------------------------------------

init_learning_state()
_SCORER = get_profile_scorer()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _temp_backup_dir(tmp_path: Path):
    """Patch _BACKUP_DIR to a temp directory for isolation."""
    return patch(
        "app.services.gae_state._BACKUP_DIR",
        tmp_path / "centroid_backups",
    )


# ---------------------------------------------------------------------------
# Test 1 — serialize_centroid_tensor produces sha256
# ---------------------------------------------------------------------------

def test_serialize_produces_sha256():
    payload = serialize_centroid_tensor(_SCORER)

    # Required keys present
    assert "mu" in payload
    assert "shape" in payload
    assert "step" in payload
    assert "timestamp_epoch" in payload
    assert "version" in payload
    assert "sha256" in payload

    # sha256 is a 64-char hex string
    sha = payload["sha256"]
    assert isinstance(sha, str) and len(sha) == 64

    # sha256 is verifiable: re-compute over payload minus sha256
    verify_payload = {k: v for k, v in payload.items() if k != "sha256"}
    canonical = json.dumps(verify_payload, sort_keys=True)
    expected = hashlib.sha256(canonical.encode()).hexdigest()
    assert sha == expected, f"sha256 mismatch: stored={sha!r} computed={expected!r}"

    # shape matches actual mu
    assert payload["shape"] == list(_SCORER.centroids.shape)
    assert isinstance(payload["timestamp_epoch"], int)
    assert payload["timestamp_epoch"] > 0


# ---------------------------------------------------------------------------
# Test 2 — write_centroid_backup writes timestamped + latest files
# ---------------------------------------------------------------------------

def test_backup_writes_file(tmp_path):
    with _temp_backup_dir(tmp_path):
        payload = write_centroid_backup(_SCORER)

    backup_dir = tmp_path / "centroid_backups"
    assert backup_dir.exists()

    # Timestamped file
    backup_id = payload["backup_id"]
    ts_file = backup_dir / f"{backup_id}.json"
    assert ts_file.exists(), f"Timestamped backup not found: {ts_file}"

    # Latest file
    latest = backup_dir / "centroid_backup_latest.json"
    assert latest.exists(), "centroid_backup_latest.json not created"

    # Content is valid JSON with sha256
    raw = json.loads(ts_file.read_text())
    assert raw["sha256"] == payload["sha256"]
    assert raw["backup_id"] == backup_id


# ---------------------------------------------------------------------------
# Test 3 — restore_from_backup reloads mu into the live scorer
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_restore_from_backup(tmp_path):
    # Use get_profile_scorer() live — avoids stale reference if other tests
    # called init_learning_state() and created a new scorer object.
    scorer = get_profile_scorer()
    with _temp_backup_dir(tmp_path):
        # Capture current mu and back it up
        original_mu = scorer.centroids.copy()
        written = write_centroid_backup(scorer)

        # Corrupt live mu
        scorer.centroids[:] = 0.0
        assert not np.allclose(scorer.centroids, original_mu)

        # Restore from backup — should put mu back to original_mu
        restored = await restore_centroid_from_backup(written["backup_id"])

        # Verify inside context so _BACKUP_DIR patch is still active
        assert np.allclose(scorer.centroids, original_mu), "mu not restored correctly"
        assert restored["sha256"] == written["sha256"]


# ---------------------------------------------------------------------------
# Test 4 — restore_centroid_from_backup raises ValueError on checksum mismatch
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_restore_validates_checksum(tmp_path):
    with _temp_backup_dir(tmp_path):
        written = write_centroid_backup(_SCORER)

        # Tamper with the backup file
        backup_dir = tmp_path / "centroid_backups"
        ts_file = backup_dir / f"{written['backup_id']}.json"
        raw = json.loads(ts_file.read_text())
        raw["sha256"] = "0" * 64          # bad hash
        ts_file.write_text(json.dumps(raw))

        with pytest.raises(ValueError, match="[Cc]hecksum"):
            await restore_centroid_from_backup(written["backup_id"])


# ---------------------------------------------------------------------------
# Test 5 — list_centroid_backups returns file metadata
# ---------------------------------------------------------------------------

def test_list_backups_returns_files(tmp_path):
    with _temp_backup_dir(tmp_path):
        # Write two backups — sleep 5ms so timestamps differ by ≥1 ms
        p1 = write_centroid_backup(_SCORER)
        time.sleep(0.005)
        p2 = write_centroid_backup(_SCORER)

        backups = list_centroid_backups()

    assert len(backups) >= 2, f"Expected ≥2 backups, got {len(backups)}"
    ids = {b["backup_id"] for b in backups}
    assert p1["backup_id"] in ids
    assert p2["backup_id"] in ids

    # Each entry has required keys
    for b in backups:
        assert "backup_id" in b
        assert "timestamp_epoch" in b
        assert "step" in b
        assert "sha256" in b
