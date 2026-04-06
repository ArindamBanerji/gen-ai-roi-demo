# ============================================================================
# F9 — Analyst Benchmarking Report
# GET /api/soc/analyst-benchmarking
# Reads from ShadowDecision nodes (source="v_shadow_synthetic_v3")
# ============================================================================

@router.get("/analyst-benchmarking")
async def get_analyst_benchmarking():
    """
    F9 analyst benchmarking report derived from V-SHADOW-SYNTHETIC-v3.

    Returns overall agreement rate, per-category breakdown (sorted by
    agreement rate ascending — least agreement first = most interesting),
    per-archetype override precision, and day-level variance.

    Returns graceful "accumulating" state if no ShadowDecision nodes exist.
    """
    SOURCE = "v_shadow_synthetic_v3"

    # ── 1. Overall ────────────────────────────────────────────────────────
    overall_result = await neo4j_client.run_query(
        """
        MATCH (sd:ShadowDecision {source: $source})
        RETURN count(sd) AS total,
               sum(CASE WHEN sd.agreed    THEN 1 ELSE 0 END) AS agreed_count,
               sum(CASE WHEN sd.ai_correct THEN 1 ELSE 0 END) AS ai_correct_count
        """,
        {"source": SOURCE},
    )

    row = overall_result[0] if overall_result else {}
    total = row.get("total", 0)

    if not total:
        return {
            "status": "accumulating",
            "message": "Shadow decision data not yet loaded. Run Step 3 ingest first.",
        }

    overall_agree_rate = round(row["agreed_count"] / total, 4)
    overall_ai_accuracy = round(row["ai_correct_count"] / total, 4)

    # ── 2. Per category ───────────────────────────────────────────────────
    cat_result = await neo4j_client.run_query(
        """
        MATCH (sd:ShadowDecision {source: $source})
        RETURN sd.category AS category,
               count(sd)   AS total,
               sum(CASE WHEN sd.agreed     THEN 1 ELSE 0 END) AS agreed_count,
               sum(CASE WHEN sd.ai_correct THEN 1 ELSE 0 END) AS ai_correct_count,
               sum(CASE WHEN NOT sd.agreed THEN 1 ELSE 0 END) AS override_count
        ORDER BY agreed_count ASC
        """,
        {"source": SOURCE},
    )

    per_category = {}
    for r in cat_result:
        cat_total = r["total"] or 1
        per_category[r["category"]] = {
            "agree_rate":     round(r["agreed_count"]    / cat_total, 4),
            "ai_accuracy":    round(r["ai_correct_count"] / cat_total, 4),
            "override_count": r["override_count"],
            "total":          r["total"],
        }

    # ── 3. Per archetype ──────────────────────────────────────────────────
    arch_result = await neo4j_client.run_query(
        """
        MATCH (sd:ShadowDecision {source: $source})
        RETURN sd.analyst AS analyst,
               sum(CASE WHEN NOT sd.agreed THEN 1 ELSE 0 END) AS override_count,
               sum(CASE WHEN NOT sd.agreed AND sd.analyst_correct
                        THEN 1 ELSE 0 END) AS correct_overrides
        ORDER BY override_count DESC
        """,
        {"source": SOURCE},
    )

    per_archetype = {}
    for r in arch_result:
        oc = r["override_count"] or 1
        per_archetype[r["analyst"]] = {
            "override_count":     r["override_count"],
            "override_precision": round(r["correct_overrides"] / oc, 4),
        }

    # ── 4. Day variance ───────────────────────────────────────────────────
    day_result = await neo4j_client.run_query(
        """
        MATCH (sd:ShadowDecision {source: $source})
        WITH sd.day AS day,
             count(sd) AS day_total,
             sum(CASE WHEN sd.agreed THEN 1 ELSE 0 END) AS day_agreed
        WITH day, round(toFloat(day_agreed) / day_total, 4) AS daily_rate
        RETURN min(daily_rate) AS min_daily_agree,
               max(daily_rate) AS max_daily_agree
        """,
        {"source": SOURCE},
    )

    day_row = day_result[0] if day_result else {}
    min_rate = day_row.get("min_daily_agree", 0.0)
    max_rate = day_row.get("max_daily_agree", 1.0)
    spread = round((max_rate or 0) - (min_rate or 0), 4)
    trend = "stable" if spread < 0.20 else "variable"

    # ── Lead finding ──────────────────────────────────────────────────────
    # Category with lowest agreement rate (most interesting)
    lowest_cat = min(per_category, key=lambda c: per_category[c]["agree_rate"])
    lowest_rate = per_category[lowest_cat]["agree_rate"]
    lead_finding = (
        f"On {lowest_cat.replace('_', ' ')}, analysts override the AI "
        f"{round((1 - lowest_rate) * 100)}% of the time even when the AI "
        f"recommendation is correct. This is a training opportunity."
    )

    return {
        "status": "ready",
        "source": SOURCE,
        "total_decisions": total,
        "overall_agreement_rate": overall_agree_rate,
        "overall_ai_accuracy": overall_ai_accuracy,
        "lead_finding": lead_finding,
        "per_category": per_category,
        "per_archetype": per_archetype,
        "day_variance": {
            "min_daily_agree": min_rate,
            "max_daily_agree": max_rate,
            "trend": trend,
        },
    }
