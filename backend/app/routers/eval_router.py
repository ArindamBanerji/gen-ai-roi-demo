"""
FEATURE-01 upload-based evaluation router.
"""

from __future__ import annotations

import csv
import io
from dataclasses import asdict

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.services.eval_service import (
    REQUIRED_COLUMNS,
    TEMPLATE_FORMATS,
    example_template_rows,
    run_evaluation,
    validate_csv_rows,
)


router = APIRouter()

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_ROWS = 50_000


@router.post("/eval/upload")
async def upload_eval_csv(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Expected a CSV upload")

    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"CSV exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit",
        )
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded CSV is empty")

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"CSV decode failed: {exc}") from exc

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV must include a header row")

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in reader.fieldnames]
    if missing_columns:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Missing required columns",
                "missing_columns": missing_columns,
                "required_columns": REQUIRED_COLUMNS,
            },
        )

    rows: list[tuple[int, dict[str, str]]] = []
    for row_number, row in enumerate(reader, start=2):
        if len(rows) >= MAX_ROWS:
            raise HTTPException(
                status_code=413,
                detail=f"CSV exceeds {MAX_ROWS} row limit",
            )
        rows.append((row_number, row))
    if not rows:
        raise HTTPException(status_code=400, detail="CSV contains no data rows")

    clean_rows, errors, warnings = validate_csv_rows(rows)
    invalid_ratio = len(errors) / len(rows)
    if len(errors) > 0 and invalid_ratio > 0.10:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "More than 10% of rows failed validation",
                "invalid_rows": len(errors),
                "total_rows": len(rows),
                "invalid_ratio": round(invalid_ratio, 6),
                "row_errors": errors,
            },
        )

    if not clean_rows:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "CSV contains no valid rows",
                "row_errors": errors,
            },
        )

    try:
        result = run_evaluation(clean_rows)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    payload = asdict(result)
    payload["total_rows"] = len(rows)
    payload["invalid_rows"] = len(errors)
    payload["warnings"] = list(payload.get("warnings", [])) + list(warnings)
    payload["row_errors"] = errors
    return payload


@router.get("/eval/templates")
async def get_eval_templates():
    return {
        "formats": [
            {
                "format": template_format,
                "download_url": f"/api/eval/templates/{template_format}.csv",
            }
            for template_format in TEMPLATE_FORMATS
        ],
        "required_columns": REQUIRED_COLUMNS,
        "example_count": len(example_template_rows()),
    }


@router.get("/eval/templates/{template_format}.csv")
async def download_eval_template(template_format: str):
    if template_format not in TEMPLATE_FORMATS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown template format {template_format!r}",
        )

    output = io.StringIO()
    rows = example_template_rows()
    fieldnames = ["row_id"] + REQUIRED_COLUMNS
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                f'attachment; filename="soc_eval_template_{template_format}.csv"'
            )
        },
    )
