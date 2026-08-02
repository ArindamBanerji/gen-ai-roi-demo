#!/usr/bin/env python3
"""
migrate_aura_to_age.py -- Block 8.5 Aura -> AGE data migration.

Exports all nodes and relationships from Neo4j Aura and
imports them into PostgreSQL + Apache AGE.

Handles:
  - Field remap: id -> decision_id (Decision), id -> alert_id (Alert)
  - Label rename: ThreatIntel -> ThreatIndicator
  - All 12,120 nodes across 21 label types
  - All 8,385 relationships across 18 types
  - Batched import to avoid memory issues
  - Idempotent: MERGE on key fields -- safe to re-run

Usage:
  # Dry run (audit only, no writes):
  python support/setup/migrate_aura_to_age.py --dry-run

  # Live migration:
  GRAPH_BACKEND=age DATABASE_URL="postgresql://postgres:postgres@localhost:5433/soc_copilot?sslmode=disable" \
      python support/setup/migrate_aura_to_age.py --live

  # Migrate specific tiers only:
  python support/setup/migrate_aura_to_age.py --live --tier p0
  python support/setup/migrate_aura_to_age.py --live --tier p1
  python support/setup/migrate_aura_to_age.py --live --tier p2

Tier definitions (from GAP registry):
  P0 (demo-blocking):  Decision, DECIDED_ON, Campaign, PART_OF
  P1 (accuracy):       Alert, User, Asset, ThreatIntel->ThreatIndicator,
                       AttackPattern, TRIGGERED_EVOLUTION, INVOLVES,
                       DETECTED_ON, MATCHES, CALIBRATED_BY
  P2 (feature):        ShadowDecision, DecisionContext, AlertType,
                       Playbook, DataClass, ProfileSnapshot,
                       AlertCategory, AnalystArchetype, TravelRecord,
                       Checkpoint, TravelContext, SLA, PhishingCampaign,
                       all remaining relationships
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

BATCH_SIZE = 100  # nodes per batch

# ── Field remapping rules ────────────────────────────────────────────────────
# Aura field → AGE field for each label
FIELD_REMAPS = {
    "Decision": {"id": "decision_id"},
    "Alert":    {"id": "alert_id"},
}

# ── Label rename rules ───────────────────────────────────────────────────────
LABEL_RENAMES = {
    "ThreatIntel": "ThreatIndicator",
}

# ── Key fields for MERGE (must be unique per node) ───────────────────────────
KEY_FIELDS = {
    "Decision":        "decision_id",
    "Alert":           "alert_id",
    "User":            "id",
    "Asset":           "id",
    "Campaign":        "id",
    "ThreatIndicator": "id",
    "ShadowDecision":  "composite_key",  # synthesized from day+alert_idx+analyst+source
    "DecisionContext": "id",
    "AttackPattern":   "id",
    "Playbook":        "id",
    "AlertType":       "id",
    "DataClass":       "id",
    "ProfileSnapshot": "id",
    "AlertCategory":   "name",        # keyed by name, not id
    "AnalystArchetype":"name",        # keyed by name, not id
    "TravelRecord":    "id",
    "Checkpoint":      "id",
    "TravelContext":   "id",
    "SLA":             "id",
    "PhishingCampaign":"id",
}

# ── Composite key definitions (nodes with no single unique field) ─────────────
# Fields are joined with '_' to form a synthetic composite_key property.
COMPOSITE_KEYS: Dict[str, List[str]] = {
    "ShadowDecision": ["day", "alert_idx", "analyst", "source"],
}

# ── Aura key field names (before AGE field remapping) ────────────────────────
# When exporting relationships, Aura properties use the ORIGINAL field names.
# KEY_FIELDS stores the AGE field name used in MERGE/MATCH. For labels where
# the field was renamed (e.g. Decision.id → decision_id), we must read the
# Aura name from src_props/tgt_props but MATCH in AGE using the remapped name.
AURA_KEY_FIELDS: Dict[str, str] = {
    "Decision": "id",   # Aura: id  ->  AGE: decision_id
    "Alert":    "id",   # Aura: id  ->  AGE: alert_id
}

# ── Tier definitions ─────────────────────────────────────────────────────────
NODE_TIERS = {
    "p0": ["Decision", "Campaign"],
    "p1": ["Alert", "User", "Asset", "ThreatIntel",
           "AttackPattern", "ThreatIndicator"],
    "p2": ["ShadowDecision", "DecisionContext", "AlertType",
           "Playbook", "DataClass", "ProfileSnapshot",
           "AlertCategory", "AnalystArchetype", "TravelRecord",
           "Checkpoint", "TravelContext", "SLA", "PhishingCampaign"],
}

REL_TIERS = {
    "p0": ["PART_OF"],           # DECIDED_ON moved to p1 -- requires Alert nodes (p1)
    "p1": ["DECIDED_ON",         # Decision->Alert; Alert nodes must exist first
           "INVOLVES", "DETECTED_ON", "MATCHES",
           "ASSOCIATED_WITH", "MEMBER_OF", "HAS_TRAVEL",
           "CLASSIFIED_AS"],
    "p2": ["IN_CATEGORY", "BY_ANALYST", "HAD_CONTEXT",
           "FOR_ALERT", "HANDLED_BY", "STORES",
           "SUBJECT_TO", "ASSIGNED_TO", "APPLIED_PLAYBOOK"],
}


def remap_fields(label: str, props: Dict) -> Dict:
    """Apply field remapping rules for a given label."""
    remaps = FIELD_REMAPS.get(label, {})
    result = {}
    for k, v in props.items():
        new_key = remaps.get(k, k)
        result[new_key] = v
    return result


def get_age_label(aura_label: str) -> str:
    """Apply label rename rules."""
    return LABEL_RENAMES.get(aura_label, aura_label)


def format_props_for_age(props: Dict) -> str:
    """
    Format properties dict as AGE-safe Cypher property string.
    All values inlined as literals (AGE no-param rule).
    """
    parts = []
    for k, v in props.items():
        if v is None:
            continue
        if isinstance(v, bool):
            parts.append(f"{k}: {str(v).lower()}")
        elif isinstance(v, (int, float)):
            parts.append(f"{k}: {v}")
        else:
            escaped = str(v).replace("\\", "\\\\").replace("'", "\\'")[:500]
            parts.append(f"{k}: '{escaped}'")
    return ", ".join(parts)


async def export_nodes_from_aura(
    graph_client,
    label: str,
    skip: int = 0,
    limit: int = BATCH_SIZE,
) -> List[Dict]:
    """Export a batch of nodes from Aura."""
    results = await graph_client.run_query(
        f"MATCH (n:{label}) RETURN n SKIP {skip} LIMIT {limit}"
    )
    nodes = []
    for r in results:
        if r.get("n"):
            nodes.append(r["n"])
    return nodes


async def import_nodes_to_age(
    age_client,
    label: str,
    nodes: List[Dict],
    dry_run: bool = False,
) -> int:
    """Import a batch of nodes into AGE."""
    age_label = get_age_label(label)
    key_field = KEY_FIELDS.get(age_label, "id")
    composite_fields = COMPOSITE_KEYS.get(age_label)
    imported = 0

    for node in nodes:
        props = remap_fields(label, node)
        if not props:
            continue

        # Build composite key if this label has no single unique field
        if composite_fields:
            key_val = "_".join(
                str(props.get(f) or "") for f in composite_fields
            )
            key_field_use = "composite_key"
            props["composite_key"] = key_val
        else:
            key_val = props.get(key_field)
            if key_val is None:
                # Fall back to first available field
                key_val = list(props.values())[0] if props else "unknown"
                key_field_use = list(props.keys())[0] if props else "id"
            else:
                key_field_use = key_field

        props_str = format_props_for_age(props)

        if dry_run:
            imported += 1
            continue

        try:
            escaped_key = str(key_val).replace("\\", "\\\\").replace("'", "\\'")
            await age_client.run_query(
                f"MERGE (n:{age_label} {{{key_field_use}: '{escaped_key}'}}) "
                f"SET n += {{{props_str}}} "
                f"RETURN n"
            )
            imported += 1
        except Exception as e:
            logger.warning(f"Failed to import {age_label} node {key_val}: {e}")

    return imported


async def export_relationships_from_aura(
    graph_client,
    rel_type: str,
    skip: int = 0,
    limit: int = BATCH_SIZE,
) -> List[Dict]:
    """Export a batch of relationships from Aura.

    Returns full node properties so import_relationship_to_age() can
    look up the correct key field per label (nodes without an 'id' field,
    e.g. ShadowDecision, AlertCategory, AnalystArchetype, would yield
    null when queried with a.id).
    """
    results = await graph_client.run_query(
        f"""
        MATCH (a)-[r:{rel_type}]->(b)
        RETURN
            labels(a)[0] AS src_label,
            properties(a) AS src_props,
            labels(b)[0] AS tgt_label,
            properties(b) AS tgt_props,
            properties(r) AS props
        SKIP {skip} LIMIT {limit}
        """
    )
    return results


async def import_relationship_to_age(
    age_client,
    rel: Dict,
    rel_type: str,
    dry_run: bool = False,
) -> bool:
    """Import a single relationship into AGE.

    Key resolution order for each endpoint:
      1. If the label is in COMPOSITE_KEYS: synthesize composite_key from Aura props.
      2. Otherwise: use AURA_KEY_FIELDS to read the Aura property name (which may
         differ from the AGE key due to field remapping, e.g. Decision.id -> decision_id).
         The AGE MATCH always uses KEY_FIELDS[label].
    """
    src_label = get_age_label(rel.get("src_label", "Node"))
    tgt_label = get_age_label(rel.get("tgt_label", "Node"))
    src_props = rel.get("src_props") or {}
    tgt_props = rel.get("tgt_props") or {}

    # Resolve source AGE key (used in MATCH) and id value (read from Aura props).
    # src_age_key  — field name in AGE (may differ from Aura, e.g. alert_id).
    # src_aura_key — field name in Aura (original, before remapping).
    src_composite = COMPOSITE_KEYS.get(src_label)
    if src_composite:
        src_age_key = "composite_key"
        src_id = "_".join(str(src_props.get(f) or "") for f in src_composite)
    else:
        src_age_key = KEY_FIELDS.get(src_label, "id")
        src_aura_key = AURA_KEY_FIELDS.get(src_label, src_age_key)
        src_id = src_props.get(src_aura_key)

    # Resolve target AGE key and id value.
    tgt_composite = COMPOSITE_KEYS.get(tgt_label)
    if tgt_composite:
        tgt_age_key = "composite_key"
        tgt_id = "_".join(str(tgt_props.get(f) or "") for f in tgt_composite)
    else:
        tgt_age_key = KEY_FIELDS.get(tgt_label, "id")
        tgt_aura_key = AURA_KEY_FIELDS.get(tgt_label, tgt_age_key)
        tgt_id = tgt_props.get(tgt_aura_key)

    if not src_id or not tgt_id:
        logger.debug(
            f"Skipping {rel_type}: {src_label}.{src_age_key}={src_id!r} "
            f"-> {tgt_label}.{tgt_age_key}={tgt_id!r}"
        )
        return False

    if dry_run:
        return True

    props = rel.get("props", {}) or {}
    props_str = format_props_for_age(props) if props else ""
    rel_props = f" {{{props_str}}}" if props_str else ""

    src_escaped = str(src_id).replace("\\", "\\\\").replace("'", "\\'")
    tgt_escaped = str(tgt_id).replace("\\", "\\\\").replace("'", "\\'")

    try:
        await age_client.run_query(
            f"""
            MATCH (a:{src_label} {{{src_age_key}: '{src_escaped}'}})
            MATCH (b:{tgt_label} {{{tgt_age_key}: '{tgt_escaped}'}})
            MERGE (a)-[r:{rel_type}{rel_props}]->(b)
            RETURN count(r) AS cnt
            """
        )
        return True
    except Exception as e:
        logger.warning(
            f"Failed to import {rel_type} "
            f"{src_label}({src_id})->{tgt_label}({tgt_id}): {e}"
        )
        return False


async def migrate_tier(
    graph_client,
    age_client,
    tier: str,
    dry_run: bool,
) -> Dict:
    """Migrate all nodes and relationships for a given tier."""
    results = {
        "nodes": {},
        "relationships": {},
        "errors": 0,
    }

    node_labels = NODE_TIERS.get(tier, [])
    rel_types = REL_TIERS.get(tier, [])

    # Migrate nodes
    for label in node_labels:
        logger.info(f"  [{tier.upper()}] Migrating {label} nodes...")
        skip = 0
        total = 0
        while True:
            batch = await export_nodes_from_aura(
                graph_client, label, skip, BATCH_SIZE
            )
            if not batch:
                break
            imported = await import_nodes_to_age(
                age_client, label, batch, dry_run
            )
            total += imported
            skip += BATCH_SIZE
            if len(batch) < BATCH_SIZE:
                break
        results["nodes"][label] = total
        logger.info(f"    [OK] {label}: {total} nodes")

    # Migrate relationships
    for rel_type in rel_types:
        logger.info(f"  [{tier.upper()}] Migrating {rel_type} relationships...")
        skip = 0
        total = 0
        while True:
            batch = await export_relationships_from_aura(
                graph_client, rel_type, skip, BATCH_SIZE
            )
            if not batch:
                break
            for rel in batch:
                ok = await import_relationship_to_age(
                    age_client, rel, rel_type, dry_run
                )
                if ok:
                    total += 1
                else:
                    results["errors"] += 1
            skip += BATCH_SIZE
            if len(batch) < BATCH_SIZE:
                break
        results["relationships"][rel_type] = total
        logger.info(f"    [OK] {rel_type}: {total} relationships")

    return results


async def run_migration(args):
    """Main migration entry point."""
    dry_run = args.dry_run
    tiers = [args.tier] if args.tier else ["p0", "p1", "p2"]

    if dry_run:
        logger.info("=== DRY RUN -- no writes to AGE ===")
    else:
        # Validate AGE backend
        if os.getenv("GRAPH_BACKEND", "neo4j").lower() != "age":
            logger.error(
                "[ERROR] GRAPH_BACKEND must be 'age' for live migration.\n"
                "  Set: GRAPH_BACKEND=age DATABASE_URL=postgresql://..."
            )
            sys.exit(1)

    logger.info("=== Aura -> AGE Migration ===")
    logger.info(f"Tiers: {tiers}")
    logger.info(f"Dry run: {dry_run}")
    logger.info("")

    # Load .env for Neo4j credentials
    try:
        from dotenv import load_dotenv
        # Try repo root first, then parent of cwd
        for env_path in [".env", "../.env", "../../.env"]:
            if os.path.exists(env_path):
                load_dotenv(env_path)
                logger.info(f"Loaded env from: {env_path}")
                break
    except ImportError:
        pass

    raise RuntimeError(
        "Aura-to-AGE migration requires an explicit legacy source adapter; "
        "the retired Neo4jClient is no longer available."
    )

    # Set up AGE client (target)
    target_db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5433/soc_copilot?sslmode=disable"
    )
    import ci_platform.graph.age_client as age_mod
    age_client = age_mod.AGEClient(dsn=target_db_url)

    if not dry_run:
        await age_client.ensure_graph()
        logger.info(f"AGE graph ready: {age_client._graph}")

    # Run migration tier by tier
    grand_total_nodes = 0
    grand_total_rels = 0
    grand_total_errors = 0

    for tier in tiers:
        logger.info(f"\n--- Tier {tier.upper()} ---")
        results = await migrate_tier(
            graph_client, age_client, tier, dry_run
        )
        tier_nodes = sum(results["nodes"].values())
        tier_rels = sum(results["relationships"].values())
        grand_total_nodes += tier_nodes
        grand_total_rels += tier_rels
        grand_total_errors += results["errors"]
        logger.info(
            f"  Tier {tier.upper()} complete: "
            f"{tier_nodes} nodes, {tier_rels} relationships"
        )

    logger.info("")
    logger.info("=== Migration Summary ===")
    logger.info(f"  Total nodes migrated:         {grand_total_nodes}")
    logger.info(f"  Total relationships migrated: {grand_total_rels}")
    logger.info(f"  Errors:                       {grand_total_errors}")
    if dry_run:
        logger.info("  (DRY RUN -- nothing written)")
    else:
        logger.info("  Migration complete.")
        logger.info("  Next: python support/setup/rebuild_age_graph.py --verify")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate Neo4j Aura -> AGE/PostgreSQL"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true",
                       help="Audit only -- no writes")
    group.add_argument("--live", action="store_true",
                       help="Execute migration")
    parser.add_argument(
        "--tier",
        choices=["p0", "p1", "p2"],
        default=None,
        help="Migrate specific tier only (default: all tiers)"
    )
    args = parser.parse_args()

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_migration(args))


if __name__ == "__main__":
    main()
