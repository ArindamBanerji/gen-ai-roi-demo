"""
Audit Router — Decision audit trail with JSON/CSV export and chain verification

GET /api/audit/decisions?format=json   → JSON array of all decision records
GET /api/audit/decisions?format=csv    → CSV file download
GET /api/audit/verify                  → SHA-256 chain verification result

CSV columns:
  id, alert_id, timestamp, situation_type, action_taken,
  factors, confidence, outcome, hash
"""
import csv
import io

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.services.audit import reconstruct_from_memory, get_decisions, verify_chain


router = APIRouter()

_CSV_COLUMNS = [
    "id",
    "alert_id",
    "timestamp",
    "situation_type",
    "action_taken",
    "factors",
    "confidence",
    "outcome",
    "hash",
]


@router.get("/audit/decisions")
async def get_audit_decisions(format: str = "json"):
    """
    Return the full decision audit trail.

    Query Parameters:
        format: "json" (default) or "csv"

    JSON response: { decisions: [...], total: N }
    CSV response:  attachment download — soc_decision_audit.csv
                   factors column uses "|" as delimiter within the cell
                   hash column contains the SHA-256 chain hash for each record
    """
    print(f"[AUDIT] GET /audit/decisions called — format={format}")

    try:
        # Back-fill from FEEDBACK_GIVEN before returning, so the ledger is
        # always current even if record_decision() was never called directly.
        added = reconstruct_from_memory()
        decisions = get_decisions()
        print(f"[AUDIT] {len(decisions)} records ({added} reconstructed this call)")

        # ================================================================
        # CSV export
        # ================================================================
        if format.lower() == "csv":
            output = io.StringIO()
            writer = csv.writer(output)

            writer.writerow(_CSV_COLUMNS)

            for rec in decisions:
                factors_str = "|".join(rec.get("factors") or [])
                writer.writerow([
                    rec.get("id", ""),
                    rec.get("alert_id", ""),
                    rec.get("timestamp", ""),
                    rec.get("situation_type", ""),
                    rec.get("action_taken", ""),
                    factors_str,
                    rec.get("confidence", ""),
                    rec.get("outcome", ""),
                    rec.get("hash", ""),
                ])

            csv_content = output.getvalue()
            output.close()

            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={
                    "Content-Disposition": 'attachment; filename="soc_decision_audit.csv"'
                },
            )

        # ================================================================
        # JSON export (default)
        # ================================================================
        return {
            "decisions": decisions,
            "total": len(decisions),
        }

    except Exception as exc:
        print(f"[ERROR] Audit retrieval failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Audit retrieval failed: {str(exc)}",
        )


@router.get("/audit/verify")
async def verify_audit_chain():
    """
    Verify the SHA-256 tamper-evident hash chain for all decision records.

    Walks the ledger in chronological order (insertion order) and recomputes
    each record's hash from: previous_hash + JSON of immutable decision fields.

    Returns:
        {
          "chain_length":   int,
          "verified":       bool,
          "first_record":   ISO timestamp | null,
          "last_record":    ISO timestamp | null,
          "broken_at_index": int   (only present when verified=False)
        }

    A verified=True result means no records have been reordered, inserted, or
    had their immutable fields (id, alert_id, timestamp, situation_type,
    action_taken, factors, confidence) tampered with since they were recorded.
    """
    print("[AUDIT] GET /audit/verify called")

    try:
        # Reconstruct first so the ledger is current
        reconstruct_from_memory()
        result = verify_chain()
        print(
            f"[AUDIT] verify_chain → verified={result['verified']}, "
            f"chain_length={result['chain_length']}"
        )
        return result

    except Exception as exc:
        print(f"[ERROR] Chain verification failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Chain verification failed: {str(exc)}",
        )
