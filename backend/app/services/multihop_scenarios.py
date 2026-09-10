"""Stage 1 SOC multi-hop scenario adapters for demo investigation traces.

PLANTED SYNTHETIC — POSITIVE CONTROL — NOT A MEASUREMENT OF VLD VALUE ON REAL DECISIONS.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, cast

import numpy as np

from app.domains.soc.config import SOCDomainConfig
from app.models.investigation import InvestigationResult, InvestigationStep
from app.services.investigation_router import InvestigationRouter

ROOT = Path(__file__).resolve().parents[2]
STAGE1_PATH = ROOT / "data" / "soc_multihop_stage1.json"
FACTOR_NAMES = [
    "privileged_identity_context",
    "asset_criticality",
    "threat_intel_enrichment",
    "time_anomaly",
    "pattern_history",
    "device_trust",
]
SHOWCASE_SCENARIO_IDS = [
    "SOC-MH-002-v1",
    "SOC-MH-004-v1",
    "SOC-MH-005-v1",
    "SOC-MH-003-v1",
]


class ScenarioGraphStore:
    """Read-only graph adapter backed by one Stage 1 scenario."""

    def __init__(self, scenario: dict[str, Any]) -> None:
        self.scenario = scenario
        self.hops = {int(h["step"]): h for h in scenario.get("decision_tree", {}).get("hops", [])}
        self.correct_by_step = {int(k): list(v) for k, v in scenario.get("correct_branches", {}).items()}
        self.available_by_step = {int(k): list(v) for k, v in scenario.get("available_branches", {}).items()}
        self.misleading = set(scenario.get("misleading_branches", []))
        self.read_costs = {str(k): int(v) for k, v in scenario.get("read_costs", {}).items()}
        self.nodes = {str(n.get("id")): dict(n) for n in scenario.get("graph_nodes", [])}
        self.edges = [dict(e) for e in scenario.get("graph_edges", [])]

    def get_alert(self, alert_id: str) -> dict[str, Any] | None:
        alert = dict(self.scenario.get("alert", {}))
        if alert_id in {alert.get("alert_id"), alert.get("id")}:
            return alert
        for node in self.nodes.values():
            if node.get("type") == "Alert" and node.get("id") == alert_id:
                return {**dict(node.get("properties", {})), "alert_id": alert_id}
        return None

    def get_security_context(self, alert_id: str) -> dict[str, Any]:
        return {
            "alert_id": alert_id,
            "scenario_id": self.scenario.get("scenario_id"),
            "scenario_type": self.scenario.get("scenario_type"),
            "branching_kind": self.scenario.get("branching_kind"),
            "rho_planted": self.scenario.get("rho_planted"),
            "surface_factors": self.scenario.get("alert", {}).get("surface_factors", {}),
            "nodes_consulted": len(self.nodes),
            "edges_consulted": len(self.edges),
            "origin": "planted_multihop_stage1",
        }

    def get_evidence(self, branch_name: str, step: int | None = None) -> dict[str, Any]:
        step = int(step or self.step_for_branch(branch_name) or 1)
        hop = self.hops.get(step, {})
        correct = branch_name in self.correct_by_step.get(step, [])
        misleading = branch_name in self.misleading
        factor = str(hop.get("factor_enriched") or "pattern_history")
        new_value = float(hop.get("factor_new_value", 0.5))
        if misleading:
            new_value = 1.0 - new_value
        elif not correct:
            new_value = 0.5
        return {
            "branch_name": branch_name,
            "step": step,
            "correct_branch": correct,
            "misleading_branch": misleading,
            "evidence_source": hop.get("evidence_source", branch_name),
            "evidence_found": hop.get("evidence_found", "neutral evidence"),
            "question": hop.get("question", "Which branch should be read next?"),
            "narration": hop.get("narration", "Checked planted multi-hop evidence."),
            "factor_enriched": factor,
            "factor_new_value": max(0.0, min(1.0, new_value)),
            "evidence_keys": [branch_name, factor, "evidence_found", "narration"],
            "selected_edge": edge_for_branch(branch_name),
            "read_cost": self.read_costs.get(branch_name, 1),
        }

    def step_for_branch(self, branch_name: str) -> int | None:
        for step, branches in self.available_by_step.items():
            if branch_name in branches:
                return step
        return None

    def get_neighbors(self, node_id: str, edge_type: str | None = None, node_type: str | None = None) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for edge in self.edges:
            if edge.get("from") != node_id:
                continue
            if edge_type is not None and edge.get("type") != edge_type:
                continue
            node = self.nodes.get(str(edge.get("to")))
            if not node:
                continue
            if node_type is not None and node.get("type") != node_type:
                continue
            out.append(node)
        return out


class ScenarioFactorProvider:
    """Computes vectors from Stage 1 surface_factors plus admitted evidence."""

    async def compute(self, alert: dict[str, Any], context: Any) -> tuple[np.ndarray, dict[str, dict[str, Any]]]:
        vector = surface_vector(alert)
        evidence_items = getattr(context, "admitted_evidence", []) or []
        for evidence in evidence_items:
            factor = evidence.get("factor_enriched")
            if factor in FACTOR_NAMES:
                vector[FACTOR_NAMES.index(str(factor))] = float(evidence.get("factor_new_value", vector[FACTOR_NAMES.index(str(factor))]))
        provenance = {name: {"value": float(vector[i]), "source": "stage1_multihop"} for i, name in enumerate(FACTOR_NAMES)}
        return vector, provenance


class ScenarioEvidenceContext:
    def __init__(self, admitted_evidence: list[dict[str, Any]]) -> None:
        self.admitted_evidence = list(admitted_evidence)


def load_stage1_scenarios(path: Path = STAGE1_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return list(json.loads(path.read_text(encoding="utf-8"))["scenarios"])


def scenario_by_alert_id(alert_id: str) -> dict[str, Any] | None:
    for scenario in load_stage1_scenarios():
        alert = scenario.get("alert", {})
        ids = {str(alert.get("alert_id") or ""), str(alert.get("id") or "")}
        ids.update(str(node.get("id") or "") for node in scenario.get("graph_nodes", []) if node.get("type") == "Alert")
        if alert_id in ids:
            return scenario
    return None


def scenario_by_id(scenario_id: str) -> dict[str, Any] | None:
    for scenario in load_stage1_scenarios():
        if scenario.get("scenario_id") == scenario_id:
            return scenario
    return None


def surface_vector(alert: dict[str, Any]) -> np.ndarray:
    factors = alert.get("surface_factors", {})
    return cast(np.ndarray, np.asarray([float(factors.get(name, 0.5)) for name in FACTOR_NAMES], dtype=np.float64))


def branch_category(branch: str) -> str:
    mapping = {
        "auth": "credential_access",
        "identity": "credential_access",
        "credential": "credential_access",
        "token": "credential_access",
        "session": "credential_access",
        "hr": "insider_threat",
        "peer": "insider_threat",
        "behavior": "insider_threat",
        "process": "malware_execution",
        "command": "malware_execution",
        "scanner": "malware_execution",
        "campaign": "malware_execution",
        "exploit": "malware_execution",
        "patch": "malware_execution",
        "source_host": "lateral_movement",
        "host": "lateral_movement",
        "network": "lateral_movement",
        "pivot": "lateral_movement",
        "group": "lateral_movement",
        "egress": "data_exfiltration",
        "volume": "data_exfiltration",
        "destination": "data_exfiltration",
        "asset_scope": "data_exfiltration",
        "change": "cloud_infrastructure",
        "config": "cloud_infrastructure",
        "api": "cloud_infrastructure",
        "role": "cloud_infrastructure",
        "deploy": "cloud_infrastructure",
    }
    for token, category in mapping.items():
        if token in branch:
            return str(category)
    return "credential_access"


def edge_for_branch(branch: str) -> str:
    if "auth" in branch:
        return "HAS_AUTH_TRAIL"
    if "process" in branch:
        return "TRIGGERED_BY"
    if "host" in branch or "network" in branch or "pivot" in branch:
        return "CONNECTED_TO"
    if "hr" in branch:
        return "HAS_EMPLOYMENT_CONTEXT"
    if "peer" in branch or "behavior" in branch:
        return "MEMBER_OF_COHORT"
    if "change" in branch:
        return "COVERED_BY_CHANGE"
    if "group" in branch:
        return "MEMBER_OF"
    if "role" in branch:
        return "BINDS_ROLE"
    if "campaign" in branch:
        return "MEMBER_OF"
    return "READS"


def choose_branch(scenario: dict[str, Any], step: int, v: np.ndarray, scorer: Any, *, force_correct: bool = False) -> str | None:
    available = list(scenario.get("available_branches", {}).get(str(step), []))
    if not available:
        return None
    correct = list(scenario.get("correct_branches", {}).get(str(step), []))
    if force_correct and correct:
        return str(correct[0])
    distances = InvestigationRouter({}).category_distances(v, scorer)
    order = sorted(distances, key=lambda category: distances[category])
    rank = {category: idx for idx, category in enumerate(order)}
    return str(sorted(available, key=lambda b: (rank.get(branch_category(str(b)), 999), str(b)))[0])


def _score_best(v: np.ndarray, scorer: Any) -> Any:
    return InvestigationRouter({}).score_best_from_centroids(v, scorer)


def _apply_evidence(v: np.ndarray, evidence: dict[str, Any]) -> np.ndarray:
    out = v.copy()
    factor = evidence.get("factor_enriched")
    if factor in FACTOR_NAMES:
        out[FACTOR_NAMES.index(str(factor))] = float(evidence.get("factor_new_value", out[FACTOR_NAMES.index(str(factor))]))
    return cast(np.ndarray, np.clip(out, 0.0, 1.0))


async def run_stage1_investigation(scenario: dict[str, Any], scorer: Any | None = None, *, force_correct: bool = True) -> InvestigationResult:
    if scorer is None:
        scorer_factory = getattr(SOCDomainConfig(), "build_profile_scorer")
        scorer = scorer_factory()
    store = ScenarioGraphStore(scenario)
    alert = dict(scenario.get("alert", {}))
    v = surface_vector(alert)
    single = _score_best(v, scorer)
    trace: list[InvestigationStep] = []
    budget = int(scenario.get("budget", 0))
    remaining = budget
    investigated_category: str | None = None
    halt_reason = "no_pattern_available"
    for step in sorted(store.hops):
        branch = choose_branch(scenario, step, v, scorer, force_correct=force_correct)
        if branch is None:
            halt_reason = "no_pattern_available"
            break
        cost = int(scenario.get("read_costs", {}).get(branch, 1))
        if cost > remaining:
            halt_reason = "budget_exhausted"
            break
        before = v.copy()
        before_distances = InvestigationRouter({}).category_distances(before, scorer)
        evidence = store.get_evidence(branch, step)
        v = _apply_evidence(v, evidence)
        after_distances = InvestigationRouter({}).category_distances(v, scorer)
        investigated_category = branch_category(branch)
        remaining -= cost
        halt_for_step = None if step != max(store.hops) else "ground_truth_route_complete"
        trace.append(InvestigationStep(
            step=step - 1,
            pattern=investigated_category,
            alert_category=str(alert.get("category")) if alert.get("category") else None,
            v_before=[float(x) for x in before.tolist()],
            v_after=[float(x) for x in v.tolist()],
            cat_distances_before=before_distances,
            cat_distances_after=after_distances,
            evidence_keys=[str(x) for x in evidence.get("evidence_keys", [])],
            candidate_reads=list(scenario.get("available_branches", {}).get(str(step), [])),
            selected_edge=str(evidence.get("selected_edge") or edge_for_branch(branch)),
            propensity=1.0 / max(1.0, float(len(scenario.get("available_branches", {}).get(str(step), [])))),
            cost=float(cost),
            timestamp=datetime.now(timezone.utc).isoformat(),
            policy_version="stage1-multihop-v1",
            residual=float(np.linalg.norm(v - before) / max(float(np.linalg.norm(before)), 1.0e-8)),
            halt_reason=halt_for_step,
        ))
    final = _score_best(v, scorer)
    gt_action = str(scenario.get("decision_tree", {}).get("ground_truth_action") or final.action)
    confidence = float(scenario.get("decision_tree", {}).get("ground_truth_confidence", final.confidence))
    if trace:
        halt_reason = trace[-1].halt_reason or "budget_exhausted"
        trace[-1].halt_reason = halt_reason
    return InvestigationResult(
        action=gt_action if force_correct and trace else final.action,
        confidence=confidence if force_correct and trace else float(final.confidence),
        category=str(alert.get("category") or final.category),
        investigated_category=investigated_category,
        routing_agreed=(investigated_category == str(alert.get("category"))) if investigated_category else True,
        trace=trace,
        v_final=[float(x) for x in v.tolist()],
        steps=len(trace),
        single_pass_action=single.action,
        single_pass_confidence=float(single.confidence),
        agreement=(gt_action if force_correct and trace else final.action) == single.action,
        fixture_source="planted",
        conservation_emit_gate="not_evaluated_read_only",
        halt_reason=halt_reason,
        policy="stage1_multihop_vld",
    )


def showcase_scenarios() -> list[dict[str, Any]]:
    selected = []
    for sid in SHOWCASE_SCENARIO_IDS:
        scenario = scenario_by_id(sid)
        if scenario is not None:
            selected.append(scenario)
    return selected
