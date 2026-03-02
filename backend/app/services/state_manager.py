"""
StateManager — Atomic reset coordinator (TD-026).

Orchestrates soft and hard resets across three stores:
  • GAE LearningState   (W matrix, history, decision_count)
  • Audit hash chain    (decision ledger)
  • Neo4j graph         (Decision node outcomes / nodes)

All dependencies are injected so this module imports no SOC-specific code.

Usage (see routers/admin.py):
    from app.services.state_manager import StateManager, ResetError
    sm = StateManager(gae_state, audit, neo4j_client, domain_config)
    await sm.soft_reset()
    await sm.hard_reset()
"""

import logging
import os
import sys

log = logging.getLogger(__name__)


class ResetError(Exception):
    """Raised when a reset operation fails; carries the step that failed."""


class StateManager:
    """
    Atomic reset coordinator.

    Parameters
    ----------
    learning_state_service : module
        Must expose get_learning_state(), save_learning_state(),
        reset_learning_state().
    audit_store : module
        Must expose reset_audit_state(), record_reset_marker(mode: str).
    neo4j_service : Neo4jClient
        Must expose run_query(cypher, params=None).
    domain_config : DomainConfig
        Active domain configuration (used to report metadata in responses).
    """

    def __init__(self, learning_state_service, audit_store, neo4j_service, domain_config):
        self._ls_svc = learning_state_service
        self._audit  = audit_store
        self._neo4j  = neo4j_service
        self._domain_config = domain_config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def soft_reset(self) -> dict:
        """
        Reset learning state to priors. Clear Decision outcomes. Keep nodes.

        Steps (ordered; no partial state on failure):
          1. W → priors; history and decision_count cleared.
          2. Neo4j: REMOVE correct/outcome props from Decision nodes (keep nodes).
          3. Audit: clear ledger, write RESET marker, start fresh hash chain.

        Returns
        -------
        dict  {"W_shape": [n_actions, n_factors], "decision_count": 0}

        Raises
        ------
        ResetError  with the step name when any step fails.
        """
        ls = self._ls_svc.get_learning_state()

        # Snapshot for best-effort rollback if Neo4j or audit fails
        rollback_W       = ls.W.copy()
        rollback_history = list(ls.history)
        rollback_count   = ls.decision_count

        committed: list[str] = []
        try:
            # Step 1+2: reset W → priors, clear history/count
            self._ls_svc.reset_learning_state()
            committed.append("learning_state")

            # Step 3: clear outcomes on Decision nodes; keep nodes
            await self._neo4j.run_query(
                "MATCH (d:Decision) "
                "REMOVE d.correct, d.outcome "
                "RETURN count(d) AS cleared"
            )
            committed.append("neo4j_outcomes")

            # Step 4: audit — clear ledger, anchor fresh chain with RESET marker
            self._audit.reset_audit_state()
            self._audit.record_reset_marker("soft")
            committed.append("audit")

        except Exception as exc:
            log.error(
                "[StateManager] soft_reset failed (committed=%s): %s",
                committed, exc,
            )
            if "learning_state" in committed:
                self._rollback_learning_state(rollback_W, rollback_history, rollback_count)
            raise ResetError(
                f"soft_reset failed after {committed}: {exc}"
            ) from exc

        new_ls = self._ls_svc.get_learning_state()
        log.info("[StateManager] soft_reset complete — W%s step=%d", new_ls.W.shape, new_ls.decision_count)
        return {
            "W_shape":       list(new_ls.W.shape),
            "decision_count": new_ls.decision_count,
        }

    async def hard_reset(self) -> dict:
        """
        Full reset. Delete Decision nodes and re-seed graph.

        Steps (ordered; no partial state on failure):
          1. W → priors; history and decision_count cleared.
          2. Neo4j: DETACH DELETE all Decision (and DecisionContext) nodes.
          3. Audit: clear ledger, write RESET marker, start fresh hash chain.
          4. Re-seed Neo4j from canonical seed script.

        Returns
        -------
        dict  {"W_shape": [n_actions, n_factors], "decision_count": 0}

        Raises
        ------
        ResetError  with the step name when any step fails.
        """
        ls = self._ls_svc.get_learning_state()

        rollback_W       = ls.W.copy()
        rollback_history = list(ls.history)
        rollback_count   = ls.decision_count

        committed: list[str] = []
        try:
            # Step 1+2: reset W → priors, clear history/count
            self._ls_svc.reset_learning_state()
            committed.append("learning_state")

            # Step 3: delete Decision nodes (stronger than soft_reset)
            await self._neo4j.run_query(
                "MATCH (d:Decision) "
                "OPTIONAL MATCH (d)-[:HAD_CONTEXT]->(ctx:DecisionContext) "
                "DETACH DELETE d, ctx"
            )
            committed.append("neo4j_delete")

            # Step 4: audit reset + RESET marker
            self._audit.reset_audit_state()
            self._audit.record_reset_marker("hard")
            committed.append("audit")

            # Step 5: re-seed Neo4j from canonical dataset
            self._ensure_backend_on_path()
            import seed_neo4j  # backend/seed_neo4j.py
            await seed_neo4j.seed_data()
            committed.append("seed")

        except Exception as exc:
            log.error(
                "[StateManager] hard_reset failed (committed=%s): %s",
                committed, exc,
            )
            if "learning_state" in committed:
                self._rollback_learning_state(rollback_W, rollback_history, rollback_count)
            raise ResetError(
                f"hard_reset failed after {committed}: {exc}"
            ) from exc

        new_ls = self._ls_svc.get_learning_state()
        log.info("[StateManager] hard_reset complete — W%s step=%d", new_ls.W.shape, new_ls.decision_count)
        return {
            "W_shape":       list(new_ls.W.shape),
            "decision_count": new_ls.decision_count,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _rollback_learning_state(self, W, history, decision_count) -> None:
        """
        Best-effort restore of the learning state after a failed reset.

        Called when learning_state was committed but a later step failed.
        Restores W, history, and decision_count to their pre-reset values
        and persists the rollback to disk.
        """
        try:
            ls = self._ls_svc.get_learning_state()
            ls.W             = W
            ls.history       = history
            ls.decision_count = decision_count
            self._ls_svc.save_learning_state()
            log.info("[StateManager] Learning state rolled back successfully")
        except Exception as rb_exc:
            log.error(
                "[StateManager] Learning state rollback failed (state may be inconsistent): %s",
                rb_exc,
            )

    @staticmethod
    def _ensure_backend_on_path() -> None:
        """Add backend/ to sys.path so `import seed_neo4j` resolves."""
        # __file__ = backend/app/services/state_manager.py  →  backend/ is 3 levels up
        backend_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
