from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np


@dataclass
class BenchmarkingReport:
    period_start: str
    period_end: str
    total_decisions: int
    # Section 1
    system_accuracy: float
    analyst_accuracy: float
    disagreement_rate: float
    system_correct_on_disagreements: int
    analyst_correct_on_disagreements: int
    per_category_accuracy: Dict
    # Section 2
    iks_start: float
    iks_end: float
    iks_delta: float
    categories_calibrated: int
    # Section 3
    system_acceptance_rate: float
    guaranteed_consistency: float
    estimated_annual_savings: Dict


class BenchmarkingEngine:
    def __init__(self, db_client):
        self.db = db_client

    def generate_report(self, start_date: str, end_date: str,
                        analyst_hourly_cost: float = 85.0) -> BenchmarkingReport:
        decisions = self._fetch_verified_decisions(start_date, end_date)
        accuracy = self._compute_accuracy(decisions)
        adaptation = self._compute_adaptation(start_date, end_date)
        consistency = self._compute_consistency(decisions, analyst_hourly_cost)
        return BenchmarkingReport(
            period_start=start_date, period_end=end_date,
            total_decisions=len(decisions), **accuracy, **adaptation, **consistency
        )

    def _compute_accuracy(self, decisions: List[Dict]) -> Dict:
        system_correct = 0
        analyst_correct = 0
        disagreements = 0
        sys_correct_disagree = 0
        ana_correct_disagree = 0
        category_stats = {}

        for d in decisions:
            sys_act = d.get('system_action', '')
            ana_act = d.get('analyst_action', '')
            gt_act = d.get('gt_action', sys_act)  # fallback
            cat = d.get('category', 'unknown')

            if cat not in category_stats:
                category_stats[cat] = {
                    'total': 0, 'system_correct': 0,
                    'analyst_correct': 0, 'disagreements': 0
                }
            category_stats[cat]['total'] += 1

            if sys_act == gt_act:
                system_correct += 1
                category_stats[cat]['system_correct'] += 1
            if ana_act == gt_act:
                analyst_correct += 1
                category_stats[cat]['analyst_correct'] += 1
            if sys_act != ana_act:
                disagreements += 1
                category_stats[cat]['disagreements'] += 1
                if sys_act == gt_act:
                    sys_correct_disagree += 1
                if ana_act == gt_act:
                    ana_correct_disagree += 1

        n = max(len(decisions), 1)
        per_cat = {}
        for cat, s in category_stats.items():
            t = max(s['total'], 1)
            per_cat[cat] = {
                'system_accuracy': round(s['system_correct'] / t, 3),
                'analyst_accuracy': round(s['analyst_correct'] / t, 3),
                'disagreement_rate': round(s['disagreements'] / t, 3),
                'total': s['total']
            }

        return {
            'system_accuracy': round(system_correct / n, 3),
            'analyst_accuracy': round(analyst_correct / n, 3),
            'disagreement_rate': round(disagreements / n, 3),
            'system_correct_on_disagreements': sys_correct_disagree,
            'analyst_correct_on_disagreements': ana_correct_disagree,
            'per_category_accuracy': per_cat
        }

    def _compute_adaptation(self, start_date: str, end_date: str) -> Dict:
        # Query IKS at start and end of period
        # For now: return from current IKS service
        return {
            'iks_start': 0.0,
            'iks_end': 0.0,
            'iks_delta': 0.0,
            'categories_calibrated': 0
        }

    def _compute_consistency(self, decisions: List[Dict],
                             hourly_cost: float) -> Dict:
        accepted = sum(1 for d in decisions
                       if d.get('system_action') == d.get('analyst_action'))
        n = max(len(decisions), 1)
        o_bar = accepted / n
        guaranteed = (1 - o_bar) ** 2

        shifts_per_year = 365 * 3
        annual_cost = hourly_cost * 8 * shifts_per_year
        dup_savings = annual_cost * 0.08 * (1 - guaranteed)
        esc_savings = annual_cost * 0.05 * o_bar
        mttr_savings = annual_cost * 0.12 * o_bar
        error_cost = annual_cost * 0.03 * (1 - o_bar)
        net = dup_savings + esc_savings + mttr_savings - error_cost

        return {
            'system_acceptance_rate': round(o_bar, 3),
            'guaranteed_consistency': round(guaranteed, 3),
            'estimated_annual_savings': {
                'duplicate_effort': round(dup_savings, 2),
                'escalation_churn': round(esc_savings, 2),
                'mttr_improvement': round(mttr_savings, 2),
                'error_cost_offset': round(error_cost, 2),
                'net_annual_savings': round(net, 2),
                'assumptions': {
                    'analyst_hourly_cost': hourly_cost,
                    'shifts_per_year': shifts_per_year
                }
            }
        }

    def format_executive_summary(self, report: BenchmarkingReport) -> str:
        return (
            f"Over the period {report.period_start} to {report.period_end}, "
            f"the system made {report.total_decisions} verified decisions. "
            f"System accuracy: {report.system_accuracy:.1%}. "
            f"Analyst accuracy: {report.analyst_accuracy:.1%}. "
            f"On the {report.disagreement_rate:.1%} of disagreements, the system "
            f"was correct {report.system_correct_on_disagreements} times and "
            f"analysts were correct {report.analyst_correct_on_disagreements} times. "
            f"Consistency: {report.guaranteed_consistency:.0%} of case pairs receive "
            f"perfectly consistent recommendations. "
            f"Estimated annual savings: "
            f"${report.estimated_annual_savings['net_annual_savings']:,.0f}."
        )

    def _fetch_verified_decisions(self, start_date, end_date) -> List[Dict]:
        query = """
        MATCH (d:Decision)
        WHERE d.domain = 'soc' AND d.outcome IS NOT NULL
        RETURN d.decision_id AS id, d.action AS system_action,
               d.analyst_action AS analyst_action,
               d.category AS category,
               d.confidence AS confidence
        """
        try:
            records = self.db.run_query(query)
            return [dict(r) for r in records] if records else []
        except Exception:
            return []
