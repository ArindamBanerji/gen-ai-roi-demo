"""Campaign cohort day-zero state machine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from copilot_sdk.substantiation.cohort_day_zero import (
    STATES,
    BaseCohortDayZeroState,
    compute_state,
    evaluate_v7_gate as _sdk_evaluate_v7_gate,
)

VALID_STATES = frozenset(STATES)
REAL_PROVENANCE = "real"
SAMPLE_PROVENANCE = "sample"
ORACLE_PROVENANCE = "oracle"
TREATMENT_GROUPS = frozenset({"treatment", "shown", "visible", "not_suppressed"})
CONTROL_GROUPS = frozenset({"control", "holdout", "suppressed"})
POSITIVE_ACTIONS = frozenset({"escalate", "escalate_tier2", "investigate", "refer_to_analyst"})


def evaluate_v7_gate(cohort_status: dict[str, Any]) -> dict[str, Any]:
    """Compatibility wrapper around the SDK v7.0 gate."""

    real = cohort_status["real"]
    records = cohort_status.get("records") or real.get("records") or []
    threshold_k = int(cohort_status.get("threshold_k") or real.get("threshold_k") or 50)
    gate_input = dict(real)
    gate_input["provenance"] = REAL_PROVENANCE
    gate_input["magnitude"] = real.get("magnitude")
    if records:
        gate_input["records"] = records
    return _sdk_evaluate_v7_gate(gate_input, threshold_k)


class CohortStatusService(BaseCohortDayZeroState):
    """Campaign cohort day-zero state machine.

    State transitions are driven only by real decision cohorts. Sample
    structure and oracle instrument validation are displayed separately.
    """

    THRESHOLD_K = 50

    def __init__(
        self,
        graph_store: Any = None,
        oracle_artifact_path: str | Path | None = None,
        decision_records: list[dict[str, Any]] | None = None,
    ) -> None:
        self._graph_store = graph_store
        self._oracle_artifact_path = (
            Path(oracle_artifact_path)
            if oracle_artifact_path is not None
            else _default_oracle_artifact_path()
        )
        self._decision_records = list(decision_records) if decision_records is not None else None

    def _load_instrument(self) -> dict[str, Any]:
        """Load oracle self-test results. T-O provenance."""
        path = self._oracle_artifact_path
        if path is None or not path.exists():
            return {
                "validated": False,
                "provenance": ORACLE_PROVENANCE,
                "source_artifact": str(path) if path is not None else "",
                "experiments": [],
            }
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {
                "validated": False,
                "provenance": ORACLE_PROVENANCE,
                "source_artifact": str(path),
                "experiments": [],
            }

        experiments = _coerce_experiments(payload)
        return {
            "validated": bool(experiments) and all(bool(exp["pass"]) for exp in experiments),
            "provenance": ORACLE_PROVENANCE,
            "source_artifact": str(path),
            "experiments": experiments,
        }

    def _count_real_cohorts(self) -> dict[str, Any]:
        """Count decisions WHERE provenance=='real' grouped by holdout."""
        treatment, control = _count_arms(self._real_decisions())
        return {
            "treatment_n": treatment,
            "control_n": control,
        }

    def _count_structure_cohorts(self) -> dict[str, Any]:
        """Count decisions WHERE provenance=='sample' for structure display."""
        treatment, control = _count_arms(self._sample_decisions())
        present = treatment + control > 0
        return {
            "present": present,
            "treatment_n": treatment,
            "control_n": control,
            "split_balanced": _split_balanced(treatment, control) if present else None,
            "join_ok": present if present else None,
            "provenance": SAMPLE_PROVENANCE,
        }

    def _compute_real_lift(self) -> float:
        """Compute lift from provenance=='real' decisions ONLY.

        F-26: sample and oracle records raise instead of entering this metric.
        """
        records = self._real_decisions()
        for record in records:
            provenance = _provenance(record)
            if provenance == SAMPLE_PROVENANCE or provenance == ORACLE_PROVENANCE or provenance != REAL_PROVENANCE:
                raise ValueError("Campaign magnitude must use provenance=='real' records only")
        treatment = [record for record in records if _arm(record) == "treatment"]
        control = [record for record in records if _arm(record) == "control"]
        if not treatment or not control:
            raise ValueError("Campaign magnitude requires treatment and control real cohorts")
        return round(_positive_rate(treatment) - _positive_rate(control), 6)

    def _real_decisions(self) -> list[dict[str, Any]]:
        return [
            record
            for record in self._read_decisions()
            if _provenance(record) == REAL_PROVENANCE and _arm(record) in {"treatment", "control"}
        ]

    def _sample_decisions(self) -> list[dict[str, Any]]:
        return [
            record
            for record in self._read_decisions()
            if _provenance(record) == SAMPLE_PROVENANCE and _arm(record) in {"treatment", "control"}
        ]

    def _read_decisions(self) -> list[dict[str, Any]]:
        if self._decision_records is not None:
            return [dict(record) for record in self._decision_records if isinstance(record, dict)]
        if self._graph_store is None:
            return []
        if isinstance(self._graph_store, list):
            return [dict(record) for record in self._graph_store if isinstance(record, dict)]

        reader = getattr(self._graph_store, "cohort_decisions", None)
        if callable(reader):
            try:
                records = reader()
            except Exception:
                return []
            return [dict(record) for record in records if isinstance(record, dict)]
        return []


def _default_oracle_artifact_path() -> Path:
    return Path(__file__).resolve().parents[2] / "soc_oracle_plumb_results.json"


def _coerce_experiments(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        raw_experiments = payload.get("experiments")
        if raw_experiments is None:
            raw_experiments = payload.get("results")
        if raw_experiments is None:
            raw_experiments = payload
    else:
        raw_experiments = payload

    if isinstance(raw_experiments, dict):
        items = [
            {"name": str(name), **(value if isinstance(value, dict) else {})}
            for name, value in raw_experiments.items()
        ]
    elif isinstance(raw_experiments, list):
        items = [item for item in raw_experiments if isinstance(item, dict)]
    else:
        items = []

    experiments: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        name = str(item.get("name") or item.get("experiment") or f"experiment_{index + 1}")
        experiments.append({
            "name": name,
            "injected_lift": _float_or_zero(item.get("injected_lift", item.get("expected_lift", 0.0))),
            "recovered_lift": _float_or_zero(item.get("recovered_lift", item.get("measured_lift", 0.0))),
            "pass": bool(item.get("pass", item.get("passed", False))),
        })
    return experiments


def _count_arms(records: list[dict[str, Any]]) -> tuple[int, int]:
    treatment = sum(1 for record in records if _arm(record) == "treatment")
    control = sum(1 for record in records if _arm(record) == "control")
    return treatment, control


def _arm(record: dict[str, Any]) -> str | None:
    value = str(record.get("holdout_group") or record.get("cohort") or "").strip().lower()
    if value in TREATMENT_GROUPS:
        return "treatment"
    if value in CONTROL_GROUPS:
        return "control"
    return None


def _provenance(record: dict[str, Any]) -> str:
    return str(record.get("provenance") or record.get("provenance_tier") or "").strip().lower()


def _positive_rate(records: list[dict[str, Any]]) -> float:
    return sum(1 for record in records if _positive(record)) / len(records)


def _positive(record: dict[str, Any]) -> bool:
    action = str(record.get("analyst_action") or record.get("action") or "").strip().lower()
    if action in POSITIVE_ACTIONS:
        return True
    if action in {"dismiss", "suppress", "monitor", "ignore"}:
        return False
    if "correct" in record:
        return bool(record.get("correct"))
    try:
        return float(record.get("quality_signal", 0.0)) > 0.0
    except (TypeError, ValueError):
        return False


def _split_balanced(treatment: int, control: int) -> bool:
    total = treatment + control
    if total == 0:
        return False
    return abs(treatment - control) <= max(1, int(total * 0.1))


def _float_or_zero(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
