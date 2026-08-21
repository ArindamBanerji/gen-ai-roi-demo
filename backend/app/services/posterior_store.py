"""PostgreSQL persistence for RL Phase 2 Beta posteriors.

This store intentionally uses a small relational table in the existing
PostgreSQL instance. It does not use AGE graph nodes or Cypher.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from copilot_sdk.config import GraphConfig

log = logging.getLogger(__name__)

POSTERIOR_HEALTH_CONNECT_TIMEOUT_SECONDS = 2


def _default_posteriors(n_categories: int, n_actions: int) -> dict[str, list[list[float]]]:
    return {
        "alphas": [[1.0 for _ in range(n_actions)] for _ in range(n_categories)],
        "betas": [[1.0 for _ in range(n_actions)] for _ in range(n_categories)],
    }


class PosteriorStore:
    """Tiny PostgreSQL store for per-category/action Beta posteriors."""

    _UNSET = object()

    def __init__(self, graph_config: GraphConfig | str | None = _UNSET) -> None:
        """Create a store from the typed SOC graph configuration.

        A raw DSN remains accepted only for existing unit-level storage tests;
        application code passes ``GraphConfig`` explicitly.  Passing ``None``
        is an error so a missing graph contract cannot silently become an
        in-memory posterior store.
        """
        was_unset = graph_config is self._UNSET
        if was_unset:
            graph_config = GraphConfig.load(
                "soc",
                profile="test" if os.environ.get("PYTEST_CURRENT_TEST") else "production",
            )
        if graph_config is None:
            raise ValueError("PosteriorStore requires GraphConfig")

        self._graph_config = graph_config if isinstance(graph_config, GraphConfig) else None
        if isinstance(graph_config, str):
            self._dsn = graph_config
        else:
            if not isinstance(graph_config, GraphConfig):
                raise TypeError("PosteriorStore requires GraphConfig")
            if not graph_config.dsn:
                raise ValueError("PosteriorStore requires GraphConfig with a DSN")
            self._dsn = graph_config.dsn
            # POSTERIOR_DSN is deliberately limited to test runs.  It is a
            # storage endpoint override, not a replacement for GraphConfig.
            if was_unset and os.environ.get("PYTEST_CURRENT_TEST"):
                self._dsn = self._resolve_dsn()
        self._table_ready = False

    @staticmethod
    def _resolve_dsn() -> str:
        # POSTERIOR_DSN is an explicit test-only override. Production graph
        # connection settings remain owned by the typed GraphConfig.
        if os.environ.get("PYTEST_CURRENT_TEST"):
            override = os.environ.get("POSTERIOR_DSN", "").strip()
            if override:
                if "sslmode" not in override:
                    sep = "&" if "?" in override else "?"
                    override += f"{sep}sslmode=disable"
                return override
        config = GraphConfig.load(
            "soc",
            profile="test" if os.environ.get("PYTEST_CURRENT_TEST") else "production",
        )
        if not config.dsn:
            raise RuntimeError("SOC GraphConfig does not provide a posterior DSN")
        return config.dsn

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
            raise RuntimeError("[PosteriorStore] save failed") from exc

    def load(self, n_categories: int, n_actions: int) -> dict[str, list[list[float]]]:
        """Load posterior parameters; surface storage failures."""
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
            raise RuntimeError("[PosteriorStore] load failed") from exc
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
            raise RuntimeError("[PosteriorStore] clear failed") from exc

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
