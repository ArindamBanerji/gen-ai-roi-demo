from app.domains.soc import severity
from app.framework.feedback_base import get_reward_summary
from app.framework.feedback_store import FEEDBACK_GIVEN
from app.services import rl_engine
from app.services.rl_engine import ChainCredit, RewardComputer, RewardLedger


def _result(outcome="correct"):
    return RewardComputer("soc", {"credential_access": {"base": 0.70}}).compute(
        "escalate",
        outcome,
        "credential_access",
        {},
    )


def test_append_creates_entry():
    ledger = RewardLedger()
    entry = ledger.append("D-1", _result(), "credential_access", "escalate", alert_id="A-1")
    assert entry.decision_id == "D-1"
    assert entry.alert_id == "A-1"
    assert entry.schema_version == 1


def test_append_only_behavior():
    ledger = RewardLedger()
    ledger.append("D-1", _result(), "credential_access", "escalate")
    ledger.append("D-2", _result("incorrect"), "credential_access", "escalate")
    assert [entry["decision_id"] for entry in ledger.get_entries()] == ["D-1", "D-2"]


def test_empty_summary():
    assert RewardLedger().get_summary() == {
        "total_entries": 0,
        "correct": 0,
        "incorrect": 0,
        "cumulative_graded_reward": 0,
        "avg_reward_weight": 0.0,
        "schema_version": 1,
    }


def test_summary_with_data():
    ledger = RewardLedger()
    ledger.append("D-1", _result(), "credential_access", "escalate")
    ledger.append("D-2", _result("incorrect"), "credential_access", "escalate")
    summary = ledger.get_summary()
    assert summary["total_entries"] == 2
    assert summary["correct"] == 1
    assert summary["incorrect"] == 1
    assert summary["cumulative_graded_reward"] == -13.3


def test_get_entries_limit():
    ledger = RewardLedger()
    for idx in range(3):
        ledger.append(f"D-{idx}", _result(), "credential_access", "escalate")
    assert [entry["decision_id"] for entry in ledger.get_entries(limit=2)] == ["D-1", "D-2"]


def test_reward_ledger_retention_drops_oldest_entries(monkeypatch):
    monkeypatch.setattr(RewardLedger, "MAX_ENTRIES", 3)
    ledger = RewardLedger()
    for idx in range(5):
        ledger.append(f"D-{idx}", _result(), "credential_access", "escalate")

    assert [entry["decision_id"] for entry in ledger.get_entries(limit=10)] == ["D-2", "D-3", "D-4"]
    assert ledger.get_summary()["total_entries"] == 3


def test_reward_ledger_retention_drops_oldest_chain_credits(monkeypatch):
    monkeypatch.setattr(RewardLedger, "MAX_CHAIN_CREDITS", 2)
    ledger = RewardLedger()
    for idx in range(4):
        ledger.add_chain_credit(ChainCredit(f"D-{idx}", "D-target", 0.5, 1.0, idx))

    credits = ledger.get_chain_credits("D-target")
    assert [credit["source_decision_id"] for credit in credits] == ["D-2", "D-3"]


def test_reset_clears():
    ledger = RewardLedger()
    ledger.append("D-1", _result(), "credential_access", "escalate")
    ledger.add_chain_credit(ChainCredit("D-1", "D-0", 0.5, 1.0, 1))
    ledger.reset()
    assert ledger.get_entries() == []
    assert ledger.get_chain_credits() == []


def test_reward_ledger_separate_from_feedback_given():
    FEEDBACK_GIVEN.clear()
    ledger = RewardLedger()
    ledger.append("D-1", _result(), "credential_access", "escalate")
    assert FEEDBACK_GIVEN == {}


def test_feature_flag_gates_graded_summary(monkeypatch):
    from app.domains.soc import config as soc_config

    FEEDBACK_GIVEN.clear()
    rl_engine.reset_rl_state()
    ledger = rl_engine.get_reward_ledger()
    ledger.append("D-1", _result(), "credential_access", "escalate")

    monkeypatch.setattr(soc_config, "RL_REWARD_LEDGER_ENABLED", False)
    disabled = get_reward_summary()
    assert "graded" not in disabled

    monkeypatch.setattr(soc_config, "RL_REWARD_LEDGER_ENABLED", True)
    enabled = get_reward_summary()
    assert enabled["graded"]["total_entries"] == 1
    rl_engine.reset_rl_state()


def test_severity_loader_loads_json_and_default_fallback():
    severity.reset_severity_cache()
    weights = severity.get_severity_weights()
    assert weights["credential_access"]["base"] == 0.70
    assert severity.get_category_severity("missing") == 0.50
