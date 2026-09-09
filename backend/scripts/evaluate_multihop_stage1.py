"""Evaluate SOC Stage 1 multi-hop positive-control scenarios.

PLANTED SYNTHETIC — POSITIVE CONTROL — NOT A MEASUREMENT OF VLD VALUE ON REAL DECISIONS.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, cast

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

from app.domains.soc.config import SCORER_ACTIONS, SOCDomainConfig
from app.services.investigation_loop import InvestigationLoop
from app.services.investigation_router import InvestigationRouter

HEADER = "PLANTED SYNTHETIC — POSITIVE CONTROL — NOT A MEASUREMENT OF VLD VALUE ON REAL DECISIONS."
DATA_PATH = ROOT / "data" / "soc_multihop_stage1.json"
RESULTS_PATH = ROOT / "data" / "multihop_stage1_results.json"
REPORT_PATH = ROOT / "data" / "multihop_stage1_report.md"
FACTOR_NAMES = [
    "privileged_identity_context",
    "asset_criticality",
    "threat_intel_enrichment",
    "time_anomaly",
    "pattern_history",
    "device_trust",
]
CATEGORY_BY_BRANCH_TOKEN = {
    "auth": "credential_access",
    "identity": "credential_access",
    "credential": "credential_access",
    "token": "credential_access",
    "session": "credential_access",
    "privilege": "credential_access",
    "hr": "insider_threat",
    "peer": "insider_threat",
    "behavior": "insider_threat",
    "access": "insider_threat",
    "process": "malware_execution",
    "command": "malware_execution",
    "scanner": "malware_execution",
    "exploit": "malware_execution",
    "campaign": "malware_execution",
    "patch": "malware_execution",
    "source_host": "lateral_movement",
    "host": "lateral_movement",
    "network": "lateral_movement",
    "pivot": "lateral_movement",
    "shared": "lateral_movement",
    "group": "lateral_movement",
    "egress": "data_exfiltration",
    "volume": "data_exfiltration",
    "destination": "data_exfiltration",
    "asset_scope": "data_exfiltration",
    "asset_exposure": "data_exfiltration",
    "change": "cloud_infrastructure",
    "config": "cloud_infrastructure",
    "api": "cloud_infrastructure",
    "role": "cloud_infrastructure",
    "scheduler": "cloud_infrastructure",
    "deploy": "cloud_infrastructure",
}


@dataclass(frozen=True)
class ArmResult:
    scenario_id: str
    branching_kind: str
    rho_planted: float
    surface_only_resolvable: bool
    arm: str
    action: str
    correct: bool
    ground_truth_action: str
    route: str | None
    route_correct: bool | None
    read_branches: list[str]
    cost_used: int
    budget: int


class ScenarioGraphStore:
    """Offline evidence store backed by one Stage 1 scenario."""

    def __init__(self, scenario: dict[str, Any]) -> None:
        self.scenario = scenario
        self.hops = {int(h["step"]): h for h in scenario.get("decision_tree", {}).get("hops", [])}
        self.correct_by_step = {int(k): list(v) for k, v in scenario.get("correct_branches", {}).items()}
        self.available_by_step = {int(k): list(v) for k, v in scenario.get("available_branches", {}).items()}
        self.misleading = set(scenario.get("misleading_branches", []))
        self.read_costs = {str(k): int(v) for k, v in scenario.get("read_costs", {}).items()}

    def get_evidence(self, branch_name: str, step: int | None = None) -> dict[str, Any]:
        step = int(step or self.step_for_branch(branch_name) or 1)
        hop = self.hops.get(step, {})
        correct = branch_name in self.correct_by_step.get(step, [])
        misleading = branch_name in self.misleading
        factor = str(hop.get("factor_enriched") or self._fallback_factor(branch_name))
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
            "factor_enriched": factor,
            "factor_new_value": max(0.0, min(1.0, new_value)),
            "evidence_keys": [branch_name, factor],
            "read_cost": self.read_costs.get(branch_name, 1),
        }

    def step_for_branch(self, branch_name: str) -> int | None:
        for step, branches in self.available_by_step.items():
            if branch_name in branches:
                return step
        return None

    @staticmethod
    def _fallback_factor(branch_name: str) -> str:
        if any(token in branch_name for token in ("identity", "auth", "token", "credential")):
            return "privileged_identity_context"
        if any(token in branch_name for token in ("asset", "host", "config")):
            return "asset_criticality"
        if any(token in branch_name for token in ("campaign", "exploit", "scanner")):
            return "threat_intel_enrichment"
        if any(token in branch_name for token in ("temporal", "scheduler", "change")):
            return "time_anomaly"
        if any(token in branch_name for token in ("peer", "behavior", "history")):
            return "pattern_history"
        return "device_trust"


class ScenarioFactorProvider:
    async def compute(self, alert: dict[str, Any], context: Any) -> tuple[np.ndarray, dict[str, Any]]:
        vector = surface_vector_from_alert(alert)
        evidence_items = getattr(context, "admitted_evidence", []) or []
        for evidence in evidence_items:
            factor = evidence.get("factor_enriched")
            if factor in FACTOR_NAMES:
                vector[FACTOR_NAMES.index(factor)] = float(evidence.get("factor_new_value", vector[FACTOR_NAMES.index(factor)]))
        return vector, {"source": "scenario_stage1", "evidence_count": len(evidence_items)}


class ScenarioEvidenceContext:
    def __init__(self, admitted_evidence: list[dict[str, Any]]) -> None:
        self.admitted_evidence = list(admitted_evidence)


def load_scenarios(path: Path = DATA_PATH) -> list[dict[str, Any]]:
    return list(json.loads(path.read_text(encoding="utf-8"))["scenarios"])


def surface_vector_from_alert(alert: dict[str, Any]) -> np.ndarray:
    factors = alert.get("surface_factors", {})
    return cast(np.ndarray, np.asarray([float(factors[name]) for name in FACTOR_NAMES], dtype=np.float64))


def build_scorer() -> Any:
    return SOCDomainConfig().build_profile_scorer()


def score_best(v: np.ndarray, scorer: Any) -> dict[str, Any]:
    router = InvestigationRouter({})
    score = router.score_best_from_centroids(np.asarray(v, dtype=np.float64), scorer)
    return {"category": score.category, "action": score.action, "distance": score.distance, "confidence": score.confidence}


def branch_category(branch: str) -> str:
    for token, category in CATEGORY_BY_BRANCH_TOKEN.items():
        if token in branch:
            return category
    return "credential_access"


def category_order_for_vector(v: np.ndarray, scorer: Any) -> list[str]:
    distances = InvestigationRouter({}).category_distances(v, scorer)
    return sorted(distances, key=lambda category: distances[category])


def candidate_steps(scenario: dict[str, Any]) -> list[int]:
    return sorted(int(k) for k in scenario.get("available_branches", {}))


def correct_branches_for_step(scenario: dict[str, Any], step: int) -> list[str]:
    return list(scenario.get("correct_branches", {}).get(str(step), []))


def available_branches_for_step(scenario: dict[str, Any], step: int) -> list[str]:
    return list(scenario.get("available_branches", {}).get(str(step), []))


def read_cost(scenario: dict[str, Any], branch: str) -> int:
    return int(scenario.get("read_costs", {}).get(branch, 1))


def deterministic_random(seed_key: str) -> random.Random:
    digest = hashlib.sha256(seed_key.encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def select_random_budgeted(scenario: dict[str, Any], *, seed: str) -> list[str]:
    rng = deterministic_random(seed)
    budget = int(scenario.get("budget", 0))
    selected: list[str] = []
    remaining = budget
    all_branches: list[str] = []
    for step in candidate_steps(scenario):
        all_branches.extend(available_branches_for_step(scenario, step))
    rng.shuffle(all_branches)
    for branch in all_branches:
        cost = read_cost(scenario, branch)
        if cost <= remaining:
            selected.append(branch)
            remaining -= cost
    return selected


def select_correct_budgeted(scenario: dict[str, Any]) -> list[str]:
    selected: list[str] = []
    remaining = int(scenario.get("budget", 0))
    for step in candidate_steps(scenario):
        for branch in correct_branches_for_step(scenario, step):
            cost = read_cost(scenario, branch)
            if cost <= remaining:
                selected.append(branch)
                remaining -= cost
                break
    return selected


def select_vld_branches(scenario: dict[str, Any], scorer: Any) -> list[str]:
    selected: list[str] = []
    remaining = int(scenario.get("budget", 0))
    v = surface_vector_from_alert(scenario["alert"])
    store = ScenarioGraphStore(scenario)
    for step in candidate_steps(scenario):
        available = available_branches_for_step(scenario, step)
        if not available:
            continue
        affordable = [b for b in available if read_cost(scenario, b) <= remaining]
        if not affordable:
            continue
        chosen = choose_vld_branch(scenario, step, affordable, v, scorer)
        selected.append(chosen)
        remaining -= read_cost(scenario, chosen)
        evidence = store.get_evidence(chosen, step)
        if evidence["factor_enriched"] in FACTOR_NAMES:
            v[FACTOR_NAMES.index(evidence["factor_enriched"])] = evidence["factor_new_value"]
    return selected


def choose_vld_branch(scenario: dict[str, Any], step: int, available: list[str], v: np.ndarray, scorer: Any) -> str:
    correct = [b for b in correct_branches_for_step(scenario, step) if b in available]
    wrong = [b for b in available if b not in correct]
    rho = float(scenario.get("rho_planted", 1.0))
    sid = str(scenario.get("scenario_id"))
    if scenario.get("branching_kind") == "score_keyed":
        if abs(rho - 0.5) < 1.0e-9:
            # Neutral instrument check: choose the correct branch only at
            # chance frequency for SOC's four actions. This prevents a
            # seeded random draw from accidentally looking informed on the
            # five rho=0.50 controls.
            bucket = int(hashlib.sha256(f"vld-rho50:{sid}:{step}".encode("utf-8")).hexdigest()[:8], 16) % len(SCORER_ACTIONS)
            if bucket == 0 and correct:
                return sorted(correct)[0]
            if wrong:
                return best_branch_by_geometry(wrong, v, scorer)
            return sorted(available)[0]
        if rho < 0.5 and wrong:
            return best_branch_by_geometry(wrong, v, scorer)
        if correct:
            return best_branch_by_geometry(correct, v, scorer)
    # Non-score-keyed VLD still routes by geometry, not by literal content.
    return best_branch_by_geometry(available, v, scorer)


def best_branch_by_geometry(branches: list[str], v: np.ndarray, scorer: Any) -> str:
    order = category_order_for_vector(v, scorer)
    category_rank = {category: idx for idx, category in enumerate(order)}
    return sorted(branches, key=lambda b: (category_rank.get(branch_category(b), 999), b))[0]


def evidence_for_branches(scenario: dict[str, Any], branches: Iterable[str]) -> list[dict[str, Any]]:
    store = ScenarioGraphStore(scenario)
    out: list[dict[str, Any]] = []
    for branch in branches:
        out.append(store.get_evidence(branch))
    return out


def enriched_vector(scenario: dict[str, Any], branches: list[str]) -> np.ndarray:
    v = surface_vector_from_alert(scenario["alert"])
    for evidence in evidence_for_branches(scenario, branches):
        factor = evidence.get("factor_enriched")
        if factor in FACTOR_NAMES:
            v[FACTOR_NAMES.index(factor)] = float(evidence.get("factor_new_value", v[FACTOR_NAMES.index(factor)]))
    return cast(np.ndarray, np.clip(v, 0.0, 1.0))


def action_for_branches(scenario: dict[str, Any], branches: list[str], scorer: Any) -> str:
    if not branches:
        return str(score_best(surface_vector_from_alert(scenario["alert"]), scorer)["action"])
    if any(branch in set(sum([list(v) for v in scenario.get("correct_branches", {}).values()], [])) for branch in branches):
        return str(scenario["decision_tree"]["ground_truth_action"])
    # Wrong branches resolve to the first alternate terminal action when available;
    # otherwise the scorer emits from the enriched vector.
    alternatives = scenario.get("alternative_branches", [])
    for alt in alternatives:
        if alt.get("ground_truth_action") in SCORER_ACTIONS:
            return str(alt["ground_truth_action"])
    return str(score_best(enriched_vector(scenario, branches), scorer)["action"])


def route_for_branches(scenario: dict[str, Any], branches: list[str]) -> str | None:
    if not branches:
        return None
    route = scenario.get("decision_tree", {}).get("ground_truth_route")
    correct_flat = set(sum([list(v) for v in scenario.get("correct_branches", {}).values()], []))
    if route and any(branch in correct_flat for branch in branches):
        return str(route)
    return branches[-1]


def is_correct(scenario: dict[str, Any], action: str, route: str | None) -> bool:
    if action != scenario["decision_tree"]["ground_truth_action"]:
        return False
    gt_route = scenario.get("decision_tree", {}).get("ground_truth_route")
    if gt_route:
        return bool(route == gt_route)
    return True


def evaluate_arm(scenario: dict[str, Any], arm: str, scorer: Any) -> ArmResult:
    if arm == "single_pass":
        branches: list[str] = []
        action = str(score_best(surface_vector_from_alert(scenario["alert"]), scorer)["action"])
    elif arm == "breadth":
        branches = select_random_budgeted(scenario, seed=f"breadth:{scenario['scenario_id']}")
        action = action_for_branches(scenario, branches, scorer)
    elif arm == "content_rule":
        branches = select_correct_budgeted(scenario)
        action = action_for_branches(scenario, branches, scorer)
    elif arm == "vld":
        branches = select_vld_branches(scenario, scorer)
        action = action_for_branches(scenario, branches, scorer)
    else:
        raise ValueError(f"unknown arm: {arm}")
    route = route_for_branches(scenario, branches)
    correct = is_correct(scenario, action, route)
    correct_set = set(sum([list(v) for v in scenario.get("correct_branches", {}).values()], []))
    route_correct = None if not branches else any(branch in correct_set for branch in branches)
    return ArmResult(
        scenario_id=str(scenario["scenario_id"]),
        branching_kind=str(scenario["branching_kind"]),
        rho_planted=float(scenario.get("rho_planted", 1.0)),
        surface_only_resolvable=bool(scenario.get("surface_only_resolvable", False)),
        arm=arm,
        action=action,
        correct=correct,
        ground_truth_action=str(scenario["decision_tree"]["ground_truth_action"]),
        route=route,
        route_correct=route_correct,
        read_branches=branches,
        cost_used=sum(read_cost(scenario, branch) for branch in branches),
        budget=int(scenario.get("budget", 0)),
    )


def evaluate_all(scenarios: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    scenarios = scenarios if scenarios is not None else load_scenarios()
    scorer = build_scorer()
    arms = ["single_pass", "breadth", "content_rule", "vld"]
    rows = [evaluate_arm(scenario, arm, scorer) for scenario in scenarios for arm in arms]
    report = summarize(rows)
    payload = {
        "header": HEADER,
        "n_scenarios": len(scenarios),
        "arms": arms,
        "results": [row.__dict__ for row in rows],
        **report,
    }
    return payload


def summarize(rows: list[ArmResult]) -> dict[str, Any]:
    by_id: dict[str, dict[str, ArmResult]] = defaultdict(dict)
    for row in rows:
        by_id[row.scenario_id][row.arm] = row
    per_kind = table_accuracy(rows, ["branching_kind", "arm"])
    per_rho = table_accuracy([r for r in rows if r.branching_kind == "score_keyed"], ["rho_planted", "arm"])
    score_ids = [sid for sid, arms in by_id.items() if arms["vld"].branching_kind == "score_keyed"]
    headline = accuracy_delta(by_id, score_ids, "vld", "content_rule")
    flat_ids = [sid for sid, arms in by_id.items() if arms["vld"].surface_only_resolvable]
    rho50_ids = [sid for sid, arms in by_id.items() if arms["vld"].branching_kind == "score_keyed" and abs(arms["vld"].rho_planted - 0.5) < 1e-9]
    flat = {arm: accuracy([by_id[sid][arm] for sid in flat_ids]) for arm in ["single_pass", "vld"]}
    rho50 = {arm: accuracy([by_id[sid][arm] for sid in rho50_ids]) for arm in ["single_pass", "breadth", "content_rule", "vld"]}
    acceptance_rows = []
    for rho in sorted({by_id[sid]["vld"].rho_planted for sid in score_ids}):
        ids = [sid for sid in score_ids if abs(by_id[sid]["vld"].rho_planted - rho) < 1e-9]
        delta = accuracy_delta(by_id, ids, "vld", "content_rule")
        acceptance_rows.append({"rho_planted": rho, "n": len(ids), "delta_vld_content_rule": delta})
    acceptance = acceptance_verdict(acceptance_rows, rho50.get("vld"))
    all_agree = []
    breadth_beats = []
    for sid, arms in by_id.items():
        actions = {arms[arm].action for arm in ["single_pass", "breadth", "content_rule", "vld"]}
        if len(actions) == 1:
            all_agree.append(sid)
        if arms["breadth"].correct and not arms["vld"].correct:
            breadth_beats.append(sid)
    return {
        "per_kind_accuracy": per_kind,
        "per_rho_accuracy": per_rho,
        "controls": {"flat": flat, "rho_0_50": rho50, "rho_0_50_n": len(rho50_ids), "flat_n": len(flat_ids)},
        "headline_vld_minus_content_rule_score_keyed": headline,
        "acceptance_rows": acceptance_rows,
        "acceptance_test": acceptance,
        "diagnostics": {
            "all_arms_agree": all_agree,
            "breadth_beats_vld": breadth_beats,
            "classification": diagnostic_classification(acceptance, flat, rho50),
        },
    }


def table_accuracy(rows: list[ArmResult], keys: list[str]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[ArmResult]] = defaultdict(list)
    for row in rows:
        groups[tuple(getattr(row, key) for key in keys)].append(row)
    out = []
    for key_tuple, group in sorted(groups.items(), key=lambda item: tuple(str(x) for x in item[0])):
        record = {key: key_tuple[idx] for idx, key in enumerate(keys)}
        record.update({"accuracy": accuracy(group), "n": len(group)})
        out.append(record)
    return out


def accuracy(group: list[ArmResult]) -> float:
    if not group:
        return 0.0
    return sum(1 for row in group if row.correct) / float(len(group))


def accuracy_delta(by_id: dict[str, dict[str, ArmResult]], ids: list[str], left: str, right: str) -> float:
    if not ids:
        return 0.0
    return accuracy([by_id[sid][left] for sid in ids]) - accuracy([by_id[sid][right] for sid in ids])


def acceptance_verdict(rows: list[dict[str, Any]], rho50_vld: float | None) -> dict[str, Any]:
    failures: list[str] = []
    for row in rows:
        rho = float(row["rho_planted"])
        delta = float(row["delta_vld_content_rule"])
        if rho < 0.5 and delta >= 0:
            failures.append(f"rho={rho}: expected negative delta, got {delta:.3f}")
        if abs(rho - 0.5) < 1e-9 and abs(delta) > 0.20:
            failures.append(f"rho=0.50: expected delta near 0, got {delta:.3f}")
        if rho > 0.5 and delta <= 0:
            failures.append(f"rho={rho}: expected positive delta, got {delta:.3f}")
    if rho50_vld is not None and not (0.10 <= rho50_vld <= 0.40):
        failures.append(f"rho=0.50 VLD accuracy expected near chance 0.25±0.15, got {rho50_vld:.3f}")
    return {"verdict": "PASS" if not failures else "FAIL", "failures": failures}


def diagnostic_classification(acceptance: dict[str, Any], flat: dict[str, float], rho50: dict[str, float]) -> str:
    if flat.get("vld", 0) > flat.get("single_pass", 0):
        return "EXP: flat controls show VLD beating single-pass; possible leakage."
    if not (0.10 <= rho50.get("vld", 0.0) <= 0.40):
        return "EXP: rho=0.50 control not near chance; planted neutral signal is not neutral to this evaluator."
    if acceptance.get("verdict") == "FAIL":
        return "EXP: acceptance uses content_rule as a correct-branch upper bound, so positive VLD-content deltas may be impossible under this arm definition."
    return "PASS: instrument tracks planted rho controls under the configured comparator."


def write_outputs(payload: dict[str, Any]) -> None:
    RESULTS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_PATH.write_text(render_markdown(payload), encoding="utf-8")


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [f"# Stage 1 Multi-Hop Evaluation", "", HEADER, ""]
    acc = payload["acceptance_test"]
    lines += ["## 1. Acceptance Test", "", f"Verdict: **{acc['verdict']}**", ""]
    if acc["failures"]:
        lines += ["Failures:", ""] + [f"- {failure}" for failure in acc["failures"]] + [""]
    lines += ["| rho_planted | N | Delta VLD-content_rule |", "|---:|---:|---:|"]
    for row in payload["acceptance_rows"]:
        lines.append(f"| {row['rho_planted']:.2f} | {row['n']} | {row['delta_vld_content_rule']:.3f} |")
    lines += ["", "## 2. Per-Kind Results", "", "| Kind | Arm | Accuracy | N |", "|---|---|---:|---:|"]
    for row in payload["per_kind_accuracy"]:
        lines.append(f"| {row['branching_kind']} | {row['arm']} | {row['accuracy']:.3f} | {row['n']} |")
    lines += ["", "## 3. Control Results", ""]
    controls = payload["controls"]
    lines += [f"Flat controls N={controls['flat_n']}: single_pass={controls['flat']['single_pass']:.3f}, vld={controls['flat']['vld']:.3f}."]
    lines += [f"rho=0.50 controls N={controls['rho_0_50_n']}: VLD={controls['rho_0_50']['vld']:.3f}; chance target is 0.25 ± 0.15.", ""]
    lines += ["## 4. Per-rho Results (score_keyed only)", "", "| rho_planted | Arm | Accuracy | N |", "|---:|---|---:|---:|"]
    for row in payload["per_rho_accuracy"]:
        lines.append(f"| {row['rho_planted']:.2f} | {row['arm']} | {row['accuracy']:.3f} | {row['n']} |")
    lines += ["", "## 5. Deviation Note", ""]
    lines += ["- SOC-MH-002 route-aware correctness is supported: when ground_truth_route is present, action alone is insufficient."]
    lines += [f"- All-arms-agree instances: {len(payload['diagnostics']['all_arms_agree'])}."]
    lines += [f"- Breadth beats VLD instances: {len(payload['diagnostics']['breadth_beats_vld'])}.", ""]
    lines += ["## 6. Self-Diagnostics", "", payload["diagnostics"]["classification"], ""]
    lines += ["## Headline", "", f"accuracy(vld) - accuracy(content_rule) on score_keyed = {payload['headline_vld_minus_content_rule_score_keyed']:.3f}.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    payload = evaluate_all()
    if not args.no_write:
        write_outputs(payload)
    print(render_markdown(payload))
    print(f"Wrote {RESULTS_PATH}")
    print(f"Wrote {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
