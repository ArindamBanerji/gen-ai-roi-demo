"""
migrate_datetime_to_epoch.py -- Convert AGE native datetime() fields to
epoch integers (milliseconds since Unix epoch) across all node types.

PREREQUISITE: Aura snapshot taken 2026-04-04 00:40:11. Do NOT run without it.

Run from gen-ai-roi-demo-v4-v50/backend/:
    python scripts/migrate_datetime_to_epoch.py            # interactive (Phase 1 + confirm + Phase 3)
    python scripts/migrate_datetime_to_epoch.py --dry-run  # print Cypher only, no writes
    python scripts/migrate_datetime_to_epoch.py --phase1-only  # add _epoch fields, stop before removal

THREE PHASES:
  Phase 1 -- Add *_epoch fields alongside existing datetime fields
  Phase 2 -- Print verification sample (5 nodes per type, both fields)
  Phase 3 -- Remove old datetime fields (requires y/n confirmation, or --phase1-only to skip)
"""

import argparse
import asyncio
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BACKEND))

try:
    from dotenv import load_dotenv
    _env = _BACKEND.parent / ".env"
    if _env.exists():
        load_dotenv(_env)
        print(f"[env] Loaded .env from {_env}")
    else:
        print(f"[env] WARNING: .env not found at {_env}")
except ImportError:
    print("[env] WARNING: python-dotenv not installed")

from app.db.graph_client import graph_client  # noqa: E402


# ---------------------------------------------------------------------------
# Migration spec
# Each entry: (label_or_rel, field, is_relationship)
# ---------------------------------------------------------------------------

NODE_MIGRATIONS = [
    # (node_label, field_name)
    ("Decision",              "timestamp"),
    ("Decision",              "verified_at"),
    ("Alert",                 "timestamp"),
    ("EvolutionEvent",        "timestamp"),
    ("ProfileSnapshot",       "timestamp"),
    ("Checkpoint",            "timestamp"),
    ("Intervention",          "timestamp"),
    ("ThreatIndicator",       "created_at"),
    ("ThreatIndicator",       "last_seen"),
    ("Campaign",              "updated_at"),
    ("CrowdStrikeEnrichment", "refreshed_at"),
    ("GreyNoiseEnrichment",   "refreshed_at"),
    ("GreyNoiseEnrichment",   "linked_at"),
    ("PulseDiveEnrichment",   "refreshed_at"),
    ("PulseDiveEnrichment",   "linked_at"),
    ("HealthLog",             "timestamp"),      # skip if no nodes found
]

REL_MIGRATIONS = [
    # (rel_type, field_name)
    ("TRIGGERED_EVOLUTION", "timestamp"),
    ("EDR_MANAGED_BY",      "linked_at"),
]


# ---------------------------------------------------------------------------
# Cypher builders
# ---------------------------------------------------------------------------

def phase1_node_cypher(label: str, field: str) -> str:
    epoch_field = f"{field}_epoch"
    return (
        f"MATCH (n:{label})\n"
        f"WHERE n.{field} IS NOT NULL\n"
        f"  AND n.{epoch_field} IS NULL\n"
        f"SET n.{epoch_field} = timestamp(n.{field})\n"
        f"RETURN count(n) AS updated"
    )


def phase1_rel_cypher(rel_type: str, field: str) -> str:
    epoch_field = f"{field}_epoch"
    return (
        f"MATCH ()-[r:{rel_type}]->()\n"
        f"WHERE r.{field} IS NOT NULL\n"
        f"  AND r.{epoch_field} IS NULL\n"
        f"SET r.{epoch_field} = timestamp(r.{field})\n"
        f"RETURN count(r) AS updated"
    )


def verify_node_cypher(label: str, field: str) -> str:
    epoch_field = f"{field}_epoch"
    return (
        f"MATCH (n:{label})\n"
        f"WHERE n.{epoch_field} IS NOT NULL\n"
        f"RETURN n.{field} AS original, n.{epoch_field} AS epoch\n"
        f"LIMIT 5"
    )


def phase3_node_cypher(label: str, field: str) -> str:
    return (
        f"MATCH (n:{label})\n"
        f"WHERE n.{field} IS NOT NULL\n"
        f"REMOVE n.{field}\n"
        f"RETURN count(n) AS removed"
    )


def phase3_rel_cypher(rel_type: str, field: str) -> str:
    return (
        f"MATCH ()-[r:{rel_type}]->()\n"
        f"WHERE r.{field} IS NOT NULL\n"
        f"REMOVE r.{field}\n"
        f"RETURN count(r) AS removed"
    )


def count_node_cypher(label: str, field: str) -> str:
    epoch_field = f"{field}_epoch"
    return (
        f"MATCH (n:{label})\n"
        f"WHERE n.{epoch_field} IS NOT NULL\n"
        f"RETURN count(n) AS n"
    )


def count_rel_cypher(rel_type: str, field: str) -> str:
    epoch_field = f"{field}_epoch"
    return (
        f"MATCH ()-[r:{rel_type}]->()\n"
        f"WHERE r.{epoch_field} IS NOT NULL\n"
        f"RETURN count(r) AS n"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def step(label: str) -> None:
    print(f"\n[--] {label}")


async def run_query(cypher: str, dry_run: bool):
    """Execute query or print it if dry_run."""
    if dry_run:
        print(f"\n    CYPHER:\n{_indent(cypher)}")
        return None
    rows = await graph_client.run_query(cypher)
    return rows


def _indent(text: str, prefix: str = "      ") -> str:
    return "\n".join(prefix + line for line in text.splitlines())


# ---------------------------------------------------------------------------
# Phase 1
# ---------------------------------------------------------------------------

async def phase1(dry_run: bool) -> None:
    section("PHASE 1 -- Add *_epoch fields (non-destructive)")

    for label, field in NODE_MIGRATIONS:
        cypher = phase1_node_cypher(label, field)
        step(f"Node ({label}).{field} -> {field}_epoch")
        rows = await run_query(cypher, dry_run)
        if rows is not None:
            updated = rows[0]["updated"] if rows else 0
            print(f"    updated: {updated}")

    for rel_type, field in REL_MIGRATIONS:
        cypher = phase1_rel_cypher(rel_type, field)
        step(f"Rel [:{rel_type}].{field} -> {field}_epoch")
        rows = await run_query(cypher, dry_run)
        if rows is not None:
            updated = rows[0]["updated"] if rows else 0
            print(f"    updated: {updated}")


# ---------------------------------------------------------------------------
# Phase 2 — Verification sample
# ---------------------------------------------------------------------------

async def phase2_verify(dry_run: bool) -> None:
    section("PHASE 2 -- Verification sample (5 nodes per field)")

    for label, field in NODE_MIGRATIONS:
        cypher = verify_node_cypher(label, field)
        step(f"Sample ({label}).{field}")
        if dry_run:
            print(f"\n    CYPHER:\n{_indent(cypher)}")
            continue
        rows = await graph_client.run_query(cypher)
        if not rows:
            print("    (no nodes with epoch field -- may be empty or HealthLog absent)")
        else:
            for r in rows:
                print(f"    original={r.get('original')}  epoch={r.get('epoch')}")


# ---------------------------------------------------------------------------
# Phase 3
# ---------------------------------------------------------------------------

async def phase3(dry_run: bool) -> None:
    section("PHASE 3 -- Remove old datetime fields")

    for label, field in NODE_MIGRATIONS:
        cypher = phase3_node_cypher(label, field)
        step(f"REMOVE ({label}).{field}")
        rows = await run_query(cypher, dry_run)
        if rows is not None:
            removed = rows[0]["removed"] if rows else 0
            print(f"    removed: {removed}")

    for rel_type, field in REL_MIGRATIONS:
        cypher = phase3_rel_cypher(rel_type, field)
        step(f"REMOVE [:{rel_type}].{field}")
        rows = await run_query(cypher, dry_run)
        if rows is not None:
            removed = rows[0]["removed"] if rows else 0
            print(f"    removed: {removed}")


# ---------------------------------------------------------------------------
# Final counts
# ---------------------------------------------------------------------------

async def final_counts(dry_run: bool) -> None:
    section("FINAL -- Node counts with *_epoch fields")

    for label, field in NODE_MIGRATIONS:
        cypher = count_node_cypher(label, field)
        step(f"Count ({label}) with {field}_epoch")
        if dry_run:
            print(f"\n    CYPHER:\n{_indent(cypher)}")
            continue
        rows = await graph_client.run_query(cypher)
        n = rows[0]["n"] if rows else 0
        print(f"    {n} nodes")

    for rel_type, field in REL_MIGRATIONS:
        cypher = count_rel_cypher(rel_type, field)
        step(f"Count [:{rel_type}] with {field}_epoch")
        if dry_run:
            print(f"\n    CYPHER:\n{_indent(cypher)}")
            continue
        rows = await graph_client.run_query(cypher)
        n = rows[0]["n"] if rows else 0
        print(f"    {n} rels")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Migrate AGE datetime fields to epoch integers"
    )
    p.add_argument("--dry-run", action="store_true",
                   help="Print Cypher queries without executing")
    p.add_argument("--phase1-only", action="store_true",
                   help="Add _epoch fields only; skip Phase 3 removal")
    return p.parse_args()


async def main() -> None:
    args = parse_args()

    print("\n" + "=" * 60)
    print("  AGE datetime -> epoch migration")
    print("  PREREQUISITE: Aura snapshot 2026-04-04 00:40:11 must exist")
    print("=" * 60)
    if args.dry_run:
        print("  Mode: DRY-RUN (no writes)")
    elif args.phase1_only:
        print("  Mode: PHASE 1 ONLY (no removal)")
    else:
        print("  Mode: FULL MIGRATION (Phase 1 + Phase 3)")

    if not args.dry_run:
        await graph_client.connect()

    try:
        # Phase 1 — add _epoch fields
        await phase1(args.dry_run)

        # Phase 2 — verification sample
        await phase2_verify(args.dry_run)

        if args.phase1_only:
            print("\n[--] --phase1-only set -- stopping before Phase 3 removal.")
            await final_counts(args.dry_run)
            return

        if args.dry_run:
            # Still show Phase 3 queries in dry-run
            await phase3(args.dry_run)
            await final_counts(args.dry_run)
            return

        # Prompt before destructive Phase 3
        print("\n" + "=" * 60)
        print("  Phase 2 verification complete.")
        print("  Phase 3 will REMOVE the original datetime fields.")
        print("  This is irreversible without the Aura snapshot.")
        answer = input("  Proceed with Phase 3? [y/N]: ").strip().lower()
        if answer != "y":
            print("  Aborted -- Phase 3 skipped. _epoch fields are in place.")
            return

        await phase3(args.dry_run)
        await final_counts(args.dry_run)

        print("\n" + "=" * 60)
        print("  Migration complete.")
        print("=" * 60)

    finally:
        if not args.dry_run:
            await graph_client.close()


if __name__ == "__main__":
    asyncio.run(main())
