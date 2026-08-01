from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = REPO_ROOT / "scripts" / "diagnostics" / "run_soc_route_validation.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_soc_route_validation", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_cli_phase_plan_and_env_parsing():
    runner = load_runner()

    args = runner.parse_args(
        [
            "--port",
            "8001",
            "--prefix",
            "P5DSHADOW",
            "--count",
            "5",
            "--phase",
            "all",
            "--run-250",
            "--false-graph",
            "false_graph",
            "--true-graph",
            "true_graph",
            "--proof-graph",
            "proof_graph",
            "--false-env",
            "USE_SOC_DECISION_PIPELINE_SHADOW=false,USE_ENTITY_CACHE=false,AGE_USE_POOL=true",
            "--true-env",
            "USE_SOC_DECISION_PIPELINE_SHADOW=true,USE_ENTITY_CACHE=false,AGE_USE_POOL=true",
            "--proof-env",
            "USE_SOC_DECISION_PIPELINE_SHADOW=true,USE_ENTITY_CACHE=false,AGE_USE_POOL=true",
            "--compare-profile",
            "shadow",
        ]
    )

    config = runner.config_from_args(args)
    assert config.phases == ("false_baseline", "true_compare", "proof_250")
    assert config.false_env["USE_SOC_DECISION_PIPELINE_SHADOW"] == "false"
    assert config.true_env["USE_SOC_DECISION_PIPELINE_SHADOW"] == "true"
    assert config.proof_env["AGE_USE_POOL"] == "true"
    assert [phase.graph for phase in runner.phase_plan(config)] == [
        "false_graph",
        "true_graph",
        "proof_graph",
    ]


def test_cli_rejects_assume_backend_contract():
    runner = load_runner()

    with pytest.raises(SystemExit):
        runner.parse_args(["--assume-backend-contract"])


def test_workload_defaults_and_latency_stats():
    runner = load_runner()
    alert_ids = runner.deterministic_alert_ids("P5DSHADOW", 5)

    workloads = runner.build_workloads(
        alert_ids,
        selected=("unique_once", "repeat_same", "mixed_reuse"),
        repeat_count=5,
    )

    assert workloads["unique_once"] == alert_ids
    assert workloads["repeat_same"] == ["P5DSHADOW-0001"] * 5
    assert workloads["mixed_reuse"] == [
        "P5DSHADOW-0001",
        "P5DSHADOW-0002",
        "P5DSHADOW-0001",
        "P5DSHADOW-0003",
        "P5DSHADOW-0001",
        "P5DSHADOW-0004",
        "P5DSHADOW-0005",
        "P5DSHADOW-0001",
    ]
    stats = runner.latency_stats([0.1, 0.2, 0.4], request_count=4)
    assert stats["avg_seconds"] == pytest.approx(0.233333333)
    assert stats["median_seconds"] == 0.2
    assert stats["p95_seconds"] == 0.4
    assert stats["failure_count"] == 1


def test_compare_outputs_excludes_dynamic_fields_and_reports_paths():
    runner = load_runner()
    false_by_id = {
        "A-0001": {
            "recommendation.action": "investigate",
            "recommendation.confidence": 0.8,
            "gae_scoring.factor_vector": [1, 2],
        }
    }
    true_by_id = {
        "A-0001": {
            "recommendation.action": "refer_to_analyst",
            "recommendation.confidence": 0.8,
            "gae_scoring.factor_vector": [1, 2],
        }
    }

    comparison = runner.compare_projected_outputs(false_by_id, true_by_id, ["A-0001"])

    assert comparison["matched"] is False
    assert comparison["field_status"]["recommendation.action"] == "FAIL"
    assert comparison["field_status"]["gae_scoring.factor_vector"] == "PASS"
    assert comparison["differences"] == [
        {
            "alert_id": "A-0001",
            "field": "recommendation.action",
            "false": "investigate",
            "true": "refer_to_analyst",
        }
    ]
    assert "decision IDs" in comparison["excluded_fields"]


def test_shadow_profile_requires_matching_diagnostics_and_zero_side_effects():
    runner = load_runner()
    good_diag = {
        "matched": True,
        "differences": [],
        "side_effects": {
            "decision_writes": 0,
            "outcome_writes": 0,
            "proof_writes": 0,
            "counter_updates": 0,
            "graph_mutations": 0,
        },
    }
    bad_diag = {
        **good_diag,
        "status": "shadow_failed",
    }

    assert runner.validate_shadow_profile(
        [{"diagnostics": {"soc_decision_pipeline_shadow": good_diag}}]
    )["passed"] is True
    failed = runner.validate_shadow_profile(
        [{"diagnostics": {"soc_decision_pipeline_shadow": bad_diag}}]
    )
    assert failed["passed"] is False
    assert failed["shadow_failed"] is True


def test_shadow_profile_failure_makes_phase_fail():
    runner = load_runner()
    artifact = {
        "status": "PASS",
        "contract": {"verified": True},
        "queue": {"queue_visible": True},
        "workloads": {
            "unique_once": {
                "failures": [],
                "profile_validation": {
                    "profile": "shadow",
                    "passed": False,
                    "diagnostics_present": False,
                    "matched_true": False,
                },
            }
        },
    }

    failed = runner.phase_failed_checks(artifact)

    assert "workloads.unique_once.profile_validation.diagnostics_present" in failed
    assert "workloads.unique_once.profile_validation.matched_true" in failed


def test_entity_cache_profile_requires_safe_visible_stats():
    runner = load_runner()
    health = {
        "components": {
            "entity_cache": {
                "enabled": True,
                "hits": 1,
                "misses": 2,
                "loads": 2,
                "size": 2,
                "max_size": 4096,
            }
        }
    }

    assert runner.validate_entity_cache_profile(health, expect_enabled=True)["passed"] is True
    leaked = {
        "components": {
            "entity_cache": {
                "enabled": True,
                "hits": 1,
                "misses": 2,
                "loads": 2,
                "size": 2,
                "max_size": 4096,
                "alert_id": "SECRET-0001",
            }
        }
    }
    assert runner.validate_entity_cache_profile(leaked, expect_enabled=True)["passed"] is False


def test_entity_cache_profile_failure_makes_phase_fail():
    runner = load_runner()
    artifact = {
        "status": "PASS",
        "contract": {"verified": True},
        "queue": {"queue_visible": True},
        "profile_validation": {
            "profile": "entity_cache",
            "passed": False,
            "visible": False,
            "enabled_matches": False,
        },
        "workloads": {},
    }

    failed = runner.phase_failed_checks(artifact)

    assert "profile_validation.visible" in failed
    assert "profile_validation.enabled_matches" in failed


def test_strict_contract_rejects_stale_graph_and_port():
    runner = load_runner()
    contract = {
        "launcher": "copilot-sdk/demo.py --diag-mode",
        "graph_name": "old_graph",
        "backend_port": 8002,
        "connection_mode": "warm_fallback",
        "use_entity_cache": "false",
        "age_use_pool_requested": "true",
        "age_use_pool": "true",
    }

    result = runner.validate_contract(
        contract,
        expected_graph="new_graph",
        expected_port=8001,
        expected_env={"USE_ENTITY_CACHE": "false", "AGE_USE_POOL": "true"},
    )

    assert result["verified"] is False
    assert "graph mismatch" in result["errors"]
    assert "port mismatch" in result["errors"]


def test_waits_for_contract_after_health_before_phase_proceeds(tmp_path, monkeypatch):
    runner = load_runner()
    contract_path = tmp_path / "soc_diag_backend_contract.json"
    phase = runner.PhaseConfig("false_baseline", "graph_ready", {"USE_ENTITY_CACHE": "false", "AGE_USE_POOL": "true"})
    config = runner.RunnerConfig(
        port=8001,
        prefix="P5DSHADOW",
        count=1,
        phases=("false_baseline",),
        compare_profile="generic",
        workloads=("unique_once",),
        repeat_count=1,
        false_graph="graph_ready",
        true_graph=None,
        proof_graph=None,
        false_env=phase.env,
        true_env={},
        proof_env={},
        out_dir=tmp_path,
        graph_dsn="dsn",
        run_250=False,
        strict_contract=True,
        contract_path=contract_path,
        readiness_timeout_seconds=1.0,
    )
    calls = {"sleep": 0}

    def fake_sleep(_seconds):
        calls["sleep"] += 1
        if calls["sleep"] == 2:
            contract_path.write_text(
                json.dumps(
                    {
                        "launcher": "copilot-sdk/demo.py --diag-mode",
                        "graph_name": "graph_ready",
                        "backend_port": 8001,
                        "connection_mode": "warm_fallback",
                        "use_entity_cache": "false",
                        "age_use_pool_requested": "true",
                        "age_use_pool": "true",
                    }
                ),
                encoding="utf-8",
            )

    monkeypatch.setattr(runner, "wait_for_health", lambda *_args, **_kwargs: {"ok": True})
    monkeypatch.setattr(runner.time, "sleep", fake_sleep)

    health, _contract, contract_status = runner.await_backend_readiness(
        phase,
        config,
        backend_url="http://127.0.0.1:8001",
        phase_started_at=0,
    )

    assert health == {"ok": True}
    assert contract_status["verified"] is True
    assert calls["sleep"] >= 2


def test_contract_never_appears_fails_with_phase_context(tmp_path, monkeypatch):
    runner = load_runner()

    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: None)

    with pytest.raises(runner.RouteValidationError) as exc:
        runner.wait_for_contract_file(
            tmp_path / "missing_contract.json",
            phase="proof_250",
            graph="proof_graph",
            port=8001,
            timeout_seconds=0.01,
            poll_interval_seconds=0.001,
        )

    message = str(exc.value)
    assert "phase=proof_250" in message
    assert "graph=proof_graph" in message
    assert "port=8001" in message


def test_malformed_contract_json_fails(tmp_path):
    runner = load_runner()
    contract_path = tmp_path / "soc_diag_backend_contract.json"
    contract_path.write_text("{bad json", encoding="utf-8")

    with pytest.raises(runner.RouteValidationError):
        runner.load_contract_json(contract_path)


def test_strict_contract_rejects_wrong_launcher_and_pool_and_stale_timestamp(tmp_path):
    runner = load_runner()
    contract_path = tmp_path / "soc_diag_backend_contract.json"
    contract_path.write_text("{}", encoding="utf-8")
    contract = {
        "launcher": "wrong.py",
        "graph_name": "graph",
        "backend_port": 8001,
        "connection_mode": "warm_fallback",
        "use_entity_cache": "false",
        "age_use_pool_requested": "false",
        "age_use_pool": "false",
    }

    result = runner.validate_contract(
        contract,
        expected_graph="graph",
        expected_port=8001,
        expected_env={"USE_ENTITY_CACHE": "false", "AGE_USE_POOL": "true"},
        phase_started_at=9999999999,
        contract_path=contract_path,
    )

    assert result["verified"] is False
    assert "launcher mismatch" in result["errors"]
    assert "age_use_pool_requested mismatch" in result["errors"]
    assert "age_use_pool mismatch" in result["errors"]
    assert "contract file timestamp predates phase start" in result["errors"]


def test_contract_path_clearing_is_explicit_without_backend(tmp_path):
    runner = load_runner()
    path = tmp_path / "soc_diag_backend_contract.json"
    path.write_text("{}", encoding="utf-8")

    result = runner.clear_contract_path(path)

    assert result == {"path": str(path), "existed": True, "cleared": True}
    assert not path.exists()


def test_queue_guard_failure_writes_fail_artifact_and_skips_analyze(tmp_path, monkeypatch):
    runner = load_runner()
    phase = runner.PhaseConfig("false_baseline", "queue_graph", {"USE_ENTITY_CACHE": "false"})
    config = runner.RunnerConfig(
        port=8001,
        prefix="P5DSHADOW",
        count=1,
        phases=("false_baseline",),
        compare_profile="generic",
        workloads=("unique_once",),
        repeat_count=1,
        false_graph="queue_graph",
        true_graph=None,
        proof_graph=None,
        false_env=phase.env,
        true_env={},
        proof_env={},
        out_dir=tmp_path,
        graph_dsn="dsn",
        run_250=False,
        strict_contract=True,
        contract_path=tmp_path / "contract.json",
        readiness_timeout_seconds=1.0,
    )
    stopped = {"called": False}

    class DummyProcess:
        pass

    monkeypatch.setattr(runner, "stop_stale_backend", lambda _port: None)
    monkeypatch.setattr(runner, "clear_contract_path", lambda _path: {"cleared": True})
    monkeypatch.setattr(runner, "start_backend", lambda *_args, **_kwargs: DummyProcess())
    monkeypatch.setattr(
        runner,
        "await_backend_readiness",
        lambda *_args, **_kwargs: (
            {"ok": True},
            {},
            {"verified": True, "errors": [], "path": str(config.contract_path)},
        ),
    )
    monkeypatch.setattr(runner, "seed_alerts", lambda *_args, **_kwargs: {"seeded": True})
    monkeypatch.setattr(runner, "verify_queue", lambda *_args, **_kwargs: {"queue_visible": False, "missing_ids": ["P5DSHADOW-0001"]})
    monkeypatch.setattr(
        runner,
        "capture_workloads",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("analyze should not run")),
    )
    monkeypatch.setattr(runner, "stop_backend", lambda _process: stopped.__setitem__("called", True))

    artifact = runner.run_route_phase(phase, config)

    assert artifact["status"] == "FAIL"
    assert "seeded alerts not queue-visible" in artifact["error"]
    assert stopped["called"] is True
    written = json.loads((tmp_path / "route_validation_false_baseline.json").read_text(encoding="utf-8"))
    assert written["status"] == "FAIL"


def test_readiness_failure_attempts_backend_cleanup(tmp_path, monkeypatch):
    runner = load_runner()
    phase = runner.PhaseConfig("false_baseline", "ready_graph", {"USE_ENTITY_CACHE": "false"})
    config = runner.RunnerConfig(
        port=8001,
        prefix="P5DSHADOW",
        count=1,
        phases=("false_baseline",),
        compare_profile="generic",
        workloads=("unique_once",),
        repeat_count=1,
        false_graph="ready_graph",
        true_graph=None,
        proof_graph=None,
        false_env=phase.env,
        true_env={},
        proof_env={},
        out_dir=tmp_path,
        graph_dsn="dsn",
        run_250=False,
        strict_contract=True,
        contract_path=tmp_path / "contract.json",
        readiness_timeout_seconds=1.0,
    )
    stopped = {"called": False}

    class DummyProcess:
        pass

    monkeypatch.setattr(runner, "stop_stale_backend", lambda _port: None)
    monkeypatch.setattr(runner, "clear_contract_path", lambda _path: {"cleared": True})
    monkeypatch.setattr(runner, "start_backend", lambda *_args, **_kwargs: DummyProcess())
    monkeypatch.setattr(
        runner,
        "await_backend_readiness",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(runner.RouteValidationError("contract timeout")),
    )
    monkeypatch.setattr(runner, "stop_backend", lambda _process: stopped.__setitem__("called", True))

    artifact = runner.run_route_phase(phase, config)

    assert artifact["status"] == "FAIL"
    assert "contract timeout" in artifact["error"]
    assert stopped["called"] is True


def test_stop_stale_backend_failure_is_clear(monkeypatch):
    runner = load_runner()

    class Completed:
        returncode = 1
        stdout = ""
        stderr = "access denied"

    monkeypatch.setattr(runner.os, "name", "nt")
    monkeypatch.setattr(runner.subprocess, "run", lambda *_args, **_kwargs: Completed())

    with pytest.raises(runner.RouteValidationError) as exc:
        runner.stop_stale_backend(8001)

    assert "failed to clear stale backend on port 8001" in str(exc.value)


def test_phase_dependencies_block_later_phases_in_all(tmp_path, monkeypatch):
    runner = load_runner()
    config = runner.RunnerConfig(
        port=8001,
        prefix="P5DSHADOW",
        count=1,
        phases=("false_baseline", "true_compare", "proof_250"),
        compare_profile="generic",
        workloads=("unique_once",),
        repeat_count=1,
        false_graph="false_graph",
        true_graph="true_graph",
        proof_graph="proof_graph",
        false_env={},
        true_env={},
        proof_env={},
        out_dir=tmp_path,
        graph_dsn="dsn",
        run_250=True,
        strict_contract=True,
        contract_path=tmp_path / "contract.json",
        readiness_timeout_seconds=1.0,
    )

    def fake_route_phase(phase, _config):
        assert phase.name == "false_baseline"
        return {"phase": phase.name, "status": "FAIL", "graph": phase.graph, "contract": {"verified": False}}

    monkeypatch.setattr(runner, "run_route_phase", fake_route_phase)
    monkeypatch.setattr(
        runner,
        "run_proof_phase",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("proof should be blocked")),
    )

    results = runner.run(config)

    assert results["false_baseline"]["status"] == "FAIL"
    assert results["true_compare"]["status"] == "BLOCKED"
    assert results["proof_250"]["status"] == "BLOCKED"
    assert results["summary"]["status"] == "FAIL"


def test_true_failure_blocks_proof_in_all(tmp_path, monkeypatch):
    runner = load_runner()
    config = runner.RunnerConfig(
        port=8001,
        prefix="P5DSHADOW",
        count=1,
        phases=("false_baseline", "true_compare", "proof_250"),
        compare_profile="generic",
        workloads=("unique_once",),
        repeat_count=1,
        false_graph="false_graph",
        true_graph="true_graph",
        proof_graph="proof_graph",
        false_env={},
        true_env={},
        proof_env={},
        out_dir=tmp_path,
        graph_dsn="dsn",
        run_250=True,
        strict_contract=True,
        contract_path=tmp_path / "contract.json",
        readiness_timeout_seconds=1.0,
    )

    def fake_route_phase(phase, _config):
        return {"phase": phase.name, "status": "PASS" if phase.name == "false_baseline" else "FAIL", "graph": phase.graph}

    monkeypatch.setattr(runner, "run_route_phase", fake_route_phase)
    monkeypatch.setattr(
        runner,
        "run_proof_phase",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("proof should be blocked")),
    )

    results = runner.run(config)

    assert results["true_compare"]["status"] == "FAIL"
    assert results["proof_250"]["status"] == "BLOCKED"
    assert results["summary"]["status"] == "FAIL"


def test_comparison_rejects_stale_prefix_artifacts():
    runner = load_runner()
    false_artifact = {
        "status": "PASS",
        "prefix": "OLD",
        "count": 1,
        "alert_ids": ["A-0001"],
        "contract": {"verified": True},
        "queue": {"queue_visible": True},
        "workloads": {},
    }
    true_artifact = {
        "status": "PASS",
        "prefix": "NEW",
        "count": 1,
        "alert_ids": ["A-0001"],
        "contract": {"verified": True},
        "queue": {"queue_visible": True},
        "workloads": {},
    }

    comparison = runner.build_comparison(false_artifact, true_artifact)

    assert comparison["status"] == "FAIL"
    assert "artifact.prefix_mismatch" in comparison["failed_checks"]


def test_summary_generation_and_performance_ledger():
    runner = load_runner()
    results = {
        "false_baseline": {
            "status": "PASS",
            "graph": "false_graph",
            "contract": {"verified": True},
        },
        "true_compare": {
            "status": "PASS",
            "graph": "true_graph",
            "contract": {"verified": True},
        },
        "comparison": {"status": "PASS", "diagnostics_summary": {"shadow": "ok"}},
    }

    summary = runner.build_final_summary(results)

    assert summary["status"] == "PASS"
    assert summary["phases_run"] == ["false_baseline", "true_compare"]
    assert summary["parity_status"] == "PASS"
    assert summary["performance_ledger"]["buyer_facing_claim_allowed"] is False


def test_generic_parity_difference_fails_comparison_and_true_phase():
    runner = load_runner()
    false_artifact = {
        "status": "PASS",
        "graph": "false_graph",
        "contract": {"verified": True},
        "queue": {"queue_visible": True},
        "alert_ids": ["A-0001"],
        "workloads": {
            "unique_once": {
                "failures": [],
                "profile_validation": {"profile": "generic", "passed": True},
                "captures": [
                    {
                        "alert_id": "A-0001",
                        "comparable": {"recommendation.action": "investigate"},
                    }
                ],
            }
        },
    }
    true_artifact = {
        "status": "PASS",
        "graph": "true_graph",
        "contract": {"verified": True},
        "queue": {"queue_visible": True},
        "alert_ids": ["A-0001"],
        "workloads": {
            "unique_once": {
                "failures": [],
                "profile_validation": {"profile": "generic", "passed": True},
                "captures": [
                    {
                        "alert_id": "A-0001",
                        "comparable": {"recommendation.action": "refer_to_analyst"},
                    }
                ],
            }
        },
    }

    comparison = runner.build_comparison(false_artifact, true_artifact)
    summary = runner.build_final_summary(
        {
            "false_baseline": false_artifact,
            "true_compare": {**true_artifact, "status": "FAIL"},
            "comparison": comparison,
        }
    )

    assert comparison["status"] == "FAIL"
    assert comparison["phase_status"]["true_compare"] == "FAIL"
    assert comparison["failed_checks"] == ["parity.A-0001.recommendation.action"]
    assert summary["status"] == "FAIL"


def test_proof_output_validation_parses_compact_summary():
    runner = load_runner()
    stdout = """
    [SOC DIAG F] final verdict EXTERNAL_DIAGNOSTIC_F_PASS
    - valid_outcomes: `250`
    - l5_dk_weight: `1`
    - dk_welford_rows: `1`
    - max_n_decisions_used: `250`
    - avg_analyze_seconds: `0.202`
    - max_analyze_seconds: `0.571`
    - avg_outcome_seconds: `0.440`
    """

    validation = runner.validate_proof_output(stdout, returncode=0)

    assert validation["passed"] is True
    assert validation["summary"]["valid_outcomes"] == 250
    assert validation["summary"]["avg_analyze_seconds"] == 0.202
    assert validation["expected"]["max_n_decisions_used"] == 250


@pytest.mark.parametrize(
    ("field", "line"),
    [
        ("valid_outcomes", ""),
        ("l5_dk_weight", ""),
        ("dk_welford_rows", ""),
        ("max_n_decisions_used", ""),
        ("l5_dk_weight", "- l5_dk_weight: `0`"),
        ("dk_welford_rows", "- dk_welford_rows: `0`"),
        ("max_n_decisions_used", "- max_n_decisions_used: `249`"),
    ],
)
def test_proof_output_validation_fails_missing_or_wrong_invariants(field, line):
    runner = load_runner()
    lines = {
        "valid_outcomes": "- valid_outcomes: `250`",
        "l5_dk_weight": "- l5_dk_weight: `1`",
        "dk_welford_rows": "- dk_welford_rows: `1`",
        "max_n_decisions_used": "- max_n_decisions_used: `250`",
    }
    if line:
        lines[field] = line
    else:
        lines.pop(field)
    stdout = "\n".join(["EXTERNAL_DIAGNOSTIC_F_PASS", *lines.values()])

    validation = runner.validate_proof_output(stdout, returncode=0)

    assert validation["passed"] is False
    assert any(field in error for error in validation["errors"])


def test_final_summary_fails_when_proof_phase_fails():
    runner = load_runner()
    summary = runner.build_final_summary(
        {
            "proof_250": {
                "status": "FAIL",
                "contract": {"verified": True},
                "proof_validation": {"passed": False},
            }
        }
    )

    assert summary["status"] == "FAIL"
    assert summary["proof_status"] == "FAIL"


def test_unit_tests_do_not_need_backend_subprocess(monkeypatch):
    runner = load_runner()

    def fail_subprocess(*_args, **_kwargs):
        raise AssertionError("unit test should not execute backend subprocesses")

    monkeypatch.setattr(runner.subprocess, "run", fail_subprocess)
    monkeypatch.setattr(runner.subprocess, "Popen", fail_subprocess)

    assert runner.validate_generic_profile()["passed"] is True
    assert runner.parse_env_assignments("A=1,B=2") == {"A": "1", "B": "2"}
