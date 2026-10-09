"""
app/services/override_detector.py -- SOC override detector service.

Loads analyst correct-override examples from AGE ShadowDecision nodes
and activates the module-level OverrideDetector singleton when >= 50
examples are available.

Query filter:
    agreed = false          -- analyst disagreed with AI
    analyst_correct = true  -- analyst was right to disagree
    source = 'v_shadow_synthetic_v3'

The singleton is exposed as `override_detector` for import by the
triage pipeline and any other consumer.
"""

from __future__ import annotations

import logging
from typing import Any

from app.framework.override_detector import OverrideDetector

log = logging.getLogger(__name__)

# Module-level singleton — loaded once at startup via load_from_graph().
override_detector = OverrideDetector()
override_detector.graph_loaded = False

_QUERY = """
MATCH (sd:ShadowDecision)
WHERE sd.agreed = false
  AND sd.analyst_correct = true
  AND sd.source = 'v_shadow_synthetic_v3'
RETURN sd.alert_idx     AS alert_idx,
       sd.category      AS category,
       sd.analyst_action AS analyst_action,
       sd.ai_action     AS ai_action,
       sd.reasoning     AS reasoning
"""


async def load_from_graph(graph_client: Any) -> OverrideDetector:
    """
    Query AGE for correct-override ShadowDecision nodes and load them
    into the module-level singleton.

    Safe to call multiple times -- each call fully replaces the example set.

    Parameters
    ----------
    graph_client:
        Any object with an async `run_query(query, params)` method
        (e.g. app.db.graph_client.graph_client).

    Returns
    -------
    The loaded OverrideDetector singleton (activated iff count >= 50).
    """
    try:
        results = await graph_client.run_query(_QUERY, {})
    except (ConnectionError, TimeoutError, OSError, RuntimeError) as exc:
        log.warning("[OverrideDetector] AGE query failed -- retaining previous set: %s", exc)
        override_detector.graph_loaded = False
        return override_detector
    if results is None or not isinstance(results, list) or any(
        not isinstance(row, dict) for row in results
    ):
        log.warning("[OverrideDetector] AGE query returned malformed data -- retaining previous set")
        override_detector.graph_loaded = False
        return override_detector
    examples = [dict(row) for row in results]

    override_detector.load(examples)
    override_detector.graph_loaded = True

    if override_detector.activated:
        log.info(
            "[OverrideDetector] ACTIVATED -- %d correct-override examples loaded.",
            override_detector.example_count,
        )
    else:
        log.info(
            "[OverrideDetector] inactive -- %d/%d correct-override examples loaded.",
            override_detector.example_count,
            override_detector._threshold,
        )

    return override_detector
