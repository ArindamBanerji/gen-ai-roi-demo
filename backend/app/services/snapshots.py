"""
ProfileSnapshot service -- persists centroid state to Neo4j every 50 decisions.

A ProfileSnapshot node captures the full mu tensor at a point in time so that
IKS trend computation has historical anchor points to compare against.

Reference: docs/soc_copilot_design_v1.md Sec.14 (IKS / ProfileSnapshot).
"""

import logging
import time
from datetime import datetime

log = logging.getLogger(__name__)

_SNAPSHOT_INTERVAL = 50  # decisions between snapshots


async def maybe_write_profile_snapshot(decision_count: int) -> None:
    """
    Write a ProfileSnapshot node to Neo4j if decision_count is a multiple of
    _SNAPSHOT_INTERVAL (50).

    Call this after save_learning_state() in the outcome write-back path.
    No-op if the interval has not been reached.

    Parameters
    ----------
    decision_count : int
        Current total decision count from the ProfileScorer.
    """
    if decision_count == 0 or decision_count % _SNAPSHOT_INTERVAL != 0:
        return
    await _write_profile_snapshot(decision_count)


async def _write_profile_snapshot(decision_count: int) -> None:
    """Write one ProfileSnapshot node capturing the current mu tensor."""
    try:
        from app.db.neo4j import neo4j_client
        from app.services.gae_state import get_profile_scorer

        scorer = get_profile_scorer()
        mu_list = scorer.centroids.tolist()   # shape (n_categories, n_actions, n_factors)
        counts_list = scorer.counts.tolist()

        await neo4j_client.run_query(
            """
            CREATE (ps:ProfileSnapshot {
                decision_count:  $decision_count,
                timestamp_epoch: $timestamp_epoch,
                mu:              $mu,
                counts:          $counts
            })
            """,
            {
                "decision_count":  decision_count,
                "timestamp_epoch": int(datetime.utcnow().timestamp() * 1000),
                "mu":              str(mu_list),   # store as JSON string (Neo4j has no tensor type)
                "counts":          str(counts_list),
            },
        )
        log.info(
            "[GAE] ProfileSnapshot written at decision_count=%d (mu shape=%s)",
            decision_count,
            list(scorer.centroids.shape),
        )
    except Exception as exc:
        log.warning("[GAE] ProfileSnapshot write failed at step=%d: %s", decision_count, exc)
