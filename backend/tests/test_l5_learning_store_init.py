from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


class FakeLearningState:
    def __init__(self):
        self.decision_count = 0
        self.profile_scorer = None

    def attach_profile_scorer(self, scorer):
        self.profile_scorer = scorer


class FakeScorer:
    eta_override = 0.01
    actions = ["escalate"]
    tau = 0.1

    def __init__(self):
        self.centroids = np.array([[0.0, 1.0]])


class FakeSOCConfig:
    def build_profile_scorer(self):
        return FakeScorer()


@pytest.fixture
def isolated_gae_state(monkeypatch, tmp_path):
    from app.domains.soc import config as soc_config
    from app.services import gae_state
    from copilot_sdk.config import GraphConfig
    from copilot_sdk.graph import factory as graph_factory
    from copilot_sdk.graph.memory_store import InMemoryGraphStore

    monkeypatch.delenv("GRAPH_DSN", raising=False)
    monkeypatch.delenv("AGE_GRAPH_NAME", raising=False)
    monkeypatch.setattr(
        GraphConfig,
        "load",
        lambda _domain: SimpleNamespace(
            backend="sqlite",
            dsn=None,
            graph="test_graph",
            authorized="soc:test_graph",
        ),
    )
    monkeypatch.setattr(
        graph_factory,
        "create_graph_store",
        lambda **_kwargs: InMemoryGraphStore(domain="soc"),
    )
    monkeypatch.setattr(gae_state, "_learning_state", None)
    monkeypatch.setattr(gae_state, "_learning_store", None)
    monkeypatch.setattr(gae_state, "_bootstrap_metadata", None)
    monkeypatch.setattr(gae_state, "_bootstrap_result", None)
    monkeypatch.setattr(gae_state, "_STATE_PATH", tmp_path / "gae_learning_state.json")
    monkeypatch.setattr(gae_state, "_MU_ZERO_PATH", tmp_path / "iks_bootstrap_soc.json")
    monkeypatch.setattr(gae_state, "_make_fresh_state", lambda: FakeLearningState())
    monkeypatch.setattr(gae_state, "save_learning_state", lambda: None)
    monkeypatch.setattr(soc_config, "SOCDomainConfig", FakeSOCConfig)
    monkeypatch.setattr(
        gae_state,
        "bootstrap_calibration",
        lambda **kwargs: SimpleNamespace(
            n_decisions=3,
            final_drift=0.0,
            converged=True,
        ),
    )
    return gae_state


def test_get_learning_store_exists_and_defaults_none(isolated_gae_state):
    assert callable(isolated_gae_state.get_learning_store)
    assert isolated_gae_state.get_learning_store() is None


def test_init_without_graph_dsn_keeps_learning_store_none(isolated_gae_state):
    state = isolated_gae_state.init_learning_state()

    assert isolated_gae_state.get_learning_store() is None
    assert isolated_gae_state.get_learning_state() is state
    assert isolated_gae_state.get_profile_scorer() is state.profile_scorer


def test_init_with_graph_dsn_creates_learning_store_with_default_graph(isolated_gae_state, monkeypatch):
    calls = []

    class FakeAdapter:
        def __init__(self, *, dsn, graph_name):
            calls.append({"dsn": dsn, "graph_name": graph_name})

    monkeypatch.setenv("GRAPH_DSN", "postgresql://soc_user:secret@localhost/soc")
    monkeypatch.setattr(isolated_gae_state, "_load_age_learning_store_adapter", lambda: FakeAdapter)

    isolated_gae_state.init_learning_state()

    assert calls == [
        {
            "dsn": "postgresql://soc_user:secret@localhost/soc",
            "graph_name": "soc_graph",
        }
    ]
    assert isinstance(isolated_gae_state.get_learning_store(), FakeAdapter)


def test_init_with_graph_name_override(isolated_gae_state, monkeypatch):
    calls = []

    class FakeAdapter:
        def __init__(self, *, dsn, graph_name):
            calls.append({"dsn": dsn, "graph_name": graph_name})

    monkeypatch.setenv("GRAPH_DSN", "postgresql://soc_user:secret@localhost/soc")
    monkeypatch.setenv("AGE_GRAPH_NAME", "soc_l5_test_graph")
    monkeypatch.setattr(isolated_gae_state, "_load_age_learning_store_adapter", lambda: FakeAdapter)

    isolated_gae_state.init_learning_state()

    assert calls[0]["graph_name"] == "soc_l5_test_graph"


def test_adapter_failure_does_not_crash_or_leak_dsn(isolated_gae_state, monkeypatch, caplog):
    raw_dsn = "postgresql://soc_user:secret@localhost/soc"

    def fail_import():
        raise RuntimeError(f"could not connect to {raw_dsn}")

    monkeypatch.setenv("GRAPH_DSN", raw_dsn)
    monkeypatch.setattr(isolated_gae_state, "_load_age_learning_store_adapter", fail_import)

    isolated_gae_state.init_learning_state()

    log_text = caplog.text
    assert isolated_gae_state.get_learning_store() is None
    assert "SOC L5 learning store unavailable" in log_text
    assert raw_dsn not in log_text
    assert "secret" not in log_text


def test_feedback_and_triage_do_not_import_learning_store():
    root = Path(__file__).resolve().parents[1]
    checked = []
    for pattern in ("feedback*.py", "triage.py"):
        for path in (root / "app").rglob(pattern):
            checked.append(path)
            text = path.read_text(encoding="utf-8", errors="ignore")
            assert "get_learning_store" not in text
    assert checked
