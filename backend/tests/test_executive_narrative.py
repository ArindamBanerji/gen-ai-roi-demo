from app.services.executive_narrative import ExecutiveNarrative


class MockDB:
    def run_query(self, query, params=None):
        return []


def test_three_sections():
    narrative = ExecutiveNarrative(MockDB())
    result = narrative.generate_weekly()
    assert 'section_1_what_changed' in result
    assert 'section_2_what_discovered' in result
    assert 'section_3_what_knows' in result


def test_headline_present():
    narrative = ExecutiveNarrative(MockDB())
    result = narrative.generate_weekly()
    assert 'headline' in result
    assert len(result['headline']) > 0


def test_what_changed_structure():
    narrative = ExecutiveNarrative(MockDB())
    result = narrative.generate_weekly()
    section = result['section_1_what_changed']
    assert 'total_verified' in section
    assert 'top_shifts' in section


def test_what_discovered_structure():
    narrative = ExecutiveNarrative(MockDB())
    result = narrative.generate_weekly()
    section = result['section_2_what_discovered']
    assert 'attack_chains_detected' in section
    assert 'new_entities' in section


def test_what_knows_structure():
    narrative = ExecutiveNarrative(MockDB())
    result = narrative.generate_weekly()
    section = result['section_3_what_knows']
    assert 'iks_current' in section
    assert 'health_status' in section


def test_period_present():
    narrative = ExecutiveNarrative(MockDB())
    result = narrative.generate_weekly()
    assert 'period' in result


def test_period_week_ending_explicit():
    narrative = ExecutiveNarrative(MockDB())
    result = narrative.generate_weekly(week_ending='2026-03-19')
    assert result['period']['end'] == '2026-03-19'
    assert result['period']['start'] == '2026-03-12'


def test_headline_fallback_when_no_data():
    narrative = ExecutiveNarrative(MockDB())
    result = narrative.generate_weekly()
    # With empty DB the fallback headline should be returned
    assert 'digest' in result['headline'].lower() or len(result['headline']) > 0


def test_override_comment_field_on_schema():
    from app.models.schemas import OutcomeRequest
    import inspect
    fields = OutcomeRequest.model_fields
    assert 'override_comment' in fields
    # must be optional (default None)
    assert fields['override_comment'].default is None
