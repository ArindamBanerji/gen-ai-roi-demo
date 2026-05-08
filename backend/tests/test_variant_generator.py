import inspect
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.framework.evolution_ledger import (
    ARTIFACT_CONTEXT_POLICY,
    ARTIFACT_EVIDENCE_ORDER,
    ARTIFACT_PROMPT_MODULE,
    ARTIFACT_ROUTING_RULE,
    ARTIFACT_SCORING_THRESHOLD,
    VARIANT_CREATED,
)
from app.services import variant_generator as generator
from app.services import variant_registry as registry


class _SignalRule:
    rule_id = "RULE-TEST"
    artifact_type = ARTIFACT_ROUTING_RULE
    description = "test rule"

    def __init__(self, signal=None):
        self.signal = signal or generator.GraphSignal(
            rule_id=self.rule_id,
            trigger_id="signal-1",
            artifact_type=self.artifact_type,
            evidence={"category": "credential_access", "timestamp_epoch": 123.0},
            category="credential_access",
            description="test signal",
        )

    async def detect(self, neo4j_client):
        return self.signal

    def generate_variant(self, signal):
        return registry.VariantRecord(
            variant_id="variant_test",
            artifact_type=signal.artifact_type,
            category=signal.category,
            config={"action": "escalate"},
            status=registry.CANDIDATE,
            trigger_key=f"{signal.rule_id}_{signal.trigger_id}",
            graph_trigger=signal.evidence,
            created_at=123.0,
        )


class _NullRule(_SignalRule):
    async def detect(self, neo4j_client):
        return None


class _BoomRule(_SignalRule):
    rule_id = "RULE-BOOM"

    async def detect(self, neo4j_client):
        raise RuntimeError("boom")


def setup_function():
    registry.reset_variant_registry()


@pytest.fixture
def ledger(monkeypatch):
    mock = AsyncMock(return_value={"id": "evo_1"})
    monkeypatch.setattr(generator, "record_evolution_event", mock)
    return mock


def _patch_module(monkeypatch, module_name, module):
    real_import = generator.importlib.import_module

    def fake_import(name):
        if name == module_name:
            return module
        return real_import(name)

    monkeypatch.setattr(generator.importlib, "import_module", fake_import)


def _accuracy_rows(category, total, correct):
    return [
        {"category": category, "correct": index < correct}
        for index in range(total)
    ]


class _CoverageClient:
    def __init__(self, rows=None, exc=None):
        self.rows = rows or []
        self.exc = exc
        self.queries = []

    async def run_query(self, query):
        self.queries.append(query)
        if self.exc:
            raise self.exc
        return self.rows


def _coverage_rows(**counts):
    return [{"category": category, "cnt": count} for category, count in counts.items()]


def _drift_client(recent_rows=None, prior_rows=None, side_effect=None):
    client = SimpleNamespace()
    if side_effect is not None:
        client.run_query = AsyncMock(side_effect=side_effect)
    else:
        client.run_query = AsyncMock(side_effect=[
            recent_rows or [],
            prior_rows or [],
        ])
    return client


class _WarmRule:
    rule_id = "RULE-WARM"
    artifact_type = ARTIFACT_SCORING_THRESHOLD
    description = "warm rule"

    def __init__(self, category="credential_access"):
        self.signal = generator.GraphSignal(
            rule_id=self.rule_id,
            trigger_id=f"{category}_drift",
            artifact_type=self.artifact_type,
            evidence={"category": category, "timestamp_epoch": 456.0},
            category=category,
            description="warm signal",
        )

    async def detect(self, neo4j_client):
        return self.signal

    def generate_variant(self, signal):
        return registry.VariantRecord(
            variant_id=generator._variant_id(signal.rule_id, signal.trigger_id),
            artifact_type=signal.artifact_type,
            category=signal.category,
            config={
                "category": signal.category,
                "current_value": 0.90,
                "proposed_value": 0.85,
                "auto_approve_action": "suppress",
            },
            status=registry.CANDIDATE,
            trigger_key=f"{signal.rule_id}_{signal.trigger_id}",
            graph_trigger=signal.evidence,
            created_at=456.0,
        )


def _event(event_type, timestamp_epoch=1_700_000_000_000, after_state=None):
    return {
        "event_type": event_type,
        "timestamp_epoch": timestamp_epoch,
        "after_state": after_state or {},
    }


def _patch_history(monkeypatch, events=None, side_effect=None):
    mock = AsyncMock(side_effect=side_effect)
    if side_effect is None:
        mock.return_value = events or []
    real_import = generator.importlib.import_module

    def fake_import(name):
        if name == "app.framework.evolution_ledger":
            return SimpleNamespace(
                get_variant_history=mock,
                VARIANT_CREATED="variant_created",
                PROMOTION_APPROVED="promotion_approved",
                PROMOTION_REJECTED="promotion_rejected",
                ROLLBACK="rollback",
            )
        return real_import(name)

    monkeypatch.setattr(generator.importlib, "import_module", fake_import)
    return mock


@pytest.mark.asyncio
async def test_generator_with_no_rules_returns_empty(ledger):
    gen = generator.VariantGenerator(rules=[])

    assert await gen.scan_for_opportunities(object()) == []
    ledger.assert_not_called()


@pytest.mark.asyncio
async def test_rule_returns_none_generates_no_variant(ledger):
    gen = generator.VariantGenerator(rules=[_NullRule()])

    assert await gen.scan_for_opportunities(object()) == []
    assert registry.get_all_variants() == []
    ledger.assert_not_called()


@pytest.mark.asyncio
async def test_rule_signal_generates_variant_and_registers(ledger):
    gen = generator.VariantGenerator(rules=[_SignalRule()])

    created = await gen.scan_for_opportunities(object())

    assert [record.variant_id for record in created] == ["variant_test"]
    assert registry.get_variant("variant_test") is not None
    ledger.assert_awaited_once()


@pytest.mark.asyncio
async def test_same_signal_twice_does_not_duplicate(ledger):
    gen = generator.VariantGenerator(rules=[_SignalRule()])

    first = await gen.scan_for_opportunities(object())
    second = await gen.scan_for_opportunities(object())

    assert len(first) == 1
    assert second == []
    assert len(registry.get_all_variants()) == 1
    assert ledger.await_count == 1


@pytest.mark.asyncio
async def test_rule_exception_logged_and_other_rules_continue(ledger, caplog):
    gen = generator.VariantGenerator(rules=[_BoomRule(), _SignalRule()])

    with caplog.at_level(logging.WARNING):
        created = await gen.scan_for_opportunities(object())

    assert [record.variant_id for record in created] == ["variant_test"]
    assert "RULE-BOOM" in caplog.text
    assert "boom" in caplog.text


@pytest.mark.asyncio
async def test_ledger_failure_does_not_leave_registry_inconsistent(monkeypatch):
    monkeypatch.setattr(
        generator,
        "record_evolution_event",
        AsyncMock(side_effect=RuntimeError("ledger unavailable")),
    )
    gen = generator.VariantGenerator(rules=[_SignalRule()])

    created = await gen.scan_for_opportunities(object())

    assert created == []
    assert registry.get_all_variants() == []


@pytest.mark.asyncio
async def test_consult_history_no_prior_events_proceeds(monkeypatch):
    _patch_history(monkeypatch, [])

    assert await generator._consult_history(object(), "v1") == {"action": "proceed"}


@pytest.mark.asyncio
async def test_consult_history_recent_rejection_skips(monkeypatch):
    monkeypatch.setattr(generator.time, "time", lambda: 1_700_000_000.0)
    _patch_history(monkeypatch, [
        _event("promotion_rejected", timestamp_epoch=1_699_999_000_000),
    ])

    result = await generator._consult_history(object(), "v1")

    assert result["action"] == "skip"
    assert result["reason"] == "recent rejection"


@pytest.mark.asyncio
async def test_consult_history_old_rejection_proceeds(monkeypatch):
    monkeypatch.setattr(generator.time, "time", lambda: 1_700_000_000.0)
    _patch_history(monkeypatch, [
        _event("promotion_rejected", timestamp_epoch=1_696_000_000_000),
    ])

    assert await generator._consult_history(object(), "v1") == {"action": "proceed"}


@pytest.mark.asyncio
async def test_consult_history_rollback_skips_regardless_of_age(monkeypatch):
    monkeypatch.setattr(generator.time, "time", lambda: 1_700_000_000.0)
    _patch_history(monkeypatch, [
        _event("rollback", timestamp_epoch=1_600_000_000),
    ])

    result = await generator._consult_history(object(), "v1")

    assert result["action"] == "skip"
    assert result["reason"] == "prior rollback"


@pytest.mark.asyncio
async def test_consult_history_promotion_warm_starts_from_variant_created(monkeypatch):
    config = {"category": "old_category", "current_value": 0.95}
    _patch_history(monkeypatch, [
        _event("variant_created", timestamp_epoch=1_600_000_000_000, after_state=config),
        _event("promotion_approved", timestamp_epoch=1_600_010_000_000),
    ])

    result = await generator._consult_history(object(), "v1")

    assert result == {"action": "warm_start", "baseline_config": config}


@pytest.mark.asyncio
async def test_consult_history_promotion_with_empty_created_state_proceeds(monkeypatch):
    _patch_history(monkeypatch, [
        _event("variant_created", timestamp_epoch=1_600_000_000_000, after_state={}),
        _event("promotion_approved", timestamp_epoch=1_600_010_000_000),
    ])

    assert await generator._consult_history(object(), "v1") == {"action": "proceed"}


@pytest.mark.asyncio
async def test_consult_history_promotion_without_created_event_proceeds(monkeypatch):
    _patch_history(monkeypatch, [
        _event("promotion_approved", timestamp_epoch=1_600_010_000_000),
    ])

    assert await generator._consult_history(object(), "v1") == {"action": "proceed"}


@pytest.mark.asyncio
async def test_consult_history_query_failure_proceeds(monkeypatch):
    _patch_history(monkeypatch, side_effect=RuntimeError("history down"))

    assert await generator._consult_history(object(), "v1") == {"action": "proceed"}


@pytest.mark.asyncio
async def test_consult_history_most_recent_terminal_event_wins(monkeypatch):
    monkeypatch.setattr(generator.time, "time", lambda: 1_700_000_000.0)
    _patch_history(monkeypatch, [
        _event("rollback", timestamp_epoch=1_600_000_000_000),
        _event("promotion_rejected", timestamp_epoch=1_699_999_000_000),
    ])

    result = await generator._consult_history(object(), "v1")

    assert result["action"] == "skip"
    assert result["reason"] == "recent rejection"


@pytest.mark.asyncio
async def test_consult_history_only_non_terminal_events_proceeds(monkeypatch):
    _patch_history(monkeypatch, [
        _event("variant_created", timestamp_epoch=1_600_000_000_000, after_state={"a": 1}),
        _event("shadow_started", timestamp_epoch=1_600_001_000_000),
        _event("shadow_result", timestamp_epoch=1_600_002_000_000),
    ])

    assert await generator._consult_history(object(), "v1") == {"action": "proceed"}


@pytest.mark.asyncio
async def test_consult_history_millisecond_timestamp_epoch(monkeypatch):
    monkeypatch.setattr(generator.time, "time", lambda: 1_700_000_000.0)
    _patch_history(monkeypatch, [
        _event("promotion_rejected", timestamp_epoch=1_699_999_000_000),
    ])

    result = await generator._consult_history(object(), "v1")

    assert result["action"] == "skip"


@pytest.mark.asyncio
async def test_scan_skips_when_history_says_skip(monkeypatch, ledger):
    monkeypatch.setattr(generator, "_consult_history", AsyncMock(return_value={
        "action": "skip",
        "reason": "recent rejection",
    }))
    gen = generator.VariantGenerator(rules=[_WarmRule()])

    created = await gen.scan_for_opportunities(object())

    assert created == []
    ledger.assert_not_called()


@pytest.mark.asyncio
async def test_scan_warm_starts_config_and_category(monkeypatch, ledger):
    monkeypatch.setattr(generator, "_consult_history", AsyncMock(return_value={
        "action": "warm_start",
        "baseline_config": {
            "category": "old_category",
            "current_value": 0.97,
            "proposed_value": 0.91,
            "auto_approve_action": "approve",
        },
    }))
    gen = generator.VariantGenerator(rules=[_WarmRule(category="insider_threat")])

    created = await gen.scan_for_opportunities(object())

    assert len(created) == 1
    assert created[0].config == {
        "category": "insider_threat",
        "current_value": 0.97,
        "proposed_value": 0.91,
        "auto_approve_action": "approve",
    }
    kwargs = ledger.await_args.kwargs
    assert kwargs["after_state"] == created[0].config
    assert kwargs["metadata"]["warm_started"] is True
    assert kwargs["metadata"]["baseline_variant_id"] == created[0].variant_id


@pytest.mark.asyncio
async def test_scan_proceeds_normally_when_history_says_proceed(monkeypatch, ledger):
    monkeypatch.setattr(generator, "_consult_history", AsyncMock(return_value={"action": "proceed"}))
    gen = generator.VariantGenerator(rules=[_WarmRule(category="credential_access")])

    created = await gen.scan_for_opportunities(object())

    assert len(created) == 1
    assert created[0].config["current_value"] == 0.90
    assert created[0].config["proposed_value"] == 0.85
    assert ledger.await_args.kwargs["metadata"]["warm_started"] is False


@pytest.mark.asyncio
async def test_import_error_in_detect_returns_none(monkeypatch):
    def raise_import_error(name):
        raise ImportError(name)

    monkeypatch.setattr(generator.importlib, "import_module", raise_import_error)

    assert await generator.CampaignEscalateRule().detect(object()) is None


@pytest.mark.asyncio
async def test_campaign_rule_generates_routing_rule_config_shape(monkeypatch):
    service = SimpleNamespace(
        refresh=AsyncMock(return_value={
            "discoveries": [
                {
                    "type": "campaign",
                    "campaign_id": "C-007",
                    "category": "credential_access",
                    "trigger_categories": ["credential_access", "lateral_movement"],
                }
            ]
        })
    )
    _patch_module(
        monkeypatch,
        "app.services.cross_graph_discovery",
        SimpleNamespace(discovery_service=service),
    )
    rule = generator.CampaignEscalateRule()

    signal = await rule.detect(object())
    record = rule.generate_variant(signal)

    assert signal.trigger_id == "C-007"
    assert record.artifact_type == ARTIFACT_ROUTING_RULE
    assert record.config == {
        "action": "escalate",
        "trigger_categories": ["credential_access", "lateral_movement"],
        "campaign_pattern": "C-007",
        "min_confidence": 0.70,
    }


@pytest.mark.asyncio
async def test_drift_rule_declining_category_generates_scoring_threshold_config_shape():
    rule = generator.DriftThresholdRule()
    client = _drift_client(
        recent_rows=_accuracy_rows("insider_threat", 50, 41),
        prior_rows=_accuracy_rows("insider_threat", 50, 44),
    )

    signal = await rule.detect(client)
    record = rule.generate_variant(signal)

    assert signal.trigger_id == "insider_threat_drift"
    assert signal.evidence == {
        "category": "insider_threat",
        "recent_accuracy": 0.82,
        "prior_accuracy": 0.88,
        "decline_pp": 6.0,
        "recent_decisions": 50,
        "prior_decisions": 50,
        "detection_method": "per_category_accuracy_trend",
    }
    assert signal.description == "Accuracy declined 6.0pp for insider_threat over 14 days"
    assert record.artifact_type == ARTIFACT_SCORING_THRESHOLD
    assert record.config == {
        "category": "insider_threat",
        "parameter": "auto_approve_threshold",
        "current_value": 0.90,
        "proposed_value": 0.85,
        "auto_approve_action": "suppress",
        "reduction_pp": 5.0,
    }


@pytest.mark.asyncio
async def test_drift_rule_stable_category_returns_none():
    client = _drift_client(
        recent_rows=_accuracy_rows("credential_access", 100, 84),
        prior_rows=_accuracy_rows("credential_access", 100, 85),
    )

    assert await generator.DriftThresholdRule().detect(client) is None


@pytest.mark.asyncio
async def test_drift_rule_improving_category_returns_none():
    client = _drift_client(
        recent_rows=_accuracy_rows("credential_access", 100, 85),
        prior_rows=_accuracy_rows("credential_access", 100, 80),
    )

    assert await generator.DriftThresholdRule().detect(client) is None


@pytest.mark.asyncio
async def test_drift_rule_insufficient_recent_data_returns_none():
    client = _drift_client(
        recent_rows=_accuracy_rows("credential_access", 9, 6),
        prior_rows=_accuracy_rows("credential_access", 20, 18),
    )

    assert await generator.DriftThresholdRule().detect(client) is None


@pytest.mark.asyncio
async def test_drift_rule_insufficient_prior_data_returns_none():
    client = _drift_client(
        recent_rows=_accuracy_rows("credential_access", 20, 15),
        prior_rows=_accuracy_rows("credential_access", 9, 9),
    )

    assert await generator.DriftThresholdRule().detect(client) is None


@pytest.mark.asyncio
async def test_drift_rule_no_verified_decisions_returns_none():
    client = _drift_client()

    assert await generator.DriftThresholdRule().detect(client) is None


@pytest.mark.asyncio
async def test_drift_rule_multiple_declines_chooses_worst():
    client = _drift_client(
        recent_rows=(
            _accuracy_rows("credential_access", 50, 40)
            + _accuracy_rows("insider_threat", 50, 35)
        ),
        prior_rows=(
            _accuracy_rows("credential_access", 50, 43)
            + _accuracy_rows("insider_threat", 50, 45)
        ),
    )

    signal = await generator.DriftThresholdRule().detect(client)

    assert signal.category == "insider_threat"
    assert signal.trigger_id == "insider_threat_drift"
    assert signal.evidence["decline_pp"] == 20.0


@pytest.mark.asyncio
async def test_drift_rule_both_queries_fail_returns_none(caplog):
    client = _drift_client(side_effect=RuntimeError("age unavailable"))

    with caplog.at_level(logging.WARNING):
        signal = await generator.DriftThresholdRule().detect(client)

    assert signal is None
    assert "Unable to load per-category accuracy drift trends" in caplog.text


@pytest.mark.asyncio
async def test_drift_rule_partial_query_failure_returns_none():
    client = _drift_client(
        side_effect=[
            _accuracy_rows("credential_access", 20, 10),
            RuntimeError("prior failed"),
        ]
    )

    assert await generator.DriftThresholdRule().detect(client) is None


@pytest.mark.asyncio
async def test_drift_rule_exact_threshold_fires():
    client = _drift_client(
        recent_rows=_accuracy_rows("credential_access", 100, 82),
        prior_rows=_accuracy_rows("credential_access", 100, 85),
    )

    signal = await generator.DriftThresholdRule().detect(client)

    assert signal is not None
    assert signal.evidence["decline_pp"] == 3.0


@pytest.mark.asyncio
async def test_drift_rule_just_below_threshold_does_not_fire():
    client = _drift_client(
        recent_rows=_accuracy_rows("credential_access", 1000, 820),
        prior_rows=_accuracy_rows("credential_access", 1000, 849),
    )

    assert await generator.DriftThresholdRule().detect(client) is None


@pytest.mark.asyncio
async def test_drift_rule_query_pattern_is_age_safe(monkeypatch):
    monkeypatch.setattr(generator.time, "time", lambda: 1_700_000_000.0)
    client = _drift_client(
        recent_rows=_accuracy_rows("credential_access", 20, 10),
        prior_rows=_accuracy_rows("credential_access", 20, 19),
    )

    await generator._get_per_category_accuracy_trends(client)

    queries = [call.args[0] for call in client.run_query.await_args_list]
    assert len(queries) == 2
    assert all("MATCH (d:Decision)" in query for query in queries)
    assert all("d.outcome IS NOT NULL" in query for query in queries)
    assert all("d.correct IS NOT NULL" in query for query in queries)
    assert all("d.category IS NOT NULL" in query for query in queries)
    assert all("d.verified_at_epoch >=" in query for query in queries)
    assert all("MERGE" not in query for query in queries)
    assert all("$" not in query for query in queries)
    assert all("169" in query or "170" in query for query in queries)


@pytest.mark.asyncio
async def test_drift_rule_recent_only_category_does_not_fire():
    client = _drift_client(
        recent_rows=_accuracy_rows("credential_access", 20, 10),
        prior_rows=[],
    )

    assert await generator.DriftThresholdRule().detect(client) is None


@pytest.mark.asyncio
async def test_drift_rule_prior_only_category_does_not_fire():
    client = _drift_client(
        recent_rows=[],
        prior_rows=_accuracy_rows("credential_access", 20, 19),
    )

    assert await generator.DriftThresholdRule().detect(client) is None


@pytest.mark.asyncio
async def test_drift_rule_skips_rows_missing_category_or_correctness():
    client = _drift_client(
        recent_rows=(
            _accuracy_rows("credential_access", 20, 10)
            + [{"category": "", "correct": True}, {"category": "credential_access"}]
        ),
        prior_rows=(
            _accuracy_rows("credential_access", 20, 19)
            + [{"correct": True}, {"category": "credential_access", "correct": None}]
        ),
    )

    signal = await generator.DriftThresholdRule().detect(client)

    assert signal.evidence["recent_decisions"] == 20
    assert signal.evidence["prior_decisions"] == 20


@pytest.mark.asyncio
async def test_drift_rule_coerces_correctness_values():
    client = _drift_client(
        recent_rows=[
            {"category": "credential_access", "correct": "true"} for _ in range(8)
        ] + [
            {"category": "credential_access", "correct": "false"} for _ in range(12)
        ],
        prior_rows=[
            {"category": "credential_access", "correct": 1} for _ in range(18)
        ] + [
            {"category": "credential_access", "correct": 0} for _ in range(2)
        ],
    )

    signal = await generator.DriftThresholdRule().detect(client)

    assert signal.evidence["recent_accuracy"] == 0.4
    assert signal.evidence["prior_accuracy"] == 0.9


@pytest.mark.asyncio
async def test_override_rule_generates_prompt_module_config_shape(monkeypatch):
    detector = SimpleNamespace(
        activated=True,
        example_count=3,
        examples=[{"category": "malware", "pattern": "high_conf_suppress_override"}],
        status=lambda: {
            "activated": True,
            "pattern": "high_conf_suppress_override",
            "example_count": 3,
            "threshold": 2,
        },
    )
    _patch_module(
        monkeypatch,
        "app.services.override_detector",
        SimpleNamespace(override_detector=detector),
    )
    rule = generator.OverridePromptRule()

    signal = await rule.detect(object())
    record = rule.generate_variant(signal)

    assert record.artifact_type == ARTIFACT_PROMPT_MODULE
    assert record.config == {
        "override_pattern": "high_conf_suppress_override",
        "prompt_id_current": "SUPPRESSION_v1",
        "prompt_id_variant": "SUPPRESSION_v2",
        "framing_change": "Add explicit factor contribution breakdown",
    }


@pytest.mark.asyncio
async def test_dk_rule_returns_none_under_continuous_or_null_weights(monkeypatch):
    rule = generator.DKReorderRule()
    states = [
        None,
        {"strategy": "two_phase", "dk_weights": None},
    ]

    monkeypatch.setattr(generator, "_live_dk_learning_state", lambda: states.pop(0))

    assert await rule.detect(object()) is None
    assert await rule.detect(object()) is None


@pytest.mark.asyncio
async def test_dk_rule_generates_evidence_order_config_shape(monkeypatch):
    rule = generator.DKReorderRule()
    monkeypatch.setattr(generator, "_live_dk_learning_state", lambda: {
        "strategy": "two_phase",
        "category": "credential_access",
        "dk_weights": [[0.1, 0.34, 0.2]],
        "factor_labels": [
            "asset_criticality",
            "threat_intel_enrichment",
            "campaign_correlation",
        ],
    })

    signal = await rule.detect(object())
    record = rule.generate_variant(signal)

    assert record.artifact_type == ARTIFACT_EVIDENCE_ORDER
    assert record.config == {
        "new_order": [
            "threat_intel_enrichment",
            "campaign_correlation",
            "asset_criticality",
        ],
        "top_factor": "threat_intel_enrichment",
        "top_weight": 0.34,
    }


def test_live_dk_adapter_reads_profile_scorer_path(monkeypatch):
    class Scorer:
        _learning_strategy = object()

        def get_dk_weights(self, category_index):
            assert category_index == 0
            return [0.1, 0.34, 0.2]

    real_import = generator.importlib.import_module

    def fake_import(name):
        if name == "app.services.gae_state":
            return SimpleNamespace(get_profile_scorer=lambda: Scorer())
        if name == "app.domains.soc.config":
            return SimpleNamespace(
                SOC_CATEGORIES=["credential_access"],
                SOC_FACTORS=[
                    "asset_criticality",
                    "threat_intel_enrichment",
                    "campaign_correlation",
                ],
            )
        return real_import(name)

    monkeypatch.setattr(generator.importlib, "import_module", fake_import)

    state = generator._live_dk_learning_state()

    assert state["strategy"] == "two_phase"
    assert state["category"] == "credential_access"
    assert state["dk_weights"] == [0.1, 0.34, 0.2]


@pytest.mark.asyncio
async def test_plateau_rule_fires_below_target_and_flat(monkeypatch):
    def build_accuracy_trajectory(live_data):
        assert live_data == {"credential_access": 100}
        return {
            "categories": [{
                "category": "credential_access",
                "decision_count": 100,
                "current_accuracy": 0.83,
                "mean_14d_accuracy": 0.831,
            }]
        }

    _patch_module(
        monkeypatch,
        "app.services.accuracy_trajectory",
        SimpleNamespace(build_accuracy_trajectory=build_accuracy_trajectory),
    )
    rule = generator.PlateauContextRule()
    client = AsyncMock()
    client.run_query = AsyncMock(return_value=[{"category": "credential_access", "cnt": 100}])

    signal = await rule.detect(client)
    record = rule.generate_variant(signal)

    assert signal.trigger_id == "credential_access_plateau"
    assert record.artifact_type == ARTIFACT_CONTEXT_POLICY
    assert record.config == {
        "category": "credential_access",
        "current_accuracy": 0.83,
        "theta_target": 0.85,
        "traversal_add": "campaign_correlation",
        "traversal_remove": None,
    }


@pytest.mark.asyncio
async def test_plateau_rule_does_not_fire_above_target(monkeypatch):
    def build_accuracy_trajectory(live_data):
        return {
            "categories": [{
                "category": "credential_access",
                "decision_count": 100,
                "current_accuracy": 0.86,
                "mean_14d_accuracy": 0.861,
            }]
        }

    _patch_module(
        monkeypatch,
        "app.services.accuracy_trajectory",
        SimpleNamespace(build_accuracy_trajectory=build_accuracy_trajectory),
    )
    rule = generator.PlateauContextRule()
    client = AsyncMock()
    client.run_query = AsyncMock(return_value=[{"category": "credential_access", "cnt": 100}])

    assert await rule.detect(client) is None


@pytest.mark.asyncio
async def test_coverage_gap_rule_fires_for_low_coverage_category():
    rule = generator.CoverageGapRule()
    client = _CoverageClient(_coverage_rows(credential_access=400, insider_threat=30))

    signal = await rule.detect(client)

    assert signal is not None
    assert signal.rule_id == "RULE-COVERAGE-GAP"
    assert signal.trigger_id == "insider_threat_coverage_gap"
    assert signal.artifact_type == ARTIFACT_CONTEXT_POLICY
    assert signal.category == "insider_threat"
    assert signal.evidence == {
        "category": "insider_threat",
        "current_decisions": 30,
        "max_category_decisions": 400,
        "coverage_ratio": 0.075,
        "gap_threshold": 0.15,
        "detection_method": "per_category_coverage_gap",
    }
    assert "insider_threat" in signal.description


@pytest.mark.asyncio
async def test_coverage_gap_rule_balanced_categories_return_none():
    rule = generator.CoverageGapRule()
    client = _CoverageClient(_coverage_rows(credential_access=400, malware_execution=360))

    assert await rule.detect(client) is None


@pytest.mark.asyncio
async def test_coverage_gap_rule_requires_low_absolute_total():
    rule = generator.CoverageGapRule()
    client = _CoverageClient(_coverage_rows(credential_access=1000, insider_threat=60))

    assert await rule.detect(client) is None


@pytest.mark.asyncio
async def test_coverage_gap_rule_requires_sufficient_max_category():
    rule = generator.CoverageGapRule()
    client = _CoverageClient(_coverage_rows(credential_access=99, insider_threat=10))

    assert await rule.detect(client) is None


@pytest.mark.asyncio
async def test_coverage_gap_rule_empty_graph_returns_none():
    rule = generator.CoverageGapRule()

    assert await rule.detect(_CoverageClient([])) is None


@pytest.mark.asyncio
async def test_coverage_gap_rule_chooses_lowest_ratio():
    rule = generator.CoverageGapRule()
    client = _CoverageClient(_coverage_rows(credential_access=500, insider_threat=30, cloud_infrastructure=20))

    signal = await rule.detect(client)

    assert signal.category == "cloud_infrastructure"
    assert signal.evidence["coverage_ratio"] == 0.04


@pytest.mark.asyncio
async def test_coverage_gap_rule_query_failure_returns_none():
    rule = generator.CoverageGapRule()

    assert await rule.detect(_CoverageClient(exc=RuntimeError("graph unavailable"))) is None


def test_coverage_gap_rule_generate_variant_context_policy_config():
    signal = generator.GraphSignal(
        rule_id="RULE-COVERAGE-GAP",
        trigger_id="insider_threat_coverage_gap",
        artifact_type=ARTIFACT_CONTEXT_POLICY,
        evidence={
            "category": "insider_threat",
            "current_decisions": 30,
            "max_category_decisions": 400,
            "coverage_ratio": 0.075,
        },
        category="insider_threat",
        description="Coverage gap",
    )

    record = generator.CoverageGapRule().generate_variant(signal)

    assert record.artifact_type == ARTIFACT_CONTEXT_POLICY
    assert record.config == {
        "category": "insider_threat",
        "policy": "deep_context",
        "current_decisions": 30,
        "max_category_decisions": 400,
        "coverage_ratio": 0.075,
        "description": "Extended graph traversal for under-covered insider_threat",
    }


def test_coverage_gap_rule_registered_in_default_rules():
    gen = generator.VariantGenerator()

    assert "RULE-COVERAGE-GAP" in [rule.rule_id for rule in gen.rules]


@pytest.mark.asyncio
async def test_coverage_gap_rule_warm_start_skip_prevents_generation(monkeypatch, ledger):
    monkeypatch.setattr(
        generator,
        "_consult_history",
        AsyncMock(return_value={"action": "skip", "reason": "prior rollback"}),
    )
    gen = generator.VariantGenerator(rules=[generator.CoverageGapRule()])
    client = _CoverageClient(_coverage_rows(credential_access=400, insider_threat=30))

    variants = await gen.scan_for_opportunities(client)

    assert variants == []
    assert registry.get_all_variants() == []
    ledger.assert_not_awaited()


@pytest.mark.asyncio
async def test_coverage_gap_rule_query_is_age_safe():
    rule = generator.CoverageGapRule()
    client = _CoverageClient(_coverage_rows(credential_access=400, insider_threat=30))

    await rule.detect(client)

    query = client.queries[0]
    assert "MATCH (d:Decision)" in query
    assert "MERGE" not in query
    assert "$" not in query


@pytest.mark.asyncio
async def test_coverage_gap_rule_ratio_boundary_is_exclusive():
    rule = generator.CoverageGapRule()
    client = _CoverageClient(_coverage_rows(credential_access=200, insider_threat=30))

    assert await rule.detect(client) is None


@pytest.mark.asyncio
async def test_coverage_gap_rule_count_boundary_is_exclusive():
    rule = generator.CoverageGapRule()
    client = _CoverageClient(_coverage_rows(credential_access=500, insider_threat=50))

    assert await rule.detect(client) is None


@pytest.mark.asyncio
async def test_coverage_gap_rule_single_category_returns_none():
    rule = generator.CoverageGapRule()
    client = _CoverageClient(_coverage_rows(credential_access=500))

    assert await rule.detect(client) is None


def test_context_policy_remains_not_shadow_testable():
    from app.services.shadow_runner import SHADOW_TESTABLE_ARTIFACTS

    assert ARTIFACT_CONTEXT_POLICY not in SHADOW_TESTABLE_ARTIFACTS


@pytest.mark.asyncio
async def test_register_rule_adds_runtime_rule(ledger):
    gen = generator.VariantGenerator(rules=[])

    gen.register_rule(_SignalRule())
    created = await gen.scan_for_opportunities(object())

    assert [record.variant_id for record in created] == ["variant_test"]


@pytest.mark.asyncio
async def test_generated_variant_passes_graph_context_to_ledger(ledger):
    signal = generator.GraphSignal(
        rule_id="RULE-CONTEXT",
        trigger_id="trigger-a",
        artifact_type=ARTIFACT_CONTEXT_POLICY,
        evidence={"campaign_id": "C-009", "correlation": 0.91},
        category="credential_access",
        description="context signal",
    )
    gen = generator.VariantGenerator(rules=[_SignalRule(signal)])

    await gen.scan_for_opportunities(object())

    kwargs = ledger.await_args.kwargs
    assert kwargs["graph_context"] == {"campaign_id": "C-009", "correlation": 0.91}
    assert kwargs["metadata"] == {
        "trigger_key": "RULE-CONTEXT_trigger-a",
        "rule_id": "RULE-CONTEXT",
        "warm_started": False,
    }


@pytest.mark.asyncio
async def test_record_evolution_event_called_with_variant_created(ledger):
    gen = generator.VariantGenerator(rules=[_SignalRule()])

    await gen.scan_for_opportunities(object())

    kwargs = ledger.await_args.kwargs
    assert kwargs["event_type"] == VARIANT_CREATED
    assert kwargs["before_state"] == {}
    assert kwargs["after_state"] == {"action": "escalate"}


def test_all_five_config_shapes_match_request():
    campaign = generator.CampaignEscalateRule().generate_variant(
        generator.GraphSignal(
            "RULE-CAMPAIGN-ESCALATE",
            "C-007",
            ARTIFACT_ROUTING_RULE,
            {"campaign_id": "C-007"},
            "credential_access",
            "campaign",
        )
    )
    drift = generator.DriftThresholdRule().generate_variant(
        generator.GraphSignal(
            "RULE-DRIFT-THRESHOLD",
            "insider_threat_drift",
            ARTIFACT_SCORING_THRESHOLD,
            {"current_value": 0.90, "proposed_value": 0.85},
            "insider_threat",
            "drift",
        )
    )
    override = generator.OverridePromptRule().generate_variant(
        generator.GraphSignal(
            "RULE-OVERRIDE-PROMPT",
            "high_conf_suppress_override",
            ARTIFACT_PROMPT_MODULE,
            {"override_pattern": "high_conf_suppress_override"},
            None,
            "override",
        )
    )
    dk = generator.DKReorderRule().generate_variant(
        generator.GraphSignal(
            "RULE-DK-REORDER",
            "dk_reorder",
            ARTIFACT_EVIDENCE_ORDER,
            {
                "weights": [0.34, 0.1],
                "factor_labels": ["threat_intel_enrichment", "identity_risk"],
            },
            "credential_access",
            "dk",
        )
    )
    plateau = generator.PlateauContextRule().generate_variant(
        generator.GraphSignal(
            "RULE-PLATEAU-CONTEXT",
            "credential_access_plateau",
            ARTIFACT_CONTEXT_POLICY,
            {"current_accuracy": 0.83},
            "credential_access",
            "plateau",
        )
    )

    assert campaign.config == {
        "action": "escalate",
        "trigger_categories": ["credential_access", "lateral_movement"],
        "campaign_pattern": "C-007",
        "min_confidence": 0.70,
    }
    assert drift.config == {
        "category": "insider_threat",
        "parameter": "auto_approve_threshold",
        "current_value": 0.90,
        "proposed_value": 0.85,
        "auto_approve_action": "suppress",
        "reduction_pp": 5.0,
    }
    assert override.config == {
        "override_pattern": "high_conf_suppress_override",
        "prompt_id_current": "SUPPRESSION_v1",
        "prompt_id_variant": "SUPPRESSION_v2",
        "framing_change": "Add explicit factor contribution breakdown",
    }
    assert dk.config == {
        "new_order": ["threat_intel_enrichment", "identity_risk"],
        "top_factor": "threat_intel_enrichment",
        "top_weight": 0.34,
    }
    assert plateau.config == {
        "category": "credential_access",
        "current_accuracy": 0.83,
        "theta_target": 0.85,
        "traversal_add": "campaign_correlation",
        "traversal_remove": None,
    }


def test_p16_generator_has_no_level1_imports_or_writes():
    source = inspect.getsource(generator)

    forbidden = [
        "ProfileScorer",
        "centroids",
        "build_profile_scorer",
    ]
    for token in forbidden:
        assert token not in source
