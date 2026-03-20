"""
Tests for P21: Transparency Page (L-11).
"""

from app.services.transparency_page import generate_transparency_page


def test_three_levels():
    page = generate_transparency_page()
    assert 'level_1_analyst' in page
    assert 'level_2_ciso' in page
    assert 'level_3_auditor' in page


def test_limitations_always_present():
    page = generate_transparency_page()
    assert 'limitations' in page
    assert len(page['limitations']['items']) >= 5


def test_analyst_level_no_equations():
    page = generate_transparency_page()
    for section in page['level_1_analyst']['sections']:
        assert 'eta' not in section['content'].lower()
        assert 'sigma' not in section['content'].lower()


def test_auditor_has_equations():
    page = generate_transparency_page()
    contents = ' '.join(s['content'] for s in page['level_3_auditor']['sections'])
    assert 'tau=0.1' in contents
    assert 'ECE=0.036' in contents


def test_limitations_mention_synthetic():
    page = generate_transparency_page()
    lim_text = ' '.join(page['limitations']['items'])
    assert 'synthetic' in lim_text.lower()


def test_ciso_mentions_iks():
    page = generate_transparency_page()
    contents = ' '.join(s['content'] for s in page['level_2_ciso']['sections'])
    assert 'IKS' in contents
