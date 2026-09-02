"""Strict SOC-facing wrappers around learning calibration helpers."""

from typing import Any, Mapping, cast

from copilot_sdk.rl import RewardComputer, RewardResult
from gae.calibration import compute_theta_min as _gae_compute_theta_min

from app.services.rl_engine import SOCBinaryReward


def compute_theta_min(alpha: float, V: float) -> float:
    """Compute the deployment threshold, rejecting invalid inputs."""
    if alpha <= 0:
        raise ValueError("alpha must be positive")
    if V <= 0:
        raise ValueError("V must be positive")
    return cast(float, _gae_compute_theta_min(alpha, V))


def compute_soc_binary_reward(
    decision: Mapping[str, Any],
    outcome: Mapping[str, Any],
) -> RewardResult:
    """Compute SOC's binary reward through the SDK RL framework."""
    recommended_action = str(
        decision.get("recommended_action", decision.get("action", ""))
    )
    actual_action = str(outcome.get("actual_action", outcome.get("action", "")))
    return RewardComputer(SOCBinaryReward(), domain="soc").compute(
        recommended_action,
        actual_action,
        outcome,
        decision_id=str(decision.get("decision_id", "")) or None,
    )
