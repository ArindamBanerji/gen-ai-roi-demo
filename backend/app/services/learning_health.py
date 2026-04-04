"""
Learning Health Monitor (P9).

Implements two-threshold conservation law monitoring for the GAE learning system:

  Conservation law:  alpha(t) * q(t) * V(t) >= theta_min   (absolute floor)
  Relative drop:     signal >= baseline - k*sigma           (relative threshold)

Status levels:
  CALIBRATING : fewer than 300 decisions recorded (< ~30 days)
  GREEN        : conservation satisfied AND signal >= baseline - 2*sigma
  AMBER        : conservation satisfied BUT signal < baseline - 2*sigma
  RED          : conservation violated OR signal < baseline - 3*sigma

Auto-pause triggers after AUTO_PAUSE_RED_DAYS=14 consecutive RED days.

Reference: docs/project_status_and_plan_v3_part2.md P9
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

import numpy as np
from gae.calibration import derive_theta_min, check_conservation

from app.services.gae_state import get_learning_state

log = logging.getLogger(__name__)

CALIBRATION_DECISIONS: int = 300   # proxy for ~30 days at ~10/day
CALIBRATION_DAYS:      int = 30
AUTO_PAUSE_RED_DAYS:   int = 14
WINDOW_DECISIONS:      int = 50    # rolling window for alpha/q estimation


class LearningHealthMonitor:
    """Two-threshold conservation law monitor for the GAE learning system."""

    CALIBRATION_DAYS    = CALIBRATION_DAYS
    AUTO_PAUSE_RED_DAYS = AUTO_PAUSE_RED_DAYS
    AMBER_SIGMA         = 2.0
    RED_SIGMA           = 3.0

    # -------------------------------------------------------------------------
    # Component extraction
    # -------------------------------------------------------------------------

    @staticmethod
    def _extract_components(history: list, window: int = WINDOW_DECISIONS) -> dict:
        """Extract alpha, q, V from the last `window` WeightUpdate entries.

        Returns
        -------
        dict with keys: alpha (float), q (float), V (float), n (int)
            alpha — mean effective learning rate
            q     — mean confidence at decision time (signal quality proxy)
            V     — decisions per day (volume); falls back to raw count
        """
        if not history:
            return {"alpha": 0.0, "q": 0.0, "V": 0.0, "n": 0}

        recent = history[-window:]
        alphas = [wu.alpha_effective for wu in recent if hasattr(wu, "alpha_effective")]
        confs  = [wu.confidence_at_decision for wu in recent if hasattr(wu, "confidence_at_decision")]

        alpha = float(np.mean(alphas)) if alphas else 0.0
        q     = float(np.mean(confs))  if confs  else 0.0

        # V: decisions per day estimated from timestamp spread
        V = float(len(recent))  # fallback: raw count
        if len(recent) >= 2:
            try:
                from datetime import datetime
                t0_str = getattr(recent[0],  "timestamp", None)
                t1_str = getattr(recent[-1], "timestamp", None)
                if t0_str and t1_str:
                    t0 = datetime.fromisoformat(str(t0_str).replace("Z", "+00:00"))
                    t1 = datetime.fromisoformat(str(t1_str).replace("Z", "+00:00"))
                    span_days = max((t1 - t0).total_seconds() / 86400.0, 1 / 1440.0)
                    V = len(recent) / span_days
            except Exception as exc:
                log.debug("[HEALTH] V estimation failed: %s", exc)

        return {"alpha": alpha, "q": q, "V": V, "n": len(history)}

    # -------------------------------------------------------------------------
    # Signal computation
    # -------------------------------------------------------------------------

    @staticmethod
    def _compute_signal(alpha: float, q: float, V: float) -> float:
        """alpha * q * V composite conservation signal."""
        return alpha * q * V

    @staticmethod
    def _build_calibration_baseline(history: list) -> tuple[float, float]:
        """
        Derive baseline mean and std from the first CALIBRATION_DECISIONS window.

        Samples signal at every 10th decision using a 50-decision rolling window.
        Returns (baseline_mean, baseline_std).
        """
        cal_window = history[:CALIBRATION_DECISIONS]
        if not cal_window:
            return 0.0, 0.0

        signals: list[float] = []
        for i in range(0, len(cal_window), 10):
            chunk = cal_window[max(0, i - WINDOW_DECISIONS) : i + 1]
            if chunk:
                c = LearningHealthMonitor._extract_components(chunk, window=len(chunk))
                signals.append(LearningHealthMonitor._compute_signal(c["alpha"], c["q"], c["V"]))

        if not signals:
            return 0.0, 0.0

        return float(np.mean(signals)), float(np.std(signals))

    # -------------------------------------------------------------------------
    # Main evaluation
    # -------------------------------------------------------------------------

    @staticmethod
    async def evaluate(neo4j_service: Any = None) -> dict:
        """
        Evaluate current learning health.

        Parameters
        ----------
        neo4j_service : optional Neo4j client (for RED-day count from HealthLog nodes)

        Returns
        -------
        dict:
            status            : "GREEN" | "AMBER" | "RED" | "CALIBRATING"
            signal            : float  (alpha * q * V)
            theta_min         : float  (absolute conservation floor)
            conservation      : dict   (passed, status, headroom)
            components        : dict   (alpha, q, V, n)
            baseline          : float | None
            baseline_std      : float | None
            red_days          : int
            auto_pause_active : bool
            interpretation    : str
        """
        state          = get_learning_state()
        history        = getattr(state, "history", [])
        decision_count = getattr(state, "decision_count", len(history))

        comps          = LearningHealthMonitor._extract_components(history)
        alpha, q, V    = comps["alpha"], comps["q"], comps["V"]
        theta_min      = derive_theta_min()
        cc             = check_conservation(alpha, q, V, theta_min)
        signal         = LearningHealthMonitor._compute_signal(alpha, q, V)

        # ── Calibration phase ────────────────────────────────────────────────
        if decision_count < CALIBRATION_DECISIONS:
            return {
                "status":            "CALIBRATING",
                "signal":            round(signal, 6),
                "theta_min":         round(theta_min, 6),
                "conservation":      {
                    "passed":   cc.passed,
                    "status":   cc.status,
                    "headroom": round(cc.headroom, 4),
                },
                "components":        _round_comps(comps),
                "baseline":          None,
                "baseline_std":      None,
                "red_days":          0,
                "auto_pause_active": False,
                "interpretation":    (
                    f"Calibrating — {decision_count} decisions recorded "
                    f"(target: {CALIBRATION_DECISIONS} / ~{CALIBRATION_DAYS} days)"
                ),
            }

        # ── Baseline from calibration window ─────────────────────────────────
        baseline, baseline_std = LearningHealthMonitor._build_calibration_baseline(history)

        # ── Two-threshold status ──────────────────────────────────────────────
        amber_floor = baseline - LearningHealthMonitor.AMBER_SIGMA * baseline_std
        red_floor   = baseline - LearningHealthMonitor.RED_SIGMA   * baseline_std

        if not cc.passed or signal < red_floor:
            status = "RED"
        elif signal < amber_floor:
            status = "AMBER"
        else:
            status = "GREEN"

        # ── RED-day count (HealthLog nodes or approximation) ─────────────────
        red_days          = await LearningHealthMonitor._count_red_days(neo4j_service)
        auto_pause_active = red_days >= AUTO_PAUSE_RED_DAYS

        return {
            "status":            status,
            "signal":            round(signal, 6),
            "theta_min":         round(theta_min, 6),
            "conservation":      {
                "passed":   cc.passed,
                "status":   cc.status,
                "headroom": round(cc.headroom, 4),
            },
            "components":        _round_comps(comps),
            "baseline":          round(baseline, 6),
            "baseline_std":      round(baseline_std, 6),
            "red_days":          red_days,
            "auto_pause_active": auto_pause_active,
            "interpretation":    LearningHealthMonitor._interpret(
                status, signal, theta_min, red_days
            ),
        }

    # -------------------------------------------------------------------------
    # RED-day counting
    # -------------------------------------------------------------------------

    @staticmethod
    async def _count_red_days(neo4j_service: Any) -> int:
        """
        Count consecutive RED-status days from HealthLog nodes.

        Returns 0 if neo4j_service is None or the query fails.
        """
        if neo4j_service is None:
            return 0
        try:
            rows = await neo4j_service.run_query(
                """
                MATCH (h:HealthLog)
                WHERE h.status = 'RED'
                  AND h.timestamp_epoch >= $cutoff_epoch
                RETURN count(DISTINCT (h.timestamp_epoch / 86400000)) AS red_days
                """,
                {"cutoff_epoch": int((datetime.utcnow().timestamp() - (AUTO_PAUSE_RED_DAYS + 1) * 86400) * 1000)},
            )
            return int((rows[0].get("red_days") or 0) if rows else 0)
        except Exception as exc:
            log.debug("[HEALTH] red_days query failed: %s", exc)
            return 0

    # -------------------------------------------------------------------------
    # Interpretation
    # -------------------------------------------------------------------------

    @staticmethod
    def _interpret(status: str, signal: float, theta_min: float, red_days: int) -> str:
        if status == "GREEN":
            return "Conservation law satisfied — learning system is healthy"
        if status == "AMBER":
            return (
                f"Signal degraded below baseline-{LearningHealthMonitor.AMBER_SIGMA}sigma "
                f"(signal={signal:.4f}) — monitor closely"
            )
        if status == "RED":
            if red_days >= AUTO_PAUSE_RED_DAYS:
                return (
                    f"AUTO-PAUSE active: {red_days} RED days >= {AUTO_PAUSE_RED_DAYS} threshold "
                    "— learning updates suspended"
                )
            return (
                f"Conservation violation (signal={signal:.4f} < theta_min={theta_min:.4f}) "
                f"— {red_days} RED day(s) accumulated"
            )
        return f"Status: {status}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _round_comps(comps: dict) -> dict:
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in comps.items()}
