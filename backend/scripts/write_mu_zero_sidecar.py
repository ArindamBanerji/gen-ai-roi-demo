"""
One-time backfill script — write the μ₀ IKS sidecar from the current live
ProfileScorer centroid state.

Context
-------
The bootstrap checkpoint already has metadata.bootstrap=True, so the normal
startup path (init_learning_state / bootstrap_calibration) skips the WIRING-0
sidecar write.  This script captures the equivalent μ₀ from the currently
loaded centroids so that IKS can produce a real drift score instead of the
50.0 fallback.

Usage
-----
    cd backend/
    python scripts/write_mu_zero_sidecar.py

Source tag "manual_capture_v1" distinguishes this write from an automatic
bootstrap write so the origin is always traceable in the JSON.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure backend/ is on sys.path so app.* imports resolve correctly
# ---------------------------------------------------------------------------
_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

_SIDECAR_PATH = _BACKEND_DIR / "app" / "data" / "iks_bootstrap_soc.json"


def main() -> None:
    # Step 1: initialize learning state the same way the backend does at startup
    from app.services.gae_state import init_learning_state

    print("[write_mu_zero_sidecar] Initializing learning state ...")
    init_learning_state()

    # Step 2: capture current ProfileScorer centroid state before any mutations
    from app.services.gae_state import get_profile_scorer
    scorer = get_profile_scorer()
    mu_zero = scorer.mu.copy()

    # Step 3: write sidecar JSON
    _SIDECAR_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "mu_zero":   mu_zero.tolist(),
        "shape":     list(mu_zero.shape),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "domain":    "soc",
        "source":    "manual_capture_v1",
    }
    with open(_SIDECAR_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    # Step 4: confirm
    print(f"[write_mu_zero_sidecar] Written: {_SIDECAR_PATH}")
    print(f"[write_mu_zero_sidecar] shape     = {payload['shape']}")
    print(f"[write_mu_zero_sidecar] timestamp = {payload['timestamp']}")
    print(f"[write_mu_zero_sidecar] source    = {payload['source']}")


if __name__ == "__main__":
    main()
