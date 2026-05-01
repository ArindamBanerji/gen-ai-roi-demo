"""
CheckpointService contract tests (TD-033, Phase 4 §17.5).

Verifies create_checkpoint() and rollback() without a live Neo4j connection.
Uses a lightweight in-memory mock for neo4j_service and a minimal scorer stub.

4 tests.
"""
import asyncio
import json

import numpy as np

from app.framework.checkpoint import CheckpointService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    return asyncio.run(coro)


class _MockNeo4j:
    """In-memory neo4j stub: captures CREATE payloads, serves them on MATCH."""

    def __init__(self):
        self._checkpoints: dict = {}

    async def run_query(self, query: str, params: dict = None):
        params = params or {}
        if "CREATE" in query and "id" in params:
            self._checkpoints[params["id"]] = {
                "mu_snapshot":     params.get("mu",     "[]"),
                "counts_snapshot": params.get("counts", "[]"),
                "decision_count":  params.get("dc",     0),
                "reason":          params.get("reason", ""),
                "timestamp_epoch": params.get("timestamp_epoch", 0),
            }
            return []
        if "MATCH" in query and "id" in params:
            cp_id = params["id"]
            if cp_id in self._checkpoints:
                return [self._checkpoints[cp_id]]
            return []
        return []


class _MockScorer:
    """Minimal ProfileScorer stub — exposes only the fields checkpoint code reads."""

    def __init__(
        self,
        centroids: np.ndarray,
        counts: np.ndarray = None,
        decision_count: int = 0,
    ):
        self.centroids      = centroids.copy()
        self.counts         = np.zeros_like(centroids) if counts is None else counts.copy()
        self.decision_count = decision_count
        self._frozen        = False

    def freeze(self):
        self._frozen = True


# ---------------------------------------------------------------------------
# Test 1 — create_checkpoint uses scorer.centroids for mu_snapshot
# ---------------------------------------------------------------------------

def test_checkpoint_create_uses_centroids_not_mu():
    """
    create_checkpoint stores scorer.centroids as the mu_snapshot.
    Verifies the access path (not just that *some* array is stored).
    """
    centroids = np.array([[[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]]])
    scorer    = _MockScorer(centroids=centroids, decision_count=42)
    neo4j     = _MockNeo4j()

    cp_id = _run(CheckpointService.create_checkpoint(scorer, neo4j, reason="test"))

    assert cp_id in neo4j._checkpoints, "Checkpoint must be stored in neo4j stub"
    stored_mu = json.loads(neo4j._checkpoints[cp_id]["mu_snapshot"])
    assert np.allclose(
        np.array(stored_mu, dtype=np.float64),
        centroids,
        atol=1e-9,
    ), "Stored mu_snapshot must equal scorer.centroids at checkpoint time"


# ---------------------------------------------------------------------------
# Test 2 — rollback restores centroids to exact checkpoint state
# ---------------------------------------------------------------------------

def test_checkpoint_rollback_restores_exact_values():
    """
    Create checkpoint at state A, mutate scorer, rollback — centroids must
    match state A exactly (np.allclose, atol=1e-9).
    """
    centroids_a = np.array([[[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]]])
    scorer      = _MockScorer(centroids=centroids_a.copy(), decision_count=10)
    neo4j       = _MockNeo4j()

    # Checkpoint at state A
    cp_id = _run(CheckpointService.create_checkpoint(scorer, neo4j, reason="state_A"))

    # Mutate scorer (simulate subsequent learning updates)
    scorer.centroids = np.array([[[0.9, 0.8, 0.7, 0.6], [0.5, 0.4, 0.3, 0.2]]])

    # Rollback
    result = _run(CheckpointService.rollback(cp_id, scorer, neo4j))

    assert result.get("status") == "rolled_back", f"Expected rolled_back; got {result}"
    assert np.allclose(scorer.centroids, centroids_a, atol=1e-9), (
        "Rollback must restore centroids to the exact checkpoint state A"
    )


# ---------------------------------------------------------------------------
# Test 3 — rollback rejects NaN payload without corrupting scorer
# ---------------------------------------------------------------------------

def test_checkpoint_rollback_rejects_nan_payload():
    """
    A checkpoint with NaN values in mu_snapshot must be rejected.
    rollback() must return an error dict and leave scorer.centroids unchanged.
    """
    safe_centroids = np.array([[[0.5, 0.5, 0.5, 0.5]]])
    scorer         = _MockScorer(centroids=safe_centroids.copy(), decision_count=5)
    neo4j          = _MockNeo4j()

    bad_cp_id = "bad-cp-nan-test-xyz"
    neo4j._checkpoints[bad_cp_id] = {
        "mu_snapshot": json.dumps(
            [[[float("nan"), float("nan"), float("nan"), float("nan")]]],
            allow_nan=True,
        ),
        "counts_snapshot": "[]",
        "decision_count":  5,
    }

    result = _run(CheckpointService.rollback(bad_cp_id, scorer, neo4j))

    assert result is not None, "rollback must return a result dict (no unhandled exception)"
    assert "error" in result, (
        f"NaN payload must be rejected with error dict; got {result}"
    )
    assert np.allclose(scorer.centroids, safe_centroids, atol=1e-9), (
        "Scorer must be unchanged after rejected rollback"
    )


# ---------------------------------------------------------------------------
# Test 5 — rollback rejects Inf payload without corrupting scorer
# ---------------------------------------------------------------------------

def test_checkpoint_rollback_rejects_inf_centroids():
    """
    A checkpoint with Inf values in mu_snapshot must be rejected.
    rollback() must return an error dict and leave scorer.centroids unchanged.
    """
    safe_centroids = np.array([[[0.3, 0.3, 0.3, 0.3]]])
    scorer         = _MockScorer(centroids=safe_centroids.copy(), decision_count=7)
    neo4j          = _MockNeo4j()

    bad_cp_id = "bad-cp-inf-test-xyz"
    neo4j._checkpoints[bad_cp_id] = {
        "mu_snapshot": json.dumps(
            [[[float("inf"), float("-inf"), float("inf"), float("inf")]]],
            allow_nan=True,
        ),
        "counts_snapshot": "[]",
        "decision_count":  7,
    }

    result = _run(CheckpointService.rollback(bad_cp_id, scorer, neo4j))

    assert result is not None, "rollback must return a result dict (no unhandled exception)"
    assert "error" in result, (
        f"Inf payload must be rejected with error dict; got {result}"
    )
    assert np.allclose(scorer.centroids, safe_centroids, atol=1e-9), (
        "Scorer must be unchanged after Inf-payload rollback rejection"
    )


# ---------------------------------------------------------------------------
# Test 4 — checkpoint snapshot is immutable after scorer modification
# ---------------------------------------------------------------------------

def test_checkpoint_snapshot_immutable():
    """
    Modifying scorer.centroids after create_checkpoint must NOT alter the
    stored snapshot.  Immutability comes from json.dumps() capturing a copy.
    """
    centroids_v1 = np.array([[[0.1, 0.2, 0.3, 0.4]]])
    scorer       = _MockScorer(centroids=centroids_v1.copy(), decision_count=1)
    neo4j        = _MockNeo4j()

    # Create checkpoint at version 1
    cp_id = _run(CheckpointService.create_checkpoint(scorer, neo4j, reason="v1"))
    snapshot_at_create = json.loads(neo4j._checkpoints[cp_id]["mu_snapshot"])

    # Mutate scorer (simulate learning updates)
    scorer.centroids      = np.array([[[0.9, 0.8, 0.7, 0.6]]])
    scorer.decision_count = 50

    # Re-read stored checkpoint — must be unchanged
    snapshot_at_read = json.loads(neo4j._checkpoints[cp_id]["mu_snapshot"])

    assert snapshot_at_create == snapshot_at_read, (
        "Checkpoint snapshot must be immutable after scorer modification"
    )
    assert np.allclose(
        np.array(snapshot_at_create, dtype=np.float64),
        centroids_v1,
        atol=1e-9,
    ), "Checkpoint must reflect scorer state at creation time, not current state"
