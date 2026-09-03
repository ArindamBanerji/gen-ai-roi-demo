from __future__ import annotations

from pathlib import Path


MAIN_PY = Path(__file__).resolve().parents[1] / "app" / "main.py"
DEV_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:5176",
    "http://localhost:5177",
]


def _source() -> str:
    return MAIN_PY.read_text(encoding="utf-8")


def test_soc_does_not_allow_wildcard_cors() -> None:
    source = _source()
    assert 'allow_origins=["*"]' not in source
    assert "allow_origins=['*']" not in source


def test_soc_uses_cors_origins_env() -> None:
    source = _source()
    assert "CORS_ORIGINS" in source
    assert "ALLOWED_ORIGINS" in source
    assert '.split(",")' in source
    assert "origin.strip()" in source
    assert "if origin.strip()" in source


def test_soc_default_dev_origins_include_expected_ports() -> None:
    source = _source()
    for origin in DEV_ORIGINS:
        assert origin in source


def test_soc_preserves_existing_cors_flags() -> None:
    source = _source()
    assert "allow_credentials=_cors_credentials()" in source
    assert 'allow_methods=["GET", "POST", "PUT", "DELETE"]' in source
    assert 'allow_headers=["Content-Type", "Authorization"]' in source


def test_soc_configures_preflight_cache() -> None:
    assert "max_age=600" in _source()


def test_dev_mode_disables_credentials_for_wildcard_origin() -> None:
    source = _source()
    assert "CORS_DEV_MODE" in source
    assert 'return ["*"]' in source
    assert 'return "*" not in _cors_origins()' in source
