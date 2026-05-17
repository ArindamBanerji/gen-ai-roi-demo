from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from app.seed.config import SeedConfig
from app.seed.runner import generate_seed


ROOT = Path(__file__).resolve().parents[1]


def test_watchfilesignore_exists():
    path = ROOT / ".watchfilesignore"
    assert path.exists()
    patterns = set(path.read_text(encoding="utf-8").splitlines())
    assert {"_*.py", "*.pyc", "__pycache__", ".pytest_cache"}.issubset(patterns)


def test_generate_seed_has_reseed_flag():
    result = subprocess.run(
        [sys.executable, "scripts/generate_seed.py", "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "--reseed" in result.stdout
    assert "--reseed-clean" in result.stdout


def test_seed_hash_in_metadata():
    data = generate_seed()
    seed_hash = data["metadata"].get("seed_hash")
    assert isinstance(seed_hash, str)
    assert re.fullmatch(r"[0-9a-f]{16}", seed_hash)


def test_seed_hash_deterministic():
    first = generate_seed(SeedConfig(seed=42))["metadata"]["seed_hash"]
    second = generate_seed(SeedConfig(seed=42))["metadata"]["seed_hash"]
    assert first == second


def test_seed_hash_changes_with_different_seed():
    first = generate_seed(SeedConfig(seed=42))["metadata"]["seed_hash"]
    second = generate_seed(SeedConfig(seed=43))["metadata"]["seed_hash"]
    assert first != second


def test_live_backend_marker_registered():
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--markers"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "@pytest.mark.live_backend" in result.stdout
