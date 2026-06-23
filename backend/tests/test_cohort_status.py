from __future__ import annotations

import inspect
import json

import pytest

from app.services.cohort_status import (
    CohortStatusService,
    VALID_STATES,
    compute_state,
    evaluate_v7_gate,
)


def test_t1_sample_only_no_lift() -> None:
    status = CohortStatusService(decision_records=_records("sample", 10, 10)).get_status()

    assert status["real"]["magnitude"] is None
    assert status["real"]["status"] == "pending"
    assert status["state"] != "MEASURED"
    assert status["state"] == "INSTRUMENT_VALIDATED"


def test_t2_lift_query_filters_provenance() -> None:
    source = inspect.getsource(CohortStatusService._compute_real_lift)

    assert "provenance" in source
    assert "sample" in source
    assert "oracle" in source
    assert "real" in source


def test_t3_one_real_below_k() -> None:
    status = CohortStatusService(decision_records=_records("real", 1, 0)).get_status()

    assert status["state"] == "ACCUMULATING"
    assert status["real"]["magnitude"] is None
    assert status["real"]["treatment_n"] == 1
    assert status["real"]["control_n"] == 0


def test_t4_real_above_k_both_arms() -> None:
    records = _records("real", 50, 50, treatment_positive=40, control_positive=20)
    records.extend(_records("sample", 500, 500, treatment_positive=0, control_positive=500))

    status = CohortStatusService(decision_records=records).get_status()

    assert status["state"] == "MEASURED"
    assert status["real"]["magnitude"] is not None
    assert status["real"]["magnitude"] == pytest.approx(0.4)
    assert status["real"]["treatment_n"] == 50
    assert status["real"]["control_n"] == 50


def test_t5_instrument_present_at_every_state(tmp_path) -> None:
    artifact = tmp_path / "soc_oracle_plumb_results.json"
    artifact.write_text(
        json.dumps({"experiments": [{"name": "known_lift", "expected_lift": 0.1, "measured_lift": 0.1, "passed": True}]}),
        encoding="utf-8",
    )
    cases = [
        _records("sample", 5, 5),
        _records("real", 1, 0),
        _records("real", 50, 50),
    ]

    for records in cases:
        status = CohortStatusService(decision_records=records, oracle_artifact_path=artifact).get_status()
        assert "validated" in status["instrument"]
        assert status["instrument"]["validated"] is True
        assert status["instrument"]["provenance"] == "oracle"


def test_structure_never_moves_state() -> None:
    status = CohortStatusService(decision_records=_records("sample", 500, 500)).get_status()

    assert status["state"] == "INSTRUMENT_VALIDATED"
    assert status["structure"]["present"] is True
    assert status["real"]["magnitude"] is None


def test_v7_gate_abstains_below_threshold() -> None:
    status = CohortStatusService(decision_records=_records("real", 1, 0)).get_status()

    result = evaluate_v7_gate(status)

    assert result["status"] == "awaiting_real_cohorts"
    assert result["status"] not in {"conditions_met", "conditions_not_met"}
    assert result["magnitude"] is None


def test_v7_gate_rejects_non_real() -> None:
    status = {
        "real": {
            "treatment_n": 50,
            "control_n": 50,
            "threshold_k": 50,
            "magnitude": 0.1,
            "records": [_record("sample", "treatment", True)],
        }
    }

    with pytest.raises(ValueError):
        evaluate_v7_gate(status)


def test_oracle_artifact_missing_graceful(tmp_path) -> None:
    missing = tmp_path / "missing_oracle_results.json"

    status = CohortStatusService(decision_records=[], oracle_artifact_path=missing).get_status()

    assert status["instrument"]["validated"] is False
    assert status["instrument"]["experiments"] == []
    assert status["state"] == "INSTRUMENT_VALIDATED"


def test_lift_null_at_instrument_validated() -> None:
    status = CohortStatusService(decision_records=[]).get_status()

    assert status["state"] == "INSTRUMENT_VALIDATED"
    assert status["real"]["magnitude"] is None


def test_lift_null_at_accumulating() -> None:
    status = CohortStatusService(decision_records=_records("real", 49, 50)).get_status()

    assert status["state"] == "ACCUMULATING"
    assert status["real"]["magnitude"] is None


def test_state_enum_values() -> None:
    assert VALID_STATES == {"INSTRUMENT_VALIDATED", "ACCUMULATING", "MEASURED"}
    assert compute_state(0, 0, 50) in VALID_STATES
    assert compute_state(1, 0, 50) in VALID_STATES
    assert compute_state(50, 50, 50) in VALID_STATES


def _records(
    provenance: str,
    treatment_n: int,
    control_n: int,
    *,
    treatment_positive: int | None = None,
    control_positive: int | None = None,
) -> list[dict]:
    treatment_positive = treatment_n if treatment_positive is None else treatment_positive
    control_positive = control_n if control_positive is None else control_positive
    records = [
        _record(provenance, "treatment", index < treatment_positive)
        for index in range(treatment_n)
    ]
    records.extend(
        _record(provenance, "control", index < control_positive)
        for index in range(control_n)
    )
    return records


def _record(provenance: str, holdout_group: str, positive: bool) -> dict:
    return {
        "decision_id": f"{provenance}-{holdout_group}-{positive}",
        "provenance": provenance,
        "holdout_group": holdout_group,
        "analyst_action": "escalate_tier2" if positive else "dismiss",
        "campaign_id": "campaign-1",
    }
