"""Campaign cohort status endpoint."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from app.db.graph_client import graph_client
from app.services.cohort_status import CohortStatusService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/campaign/cohort-status")
async def get_campaign_cohort_status() -> dict[str, Any]:
    """Return campaign cohort day-zero state.

    Always succeeds. Graph read failures produce an empty real cohort, while
    the instrument panel still reports the oracle artifact state.
    """
    records = await _read_decision_records()
    return CohortStatusService(decision_records=records).get_status()


async def _read_decision_records() -> list[dict[str, Any]]:
    query = """
    MATCH (d:Decision)
    WHERE d.domain = 'soc'
    RETURN
        d.decision_id AS decision_id,
        d.provenance AS provenance,
        d.provenance_tier AS provenance_tier,
        d.holdout_group AS holdout_group,
        d.cohort AS cohort,
        d.analyst_action AS analyst_action,
        d.action AS action,
        d.correct AS correct,
        d.quality_signal AS quality_signal,
        d.campaign_id AS campaign_id
    """
    try:
        records = await graph_client.run_query(query)
    except Exception as exc:
        logger.debug("cohort status graph read failed: %s", exc)
        return []
    return [dict(record) for record in records if isinstance(record, dict)]
