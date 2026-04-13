"""
H7-FIX-1 tests: process_outcome() no longer returns PAT-TRAVEL-001 for
non-travel alert categories.

Run from backend/ directory:
    pytest tests/test_h7_fix1.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def test_category_pattern_map_complete():
    """Every SOC category must map to a pattern that is not PAT-TRAVEL-001."""
    from app.domains.soc.config import SOCDomainConfig, SOC_CATEGORIES
    cfg = SOCDomainConfig()
    for cat in SOC_CATEGORIES:
        pattern = cfg.get_pattern_for_category(cat)
        assert pattern != "PAT-TRAVEL-001", (
            f"Category {cat!r} still returns PAT-TRAVEL-001"
        )
        assert pattern.startswith("PAT-"), f"Invalid pattern for {cat!r}: {pattern!r}"


def test_get_pattern_for_known_categories():
    """Known categories return their canonical patterns."""
    from app.domains.soc.config import SOCDomainConfig
    cfg = SOCDomainConfig()
    assert cfg.get_pattern_for_category("credential_access") == "PAT-CRED-001"
    assert cfg.get_pattern_for_category("insider_threat") == "PAT-INSIDER-001"
    assert cfg.get_pattern_for_category("data_exfiltration") == "PAT-EXFIL-001"


def test_get_pattern_for_unknown_category():
    """Unknown category falls back to PAT-UNKNOWN-001, not PAT-TRAVEL-001."""
    from app.domains.soc.config import SOCDomainConfig
    cfg = SOCDomainConfig()
    result = cfg.get_pattern_for_category("nonexistent_category")
    assert result == "PAT-UNKNOWN-001"


def test_pat_travel_001_not_returned_for_non_travel():
    """Non-travel categories must never return PAT-TRAVEL-001."""
    from app.domains.soc.config import SOCDomainConfig
    cfg = SOCDomainConfig()
    non_travel = [
        "credential_access",
        "malware_execution",
        "data_exfiltration",
        "insider_threat",
        "cloud_infrastructure",
    ]
    for cat in non_travel:
        assert cfg.get_pattern_for_category(cat) != "PAT-TRAVEL-001", (
            f"{cat!r} should not return PAT-TRAVEL-001"
        )


def test_all_patterns_unique():
    """Each category maps to a unique pattern ID."""
    from app.domains.soc.config import SOCDomainConfig, SOC_CATEGORIES
    cfg = SOCDomainConfig()
    patterns = [cfg.get_pattern_for_category(c) for c in SOC_CATEGORIES]
    assert len(patterns) == len(set(patterns)), (
        "Each category should map to a unique pattern; "
        f"got duplicates in: {patterns}"
    )


def test_backend_import_clean():
    """Backend imports cleanly and category lookup works end-to-end."""
    from app.main import app  # noqa: F401 — import side-effect check
    from app.domains.soc.config import SOCDomainConfig
    cfg = SOCDomainConfig()
    assert cfg.get_pattern_for_category("lateral_movement") == "PAT-LATERAL-001"
