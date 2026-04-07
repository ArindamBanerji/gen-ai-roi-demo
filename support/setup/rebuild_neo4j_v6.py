"""
rebuild_neo4j_v6.py — Full database recreation for v6.0.

Wipes Neo4j and re-seeds from scratch in the correct dependency order.
Use this as a recovery path if the Aura snapshot is unavailable.

Run from repo root (gen-ai-roi-demo-v4-v50/):
    python support/setup/rebuild_neo4j_v6.py \\
        --shadow-json path/to/v_shadow_synthetic_results(1).json \\
        --pilot-json  path/to/synthetic_pilot_decisions.json

Options:
    --dry-run       Print all steps without executing any of them.
    --shadow-json   Path to v_shadow_synthetic_results(1).json
                    Default: <repo_root>/v_shadow_synthetic_results(1).json
    --pilot-json    Path to synthetic_pilot_decisions.json
                    Default: <repo_root>/synthetic_pilot_decisions.json
"""

import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path

# -- Paths --------------------------------------------------------------------

_SETUP_DIR  = Path(__file__).resolve().parent          # support/setup/
_REPO_ROOT  = _SETUP_DIR.parent.parent                 # gen-ai-roi-demo-v4-v50/
_BACKEND    = _REPO_ROOT / "backend"

sys.path.insert(0, str(_BACKEND))

try:
    from dotenv import load_dotenv
    _env = _REPO_ROOT / ".env"
    if _env.exists():
        load_dotenv(_env)
        print(f"[env] Loaded .env from {_env}")
    else:
        print(f"[env] WARNING: .env not found at {_env}")
except ImportError:
    print("[env] WARNING: python-dotenv not installed")

from app.db.neo4j import neo4j_client  # noqa: E402  (after sys.path insert)

# -- Arg parsing --------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Rebuild Neo4j database for SOC Copilot v6.0"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print steps without executing"
    )
    parser.add_argument(
        "--shadow-json",
        default=str(_REPO_ROOT / "v_shadow_synthetic_results(1).json"),
        help="Path to V-SHADOW-SYNTHETIC-v3 JSON file"
    )
    parser.add_argument(
        "--pilot-json",
        default=str(_REPO_ROOT / "synthetic_pilot_decisions.json"),
        help="Path to synthetic pilot decisions JSON file"
    )
    return parser.parse_args()

# -- Step runner --------------------------------------------------------------

def run_step(label: str, cmd: list[str], dry_run: bool) -> None:
    print(f"\n{'-' * 60}")
    print(f"[step] {label}")
    print(f"       {' '.join(cmd)}")
    if dry_run:
        print("       [dry-run] skipped")
        return
    result = subprocess.run(cmd, cwd=str(_BACKEND))
    if result.returncode != 0:
        print(f"\nERROR: step failed with exit code {result.returncode}")
        print("Aborting rebuild.")
        sys.exit(result.returncode)

# -- Node count summary --------------------------------------------------------

COUNT_QUERY = """
MATCH (n)
WHERE labels(n)[0] IS NOT NULL
RETURN labels(n)[0] AS label, count(n) AS count
ORDER BY count DESC
"""

async def print_node_summary(dry_run: bool) -> None:
    print(f"\n{'-' * 60}")
    print("[step] Node count summary")
    if dry_run:
        print("       [dry-run] skipped")
        return
    await neo4j_client.connect()
    try:
        rows = await neo4j_client.run_query(COUNT_QUERY)
        if not rows:
            print("  (no nodes found)")
        else:
            total = sum(r["count"] for r in rows)
            for r in rows:
                print(f"  {r['label']:<30} {r['count']:>6}")
            print(f"  {'TOTAL':<30} {total:>6}")
    finally:
        await neo4j_client.close()

# -- Main ---------------------------------------------------------------------

WIPE_QUERY = "MATCH (n) DETACH DELETE n"

async def wipe_database(dry_run: bool) -> None:
    print(f"\n{'-' * 60}")
    print("[step] DETACH DELETE all nodes (clean slate)")
    if dry_run:
        print("       [dry-run] skipped")
        return
    await neo4j_client.connect()
    try:
        await neo4j_client.run_query(WIPE_QUERY)
        print("       Done — all nodes deleted")
    finally:
        await neo4j_client.close()


async def main() -> None:
    args = parse_args()

    shadow_json = Path(args.shadow_json)
    pilot_json  = Path(args.pilot_json)

    print("\n" + "=" * 60)
    print("  SOC Copilot — Neo4j Rebuild v6.0")
    print("=" * 60)
    print(f"  Repo root   : {_REPO_ROOT}")
    print(f"  Backend     : {_BACKEND}")
    print(f"  Shadow JSON : {shadow_json}")
    print(f"  Pilot JSON  : {pilot_json}")
    print(f"  NEO4J_URI   : {os.getenv('NEO4J_URI', '(not set)')}")
    if args.dry_run:
        print("  Mode        : DRY-RUN (no writes)")

    if not args.dry_run:
        # Validate data files exist before starting destructive wipe
        missing = [p for p in [shadow_json, pilot_json] if not p.exists()]
        if missing:
            print("\nERROR: required data files not found:")
            for p in missing:
                print(f"  {p}")
            print("\nPass correct paths via --shadow-json and --pilot-json.")
            sys.exit(1)

    python = sys.executable

    # -- Step 1: wipe ---------------------------------------------------------
    await wipe_database(args.dry_run)

    # -- Step 2: base seed ----------------------------------------------------
    _seed_cmd = [python, str(_BACKEND / "seed_neo4j.py")]
    if args.dry_run:
        _seed_cmd.append("--dry-run")
    run_step(
        "seed_neo4j.py — base Alert, User, Asset, ThreatIntel nodes",
        _seed_cmd,
        args.dry_run,
    )

    # -- Step 3: realistic alert pool -----------------------------------------
    run_step(
        "seed_realistic.py — realistic alert pool",
        [python, str(_BACKEND / "app" / "scripts" / "seed_realistic.py")],
        args.dry_run,
    )

    # -- Step 4: shadow decisions ---------------------------------------------
    run_step(
        "ingest_shadow_decisions.py — V-SHADOW-SYNTHETIC-v3",
        [python, str(_BACKEND / "ingest_shadow_decisions.py"), str(shadow_json)],
        args.dry_run,
    )

    # -- Step 5: seed verified decisions --------------------------------------
    run_step(
        "seed_verified_decisions.py — 50 verified seed decisions",
        [python, str(_BACKEND / "scripts" / "seed_verified_decisions.py")],
        args.dry_run,
    )

    # -- Step 6: ingest synthetic pilot decisions ------------------------------
    run_step(
        "ingest_synthetic_decisions.py — synthetic pilot decisions",
        [python, str(_BACKEND / "scripts" / "ingest_synthetic_decisions.py"), str(pilot_json)],
        args.dry_run,
    )

    # -- Step 7: node count summary --------------------------------------------
    await print_node_summary(args.dry_run)

    print(f"\n{'=' * 60}")
    print("  Rebuild complete." if not args.dry_run else "  Dry-run complete — no changes made.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
