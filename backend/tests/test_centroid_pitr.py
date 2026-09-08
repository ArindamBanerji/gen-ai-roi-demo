"""AGE-backed centroid checkpoint tests."""

from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

from app.services import gae_state


class FakeCheckpointStore:
    def __init__(self, rows):
        self.rows = rows
        self.writes = []

    def count_verified(self, domain):
        assert domain == "soc"
        return 12

    def write_centroid_checkpoint(self, **kwargs):
        self.writes.append(kwargs)
        self.rows.append({
            "checkpoint_id": kwargs["checkpoint_id"],
            "centroids": kwargs["centroids"].tolist(),
            "shape": kwargs["shape"],
            "created_at": 2000.0,
            "decisions_count": kwargs["decisions_count"],
            "metadata": kwargs["metadata"],
        })

    def get_centroid_checkpoints(self, domain, include_v2=False, limit=None):
        assert domain == "soc"
        assert include_v2 is True
        return list(self.rows)


def _scorer_and_store():
    scorer = SimpleNamespace(
        centroids=np.zeros((6, 4, 6), dtype=np.float64),
        decision_count=12,
    )
    store = FakeCheckpointStore([])
    scorer.graph_store = store
    return scorer, store


def test_manual_checkpoint_writes_full_tensor_to_age():
    scorer, store = _scorer_and_store()
    with patch.object(gae_state, "get_profile_scorer", return_value=scorer):
        payload = gae_state.create_centroid_checkpoint()

    assert len(store.writes) == 1
    write = store.writes[0]
    assert write["domain"] == "soc"
    assert write["checkpoint_id"] == payload["backup_id"]
    np.testing.assert_array_equal(write["centroids"], scorer.centroids)
    assert write["shape"] == [6, 4, 6]
    assert write["decisions_count"] == 12
    assert payload["backup_id"].startswith("soc:pitr:")
    assert payload["shape"] == [6, 4, 6]
    assert payload["step"] == 12


def test_checkpoint_listing_reads_age_not_filesystem():
    scorer, store = _scorer_and_store()
    store.rows.append({
        "checkpoint_id": "soc:pitr:one",
        "centroids": np.ones((6, 4, 6)).tolist(),
        "shape": [6, 4, 6],
        "created_at": 1000.0,
        "decisions_count": 4,
        "metadata": {"decision_count": 4},
    })
    with patch.object(gae_state, "get_profile_scorer", return_value=scorer):
        rows = gae_state.list_centroid_checkpoints()

    assert [row["backup_id"] for row in rows] == ["soc:pitr:one"]
    assert rows[0]["mu"][0][0][0] == 1.0


@pytest.mark.asyncio
async def test_restore_checkpoint_loads_age_tensor():
    scorer, store = _scorer_and_store()
    store.rows.append({
        "checkpoint_id": "soc:pitr:restore",
        "centroids": np.full((6, 4, 6), 3.0).tolist(),
        "shape": [6, 4, 6],
        "created_at": 1000.0,
        "decisions_count": 8,
        "metadata": {"decision_count": 8},
    })
    with patch.object(gae_state, "get_profile_scorer", return_value=scorer), \
         patch.object(gae_state, "_learning_state", SimpleNamespace(profile_scorer=scorer)):
        payload = await gae_state.restore_centroid_checkpoint("soc:pitr:restore")

    assert payload["backup_id"] == "soc:pitr:restore"
    assert float(scorer.centroids[0, 0, 0]) == 3.0
