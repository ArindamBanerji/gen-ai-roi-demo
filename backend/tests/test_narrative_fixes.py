"""
Narrative fix tests -- Option A.

Checks:
  - Tab-2 subtitle is present in RuntimeEvolutionTab.tsx
  - Tab-3 subtitle is present in AlertTriageTab.tsx
  - The string literal "7823" does not appear in the narrative/reasoning
    service files (narrative.py, reasoning.py) -- those must use the alert_id
    passed at runtime, never a hardcoded ID.
  - In RuntimeEvolutionTab.tsx the string "7823" appears at most once
    (the DEFAULT_ALERT_ID constant definition). Scattered inline literals
    were the problem; the constant itself is the controlled single source.
  - AlertTriageTab.tsx has no reference to "7823".

Run from backend/ directory:
    pytest tests/test_narrative_fixes.py -v
"""

import pathlib


_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_FRONTEND_TABS = _REPO_ROOT / "frontend" / "src" / "components" / "tabs"
_BACKEND_SERVICES = _REPO_ROOT / "backend" / "app" / "services"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# test_tab2_subtitle_present
# ---------------------------------------------------------------------------

def test_tab2_subtitle_present():
    """RuntimeEvolutionTab.tsx must contain the Tab-2 subtitle text."""
    tab2 = _FRONTEND_TABS / "RuntimeEvolutionTab.tsx"
    assert tab2.exists(), f"File not found: {tab2}"
    assert "How the system's judgment has evolved" in _read(tab2), (
        "Tab-2 subtitle not found in RuntimeEvolutionTab.tsx"
    )


# ---------------------------------------------------------------------------
# test_tab3_subtitle_present
# ---------------------------------------------------------------------------

def test_tab3_subtitle_present():
    """AlertTriageTab.tsx must contain the Tab-3 subtitle text."""
    tab3 = _FRONTEND_TABS / "AlertTriageTab.tsx"
    assert tab3.exists(), f"File not found: {tab3}"
    assert "Active decisions" in _read(tab3), (
        "Tab-3 subtitle not found in AlertTriageTab.tsx"
    )


# ---------------------------------------------------------------------------
# test_alert_id_not_hardcoded
# ---------------------------------------------------------------------------

def test_alert_id_not_hardcoded():
    """
    '7823' must not appear in the narrative/reasoning service files.
    Those files must use the alert_id parameter passed at runtime.

    In RuntimeEvolutionTab.tsx '7823' is allowed exactly once -- the
    DEFAULT_ALERT_ID constant definition.  Scattered inline literals (the
    original bug) would push the count above 1.

    AlertTriageTab.tsx must have zero occurrences.
    """
    # narrative.py and reasoning.py must be clean
    for name in ("narrative.py", "reasoning.py"):
        f = _BACKEND_SERVICES / name
        assert f.exists(), f"File not found: {f}"
        assert "7823" not in _read(f), (
            f"Hardcoded '7823' found in {name} -- narrative/reasoning must use "
            "the alert_id parameter, not a hardcoded ID"
        )

    # RuntimeEvolutionTab.tsx: at most 1 occurrence (the constant definition)
    tab2 = _FRONTEND_TABS / "RuntimeEvolutionTab.tsx"
    content2 = _read(tab2)
    count = content2.count("7823")
    assert count <= 1, (
        f"Expected at most 1 occurrence of '7823' in RuntimeEvolutionTab.tsx "
        f"(the DEFAULT_ALERT_ID constant), found {count}. "
        "Inline literals must be replaced with the constant."
    )

    # AlertTriageTab.tsx: zero occurrences
    tab3 = _FRONTEND_TABS / "AlertTriageTab.tsx"
    assert "7823" not in _read(tab3), (
        "Unexpected '7823' found in AlertTriageTab.tsx"
    )
