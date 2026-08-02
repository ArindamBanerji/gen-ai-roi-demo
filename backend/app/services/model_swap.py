from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List

import numpy as np
from fastapi import HTTPException

from app.data.alert_pool import get_alert_pool
from app.db.graph_client import graph_client
from app.domains.soc.config import SOCDomainConfig, resolve_alert_category
from app.domains.soc.orchestrator import compute_factor_vector
from app.services.gae_state import get_profile_scorer


@dataclass(slots=True)
class ModelSwapResult:
    ok: bool
    status: str
    n_alerts_requested: int
    n_alerts_processed: int
    llm_calls_made: int
    llm_dependency: bool
    narrative_affects_scoring: bool
    narrative_llm_used: str
    scoring_method: str
    summary: str
    reproducibility_check: Dict[str, Any]
    alerts: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def _get_narrative_llm_name() -> str:
    """Return the configured narrative LLM/provider name if present."""
    for key in ("NARRATIVE_PROVIDER", "NARRATIVE_LLM", "NARRATIVE_MODEL", "LLM_PROVIDER"):
        value = os.getenv(key)
        if value and value.strip():
            return value.strip()
    return "UNKNOWN"


async def _score_alert(
    alert: Dict[str, Any],
    scorer: Any,
    factor_computers: List[Any],
    neo4j_service: Any,
) -> Dict[str, Any]:
    """Compute factors and score a single alert through the real pipeline."""
    alert_payload = dict(alert)
    alert_id = alert_payload.get("alert_id") or alert_payload.get("id") or "UNKNOWN"
    alert_payload.setdefault("alert_id", alert_id)
    alert_payload.setdefault("id", alert_id)

    raw_category = alert_payload.get("category") or alert_payload.get("alert_type") or "unknown"
    category = resolve_alert_category(raw_category)
    if category == "unclassified":
        raise HTTPException(
            status_code=422,
            detail={
                "error": "unclassified_alert_type",
                "alert_type": raw_category,
                "message": "Alert type is not mapped to a scorable SOC category.",
            },
        )
    alert_payload.setdefault("category", category)
    alert_payload.setdefault("alert_type", raw_category)

    factor_vector = await compute_factor_vector(alert_payload, factor_computers, neo4j_service)
    category_index = SOCDomainConfig().get_category_index(category)
    scoring_result = scorer.score(factor_vector.flatten(), category_index=category_index)

    probabilities = np.asarray(scoring_result.probabilities, dtype=np.float64).tolist()
    factor_values = np.asarray(factor_vector, dtype=np.float64).flatten().tolist()

    return {
        "alert_id": alert_id,
        "category": category,
        "category_index": category_index,
        "action_name": scoring_result.action_name,
        "confidence": float(scoring_result.confidence),
        "probabilities": probabilities,
        "factor_vector": factor_values,
    }


async def run_model_swap_trial(neo4j_service=None, n_alerts: int = 20) -> ModelSwapResult:
    neo4j_service = neo4j_service or graph_client
    scorer = get_profile_scorer()
    narrative_llm_used = _get_narrative_llm_name()

    if scorer is None:
        summary = (
            "Zero LLM calls; deterministic centroid tensor + softmax scoring; "
            "narrative affects scoring: False. Scorer not ready."
        )
        return ModelSwapResult(
            ok=False,
            status="error",
            n_alerts_requested=max(0, int(n_alerts)),
            n_alerts_processed=0,
            llm_calls_made=0,
            llm_dependency=False,
            narrative_affects_scoring=False,
            narrative_llm_used=narrative_llm_used,
            scoring_method="deterministic centroid tensor + softmax scoring",
            summary=summary,
            reproducibility_check={
                "passed": False,
                "reason": "ProfileScorer not initialized",
            },
            alerts=[],
            errors=["ProfileScorer not initialized"],
        )

    alert_pool = get_alert_pool()
    if not alert_pool:
        summary = (
            "Zero LLM calls; deterministic centroid tensor + softmax scoring; "
            "narrative affects scoring: False. Demo alert pool empty."
        )
        return ModelSwapResult(
            ok=False,
            status="error",
            n_alerts_requested=max(0, int(n_alerts)),
            n_alerts_processed=0,
            llm_calls_made=0,
            llm_dependency=False,
            narrative_affects_scoring=False,
            narrative_llm_used=narrative_llm_used,
            scoring_method="deterministic centroid tensor + softmax scoring",
            summary=summary,
            reproducibility_check={
                "passed": False,
                "reason": "Demo alert pool empty",
            },
            alerts=[],
            errors=["Demo alert pool empty"],
        )

    requested_alerts = max(0, int(n_alerts))
    selected_alerts = [alert_pool[idx % len(alert_pool)] for idx in range(requested_alerts)]
    factor_computers = SOCDomainConfig.get_factor_computers()

    alert_results: List[Dict[str, Any]] = []
    errors: List[str] = []

    for alert in selected_alerts:
        try:
            result = await _score_alert(alert, scorer, factor_computers, neo4j_service)
            alert_results.append(result)
        except Exception as exc:
            errors.append(f"{alert.get('alert_id') or alert.get('id') or 'UNKNOWN'}: {exc}")

    reproducibility_check: Dict[str, Any]
    if alert_results:
        first_alert = selected_alerts[0]
        try:
            first_run = await _score_alert(first_alert, scorer, factor_computers, neo4j_service)
            second_run = await _score_alert(first_alert, scorer, factor_computers, neo4j_service)
            reproducibility_check = {
                "passed": (
                    first_run["action_name"] == second_run["action_name"]
                    and first_run["confidence"] == second_run["confidence"]
                    and first_run["probabilities"] == second_run["probabilities"]
                    and first_run["factor_vector"] == second_run["factor_vector"]
                ),
                "first_run": first_run,
                "second_run": second_run,
            }
        except Exception as exc:
            reproducibility_check = {
                "passed": False,
                "reason": str(exc),
            }
            errors.append(f"reproducibility_check: {exc}")
    else:
        reproducibility_check = {
            "passed": False,
            "reason": "No alerts were scored",
        }

    summary = (
        "Zero LLM calls; deterministic centroid tensor + softmax scoring; "
        "narrative affects scoring: False. "
        f"Processed {len(alert_results)} of {requested_alerts} demo alerts."
    )

    ok = not errors and len(alert_results) == requested_alerts
    status = "ok" if ok else ("partial" if alert_results else "error")

    return ModelSwapResult(
        ok=ok,
        status=status,
        n_alerts_requested=requested_alerts,
        n_alerts_processed=len(alert_results),
        llm_calls_made=0,
        llm_dependency=False,
        narrative_affects_scoring=False,
        narrative_llm_used=narrative_llm_used,
        scoring_method="deterministic centroid tensor + softmax scoring",
        summary=summary,
        reproducibility_check=reproducibility_check,
        alerts=alert_results,
        errors=errors,
    )
