from __future__ import annotations

import pytest

from app.domains.soc.constants import GAMMA_THEOREM
from app.services.cohort_status import evaluate_v7_gate


pytestmark = pytest.mark.no_data_guard


def test_gamma_theorem_reference_exists() -> None:
    assert GAMMA_THEOREM["claim_id"] == "CC-21"
    assert GAMMA_THEOREM["registry_claim_id"] == "SOC-gamma"
    assert GAMMA_THEOREM["tier"] == "analytic"
    assert GAMMA_THEOREM["epsilon_firm_threshold"] == 0.125
    assert "epsilon_firm > 0.125" in GAMMA_THEOREM["conditions"]
    assert GAMMA_THEOREM["status"] == "proven"


def test_soc_cohort_gate_rejects_non_real() -> None:
    with pytest.raises(ValueError):
        evaluate_v7_gate(
            {
                "real": {
                    "treatment_n": 50,
                    "control_n": 50,
                    "threshold_k": 30,
                    "magnitude": 0.1,
                    "provenance": "sample",
                },
                "records": [{"provenance": "sample", "cohort": "treatment"}],
            }
        )
