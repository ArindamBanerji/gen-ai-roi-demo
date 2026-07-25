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

Auto-pause triggers after AUTO_PAUSE_RED_DAYS=14 RED days in a 30-day rolling window.

Reference: docs/project_status_and_plan_v3_part2.md P9
"""

from __future__ import annotations

import logging
import asyncio
from datetime import datetime
from typing import Any, Optional

import numpy as np
from gae.calibration import compute_theta_min, derive_theta_min, check_conservation

from app.services.gae_state import get_learning_state, get_learning_store
from app.db.neo4j import soc_decision_where

log = logging.getLogger(__name__)

CALIBRATION_DECISIONS: int = 300   # proxy for ~30 days at ~10/day
CALIBRATION_DAYS:      int = 30
AUTO_PAUSE_RED_DAYS:   int = 14
# Cumulative-over-window, NOT consecutive. The conservation law (α·q·V ≥ θ_min)
# uses rolling aggregates — q over 400 decisions, α/V over 50. The auto-pause arm
# must use the same temporal model. Consecutive-only counting creates a semantic
# mismatch: a system can breach the rolling conservation signal while the consecutive
# counter keeps resetting on intermittent GREEN days.
AUTO_PAUSE_LOOKBACK_DAYS: int = 30  # ~2x threshold; covers 3-4x q_window at V=200
WINDOW_DECISIONS:      int = 50    # rolling window for alpha/q estimation
CONSERVATIVE_THETA_MIN: float = 1_000_000_000.0
_L5_CONSERVATION_STORE_LOCK = asyncio.Lock()


def _is_learning_enabled(default: bool = True) -> bool:
    """Lazy-import LEARNING_ENABLED from SOC config.

    Fail open to True so non-SOC or broken-config contexts do not mask real
    RED conservation states as pre-activation.
    """
    try:
        from app.domains.soc.config import LEARNING_ENABLED

        return bool(LEARNING_ENABLED)
    except (ImportError, AttributeError):
        return default


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
    def _extract_components(
        history: list, window: int = WINDOW_DECISIONS, q_window: int = 400
    ) -> dict:
        """Extract legacy health components from verified WeightUpdate history.

        Returns
        -------
        dict with keys: alpha (float), q (float), V (float), n (int)
            alpha -- legacy mean effective learning rate over the last `window`
                    verified decisions. This value is kept only as historical
                    diagnostics and must not be used as theta_min alpha.
            q     -- fraction of the last `q_window` verified decisions with
                    outcome == +1 (stable rolling verified accuracy)
            V     -- decisions per day over the last `window` verified
                    decisions; falls back to raw count

        Notes
        -----
        History is verified-only in the backend paths that populate it:
        triage and simulation both pass outcome as +1 or -1 into
        learning_state.update(), and LearningState.update() asserts
        outcome in (+1, -1). For q_window=400, binomial sampling error is
        on the order of ~2-3 percentage points depending on true accuracy.
        """
        if not history:
            return {"alpha": 0.0, "q": 0.0, "V": 0.0, "n": 0}

        recent = history[-window:]
        alphas = [wu.alpha_effective for wu in recent if hasattr(wu, "alpha_effective")]
        q_recent = history[-q_window:]

        alpha = float(np.mean(alphas)) if alphas else 0.0
        if q_recent:
            q = float(sum(1 for wu in q_recent if wu.outcome == 1) / len(q_recent))
        else:
            q = 0.0

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

    @staticmethod
    async def _apply_soc_conservation_components(comps: dict, neo4j_service: Any = None) -> dict:
        """Replace legacy components with SOC verified coverage statistics.

        SOC-3/#132 defines alpha as cumulative verified category coverage, not
        override rate and not the GAE learning-rate trace. V and q are computed
        from verified decisions only so preview/ghost decisions cannot inflate
        the conservation signal.
        """
        updated = dict(comps)
        updated["alpha_source"] = "soc_coverage_unavailable"

        stats = await _query_soc_verified_conservation_stats(neo4j_service)

        if stats is None:
            # Legacy alpha_effective is a learning-rate trace. Treat missing
            # verified coverage evidence conservatively while retaining legacy q
            # as diagnostic verified accuracy.
            updated["alpha"] = 0.0
            updated["categories_total"] = _soc_categories_total()
            updated["categories_with_data"] = None
            updated["verified_decisions"] = None
            updated["correct_verified_decisions"] = None
            updated["override_rate"] = None
            updated["complacency_advisory"] = False
            return updated

        categories_total = int(stats.get("categories_total") or _soc_categories_total())
        categories_with_data = int(stats.get("categories_with_data") or 0)
        verified = int(stats.get("verified_decisions") or 0)
        correct = int(stats.get("correct_verified_decisions") or 0)
        overrides = int(stats.get("overrides") or 0)

        alpha = (
            max(0.0, min(1.0, categories_with_data / categories_total))
            if categories_total > 0
            else 0.0
        )
        q = max(0.0, min(1.0, correct / verified)) if verified > 0 else 0.0
        override_rate = max(0.0, min(1.0, overrides / verified)) if verified > 0 else 0.0

        updated["alpha"] = alpha
        updated["q"] = q
        updated["V"] = float(verified)
        updated["n"] = verified
        updated["categories_total"] = categories_total
        updated["categories_with_data"] = categories_with_data
        updated["verified_decisions"] = verified
        updated["correct_verified_decisions"] = correct
        updated["override_rate"] = override_rate
        updated["complacency_advisory"] = verified >= 200 and override_rate < 0.02
        updated["alpha_source"] = "soc_verified_category_coverage"
        return updated

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

        # WeightUpdate history only has alpha_effective, a legacy learning-rate
        # trace. Without historical override-rate evidence, relative floors are
        # unavailable rather than learning-rate-derived.
        return 0.0, 0.0

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
            pre_activation    : bool
            learning_enabled  : bool | None
            health_source     : str
            status_reason     : str | None
        """
        state          = get_learning_state()
        history        = getattr(state, "history", [])
        history        = history or []   # guard: attribute may exist but be explicitly None
        decision_count = getattr(state, "decision_count", len(history))

        comps          = LearningHealthMonitor._extract_components(history)
        comps          = await LearningHealthMonitor._apply_soc_conservation_components(
            comps, neo4j_service
        )
        alpha, q, V    = comps["alpha"], comps["q"], comps["V"]
        if alpha <= 0 or V <= 0:
            theta_min = CONSERVATIVE_THETA_MIN
        else:
            try:
                theta_min = compute_theta_min(alpha, V)
            except ValueError:
                theta_min = derive_theta_min()
        cc             = check_conservation(alpha, q, V, theta_min)
        conservation_passed = bool(cc.passed and alpha > 0 and V > 0)
        signal         = LearningHealthMonitor._compute_signal(alpha, q, V)

        learning_enabled = _is_learning_enabled()

        # ── Pre-activation / frozen learning phase ───────────────────────────
        if (
            learning_enabled is False
            and decision_count >= CALIBRATION_DECISIONS
            and int(comps.get("n", 0) or 0) == 0
            and signal == 0.0
        ):
            return {
                "status":            "CALIBRATING",
                "signal":            round(signal, 6),
                "theta_min":         round(theta_min, 6),
                "conservation":      {
                    "passed":   True,
                    "status":   "CALIBRATING",
                    "headroom": 0.0,
                },
                "components":        _round_comps(comps),
                "baseline":          None,
                "baseline_std":      None,
                "red_days":          0,
                "auto_pause_active": False,
                "interpretation":    (
                    f"Pre-activation -- learning is disabled with {decision_count} "
                    "decisions recorded but no live learning history. Conservation "
                    "cannot be evaluated until learning is enabled."
                ),
                "pre_activation":    True,
                "learning_enabled":  False,
                "health_source":     "learning_health_pre_activation",
                "status_reason":     "learning_disabled_no_live_history",
            }

        # ── Calibration phase ────────────────────────────────────────────────
        if decision_count < CALIBRATION_DECISIONS:
            return {
                "status":            "CALIBRATING",
                "signal":            round(signal, 6),
                "theta_min":         round(theta_min, 6),
                "conservation":      {
                      "passed":   conservation_passed,
                    "status":   cc.status,
                    "headroom": round(cc.headroom, 4),
                },
                "components":        _round_comps(comps),
                "baseline":          None,
                "baseline_std":      None,
                "red_days":          0,
                "auto_pause_active": False,
                "interpretation":    (
                    f"Calibrating -- {decision_count} decisions recorded "
                    f"(target: {CALIBRATION_DECISIONS} / ~{CALIBRATION_DAYS} days)"
                ),
                "pre_activation":    False,
                "learning_enabled":  learning_enabled,
                "health_source":     "learning_health",
                "status_reason":     None,
            }

        # ── Baseline from calibration window ─────────────────────────────────
        baseline, baseline_std = LearningHealthMonitor._build_calibration_baseline(history)

        # ── Two-threshold status ──────────────────────────────────────────────
        amber_floor = baseline - LearningHealthMonitor.AMBER_SIGMA * baseline_std
        red_floor   = baseline - LearningHealthMonitor.RED_SIGMA   * baseline_std

        if not conservation_passed or signal < red_floor:
            status = "RED"
        elif signal < amber_floor:
            status = "AMBER"
        else:
            status = "GREEN"

        # ── RED-day count (HealthLog nodes or approximation) ─────────────────
        red_days          = await LearningHealthMonitor._count_red_days(neo4j_service)
        auto_pause_active = red_days >= AUTO_PAUSE_RED_DAYS

        result = {
            "status":            status,
            "signal":            round(signal, 6),
            "theta_min":         round(theta_min, 6),
            "conservation":      {
                  "passed":   conservation_passed,
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
            "pre_activation":    False,
            "learning_enabled":  learning_enabled,
            "health_source":     "learning_health",
            "status_reason":     None,
            "complacency_advisory": bool(comps.get("complacency_advisory", False)),
        }
        if result["complacency_advisory"]:
            log.info(
                "[HEALTH] SOC complacency advisory: override_rate=%.4f over %d verified decisions",
                float(comps.get("override_rate") or 0.0),
                int(comps.get("verified_decisions") or 0),
            )
        await _persist_l5_conservation_state(result)
        return result

    # -------------------------------------------------------------------------
    # RED-day counting
    # -------------------------------------------------------------------------

    @staticmethod
    async def _count_red_days(neo4j_service: Any) -> int:
        """
        Count distinct RED-status days in the 30-day lookback window.

        Cumulative, not consecutive -- matches the rolling-aggregate semantics of
        the conservation law (alpha, q, V use rolling windows, not consecutive runs).
        Returns 0 if neo4j_service is None or the query fails.
        """
        if neo4j_service is None:
            return 0
        try:
            # Inline the cutoff as a literal integer — $param is forbidden in AGE
            # (AGEClient does naive string substitution, not driver parameterization).
            # Integer inlining is safe here: value is computed, never from user input.
            _cutoff = int((datetime.utcnow().timestamp() - AUTO_PAUSE_LOOKBACK_DAYS * 86400) * 1000)
            rows = await neo4j_service.run_query(
                f"""
                MATCH (h:HealthLog)
                WHERE h.status = 'RED'
                  AND h.timestamp_epoch >= {_cutoff}
                RETURN count(DISTINCT (h.timestamp_epoch / 86400000)) AS red_days
                """
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
            return "Conservation law satisfied -- learning system is healthy"
        if status == "AMBER":
            return (
                f"Signal degraded below baseline-{LearningHealthMonitor.AMBER_SIGMA}sigma "
                f"(signal={signal:.4f}) -- monitor closely"
            )
        if status == "RED":
            if red_days >= AUTO_PAUSE_RED_DAYS:
                return (
                    f"AUTO-PAUSE active: {red_days} RED days >= {AUTO_PAUSE_RED_DAYS} threshold "
                    "-- learning updates suspended"
                )
            return (
                f"Conservation violation (signal={signal:.4f} < theta_min={theta_min:.4f}) "
                f"-- {red_days} RED day(s) accumulated"
            )
        return f"Status: {status}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _round_comps(comps: dict) -> dict:
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in comps.items()}


def _soc_categories_total() -> int:
    try:
        from app.domains.soc.config import N_CATEGORIES

        return int(N_CATEGORIES)
    except Exception:
          return 6


def _soc_category_names() -> set[str]:
    try:
        from app.domains.soc.config import SOC_CATEGORIES

        return {str(category) for category in SOC_CATEGORIES}
    except Exception:
        return {
            "credential_access",
            "malware_execution",
            "lateral_movement",
            "data_exfiltration",
            "insider_threat",
            "cloud_infrastructure",
        }


def _coerce_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


async def _query_soc_verified_conservation_stats(neo4j_service: Any = None) -> dict | None:
    if neo4j_service is None or not hasattr(neo4j_service, "run_query"):
        return None

    valid_categories = _soc_category_names()
    category_literals = ", ".join(
        "'" + category.replace("\\", "\\\\").replace("'", "\\'") + "'"
        for category in sorted(valid_categories)
    )

    try:
        _soc_where = soc_decision_where()
        rows = await neo4j_service.run_query(
            f"""
            MATCH (d:Decision)
            WHERE {_soc_where}
              AND d.verified_at_epoch IS NOT NULL
              AND (d.status IS NOT NULL OR d.outcome IS NOT NULL)
              AND d.category IN [{category_literals}]
            RETURN d.category AS category,
                   count(d) AS verified,
                   sum(CASE WHEN d.correct = true OR d.outcome = 'correct' THEN 1 ELSE 0 END) AS correct,
                   sum(CASE WHEN d.was_override = true THEN 1 ELSE 0 END) AS overrides
            """
        )
    except Exception as exc:
        log.debug("[HEALTH] SOC verified conservation query failed: %s", exc)
        return None

    categories_with_data: set[str] = set()
    verified = 0
    correct = 0
    overrides = 0
    for row in rows or []:
        category = row.get("category")
        if category not in valid_categories:
            continue
        row_verified = _coerce_int(row.get("verified"))
        if row_verified <= 0:
            continue
        categories_with_data.add(str(category))
        verified += row_verified
        correct += _coerce_int(row.get("correct"))
        overrides += _coerce_int(row.get("overrides"))

    return {
        "categories_total": _soc_categories_total(),
        "categories_with_data": len(categories_with_data),
        "verified_decisions": verified,
        "correct_verified_decisions": correct,
        "overrides": overrides,
    }


def _resolve_categories_with_data(health: dict, categories_total: int) -> int | None:
    components = health.get("components") or {}
    value = health.get("categories_with_data", components.get("categories_with_data"))
    if value is None:
        return None

    try:
        categories_with_data = int(value)
    except (TypeError, ValueError):
        return None

    if categories_with_data < 0 or categories_with_data > categories_total:
        return None
    return categories_with_data


async def _persist_l5_conservation_state(health: dict) -> None:
    """Persist SOC conservation state when an optional L5 store is available."""
    status = str(health.get("status") or "").upper()
    if status not in {"GREEN", "AMBER", "RED"}:
        return

    categories_total = _soc_categories_total()
    categories_with_data = _resolve_categories_with_data(health, categories_total)
    if categories_with_data is None:
        log.debug(
            "[HEALTH][L5] Conservation state skipped for soc: "
            "categories_with_data unavailable"
        )
        return

    store = get_learning_store()
    if store is None:
        return

    async with _L5_CONSERVATION_STORE_LOCK:
        try:
            old_state = store.get_conservation_state("soc")
        except Exception as exc:
            log.warning(
                "[HEALTH][L5] Conservation state read failed; skipping persistence "
                "(domain=soc, status=%s, error_type=%s)",
                status,
                type(exc).__name__,
            )
            return

        old_status = None
        if isinstance(old_state, dict):
            candidate = old_state.get("status")
            old_status = str(candidate).upper() if candidate is not None else None

        components = health.get("components") or {}
        baseline_product = float(health.get("baseline") or 0.0)
        baseline_std = float(health.get("baseline_std") or 0.0)
        relative_threshold = baseline_product - (
            LearningHealthMonitor.AMBER_SIGMA * baseline_std
        )

        try:
            store.update_conservation_state(
                domain="soc",
                status=status,
                alpha=float(components.get("alpha") or 0.0),
                q=float(components.get("q") or 0.0),
                V=int(float(components.get("V") or 0.0)),
                theta_min=float(health["theta_min"]),
                product=float(health["signal"]),
                categories_total=categories_total,
                categories_with_data=categories_with_data,
                baseline_product=baseline_product,
                relative_threshold=relative_threshold,
                  complacency_flag="true" if health.get("complacency_advisory") else "false",
                caused_by_decision_id=None,
                old_status=old_status,
            )
        except Exception as exc:
            log.warning(
                "[HEALTH][L5] Conservation state update failed "
                "(domain=soc, status=%s, error_type=%s)",
                status,
                type(exc).__name__,
            )


# ---------------------------------------------------------------------------
# Block 9.2 — Spike detector (deployment-specific σ)
# ---------------------------------------------------------------------------

_VOLUME_WINDOW_DAYS = 30


async def compute_volume_baseline(neo4j_client: Any) -> dict:
    """
    Compute rolling 30-day alert volume baseline from Alert nodes.

    Groups alerts into daily buckets using timestamp_epoch.
    spike_sigma comes from GateConfig -- 5.0 before N_min, 3.0 after.

    Returns
    -------
    dict:
      daily_mean      : float  -- mean daily alert count over window
      daily_std       : float  -- std of daily counts (floor=1.0)
      spike_threshold : float  -- mean + spike_sigma * std
      spike_sigma     : float  -- 5.0 (conservative) or 3.0 (calibrated)
      window_days     : int    -- 30
      data_points     : int    -- number of days with at least one alert
    """
    import time as _time
    from app.domains.soc.config import GateConfig

    now_epoch   = int(_time.time() * 1000)
    cutoff_epoch = now_epoch - _VOLUME_WINDOW_DAYS * 86_400_000

    daily_counts: list[float] = []
    try:
        rows = await neo4j_client.run_query(
            f"""
            MATCH (a:Alert)
            WHERE a.timestamp_epoch > {cutoff_epoch}
            WITH a.timestamp_epoch / 86400000 AS day_bucket, count(a) AS daily_count
            RETURN day_bucket, daily_count
            ORDER BY day_bucket
            """
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
    today_count  : int -- number of alerts received so far today

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
# Block 9.3 — Category freeze (volume spikes only)
# ---------------------------------------------------------------------------

_FREEZE_MULTIPLIER = 2.0   # freeze when today_share > 2x baseline_share


async def compute_category_baseline(neo4j_client: Any) -> dict[str, float]:
    """
    Compute 30-day baseline category distribution of Alert nodes.

    Returns fractional share per category (sums to ~=1.0).
    Returns {} when no alert data is available.

    Example: {"credential_access": 0.35, "lateral_movement": 0.15, ...}
    """
    import time as _time
    cutoff_epoch = int(_time.time() * 1000) - _VOLUME_WINDOW_DAYS * 86_400_000

    try:
        rows = await neo4j_client.run_query(
            f"""
            MATCH (a:Alert)
            WHERE a.timestamp_epoch > {cutoff_epoch} AND a.category IS NOT NULL
            RETURN a.category AS category, count(a) AS cnt
            """
        )
    except Exception as exc:
        log.warning("[D2] compute_category_baseline query failed: %s", exc)
        return {}

    total = sum(int(r.get("cnt") or 0) for r in rows)
    if total == 0:
        return {}

    return {
        r["category"]: round(int(r.get("cnt") or 0) / total, 6)
        for r in rows
        if r.get("category")
    }


async def detect_frozen_categories(
    neo4j_client: Any,
    today_category_counts: dict,
) -> list:
    """
    Return list of category names to freeze during the current spike.

    Only meaningful when a volume spike is active (D3 coupled constraint).
    Returns [] immediately if no spike is active -- do not freeze on other signals.

    A category is frozen when its share of today's alerts exceeds
    _FREEZE_MULTIPLIER (2x) its 30-day baseline share.

    Parameters
    ----------
    neo4j_client          : async Neo4j client
    today_category_counts : dict[str, int] -- alert counts by category for today

    Returns
    -------
    list[str] of frozen category names (may be empty)
    """
    from app.services.gae_state import is_volume_spike_active

    if not is_volume_spike_active():
        return []

    today_total = sum(today_category_counts.values())
    if today_total == 0:
        return []

    baseline = await compute_category_baseline(neo4j_client)

    frozen: list[str] = []
    for category, count in today_category_counts.items():
        today_share    = count / today_total
        baseline_share = baseline.get(category, 0.0)

        # No baseline data for this category — cannot compare, skip freeze
        if baseline_share <= 0.0:
            continue

        if today_share > _FREEZE_MULTIPLIER * baseline_share:
            log.warning(
                "[D2] Freezing category '%s': today_share=%.3f > %.1f x baseline=%.3f",
                category, today_share, _FREEZE_MULTIPLIER, baseline_share,
            )
            frozen.append(category)

    return frozen


# ---------------------------------------------------------------------------
# Block 9.1 — Per-analyst precision computation
# ---------------------------------------------------------------------------

_MIN_ANALYST_DECISIONS = 10   # exclude analysts with fewer decisions
_MIN_ANALYSTS_REQUIRED = 2    # return {} if fewer than 2 analysts qualify


async def compute_analyst_precision(neo4j_client: Any) -> dict[str, float]:
    """
    Compute per-analyst override precision from Decision nodes.

    Only counts decisions with a known source_id and verified_by analyst.
    Excludes analysts with fewer than _MIN_ANALYST_DECISIONS (10) decisions.
    Returns {} if fewer than _MIN_ANALYSTS_REQUIRED (2) analysts qualify.

    Returns
    -------
    dict mapping analyst name -> precision (correct / total), e.g.
      {"analyst_a": 0.82, "analyst_b": 0.71}
    """
    try:
        _soc_where = soc_decision_where()
        rows = await neo4j_client.run_query(
            f"""
            MATCH (d:Decision)
            WHERE {_soc_where}
              AND d.source_id IS NOT NULL AND d.verified_by IS NOT NULL
            WITH d.verified_by AS analyst,
                 count(d) AS total,
                 sum(CASE WHEN d.correct = true THEN 1 ELSE 0 END) AS correct
            WHERE total >= {_MIN_ANALYST_DECISIONS}
            RETURN analyst, toFloat(correct) / toFloat(total) AS precision
            """
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

    Condition 1 -- Coverage: verified_decisions / total_decisions >= 0.20
    Condition 2 -- Drift: last-7d rate >= prior-7d rate * 0.80
    Condition 3 -- Conservation: GREEN or CALIBRATING; UNKNOWN is cautious

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
            f"MATCH (d:Decision) WHERE {soc_decision_where()} "
            "RETURN count(d) AS total"
        )
        total_decisions = int((rows[0].get("total") or 0) if rows else 0)
    except Exception as exc:
        log.debug("[VERIF-HEALTH] total_decisions query failed: %s", exc)

    try:
        rows = await neo4j_client.run_query(
            f"MATCH (d:Decision) WHERE {soc_decision_where()} "
            "AND d.outcome IS NOT NULL AND d.verified_at_epoch IS NOT NULL "
            "RETURN count(d) AS verified"
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
        _soc_where = soc_decision_where()
        rows = await neo4j_client.run_query(
            f"""
            MATCH (d:Decision)
            WHERE {_soc_where}
              AND d.timestamp_epoch >= {last_7d_start} AND d.timestamp_epoch < {now_ms}
            RETURN
              count(d) AS total,
              count(CASE WHEN d.verified_at_epoch IS NOT NULL THEN 1 END) AS verified
            """
        )
        if rows:
            last_7d_total    = int(rows[0].get("total")    or 0)
            last_7d_verified = int(rows[0].get("verified") or 0)
    except Exception as exc:
        log.debug("[VERIF-HEALTH] last_7d query failed: %s", exc)

    try:
        _soc_where = soc_decision_where()
        rows = await neo4j_client.run_query(
            f"""
            MATCH (d:Decision)
            WHERE {_soc_where}
              AND d.timestamp_epoch >= {prior_7d_start} AND d.timestamp_epoch < {last_7d_start}
            RETURN
              count(d) AS total,
              count(CASE WHEN d.verified_at_epoch IS NOT NULL THEN 1 END) AS verified
            """
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

    conservation_healthy = conservation_status in ("GREEN", "CALIBRATING")

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
