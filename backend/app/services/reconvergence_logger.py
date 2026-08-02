"""
app/services/reconvergence_logger.py -- EXP-G1 data collection.

Logs re-convergence events to Neo4j so that the temporal compounding
exponent (EXP-G1) can be measured when 90 days of pilot data exists.

Design constraints:
  - NEVER raises -- always degrades safely (triage must not be blocked)
  - Called by re-convergence detection (not yet hooked in -- infrastructure only)
  - Each event stores the 8 fields required by EXP-G1 analysis
"""

import json
import logging
import time
import uuid
from typing import Optional

import numpy as np

log = logging.getLogger(__name__)

_CREATE_EVENT_QUERY = """
CREATE (e:ReConvergenceEvent {
    re_convergence_event_id:          $event_id,
    convergence_start_decisions:      $start,
    convergence_end_decisions:        $end,
    n_reconverge:                     $n_reconverge,
    graph_entity_count_at_start:      $graph_count,
    sigma_squared_per_factor_at_start: $sigma_json,
    trigger_type:                     $trigger_type,
    domain:                           $domain,
    logged_at_epoch:                  $now
})
RETURN e.re_convergence_event_id AS event_id
"""

_READ_EVENTS_QUERY = """
MATCH (e:ReConvergenceEvent)
RETURN e.re_convergence_event_id          AS re_convergence_event_id,
       e.convergence_start_decisions      AS convergence_start_decisions,
       e.convergence_end_decisions        AS convergence_end_decisions,
       e.n_reconverge                     AS n_reconverge,
       e.graph_entity_count_at_start      AS graph_entity_count_at_start,
       e.trigger_type                     AS trigger_type,
       e.domain                           AS domain,
       e.logged_at_epoch                  AS logged_at_epoch
ORDER BY e.logged_at_epoch DESC
LIMIT $limit
"""


async def log_reconvergence_event(
    graph_client,
    convergence_start_decisions: int,
    convergence_end_decisions: int,
    graph_entity_count_at_start: int,
    sigma_squared_per_factor_at_start: dict,
    trigger_type: str,
    domain: str,
) -> Optional[str]:
    """
    Log a re-convergence event to Neo4j.

    Called when accuracy drops below threshold and begins recovering.
    Required for EXP-G1 (temporal compounding exponent measurement).

    Parameters
    ----------
    graph_client                      : async Neo4j client
    convergence_start_decisions       : decision count when accuracy dropped
    convergence_end_decisions         : decision count when accuracy recovered
    graph_entity_count_at_start       : total graph nodes at event start
    sigma_squared_per_factor_at_start : {factor_name: sigma^2} at event start
    trigger_type                      : "threat_landscape_shift" |
                                        "new_category" | "reorganization"
    domain                            : alert category that triggered event

    Returns
    -------
    event_id (str) on success, None on failure.
    Never raises.
    """
    event_id = str(uuid.uuid4())
    n_reconverge = max(0, convergence_end_decisions - convergence_start_decisions)

    try:
        await graph_client.run_query(
            _CREATE_EVENT_QUERY,
            {
                "event_id":    event_id,
                "start":       convergence_start_decisions,
                "end":         convergence_end_decisions,
                "n_reconverge": n_reconverge,
                "graph_count": graph_entity_count_at_start,
                "sigma_json":  json.dumps(sigma_squared_per_factor_at_start,
                                          sort_keys=True),
                "trigger_type": trigger_type,
                "domain":       domain,
                "now":          int(time.time() * 1000),
            },
        )
        log.info("[EXP-G1] Logged re-convergence event %s (domain=%s, n=%d)",
                 event_id, domain, n_reconverge)
        return event_id
    except Exception as exc:
        log.warning("[EXP-G1] Failed to log reconvergence event: %s", exc)
        return None


_CREATE_DISTANCE_LOG_QUERY = """
CREATE (d:DecisionDistanceLog {
    decision_id:                     $decision_id,
    centroid_distance_to_canonical:  $distance,
    pattern_history_value:           $ph_value,
    alert_category_distribution:     $cat_dist,
    logged_at_epoch:                 $now
})
RETURN d.decision_id AS id
"""

_READ_CATEGORY_DIST_QUERY = """
MATCH (d:Decision)
WHERE d.domain = 'soc' AND d.category IS NOT NULL
RETURN d.category AS category, count(d) AS cnt
ORDER BY cnt DESC
LIMIT 100
"""

_READ_DISTANCE_LOG_QUERY = """
MATCH (d:DecisionDistanceLog)
RETURN d.decision_id                    AS decision_id,
       d.centroid_distance_to_canonical AS centroid_distance_to_canonical,
       d.pattern_history_value          AS pattern_history_value,
       d.alert_category_distribution    AS alert_category_distribution,
       d.logged_at_epoch                AS logged_at_epoch
ORDER BY d.logged_at_epoch DESC
LIMIT $limit
"""


async def log_decision_distance(
    graph_client,
    decision_id: str,
    mu: np.ndarray,
    mu_zero: np.ndarray,
    pattern_history_value: float,
    alert_category_distribution: dict,
) -> Optional[str]:
    """
    Log per-decision EXP-G1 fields to a DecisionDistanceLog Neo4j node.

    Fields logged:
      centroid_distance_to_canonical -- L2 norm(mu - mu_zero), primary gamma metric
      pattern_history_value          -- factor_vector[4], W2 enrichment signal
      alert_category_distribution    -- rolling 100-decision category mix

    Never raises -- degrades safely. Returns decision_id on success, None on failure.
    """
    try:
        centroid_distance = float(np.linalg.norm(mu.flatten() - mu_zero.flatten()))

        await graph_client.run_query(
            _CREATE_DISTANCE_LOG_QUERY,
            {
                "decision_id": decision_id,
                "distance":    centroid_distance,
                "ph_value":    float(pattern_history_value),
                "cat_dist":    json.dumps(alert_category_distribution, sort_keys=True),
                "now":         int(time.time() * 1000),
            },
        )
        log.info(
            "[EXP-G1] DecisionDistanceLog written: id=%s dist=%.4f ph=%.4f",
            decision_id, centroid_distance, pattern_history_value,
        )
        return decision_id
    except Exception as exc:
        log.warning("[EXP-G1] DecisionDistanceLog failed: %s", exc)
        return None


async def read_decision_distance_log(graph_client, limit: int = 50) -> list:
    """
    Return the last `limit` DecisionDistanceLog entries. Returns [] on failure.
    """
    try:
        rows = await graph_client.run_query(_READ_DISTANCE_LOG_QUERY, {"limit": limit})
        return [dict(r) for r in (rows or [])]
    except Exception as exc:
        log.warning("[EXP-G1] Failed to read DecisionDistanceLog: %s", exc)
        return []


async def fetch_category_distribution(graph_client) -> dict:
    """
    Query Neo4j for the last 100 decisions and return category mix as dict.
    Returns {} on failure. Values sum to 1.0.
    """
    try:
        rows = await graph_client.run_query(_READ_CATEGORY_DIST_QUERY, {})
        if not rows:
            return {}
        total = sum(int(r["cnt"]) for r in rows)
        if total == 0:
            return {}
        return {r["category"]: round(int(r["cnt"]) / total, 4) for r in rows}
    except Exception as exc:
        log.warning("[EXP-G1] Failed to fetch category distribution: %s", exc)
        return {}


async def read_reconvergence_events(graph_client, limit: int = 50) -> list:
    """
    Read the last `limit` re-convergence events from Neo4j.
    Returns [] on any failure (never raises).
    """
    try:
        rows = await graph_client.run_query(
            _READ_EVENTS_QUERY,
            {"limit": limit},
        )
        return [dict(r) for r in (rows or [])]
    except Exception as exc:
        log.warning("[EXP-G1] Failed to read reconvergence events: %s", exc)
        return []
