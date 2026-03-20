from app.services.benchmarking_level2 import Level2BenchmarkingSection

MOCK_DATA = {
    'group_a': {'acceptance_rate': 0.70, 'accuracy': 0.69,
                'resolution_time': 1.4, 'reward': 0.72, 'n_decisions': 380},
    'group_b': {'acceptance_rate': 0.80, 'accuracy': 0.79,
                'resolution_time': 1.2, 'reward': 0.80, 'n_decisions': 385},
    'variant_promoted': True,
    'decisions_to_promotion': 143,
    'conservation_breached': False,
    'p_value': 0.001,
    'cohens_d': 3.7
}


def test_four_subsections():
    section = Level2BenchmarkingSection()
    result = section.generate_section(MOCK_DATA)
    assert 'subsection_1_ab_comparison' in result
    assert 'subsection_2_promotion_timeline' in result
    assert 'subsection_3_conservation' in result
    assert 'subsection_4_narrative' in result


def test_ab_comparison_metrics():
    section = Level2BenchmarkingSection()
    result = section.generate_section(MOCK_DATA)
    metrics = result['subsection_1_ab_comparison']['metrics']
    assert len(metrics) == 3
    assert metrics[0]['delta'] > 0  # Group B better


def test_promotion_recorded():
    section = Level2BenchmarkingSection()
    result = section.generate_section(MOCK_DATA)
    timeline = result['subsection_2_promotion_timeline']
    assert timeline['variant_promoted'] is True
    assert timeline['decisions_to_promotion'] == 143


def test_conservation_never_breached():
    section = Level2BenchmarkingSection()
    result = section.generate_section(MOCK_DATA)
    cons = result['subsection_3_conservation']
    assert cons['status'] == 'never_breached'


def test_narrative_readable():
    section = Level2BenchmarkingSection()
    result = section.generate_section(MOCK_DATA)
    narrative = result['subsection_4_narrative']
    assert 'acceptance rate' in narrative
    assert 'conservation law' in narrative
    assert 'promoted' in narrative


def test_no_promotion_case():
    data = {**MOCK_DATA, 'variant_promoted': False, 'decisions_to_promotion': None}
    section = Level2BenchmarkingSection()
    result = section.generate_section(data)
    assert 'not yet' in result['subsection_4_narrative']
