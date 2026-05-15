import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np

from app.services.gae_state import (
    get_frozen_categories,
    guarded_update,
    is_category_frozen,
    set_frozen_categories,
    set_volume_spike,
)
from app.services.learning_health import compute_verification_health


def _run(coro):
    return asyncio.run(coro)


def _healthy_verification_client():
    client = AsyncMock()
    client.run_query.side_effect = [
        [{"total": 1000}],
        [{"verified": 300}],
        [{"total": 100, "verified": 30}],
        [{"total": 100, "verified": 30}],
    ]
    return client


def test_unknown_conservation_is_not_green():
    client = _healthy_verification_client()

    with patch(
        "app.services.learning_health.LearningHealthMonitor.evaluate",
        new=AsyncMock(side_effect=RuntimeError("conservation unavailable")),
    ):
        result = _run(compute_verification_health(client))

    assert result["conservation_status"] == "UNKNOWN"
    assert result["conservation_healthy"] is False
    assert result["status"] == "AMBER"


def test_frozen_categories_clear_on_spike_clear():
    try:
        set_volume_spike(True)
        set_frozen_categories(["credential_access"])

        assert is_category_frozen("credential_access") is True

        set_volume_spike(False)

        assert get_frozen_categories() == set()
        assert is_category_frozen("credential_access") is False
    finally:
        set_volume_spike(False)
        set_frozen_categories([])


def test_frozen_categories_persist_while_spike_active():
    try:
        set_volume_spike(True)
        set_frozen_categories(["credential_access"])

        assert is_category_frozen("credential_access") is True
        assert get_frozen_categories() == {"credential_access"}
    finally:
        set_volume_spike(False)
        set_frozen_categories([])


def test_spike_clear_allows_learning_for_previously_frozen():
    scorer = MagicMock()
    scorer.update.return_value = MagicMock()

    try:
        set_volume_spike(True)
        set_frozen_categories(["credential_access"])
        set_volume_spike(False)

        result = guarded_update(
            scorer,
            f=np.zeros(6),
            category_index=0,
            action_index=0,
            correct=True,
            category_name="credential_access",
        )

        assert result is not None
        scorer.update.assert_called_once()
        assert is_category_frozen("credential_access") is False
    finally:
        set_volume_spike(False)
        set_frozen_categories([])
