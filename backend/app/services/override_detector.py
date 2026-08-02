"""
app/services/override_detector.py -- SOC override detector service.

Loads analyst correct-override examples from Neo4j ShadowDecision nodes
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

# Module-level singleton — loaded once at startup via load_from_neo4j().
override_detector = OverrideDetector()

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


async def load_from_neo4j(graph_client: Any) -> OverrideDetector:
    """
    Query Neo4j for correct-override ShadowDecision nodes and load them
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
        examples = [dict(r) for r in results] if results else []
    except Exception as exc:
        log.warning("[OverrideDetector] Neo4j query failed -- using empty set: %s", exc)
        examples = []

    override_detector.load(examples)

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
