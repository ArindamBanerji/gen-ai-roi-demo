import asyncio
import threading
import time

import numpy as np
import pytest
from gae.learning import CalibrationProfile, LearningState
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.routers import simulation as simulation_router
from app.services.simulation import SimulationResult, _clone_learning_state_for_simulation


def _patch_fast_health(monkeypatch):
    from app import main as app_main
    from app.services.posterior_store import PosteriorStore

    monkeypatch.setattr(PosteriorStore, "health_check", lambda self: {"healthy": True})
    monkeypatch.setattr(app_main, "_safe_entity_cache_health", lambda: {"healthy": True})


def test_simulation_clone_detaches_profile_scorer():
    live_state = LearningState(
        W=np.ones((2, 2), dtype=np.float64),
        n_actions=2,
        n_factors=2,
        factor_names=["asset", "intel"],
        profile=CalibrationProfile(),
        decision_count=7,
        profile_scorer=object(),
    )

    sim_state = _clone_learning_state_for_simulation(live_state)

    assert sim_state.profile_scorer is None
    assert sim_state.decision_count == live_state.decision_count
    assert np.array_equal(sim_state.W, live_state.W)

    sim_state.update(
        action_index=0,
        action_name="investigate",
        outcome=1,
        f=np.ones((1, 2), dtype=np.float64),
        confidence_at_decision=0.5,
    )

    assert not np.array_equal(sim_state.W, live_state.W)
    assert np.array_equal(live_state.W, np.ones((2, 2), dtype=np.float64))


def _patch_simulation_dependencies(
    monkeypatch,
    *,
    delay: float,
    fail: bool = False,
    blocking_delay: float = 0.0,
    thread_ids: list[int] | None = None,
):
    simulation_router._simulations.clear()
    simulation_router._simulation_tasks.clear()

    async def fake_soft_reset(self):
        return None

    async def fake_alert_pool():
        return [
            {
                "alert_id": "sim-alert-1",
                "category": "credential_access",
                "ground_truth_action": "investigate",
            }
        ]

    class FakeSimulationOrchestrator:
        def __init__(self, *args, **kwargs):
            pass

        async def run(self, n_decisions, alert_pool, speed_ms=200, on_progress=None):
            if thread_ids is not None:
                thread_ids.append(threading.get_ident())
            if blocking_delay:
                time.sleep(blocking_delay)
            for step in range(n_decisions):
                if fail:
                    raise RuntimeError("simulated failure")
                if on_progress:
                    await on_progress(
                        step + 1,
                        n_decisions,
                        {
                            "cumulative_accuracy": 1.0,
                            "category_accuracy": {"credential_access": 1.0},
                            "W_snapshot": [[1.0]],
                        },
                    )
                await asyncio.sleep(delay)

            return SimulationResult(
                n_decisions=n_decisions,
                overall_accuracy=1.0,
                category_accuracy={"credential_access": 1.0},
                weight_trajectory=[[[1.0]]],
                experiment_log=[],
                duration_seconds=delay * n_decisions,
                ground_truth_accuracy=1.0,
                category_ground_truth={"credential_access": 1.0},
            )

    monkeypatch.setattr(simulation_router.StateManager, "soft_reset", fake_soft_reset)
    monkeypatch.setattr(simulation_router, "_load_alert_pool", fake_alert_pool)
    monkeypatch.setattr(
        simulation_router,
        "SimulationOrchestrator",
        FakeSimulationOrchestrator,
    )
    monkeypatch.setattr(
        "app.core.domain_registry.get_domain_config",
        lambda: object(),
    )
    _patch_fast_health(monkeypatch)


async def _client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def _wait_for_status(client: AsyncClient, sim_id: str, status: str, timeout: float = 5.0):
    deadline = asyncio.get_running_loop().time() + timeout
    latest = None
    while asyncio.get_running_loop().time() < deadline:
        response = await client.get(f"/api/simulation/progress/{sim_id}")
        latest = response.json()
        if latest["status"] == status:
            return latest
        await asyncio.sleep(0.05)
    pytest.fail(f"simulation did not reach {status!r}; latest={latest}")


@pytest.mark.asyncio
async def test_health_responds_during_simulation(monkeypatch):
    main_thread_id = threading.get_ident()
    worker_thread_ids: list[int] = []
    _patch_simulation_dependencies(
        monkeypatch,
        delay=0.01,
        blocking_delay=0.6,
        thread_ids=worker_thread_ids,
    )

    async with await _client() as client:
        response = await asyncio.wait_for(
            client.post("/api/simulation/start", json={"n_decisions": 5, "speed_ms": 100}),
            timeout=1.0,
        )
        assert response.status_code == 200
        sim_id = response.json()["simulation_id"]

        for _ in range(20):
            if worker_thread_ids:
                break
            await asyncio.sleep(0.02)
        assert worker_thread_ids
        assert worker_thread_ids[0] != main_thread_id

        health = await asyncio.wait_for(client.get("/health"), timeout=5.0)
        assert health.status_code == 200

        await _wait_for_status(client, sim_id, "complete")


@pytest.mark.asyncio
async def test_progress_responds_during_simulation(monkeypatch):
    _patch_simulation_dependencies(monkeypatch, delay=0.2)

    async with await _client() as client:
        response = await client.post(
            "/api/simulation/start",
            json={"n_decisions": 10, "speed_ms": 200},
        )
        sim_id = response.json()["simulation_id"]

        await asyncio.sleep(0.3)
        progress = await asyncio.wait_for(
            client.get(f"/api/simulation/progress/{sim_id}"),
            timeout=5.0,
        )
        completed = await _wait_for_status(client, sim_id, "complete")

    assert progress.status_code == 200
    data = progress.json()
    assert data["status"] == "running"
    assert data["step"] >= 1
    assert completed["status"] == "complete"


@pytest.mark.asyncio
async def test_simulation_completes_in_thread(monkeypatch):
    main_thread_id = threading.get_ident()
    worker_thread_ids: list[int] = []
    _patch_simulation_dependencies(monkeypatch, delay=0.01, thread_ids=worker_thread_ids)

    async with await _client() as client:
        response = await client.post(
            "/api/simulation/start",
            json={"n_decisions": 5, "speed_ms": 50},
        )
        sim_id = response.json()["simulation_id"]

        data = await _wait_for_status(client, sim_id, "complete")

    assert data["status"] == "complete"
    assert data["step"] == 5
    assert worker_thread_ids
    assert worker_thread_ids[0] != main_thread_id


@pytest.mark.asyncio
async def test_simulation_error_does_not_crash_server(monkeypatch):
    _patch_simulation_dependencies(monkeypatch, delay=0.01, fail=True)

    async with await _client() as client:
        response = await client.post(
            "/api/simulation/start",
            json={"n_decisions": 5, "speed_ms": 50},
        )
        sim_id = response.json()["simulation_id"]

        for _ in range(20):
            progress = await client.get(f"/api/simulation/progress/{sim_id}")
            if progress.json()["status"] == "error":
                break
            await asyncio.sleep(0.05)

        health = await asyncio.wait_for(client.get("/health"), timeout=5.0)

    assert progress.json()["status"] == "error"
    assert health.status_code == 200
