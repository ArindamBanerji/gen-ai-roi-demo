"""Injection tests for the live SOC learning-health provider."""

from app.services.evolver import SOCConservationProvider


def _health(status: str, *, count: int = 12) -> dict[str, object]:
    return {
        "status": status,
        "health_source": "learning_health",
        "components": {"n": count},
    }


def test_soc_provider_returns_green_when_healthy() -> None:
    provider = SOCConservationProvider()
    provider.update_from_health(_health("GREEN"))
    state = provider.get_state()
    assert state["status"] == "GREEN"
    assert state["overallSafe"] is True


def test_soc_provider_returns_unknown_on_exception() -> None:
    provider = SOCConservationProvider()
    provider.mark_unknown("learning_health_error")
    state = provider.get_state()
    assert state["status"] == "UNKNOWN"
    assert state["overallSafe"] is False


def test_soc_provider_returns_calibrating_during_calibration() -> None:
    provider = SOCConservationProvider()
    provider.update_from_health(_health("CALIBRATING", count=2))
    assert provider.get_state()["status"] == "CALIBRATING"
    assert provider.get_state()["overallSafe"] is False


def test_soc_provider_returns_actual_amber_red() -> None:
    provider = SOCConservationProvider()
    for status in ("AMBER", "RED"):
        provider.update_from_health(_health(status))
        assert provider.get_state()["status"] == status
        assert provider.get_state()["overallSafe"] is False


def test_soc_provider_has_required_fields() -> None:
    provider = SOCConservationProvider()
    provider.update_from_health(_health("GREEN"))
    state = provider.get_state()
    assert state["domain"] == "soc"
    assert state["source"] == "learning_health"
    assert isinstance(state["observed_at"], str)


def test_soc_provider_ttl_caches_then_refreshes() -> None:
    now = [100.0]
    provider = SOCConservationProvider(freshness_ttl=30.0, clock=lambda: now[0])
    provider.update_from_health(_health("GREEN"))
    assert provider.get_state()["status"] == "GREEN"
    provider.update_from_health(_health("AMBER"))
    assert provider.get_state()["status"] == "AMBER"
    now[0] += 31.0
    assert provider.get_state()["status"] == "UNKNOWN"


def test_soc_provider_stale_returns_unknown() -> None:
    now = [100.0]
    provider = SOCConservationProvider(freshness_ttl=30.0, clock=lambda: now[0])
    provider.update_from_health(_health("GREEN"))
    now[0] += 31.0
    assert provider.get_state()["status"] == "UNKNOWN"
