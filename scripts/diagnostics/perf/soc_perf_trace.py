from __future__ import annotations

import contextlib
import hashlib
import json
import os
import random
import time
import uuid
from pathlib import Path
from typing import Any, Iterator


FALSE_VALUES = {"", "0", "false", "no", "off"}
SECRET_KEYS = {"dsn", "graph_dsn", "password", "token", "secret", "authorization"}


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in FALSE_VALUES


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_output() -> Path:
    return _repo_root() / "scratch" / "temp" / "soc_perf_trace.jsonl"


def _resolve_output_path(value: str | None) -> Path:
    if not value:
        return _default_output()
    path = Path(value)
    if path.is_absolute():
        return path
    return _repo_root() / path


def _hash_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def _safe_value(key: str, value: Any, *, include_cypher: bool, include_factor_vector: bool) -> Any:
    lowered = key.lower()
    if any(secret in lowered for secret in SECRET_KEYS):
        return "<redacted>"
    if "cypher" in lowered:
        if include_cypher:
            return str(value)
        return _hash_text(str(value))
    if "factor_vector" in lowered or lowered in {"f", "vector"}:
        if include_factor_vector:
            return value
        try:
            return {"redacted": True, "len": len(value)}
        except Exception:
            return "<redacted>"
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_safe_value(key, item, include_cypher=include_cypher, include_factor_vector=include_factor_vector) for item in value[:20]]
    if isinstance(value, dict):
        return {
            str(k): _safe_value(str(k), v, include_cypher=include_cypher, include_factor_vector=include_factor_vector)
            for k, v in list(value.items())[:50]
        }
    return str(value)


class PerfTracer:
    def __init__(self) -> None:
        self.enabled = _bool_env("SOC_PERF_TRACE_ENABLED", False)
        self.level = os.getenv("SOC_PERF_TRACE_LEVEL", "summary").strip().lower() or "summary"
        self.output = _resolve_output_path(os.getenv("SOC_PERF_TRACE_OUTPUT"))
        self.slow_ms = _float_env("SOC_PERF_TRACE_SLOW_MS", 500.0)
        self.include_cypher = _bool_env("SOC_PERF_TRACE_INCLUDE_CYPHER", False)
        self.include_factor_vector = _bool_env("SOC_PERF_TRACE_INCLUDE_FACTOR_VECTOR", False)
        self.sample_rate = min(1.0, max(0.0, _float_env("SOC_PERF_TRACE_SAMPLE_RATE", 1.0)))
        self.max_events = max(0, _int_env("SOC_PERF_TRACE_MAX_EVENTS_PER_REQUEST", 500))
        self.flush_every = max(1, _int_env("SOC_PERF_TRACE_FLUSH_EVERY_N", 25))
        self.trace_id = str(uuid.uuid4())
        self._events_written = 0
        self._events_since_flush = 0

    def should_trace(self) -> bool:
        if not self.enabled:
            return False
        if self.max_events and self._events_written >= self.max_events:
            return False
        return random.random() <= self.sample_rate

    def sanitize_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            str(k): _safe_value(
                str(k),
                v,
                include_cypher=self.include_cypher,
                include_factor_vector=self.include_factor_vector,
            )
            for k, v in metadata.items()
        }

    def emit_best_effort(self, event: dict[str, Any]) -> None:
        if not self.enabled:
            return
        try:
            self.output.parent.mkdir(parents=True, exist_ok=True)
            with self.output.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, default=str, separators=(",", ":")) + "\n")
                self._events_since_flush += 1
                if self._events_since_flush >= self.flush_every:
                    handle.flush()
                    self._events_since_flush = 0
            self._events_written += 1
        except Exception:
            return

    @contextlib.contextmanager
    def phase(
        self,
        phase: str,
        *,
        route: str | None = None,
        alert_id: str | None = None,
        decision_id: str | None = None,
        attempt_index: int | None = None,
        graph_name: str | None = None,
        query_label: str | None = None,
        **metadata: Any,
    ) -> Iterator[None]:
        sampled = self.should_trace()
        if not sampled:
            yield
            return
        started_perf = time.perf_counter()
        started_epoch = time.time()
        status = "ok"
        exception_type: str | None = None
        try:
            yield
        except Exception as exc:
            status = "error"
            exception_type = type(exc).__name__
            raise
        finally:
            duration_ms = round((time.perf_counter() - started_perf) * 1000.0, 3)
            if self.level == "summary" and duration_ms < self.slow_ms and phase not in {
                "total_attempt",
                "analyze_http_request",
                "outcome_http_request",
                "report_write",
            }:
                return
            event = {
                "event_type": "phase_timing",
                "trace_id": self.trace_id,
                "route": route,
                "phase": phase,
                "query_label": query_label,
                "started_epoch": started_epoch,
                "duration_ms": duration_ms,
                "status": status,
                "exception_type": exception_type,
                "graph_name": graph_name,
                "alert_id": alert_id,
                "decision_id": decision_id,
                "attempt_index": attempt_index,
                "sampled": sampled,
                "metadata": self.sanitize_metadata(metadata),
            }
            self.emit_best_effort(event)


_TRACER: PerfTracer | None = None


def get_tracer() -> PerfTracer:
    global _TRACER
    if _TRACER is None:
        _TRACER = PerfTracer()
    return _TRACER


def current_output_path() -> Path:
    return get_tracer().output
