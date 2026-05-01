import csv
import io
from dataclasses import asdict

from fastapi import APIRouter
from fastapi.responses import Response

from app.services.evidence_room import EvidenceRoomService, dumps_json_safe
from app.services.governance_report import generate_governance_report


router = APIRouter(tags=["Governance Evidence"])


@router.get("/governance/report")
async def get_governance_report():
    return asdict(await generate_governance_report())


@router.get("/governance/report/csv")
async def get_governance_report_csv():
    report = await generate_governance_report()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["section", "article", "evidence_key", "evidence_value", "status"])

    for section in report.sections:
        for key, value in section.evidence.items():
            writer.writerow([section.title, section.article, key, value, section.status])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="governance_report.csv"'},
    )


@router.get("/governance/summary")
async def get_governance_summary():
    report = await generate_governance_report()
    return {
        "title": report.title,
        "generated_at": report.generated_at,
        "overall_assessment": report.overall_assessment,
        "legal_disclaimer": report.legal_disclaimer,
        "sections": [
            {
                "article": section.article,
                "title": section.title,
                "status": section.status,
                "evidence_count": section.evidence_count,
                "legal_disclaimer": section.legal_disclaimer,
            }
            for section in report.sections
        ],
    }


@router.get("/soc/evidence-room")
async def get_evidence_room():
    return await EvidenceRoomService().get_evidence_summary()


@router.get("/soc/evidence-room/export")
async def get_evidence_room_export():
    payload = await EvidenceRoomService().export_evidence_pack()
    return Response(
        content=dumps_json_safe(payload),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="evidence_pack.json"'},
    )
