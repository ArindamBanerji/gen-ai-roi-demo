"""
Tests for P20: EU AI Act Compliance Dashboard (L-10).
"""

from app.services.compliance_dashboard import generate_compliance_page


def test_all_five_articles():
    page = generate_compliance_page()
    articles = {a['article'] for a in page['articles']}
    assert articles == {9, 12, 13, 14, 15}


def test_all_fully_addressed():
    page = generate_compliance_page()
    for a in page['articles']:
        assert a['status'] == 'fully_addressed'


def test_article_9_mentions_conservation():
    page = generate_compliance_page()
    art9 = next(a for a in page['articles'] if a['article'] == 9)
    assert 'conservation' in art9['evidence'].lower()


def test_article_14_mentions_intervention():
    page = generate_compliance_page()
    art14 = next(a for a in page['articles'] if a['article'] == 14)
    assert 'intervention' in art14['evidence'].lower()


def test_enforcement_date():
    page = generate_compliance_page()
    assert page['enforcement_date'] == '2026-08-02'


def test_summary_counts():
    page = generate_compliance_page()
    assert page['summary']['fully_addressed'] == 5
    assert page['summary']['total_articles'] == 5
