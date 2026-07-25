from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app.domains.soc.config import SOC_CATEGORIES
from app.services import learning_health
from app.services.learning_health import LearningHealthMonitor


def _history(count: int, *, outcome: int = 1) -> list:
    start = datetime(2026, 1, 1, 0, 0, 0)
    return [
        SimpleNamespace(
            alpha_effective=0.01,
            outcome=outcome,
            timestamp=(start + timedelta(minutes=i)).isoformat(),
        )
        for i in range(count)
    ]


class _State:
    def __init__(self, count: int = 400):
        self.history = _history(count)
        self.decision_count = count


class _SocConservationGraph:
    def __init__(self, rows: list[dict]):
        self.rows = rows
        self.queries: list[str] = []

    async def run_query(self, query: str) -> list[dict]:
        self.queries.append(query)
        if "MATCH (h:HealthLog)" in query:
            return [{"red_days": 0}]
        if "MATCH (d:Decision)" in query and "RETURN d.category AS category" in query:
            return self._verified_soc_category_rows()
        return []

    def _verified_soc_category_rows(self) -> list[dict]:
        grouped: dict[str, dict[str, int | str]] = {}
        for row in self.rows:
            domain = row.get("domain")
            if domain is not None and domain != "soc":
                continue
            category = row.get("category")
            if category not in SOC_CATEGORIES:
                continue
            if row.get("verified_at_epoch") is None:
                continue
            if row.get("status") is None and row.get("outcome") is None:
                continue

            bucket = grouped.setdefault(
                str(category),
                {"category": str(category), "verified": 0, "correct": 0, "overrides": 0},
            )
            bucket["verified"] = int(bucket["verified"]) + int(row.get("verified", 1) or 0)
            bucket["correct"] = int(bucket["correct"]) + int(row.get("correct", 0) or 0)
            bucket["overrides"] = int(bucket["overrides"]) + int(row.get("overrides", 0) or 0)
        return list(grouped.values())


class _Store:
    def __init__(self):
        self.updates: list[dict] = []

    def get_conservation_state(self, domain: str) -> None:
        assert domain == "soc"
        return None

    def update_conservation_state(self, **kwargs) -> None:
        self.updates.append(kwargs)


def _row(
    category: str,
    verified: int,
    correct: int,
    overrides: int = 0,
    *,
    domain: str | None = None,
    verified_at_epoch: int | None = 1,
    outcome: str | None = "verified",
    status: str | None = None,
) -> dict:
    return {
        "domain": domain,
        "category": category,
        "verified_at_epoch": verified_at_epoch,
        "outcome": outcome,
        "status": status,
        "verified": verified,
        "correct": correct,
        "overrides": overrides,
    }


@pytest.mark.asyncio
async def test_soc_conservation_alpha_uses_category_coverage_one_of_six():
    graph = _SocConservationGraph([_row(SOC_CATEGORIES[0], 7, 6)])
    comps = await LearningHealthMonitor._apply_soc_conservation_components({}, graph)

    assert comps["categories_total"] == 6
    assert comps["categories_with_data"] == 1
    assert comps["alpha"] == pytest.approx(1 / 6)


@pytest.mark.asyncio
async def test_soc_conservation_alpha_uses_category_coverage_multiple_categories():
    graph = _SocConservationGraph([
        _row(SOC_CATEGORIES[0], 10, 9),
        _row(SOC_CATEGORIES[1], 20, 18),
        _row(SOC_CATEGORIES[2], 30, 24),
    ])
    comps = await LearningHealthMonitor._apply_soc_conservation_components({}, graph)

    assert comps["categories_with_data"] == 3
    assert comps["alpha"] == pytest.approx(0.5)


@pytest.mark.asyncio
async def test_soc_conservation_alpha_full_coverage_is_one():
    graph = _SocConservationGraph([
        _row(category, 5, 4) for category in SOC_CATEGORIES
    ])
    comps = await LearningHealthMonitor._apply_soc_conservation_components({}, graph)

    assert comps["categories_with_data"] == 6
    assert comps["alpha"] == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_soc_conservation_duplicate_category_not_double_counted():
    graph = _SocConservationGraph([_row(SOC_CATEGORIES[0], 25, 20)])
    comps = await LearningHealthMonitor._apply_soc_conservation_components({}, graph)

    assert comps["verified_decisions"] == 25
    assert comps["categories_with_data"] == 1
    assert comps["alpha"] == pytest.approx(1 / 6)


@pytest.mark.asyncio
async def test_soc_conservation_verified_only_count_filter():
    graph = _SocConservationGraph([_row(SOC_CATEGORIES[0], 12, 9)])
    comps = await LearningHealthMonitor._apply_soc_conservation_components({}, graph)

    assert comps["V"] == 12.0
    query = graph.queries[0]
    assert "d.verified_at_epoch IS NOT NULL" in query
    assert "d.status IS NOT NULL OR d.outcome IS NOT NULL" in query


@pytest.mark.asyncio
async def test_soc_conservation_ghost_or_unverified_decisions_excluded():
    graph = _SocConservationGraph([
        _row(SOC_CATEGORIES[0], 12, 9),
        _row("unknown_or_ghost_category", 999, 999),
        _row(SOC_CATEGORIES[1], 999, 999, verified_at_epoch=None),
        _row(SOC_CATEGORIES[2], 999, 999, outcome=None, status=None),
    ])
    comps = await LearningHealthMonitor._apply_soc_conservation_components({}, graph)

    assert comps["verified_decisions"] == 12
    assert comps["correct_verified_decisions"] == 9
    assert comps["categories_with_data"] == 1


@pytest.mark.asyncio
async def test_soc_verified_query_counts_route_created_decisions_without_domain():
    graph = _SocConservationGraph([
        _row(SOC_CATEGORIES[0], 1, 1, domain=None, verified_at_epoch=123, outcome="correct"),
        _row(SOC_CATEGORIES[1], 1, 0, domain=None, verified_at_epoch=124, outcome="incorrect"),
    ])

    comps = await LearningHealthMonitor._apply_soc_conservation_components({}, graph)

    assert comps["V"] == 2.0
    assert comps["q"] == pytest.approx(0.5)
    assert comps["categories_with_data"] == 2
    assert comps["alpha"] == pytest.approx(2 / 6)


@pytest.mark.asyncio
async def test_soc_verified_query_excludes_non_soc_domain_even_known_category():
    graph = _SocConservationGraph([
        _row(SOC_CATEGORIES[0], 1, 1, domain=None, verified_at_epoch=123, outcome="correct"),
        _row(SOC_CATEGORIES[1], 99, 99, domain="trading", verified_at_epoch=124, outcome="correct"),
    ])

    comps = await LearningHealthMonitor._apply_soc_conservation_components({}, graph)

    assert comps["V"] == 1.0
    assert comps["categories_with_data"] == 1


@pytest.mark.asyncio
async def test_soc_verified_query_excludes_no_domain_unknown_category():
    graph = _SocConservationGraph([
        _row("not_a_soc_category", 99, 99, domain=None, verified_at_epoch=123, outcome="correct"),
    ])

    comps = await LearningHealthMonitor._apply_soc_conservation_components({}, graph)

    assert comps["V"] == 0.0
    assert comps["categories_with_data"] == 0
    assert comps["alpha"] == 0.0


@pytest.mark.asyncio
async def test_soc_verified_query_excludes_no_domain_unverified_rows():
    graph = _SocConservationGraph([
        _row(SOC_CATEGORIES[0], 99, 99, domain=None, verified_at_epoch=None, outcome="correct"),
        _row(SOC_CATEGORIES[1], 99, 99, domain=None, verified_at_epoch=123, outcome=None, status=None),
    ])

    comps = await LearningHealthMonitor._apply_soc_conservation_components({}, graph)

    assert comps["V"] == 0.0
    assert comps["categories_with_data"] == 0


@pytest.mark.asyncio
async def test_soc_verified_query_shape_uses_exact_domain_and_active_filter():
    graph = _SocConservationGraph([_row(SOC_CATEGORIES[0], 1, 1)])

    await LearningHealthMonitor._apply_soc_conservation_components({}, graph)

    query = graph.queries[0]
    assert "d.domain = 'soc'" in query
    assert "(d.archived IS NULL OR d.archived <> true)" in query
    assert "d.category IN [" in query
    assert "credential_access" in query
    assert "d.verified_at_epoch IS NOT NULL" in query
    assert "d.status IS NOT NULL OR d.outcome IS NOT NULL" in query


@pytest.mark.asyncio
async def test_soc_conservation_q_uses_correct_over_verified():
    graph = _SocConservationGraph([_row(SOC_CATEGORIES[0], 20, 15)])
    comps = await LearningHealthMonitor._apply_soc_conservation_components({}, graph)

    assert comps["q"] == pytest.approx(0.75)


@pytest.mark.asyncio
async def test_soc_conservation_theta_min_formula_uses_correct_alpha_q_v(monkeypatch):
    graph = _SocConservationGraph([
        _row(category, 50, 40) for category in SOC_CATEGORIES
    ])
    monkeypatch.setattr(learning_health, "get_learning_state", lambda: _State(400))
    monkeypatch.setattr(learning_health, "get_learning_store", lambda: None)

    result = await LearningHealthMonitor.evaluate(graph)

    assert result["components"]["alpha"] == pytest.approx(1.0)
    assert result["components"]["q"] == pytest.approx(0.8)
    assert result["components"]["V"] == pytest.approx(300.0)
    assert result["signal"] == pytest.approx(1.0 * 0.8 * 300.0)
    assert result["theta_min"] == pytest.approx(23.53 / 300.0, rel=1e-4)


@pytest.mark.asyncio
async def test_soc_l5_conservation_persists_real_categories_with_data(monkeypatch):
    graph = _SocConservationGraph([
        _row(SOC_CATEGORIES[0], 50, 40),
        _row(SOC_CATEGORIES[1], 50, 40),
        _row(SOC_CATEGORIES[2], 50, 40),
    ])
    store = _Store()
    monkeypatch.setattr(learning_health, "get_learning_state", lambda: _State(400))
    monkeypatch.setattr(learning_health, "get_learning_store", lambda: store)

    result = await LearningHealthMonitor.evaluate(graph)

    assert result["components"]["categories_total"] == 6
    assert result["components"]["categories_with_data"] == 3
    assert len(store.updates) == 1
    assert store.updates[0]["categories_total"] == 6
    assert store.updates[0]["categories_with_data"] == 3
    assert store.updates[0]["alpha"] == pytest.approx(0.5)


@pytest.mark.asyncio
async def test_soc_l5_conservation_does_not_invent_full_coverage(monkeypatch):
    graph = _SocConservationGraph([_row(SOC_CATEGORIES[0], 50, 40)])
    store = _Store()
    monkeypatch.setattr(learning_health, "get_learning_state", lambda: _State(400))
    monkeypatch.setattr(learning_health, "get_learning_store", lambda: store)

    await LearningHealthMonitor.evaluate(graph)

    assert store.updates[0]["categories_with_data"] == 1
    assert store.updates[0]["categories_with_data"] < store.updates[0]["categories_total"]


@pytest.mark.asyncio
async def test_soc_conservation_existing_response_shape_unchanged(monkeypatch):
    graph = _SocConservationGraph([_row(SOC_CATEGORIES[0], 50, 40)])
    monkeypatch.setattr(learning_health, "get_learning_state", lambda: _State(400))
    monkeypatch.setattr(learning_health, "get_learning_store", lambda: None)

    result = await LearningHealthMonitor.evaluate(graph)

    assert "components" in result
    assert "conservation" in result
    assert "status" in result
    assert "l5" not in result
    assert "categories_with_data" not in result


@pytest.mark.asyncio
async def test_soc_conservation_complacency_advisory_unchanged(monkeypatch):
    graph = _SocConservationGraph([
        _row(category, 40, 35, overrides=0) for category in SOC_CATEGORIES
    ])
    monkeypatch.setattr(learning_health, "get_learning_state", lambda: _State(400))
    monkeypatch.setattr(learning_health, "get_learning_store", lambda: None)

    result = await LearningHealthMonitor.evaluate(graph)

    assert result["components"]["override_rate"] == 0.0
    assert result["complacency_advisory"] is True
    assert result["status"] in {"GREEN", "AMBER", "RED"}
