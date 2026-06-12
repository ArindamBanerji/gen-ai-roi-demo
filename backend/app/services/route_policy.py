"""Benchmark-gated route policy skeleton.

Package 5E Prompt 1 only defines policy resolution metadata. It does not wire
route handlers to serve pipeline output or change SOC analyze behavior.
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping

logger = logging.getLogger(__name__)


class RouteExecutionMode(str, Enum):
    CANONICAL_ONLY = "canonical_only"
    SHADOW = "shadow"
    PIPELINE_SERVED = "pipeline_served"
    DISABLED = "disabled"


CANONICAL_COPILOTS = frozenset({"soc", "trading", "purchasing", "dataops", "s2p"})
_MODE_ALIASES = {
    "canonical_only": RouteExecutionMode.CANONICAL_ONLY,
    "shadow": RouteExecutionMode.SHADOW,
    "shadow_only": RouteExecutionMode.SHADOW,
    "pipeline_read_only": RouteExecutionMode.SHADOW,
    "pipeline_served": RouteExecutionMode.PIPELINE_SERVED,
    "disabled": RouteExecutionMode.DISABLED,
}
_DISABLED_DEPRECATED_MODES = frozenset({"hybrid_fast_path", "fallback_to_canonical"})
_DEPRECATED_MODE_NAMES = frozenset({"shadow_only", "pipeline_read_only", *_DISABLED_DEPRECATED_MODES})


@dataclass(frozen=True)
class RouteDecision:
    copilot: str
    route_name: str
    selected_mode: RouteExecutionMode
    config_source: str
    reason: str
    served_output_source: str
    diagnostics_enabled: bool
    side_effect_policy: str
    benchmark_gate_status: Mapping[str, object] = field(default_factory=dict)
    fallback_state: str = "none"
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    requested_mode: RouteExecutionMode | None = None
    diagnostic_evaluation_source: str = "none"
    approved_for_serving: bool = False

    @property
    def is_blocked(self) -> bool:
        return bool(self.errors)

    def to_diagnostics(self) -> dict[str, object]:
        return {
            "copilot": self.copilot,
            "route_name": self.route_name,
            "selected_mode": self.selected_mode.value,
            "requested_mode": self.requested_mode.value if self.requested_mode else None,
            "config_source": self.config_source,
            "reason": self.reason,
            "served_output_source": self.served_output_source,
            "diagnostic_evaluation_source": self.diagnostic_evaluation_source,
            "diagnostics_enabled": self.diagnostics_enabled,
            "side_effect_policy": self.side_effect_policy,
            "benchmark_gate_status": dict(self.benchmark_gate_status),
            "fallback_state": self.fallback_state,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "approved_for_serving": self.approved_for_serving,
            "blocked": self.is_blocked,
        }


class RoutePolicyResolver:
    """Resolve route execution mode without changing route behavior."""

    def __init__(self, env: Mapping[str, str] | None = None) -> None:
        self._env = env if env is not None else os.environ

    def resolve(self, *, copilot: str, route_name: str) -> RouteDecision:
        normalized_copilot = copilot.strip().lower()
        raw_mode, source = self._read_mode(normalized_copilot)

        if not raw_mode:
            return self._canonical_decision(
                copilot=normalized_copilot,
                route_name=route_name,
                config_source=source,
                reason="no route mode configured; default canonical route remains served",
            )

        raw_mode_normalized = raw_mode.strip().lower()
        warning: tuple[str, ...] = ()
        if raw_mode_normalized in _DEPRECATED_MODE_NAMES:
            message = f"deprecated route mode alias used: {raw_mode_normalized}"
            logger.warning(message)
            warning = (message,)

        if raw_mode_normalized in _DISABLED_DEPRECATED_MODES:
            return RouteDecision(
                copilot=normalized_copilot,
                route_name=route_name,
                selected_mode=RouteExecutionMode.DISABLED,
                requested_mode=RouteExecutionMode.DISABLED,
                config_source=source,
                reason=f"{raw_mode_normalized} is deprecated and disabled; fail closed",
                served_output_source="none",
                diagnostic_evaluation_source="none",
                diagnostics_enabled=True,
                side_effect_policy="blocked_no_side_effects",
                benchmark_gate_status={
                    "approved_for_serving": False,
                    "required": "supported_route_mode",
                    "passed": False,
                },
                fallback_state="fail_closed",
                warnings=warning,
                errors=(f"deprecated route mode disabled: {raw_mode_normalized}",),
                approved_for_serving=False,
            )

        requested_mode = _MODE_ALIASES.get(raw_mode_normalized)
        if requested_mode is None:
            return RouteDecision(
                copilot=normalized_copilot,
                route_name=route_name,
                selected_mode=RouteExecutionMode.DISABLED,
                requested_mode=None,
                config_source=source,
                reason="invalid route mode; fail closed",
                served_output_source="none",
                diagnostic_evaluation_source="none",
                diagnostics_enabled=True,
                side_effect_policy="no_route_execution",
                benchmark_gate_status={"required": "valid_route_mode", "passed": False},
                fallback_state="fail_closed",
                errors=(f"invalid route mode: {raw_mode}",),
                approved_for_serving=False,
            )

        if requested_mode is RouteExecutionMode.CANONICAL_ONLY:
            return self._canonical_decision(
                copilot=normalized_copilot,
                route_name=route_name,
                config_source=source,
                reason="explicit canonical_only route mode",
                requested_mode=requested_mode,
            )

        if requested_mode is RouteExecutionMode.SHADOW:
            return RouteDecision(
                copilot=normalized_copilot,
                route_name=route_name,
                selected_mode=requested_mode,
                requested_mode=requested_mode,
                config_source=source,
                reason="shadow mode is diagnostic-only in the policy skeleton",
                served_output_source="canonical_route",
                diagnostic_evaluation_source="pipeline_diagnostic",
                diagnostics_enabled=True,
                side_effect_policy="diagnostic_zero_side_effects",
                benchmark_gate_status={"approved_for_serving": False, "skeleton_only": True},
                fallback_state="none",
                warnings=warning + ("served output remains canonical in Package 5E Prompt 1",),
                approved_for_serving=False,
            )

        if requested_mode is RouteExecutionMode.PIPELINE_SERVED:
            return RouteDecision(
                copilot=normalized_copilot,
                route_name=route_name,
                selected_mode=RouteExecutionMode.PIPELINE_SERVED,
                requested_mode=requested_mode,
                config_source=source,
                reason="pipeline_served requires a separate approval package and benchmark gates",
                served_output_source="none",
                diagnostic_evaluation_source="none",
                diagnostics_enabled=True,
                side_effect_policy="blocked_no_side_effects",
                benchmark_gate_status={
                    "approved_for_serving": False,
                    "required": "separate_approval_and_benchmark_gates",
                    "passed": False,
                },
                fallback_state="fail_closed",
                errors=("pipeline_served is not active in Package 5E Prompt 1",),
                approved_for_serving=False,
            )

        return RouteDecision(
            copilot=normalized_copilot,
            route_name=route_name,
            selected_mode=RouteExecutionMode.DISABLED,
            requested_mode=requested_mode,
            config_source=source,
            reason="disabled route mode requested",
            served_output_source="none",
            diagnostic_evaluation_source="none",
            diagnostics_enabled=True,
            side_effect_policy="no_route_execution",
            benchmark_gate_status={"approved_for_serving": False},
            fallback_state="fail_closed",
            errors=("route explicitly disabled",),
            approved_for_serving=False,
        )

    def _canonical_decision(
        self,
        *,
        copilot: str,
        route_name: str,
        config_source: str,
        reason: str,
        requested_mode: RouteExecutionMode | None = None,
    ) -> RouteDecision:
        return RouteDecision(
            copilot=copilot,
            route_name=route_name,
            selected_mode=RouteExecutionMode.CANONICAL_ONLY,
            requested_mode=requested_mode,
            config_source=config_source,
            reason=reason,
            served_output_source="canonical_route",
            diagnostic_evaluation_source="none",
            diagnostics_enabled=False,
            side_effect_policy="canonical_current_semantics",
            benchmark_gate_status={"default_canonical": True},
            fallback_state="none",
            approved_for_serving=True,
        )

    def _read_mode(self, copilot: str) -> tuple[str | None, str]:
        if copilot == "soc":
            value = self._env.get("SOC_ROUTE_MODE")
            if value is not None:
                return value, "SOC_ROUTE_MODE"

        policy_value = self._env.get("COPILOT_ROUTE_POLICY")
        if policy_value:
            policy = parse_copilot_route_policy(policy_value)
            if copilot in policy:
                return policy[copilot], "COPILOT_ROUTE_POLICY"

        return None, "default"


def parse_copilot_route_policy(value: str) -> dict[str, str]:
    policy: dict[str, str] = {}
    for item in value.split(","):
        part = item.strip()
        if not part:
            continue
        if ":" not in part:
            policy[part.lower()] = part
            continue
        copilot, mode = part.split(":", 1)
        policy[copilot.strip().lower()] = mode.strip()
    return policy


def resolve_route_policy(
    *,
    copilot: str,
    route_name: str,
    env: Mapping[str, str] | None = None,
) -> RouteDecision:
    return RoutePolicyResolver(env=env).resolve(copilot=copilot, route_name=route_name)
