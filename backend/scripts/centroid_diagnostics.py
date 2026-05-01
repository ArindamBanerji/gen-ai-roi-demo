"""
Diagnostic: Action centroid separation, category distribution, init-to-current distance.
Run from: cd $env:CLAUDE_SOC\backend
Usage: python scripts/centroid_diagnostics.py
"""
import sys
import os
import json
import numpy as np
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.domains.soc.config import SOC_CATEGORIES, SCORER_ACTIONS, SOC_FACTORS, build_profile_scorer

# ── Build scorer ──────────────────────────────────────────────
scorer = build_profile_scorer()
centroids = scorer.centroids  # shape (C, A, d)
C, A, d = centroids.shape
print(f"Tensor shape: ({C}, {A}, {d})")
print()

# ── 0A: Action centroid separation per category ───────────────
print("=" * 60)
print("0A: Per-category action centroid separation (L2)")
print("=" * 60)
for ci in range(C):
    seps = [
        np.linalg.norm(centroids[ci, a1] - centroids[ci, a2])
        for a1 in range(A) for a2 in range(a1 + 1, A)
    ]
    cat_name = SOC_CATEGORIES[ci] if ci < len(SOC_CATEGORIES) else f"cat_{ci}"
    print(f"  {cat_name:25s}: mean_sep={np.mean(seps):.4f}  min_sep={np.min(seps):.4f}  max_sep={np.max(seps):.4f}")

print()

# ── 0B: Category distribution from centroid backups ───────────
print("=" * 60)
print("0B: Category distribution (from centroid backup metadata)")
print("=" * 60)
backup_dir = Path(__file__).parent.parent / "app" / "data" / "centroid_backups"
if backup_dir.exists():
    from collections import Counter
    cat_counts = Counter()
    backup_files = sorted(backup_dir.glob("centroid_backup_[0-9]*.json"))
    for f in backup_files:
        try:
            data = json.loads(f.read_text())
            meta = data.get("metadata", {})
            cat = meta.get("category", "unknown")
            cat_counts[cat] += 1
        except (json.JSONDecodeError, KeyError):
            pass
    print(f"  Snapshots found: {len(backup_files)}")
    for cat, count in cat_counts.most_common():
        print(f"  {cat:25s}: {count}")
else:
    print("  No centroid_backups directory found.")

print()

# ── 0C: Init-to-current Frobenius distance ────────────────────
print("=" * 60)
print("0C: Init-to-current Frobenius distance")
print("=" * 60)
if backup_dir.exists():
    backup_files = sorted(backup_dir.glob("centroid_backup_[0-9]*.json"))
    if backup_files:
        try:
            first_data = json.loads(backup_files[0].read_text())
            first_mu = np.array(first_data["mu"])
            init_dist = np.linalg.norm(first_mu - centroids, "fro")
            print(f"  First snapshot: {backup_files[0].name}")
            print(f"  First snapshot shape: {first_mu.shape}")
            print(f"  Init-to-current Frobenius: {init_dist:.6f}")

            # Also show per-category distance
            if first_mu.shape == centroids.shape:
                print()
                print("  Per-category Frobenius distance:")
                for ci in range(C):
                    cat_dist = np.linalg.norm(first_mu[ci] - centroids[ci], "fro")
                    cat_name = SOC_CATEGORIES[ci] if ci < len(SOC_CATEGORIES) else f"cat_{ci}"
                    print(f"    {cat_name:25s}: {cat_dist:.6f}")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"  Error reading first snapshot: {e}")
    else:
        print("  No timestamped backup files found.")
else:
    print("  No centroid_backups directory found.")

# ── Also try bootstrap (mu_zero) ─────────────────────────────
print()
bootstrap_path = backup_dir.parent / "bootstrap_state.json" if backup_dir.exists() else None
if bootstrap_path and bootstrap_path.exists():
    try:
        bs_data = json.loads(bootstrap_path.read_text())
        mu_zero = np.array(bs_data.get("bootstrap_mu", bs_data.get("mu", [])))
        if mu_zero.shape == centroids.shape:
            bootstrap_dist = np.linalg.norm(mu_zero - centroids, "fro")
            print(f"  Bootstrap-to-current Frobenius: {bootstrap_dist:.6f}")
            print()
            print("  Per-category drift from bootstrap:")
            for ci in range(C):
                cat_dist = np.linalg.norm(mu_zero[ci] - centroids[ci], "fro")
                cat_name = SOC_CATEGORIES[ci] if ci < len(SOC_CATEGORIES) else f"cat_{ci}"
                print(f"    {cat_name:25s}: {cat_dist:.6f}")
    except (json.JSONDecodeError, KeyError) as e:
        print(f"  Error reading bootstrap: {e}")
elif bootstrap_path:
    print("  No bootstrap_state.json found.")

print()
print("Done.")
