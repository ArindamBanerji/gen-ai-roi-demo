from typing import Dict

from app.domains.soc.config import SOC_FACTORS


def generate_transparency_page() -> Dict:
    """
    L-11: Three-level transparency page.
    Level 1 (Analyst): zero technical knowledge required.
    Level 2 (CISO): convergence, IKS, conservation law explained.
    Level 3 (Auditor): equations, experiment catalog, formal definitions.
    Limitations: always visible, never hidden.
    """
    return {
        'level_1_analyst': {
            'title': 'How Recommendations Work',
            'sections': [
                {
                    'heading': 'SOC Factors',
                    'content': (
                        'Every recommendation is based on SOC factors computed '
                        'from your organization\'s security graph: '
                        + ', '.join(f.replace('_', ' ') for f in SOC_FACTORS) + '.'
                    )
                },
                {
                    'heading': 'Confidence Score',
                    'content': (
                        'Each recommendation shows a confidence score (0-100%). '
                        'Higher confidence means the system has seen many similar '
                        'cases and the factors clearly point to one action. '
                        'Below the category threshold, the alert is sent to you for review.'
                    )
                },
                {
                    'heading': 'Learning From Your Judgment',
                    'content': (
                        'When you confirm or correct a recommendation, the system '
                        'adjusts its internal profiles. Over time, it learns which '
                        'factor patterns match which actions for YOUR organization. '
                        'The half-life of this learning is approximately 14 verified '
                        'decisions per category-action pair.'
                    )
                },
                {
                    'heading': 'Similar Past Cases',
                    'content': (
                        'For each recommendation, the system shows similar past '
                        'decisions and their outcomes. This helps you calibrate '
                        'whether the current recommendation aligns with precedent.'
                    )
                }
            ]
        },
        'level_2_ciso': {
            'title': 'How the System Gets Smarter',
            'sections': [
                {
                    'heading': 'Level 1: Decision Intelligence',
                    'content': (
                        'Centroids (learned profiles) calibrate with a half-life '
                        'of ~14 verified decisions per category-action pair. '
                        'At 200 alerts/day with 30% verification, all categories '
                        'calibrate within 2-3 weeks.'
                    )
                },
                {
                    'heading': 'Level 2: Operational Adaptation',
                    'content': (
                        'Escalation framing adapts through a four-condition safety gate. '
                        'No change is promoted without statistical evidence of improvement. '
                        'Production design: 2 variants evaluated sequentially. '
                        'Gate detects manipulation of 20+ percentage points within 40 days.'
                    )
                },
                {
                    'heading': 'Conservation Law',
                    'content': (
                        'A mathematical constraint (alpha * q * V >= theta_min) ensures '
                        'the two levels compound rather than conflict. If the learning '
                        'signal thins — due to auto-approve expansion, staffing changes, '
                        'or any other cause — the system alerts before accuracy degrades. '
                        'Check the Learning Health panel for current status.'
                    )
                },
                {
                    'heading': 'Institutional Knowledge Score (IKS)',
                    'content': (
                        'IKS measures how much firm-specific judgment the system has '
                        'accumulated. Components: graph richness, decision maturity, '
                        'trust coverage, factor quality. Track IKS over time to see '
                        'compounding institutional knowledge.'
                    )
                },
                {
                    'heading': 'Graph Enrichment Acceleration',
                    'content': (
                        'Connecting additional data sources accelerates convergence. '
                        'Second SIEM: ~15% faster (validated, rho=0.8 cross-source correlation). '
                        'Full enrichment (entity resolution + threat intel): 35-47% faster '
                        'at production precision thresholds.'
                    )
                }
            ]
        },
        'level_3_auditor': {
            'title': 'Technical Specification',
            'sections': [
                {
                    'heading': 'Scoring Mechanism',
                    'content': (
                        'L2-distance ProfileScorer with temperature-scaled softmax. '
                        'Tensor shape: (n_categories, 4 actions, n_factors) = 144 parameters at today\'s SOC size. '
                        'Actions: escalate, investigate, suppress, monitor. '
                        'refer_to_analyst is a confidence-gate decision, not a scored action. '
                        'Temperature tau=0.1 (ECE=0.036, V3B validated).'
                    )
                },
                {
                    'heading': 'Learning Rule',
                    'content': (
                        'Exponential moving average (Eq. 4b-final). '
                        'eta_pos=0.05, eta_neg=0.05. Clip to [0,1]. '
                        'N_half = ln(2)/ln(1/(1-eta)) = 13.51 decisions. '
                        'Steady-state MSE = eta/(2-eta) * tr(Sigma_f) = 0.0087. '
                        'tr(Sigma_f) = 0.34 (measured from FX-1-PROXY-REAL, +44% vs design estimate).'
                    )
                },
                {
                    'heading': 'Conservation Law',
                    'content': (
                        'alpha(t) * q(t) * V(t) >= theta_min. '
                        'SOC theta_min = 0.434 (eta * N_half^2 / T_max = 0.05 * 13.51^2 / 21). '
                        'Breach window: relative threshold (baseline - 2sigma = AMBER, '
                        'baseline - 3sigma = RED). Absolute floor at theta_min as safety net. '
                        'Three-judge validated (Borkar 2008, Wu et al. 2016, Kazerouni et al. 2017).'
                    )
                },
                {
                    'heading': 'Adversarial Testing',
                    'content': (
                        '45+ experiments. Key results: '
                        'L2 poisoning: four-condition gate holds promotion to <=10%. '
                        'Subtle poisoning (10pp): structurally blocked (0% promotion). '
                        'Re-convergence compounding: 1.42x acceleration (p<0.0001). '
                        'Bridge B: 35-47% convergence acceleration at production precision.'
                    )
                },
                {
                    'heading': 'Experiment Catalog',
                    'content': (
                        'Full catalog available at /api/soc/compliance. '
                        'Categories: operator safety (OP series), synthesis validation (S series), '
                        'production calibration (PROD series), bridge experiments (B series), '
                        'factor validation (FX series), discriminant analysis (DISC series).'
                    )
                }
            ]
        },
        'limitations': {
            'title': 'Known Limitations (Always Visible)',
            'items': [
                '90.6% frozen scorer accuracy at A=4 (Day 1, before learning).',
                'All accuracy numbers validated on synthetic factor distributions, '
                'not real FactorComputer output. Real validation requires first deployment.',
                'Temporal compounding exponent (gamma) demonstrated via re-convergence '
                'simulation (1.42x), not yet measured on production data.',
                'Level 2 promotion gate detects >=20pp manipulation. '
                'Subtle manipulation (<=10pp) is structurally blocked but not detected.',
                'tau=0.1 calibrated on synthetic distributions. '
                'Recalibration on real alerts required before shadow-to-live transition (TD-034).',
                'Conservation law absolute floor (theta_min=0.434) is 33x below healthy '
                'signal at typical SOC volumes. Practical monitoring uses relative thresholds.'
            ]
        }
    }
