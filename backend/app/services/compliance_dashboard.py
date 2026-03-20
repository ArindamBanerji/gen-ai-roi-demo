from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class ComplianceArticle:
    article_number: int
    title: str
    product_evidence: str
    mechanisms: List[str]
    status: str  # "fully_addressed" | "partially_addressed"


COMPLIANCE_MAP = [
    ComplianceArticle(
        article_number=9,
        title="Risk Management System",
        product_evidence=(
            "Endogenous feedback loop (N3) disclosed as known risk. "
            "Three learning health conditions monitored continuously (L-09): "
            "coverage, drift consistency, conservation law. "
            "Auto-pause after 14 consecutive RED days. "
            "45+ adversarial experiments including deliberate poisoning. "
            "Conservation law prevents automation complacency."
        ),
        mechanisms=["L-09 Learning Health Monitor", "Conservation Law",
                     "45 Adversarial Experiments", "N3 Loop Disclosure"],
        status="fully_addressed"
    ),
    ComplianceArticle(
        article_number=12,
        title="Record-Keeping",
        product_evidence=(
            "Every decision, outcome, centroid update, and intervention logged "
            "to Neo4j graph with timestamps. Intervention audit trail (L-12). "
            "Checkpoint/rollback history preserved. "
            "Exportable as structured data."
        ),
        mechanisms=["Decision Logging", "Intervention Audit Trail (L-12)",
                     "Checkpoint History", "Structured Export"],
        status="fully_addressed"
    ),
    ComplianceArticle(
        article_number=13,
        title="Transparency and Information",
        product_evidence=(
            "Three-level transparency page (L-11): analyst, CISO, auditor. "
            "Factor provenance per decision. NL template explanations. "
            "Readable centroid values (6-dimensional, not opaque). "
            "Limitations disclosed: 90.6% frozen baseline (A=4), "
            "convergence predictions, pending experiments."
        ),
        mechanisms=["L-11 Transparency Page", "Factor Provenance",
                     "NL Templates", "Readable Centroids", "Limitations Disclosure"],
        status="fully_addressed"
    ),
    ComplianceArticle(
        article_number=14,
        title="Human Oversight",
        product_evidence=(
            "Consolidated intervention controls (L-12): freeze learning, "
            "rollback to checkpoint, disable auto-approve, category override, "
            "threshold adjustment. Every intervention logged with who/when/why. "
            "Human review mandatory below confidence threshold. "
            "Three-tier dispatch with adjustable thresholds."
        ),
        mechanisms=["L-12 Intervention Controls", "Three-Tier Dispatch",
                     "Confidence Thresholds", "Intervention Audit Log"],
        status="fully_addressed"
    ),
    ComplianceArticle(
        article_number=15,
        title="Accuracy, Robustness and Cybersecurity",
        product_evidence=(
            "Calibration: ECE=0.036 at tau=0.1 (V3B validated). "
            "Convergence health monitored per category (IKS + L-09). "
            "Conservation law ensures learning signal sufficiency. "
            "Poisoning resilience: four-condition gate holds adversarial "
            "promotion to 10 percent or less. 45+ experiments in validation catalog."
        ),
        mechanisms=["Calibration (ECE=0.036)", "IKS Convergence",
                     "Conservation Law", "Four-Condition Gate",
                     "45+ Validation Experiments"],
        status="fully_addressed"
    ),
]


def generate_compliance_page() -> Dict:
    return {
        'title': 'EU AI Act Compliance Evidence',
        'enforcement_date': '2026-08-02',
        'last_updated': datetime.utcnow().isoformat(),
        'articles': [
            {
                'article': a.article_number,
                'title': a.title,
                'evidence': a.product_evidence,
                'mechanisms': a.mechanisms,
                'status': a.status
            }
            for a in COMPLIANCE_MAP
        ],
        'summary': {
            'fully_addressed': sum(1 for a in COMPLIANCE_MAP if a.status == 'fully_addressed'),
            'total_articles': len(COMPLIANCE_MAP),
            'adversarial_experiments': 45,
            'known_risks_disclosed': 1
        }
    }
