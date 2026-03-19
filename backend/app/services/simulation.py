"""
SimulationOrchestrator — batch N alerts through the real GAE pipeline (SIM-1).

CRITICAL: every decision in a simulation follows the EXACT same code path as
a manual triage operation.  No separate scoring logic.  No shortcuts.

  alert → compute_factor_vector → score_alert → write Decision node →
  emit events → Bernoulli oracle → write outcome → learning_state.update() →
  save_learning_state → emit outcome events → log record

Reference: docs/soc_copilot_design_v1.md §14 (GAE pipeline).
"""

import asyncio
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional

import numpy as np

from app.domains.soc.config import SOCDomainConfig, LEARNING_ENABLED
from app.domains.soc.orchestrator import compute_factor_vector
from app.services.audit import record_decision as audit_record_decision
from app.services.event_bus import event_bus, DecisionMade, OutcomeVerified, GraphMutated
from app.services.gae_state import get_learning_state, save_learning_state, get_profile_scorer
from gae.scoring import score_alert


# ---------------------------------------------------------------------------
# Oracle success rates — probability the GAE selects the optimal action
# ---------------------------------------------------------------------------

_ORACLE_SUCCESS_RATES: Dict[str, float] = {
    # SIM-3a canonical categories — chosen to make learning curves diverge naturally.
    # threat_intel easiest (clear TI signal), insider hardest (all signals benign).
    "credential_access":  0.75,
    "threat_intel_match": 0.85,
    "lateral_movement":   0.65,
    "data_exfiltration":  0.70,
    "insider_threat":     0.55,
    # Legacy alert_type fallbacks (used when category is not one of the 5 above)
    "anomalous_login":    0.85,
    "phishing":           0.90,
    "malware":            0.80,
    "data_exfil":         0.75,
    "brute_force":        0.82,
    "cloud_config":       0.88,
    "privilege_escalation": 0.78,
    "credential_stuffing": 0.82,
    "c2_beacon":          0.85,
    "anomalous_behavior": 0.72,
    "unknown":            0.65,
}

# ATT&CK technique labels for experiment log enrichment
_ATTACK_TECHNIQUES: Dict[str, str] = {
    # SIM-3a canonical categories
    "credential_access":    "T1078 - Valid Accounts",
    "threat_intel_match":   "T1588 - Obtain Capabilities",
    "lateral_movement":     "T1021 - Remote Services",
    "data_exfiltration":    "T1048 - Exfiltration Over Alternative Protocol",
    "insider_threat":       "T1078.004 - Valid Accounts: Cloud Accounts",
    # Legacy alert_type fallbacks
    "anomalous_login":      "T1078 - Valid Accounts",
    "phishing":             "T1566 - Phishing",
    "malware":              "T1059 - Command and Scripting Interpreter",
    "data_exfil":           "T1041 - Exfiltration Over C2 Channel",
    "brute_force":          "T1110 - Brute Force",
    "cloud_config":         "T1537 - Transfer Data to Cloud Account",
    "privilege_escalation": "T1068 - Exploitation for Privilege Escalation",
    "credential_stuffing":  "T1110.004 - Credential Stuffing",
    "c2_beacon":            "T1071 - Application Layer Protocol",
    "anomalous_behavior":   "T1046 - Network Service Discovery",
    "unknown":              "T0000 - Unknown",
}

# ---------------------------------------------------------------------------
# Minimal fallback alert pool — used when Neo4j has no seeded alerts
# ---------------------------------------------------------------------------
# Each entry provides the fields that the 6 FactorComputers read from alert dicts:
#   TravelMatchFactor     → user_id, source_location
#   AssetCriticalityFactor→ id (alert_id), traverses Neo4j
#   ThreatIntelFactor     → id, traverses Neo4j
#   PatternHistoryFactor  → alert_type, traverses Neo4j
#   TimeAnomalyFactor     → weekend_login, business_hours_login
#   DeviceTrustFactor     → mfa_completed, device_fingerprint_match, vpn_provider

_FALLBACK_POOL: List[Dict[str, Any]] = [
    # One representative alert per SIM-3a canonical category.
    # Used only when get_alert_pool() raises (import error at test-time).
    # ground_truth_action mirrors ALERT_CATEGORIES ground_truth_action values.
    {
        "alert_id": "FB-CA-001", "id": "FB-CA-001",
        "alert_type": "anomalous_login",  "category": "credential_access",
        "ground_truth_action": "suppress",
        "user_id": "sim-ca-user1@company.com", "source_location": "Tokyo",
        "business_hours_login": False, "weekend_login": False,
        "mfa_completed": False, "device_fingerprint_match": False, "vpn_provider": None,
    },
    {
        "alert_id": "FB-TI-001", "id": "FB-TI-001",
        "alert_type": "threat_intel_match", "category": "threat_intel_match",
        "ground_truth_action": "escalate",
        "user_id": "sim-ti-user@company.com", "source_location": "External",
        "business_hours_login": True, "weekend_login": False,
        "mfa_completed": True, "device_fingerprint_match": True, "vpn_provider": "corporate-vpn",
    },
    {
        "alert_id": "FB-LM-001", "id": "FB-LM-001",
        "alert_type": "privilege_escalation", "category": "lateral_movement",
        "ground_truth_action": "escalate",
        "user_id": "sim-lm-svc@internal", "source_location": "Internal",
        "business_hours_login": False, "weekend_login": False,
        "mfa_completed": False, "device_fingerprint_match": False, "vpn_provider": None,
    },
    {
        "alert_id": "FB-DE-001", "id": "FB-DE-001",
        "alert_type": "data_exfil", "category": "data_exfiltration",
        "ground_truth_action": "escalate",
        "user_id": "sim-de-user@company.com", "source_location": "External",
        "business_hours_login": False, "weekend_login": True,
        "mfa_completed": False, "device_fingerprint_match": False, "vpn_provider": None,
    },
    {
        "alert_id": "FB-IT-001", "id": "FB-IT-001",
        "alert_type": "insider_threat", "category": "insider_threat",
        "ground_truth_action": "investigate",
        "user_id": "sim-it-user@company.com", "source_location": "Office",
        "business_hours_login": True, "weekend_login": False,
        "mfa_completed": True, "device_fingerprint_match": True, "vpn_provider": "corporate-vpn",
    },
]


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class SimulationResult:
    n_decisions:           int
    overall_accuracy:      float
    category_accuracy:     Dict[str, float]        # Bernoulli oracle accuracy per category
    weight_trajectory:     List[List[List[float]]] # W snapshot per step
    experiment_log:        List[Dict[str, Any]]    # full structured records
    duration_seconds:      float
    ground_truth_accuracy: float                   # fraction where predicted == ground truth
    category_ground_truth: Dict[str, float]        # per-category ground-truth match rate


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class SimulationOrchestrator:
    """
    Runs batch simulation through the real GAE pipeline.

    Each simulated decision follows the same path as a manual triage:
      alert → classify_situation → compute_factors → score_entity →
      decide → outcome → update_weights

    Parameters
    ----------
    state_manager :
        The new StateManager (services/state_manager.py).
        Stored for extensibility; soft_reset() is called by the router
        before instantiating the orchestrator.
    triage_service :
        Reserved for future use (pipeline functions called directly).
    domain_config : DomainConfig
        Active domain configuration.
    """

    def __init__(self, state_manager, triage_service, domain_config):
        self.state_manager   = state_manager
        self.triage_service  = triage_service
        self.domain_config   = domain_config
        self.experiment_log: List[Dict[str, Any]] = []

    async def run(
        self,
        n_decisions: int,
        alert_pool: List[Dict[str, Any]],
        speed_ms: int = 200,
        on_progress: Optional[Callable] = None,
    ) -> SimulationResult:
        """
        Run n_decisions through the GAE pipeline.

        For each decision:
          1. Pick alert from pool (round-robin)
          2. Fetch full alert data from Neo4j (same as POST /api/alert/analyze)
          3. Run compute_factor_vector (same pipeline)
          4. score_alert → select action (same pipeline)
          5. Write Decision node to Neo4j with factor_vector stored (R4)
          6. Emit DecisionMade + GraphMutated events
          7. Generate outcome: Bernoulli oracle with category success rate
          8. Update Decision node outcome in Neo4j (same as POST /api/alert/outcome)
          9. Read factor_vector back from graph + call learning_state.update() (same pipeline)
         10. save_learning_state()
         11. Emit OutcomeVerified + GraphMutated events
         12. Log structured experiment record
         13. Call on_progress callback if provided
         14. Yield for speed_ms milliseconds

        Parameters
        ----------
        n_decisions : int
        alert_pool  : list of alert dicts (from Neo4j or fallback pool)
        speed_ms    : milliseconds to sleep between decisions (0 = no delay)
        on_progress : optional async callable(step, total, record)

        Returns
        -------
        SimulationResult
        """
        from app.db.neo4j import neo4j_client
        from app.services.situation import analyze_situation

        start_ts = time.perf_counter()
        self.experiment_log = []

        computers = SOCDomainConfig.get_factor_computers()
        actions   = SOCDomainConfig.get_actions()
        tau       = SOCDomainConfig.get_temperature()

        correct_total = 0
        correct_by_category: Dict[str, int] = {}
        total_by_category:   Dict[str, int] = {}
        weight_trajectory:   List[List[List[float]]] = []
        gt_correct_total = 0
        gt_correct_by_category: Dict[str, int] = {}

        for step in range(n_decisions):
            # ------------------------------------------------------------------
            # Step 1: Pick alert (round-robin across categories)
            # ------------------------------------------------------------------
            alert_meta          = alert_pool[step % len(alert_pool)]
            alert_id            = alert_meta.get("alert_id") or alert_meta.get("id")
            category            = alert_meta.get("category") or alert_meta.get("alert_type", "unknown")
            ground_truth_action = alert_meta.get("ground_truth_action", "investigate")

            # ------------------------------------------------------------------
            # Step 2: Fetch full alert data from Neo4j
            # (same as POST /api/alert/analyze → neo4j_client.get_alert)
            # ------------------------------------------------------------------
            try:
                alert_data = await neo4j_client.get_alert(alert_id)
            except Exception:
                alert_data = None
            if alert_data is None:
                # Synthetic fallback: use pool dict itself as alert_data
                alert_data = dict(alert_meta)

            alert_type = alert_data.get("alert_type") or category

            # ------------------------------------------------------------------
            # Step 3: Situation analysis
            # (same as POST /api/alert/analyze → analyze_situation)
            # ------------------------------------------------------------------
            try:
                ctx = await neo4j_client.get_security_context(alert_id)
            except Exception:
                ctx = None
            if not ctx:
                ctx = {"alert_type": alert_type}

            try:
                situation = analyze_situation(alert_type, ctx)
                situation_type = situation.situation_type
            except Exception:
                situation_type = "unknown"

            # ------------------------------------------------------------------
            # Step 4: Compute factor vector
            # (same as POST /api/alert/analyze → compute_factor_vector)
            # ------------------------------------------------------------------
            f      = await compute_factor_vector(alert_data, computers, neo4j_client)
            f_2d   = f.reshape(1, -1)
            fv_list = f.flatten().tolist()

            # ------------------------------------------------------------------
            # Step 5: GAE scoring — capture W snapshot BEFORE update
            # (same as POST /api/alert/analyze → score_alert)
            # ------------------------------------------------------------------
            W          = get_learning_state().W
            W_snapshot = W.tolist()          # capture before weight update
            scoring    = score_alert(f_2d, W, actions, tau)

            # Ground-truth comparison: deterministic, independent of Bernoulli oracle.
            correct_vs_ground_truth = (scoring.selected_action == ground_truth_action)

            # ------------------------------------------------------------------
            # Step 6: Write Decision node to Neo4j with f(t) stored (R4)
            # Uses the exact same Cypher as triage.py analyze_alert.
            # MATCH is used (not MERGE) to stay on the identical code path.
            # For synthetic alerts the MATCH returns 0 rows so no node is
            # written — the fallback in step 9 covers the weight update.
            # ------------------------------------------------------------------
            decision_id = str(uuid.uuid4())
            await neo4j_client.run_query(
                """
                MATCH (a:Alert {id: $alert_id})
                CREATE (d:Decision {
                    id:            $decision_id,
                    action:        $action,
                    confidence:    $confidence,
                    factor_vector: $fv,
                    timestamp:     datetime(),
                    outcome:       null
                })
                CREATE (d)-[:DECIDED_ON]->(a)
                """,
                {
                    "alert_id":    alert_id,
                    "decision_id": decision_id,
                    "action":      scoring.selected_action,
                    "confidence":  scoring.confidence,
                    "fv":          fv_list,
                },
            )

            # ------------------------------------------------------------------
            # Step 7: Emit DecisionMade + GraphMutated
            # (every graph mutation MUST emit events)
            # ------------------------------------------------------------------
            await event_bus.emit(DecisionMade(
                alert_id      = alert_id,
                action        = scoring.selected_action,
                confidence    = scoring.confidence,
                factor_vector = tuple(fv_list),
            ))
            await event_bus.emit(GraphMutated(
                mutation_type     = "decision",
                affected_entities = (alert_id,),
            ))

            # ------------------------------------------------------------------
            # Step 8: Oracle outcome — Bernoulli sample
            # ------------------------------------------------------------------
            success_rate = _ORACLE_SUCCESS_RATES.get(category, 0.70)
            correct      = random.random() < success_rate
            outcome_int  = +1 if correct else -1
            outcome_str  = "correct" if correct else "incorrect"

            # ------------------------------------------------------------------
            # Step 9: Update Decision node + retrieve f(t) from graph (R4)
            # (same Cypher as POST /api/alert/outcome → gae_result query)
            # ------------------------------------------------------------------
            gae_result = await neo4j_client.run_query(
                """
                MATCH (d:Decision {id: $decision_id})
                SET d.outcome    = $outcome_label,
                    d.correct    = $correct,
                    d.verified_at = datetime()
                RETURN d.factor_vector AS factor_vector,
                       d.action        AS action,
                       d.confidence    AS confidence
                """,
                {
                    "decision_id":   decision_id,
                    "outcome_label": outcome_str,
                    "correct":       correct,
                },
            )

            # Read f from graph result; fall back to locally-computed vector
            # (fallback is only taken for synthetic alerts with no Decision node)
            if gae_result and gae_result[0].get("factor_vector") is not None:
                f_for_update = np.array(
                    gae_result[0]["factor_vector"], dtype=np.float64
                ).reshape(1, -1)
            else:
                f_for_update = f_2d

            # ------------------------------------------------------------------
            # Step 10: Weight update
            # (same as POST /api/alert/outcome → learning_state.update)
            # ------------------------------------------------------------------
            action_index = (
                actions.index(scoring.selected_action)
                if scoring.selected_action in actions
                else 0
            )
            learning_state = get_learning_state()
            learning_state.update(
                action_index           = action_index,
                action_name            = scoring.selected_action,
                outcome                = outcome_int,
                f                      = f_for_update,
                confidence_at_decision = scoring.confidence,
            )
            save_learning_state()

            # CORR-2: ProfileScorer.update() — gated by LEARNING_ENABLED (default False).
            # gt_action_index derived from ground_truth_action (always available in simulation).
            if LEARNING_ENABLED:
                from app.domains.soc.config import resolve_alert_category, SOCDomainConfig as _SDC_sim
                _cat_name_sim = resolve_alert_category(category)
                _cat_idx_sim  = _SDC_sim().get_category_index(_cat_name_sim)
                _gt_idx_sim   = actions.index(ground_truth_action) if ground_truth_action in actions else action_index
                get_profile_scorer().update(
                    f=f_for_update.flatten(),
                    category_index=_cat_idx_sim,
                    action_index=action_index,
                    correct=correct,
                    gt_action_index=_gt_idx_sim,
                )

            # ------------------------------------------------------------------
            # Step 11: Emit OutcomeVerified + GraphMutated
            # (every graph mutation MUST emit events)
            # ------------------------------------------------------------------
            await event_bus.emit(OutcomeVerified(
                alert_id    = alert_id,
                decision_id = decision_id,
                outcome     = outcome_str,
                correct     = correct,
            ))
            await event_bus.emit(GraphMutated(
                mutation_type     = "outcome",
                affected_entities = (alert_id, decision_id),
            ))

            # ------------------------------------------------------------------
            # Step 12: Accuracy accounting (Bernoulli oracle + ground truth)
            # ------------------------------------------------------------------
            correct_total                      += int(correct)
            total_by_category[category]        = total_by_category.get(category, 0) + 1
            correct_by_category[category]      = correct_by_category.get(category, 0) + int(correct)
            gt_correct_total                   += int(correct_vs_ground_truth)
            gt_correct_by_category[category]   = gt_correct_by_category.get(category, 0) + int(correct_vs_ground_truth)
            weight_trajectory.append(W_snapshot)

            cumulative_accuracy = correct_total / (step + 1)
            cat_accuracy_now    = {
                cat: correct_by_category.get(cat, 0) / total_by_category[cat]
                for cat in total_by_category
            }

            # ------------------------------------------------------------------
            # Step 12b: Write to Evidence Ledger (FIX-B)
            # Uses the same audit.record_decision() as execute_action() in
            # triage.py so simulation decisions appear in the Evidence Ledger
            # (Tab 4 / GET /api/audit/decisions).
            # ------------------------------------------------------------------
            audit_record_decision(
                alert_id       = alert_id,
                situation_type = situation_type,
                action_taken   = scoring.selected_action,
                factors        = [c.name for c in computers],
                confidence     = scoring.confidence,
            )

            # ------------------------------------------------------------------
            # Step 13: Log structured experiment record
            # ------------------------------------------------------------------
            record = self._log_decision(
                step                    = step,
                alert_id                = alert_id,
                category                = category,
                situation_type          = situation_type,
                factor_vector           = fv_list,
                W_snapshot              = W_snapshot,
                action                  = scoring.selected_action,
                confidence              = scoring.confidence,
                outcome_int             = outcome_int,
                correct                 = correct,
                cumulative_accuracy     = cumulative_accuracy,
                category_accuracy       = cat_accuracy_now,
                ground_truth_action     = ground_truth_action,
                correct_vs_ground_truth = correct_vs_ground_truth,
            )

            # ------------------------------------------------------------------
            # Step 14: Progress callback
            # ------------------------------------------------------------------
            if on_progress:
                await on_progress(step + 1, n_decisions, record)

            # ------------------------------------------------------------------
            # Step 15: Speed control
            # ------------------------------------------------------------------
            if speed_ms > 0:
                await asyncio.sleep(speed_ms / 1000.0)

        # -----------------------------------------------------------------------
        # Aggregate results
        # -----------------------------------------------------------------------
        duration = time.perf_counter() - start_ts
        overall_accuracy = correct_total / n_decisions if n_decisions else 0.0
        gt_overall = gt_correct_total / n_decisions if n_decisions else 0.0
        final_cat_accuracy = {
            cat: correct_by_category.get(cat, 0) / total_by_category[cat]
            for cat in total_by_category
        }
        final_cat_gt = {
            cat: gt_correct_by_category.get(cat, 0) / total_by_category[cat]
            for cat in total_by_category
        }

        return SimulationResult(
            n_decisions           = n_decisions,
            overall_accuracy      = round(overall_accuracy, 4),
            category_accuracy     = {k: round(v, 4) for k, v in final_cat_accuracy.items()},
            weight_trajectory     = weight_trajectory,
            experiment_log        = self.experiment_log,
            duration_seconds      = round(duration, 3),
            ground_truth_accuracy = round(gt_overall, 4),
            category_ground_truth = {k: round(v, 4) for k, v in final_cat_gt.items()},
        )

    def _log_decision(
        self,
        step:                    int,
        alert_id:                str,
        category:                str,
        situation_type:          str,
        factor_vector:           List[float],
        W_snapshot:              List[List[float]],
        action:                  str,
        confidence:              float,
        outcome_int:             int,
        correct:                 bool,
        cumulative_accuracy:     float,
        category_accuracy:       Dict[str, float],
        ground_truth_action:     str,
        correct_vs_ground_truth: bool,
    ) -> Dict[str, Any]:
        """
        Append a structured experiment record to self.experiment_log and return it.

        Record schema
        -------------
        step                    : int       — 0-indexed decision number
        timestamp               : iso8601
        alert_id                : str
        category                : str       — alert category (maps to oracle rate)
        situation_type          : str       — from SituationAnalysis
        attack_technique        : str       — ATT&CK label
        factor_vector           : [float]   — 6-element vector
        W_snapshot              : [[float]] — full W matrix at decision time (before update)
        predicted_action        : str
        confidence              : float
        oracle_outcome          : int       — +1 correct, -1 incorrect (Bernoulli)
        correct                 : bool      — Bernoulli oracle result
        ground_truth_action     : str       — expert-defined optimal action
        correct_vs_ground_truth : bool      — predicted_action == ground_truth_action
        cumulative_accuracy     : float
        category_accuracy       : {str: float}
        """
        record: Dict[str, Any] = {
            "step":                    step,
            "timestamp":               datetime.now(timezone.utc).isoformat(),
            "alert_id":                alert_id,
            "category":                category,
            "situation_type":          situation_type,
            "attack_technique":        _ATTACK_TECHNIQUES.get(category, "T0000 - Unknown"),
            "factor_vector":           factor_vector,
            "W_snapshot":              W_snapshot,
            "predicted_action":        action,
            "confidence":              round(confidence, 4),
            "oracle_outcome":          outcome_int,
            "correct":                 correct,
            "ground_truth_action":     ground_truth_action,
            "correct_vs_ground_truth": correct_vs_ground_truth,
            "cumulative_accuracy":     round(cumulative_accuracy, 4),
            "category_accuracy":       {k: round(v, 4) for k, v in category_accuracy.items()},
        }
        self.experiment_log.append(record)
        return record
