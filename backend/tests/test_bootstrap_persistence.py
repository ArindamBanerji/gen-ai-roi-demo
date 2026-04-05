"""
Block 2.2 — bootstrap_centroids persistence tests.
Tests write_bootstrap_state() and get_bootstrap_centroids() using AsyncMock.
No live Neo4j required.
"""
import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch, MagicMock

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.services.gae_state import (
    init_learning_state,
    get_profile_scorer,
    write_bootstrap_state,
    get_bootstrap_centroids,
    WRITE_DEPLOYMENT_STATE,
    READ_DEPLOYMENT_STATE,
    _GAE_VERSION,
)


# ---------------------------------------------------------------------------
# Shared setup
# ---------------------------------------------------------------------------

init_learning_state()
_SCORER = get_profile_scorer()


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Test 1 — write_bootstrap_state calls run_query with correct params
# ---------------------------------------------------------------------------

def test_write_bootstrap_state_calls_run_query():
    mock_client = AsyncMock()
    mock_client.run_query.return_value = [{"ds": {}}]

    result = _run(write_bootstrap_state(mock_client, _SCORER))

    assert mock_client.run_query.called, "run_query should have been called"
    call_args = mock_client.run_query.call_args
    query = call_args[0][0]
    params = call_args[0][1]

    assert "MERGE (ds:DeploymentState" in query
    assert "bootstrap_mu" in params
    assert "bootstrap_shape" in params
    assert "timestamp_epoch" in params
    assert params["gae_version"] == _GAE_VERSION


# ---------------------------------------------------------------------------
# Test 2 — write_bootstrap_state returns correct payload shape
# ---------------------------------------------------------------------------

def test_write_bootstrap_state_returns_payload():
    mock_client = AsyncMock()
    mock_client.run_query.return_value = [{"ds": {}}]

    result = _run(write_bootstrap_state(mock_client, _SCORER))

    assert "bootstrap_mu" in result
    assert "bootstrap_shape" in result
    assert "bootstrap_stored_at" in result
    assert "gae_version" in result
    assert result["gae_version"] == _GAE_VERSION
    assert result["bootstrap_shape"] == list(_SCORER.mu.shape)
    assert isinstance(result["bootstrap_mu"], list)
    assert isinstance(result["bootstrap_stored_at"], int)
    assert result["bootstrap_stored_at"] > 0


# ---------------------------------------------------------------------------
# Test 3 — get_bootstrap_centroids returns parsed data when node exists
# ---------------------------------------------------------------------------

def test_get_bootstrap_centroids_returns_data():
    scorer = get_profile_scorer()
    mu_list = scorer.mu.tolist()
    shape = list(scorer.mu.shape)

    mock_client = AsyncMock()
    mock_client.run_query.return_value = [{
        "bootstrap_mu":    mu_list,
        "bootstrap_shape": shape,
        "stored_at":       1700000000000,
        "gae_version":     _GAE_VERSION,
    }]

    result = _run(get_bootstrap_centroids(mock_client))

    assert result is not None
    assert result["mu"] == mu_list
    assert result["shape"] == shape
    assert result["stored_at"] == 1700000000000
    assert result["gae_version"] == _GAE_VERSION


# ---------------------------------------------------------------------------
# Test 4 — get_bootstrap_centroids returns None when node absent
# ---------------------------------------------------------------------------

def test_get_bootstrap_centroids_returns_none_when_absent():
    mock_client = AsyncMock()
    mock_client.run_query.return_value = []   # no rows

    result = _run(get_bootstrap_centroids(mock_client))

    assert result is None


def test_get_bootstrap_centroids_returns_none_on_null_mu():
    mock_client = AsyncMock()
    mock_client.run_query.return_value = [{"bootstrap_mu": None}]

    result = _run(get_bootstrap_centroids(mock_client))

    assert result is None
