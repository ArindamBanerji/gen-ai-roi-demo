"""
SOC factor orchestrator -- async Neo4j -> FactorComputer -> GAE assembly.

Calls each FactorComputer in order, then delegates vector assembly to GAE.

Reference: docs/soc_copilot_design_v1.md Sec.5.3.
"""

from typing import Any

from gae.contracts import SchemaContract, PropertySpec
from gae.factors import assemble_factor_vector


async def compute_factor_vector(alert, computers, neo4j):
    """
    Async orchestrator.  Calls each FactorComputer, then delegates to GAE.

    Parameters
    ----------
    alert : dict | Alert
        Alert object with SOC context properties.
    computers : list[FactorComputer]
        Ordered list of FactorComputer instances (from config.get_factor_computers()).
    neo4j : Neo4jClient
        Async Neo4j client with run_query(query, params) method.

    Returns
    -------
    np.ndarray, shape (d_f,)
        Dense factor vector assembled by GAE assemble_factor_vector (Eq. 2).
    """
    vector, _ = await compute_factor_vector_with_provenance(alert, computers, neo4j)
    return vector


async def compute_factor_vector_with_provenance(alert, computers, neo4j):
    """
    Compute the existing scorer factor vector plus per-factor provenance.

    The scorer input remains the same dense float vector.  The provenance map is
    an audit sidecar persisted on Decision nodes so K3 fallbacks are visible.
    """
    values = []
    names = []
    provenance = {}
    for computer in computers:
        raw = await computer.compute(alert, neo4j)
        value = float(raw)
        name = computer.name
        values.append(value)
        names.append(name)
        provenance[name] = await _factor_provenance(name, alert, neo4j, value)

    # Build raw dict + schema, then delegate to GAE
    raw_dict = {name: val for name, val in zip(names, values)}
    schema = SchemaContract(
        node_type="alert",
        properties=tuple(
            PropertySpec(name=n, required=False, default_value=0.5)
            for n in names
        ),
    )
    return assemble_factor_vector(raw_dict, schema), provenance


async def _factor_provenance(name: str, alert: Any, neo4j: Any, value: float) -> dict:
    """Return audit provenance for one extracted SOC factor."""
    if name == "privileged_identity_context":
        fields = (
            "user_risk_score",
            "user_title",
            "mfa_completed",
            "device_fingerprint_match",
        )
        return _provenance_record(
            value,
            "alert_field" if _has_any(alert, fields) else "fixture_fallback",
            "identity/session fields" if _has_any(alert, fields) else "neutral default",
        )

    if name == "asset_criticality":
        alert_id = _get(alert, "id", "")
        if alert_id and await _query_has_rows(
            neo4j,
            f"MATCH (a:Alert {{alert_id: {_S(alert_id)}}})-[:DETECTED_ON]->(asset:Asset) "
            "RETURN asset.criticality AS criticality LIMIT 1",
        ):
            return _provenance_record(value, "graph_context", "Alert->Asset graph context")
        return _provenance_record(value, "fixture_fallback", "neutral asset default")

    if name == "threat_intel_enrichment":
        return await _threat_intel_provenance(alert, neo4j, value)

    if name == "pattern_history":
        category = _get(alert, "category", "") or _get(alert, "alert_type", "")
        if category and await _query_has_rows(
            neo4j,
            f"MATCH (d:Decision)-[:TRIGGERED_EVOLUTION]->(evo:EvolutionEvent) "
             f"WHERE d.domain = 'soc' AND d.category = {_S(category)} "
             "AND d.verified_correct = true "
            "RETURN d.decision_id AS decision_id LIMIT 1",
        ):
            return _provenance_record(value, "learned", "verified decision history")
        return _provenance_record(value, "fixture_fallback", "neutral pattern-history baseline")

    if name == "time_anomaly":
        fields = ("weekend_login", "business_hours_login")
        return _provenance_record(
            value,
            "alert_field" if _has_any(alert, fields) else "fixture_fallback",
            "alert time fields" if _has_any(alert, fields) else "conservative time default",
        )

    if name == "device_trust":
        fields = ("mfa_completed", "device_fingerprint_match", "vpn", "vpn_provider")
        return _provenance_record(
            value,
            "alert_field" if _has_any(alert, fields) else "fixture_fallback",
            "alert device/session fields" if _has_any(alert, fields) else "device trust default",
        )

    return _provenance_record(value, "unknown", "unclassified factor source")


async def _threat_intel_provenance(alert: Any, neo4j: Any, value: float) -> dict:
    alert_id = _get(alert, "id", "")
    if not alert_id:
        return _provenance_record(value, "fixture_fallback", "missing alert_id")

    campaign_rows = await _query_rows(
        neo4j,
        f"MATCH (a:Alert {{alert_id: {_S(alert_id)}}})-[:MEMBER_OF]->(c:Campaign) "
        "RETURN c.campaign_id AS campaign_id LIMIT 1",
    )
    if campaign_rows:
        return _provenance_record(value, "graph_context", "campaign membership graph context")

    ti_rows = await _query_rows(
        neo4j,
        f"MATCH (a:Alert {{alert_id: {_S(alert_id)}}})-[:HAS_INDICATOR]->(ti:ThreatIndicator) "
        "RETURN ti.source AS source LIMIT 10",
    )
    sources = {
        str(row.get("source") or "unknown").lower()
        for row in ti_rows
        if isinstance(row, dict)
    }
    if any("live" in source or "pulsedive" in source or "greynoise" in source for source in sources):
        return _provenance_record(value, "scraped_external", "live threat intelligence connector")
    if sources:
        return _provenance_record(value, "fixture_fallback", "local threat-intel fallback")
    return _provenance_record(value, "fixture_fallback", "no threat-intel match")


def _provenance_record(value: float, source: str, detail: str) -> dict:
    return {
        "value": float(value),
        "source": source,
        "detail": detail,
    }


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _has_any(obj: Any, keys: tuple[str, ...]) -> bool:
    return any(_get(obj, key) is not None for key in keys)


async def _query_has_rows(neo4j: Any, query: str) -> bool:
    return bool(await _query_rows(neo4j, query))


async def _query_rows(neo4j: Any, query: str) -> list:
    try:
        rows = await neo4j.run_query(query)
        return rows if isinstance(rows, list) else []
    except Exception:
        return []


def _S(val) -> str:
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    return "'" + str(val).replace("\\", "\\\\").replace("'", "\\'") + "'"
