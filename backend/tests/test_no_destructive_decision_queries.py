"""
Verify that ONLY state_manager.py runs destructive queries on Decision nodes.
Any other file is a data wipe risk and must use StateManager instead.
"""
import os
import re
import pytest

ALLOWED_FILES = {
    "app/services/state_manager.py",
}

DESTRUCTIVE_PATTERNS = [
    re.compile(
        r'MATCH\s+\([^)]*:Decision[^)]*\).*?DETACH\s+DELETE',
        re.DOTALL | re.IGNORECASE,
    ),
    re.compile(
        r'MATCH\s+\([^)]*:Decision[^)]*\).*?REMOVE\s+\w+\.correct',
        re.DOTALL | re.IGNORECASE,
    ),
    re.compile(
        r'MATCH\s+\([^)]*:Decision[^)]*\).*?REMOVE\s+\w+\.outcome',
        re.DOTALL | re.IGNORECASE,
    ),
]


def test_no_destructive_decision_queries_outside_state_manager():
    """Only StateManager may run destructive queries on Decision nodes."""
    violations = []
    for root, dirs, files in os.walk("app"):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for fname in files:
            if not fname.endswith(".py"):
                continue
            filepath = os.path.join(root, fname).replace("\\", "/")
            if filepath in ALLOWED_FILES:
                continue
            with open(os.path.join(root, fname), encoding="utf-8", errors="replace") as f:
                content = f.read()
            for pattern in DESTRUCTIVE_PATTERNS:
                if pattern.search(content):
                    violations.append(filepath)
                    break

    assert violations == [], (
        "Destructive Decision queries found outside StateManager:\n"
        + "\n".join(f"  - {v}" for v in violations)
        + "\nRefactor to use StateManager.clear_session_decisions() "
        "or StateManager.delete_session_decisions()"
    )
