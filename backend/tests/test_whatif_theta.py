from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from app.domains.soc.config import SOCDomainConfig, compute_theta_min
from app.services.whatif_service import WhatIfScenario, run_whatif


def test_whatif_uses_compute_theta_min():
    source = Path("app/services/whatif_service.py").read_text(encoding="utf-8")

    assert "compute_theta_min" in source
    assert "gae.calibration import check_conservation, compute_theta_min" not in source
    assert "derive_theta_min" not in source


def test_whatif_theta_min_uses_override_rate():
    lower_override = run_whatif(
        WhatIfScenario(alpha=0.05, V=200.0, q_initial=1.0, q_target=1.0, horizon_days=1)
    )
    higher_override = run_whatif(
        WhatIfScenario(alpha=0.25, V=200.0, q_initial=1.0, q_target=1.0, horizon_days=1)
    )

    assert lower_override.conservation_law["theta_min"] == pytest.approx(
        compute_theta_min(0.05, 200.0)
    )
    assert higher_override.conservation_law["theta_min"] == pytest.approx(
        compute_theta_min(0.25, 200.0)
    )
    assert lower_override.conservation_law["theta_min"] > higher_override.conservation_law["theta_min"]


def test_no_derive_theta_min_deprecation_warning():
    scenario = WhatIfScenario(alpha=0.0, V=200.0, q_initial=1.0, q_target=1.0, horizon_days=1)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        run_whatif(scenario)

    assert not [item for item in caught if item.category is DeprecationWarning]


def test_whatif_does_not_use_penalty_ratio_for_theta():
    penalty_ratio = SOCDomainConfig().asymmetry_ratio
    scenario = WhatIfScenario(alpha=0.25, V=200.0, q_initial=1.0, q_target=1.0, horizon_days=1)

    result = run_whatif(scenario)

    assert result.conservation_law["theta_min"] == pytest.approx(compute_theta_min(0.25, 200.0))
    assert result.conservation_law["theta_min"] != pytest.approx(
        compute_theta_min(penalty_ratio, 200.0)
    )
