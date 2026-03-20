from app.services.benchmarking_report import BenchmarkingEngine, BenchmarkingReport


class MockDB:
    def run_query(self, query, params=None):
        return []


def test_accuracy_both_correct():
    decisions = [
        {'system_action': 'escalate', 'analyst_action': 'escalate',
         'gt_action': 'escalate', 'category': 'credential_access'}
    ] * 10
    engine = BenchmarkingEngine(MockDB())
    result = engine._compute_accuracy(decisions)
    assert result['system_accuracy'] == 1.0
    assert result['analyst_accuracy'] == 1.0
    assert result['disagreement_rate'] == 0.0


def test_system_wins_disagreement():
    decisions = [
        {'system_action': 'escalate', 'analyst_action': 'monitor',
         'gt_action': 'escalate', 'category': 'credential_access'}
    ]
    engine = BenchmarkingEngine(MockDB())
    result = engine._compute_accuracy(decisions)
    assert result['system_correct_on_disagreements'] == 1
    assert result['analyst_correct_on_disagreements'] == 0


def test_consistency_math():
    # 7 agreed, 3 disagreed -> o_bar = 0.7, (1-0.7)^2 = 0.09
    decisions = (
        [{'system_action': 'escalate', 'analyst_action': 'escalate',
          'gt_action': 'escalate', 'category': 'c'}] * 7 +
        [{'system_action': 'escalate', 'analyst_action': 'monitor',
          'gt_action': 'escalate', 'category': 'c'}] * 3
    )
    engine = BenchmarkingEngine(MockDB())
    result = engine._compute_consistency(decisions, 85.0)
    assert abs(result['guaranteed_consistency'] - 0.09) < 0.02


def test_executive_summary_readable():
    report = BenchmarkingReport(
        period_start='2026-01-01', period_end='2026-03-31',
        total_decisions=500,
        system_accuracy=0.89, analyst_accuracy=0.85,
        disagreement_rate=0.15,
        system_correct_on_disagreements=45,
        analyst_correct_on_disagreements=30,
        per_category_accuracy={},
        iks_start=20, iks_end=55, iks_delta=35,
        categories_calibrated=4,
        system_acceptance_rate=0.70,
        guaranteed_consistency=0.09,
        estimated_annual_savings={'net_annual_savings': 94000,
                                  'duplicate_effort': 0, 'escalation_churn': 0,
                                  'mttr_improvement': 0, 'error_cost_offset': 0,
                                  'assumptions': {}}
    )
    engine = BenchmarkingEngine(MockDB())
    summary = engine.format_executive_summary(report)
    assert 'verified decisions' in summary
    assert '$' in summary
    assert 'consistent' in summary


def test_empty_decisions():
    engine = BenchmarkingEngine(MockDB())
    result = engine._compute_accuracy([])
    assert result['system_accuracy'] == 0.0


def test_per_category_breakdown():
    decisions = (
        [{'system_action': 'escalate', 'analyst_action': 'escalate',
          'gt_action': 'escalate', 'category': 'credential_access'}] * 5 +
        [{'system_action': 'monitor', 'analyst_action': 'monitor',
          'gt_action': 'monitor', 'category': 'insider_threat'}] * 3
    )
    engine = BenchmarkingEngine(MockDB())
    result = engine._compute_accuracy(decisions)
    assert 'credential_access' in result['per_category_accuracy']
    assert 'insider_threat' in result['per_category_accuracy']
