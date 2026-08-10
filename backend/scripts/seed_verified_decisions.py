"""
Seed realistic verified Decision nodes into AGE for demo consistency.

The seed is additive and guarded: if the graph already has more than 100
verified decisions, no writes are performed.

Usage (from backend/):
    python scripts/seed_verified_decisions.py
"""

from __future__ import annotations

import asyncio
import random
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path / .env setup
# ---------------------------------------------------------------------------
_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

try:
    from dotenv import load_dotenv

    _env = _BACKEND_DIR.parent / ".env"
    if _env.exists():
        load_dotenv(_env)
        print(f"  Loaded .env from {_env}")
    else:
        print(f"  WARNING: .env not found at {_env}")
except ImportError:
    print("  WARNING: python-dotenv not installed")

from app.graph_schema import _S  # noqa: E402


CATEGORY_DISTRIBUTION: dict[str, int] = {
    "credential_access": 100,
    "malware_execution": 90,
    "lateral_movement": 85,
    "data_exfiltration": 80,
    "insider_threat": 75,
    "cloud_infrastructure": 70,
}

SCORER_ACTIONS = ("escalate", "investigate", "suppress", "monitor")
N_DECISIONS = 500
N_CORRECT = 425
N_OVERRIDES = 25
RANDOM_SEED = 42
SEED_SOURCE = "seed_verified"
SEED_USER = "demo-seed"
MILLISECONDS_PER_DAY = 86_400_000


def _millis(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def _alternate_action(action: str) -> str:
    for candidate in SCORER_ACTIONS:
        if candidate != action:
            return candidate
    return "investigate"


def build_demo_decisions(
    seed: int = RANDOM_SEED,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    now = now or datetime.now(timezone.utc)
    base_epoch = _millis(now - timedelta(days=30))

    categories: list[str] = []
    for category, count in CATEGORY_DISTRIBUTION.items():
        categories.extend([category] * count)
    if len(categories) != N_DECISIONS:
        raise ValueError("CATEGORY_DISTRIBUTION must sum to N_DECISIONS")

    rows: list[dict[str, Any]] = []
    for index, category in enumerate(categories):
        action = SCORER_ACTIONS[index % len(SCORER_ACTIONS)]
        is_override = index < N_OVERRIDES
        correct = index < N_CORRECT
        outcome = "overridden" if is_override else "correct" if correct else "incorrect"
        analyst_action = _alternate_action(action) if is_override else ""

        # Even spacing across 30 days plus deterministic jitter keeps the demo
        # audit trail realistic while avoiding identical timestamps.
        step = int((30 * MILLISECONDS_PER_DAY) / N_DECISIONS)
        jitter = rng.randint(0, max(1, step - 1))
        timestamp_epoch = base_epoch + index * step + jitter
        verify_delay_ms = rng.randint(3_600_000, 48 * 3_600_000)
        verified_at_epoch = timestamp_epoch + verify_delay_ms

        rows.append(
            {
                "decision_id": f"VERIFIED-{index + 1:04d}",
                "action": action,
                "confidence": round(rng.uniform(0.50, 0.95), 4),
                "factor_vector": [],
                "category": category,
                "source_id": f"seed-source-{(index % 12) + 1:02d}",
                "user_id": f"user-{(index % 40) + 1:03d}",
                "timestamp_epoch": timestamp_epoch,
                "outcome": outcome,
                "correct": correct,
                "verified_at_epoch": verified_at_epoch,
                "verified_by": SEED_USER,
                "analyst_action": analyst_action,
                "override_comment": (
                    "Demo override: analyst selected alternate action"
                    if is_override
                    else ""
                ),
                "source": SEED_SOURCE,
                "shadow_mode": False,
            }
        )

    return rows


def build_create_decision_query(decision: dict[str, Any]) -> str:
    correct = "true" if bool(decision["correct"]) else "false"
    shadow_mode = "true" if bool(decision.get("shadow_mode", False)) else "false"
    return (
        "CREATE (d:Decision {"
        f"decision_id: {_S(decision['decision_id'])}, "
        f"action: {_S(decision['action'])}, "
        f"confidence: {float(decision['confidence'])}, "
        f"factor_vector: {_S(decision.get('factor_vector', []))}, "
        f"category: {_S(decision['category'])}, "
        f"source_id: {_S(decision['source_id'])}, "
        f"user_id: {_S(decision['user_id'])}, "
        f"timestamp_epoch: {int(decision['timestamp_epoch'])}, "
        f"outcome: {_S(decision['outcome'])}, "
        f"correct: {correct}, "
        f"verified_at_epoch: {int(decision['verified_at_epoch'])}, "
        f"verified_by: {_S(decision['verified_by'])}, "
        f"analyst_action: {_S(decision.get('analyst_action', ''))}, "
        f"override_comment: {_S(decision.get('override_comment', ''))}, "
        f"source: {_S(decision.get('source', SEED_SOURCE))}, "
        f"shadow_mode: {shadow_mode}"
        "}) RETURN d.decision_id AS decision_id"
    )


async def maybe_seed_verified_decisions(client) -> dict[str, Any]:
    count = 0
    if hasattr(client, "count_verified_decisions"):
        count = int(await client.count_verified_decisions())
    else:
        rows = await client.run_query(
            "MATCH (d:Decision) WHERE d.outcome IS NOT NULL RETURN count(d) AS cnt"
        )
        count = int((rows[0].get("cnt") or 0) if rows else 0)

    if count > 100:
        message = f"Already {count} verified decisions -- skipping seed"
        print(message)
        return {"skipped": True, "existing_count": count, "message": message}

    decisions = build_demo_decisions()
    for decision in decisions:
        await client.run_query(build_create_decision_query(decision))

    correct_count = sum(1 for row in decisions if row["correct"])
    override_count = sum(1 for row in decisions if row["outcome"] == "overridden")
    category_counts = dict(Counter(row["category"] for row in decisions))
    min_ts = min(row["timestamp_epoch"] for row in decisions)
    max_ts = max(row["timestamp_epoch"] for row in decisions)

    print(f"Seeded {len(decisions)} verified decisions")
    print(f"Correct: {correct_count}; incorrect: {len(decisions) - correct_count}")
    print(f"Overrides: {override_count}")
    print(f"Category counts: {category_counts}")
    print(f"Timestamp range: {min_ts}..{max_ts}")

    return {
        "skipped": False,
        "seeded_count": len(decisions),
        "correct_count": correct_count,
        "incorrect_count": len(decisions) - correct_count,
        "override_count": override_count,
        "category_counts": category_counts,
        "timestamp_min": min_ts,
        "timestamp_max": max_ts,
    }


async def seed_demo_evolution_events(client) -> None:
    rows = await client.run_query(
        "MATCH (e:EvolutionEvent) "
        "WHERE e.event_type = 'variant_created' "
        "OR e.event_type = 'shadow_started' "
        "OR e.event_type = 'shadow_result' "
        "OR e.event_type = 'promotion_approved' "
        "OR e.event_type = 'promotion_rejected' "
        "OR e.event_type = 'rollback' "
        "RETURN count(*) AS cnt"
    )
    if rows and int(rows[0].get("cnt", 0)) > 0:
        print(f"Already {rows[0]['cnt']} evolution events -- skipping")
        return

    from gae.evolution import (
        record_evolution_event,
        VARIANT_CREATED,
        SHADOW_STARTED,
        SHADOW_RESULT,
        PROMOTION_APPROVED,
        ARTIFACT_SCORING_THRESHOLD,
        ARTIFACT_ROUTING_RULE,
    )
    import time

    now = time.time() * 1000
    day = 86_400_000

    events = [
        dict(
            event_type=VARIANT_CREATED,
            variant_id="ae_rule_drift_threshold_credential_access_drift",
            artifact_type=ARTIFACT_SCORING_THRESHOLD,
            description="Drift detected: credential_access accuracy declined 4.2pp",
            after_state={"category": "credential_access", "proposed_value": 0.85},
            graph_context={"decline_pp": 4.2, "detection_method": "per_category_accuracy_trend"},
            metadata={"rule_id": "RULE-DRIFT-THRESHOLD", "warm_started": False},
            timestamp_override=now - 20 * day,
        ),
        dict(
            event_type=SHADOW_STARTED,
            variant_id="ae_rule_drift_threshold_credential_access_drift",
            artifact_type=ARTIFACT_SCORING_THRESHOLD,
            description="Shadow testing: 25 comparison batch",
            after_state={"batch_size": 25},
            timestamp_override=now - 18 * day,
        ),
        dict(
            event_type=SHADOW_RESULT,
            variant_id="ae_rule_drift_threshold_credential_access_drift",
            artifact_type=ARTIFACT_SCORING_THRESHOLD,
            description="Shadow complete: win_rate 0.68 (17/25)",
            after_state={"win_rate": 0.68, "comparisons": 25},
            timestamp_override=now - 14 * day,
        ),
        dict(
            event_type=PROMOTION_APPROVED,
            variant_id="ae_rule_drift_threshold_credential_access_drift",
            artifact_type=ARTIFACT_SCORING_THRESHOLD,
            description="Variant promoted: superiority 0.68, conservation GREEN",
            after_state={"status": "active"},
            timestamp_override=now - 12 * day,
        ),
        dict(
            event_type=VARIANT_CREATED,
            variant_id="ae_rule_campaign_escalate_campaign_c007",
            artifact_type=ARTIFACT_ROUTING_RULE,
            description="Campaign C-007: credential_access + lateral_movement correlation",
            after_state={"campaign_id": "C-007"},
            graph_context={"campaign_alerts": 5},
            metadata={"rule_id": "RULE-CAMPAIGN-ESCALATE", "warm_started": False},
            timestamp_override=now - 5 * day,
        ),
    ]

    for evt in events:
        await record_evolution_event(client, **evt)
    print("[SEED] Seeded 5 demo evolution events")


def _build_enrichment_events(now_ms: float, day_ms: int) -> list[dict[str, Any]]:
    """Return flat AE-SEED lifecycle events for eight additional variants."""
    from gae.evolution import (
        ARTIFACT_ROUTING_RULE,
        ARTIFACT_SCORING_THRESHOLD,
        PROMOTION_APPROVED,
        PROMOTION_REJECTED,
        SHADOW_RESULT,
        SHADOW_STARTED,
        VARIANT_CREATED,
    )

    def ts(offset_days: int) -> float:
        return now_ms + offset_days * day_ms

    def drift_variant(
        *,
        variant_id: str,
        category: str,
        proposed_value: float,
        offsets: tuple[int, int, int, int],
        description: str,
        win_rate: float,
        comparisons: int,
        wins: int,
        rule_id: str,
    ) -> list[dict[str, Any]]:
        return [
            dict(
                event_type=VARIANT_CREATED,
                variant_id=variant_id,
                artifact_type=ARTIFACT_SCORING_THRESHOLD,
                description=description,
                after_state={"category": category, "proposed_value": proposed_value},
                graph_context={"category": category, "detection_method": "rolling_accuracy_drift"},
                metadata={"rule_id": rule_id, "warm_started": True, "category": category},
                timestamp_override=ts(offsets[0]),
            ),
            dict(
                event_type=SHADOW_STARTED,
                variant_id=variant_id,
                artifact_type=ARTIFACT_SCORING_THRESHOLD,
                description=f"Shadow testing: {comparisons} comparison batch for {category}",
                after_state={"batch_size": comparisons, "status": "shadow"},
                metadata={"category": category},
                timestamp_override=ts(offsets[1]),
            ),
            dict(
                event_type=SHADOW_RESULT,
                variant_id=variant_id,
                artifact_type=ARTIFACT_SCORING_THRESHOLD,
                description=f"Shadow complete: win_rate {win_rate:.3f} ({wins}/{comparisons})",
                after_state={"win_rate": win_rate, "comparisons": comparisons, "wins": wins},
                graph_context={"win_rate": win_rate, "sample_size": comparisons, "wins": wins},
                metadata={"category": category},
                timestamp_override=ts(offsets[2]),
            ),
            dict(
                event_type=PROMOTION_APPROVED,
                variant_id=variant_id,
                artifact_type=ARTIFACT_SCORING_THRESHOLD,
                description=f"Variant promoted: superiority {win_rate:.3f}, conservation GREEN",
                after_state={"status": "active", "superiority": win_rate, "conservation": "green"},
                metadata={"category": category},
                timestamp_override=ts(offsets[3]),
            ),
        ]

    def campaign_variant(
        *,
        variant_id: str,
        campaign_id: str,
        campaign_alerts: int,
        offsets: tuple[int, int, int, int],
        win_rate: float,
        comparisons: int,
        wins: int,
        rejected: bool = False,
    ) -> list[dict[str, Any]]:
        terminal_event = PROMOTION_REJECTED if rejected else PROMOTION_APPROVED
        reason = "win_rate 0.47 < threshold 0.60" if rejected else None
        terminal_description = (
            f"Promotion rejected for {campaign_id}: {reason}"
            if rejected
            else f"Variant promoted for {campaign_id}: superiority {win_rate:.3f}, conservation GREEN"
        )
        terminal_state = (
            {"status": "rejected", "reason": reason, "win_rate": win_rate}
            if rejected
            else {"status": "active", "superiority": win_rate, "conservation": "green"}
        )
        return [
            dict(
                event_type=VARIANT_CREATED,
                variant_id=variant_id,
                artifact_type=ARTIFACT_ROUTING_RULE,
                description=f"Campaign {campaign_id}: correlated cross-category alert cluster",
                after_state={"campaign_id": campaign_id},
                graph_context={"campaign_id": campaign_id, "campaign_alerts": campaign_alerts},
                metadata={"rule_id": "RULE-CAMPAIGN-ESCALATE", "warm_started": True, "campaign_id": campaign_id},
                timestamp_override=ts(offsets[0]),
            ),
            dict(
                event_type=SHADOW_STARTED,
                variant_id=variant_id,
                artifact_type=ARTIFACT_ROUTING_RULE,
                description=f"Shadow testing: {comparisons} comparison batch for {campaign_id}",
                after_state={"batch_size": comparisons, "status": "shadow"},
                metadata={"campaign_id": campaign_id},
                timestamp_override=ts(offsets[1]),
            ),
            dict(
                event_type=SHADOW_RESULT,
                variant_id=variant_id,
                artifact_type=ARTIFACT_ROUTING_RULE,
                description=f"Shadow complete: win_rate {win_rate:.2f} ({wins}/{comparisons})",
                after_state={"win_rate": win_rate, "comparisons": comparisons, "wins": wins},
                graph_context={"win_rate": win_rate, "sample_size": comparisons, "wins": wins},
                metadata={"campaign_id": campaign_id},
                timestamp_override=ts(offsets[2]),
            ),
            dict(
                event_type=terminal_event,
                variant_id=variant_id,
                artifact_type=ARTIFACT_ROUTING_RULE,
                description=terminal_description,
                after_state=terminal_state,
                metadata={"campaign_id": campaign_id},
                timestamp_override=ts(offsets[3]),
            ),
        ]

    def coverage_variant(
        *,
        variant_id: str,
        category: str,
        proposed_value: float,
        offsets: tuple[int, int, int, int],
        win_rate: float,
        comparisons: int,
        wins: int,
        technique_id: str | None = None,
    ) -> list[dict[str, Any]]:
        metadata = {"rule_id": "RULE-COVERAGE-GAP", "warm_started": True, "category": category}
        if technique_id:
            metadata["technique_id"] = technique_id
        return [
            dict(
                event_type=VARIANT_CREATED,
                variant_id=variant_id,
                artifact_type=ARTIFACT_SCORING_THRESHOLD,
                description=f"Coverage gap: {category} threshold adjusted to {proposed_value:.2f}",
                after_state={"category": category, "proposed_value": proposed_value},
                graph_context={"category": category, "coverage_gap": True},
                metadata=metadata,
                timestamp_override=ts(offsets[0]),
            ),
            dict(
                event_type=SHADOW_STARTED,
                variant_id=variant_id,
                artifact_type=ARTIFACT_SCORING_THRESHOLD,
                description=f"Shadow testing: {comparisons} comparison batch for {category} coverage",
                after_state={"batch_size": comparisons, "status": "shadow"},
                metadata=metadata,
                timestamp_override=ts(offsets[1]),
            ),
            dict(
                event_type=SHADOW_RESULT,
                variant_id=variant_id,
                artifact_type=ARTIFACT_SCORING_THRESHOLD,
                description=f"Shadow complete: win_rate {win_rate:.2f} ({wins}/{comparisons})",
                after_state={"win_rate": win_rate, "comparisons": comparisons, "wins": wins},
                graph_context={"win_rate": win_rate, "sample_size": comparisons, "wins": wins},
                metadata=metadata,
                timestamp_override=ts(offsets[2]),
            ),
            dict(
                event_type=PROMOTION_APPROVED,
                variant_id=variant_id,
                artifact_type=ARTIFACT_SCORING_THRESHOLD,
                description=f"Variant promoted: superiority {win_rate:.2f}, conservation GREEN",
                after_state={"status": "active", "superiority": win_rate, "conservation": "green"},
                metadata=metadata,
                timestamp_override=ts(offsets[3]),
            ),
        ]

    events: list[dict[str, Any]] = []
    events.extend(drift_variant(
        variant_id="ae_rule_drift_threshold_credential_access_v2",
        category="credential_access",
        proposed_value=0.75,
        offsets=(-180, -173, -158, -155),
        description="Rolling accuracy declined 82.1% to 74.3%; tighten credential_access threshold 65% to 75%",
        win_rate=0.767,
        comparisons=30,
        wins=23,
        rule_id="RULE-DRIFT-THRESHOLD",
    ))
    events.extend(drift_variant(
        variant_id="ae_rule_drift_threshold_lateral_movement_v1",
        category="lateral_movement",
        proposed_value=0.80,
        offsets=(-140, -133, -120, -117),
        description="Drift detected: lateral_movement precision dipped; tighten threshold to 80%",
        win_rate=0.72,
        comparisons=25,
        wins=18,
        rule_id="RULE-DRIFT-THRESHOLD",
    ))
    events.extend(drift_variant(
        variant_id="ae_rule_drift_threshold_cloud_infrastructure_v1",
        category="cloud_infrastructure",
        proposed_value=0.70,
        offsets=(-95, -88, -75, -73),
        description="Drift detected: cloud_infrastructure false positives rising; tune threshold to 70%",
        win_rate=0.64,
        comparisons=25,
        wins=16,
        rule_id="RULE-DRIFT-THRESHOLD",
    ))
    events.extend(campaign_variant(
        variant_id="ae_rule_campaign_escalate_campaign_c012",
        campaign_id="C-012",
        campaign_alerts=7,
        offsets=(-110, -103, -90, -87),
        win_rate=0.80,
        comparisons=20,
        wins=16,
    ))
    events.extend(campaign_variant(
        variant_id="ae_rule_campaign_escalate_campaign_c015",
        campaign_id="C-015",
        campaign_alerts=4,
        offsets=(-60, -53, -40, -37),
        win_rate=0.68,
        comparisons=25,
        wins=17,
    ))
    events.extend(campaign_variant(
        variant_id="ae_rule_campaign_escalate_campaign_c018",
        campaign_id="C-018",
        campaign_alerts=3,
        offsets=(-30, -23, -10, -8),
        win_rate=0.47,
        comparisons=30,
        wins=14,
        rejected=True,
    ))
    events.extend(coverage_variant(
        variant_id="ae_rule_coverage_gap_insider_threat_v1",
        category="insider_threat",
        proposed_value=0.55,
        offsets=(-70, -63, -50, -47),
        win_rate=0.70,
        comparisons=20,
        wins=14,
    ))
    events.extend(coverage_variant(
        variant_id="ae_rule_coverage_gap_data_exfiltration_v1",
        category="data_exfiltration",
        technique_id="T1567",
        proposed_value=0.80,
        offsets=(-45, -38, -25, -22),
        win_rate=0.76,
        comparisons=25,
        wins=19,
    ))
    return events


async def _get_existing_evolution_variant_ids(client) -> set[str]:
    try:
        rows = await client.run_query(
            "MATCH (e:EvolutionEvent) RETURN DISTINCT e.variant_id AS variant_id"
        )
    except Exception as exc:
        print(f"[SEED] Could not query existing AE variant ids; proceeding without skip set: {exc}")
        return set()

    variant_ids: set[str] = set()
    for row in rows or []:
        variant_id = row.get("variant_id") if isinstance(row, dict) else None
        if variant_id:
            variant_ids.add(str(variant_id))
    return variant_ids


async def enrich_evolution_events(client) -> dict[str, Any]:
    """Add AE-SEED enrichment variants idempotently by variant_id."""
    from gae.evolution import record_evolution_event
    import time

    day_ms = MILLISECONDS_PER_DAY
    events = _build_enrichment_events(time.time() * 1000, day_ms)
    existing_variant_ids = await _get_existing_evolution_variant_ids(client)

    events_added = 0
    events_skipped = 0
    variants_added: set[str] = set()
    variants_skipped: set[str] = set()

    for event in events:
        variant_id = str(event["variant_id"])
        if variant_id in existing_variant_ids:
            events_skipped += 1
            variants_skipped.add(variant_id)
            continue
        await record_evolution_event(client, **event)
        events_added += 1
        variants_added.add(variant_id)

    summary = {
        "events_added": events_added,
        "events_skipped": events_skipped,
        "variants_added": len(variants_added),
        "variants_skipped": len(variants_skipped),
        "variant_ids_added": sorted(variants_added),
        "variant_ids_skipped": sorted(variants_skipped),
    }
    print(f"[SEED] AE enrichment summary: {summary}")
    return summary


async def main(enrich_ae: bool = False) -> None:
    from app.db.graph_client import graph_client

    print("\n[seed_verified_decisions] Connecting to AGE...")
    await graph_client.connect()
    try:
        if enrich_ae:
            await enrich_evolution_events(graph_client)
        else:
            await maybe_seed_verified_decisions(graph_client)
            await seed_demo_evolution_events(graph_client)
    finally:
        await graph_client.close()


if __name__ == "__main__":
    asyncio.run(main(enrich_ae="--enrich-ae" in sys.argv[1:]))
