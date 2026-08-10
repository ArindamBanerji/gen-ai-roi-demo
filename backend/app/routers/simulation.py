"""
Simulation router -- SIM-1 batch GAE pipeline endpoints.

POST /api/simulation/start                 Start a simulation run
GET  /api/simulation/progress/{sim_id}     Live step / accuracy progress
GET  /api/simulation/result/{sim_id}       Full SimulationResult (when complete)
GET  /api/simulation/experiment-log/{sim_id}  Raw experiment log JSON array
"""

import asyncio
import uuid
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.simulation import SimulationOrchestrator, _FALLBACK_POOL
from app.services.state_manager import StateManager, ResetError
from app.models.responses import SimulationProgressResponse

router = APIRouter()

# ---------------------------------------------------------------------------
# In-memory simulation store — keyed by simulation_id
# ---------------------------------------------------------------------------

_simulations: Dict[str, Dict[str, Any]] = {}
_simulation_tasks: Dict[str, asyncio.Task] = {}


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------

class StartSimulationRequest(BaseModel):
    n_decisions: int = 50
    speed_ms:    int = 200


# ---------------------------------------------------------------------------
# Alert pool loader
# ---------------------------------------------------------------------------

async def _load_alert_pool():
    """
    Return the simulation alert pool -- scored actions only (BACKLOG-042).

    Imports get_alert_pool() from app.data.alert_pool -- a deterministic,
    pre-defined pool whose graph entities are seeded by seed_simulation_alerts().

    Referral alerts (ground_truth_action='refer_to_analyst') are excluded here:
    they are routing decisions handled by the confidence gate in triage.py, not
    scored actions.  Keeping them in the simulation pool causes a W_matrix
    refer_to_analyst attractor: the scorer picks refer_to_analyst, the guard at
    simulation.py:393 skips the W_matrix update, and W freezes permanently.
    Pool size: 27 total -> 24 after excluding the 3 referral alerts.

    Falls back to the minimal _FALLBACK_POOL if the import fails (e.g. during
    unit tests that run without the full package installed).
    """
    try:
        from app.data.alert_pool import get_alert_pool
        pool = get_alert_pool()
        # Exclude refer_to_analyst routing alerts — simulation scores only
        # escalate / investigate / suppress / monitor (SCORER_ACTIONS, A=4).
        sim_pool = [a for a in pool if a.get("ground_truth_action") != "refer_to_analyst"]
        print(
            f"[SIM] Alert pool loaded: {len(pool)} total, "
            f"{len(sim_pool)} for simulation (refer_to_analyst excluded)"
        )
        return sim_pool
    except Exception as exc:
        print(f"[SIM] Could not load alert pool from module ({exc}); using fallback")

    print(f"[SIM] Using synthetic fallback pool ({len(_FALLBACK_POOL)} alerts)")
    return list(_FALLBACK_POOL)


# ---------------------------------------------------------------------------
# Background simulation task
# ---------------------------------------------------------------------------

def _update_progress(sim_id: str, step: int, record: dict) -> None:
    """Update simulation progress from the worker thread."""
    sim = _simulations.get(sim_id)
    if sim is None:
        return
    sim.update({
        "step":                   step,
        "status":                 "running",
        "current_accuracy":       record["cumulative_accuracy"],
        "category_accuracy":      record["category_accuracy"],
        "latest_weight_snapshot": record["W_snapshot"],
    })


def _run_simulation_sync(
    sim_id: str,
    n_decisions: int,
    speed_ms: int,
    alert_pool: list[dict],
    orchestrator: SimulationOrchestrator,
):
    """Run the async orchestrator on a private event loop in a worker thread."""
    thread_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(thread_loop)

    async def on_progress(step: int, total: int, record: dict) -> None:
        _update_progress(sim_id, step, record)

    try:
        return thread_loop.run_until_complete(
            orchestrator.run(
                n_decisions=n_decisions,
                alert_pool=alert_pool,
                speed_ms=speed_ms,
                on_progress=on_progress,
            )
        )
    finally:
        thread_loop.run_until_complete(thread_loop.shutdown_asyncgens())
        asyncio.set_event_loop(None)
        thread_loop.close()


async def _run_simulation_bg(sim_id: str, n_decisions: int, speed_ms: int) -> None:
    """
    Async background task: runs the simulation and writes results to _simulations.

    Progress updates are written after every decision so
    GET /api/simulation/progress returns live data.
    """
    from app.core.domain_registry import get_domain_config

    try:
        alert_pool = await _load_alert_pool()

        orchestrator = SimulationOrchestrator(
            state_manager  = None,   # soft_reset already called by the start endpoint
            triage_service = None,
            domain_config  = get_domain_config(),
        )

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            _run_simulation_sync,
            sim_id,
            n_decisions,
            speed_ms,
            alert_pool,
            orchestrator,
        )

        _simulations[sim_id].update({
            "step":                   n_decisions,
            "status":                 "complete",
            "current_accuracy":       result.overall_accuracy,
            "category_accuracy":      result.category_accuracy,
            "latest_weight_snapshot": (
                result.weight_trajectory[-1] if result.weight_trajectory else []
            ),
            "result": {
                "n_decisions":           result.n_decisions,
                "overall_accuracy":      result.overall_accuracy,
                "category_accuracy":     result.category_accuracy,

                "weight_trajectory":     result.weight_trajectory,
                "experiment_log":        result.experiment_log,
                "duration_seconds":      result.duration_seconds,
            },
        })
        print(
            f"[SIM] {sim_id[:8]} complete -- "
            f"{result.n_decisions} decisions, "
            f"accuracy={result.overall_accuracy:.3f}, "
            f"duration={result.duration_seconds:.1f}s"
        )

    except Exception as exc:
        import traceback
        traceback.print_exc()
        _simulations[sim_id].update({
            "status": "error",
            "error":  str(exc),
        })
        print(f"[SIM] {sim_id[:8]} FAILED: {exc}")


def _track_simulation_task(sim_id: str, task: asyncio.Task) -> None:
    """Track detached simulation tasks and discard handles after completion."""
    _simulation_tasks[sim_id] = task

    def _cleanup(done_task: asyncio.Task) -> None:
        _simulation_tasks.pop(sim_id, None)
        try:
            done_task.exception()
        except asyncio.CancelledError:
            pass

    task.add_done_callback(_cleanup)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/simulation/start")
async def start_simulation(body: StartSimulationRequest):
    """
    Start a new batch simulation.

    Performs a soft reset first (W -> priors, clear Decision outcomes, fresh
    audit chain) so each run starts from a clean slate.

    Returns ``{"simulation_id": uuid, "status": "running"}``.
    """
    from app.services import gae_state, audit as audit_store
    from app.db.graph_client import graph_client
    from app.core.domain_registry import get_domain_config

    # Soft reset before simulation — ensures W starts from expert priors
    sm = StateManager(
        learning_state_service = gae_state,
        audit_store            = audit_store,
        graph_service          = graph_client,
        domain_config          = get_domain_config(),
    )
    try:
        await sm.soft_reset()
    except ResetError as exc:
        raise HTTPException(status_code=500, detail=f"Soft reset failed: {exc}")

    sim_id = str(uuid.uuid4())
    _simulations[sim_id] = {
        "sim_id":                 sim_id,
        "total":                  body.n_decisions,
        "step":                   0,
        "status":                 "running",
        "current_accuracy":       0.0,
        "category_accuracy":      {},
        "latest_weight_snapshot": [],
        "result":                 None,
    }

    _track_simulation_task(
        sim_id,
        asyncio.create_task(
            _run_simulation_bg(sim_id, body.n_decisions, body.speed_ms)
        ),
    )

    print(f"[SIM] Started {sim_id[:8]} -- n={body.n_decisions} speed={body.speed_ms}ms")
    return {"simulation_id": sim_id, "status": "running"}


@router.get("/simulation/progress/{simulation_id}", response_model=SimulationProgressResponse)
async def get_simulation_progress(simulation_id: str):
    """
    Return live progress for a running or completed simulation.

    Response:
    ```json
    {
      "step": 23,
      "total": 50,
      "status": "running",
      "current_accuracy": 0.826,
      "category_accuracy": {"phishing": 0.9, "malware": 0.75},
      "latest_weight_snapshot": [[...], ...]
    }
    ```
    """
    sim = _simulations.get(simulation_id)
    if sim is None:
        raise HTTPException(
            status_code=404,
            detail=f"Simulation {simulation_id} not found",
        )

    return {
        "step":                   sim["step"],
        "total":                  sim["total"],
        "status":                 sim["status"],
        "current_accuracy":       sim["current_accuracy"],
        "category_accuracy":      sim["category_accuracy"],
        "latest_weight_snapshot": sim["latest_weight_snapshot"],
    }


@router.get("/simulation/result/{simulation_id}")
async def get_simulation_result(simulation_id: str):
    """
    Return the full SimulationResult once the simulation is complete.

    Returns HTTP 202 (with detail) if still running; 404 if unknown.
    """
    sim = _simulations.get(simulation_id)
    if sim is None:
        raise HTTPException(
            status_code=404,
            detail=f"Simulation {simulation_id} not found",
        )

    if sim["status"] == "error":
        raise HTTPException(
            status_code=500,
            detail=f"Simulation failed: {sim.get('error', 'unknown error')}",
        )

    if sim["status"] != "complete":
        raise HTTPException(
            status_code=202,
            detail=f"Simulation not complete yet (step={sim['step']}/{sim['total']})",
        )

    return sim["result"]


@router.get("/simulation/experiment-log/{simulation_id}")
async def get_experiment_log(simulation_id: str):
    """
    Return the full structured experiment log as a JSON array.

    Each element is a decision record with step, factor_vector, W_snapshot,
    predicted_action, oracle_outcome, and accuracy tracking fields.

    Returns HTTP 202 if simulation is still running.
    """
    sim = _simulations.get(simulation_id)
    if sim is None:
        raise HTTPException(
            status_code=404,
            detail=f"Simulation {simulation_id} not found",
        )

    result = sim.get("result")
    if result is None:
        raise HTTPException(
            status_code=202,
            detail=f"Simulation not complete yet (step={sim['step']}/{sim['total']})",
        )

    return result["experiment_log"]
