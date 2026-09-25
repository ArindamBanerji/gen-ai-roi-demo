"""AGE-backed centroid checkpoint tests."""

from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

from app.services import gae_state


def _scorer_and_store(age_graph):
    scorer = SimpleNamespace(centroids=np.zeros((6, 4, 6), dtype=np.float64), decision_count=12, graph_store=age_graph.store)
    for _ in range(12):
        age_graph.decision(correct=True)
    return scorer, age_graph.store


def _checkpoint(store, identifier, tensor, count):
    store.write_centroid_checkpoint(domain="soc", checkpoint_id=identifier, centroids=tensor,
                                    category="all", action="all", verified_count=count, iks=0.0, factor_names_hash="test",
                                    shape=[6, 4, 6], decisions_count=count, metadata={"decision_count": count})


@pytest.mark.age
def test_manual_checkpoint_writes_full_tensor_to_age(age_graph):
    scorer, store = _scorer_and_store(age_graph)
    with patch.object(gae_state, "get_profile_scorer", return_value=scorer):
        payload = gae_state.create_centroid_checkpoint()

    rows = age_graph.reopen_store().get_centroid_checkpoints("soc", include_v2=True)
    assert len(rows) == 1
    write = rows[0]
    assert write["domain"] == "soc"
    assert write["checkpoint_id"] == payload["backup_id"]
    np.testing.assert_array_equal(write["centroids"], scorer.centroids)
    assert write["shape"] == [6, 4, 6]
    assert write["decisions_count"] == 12
    assert payload["backup_id"].startswith("soc:pitr:")
    assert payload["shape"] == [6, 4, 6]
    assert payload["step"] == 12


@pytest.mark.age
def test_checkpoint_listing_reads_age_not_filesystem(age_graph):
    scorer, store = _scorer_and_store(age_graph)
    _checkpoint(store, "soc:pitr:one", np.ones((6, 4, 6)), 4)
    scorer.graph_store = age_graph.reopen_store()
    with patch.object(gae_state, "get_profile_scorer", return_value=scorer):
        rows = gae_state.list_centroid_checkpoints()

    assert [row["backup_id"] for row in rows] == ["soc:pitr:one"]
    assert rows[0]["mu"][0][0][0] == 1.0


@pytest.mark.asyncio
@pytest.mark.age
async def test_restore_checkpoint_loads_age_tensor(age_graph):
    scorer, store = _scorer_and_store(age_graph)
    _checkpoint(store, "soc:pitr:restore", np.full((6, 4, 6), 3.0), 8)
    _checkpoint(store, "soc:pitr:newer", np.full((6, 4, 6), 9.0), 10)
    scorer.graph_store = age_graph.reopen_store()
    with patch.object(gae_state, "get_profile_scorer", return_value=scorer), \
         patch.object(gae_state, "_learning_state", SimpleNamespace(profile_scorer=scorer)):
        payload = await gae_state.restore_centroid_checkpoint("soc:pitr:restore")

    assert payload["backup_id"] == "soc:pitr:restore"
    assert float(scorer.centroids[0, 0, 0]) == 3.0
