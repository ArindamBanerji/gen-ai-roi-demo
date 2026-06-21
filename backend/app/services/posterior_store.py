"""PostgreSQL persistence for RL Phase 2 Beta posteriors.

This store intentionally uses a small relational table in the existing
PostgreSQL instance. It does not use AGE graph nodes or Cypher.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

log = logging.getLogger(__name__)

DEFAULT_POSTERIOR_DSN = "postgresql://postgres:postgres@localhost:5433/soc_copilot?connect_timeout=5"
POSTERIOR_HEALTH_CONNECT_TIMEOUT_SECONDS = 2


def _default_posteriors(n_categories: int, n_actions: int) -> dict[str, list[list[float]]]:
    return {
        "alphas": [[1.0 for _ in range(n_actions)] for _ in range(n_categories)],
        "betas": [[1.0 for _ in range(n_actions)] for _ in range(n_categories)],
    }


class PosteriorStore:
    """Tiny fail-open PostgreSQL store for per-category/action Beta posteriors."""

    def __init__(self, dsn: str | None = None) -> None:
        self._dsn = dsn or self._resolve_dsn()
        self._table_ready = False

    @staticmethod
    def _resolve_dsn() -> str:
        for name in ("POSTERIOR_DSN", "GRAPH_DSN", "AGE_DSN", "DATABASE_URL"):
            value = os.getenv(name)
            if value:
                return value
        return DEFAULT_POSTERIOR_DSN

    def save(self, alphas: list[list[float]], betas: list[list[float]]) -> None:
        """Persist all posterior parameters using DELETE + INSERT in one transaction."""
        try:
            self._ensure_table()
            rows = []
            updated_epoch = int(time.time() * 1000)
            for category_index, alpha_row in enumerate(alphas):
                beta_row = betas[category_index] if category_index < len(betas) else []
                for action_index, alpha in enumerate(alpha_row):
                    beta = beta_row[action_index] if action_index < len(beta_row) else 1.0
                    rows.append(
                        (
                            int(category_index),
                            int(action_index),
                            float(alpha),
                            float(beta),
                            updated_epoch,
                        )
                    )
            import psycopg

            conn: Any
            with psycopg.connect(self._dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM rl_posteriors")
                    cur.executemany(
                        """
                        INSERT INTO rl_posteriors
                            (category, action, alpha, beta, updated_epoch)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        rows,
                    )
        except Exception as exc:
            log.warning("[PosteriorStore] save failed: %s", exc)

    def load(self, n_categories: int, n_actions: int) -> dict[str, list[list[float]]]:
        """Load posterior parameters; return uninformative priors on failure."""
        posteriors = _default_posteriors(n_categories, n_actions)
        try:
            self._ensure_table()
            import psycopg

            conn: Any
            with psycopg.connect(self._dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT category, action, alpha, beta FROM rl_posteriors")
                    for category, action, alpha, beta in cur.fetchall():
                        category_index = int(category)
                        action_index = int(action)
                        if 0 <= category_index < n_categories and 0 <= action_index < n_actions:
                            posteriors["alphas"][category_index][action_index] = float(alpha)
                            posteriors["betas"][category_index][action_index] = float(beta)
        except Exception as exc:
            log.warning("[PosteriorStore] load failed: %s", exc)
        return posteriors

    def log_reset(self, reason: str) -> None:
        log.info("[PosteriorStore] posteriors reset: %s", reason)

    def clear(self) -> None:
        try:
            self._ensure_table()
            import psycopg

            conn: Any
            with psycopg.connect(self._dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM rl_posteriors")
        except Exception as exc:
            log.warning("[PosteriorStore] clear failed: %s", exc)

    def health_check(self) -> dict[str, Any]:
        """Return storage health without mutating posterior state."""
        try:
            self._ping_storage()
        except Exception as exc:
            return {"healthy": False, "error": str(exc)}
        return {"healthy": True}

    def _ping_storage(self) -> None:
        import psycopg

        conn: Any
        with psycopg.connect(
            self._dsn,
            connect_timeout=POSTERIOR_HEALTH_CONNECT_TIMEOUT_SECONDS,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")

    def _ensure_table(self) -> None:
        if self._table_ready:
            return
        import psycopg

        conn: Any
        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS rl_posteriors (
                        category INTEGER NOT NULL,
                        action INTEGER NOT NULL,
                        alpha DOUBLE PRECISION DEFAULT 1.0,
                        beta DOUBLE PRECISION DEFAULT 1.0,
                        updated_epoch BIGINT,
                        PRIMARY KEY (category, action)
                    )
                    """
                )
        self._table_ready = True
