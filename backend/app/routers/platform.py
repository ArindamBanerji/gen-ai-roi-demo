"""
Platform-level display endpoints.

XC-01 is fixture-backed until Gap H2 replaces the loader with a live graph
query. Keep the response shape stable so the frontend does not change later.
"""

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/platform", tags=["Platform"])

_FIXTURE_PATH = Path(__file__).resolve().parents[3] / "support" / "setup" / "cross_copilot_signals.json"
_DOMAIN_TABLE_PATH = Path(__file__).resolve().parents[3] / "support" / "setup" / "domain_applicability.json"
_WARM_START_PATH = Path(__file__).resolve().parents[3] / "support" / "setup" / "s2p_warm_start_evidence.json"
_CHAIN_CREDIT_PATH = Path(__file__).resolve().parents[3] / "support" / "setup" / "chain_credit_demo.json"
_RL_REWARD_PATH = Path(__file__).resolve().parents[3] / "support" / "setup" / "rl_reward_demo.json"
_RL_EXPLORATION_PATH = Path(__file__).resolve().parents[3] / "support" / "setup" / "rl_exploration_demo.json"
_SIGNAL_CACHE: list[dict[str, Any]] | None = None
_DOMAIN_TABLE_CACHE: dict[str, Any] | None = None
_WARM_START_CACHE: dict[str, Any] | None = None
_CHAIN_CREDIT_CACHE: dict[str, Any] | None = None
_RL_REWARD_CACHE: dict[str, Any] | None = None
_RL_EXPLORATION_CACHE: dict[str, Any] | None = None

NOTE = "Cross-copilot signals emerge from shared graph entities. Neither copilot was programmed to detect these patterns."


def _load_cross_signals() -> list[dict[str, Any]]:
    global _SIGNAL_CACHE
    if _SIGNAL_CACHE is not None:
        return list(_SIGNAL_CACHE)

    try:
        with _FIXTURE_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, list):
            raise ValueError("cross-copilot fixture must contain a list")
        _SIGNAL_CACHE = [item for item in data if isinstance(item, dict)]
    except Exception as exc:
        logger.warning("Cross-copilot signal fixture unavailable: %s", exc)
        _SIGNAL_CACHE = []

    return list(_SIGNAL_CACHE)


def _reset_cross_signal_cache() -> None:
    global _SIGNAL_CACHE
    _SIGNAL_CACHE = None


def _load_domain_table() -> dict[str, Any]:
    global _DOMAIN_TABLE_CACHE
    if _DOMAIN_TABLE_CACHE is not None:
        return dict(_DOMAIN_TABLE_CACHE)

    try:
        with _DOMAIN_TABLE_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("domain applicability fixture must contain an object")
        domains = data.get("domains", [])
        if not isinstance(domains, list):
            raise ValueError("domain applicability fixture domains must contain a list")
        _DOMAIN_TABLE_CACHE = {
            "domains": [item for item in domains if isinstance(item, dict)],
            "engine_version": str(data.get("engine_version", "v0.7.23")),
            "note": str(data.get("note", "")),
            "cross_domain_surfaces": str(data.get("cross_domain_surfaces", "")),
        }
    except Exception as exc:
        logger.warning("Domain applicability fixture unavailable: %s", exc)
        _DOMAIN_TABLE_CACHE = {
            "domains": [],
            "engine_version": "v0.7.23",
            "note": "",
            "cross_domain_surfaces": "",
        }

    return dict(_DOMAIN_TABLE_CACHE)


def _reset_domain_table_cache() -> None:
    global _DOMAIN_TABLE_CACHE
    _DOMAIN_TABLE_CACHE = None


def _load_warm_start_evidence() -> dict[str, Any]:
    global _WARM_START_CACHE
    if _WARM_START_CACHE is not None:
        return dict(_WARM_START_CACHE)

    try:
        with _WARM_START_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("warm-start evidence fixture must contain an object")
        evidence = data.get("warm_start_evidence", [])
        if not isinstance(evidence, list):
            raise ValueError("warm-start evidence fixture evidence must contain a list")
        _WARM_START_CACHE = {
            "warm_start_evidence": [item for item in evidence if isinstance(item, dict)],
            "note": str(data.get("note", "")),
        }
    except Exception as exc:
        logger.warning("Warm-start evidence fixture unavailable: %s", exc)
        _WARM_START_CACHE = {"warm_start_evidence": [], "note": ""}

    return dict(_WARM_START_CACHE)


def _reset_warm_start_cache() -> None:
    global _WARM_START_CACHE
    _WARM_START_CACHE = None


def _load_chain_credit_demo() -> dict[str, Any]:
    global _CHAIN_CREDIT_CACHE
    if _CHAIN_CREDIT_CACHE is not None:
        return dict(_CHAIN_CREDIT_CACHE)

    try:
        with _CHAIN_CREDIT_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("chain-credit fixture must contain an object")
        credits = data.get("chain_credits", [])
        summary = data.get("summary", {})
        if not isinstance(credits, list):
            raise ValueError("chain-credit fixture credits must contain a list")
        if not isinstance(summary, dict):
            raise ValueError("chain-credit fixture summary must contain an object")
        _CHAIN_CREDIT_CACHE = {
            "chain_credits": [item for item in credits if isinstance(item, dict)],
            "summary": dict(summary),
            "note": str(data.get("note", "")),
        }
    except Exception as exc:
        logger.warning("Chain-credit demo fixture unavailable: %s", exc)
        _CHAIN_CREDIT_CACHE = {"chain_credits": [], "summary": {}, "note": ""}

    return dict(_CHAIN_CREDIT_CACHE)


def _reset_chain_credit_cache() -> None:
    global _CHAIN_CREDIT_CACHE
    _CHAIN_CREDIT_CACHE = None


def _load_rl_reward_demo() -> dict[str, Any]:
    global _RL_REWARD_CACHE
    if _RL_REWARD_CACHE is not None:
        return dict(_RL_REWARD_CACHE)

    try:
        with _RL_REWARD_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("RL reward demo fixture must contain an object")
        breakdown = data.get("reward_breakdown", [])
        summary = data.get("summary", {})
        if not isinstance(breakdown, list):
            raise ValueError("RL reward demo fixture reward_breakdown must contain a list")
        if not isinstance(summary, dict):
            raise ValueError("RL reward demo fixture summary must contain an object")
        _RL_REWARD_CACHE = {
            "reward_breakdown": [item for item in breakdown if isinstance(item, dict)],
            "summary": dict(summary),
            "note": str(data.get("note", "")),
        }
    except Exception as exc:
        logger.warning("RL reward demo fixture unavailable: %s", exc)
        _RL_REWARD_CACHE = {"reward_breakdown": [], "summary": {}, "note": ""}

    return dict(_RL_REWARD_CACHE)


def _reset_rl_reward_cache() -> None:
    global _RL_REWARD_CACHE
    _RL_REWARD_CACHE = None


def _load_rl_exploration_demo() -> dict[str, Any]:
    global _RL_EXPLORATION_CACHE
    if _RL_EXPLORATION_CACHE is not None:
        return dict(_RL_EXPLORATION_CACHE)

    try:
        with _RL_EXPLORATION_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("RL exploration demo fixture must contain an object")
        exploration_log = data.get("exploration_log", [])
        summary = data.get("summary", {})
        if not isinstance(exploration_log, list):
            raise ValueError("RL exploration demo fixture exploration_log must contain a list")
        if not isinstance(summary, dict):
            raise ValueError("RL exploration demo fixture summary must contain an object")
        _RL_EXPLORATION_CACHE = {
            "exploration_log": [item for item in exploration_log if isinstance(item, dict)],
            "summary": dict(summary),
            "note": str(data.get("note", "")),
        }
    except Exception as exc:
        logger.warning("RL exploration demo fixture unavailable: %s", exc)
        _RL_EXPLORATION_CACHE = {"exploration_log": [], "summary": {}, "note": ""}

    return dict(_RL_EXPLORATION_CACHE)


def _reset_rl_exploration_cache() -> None:
    global _RL_EXPLORATION_CACHE
    _RL_EXPLORATION_CACHE = None


def reset_platform_caches() -> None:
    _reset_cross_signal_cache()
    _reset_domain_table_cache()
    _reset_warm_start_cache()
    _reset_chain_credit_cache()
    _reset_rl_reward_cache()
    _reset_rl_exploration_cache()


@router.get("/cross-signals")
async def get_cross_signals() -> dict[str, Any]:
    signals = _load_cross_signals()
    statuses = [str(signal.get("status", "")).lower() for signal in signals]
    source_domains = sorted({
        str(signal.get("source_domain"))
        for signal in signals
        if signal.get("source_domain")
    })
    return {
        "signals": signals,
        "total": len(signals),
        "active": statuses.count("active"),
        "acknowledged": statuses.count("acknowledged"),
        "source_domains": source_domains,
        "note": NOTE,
    }


@router.get("/domain-applicability")
async def get_domain_applicability() -> dict[str, Any]:
    table = _load_domain_table()
    domains = list(table.get("domains", []))
    statuses = [str(domain.get("status", "")).lower() for domain in domains]
    return {
        "domains": domains,
        "total": len(domains),
        "live": statuses.count("live"),
        "specified": statuses.count("specified"),
        "designed": statuses.count("designed"),
        "engine_version": table.get("engine_version", "v0.7.23"),
        "note": table.get("note", ""),
        "cross_domain_surfaces": table.get("cross_domain_surfaces", ""),
    }


@router.get("/warm-start-evidence")
async def get_warm_start_evidence() -> dict[str, Any]:
    data = _load_warm_start_evidence()
    evidence = list(data.get("warm_start_evidence", []))
    return {
        "evidence": evidence,
        "total": len(evidence),
        "note": data.get("note", ""),
    }


@router.get("/chain-credit-demo")
async def get_chain_credit_demo() -> dict[str, Any]:
    data = _load_chain_credit_demo()
    credits = list(data.get("chain_credits", []))
    return {
        "chain_credits": credits,
        "summary": data.get("summary", {}),
        "note": data.get("note", ""),
    }


@router.get("/rl-reward-demo")
async def get_rl_reward_demo() -> dict[str, Any]:
    data = _load_rl_reward_demo()
    return {
        "reward_breakdown": list(data.get("reward_breakdown", [])),
        "summary": data.get("summary", {}),
        "note": data.get("note", ""),
    }


@router.get("/rl-exploration-demo")
async def get_rl_exploration_demo() -> dict[str, Any]:
    data = _load_rl_exploration_demo()
    return {
        "exploration_log": list(data.get("exploration_log", [])),
        "summary": data.get("summary", {}),
        "note": data.get("note", ""),
    }
