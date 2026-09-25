from __future__ import annotations

from contextlib import asynccontextmanager
import importlib.util
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import numpy as np
import pytest

from app.domains.soc.config import SCORER_ACTIONS, SOC_CATEGORIES, SOCDomainConfig
from app.models.schemas import OutcomeRequest
from app.routers import triage
from app.services import learning_health
from app.services.learning_health import LearningHealthMonitor
from app.main import app
from app.services.triage_providers import get_learning_policy


def _load_smoke_script():
    script = (
        __import__("pathlib").Path(__file__).resolve().parents[2]
        / "scripts"
        / "soc_c9b_live_age_smoke.py"
    )
    spec = importlib.util.spec_from_file_location("soc_c9b_live_age_smoke", script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_seed_script():
    script = (
        __import__("pathlib").Path(__file__).resolve().parents[2]
        / "scripts"
        / "soc_c9b_seed_alerts.py"
    )
    spec = importlib.util.spec_from_file_location("soc_c9b_seed_alerts", script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _C9BScorer:
    n_categories = len(SOC_CATEGORIES)

    def __init__(self) -> None:
        self.reestimate_calls = 0
        self.centroids = np.zeros((len(SOC_CATEGORIES), len(SCORER_ACTIONS), 6), dtype=np.float64)
        self.centroids[0, 0] = np.array([0.25, 0.35, 0.45, 0.55, 0.65, 0.75])

    def reestimate_dk(self) -> None:
        self.reestimate_calls += 1

    def get_phase(self, _category_index: int) -> str:
        return "MEAN_CONVERGENCE"

    def get_dk_weights(self, _category_index: int):
        return np.ones(6, dtype=np.float64)


class _LearningState:
    decision_count = 400

    def update(self, **_kwargs):
        return SimpleNamespace(centroid_update=None)


class _LearningPolicy:
    def __init__(self, enabled: bool):
        self._enabled = enabled

    def enabled(self) -> bool:
        return self._enabled


@pytest.mark.asyncio
@pytest.mark.age
@pytest.mark.parametrize("soc_triage_harness", ["age"], indirect=True)
async def test_soc_c9b_full_flow_writes_all_three_l5_types(monkeypatch, soc_triage_harness, age_graph):
    store = age_graph.store
    scorer = _C9BScorer()
    soc_triage_harness.add_decision(
        decision_id="DEC-C9B",
        category=SOC_CATEGORIES[0],
        action="escalate",
        confidence=0.9,
        factors={f"f{i}": value for i, value in enumerate([0.2, 0.3, 0.4, 0.5, 0.6, 0.7])},
        factor_vector="[0.2, 0.3, 0.4, 0.5, 0.6, 0.7]",
        alert_type="anomalous_login",
    )
    for category in SOC_CATEGORIES:
        for _ in range(10):
            age_graph.decision(category=category, correct=True)

    @asynccontextmanager
    async def fake_acquire_scorer():
        yield scorer

    monkeypatch.setitem(app.dependency_overrides, get_learning_policy, lambda: _LearningPolicy(True))
    monkeypatch.setattr(triage, "get_feedback_status", lambda _alert_id: {"has_feedback": False})
    monkeypatch.setattr(triage, "get_learning_state", lambda: _LearningState())
    monkeypatch.setattr(triage, "save_learning_state", lambda: None)
    monkeypatch.setattr(triage.event_bus, "emit", AsyncMock())
    monkeypatch.setattr(
        triage,
        "process_outcome",
        lambda **_kwargs: SimpleNamespace(
            model_dump=lambda: {"graph_updates": [], "consequence": "ok"},
            graph_updates=[],
            consequence="ok",
        ),
    )
    monkeypatch.setattr("app.framework.audit.record_outcome", AsyncMock(return_value=None))
    monkeypatch.setattr("app.services.shadow_runner.fill_shadow_outcome", lambda *_args: None)
    monkeypatch.setattr("app.services.gae_state._learning_store", store)
    monkeypatch.setattr("app.services.gae_state.acquire_scorer", fake_acquire_scorer)
    monkeypatch.setattr("app.services.gae_state.get_profile_scorer", lambda: scorer)
    monkeypatch.setattr("app.services.gae_state.get_soc_centroid", lambda *_args: [0.0] * 6)
    monkeypatch.setattr(
        "app.services.gae_state.guarded_update",
        lambda *_args, **_kwargs: SOCDomainConfig().build_profile_scorer().update(
            np.array([0.2, 0.3, 0.4, 0.1, 0.5, 0.6]), 0, 0, True,
        ),
    )

    original_evaluate = LearningHealthMonitor.evaluate

    async def evaluate_with_real_l5(_graph_service):
        return await original_evaluate(_graph_service)

    monkeypatch.setattr(
        "app.services.learning_health.get_learning_state",
        lambda: _LearningState(),
    )
    monkeypatch.setattr("app.services.learning_health.get_learning_store", lambda: store)
    monkeypatch.setattr(
        "app.services.learning_health.LearningHealthMonitor.evaluate",
        evaluate_with_real_l5,
    )

    response = await triage.report_decision_outcome(
        OutcomeRequest(
            alert_id="ALERT-C9B",
            decision_id="DEC-C9B",
            outcome="correct",
            analyst_action="escalate",
        )
    )

    assert response["l5_centroid_persisted"] is True
    assert response["l5_shaped_by_attempted"] is True
    assert response["l5_persistence_skipped_reason"] is None
    assert response["l5_persistence"]["l5_persistence_source"] == "profile_scorer"
    assert "dk_weights" not in response
    assert "welford_state" not in response
    # The outcome route persists the centroid through the scorer's
    # authoritative GraphStore; the learning store captures DK/conservation
    # artifacts separately.
    persisted = age_graph.reopen_store()
    assert persisted.get_centroids("soc")
    dk = persisted.get_dk_weights("soc")
    assert dk is not None and dk["welford_state"] is not None
    conservation = persisted.get_conservation_state("soc")
    assert conservation is not None
    assert conservation["categories_total"] == 6
    assert conservation["categories_with_data"] == len(SOC_CATEGORIES)
    assert scorer.reestimate_calls == 1


@pytest.mark.asyncio
@pytest.mark.age
async def test_soc_c9b_conservation_excludes_no_domain_route_rows(monkeypatch, age_graph):
    age_graph.decision(category=SOC_CATEGORIES[0], correct=True)
    age_graph.decision(category=SOC_CATEGORIES[1], correct=False, was_override=True)
    age_graph.node("Decision", decision_id="legacy", category=SOC_CATEGORIES[2], correct=True, outcome="correct", verified_at_epoch=1)
    age_graph.decision(domain="s2p", category=SOC_CATEGORIES[3], correct=True)
    graph = age_graph.client
    monkeypatch.setattr(learning_health, "get_learning_state", lambda: _LearningState())
    monkeypatch.setattr(learning_health, "get_learning_store", lambda: None)

    result = await LearningHealthMonitor.evaluate(graph)

    assert result["components"]["categories_with_data"] == 2
    assert result["components"]["alpha"] == pytest.approx(2 / 6, abs=1e-4)
    assert result["components"]["V"] == pytest.approx(2.0)
    assert result["components"]["q"] == pytest.approx(0.5)


def test_soc_c9b_smoke_script_argument_parsing_and_redaction():
    smoke = _load_smoke_script()

    args = smoke.parse_args(["--loops", "5", "--alert-prefix", "C9B-SOC", "--start-index", "7", "--readback", "--json"])

    assert args.loops == 5
    assert args.alert_prefix == "C9B-SOC"
    assert args.start_index == 7
    assert args.readback is True
    assert smoke.redact_dsn("postgresql://postgres:secret@localhost/db") == (
        "postgresql://postgres:***@localhost/db"
    )


def test_soc_c9b_smoke_script_readiness_classification_complete():
    smoke = _load_smoke_script()
    readback = {
        "L5Centroid": {"soc": 1},
        "L5DKWeight": {"soc": 1},
        "L5ConservationState": {"soc": {"count": 1, "status": "GREEN"}},
        "Welford": {"soc": {"present": True}},
        "SHAPED_BY": {"soc": 1},
        "TRIGGERED_BY": {},
        "samples": {
            "conservation": [{"theta_min": 0.25}],
            "decisions": [{"domain": "soc", "count": 210}],
        },
    }

    verdict, missing, triggered = smoke.classify_readiness(readback)

    assert verdict == "READY_FOR_C9B_PROOF"
    assert missing == []
    assert triggered == "transition not exercised"


def test_soc_c9b_smoke_script_extracts_live_analyze_response_shape():
    smoke = _load_smoke_script()
    body = {
        "recommendation": {"action": "investigate", "decision_id": "DEC-1"},
        "gae_scoring": {"decision_id": "DEC-1"},
    }

    assert smoke.extract_decision_id(body) == "DEC-1"
    assert smoke.extract_recommended_action(body) == "investigate"


def test_soc_analyze_creates_decision_with_domain_soc():
    source = __import__("inspect").getsource(triage.analyze_alert)

    assert "CREATE (d:Decision" in source
    assert "decision_id:" in source
    assert "domain:" in source
    assert "'soc'" in source
    assert "factor_vector:" in source
    assert "outcome:" in source


def test_soc_centroid_shaped_by_can_target_route_created_decision():
    analyze_source = __import__("inspect").getsource(triage.analyze_alert)
    outcome_source = __import__("inspect").getsource(triage.report_decision_outcome)

    assert "domain:" in analyze_source and "'soc'" in analyze_source
    assert '"caused_by_decision_id": request.decision_id' in outcome_source
    assert "_persist_soc_outcome_and_centroid(" in outcome_source


def test_soc_c9b_smoke_script_missing_cell_classification():
    smoke = _load_smoke_script()
    readback = {
        "L5Centroid": {"soc": 1},
        "L5DKWeight": {},
        "L5ConservationState": {"soc": {"count": 1, "status": "GREEN"}},
        "Welford": {"soc": {"present": False}},
        "SHAPED_BY": {"soc": 1},
        "TRIGGERED_BY": {},
        "samples": {
            "conservation": [{"theta_min": 0.25}],
            "decisions": [{"domain": "soc", "count": 210}],
        },
    }

    verdict, missing, _triggered = smoke.classify_readiness(readback)

    assert verdict == "PARTIAL_SEE_MISSING"
    assert {item["cell"] for item in missing} == {"L5DKWeight", "Welford"}


def test_soc_c9b_smoke_script_database_url_preference_and_dry_run(monkeypatch):
    monkeypatch.delenv("AGE_GRAPH_NAME", raising=False)
    smoke = _load_smoke_script()
    dsn, source = smoke.choose_database_url(
        "postgresql://postgres:secret@localhost/db",
        "postgresql://postgres@localhost/db",
    )
    assert dsn == "postgresql://postgres:secret@localhost/db"
    assert "ignored passwordless GRAPH_DSN" in source

    args = smoke.parse_args(["--dry-run", "--database-url", dsn])
    summary = smoke.build_summary(args)
    assert summary["verdict"] == "PARTIAL_SEE_MISSING"
    assert summary["missing_cells"][0]["cell"] == "dry_run"
    assert args.graph_name == "soc_graph_c9b"


def test_soc_c9b_seed_and_smoke_default_to_fresh_graph(monkeypatch):
    monkeypatch.delenv("AGE_GRAPH_NAME", raising=False)
    seed = _load_seed_script()
    smoke = _load_smoke_script()

    assert seed.parse_args([]).graph_name == "soc_graph_c9b"
    assert smoke.parse_args([]).graph_name == "soc_graph_c9b"


def test_soc_c9b_seed_and_smoke_honor_graph_override():
    seed = _load_seed_script()
    smoke = _load_smoke_script()

    assert seed.parse_args(["--graph-name", "custom_graph"]).graph_name == "custom_graph"
    assert smoke.parse_args(["--graph-name", "custom_graph"]).graph_name == "custom_graph"


def test_soc_c9b_smoke_script_has_no_direct_l5_write_calls():
    script = (
        __import__("pathlib").Path(__file__).resolve().parents[2]
        / "scripts"
        / "soc_c9b_live_age_smoke.py"
    )
    source = script.read_text(encoding="utf-8")

    assert ".update_centroid(" not in source
    assert ".update_dk_weights(" not in source
    assert ".update_conservation_state(" not in source
    assert "_l5_upsert_current" not in source


def test_soc_c9b_smoke_script_alert_not_found_guidance(monkeypatch):
    smoke = _load_smoke_script()

    def fake_route_loops(*_args, **_kwargs):
        return smoke.RouteResult(
            attempted=2,
            score_ok=0,
            outcome_ok=0,
            failures=["analyze 0: HTTP 404 {\"detail\":\"Alert C9B-SOC-0001 not found\"}"],
        )

    monkeypatch.setattr(smoke, "run_route_loops", fake_route_loops)
    args = smoke.parse_args(["--loops", "2", "--database-url", "postgresql://postgres:secret@localhost/db"])
    summary = smoke.build_summary(args)

    assert summary["verdict"] == "BLOCKED_ENV"
    assert "soc_c9b_seed_alerts.py --count 2 --prefix C9B-SOC" in summary["next_action"]


def test_soc_c9b_smoke_skips_routing_actions_until_valid_outcomes(monkeypatch):
    smoke = _load_smoke_script()
    posted: list[tuple[str, dict]] = []

    class _Response:
        def __init__(self, status_code: int, body: dict):
            self.status_code = status_code
            self._body = body
            self.text = str(body)

        def json(self):
            return self._body

    class _Client:
        analyze_calls = 0

        def __init__(self, *_args, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def post(self, path: str, json: dict):
            posted.append((path, json))
            if path == "/api/alert/analyze":
                self.__class__.analyze_calls += 1
                action = "refer_to_analyst" if self.__class__.analyze_calls == 1 else "monitor"
                return _Response(200, {"recommendation": {"action": action, "decision_id": f"DEC-{self.__class__.analyze_calls}"}})
            return _Response(200, {"status": "success"})

    monkeypatch.setitem(sys.modules, "app.main", SimpleNamespace(app=object()))
    monkeypatch.setattr("fastapi.testclient.TestClient", _Client)

    result = smoke.run_route_loops(loops=1, max_attempts=3)

    assert result.attempted == 2
    assert result.score_ok == 2
    assert result.outcome_ok == 1
    assert result.valid_scorer_action_outcomes == 1
    assert result.skipped_routing_actions == 1
    assert result.invalid_actions == {"refer_to_analyst": 1}
    assert posted[-1][1]["analyst_action"] == "monitor"



def test_soc_c9b_seed_script_argument_parsing_redaction_and_ids():
    seed = _load_seed_script()

    args = seed.parse_args(["--count", "3", "--prefix", "C9B-SOC", "--dry-run", "--json"])

    assert args.count == 3
    assert args.prefix == "C9B-SOC"
    assert seed.deterministic_alert_id("C9B-SOC", 1) == "C9B-SOC-0001"
    assert seed.deterministic_alert_id("C9B-SOC", 210) == "C9B-SOC-0210"
    assert seed.redact_dsn("postgresql://postgres:secret@localhost/db") == (
        "postgresql://postgres:***@localhost/db"
    )


@pytest.mark.asyncio
async def test_soc_c9b_seed_script_dry_run_writes_nothing():
    seed = _load_seed_script()
    client = AsyncMock()

    summary = await seed.seed_alerts(
        client,
        count=2,
        prefix="C9B-SOC",
        graph_name="soc_graph",
        database_url="postgresql://postgres:secret@localhost/db",
        dsn_source="DATABASE_URL",
        dry_run=True,
    )

    assert summary.planned == 2
    assert summary.created == 0
    assert summary.existing == 0
    client.run_query.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.age
async def test_soc_c9b_seed_script_creates_only_input_nodes_and_edges(age_graph):
    seed = _load_seed_script()
    client = age_graph.client
    client.run_query = AsyncMock(wraps=client.run_query)

    summary = await seed.seed_alerts(
        client,
        count=1,
        prefix="C9B-SOC",
        graph_name="soc_graph",
        database_url="postgresql://postgres:secret@localhost/db",
        dsn_source="DATABASE_URL",
        dry_run=False,
    )
    joined = "\n".join(c.args[0] for c in client.run_query.call_args_list)

    assert summary.created == 1
    assert age_graph.query("MATCH (a:Alert) RETURN count(a) AS n") == [{"n": 1}]
    assert age_graph.query("MATCH (:Alert)-[r]->() RETURN count(r) AS n")[0]["n"] >= 2
    assert age_graph.query("MATCH (d:Decision) RETURN count(d) AS n") == [{"n": 0}]
    assert "CREATE (a:Alert" in joined
    assert "CREATE (n:User" in joined
    assert "CREATE (n:Asset" in joined
    assert "INVOLVES" in joined
    assert "DETECTED_ON" in joined
    assert "Decision" not in joined
    assert "Outcome" not in joined
    assert "SHAPED_BY" not in joined
    assert "TRIGGERED_BY" not in joined


def test_soc_c9b_seed_script_safety_source():
    script = (
        __import__("pathlib").Path(__file__).resolve().parents[2]
        / "scripts"
        / "soc_c9b_seed_alerts.py"
    )
    source = script.read_text(encoding="utf-8")

    assert "update_centroid" not in source
    assert "update_dk_weights" not in source
    assert "update_conservation_state" not in source
    assert "L5Centroid" not in source
    assert "L5DKWeight" not in source
    assert "L5ConservationState" not in source
    assert "verified_at_epoch" not in source
    assert "outcome" not in source
