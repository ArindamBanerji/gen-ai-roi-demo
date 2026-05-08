from app.services.three_claims import generate_three_claims


def test_three_claims_present():
    result = generate_three_claims()
    assert len(result['claims']) == 3


def test_all_unconditional():
    result = generate_three_claims()
    for claim in result['claims']:
        assert claim['unconditional'] is True


def test_claim_31_consistency():
    result = generate_three_claims()
    c31 = next(c for c in result['claims'] if c['id'] == 'CLAIM-31')
    assert 'consistent' in c31['headline'].lower()
    assert '144' in c31['explanation']


def test_claim_38_convergence():
    result = generate_three_claims()
    c38 = next(c for c in result['claims'] if c['id'] == 'CLAIM-38')
    assert 'calibrate' in c38['headline'].lower()
    assert '13.51' in c38['metric']


def test_conservation_law():
    result = generate_three_claims()
    cl = next(c for c in result['claims'] if c['id'] == 'conservation_law')
    assert 'silently degrade' in cl['headline']
    assert '23.53' in cl['metric']


def test_footer_mentions_a4():
    result = generate_three_claims()
    assert 'A=4' in result['footer']
