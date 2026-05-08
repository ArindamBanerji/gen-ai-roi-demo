"""Read-only RL observability endpoints."""

from __future__ import annotations

import logging
from dataclasses import asdict, is_dataclass
from typing import Any

from fastapi import APIRouter, Query

from app.domains.soc.config import SCORER_ACTIONS, SOC_CATEGORIES
from app.services import rl_engine
from app.services.rl_engine import get_reward_ledger

log = logging.getLogger(__name__)

router = APIRouter(prefix="/rl", tags=["RL Observability"])


def _to_dict(value: Any) -> dict[str, Any]:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return dict(value)
    return dict(value)


def _clamp_limit(limit: int) -> int:
    return max(1, min(int(limit), 100))


def _safe_error(exc: Exception) -> str:
    return str(exc)


@router.get("/reward-ledger/summary")
async def reward_ledger_summary() -> dict[str, Any]:
    """Return the in-memory graded reward ledger summary."""
    try:
        summary = dict(get_reward_ledger().get_summary())
        summary.setdefault("total", summary.get("total_entries", 0))
        return summary
    except Exception as exc:
        log.warning("[RL API] reward ledger summary failed: %s", exc)
        return {"total": 0, "error": _safe_error(exc)}


@router.get("/reward-ledger/entries")
async def reward_ledger_entries(limit: int = Query(20)) -> dict[str, Any]:
    """Return recent reward ledger entries without mutating ledger state."""
    capped_limit = _clamp_limit(limit)
    try:
        entries = [_to_dict(entry) for entry in get_reward_ledger().get_entries(capped_limit)]
        return {"entries": entries, "limit": capped_limit}
    except Exception as exc:
        log.warning("[RL API] reward ledger entries failed: %s", exc)
        return {"entries": [], "limit": capped_limit, "error": _safe_error(exc)}


@router.get("/posteriors/summary")
async def posterior_summary() -> dict[str, Any]:
    """Return posterior parameters.

    In production this endpoint should be admin-authenticated because posterior
    values reveal learned exploration preferences.
    """
    try:
        policy = getattr(rl_engine, "_exploration_policy", None)
        n_categories = len(SOC_CATEGORIES)
        n_actions = len(SCORER_ACTIONS)
        epsilon_base = 0.05
        target_headroom = 10.0
        alphas = [[1.0 for _ in range(n_actions)] for _ in range(n_categories)]
        betas = [[1.0 for _ in range(n_actions)] for _ in range(n_categories)]

        if policy is not None:
            n_categories = int(policy.n_categories)
            n_actions = int(policy.n_actions)
            epsilon_base = float(policy.epsilon_base)
            target_headroom = float(policy.target_headroom)
            alphas = [list(row) for row in policy.alphas]
            betas = [list(row) for row in policy.betas]

        cells: list[dict[str, Any]] = []
        for category_index in range(n_categories):
            category = (
                SOC_CATEGORIES[category_index]
                if category_index < len(SOC_CATEGORIES)
                else f"category_{category_index}"
            )
            alpha_row = alphas[category_index] if category_index < len(alphas) else []
            beta_row = betas[category_index] if category_index < len(betas) else []
            for action_index in range(n_actions):
                action = (
                    SCORER_ACTIONS[action_index]
                    if action_index < len(SCORER_ACTIONS)
                    else f"action_{action_index}"
                )
                alpha = float(alpha_row[action_index]) if action_index < len(alpha_row) else 1.0
                beta = float(beta_row[action_index]) if action_index < len(beta_row) else 1.0
                denom = alpha + beta
                mean = alpha / denom if denom > 0 else 0.5
                # Prior-adjusted estimate for standard uninformative (1,1) priors.
                total_observations = max(int(alpha + beta - 2.0), 0)
                cells.append({
                    "category": category,
                    "action": action,
                    "alpha": round(alpha, 4),
                    "beta": round(beta, 4),
                    "mean": round(mean, 4),
                    "total_observations": total_observations,
                })

        return {
            "n_categories": n_categories,
            "n_actions": n_actions,
            "epsilon_base": epsilon_base,
            "target_headroom": target_headroom,
            "cells": cells,
            "initialized": policy is not None,
        }
    except Exception as exc:
        log.warning("[RL API] posterior summary failed: %s", exc)
        return {"cells": [], "error": _safe_error(exc)}


@router.get("/chain-credit/{decision_id}")
async def chain_credit(decision_id: str) -> dict[str, Any]:
    """Return chain credit received by and given from one decision."""
    try:
        credits = get_reward_ledger().get_chain_credits()
        credits_received = []
        credits_given = []
        for credit in credits:
            item = _to_dict(credit)
            if item.get("target_decision_id") == decision_id:
                credits_received.append({
                    "source": item.get("source_decision_id"),
                    "reward": item.get("chain_reward"),
                    "gamma": item.get("gamma"),
                    "age": item.get("age"),
                })
            if item.get("source_decision_id") == decision_id:
                credits_given.append({
                    "target": item.get("target_decision_id"),
                    "reward": item.get("chain_reward"),
                    "gamma": item.get("gamma"),
                    "age": item.get("age"),
                })
        return {
            "decision_id": decision_id,
            "credits_received": credits_received,
            "credits_given": credits_given,
        }
    except Exception as exc:
        log.warning("[RL API] chain credit lookup failed: %s", exc)
        return {
            "decision_id": decision_id,
            "credits_received": [],
            "credits_given": [],
            "error": _safe_error(exc),
        }


@router.get("/status")
async def rl_status() -> dict[str, Any]:
    """Return RL subsystem feature flags and initialized component status."""
    try:
        from app.domains.soc import config as soc_config

        ledger = getattr(rl_engine, "_reward_ledger", None)
        policy = getattr(rl_engine, "_exploration_policy", None)
        entries = ledger.get_entries(limit=100000) if ledger is not None else []
        return {
            "flags": {
                "reward_ledger": bool(soc_config.RL_REWARD_LEDGER_ENABLED),
                "exploration": bool(soc_config.RL_EXPLORATION_ENABLED),
                "eta_modulation": bool(soc_config.RL_ETA_MODULATION_ENABLED),
                "chain_credit": bool(soc_config.RL_CHAIN_CREDIT_ENABLED),
            },
            "components": {
                "reward_computer": getattr(rl_engine, "_reward_computer", None) is not None,
                "reward_ledger": ledger is not None,
                "exploration_policy": policy is not None,
                "credit_assigner": getattr(rl_engine, "_credit_assigner", None) is not None,
                "posterior_store": getattr(rl_engine, "_posterior_store", None) is not None,
            },
            "ledger_entry_count": len(entries),
        }
    except Exception as exc:
        log.warning("[RL API] status failed: %s", exc)
        return {"error": _safe_error(exc)}
