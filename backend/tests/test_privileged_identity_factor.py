import asyncio

from app.domains.soc.config import (
    SCORER_ACTIONS,
    SOC_CATEGORIES,
    SOC_FACTORS,
    SOC_FACTOR_SIGMA,
    SOCDomainConfig,
)
from app.domains.soc.factors import PrivilegedIdentityContextFactor
from app.models.schemas import SecurityContext


def _run(awaitable):
    return asyncio.run(awaitable)


def test_privileged_identity_factor_admin_high_score():
    factor = PrivilegedIdentityContextFactor()
    context = SecurityContext(
        user_id="u-1",
        user_name="Admin User",
        user_title="Admin",
        user_risk_score=0.8,
        asset_id="a-1",
        asset_hostname="host-1",
        asset_criticality="HIGH",
        mfa_completed=False,
        device_fingerprint_match=False,
    )

    score = _run(factor.compute("alert-1", context))

    assert score > 0.6


def test_privileged_identity_factor_standard_user_low_score():
    factor = PrivilegedIdentityContextFactor()
    context = SecurityContext(
        user_id="u-2",
        user_name="Analyst User",
        user_title="Analyst",
        user_risk_score=0.1,
        asset_id="a-2",
        asset_hostname="host-2",
        asset_criticality="MEDIUM",
        mfa_completed=True,
        device_fingerprint_match=True,
    )

    score = _run(factor.compute("alert-2", context))

    assert score < 0.3


def test_privileged_identity_factor_no_context_returns_default():
    factor = PrivilegedIdentityContextFactor()

    score = _run(factor.compute("alert-3", None))

    assert score == 0.5


def test_soc_factors_includes_privileged_identity_context():
    assert "privileged_identity_context" in SOC_FACTORS
    assert "travel_match" not in SOC_FACTORS


def test_factor_sigma_includes_privileged_identity_context():
    assert SOC_FACTOR_SIGMA["privileged_identity_context"] == 0.10
    assert "travel_match" not in SOC_FACTOR_SIGMA


def test_centroid_shape_unchanged():
    cfg = SOCDomainConfig()
    mu = cfg.build_profile_scorer().centroids

    assert mu.shape == (len(SOC_CATEGORIES), len(SCORER_ACTIONS), len(SOC_FACTORS))
    assert mu.shape == (6, 4, 6)


def test_new_centroids_separate_suppress_monitor():
    cfg = SOCDomainConfig()
    mu = cfg.get_initial_centroids()
    suppress_idx = SCORER_ACTIONS.index("suppress")
    monitor_idx = SCORER_ACTIONS.index("monitor")

    for ci, _category in enumerate(SOC_CATEGORIES):
        delta = abs(float(mu[ci, suppress_idx, 0]) - float(mu[ci, monitor_idx, 0]))
        assert delta >= 0.05
        assert float(mu[ci, suppress_idx, 0]) != float(mu[ci, monitor_idx, 0])
