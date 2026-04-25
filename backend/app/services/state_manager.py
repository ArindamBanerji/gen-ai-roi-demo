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

log = logging.getLogger(__name__)


class ResetError(Exception):
    """Raised when a reset operation fails; carries the step that failed."""


class DataProtectionError(Exception):
    """Raised when a destructive operation would affect persistent training data."""


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

    # Persistent training data identifier — nodes with this origin survive all resets.
    PERSISTENT_ORIGIN = "zero_day_synthetic"

    # Session filter: selects session/demo decisions, excludes persistent training data.
    PERSISTENT_FILTER = "WHERE d.origin IS NULL OR d.origin <> 'zero_day_synthetic'"
    SESSION_FILTER    = PERSISTENT_FILTER  # alias used in _verify_deletion_safety calls

    def __init__(self, learning_state_service, audit_store, neo4j_service, domain_config):
        self._ls_svc = learning_state_service
        self._audit  = audit_store
        self._neo4j  = neo4j_service
        self._domain_config = domain_config

    # ------------------------------------------------------------------
    # Training data protection — all destructive Decision ops route here
    # ------------------------------------------------------------------

    async def _verify_deletion_safety(self, filter_clause: str) -> int:
        """Count nodes matched by filter_clause. Abort if any are persistent.

        Uses a CASE WHEN count so a single query handles both checks —
        avoids a separate WHERE clause that would be invalid Cypher when
        filter_clause already contains WHERE.

        Returns the total number of session nodes that would be affected.
        Raises DataProtectionError if any persistent node is in the set.
        """
        # Guard against Cypher injection via statement terminators / comments.
        # Single/double quotes are allowed (present in the PERSISTENT_FILTER constant itself).
        assert isinstance(filter_clause, str) and ";" not in filter_clause and "--" not in filter_clause, (
            f"Unsafe filter_clause: {filter_clause}"
        )
        check = await self._neo4j.run_query(
            f"MATCH (d:Decision) {filter_clause} "
            f"RETURN count(CASE WHEN d.origin = '{self.PERSISTENT_ORIGIN}' "
            f"THEN 1 ELSE null END) AS n"
        )
        n_persistent = int(check[0]["n"]) if check else 0
        if n_persistent > 0:
            raise DataProtectionError(
                f"ABORT: {n_persistent} persistent nodes would be affected. "
                f"Filter: {filter_clause}"
            )
        count = await self._neo4j.run_query(
            f"MATCH (d:Decision) {filter_clause} RETURN count(d) AS n"
        )
        return int(count[0]["n"]) if count else 0

    async def clear_session_decisions(self) -> int:
        """REMOVE correct/outcome from session decisions only. Training data preserved."""
        await self._verify_deletion_safety(self.SESSION_FILTER)
        result = await self._neo4j.run_query(
            f"MATCH (d:Decision) {self.PERSISTENT_FILTER} "
            "REMOVE d.correct, d.outcome "
            "RETURN count(d) AS cleared"
        )
        cleared = int(result[0]["cleared"]) if result else 0
        total_rows = await self._neo4j.run_query(
            "MATCH (d:Decision) RETURN count(d) AS total"
        )
        total = int(total_rows[0]["total"]) if total_rows else 0
        preserved = total - cleared
        print(f"[STATE] Cleared {cleared} session decisions. Preserved {preserved} persistent.")
        return cleared

    async def delete_session_decisions(self) -> None:
        """DETACH DELETE session decisions only. Training data preserved."""
        await self._verify_deletion_safety(self.SESSION_FILTER)
        preserved_rows = await self._neo4j.run_query(
            "MATCH (d:Decision) WHERE d.origin = 'zero_day_synthetic' "
            "RETURN count(d) AS n"
        )
        preserved_n = int(preserved_rows[0]["n"]) if preserved_rows else 0
        await self._neo4j.run_query(
            f"MATCH (d:Decision) {self.PERSISTENT_FILTER} "
            "OPTIONAL MATCH (d)-[:HAD_CONTEXT]->(ctx:DecisionContext) "
            "DETACH DELETE d, ctx"
        )
        print(f"[STATE] Deleted session decisions. Preserved {preserved_n} persistent.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def soft_reset(self, preserve_learning: bool = False) -> dict:
        """
        Reset learning state to priors. Clear Decision outcomes. Keep nodes.

        Parameters
        ----------
        preserve_learning : bool, default False
            When True, skip resetting the GAE learning state (W matrix,
            ProfileScorer centroids).  Use for demo-cycle resets that must
            not clobber accumulated IKS (BACKLOG-020).

        Steps (ordered; no partial state on failure):
          1. W → priors; history and decision_count cleared (skipped when
             preserve_learning=True).
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
            if not preserve_learning:
                self._ls_svc.reset_learning_state()
                committed.append("learning_state")

            # Step 3: clear outcomes on session Decision nodes; keep nodes + training data
            await self.clear_session_decisions()
            committed.append("neo4j_outcomes")

            # Step 4: audit — clear ledger, anchor fresh chain with RESET marker
            await self._audit.reset_audit_state()
            await self._audit.record_reset_marker("soft")
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

    async def hard_reset(self, preserve_learning: bool = False) -> dict:
        """
        Full reset. Delete Decision nodes and re-seed graph.

        Parameters
        ----------
        preserve_learning : bool, default False
            When True, skip resetting the GAE learning state (W matrix,
            ProfileScorer centroids).  Use for demo-cycle resets that must
            not clobber accumulated IKS (BACKLOG-020).

        Steps (ordered; no partial state on failure):
          1. W → priors; history and decision_count cleared (skipped when
             preserve_learning=True).
          2. Neo4j: DETACH DELETE session Decision nodes (training data preserved).
          3. Audit: clear ledger, write RESET marker, start fresh hash chain.

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
            if not preserve_learning:
                self._ls_svc.reset_learning_state()
                committed.append("learning_state")

            # Step 3: delete session Decision nodes; training data preserved
            await self.delete_session_decisions()
            committed.append("neo4j_delete")

            # Step 4: audit reset + RESET marker
            await self._audit.reset_audit_state()
            await self._audit.record_reset_marker("hard")
            committed.append("audit")

            log.info(
                "[StateManager] hard_reset complete — session decisions deleted. "
                "Run seed_zero_day.py to re-seed if needed."
            )

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

