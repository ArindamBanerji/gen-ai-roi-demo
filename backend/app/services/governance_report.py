from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, cast
from uuid import uuid4

from app.db.graph_client import graph_client


REPORT_TITLE = "Evidence supporting human oversight"
LEGAL_DISCLAIMER = (
    "Evidence supporting human oversight only. This report is not a compliance "
    "certification or legal determination."
)
DRIFT_01_NOTE = (
    "DRIFT-01 decision note: conservation RED or auto-pause blocks centroid "
    "learning; auto_pause_active overrides transient GREEN and the control fails "
    "closed if the health evaluation errors."
)
N3_RISK_TITLE = "N3 Endogenous Feedback Loop (Residual Risk: MEDIUM)"
N3_RISK_DESCRIPTION = (
    "The system's calibration state may influence which alerts are selected for "
    "analyst verification (high-confidence decisions are less likely to be "
    "manually reviewed). If verification selection is systematically biased, "
    "centroid learning may learn from a biased sample. Shadow mode "
    "(30-day pre-deployment baseline) measures verification selection bias "
    "before live mode activates. Full characterisation requires live "
    "production data."
)
N3_MITIGATION_TEXT = (
    "Mitigation: Shadow mode deployment required before go-live (enforced by "
    "P28 pipeline). Conservation law monitoring (alpha*q*V >= theta_min) "
    "provides ongoing early warning."
)
SYSTEM_VERSION = "5.0.0"


@dataclass
class GovernanceSection:
    article: str
    title: str
    status: str
    summary: str
    legal_disclaimer: str
    evidence: dict[str, Any] = field(default_factory=dict)
    evidence_count: int = 0


@dataclass
class GovernanceReport:
    title: str
    report_id: str
    generated_at: str
    system_version: str
    decision_count: int
    legal_disclaimer: str
    overall_assessment: str
    evidence_item_count: int
    known_risks: list[dict[str, str]] = field(default_factory=list)
    sections: list[GovernanceSection] = field(default_factory=list)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _flatten_evidence_count(obj: Any) -> int:
    if isinstance(obj, dict):
        return sum(_flatten_evidence_count(v) for v in obj.values())
    if isinstance(obj, list):
        return len(obj)
    return 1


def _clean_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    cleaned = value.replace("EU AI Act compliant", "evidence supporting human oversight")
    cleaned = cleaned.replace("EU AI Act Compliance Evidence", REPORT_TITLE)
    cleaned = cleaned.replace("regulatory review (EU AI Act Art. 13 compliant).", "human review.")
    return cleaned


def _clean_nested(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _clean_nested(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean_nested(v) for v in value]
    return _clean_text(value)


def _section(article: str, title: str, status: str, summary: str, evidence: dict[str, Any]) -> GovernanceSection:
    cleaned = _clean_nested(evidence)
    return GovernanceSection(
        article=article,
        title=title,
        status=status,
        summary=_clean_text(summary),
        legal_disclaimer=LEGAL_DISCLAIMER,
        evidence=cleaned,
        evidence_count=_flatten_evidence_count(cleaned),
    )


async def _collect_learning_health() -> dict[str, Any]:
    from app.services.learning_health import LearningHealthMonitor

    return await LearningHealthMonitor.evaluate(graph_client)


async def _collect_audit_evidence() -> tuple[dict[str, Any], dict[str, Any]]:
    from app.framework.audit import get_decision_rows, reconstruct_from_memory, verify_chain

    await reconstruct_from_memory()
    decisions = get_decision_rows()
    verification = verify_chain()
    return {
        "total": len(decisions),
        "sample": decisions[:5],
    }, verification


async def _collect_centroid_export() -> dict[str, Any]:
    from app.services.gae_state import build_centroid_export, get_profile_scorer

    scorer = get_profile_scorer()
    if scorer is None:
        return {"status": "cold_start", "message": "No centroid data yet"}
    return await build_centroid_export(scorer, graph_client)


async def _collect_tab2_evidence() -> dict[str, Any]:
    from app.routers.soc import _tab2_content

    return cast(dict[str, Any], await _tab2_content())


async def _collect_executive_narrative() -> dict[str, Any]:
    from app.services.executive_narrative import build_executive_narrative_async

    return cast(dict[str, Any], await build_executive_narrative_async(graph_client))


async def _collect_auto_approve_stats() -> dict[str, Any]:
    from app.routers.framework_router import auto_approve_stats

    return cast(dict[str, Any], await auto_approve_stats())


async def _collect_epistemic_state() -> dict[str, Any]:
    from app.state.graph_snapshot import get_snapshot

    try:
        snap = get_snapshot()
    except RuntimeError:
        return {"categories": {}, "total_verified": 0}
    return {
        "categories": snap.get_epistemic_state(),
        "total_verified": snap.verified_decisions,
    }


async def _collect_analyst_benchmarking() -> dict[str, Any]:
    from app.routers.soc import get_analyst_benchmarking

    return cast(dict[str, Any], await get_analyst_benchmarking())


async def generate_governance_report() -> GovernanceReport:
    learning_health = await _collect_learning_health()
    audit_decisions, audit_verify = await _collect_audit_evidence()
    centroid_export = await _collect_centroid_export()
    tab2 = await _collect_tab2_evidence()
    executive_narrative = await _collect_executive_narrative()
    auto_approve = await _collect_auto_approve_stats()
    epistemic_state = await _collect_epistemic_state()
    analyst_benchmarking = await _collect_analyst_benchmarking()

    decision_count = int(cast(
        Any,
        epistemic_state.get("total_verified")
        or audit_decisions.get("total")
        or auto_approve.get("total_decisions", 0),
    ))
    learning_status = learning_health.get("status", "UNKNOWN")
    pre_activation = bool(learning_health.get("pre_activation", False))
    art9_summary = "Controls that monitor learning quality, trigger safeguards, and disclose known residual risks."
    art15_summary = "Model robustness evidence includes calibration, convergence, drift visibility, and tensor export metadata."
    if pre_activation:
        art9_summary = (
            "Pre-activation -- conservation law monitoring is configured but learning is not yet enabled. "
            "Controls are ready to monitor learning quality, trigger safeguards, and disclose residual risks once activated."
        )
        art15_summary = (
            "Pre-activation -- model robustness monitoring is configured. Calibration, convergence, drift visibility, "
            "and tensor export will activate with learning. Current evidence reflects system configuration."
        )

    section_1 = _section(
        article="Art 9",
        title="Risk Management",
        status=learning_status,
        summary=art9_summary,
        evidence={
            "learning_health": learning_health,
            "iks_score": tab2.get("iks_score"),
            "iks_interpretation": tab2.get("iks_interpretation"),
            "drift_alert_summary": tab2.get("drift_alert_summary"),
            "trust_coverage_summary": tab2.get("trust_coverage_summary"),
            "calibration_note": tab2.get("calibration_note"),
            "epistemic_state": epistemic_state,
            "drift_01_note": DRIFT_01_NOTE,
        },
    )
    section_2 = _section(
        article="Art 12",
        title="Record-Keeping",
        status="READY" if audit_verify.get("verified", False) else "ATTENTION",
        summary="Tamper-evident audit records and exportable model state support retrospective review.",
        evidence={
            "chain_integrity": audit_verify,
            "decision_audit": audit_decisions,
            "centroid_export": centroid_export,
        },
    )
    section_3 = _section(
        article="Art 13",
        title="Transparency and Information",
        status="READY",
        summary="Human-readable narrative, glossary, and model-state summaries explain what the system observed and learned.",
        evidence={
            "headline": executive_narrative.get("headline", ""),
            "what_changed": executive_narrative.get("what_changed", {}),
            "what_discovered": executive_narrative.get("what_discovered", {}),
            "what_knows": executive_narrative.get("what_knows", {}),
            "decision_count_glossary": tab2.get("decision_count_glossary", {}),
        },
    )
    section_4 = _section(
        article="Art 14",
        title="Human Oversight",
        status="READY" if not learning_health.get("auto_pause_active") else "PAUSED",
        summary="Evidence supporting human oversight, including pause controls, analyst review signals, and override-related monitoring.",
        evidence={
            "auto_pause_active": learning_health.get("auto_pause_active"),
            "red_days": learning_health.get("red_days"),
            "auto_approve_stats": auto_approve,
            "analyst_benchmarking": analyst_benchmarking,
            "chain_verified": audit_verify.get("verified"),
        },
    )
    section_5 = _section(
        article="Art 15",
        title="Accuracy, Robustness, and Cybersecurity",
        status=learning_status,
        summary=art15_summary,
        evidence={
            "iks_score": tab2.get("iks_score"),
            "category_accuracy_summary": tab2.get("category_accuracy_summary", {}),
            "centroid_tensor_shape": centroid_export.get("tensor_shape"),
            "centroid_sha256": centroid_export.get("sha256"),
            "learning_health": learning_health,
            "epistemic_state": epistemic_state,
        },
    )

    sections = [section_1, section_2, section_3, section_4, section_5]
    evidence_item_count = sum(section.evidence_count for section in sections)

    return GovernanceReport(
        title=REPORT_TITLE,
        report_id=f"governance-{uuid4()}",
        generated_at=_now_iso(),
        system_version=SYSTEM_VERSION,
        decision_count=decision_count,
        legal_disclaimer=LEGAL_DISCLAIMER,
        overall_assessment="Evidence supporting human oversight is available across five sections.",
        evidence_item_count=evidence_item_count,
        known_risks=[
            {
                "title": N3_RISK_TITLE,
                "description": N3_RISK_DESCRIPTION,
                "mitigation": N3_MITIGATION_TEXT,
                "legal_disclaimer": LEGAL_DISCLAIMER,
            }
        ],
        sections=sections,
    )


async def generate_governance_report_dict() -> dict[str, Any]:
    return asdict(await generate_governance_report())
