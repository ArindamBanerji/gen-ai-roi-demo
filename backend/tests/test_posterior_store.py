import os

import pytest

from app.services.posterior_store import PosteriorStore


def _db_dsn() -> str | None:
    return os.getenv("POSTERIOR_DSN") or os.getenv("DATABASE_URL")


def _require_pg() -> str:
    dsn = _db_dsn()
    if not dsn:
        pytest.skip("PostgreSQL DSN unavailable")
    try:
        import psycopg

        with psycopg.connect(dsn) as conn:
            conn.execute("SELECT 1")
    except Exception as exc:
        pytest.skip(f"PostgreSQL unavailable: {exc}")
    return dsn


@pytest.fixture()
def pg_store():
    dsn = _require_pg()
    store = PosteriorStore(dsn)
    store._ensure_table()
    import psycopg

    with psycopg.connect(dsn) as conn:
        original_rows = conn.execute(
            "SELECT category, action, alpha, beta, updated_epoch FROM rl_posteriors"
        ).fetchall()
    store.clear()
    try:
        yield store
    finally:
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM rl_posteriors")
                cur.executemany(
                    """
                    INSERT INTO rl_posteriors
                        (category, action, alpha, beta, updated_epoch)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    original_rows,
                )


def test_table_creation(pg_store):
    pg_store.load(6, 4)
    import psycopg

    with psycopg.connect(pg_store._dsn) as conn:
        exists = conn.execute("SELECT to_regclass(%s)", ("public.rl_posteriors",)).fetchone()[0]
    assert exists == "rl_posteriors"


def test_save_load_round_trip_for_6x4_arrays(pg_store):
    alphas = [[float(c + a + 1) for a in range(4)] for c in range(6)]
    betas = [[float((c + 1) * (a + 1)) for a in range(4)] for c in range(6)]
    pg_store.save(alphas, betas)
    loaded = pg_store.load(6, 4)
    assert loaded["alphas"] == alphas
    assert loaded["betas"] == betas


def test_invalid_dsn_load_returns_defaults():
    store = PosteriorStore("postgresql://postgres:postgres@localhost:1/missing?connect_timeout=1")
    assert store.load(2, 3) == {
        "alphas": [[1.0, 1.0, 1.0], [1.0, 1.0, 1.0]],
        "betas": [[1.0, 1.0, 1.0], [1.0, 1.0, 1.0]],
    }


def test_invalid_dsn_save_does_not_raise_and_logs_warning(caplog):
    store = PosteriorStore("postgresql://postgres:postgres@localhost:1/missing?connect_timeout=1")
    store.save([[1.0]], [[1.0]])
    assert "save failed" in caplog.text


def test_clear_removes_rows_and_load_returns_defaults(pg_store):
    pg_store.save([[2.0]], [[3.0]])
    pg_store.clear()
    assert pg_store.load(1, 1) == {"alphas": [[1.0]], "betas": [[1.0]]}


def test_log_reset_does_not_raise(pg_store):
    pg_store.log_reset("unit_test")


def test_dsn_resolution_respects_posterior_dsn(monkeypatch):
    monkeypatch.setenv("POSTERIOR_DSN", "postgresql://example/posterior")
    monkeypatch.setenv("DATABASE_URL", "postgresql://example/database")
    assert PosteriorStore()._dsn == "postgresql://example/posterior?sslmode=disable"


def test_load_ignores_rows_outside_requested_shape(pg_store):
    pg_store.save([[2.0, 3.0], [4.0, 5.0]], [[6.0, 7.0], [8.0, 9.0]])
    loaded = pg_store.load(1, 1)
    assert loaded == {"alphas": [[2.0]], "betas": [[6.0]]}
