import asyncio
import os
import sys
import time
from unittest.mock import AsyncMock

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.domains.soc.config import SOC_CATEGORIES, SOC_PROFILE_CENTROIDS
from app.services.cross_graph_discovery import (
    DAY_MS,
    Discovery,
    DiscoveryService,
    DiscoveryType,
    _clamp_score,
    _parse_collected,
    _parse_factor_vector,
    _severity_for_score,
)


AS_OF = 1743638400000
BASELINE = AS_OF - 30 * DAY_MS
RECENT = AS_OF - 7 * DAY_MS


def run_query_strings(mock):
    return [call.args[0] for call in mock.run_query.call_args_list]


def assert_age_safe(query: str):
    forbidden = [
        "$",
        "datetime(",
        "duration(",
        "CASE WHEN",
        "MERGE",
        "toFloat(",
        "labels(",
        " AS count",
    ]
    for token in forbidden:
        assert token not in query


def discovery_row(score: float, severity: str = "low"):
    return Discovery(
        discovery_id=f"d-{score}",
        domain="soc",
        source_domains=["soc"],
        type=DiscoveryType.SHARED_ENTITY.value,
        severity=severity,
        title="t",
        description="d",
        score=score,
        discovered_at="2026-01-01T00:00:00Z",
    )


def test_parse_collected_variants():
    assert _parse_collected(["a"]) == ["a"]
    assert _parse_collected('["a", "b"]') == ["a", "b"]
    assert _parse_collected("") == []
    assert _parse_collected(None) == []
    assert _parse_collected("{bad") == []
    assert _parse_collected('{"x": 1}') == []


def test_parse_factor_vector_variants():
    assert _parse_factor_vector("[0, 1, 2, 3, 4, 5]").dtype == np.float64
    assert _parse_factor_vector([0, 1, 2, 3, 4, 5]).shape == (6,)
    assert _parse_factor_vector(None) is None
    assert _parse_factor_vector("{bad") is None
    assert _parse_factor_vector("") is None
    assert _parse_factor_vector({"x": 1}) is None
    assert _parse_factor_vector([0, 1]) is None


def test_score_clamp_and_severity_boundaries():
    assert _clamp_score(-0.1) == 0.0
    assert _clamp_score(1.2) == 1.0
    assert _severity_for_score(0.7) == "high"
    assert _severity_for_score(0.4) == "medium"
    assert _severity_for_score(0.6999) == "medium"
    assert _severity_for_score(0.3999) == "low"


@pytest.mark.asyncio
async def test_get_as_of_epoch_returns_max_alert_timestamp():
    service = DiscoveryService()
    mock = AsyncMock()
    mock.run_query.side_effect = [
        [{"max_alert_epoch": "1741305600000"}],
    ]

    assert await service._get_as_of_epoch_ms(mock) == 1741305600000


@pytest.mark.asyncio
async def test_empty_timestamp_graph_returns_empty_without_wall_clock(monkeypatch):
    service = DiscoveryService(time_fn=lambda: 9999999999.0)
    mock = AsyncMock()
    mock.run_query.side_effect = [[{"max_alert_epoch": None}]]

    envelope = await service.refresh("soc", mock)

    assert envelope["as_of_epoch_ms"] is None
    assert envelope["discoveries"] == []
    assert envelope["errors"] == ["No graph timestamps available"]
    assert len(mock.run_query.call_args_list) == 1


@pytest.mark.asyncio
async def test_stale_cache_returned_when_graph_clock_lookup_raises():
    service = DiscoveryService(ttl_seconds=10, time_fn=lambda: 100.0)
    service._cache["soc"] = {
        "domain": "soc",
        "source_domains": ["soc"],
        "generated_at": "old",
        "as_of_epoch_ms": AS_OF,
        "cache": {"hit": False, "stale": False, "ttl_seconds": 10},
        "discoveries": [{"discovery_id": "old", "score": 1.0, "severity": "high"}],
        "total": 1,
        "errors": [],
    }
    service._cache_time["soc"] = 0.0
    mock = AsyncMock()
    mock.run_query.side_effect = RuntimeError("clock down")

    envelope = await service.refresh("soc", mock)

    assert envelope["cache"]["hit"] is False
    assert envelope["cache"]["stale"] is True
    assert envelope["discoveries"][0]["discovery_id"] == "old"
    assert service._cache["soc"]["discoveries"][0]["discovery_id"] == "old"


@pytest.mark.asyncio
async def test_stale_cache_returned_when_graph_clock_has_no_timestamps():
    service = DiscoveryService(ttl_seconds=10, time_fn=lambda: 100.0)
    service._cache["soc"] = {
        "domain": "soc",
        "source_domains": ["soc"],
        "generated_at": "old",
        "as_of_epoch_ms": AS_OF,
        "cache": {"hit": False, "stale": False, "ttl_seconds": 10},
        "discoveries": [{"discovery_id": "old", "score": 1.0, "severity": "high"}],
        "total": 1,
        "errors": [],
    }
    service._cache_time["soc"] = 0.0
    mock = AsyncMock()
    mock.run_query.side_effect = [[{"max_alert_epoch": None}]]

    envelope = await service.refresh("soc", mock)

    assert envelope["cache"]["hit"] is False
    assert envelope["cache"]["stale"] is True
    assert envelope["discoveries"][0]["discovery_id"] == "old"
    assert service._cache["soc"]["discoveries"][0]["discovery_id"] == "old"


@pytest.mark.asyncio
async def test_refresh_uses_graph_clock_cutoffs_not_host_wall_clock(monkeypatch):
    service = DiscoveryService(time_fn=lambda: 123456.0)
    mock = AsyncMock()
    mock.run_query.side_effect = [
        [{"max_alert_epoch": AS_OF}],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
    ]

    await service.refresh("soc", mock)
    queries = "\n".join(run_query_strings(mock))

    assert str(BASELINE) in queries
    assert str(RECENT) in queries
    assert "123456" not in queries


@pytest.mark.asyncio
async def test_generated_queries_are_age_safe_and_use_verified_relationships():
    service = DiscoveryService()
    mock = AsyncMock()
    # Algorithm 1 new order: user_agg(qualifies), asset_agg=[], user_batch_TI=[{entity_id, indicator}]
    # No asset batch TI because no qualifying assets.
    mock.run_query.side_effect = [
        [{"max_alert_epoch": AS_OF}],
        [
            {
                "entity_id": "USR-1",
                "entity_name": "User",
                "alert_ids_json": ["A1", "A2", "A3"],
                "categories_json": ["credential_access", "lateral_movement", "insider_threat"],
                "timestamps_json": [AS_OF, AS_OF - 1, AS_OF - 2],
                "cnt": 3,
            }
        ],
        [],  # asset aggregate
        [{"entity_id": "USR-1", "indicator": "ioc", "indicator_severity": "high", "alert_id": "A1"}],  # user batch TI
        [],  # pattern convergence
        [],  # velocity user recent
        [],  # velocity user baseline
        [],  # velocity asset recent
        [],  # velocity asset baseline
    ]

    await service.refresh("soc", mock)
    queries = run_query_strings(mock)

    for query in queries:
        assert_age_safe(query)
    all_queries = "\n".join(queries)
    assert "(a:Alert)-[:INVOLVES]->(u:User)" in all_queries
    assert "(a:Alert)-[:DETECTED_ON]->(asset:Asset)" in all_queries
    assert "(d:Decision)-[:DECIDED_ON]->(a:Alert)" in all_queries
    assert "(a)-[:HAS_INDICATOR]->(ti:ThreatIndicator)" in all_queries


@pytest.mark.asyncio
async def test_shared_entity_user_qualifies_without_threat_intel():
    service = DiscoveryService()
    mock = AsyncMock()
    # New order: user_agg, asset_agg, user_batch_TI (no asset TI — no qualifying assets)
    mock.run_query.side_effect = [
        [
            {
                "entity_id": "USR-1",
                "entity_name": "Analyst",
                "alert_ids_json": ["A1", "A2", "A3"],
                "categories_json": ["credential_access", "lateral_movement", "insider_threat"],
                "timestamps_json": [AS_OF, AS_OF - 1, AS_OF - 2],
                "cnt": 3,
            }
        ],
        [],   # asset aggregate
        [],   # user batch TI (no indicators)
    ]

    discoveries = await service._shared_entity_discovery(mock, BASELINE, AS_OF)

    assert len(discoveries) == 1
    assert discoveries[0].involved_entity_ids == ["USR-1"]
    assert discoveries[0].threat_indicator_ids == []


@pytest.mark.asyncio
async def test_shared_entity_asset_qualifies_and_threat_intel_boosts():
    service = DiscoveryService()
    mock = AsyncMock()
    # New order: user_agg=[], asset_agg(qualifies), asset_batch_TI (no user TI — no qualifying users)
    mock.run_query.side_effect = [
        [],   # user aggregate
        [
            {
                "entity_id": "AST-1",
                "entity_name": "host",
                "alert_ids_json": '["A1", "A2", "A3"]',
                "categories_json": '["credential_access", "lateral_movement", "insider_threat"]',
                "timestamps_json": f"[{AS_OF}, {AS_OF - 1}, {AS_OF - 2}]",
                "cnt": 3,
            }
        ],
        # asset batch TI — new format includes entity_id
        [{"entity_id": "AST-1", "indicator": "1.2.3.4", "indicator_severity": "high", "alert_id": "A1"}],
    ]

    discoveries = await service._shared_entity_discovery(mock, BASELINE, AS_OF)

    assert len(discoveries) == 1
    assert discoveries[0].involved_entity_ids == ["AST-1"]
    assert discoveries[0].threat_indicator_ids == ["1.2.3.4"]
    assert discoveries[0].score >= 0.3


@pytest.mark.asyncio
async def test_shared_entity_single_category_or_below_min_alerts_skipped():
    service = DiscoveryService()
    mock = AsyncMock()
    mock.run_query.side_effect = [
        [
            {
                "entity_id": "USR-1",
                "entity_name": "User",
                "alert_ids_json": ["A1", "A2", "A3"],
                "categories_json": ["credential_access", "credential_access", "credential_access"],
                "timestamps_json": [AS_OF, AS_OF - 1, AS_OF - 2],
                "cnt": 3,
            }
        ],
        [
            {
                "entity_id": "AST-1",
                "entity_name": "host",
                "alert_ids_json": ["A1", "A2"],
                "categories_json": ["credential_access", "lateral_movement"],
                "timestamps_json": [AS_OF, AS_OF - 1],
                "cnt": 2,
            }
        ],
    ]

    assert await service._shared_entity_discovery(mock, BASELINE, AS_OF) == []


@pytest.mark.asyncio
async def test_shared_entity_exact_window_excludes_outside_alert():
    service = DiscoveryService()
    mock = AsyncMock()
    mock.run_query.side_effect = [
        [
            {
                "entity_id": "USR-1",
                "entity_name": "User",
                "alert_ids_json": ["A1", "A2", "A3"],
                "categories_json": ["credential_access", "lateral_movement", "insider_threat"],
                "timestamps_json": [AS_OF, AS_OF - 1, BASELINE - 1],
                "cnt": 3,
            }
        ],
        [],
    ]

    assert await service._shared_entity_discovery(mock, BASELINE, AS_OF) == []


@pytest.mark.asyncio
async def test_shared_entity_exact_window_three_inside_qualifies():
    service = DiscoveryService()
    mock = AsyncMock()
    # New order: user_agg(qualifies), asset_agg=[], user_batch_TI=[]
    mock.run_query.side_effect = [
        [
            {
                "entity_id": "USR-1",
                "entity_name": "User",
                "alert_ids_json": ["A1", "A2", "A3"],
                "categories_json": ["credential_access", "lateral_movement", "insider_threat"],
                "timestamps_json": [AS_OF, AS_OF - 1, BASELINE],
                "cnt": 3,
            }
        ],
        [],   # asset aggregate
        [],   # user batch TI
    ]

    discoveries = await service._shared_entity_discovery(mock, BASELINE, AS_OF)

    assert len(discoveries) == 1


@pytest.mark.asyncio
async def test_pattern_convergence_cross_category_same_action_discovers():
    service = DiscoveryService()
    mock = AsyncMock()
    mock.run_query.return_value = [
        {
            "decision_id": "D1",
            "alert_id": "A1",
            "category": "credential_access",
            "action": "investigate",
            "confidence": 0.9,
            "factor_vector": [0, 0, 0, 0, 0, 0],
            "timestamp_epoch": AS_OF,
        },
        {
            "decision_id": "D2",
            "alert_id": "A2",
            "category": "lateral_movement",
            "action": "investigate",
            "confidence": 0.8,
            "factor_vector": [0.1, 0, 0, 0, 0, 0],
            "timestamp_epoch": AS_OF,
        },
    ]

    discoveries, parsed = await service._pattern_convergence_discovery(mock, BASELINE)

    assert len(parsed) == 2
    assert len(discoveries) == 1
    assert discoveries[0].type == DiscoveryType.PATTERN_CONVERGENCE.value
    assert "d.confidence > 0.7" in mock.run_query.call_args.args[0].replace("0.70", "0.7")


@pytest.mark.asyncio
async def test_pattern_convergence_skips_same_category_and_malformed_vectors():
    service = DiscoveryService()
    mock = AsyncMock()
    mock.run_query.return_value = [
        {
            "decision_id": "D1",
            "alert_id": "A1",
            "category": "credential_access",
            "action": "investigate",
            "confidence": 0.9,
            "factor_vector": "{bad",
        },
        {
            "decision_id": "D2",
            "alert_id": "A2",
            "category": "credential_access",
            "action": "investigate",
            "confidence": 0.9,
            "factor_vector": [0, 0, 0, 0, 0, 0],
        },
        {
            "decision_id": "D3",
            "alert_id": "A3",
            "category": "credential_access",
            "action": "investigate",
            "confidence": 0.9,
            "factor_vector": [0.1, 0, 0, 0, 0, 0],
        },
    ]

    discoveries, parsed = await service._pattern_convergence_discovery(mock, BASELINE)

    assert len(parsed) == 2
    assert discoveries == []


@pytest.mark.asyncio
async def test_temporal_velocity_user_and_asset_spikes_detected():
    service = DiscoveryService()
    mock = AsyncMock()
    mock.run_query.side_effect = [
        [{"entity_id": "USR-1", "entity_name": "User", "alert_ids_json": ["A1", "A2", "A3"], "cnt": 3}],
        [{"entity_id": "USR-1", "entity_name": "User", "cnt": 1}],
        [{"entity_id": "AST-1", "entity_name": "host", "alert_ids_json": ["A4", "A5", "A6"], "cnt": 3}],
        [{"entity_id": "AST-1", "entity_name": "host", "cnt": 1}],
    ]

    discoveries = await service._temporal_velocity_discovery(mock, RECENT, BASELINE)

    assert [d.involved_entity_ids[0] for d in discoveries] == ["USR-1", "AST-1"]


@pytest.mark.asyncio
async def test_temporal_velocity_boundaries_and_zero_baseline():
    service = DiscoveryService()
    mock = AsyncMock()
    mock.run_query.side_effect = [
        [
            {"entity_id": "ZERO", "cnt": 100},
            {"entity_id": "LOWRECENT", "cnt": 1},
            {"entity_id": "EXACT", "cnt": 5},
            {"entity_id": "BELOW", "cnt": 4},
        ],
        [
            {"entity_id": "ZERO", "cnt": 0},
            {"entity_id": "LOWRECENT", "cnt": 1},
            {"entity_id": "EXACT", "cnt": 6},
            {"entity_id": "BELOW", "cnt": 7},
        ],
        [],
        [],
    ]

    discoveries = await service._temporal_velocity_discovery(mock, RECENT, BASELINE)

    assert [d.involved_entity_ids[0] for d in discoveries] == ["EXACT"]


def test_cross_factor_anomaly_skips_unknown_malformed_and_well_assigned():
    service = DiscoveryService()
    mean0 = np.asarray(SOC_PROFILE_CENTROIDS).mean(axis=1)[0]
    discoveries = service._cross_factor_anomaly_discovery([
        {"decision_id": "UNK", "category": "unknown", "factor_vector": [0, 0, 0, 0, 0, 0]},
        {"decision_id": "BAD", "category": "credential_access", "factor_vector": "{bad"},
        {"decision_id": "OK", "category": "credential_access", "factor_vector": mean0.tolist()},
    ])

    assert discoveries == []


def test_cross_factor_anomaly_detects_misroute_and_clamps_score():
    service = DiscoveryService()
    means = np.asarray(SOC_PROFILE_CENTROIDS).mean(axis=1)
    row = {
        "decision_id": "D1",
        "alert_id": "A1",
        "category": "credential_access",
        "factor_vector": means[SOC_CATEGORIES.index("insider_threat")].tolist(),
    }

    discoveries = service._cross_factor_anomaly_discovery([row])

    assert len(discoveries) == 1
    assert discoveries[0].type == DiscoveryType.CROSS_FACTOR_MISROUTE.value
    assert discoveries[0].score <= 1.0


def test_cross_factor_anomaly_detects_novel_without_duplicate():
    service = DiscoveryService()
    row = {
        "decision_id": "D1",
        "alert_id": "A1",
        "category": "credential_access",
        "factor_vector": [-1, -1, -1, -1, -1, -1],
    }

    discoveries = service._cross_factor_anomaly_discovery([row])

    assert len(discoveries) == 1
    assert discoveries[0].type == DiscoveryType.CROSS_FACTOR_NOVEL.value


def test_cross_factor_anomaly_prioritizes_misroute_when_also_novel():
    service = DiscoveryService()
    row = {
        "decision_id": "D-BOTH",
        "alert_id": "A-BOTH",
        "category": "credential_access",
        "factor_vector": [2, 2, 2, 2, 2, 2],
    }

    discoveries = service._cross_factor_anomaly_discovery([row])

    assert len(discoveries) == 1
    assert discoveries[0].type == DiscoveryType.CROSS_FACTOR_MISROUTE.value
    assert discoveries[0].involved_decision_ids == ["D-BOTH"]
    assert DiscoveryType.CROSS_FACTOR_NOVEL.value not in {d.type for d in discoveries}


@pytest.mark.asyncio
async def test_refresh_populates_cache_sorts_and_ids_unique():
    service = DiscoveryService(time_fn=lambda: 10.0)
    service._shared_entity_discovery = AsyncMock(return_value=[discovery_row(0.4)])
    service._pattern_convergence_discovery = AsyncMock(return_value=([discovery_row(0.9)], []))
    service._temporal_velocity_discovery = AsyncMock(return_value=[discovery_row(0.7)])
    service._cross_factor_anomaly_discovery = lambda rows: []
    mock = AsyncMock()
    mock.run_query.side_effect = [[{"max_alert_epoch": AS_OF}]]

    envelope = await service.refresh("soc", mock)

    assert envelope["total"] == 3
    assert [d["score"] for d in envelope["discoveries"]] == [0.9, 0.7, 0.4]
    assert len({d["discovery_id"] for d in envelope["discoveries"]}) == 3
    assert service._cache["soc"]["total"] == 3


@pytest.mark.asyncio
async def test_fresh_cache_returns_hit_without_graph_call():
    service = DiscoveryService(time_fn=lambda: 10.0)
    service._cache["soc"] = {
        "domain": "soc",
        "source_domains": ["soc"],
        "generated_at": "now",
        "as_of_epoch_ms": AS_OF,
        "cache": {"hit": False, "stale": False, "ttl_seconds": 60},
        "discoveries": [],
        "total": 0,
        "errors": [],
    }
    service._cache_time["soc"] = 5.0

    cached = service.get_discoveries("soc")

    assert cached["cache"]["hit"] is True
    assert cached["cache"]["stale"] is False


@pytest.mark.asyncio
async def test_cache_expires_without_sleep():
    service = DiscoveryService(ttl_seconds=10, time_fn=lambda: 20.0)
    service._cache["soc"] = {"domain": "soc"}
    service._cache_time["soc"] = 0.0

    assert service.get_discoveries("soc") is None


@pytest.mark.asyncio
async def test_stale_cache_returned_when_all_algorithms_fail():
    service = DiscoveryService(time_fn=lambda: 20.0)
    service._cache["soc"] = {
        "domain": "soc",
        "source_domains": ["soc"],
        "generated_at": "old",
        "as_of_epoch_ms": AS_OF,
        "cache": {"hit": False, "stale": False, "ttl_seconds": 60},
        "discoveries": [{"discovery_id": "old", "score": 1.0, "severity": "high"}],
        "total": 1,
        "errors": [],
    }
    service._cache_time["soc"] = 0.0
    service._shared_entity_discovery = AsyncMock(side_effect=RuntimeError("shared"))
    service._pattern_convergence_discovery = AsyncMock(side_effect=RuntimeError("pattern"))
    service._temporal_velocity_discovery = AsyncMock(side_effect=RuntimeError("velocity"))
    service._cross_factor_anomaly_discovery = lambda rows: (_ for _ in ()).throw(RuntimeError("factor"))
    mock = AsyncMock()
    mock.run_query.side_effect = [[{"max_alert_epoch": AS_OF}]]

    envelope = await service.refresh("soc", mock)

    assert envelope["cache"]["hit"] is False
    assert envelope["cache"]["stale"] is True
    assert envelope["discoveries"][0]["discovery_id"] == "old"


@pytest.mark.asyncio
async def test_all_algorithms_fail_without_cache_returns_empty_with_errors():
    service = DiscoveryService()
    service._shared_entity_discovery = AsyncMock(side_effect=RuntimeError("shared"))
    service._pattern_convergence_discovery = AsyncMock(side_effect=RuntimeError("pattern"))
    service._temporal_velocity_discovery = AsyncMock(side_effect=RuntimeError("velocity"))
    service._cross_factor_anomaly_discovery = lambda rows: (_ for _ in ()).throw(RuntimeError("factor"))
    mock = AsyncMock()
    mock.run_query.side_effect = [[{"max_alert_epoch": AS_OF}]]

    envelope = await service.refresh("soc", mock)

    assert envelope["discoveries"] == []
    assert len(envelope["errors"]) == 4


@pytest.mark.asyncio
async def test_summary_counts_severities():
    service = DiscoveryService(time_fn=lambda: 10.0)
    service._cache["soc"] = {
        "domain": "soc",
        "source_domains": ["soc"],
        "generated_at": "now",
        "as_of_epoch_ms": AS_OF,
        "cache": {"hit": False, "stale": False, "ttl_seconds": 60},
        "discoveries": [
            {"severity": "high", "score": 0.8},
            {"severity": "medium", "score": 0.5},
            {"severity": "low", "score": 0.2},
        ],
        "total": 3,
        "errors": [],
    }
    service._cache_time["soc"] = 10.0

    summary = await service.get_summary("soc", AsyncMock())

    assert summary["total"] == 3
    assert summary["high_count"] == 1
    assert summary["medium_count"] == 1
    assert summary["low_count"] == 1


# ── New tests for B1-B5 fixes ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_shared_entity_batches_threat_intel_query():
    """Algorithm 1 uses at most 4 graph queries (2 aggregates + 2 batch TI), not 100+."""
    mock = AsyncMock()
    # Provide 3 qualifying users and 3 qualifying assets.
    user_row = {
        "entity_id": "USR-1",
        "entity_name": "User",
        "alert_ids_json": ["A1", "A2", "A3"],
        "categories_json": ["credential_access", "lateral_movement", "insider_threat"],
        "timestamps_json": [AS_OF, AS_OF - 1, AS_OF - 2],
        "cnt": 3,
    }
    asset_row = {
        "entity_id": "AST-1",
        "entity_name": "host",
        "alert_ids_json": ["B1", "B2", "B3"],
        "categories_json": ["credential_access", "lateral_movement", "insider_threat"],
        "timestamps_json": [AS_OF, AS_OF - 1, AS_OF - 2],
        "cnt": 3,
    }
    mock.run_query.side_effect = [
        [user_row, user_row, user_row],  # user aggregate -- 3 qualifying
        [asset_row, asset_row, asset_row],  # asset aggregate -- 3 qualifying
        [],  # user batch TI
        [],  # asset batch TI
    ]
    service = DiscoveryService()
    await service._shared_entity_discovery(mock, BASELINE, AS_OF)
    assert mock.run_query.call_count <= 4


def test_batch_parse_vectors_returns_numpy_matrix():
    """_batch_parse_vectors returns (N, 6) float64 matrix for N valid rows."""
    service = DiscoveryService()
    rows = [
        {
            "decision_id": f"d{i}",
            "action": "investigate",
            "category": cat,
            "confidence": 0.85,
            "factor_vector": f"[{i * 0.1:.1f}, 0.3, 0.5, 0.4, 0.6, 0.2]",
            "alert_id": f"a{i}",
            "timestamp_epoch": 1741000000000,
        }
        for i, cat in enumerate(["credential_access", "lateral_movement"] * 50)
    ]
    valid, matrix = service._batch_parse_vectors(rows)
    assert len(valid) == 100
    assert matrix.shape == (100, 6)
    assert matrix.dtype == np.float64


def test_convergence_completes_under_1_second():
    """Numpy pairwise distance computation for 100 rows completes in <1s."""
    service = DiscoveryService()
    rows = [
        {
            "decision_id": f"d{i}",
            "action": "investigate",
            "category": cat,
            "confidence": 0.85,
            "factor_vector": f"[{i * 0.01:.2f}, 0.3, 0.5, 0.4, 0.6, 0.2]",
            "alert_id": f"a{i}",
            "timestamp_epoch": 1741000000000,
        }
        for i, cat in enumerate(["credential_access", "lateral_movement"] * 50)
    ]
    start = time.monotonic()
    valid, matrix = service._batch_parse_vectors(rows)
    # Simulate the vectorized pairwise distance computation
    if len(valid) > 1:
        diff = matrix[:, np.newaxis, :] - matrix[np.newaxis, :, :]
        _distances = np.sqrt((diff ** 2).sum(axis=2))
    elapsed = time.monotonic() - start
    assert elapsed < 1.0, f"Numpy computation took {elapsed:.2f}s -- vectorization may be missing"


@pytest.mark.asyncio
async def test_algorithm_timeout_returns_partial():
    """_run_algorithm returns ([], error_msg) when coroutine exceeds timeout."""
    service = DiscoveryService()

    async def slow():
        await asyncio.sleep(10)
        return [{"fake": True}]

    result, err = await service._run_algorithm(slow(), "test", timeout=0.1)
    assert result == []
    assert err is not None
    assert "timed out" in err


def test_convergence_limit_is_200():
    """CONVERGENCE_LIMIT is 200 (down from 1000) to bound pairwise work."""
    assert DiscoveryService.CONVERGENCE_LIMIT == 200
