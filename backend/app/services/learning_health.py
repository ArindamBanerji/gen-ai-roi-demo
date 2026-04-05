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


# ---------------------------------------------------------------------------
# Block 9.2 — Spike detector (deployment-specific σ)
# ---------------------------------------------------------------------------

_VOLUME_WINDOW_DAYS = 30


async def compute_volume_baseline(neo4j_client: Any) -> dict:
    """
    Compute rolling 30-day alert volume baseline from Alert nodes.

    Groups alerts into daily buckets using timestamp_epoch.
    spike_sigma comes from GateConfig — 5.0 before N_min, 3.0 after.

    Returns
    -------
    dict:
      daily_mean      : float  — mean daily alert count over window
      daily_std       : float  — std of daily counts (floor=1.0)
      spike_threshold : float  — mean + spike_sigma * std
      spike_sigma     : float  — 5.0 (conservative) or 3.0 (calibrated)
      window_days     : int    — 30
      data_points     : int    — number of days with at least one alert
    """
    import time as _time
    from app.domains.soc.config import GateConfig

    now_epoch   = int(_time.time() * 1000)
    cutoff_epoch = now_epoch - _VOLUME_WINDOW_DAYS * 86_400_000

    daily_counts: list[float] = []
    try:
        rows = await neo4j_client.run_query(
            """
            MATCH (a:Alert)
            WHERE a.timestamp_epoch > $cutoff_epoch
            WITH a.timestamp_epoch / 86400000 AS day_bucket, count(a) AS daily_count
            RETURN day_bucket, daily_count
            ORDER BY day_bucket
            """,
            {"cutoff_epoch": cutoff_epoch},
        )
        daily_counts = [float(r.get("daily_count") or 0) for r in rows if r.get("daily_count")]
    except Exception as exc:
        log.warning("[D3] volume_baseline query failed: %s", exc)

    daily_mean = float(np.mean(daily_counts)) if daily_counts else 0.0
    daily_std  = float(np.std(daily_counts))  if daily_counts else 0.0
    # Floor std at 1.0 to prevent degenerate zero-variance threshold
    daily_std_floored = max(daily_std, 1.0)

    # spike_sigma from GateConfig — uses current decision count
    n_decisions = 0
    try:
        from app.services.gae_state import get_learning_state as _get_ls
        n_decisions = _get_ls().decision_count
    except Exception:
        pass
    cfg = GateConfig(n_decisions=n_decisions, V=200.0, alpha=0.25)
    spike_sigma = cfg.spike_sigma

    spike_threshold = daily_mean + spike_sigma * daily_std_floored

    return {
        "daily_mean":      round(daily_mean, 2),
        "daily_std":       round(daily_std, 2),
        "spike_threshold": round(spike_threshold, 2),
        "spike_sigma":     spike_sigma,
        "window_days":     _VOLUME_WINDOW_DAYS,
        "data_points":     len(daily_counts),
    }


async def detect_volume_spike(neo4j_client: Any, today_count: int) -> dict:
    """
    Compare today's alert count against the 30-day baseline.

    Parameters
    ----------
    neo4j_client : async Neo4j client
    today_count  : int — number of alerts received so far today

    Returns
    -------
    dict:
      spike_detected  : bool
      today_count     : int
      spike_threshold : float
      daily_mean      : float
      daily_std       : float
    """
    baseline = await compute_volume_baseline(neo4j_client)
    spike_detected = today_count > baseline["spike_threshold"]

    if spike_detected:
        log.warning(
            "[D3] Volume spike detected: today=%d > threshold=%.1f "
            "(mean=%.1f, std=%.1f, sigma=%.1f)",
            today_count,
            baseline["spike_threshold"],
            baseline["daily_mean"],
            baseline["daily_std"],
            baseline["spike_sigma"],
        )

    return {
        "spike_detected":  spike_detected,
        "today_count":     today_count,
        "spike_threshold": baseline["spike_threshold"],
        "daily_mean":      baseline["daily_mean"],
        "daily_std":       baseline["daily_std"],
    }


# ---------------------------------------------------------------------------
# Block 9.1 — Per-analyst precision computation
# ---------------------------------------------------------------------------

_MIN_ANALYST_DECISIONS = 10   # exclude analysts with fewer decisions
_MIN_ANALYSTS_REQUIRED = 2    # return {} if fewer than 2 analysts qualify


async def compute_analyst_precision(neo4j_client: Any) -> dict[str, float]:
    """
    Compute per-analyst override precision from Decision nodes.

    Only counts live decisions (d.source = "live") where the analyst is known.
    Excludes analysts with fewer than _MIN_ANALYST_DECISIONS (10) decisions.
    Returns {} if fewer than _MIN_ANALYSTS_REQUIRED (2) analysts qualify.

    Returns
    -------
    dict mapping analyst name → precision (correct / total), e.g.
      {"analyst_a": 0.82, "analyst_b": 0.71}
    """
    try:
        rows = await neo4j_client.run_query(
            """
            MATCH (d:Decision)
            WHERE d.source = "live" AND d.analyst IS NOT NULL
            WITH d.analyst AS analyst,
                 count(d) AS total,
                 sum(CASE WHEN d.correct = true THEN 1 ELSE 0 END) AS correct
            WHERE total >= $min_decisions
            RETURN analyst, toFloat(correct) / toFloat(total) AS precision
            """,
            {"min_decisions": _MIN_ANALYST_DECISIONS},
        )
    except Exception as exc:
        log.warning("[D5] compute_analyst_precision query failed: %s", exc)
        return {}

    result = {
        r["analyst"]: float(r["precision"])
        for r in rows
        if r.get("analyst") and r.get("precision") is not None
    }

    if len(result) < _MIN_ANALYSTS_REQUIRED:
        return {}

    return result


# ---------------------------------------------------------------------------
# Block 7.6 — Verification rate health
# ---------------------------------------------------------------------------

async def compute_verification_health(neo4j_client: Any) -> dict:
    """
    Compute verification rate health across 3 conditions.

    Condition 1 — Coverage: verified_decisions / total_decisions >= 0.20
    Condition 2 — Drift: last-7d rate >= prior-7d rate * 0.80
    Condition 3 — Conservation: GREEN or UNKNOWN (not AMBER/RED)

    Status:
      GREEN : all 3 conditions healthy
      AMBER : 1-2 conditions unhealthy
      RED   : all 3 unhealthy, OR coverage_rate == 0

    Feeds the Phase 6 verification health dashboard (Tab 2).
    """
    import time as _time
    now_ms         = int(_time.time() * 1000)
    day_ms         = 86_400_000
    last_7d_start  = now_ms - 7  * day_ms
    prior_7d_start = now_ms - 14 * day_ms

    # ── Condition 1: overall coverage ────────────────────────────────────────
    total_decisions    = 0
    verified_decisions = 0
    try:
        rows = await neo4j_client.run_query(
            "MATCH (d:Decision) RETURN count(d) AS total", {}
        )
        total_decisions = int((rows[0].get("total") or 0) if rows else 0)
    except Exception as exc:
        log.debug("[VERIF-HEALTH] total_decisions query failed: %s", exc)

    try:
        rows = await neo4j_client.run_query(
            "MATCH (d:Decision) "
            "WHERE d.outcome IS NOT NULL AND d.verified_at_epoch IS NOT NULL "
            "RETURN count(d) AS verified",
            {},
        )
        verified_decisions = int((rows[0].get("verified") or 0) if rows else 0)
    except Exception as exc:
        log.debug("[VERIF-HEALTH] verified_decisions query failed: %s", exc)

    coverage_rate    = (verified_decisions / total_decisions) if total_decisions > 0 else 0.0
    coverage_healthy = coverage_rate >= 0.20

    # ── Condition 2: drift (last 7d vs prior 7d) ─────────────────────────────
    def _rate(verified: int, total: int) -> float:
        return (verified / total) if total > 0 else 0.0

    last_7d_total = last_7d_verified = 0
    prior_7d_total = prior_7d_verified = 0
    try:
        rows = await neo4j_client.run_query(
            """
            MATCH (d:Decision)
            WHERE d.timestamp_epoch >= $last_start AND d.timestamp_epoch < $now
            RETURN
              count(d) AS total,
              count(CASE WHEN d.verified_at_epoch IS NOT NULL THEN 1 END) AS verified
            """,
            {"last_start": last_7d_start, "now": now_ms},
        )
        if rows:
            last_7d_total    = int(rows[0].get("total")    or 0)
            last_7d_verified = int(rows[0].get("verified") or 0)
    except Exception as exc:
        log.debug("[VERIF-HEALTH] last_7d query failed: %s", exc)

    try:
        rows = await neo4j_client.run_query(
            """
            MATCH (d:Decision)
            WHERE d.timestamp_epoch >= $prior_start AND d.timestamp_epoch < $last_start
            RETURN
              count(d) AS total,
              count(CASE WHEN d.verified_at_epoch IS NOT NULL THEN 1 END) AS verified
            """,
            {"prior_start": prior_7d_start, "last_start": last_7d_start},
        )
        if rows:
            prior_7d_total    = int(rows[0].get("total")    or 0)
            prior_7d_verified = int(rows[0].get("verified") or 0)
    except Exception as exc:
        log.debug("[VERIF-HEALTH] prior_7d query failed: %s", exc)

    rate_last_7d  = _rate(last_7d_verified,  last_7d_total)
    rate_prior_7d = _rate(prior_7d_verified, prior_7d_total)
    # Drift healthy if last_7d rate >= 80% of prior_7d rate.
    # If prior rate is 0 (no decisions in that window), treat as healthy.
    drift_healthy = (
        rate_last_7d >= rate_prior_7d * 0.80
        if rate_prior_7d > 0
        else True
    )

    # ── Condition 3: conservation status ─────────────────────────────────────
    conservation_status = "UNKNOWN"
    try:
        health = await LearningHealthMonitor.evaluate(neo4j_client)
        conservation_status = health.get("status", "UNKNOWN")
    except Exception as exc:
        log.debug("[VERIF-HEALTH] conservation check failed: %s", exc)

    conservation_healthy = conservation_status in ("GREEN", "CALIBRATING", "UNKNOWN")

    # ── Overall status ────────────────────────────────────────────────────────
    unhealthy_count = sum([
        not coverage_healthy,
        not drift_healthy,
        not conservation_healthy,
    ])

    if coverage_rate == 0 or unhealthy_count == 3:
        status = "RED"
    elif unhealthy_count >= 1:
        status = "AMBER"
    else:
        status = "GREEN"

    return {
        "status":              status,
        "coverage_rate":       round(coverage_rate, 4),
        "coverage_healthy":    coverage_healthy,
        "drift_rate_last_7d":  round(rate_last_7d,  4),
        "drift_rate_prior_7d": round(rate_prior_7d, 4),
        "drift_healthy":       drift_healthy,
        "conservation_status": conservation_status,
        "conservation_healthy": conservation_healthy,
        "total_decisions":     total_decisions,
        "verified_decisions":  verified_decisions,
        "timestamp_epoch":     now_ms,
    }
