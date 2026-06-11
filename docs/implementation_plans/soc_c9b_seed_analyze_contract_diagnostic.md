# SOC C9B Seed Script ↔ Analyze Route Field Contract Diagnostic

Date: 2026-06-08
Model: gpt-5.3
Task Type: Broken-code-friendly diagnostic audit. No code changes.
Repo: C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50

## Executive Summary
- Field contract: MATCH.
- Value contract: NORMALIZATION_RISK.
- Runtime blocker: NO.
- Optional robustness: YES.
- Blocking fixer needed: NO.
- Seed field: The C9B seed script writes Alert `alert_type`; for `credential_access` it writes lowercase `anomalous_login`.
- Analyze route category source: `/api/alert/analyze` receives `alert_id`, loads graph context, reads `context["alert_type"]`, and calls `resolve_alert_category(alert_type)`.
- Smoke script body source: `scripts/soc_c9b_live_age_smoke.py:288` posts `{"alert_id": alert_id}` to `/api/alert/analyze`.
- Main finding: The current seed/smoke/analyze path uses the same field and compatible lowercase mapped values, but the resolver is exact-case and would not map uppercase `CREDENTIAL_STUFFING`.
- Recommended next step: No blocking fixer for C9B seed/smoke/analyze. Optional robustness: normalize `alert_type` case or add uppercase aliases if external uppercase values are expected.

## Path Resolution
- Repo path: C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50.
- Seed script candidates: `scripts/soc_c9b_seed_alerts.py`, generated diagnostic report name matches, and pycache files. Only `scripts/soc_c9b_seed_alerts.py` is the relevant source seed script.
- Seed script used: `scripts/soc_c9b_seed_alerts.py`.
- triage.py found: YES, `backend/app/routers/triage.py`.
- resolve_alert_category found: YES, `backend/app/domains/soc/config.py:308`.
- config.py found: YES, `backend/app/domains/soc/config.py`.
- smoke script found: YES, `scripts/soc_c9b_live_age_smoke.py`.

## Files and Functions Read
- `scripts/soc_c9b_seed_alerts.py`: read to identify Alert properties and seed values.
- `backend/app/routers/triage.py`: read to identify `analyze_alert()` request handling, graph load, and category resolution.
- `backend/app/main.py`: read to verify `triage.router` is mounted with `/api`.
- `backend/app/models/schemas.py`: read to identify `ProcessAlertRequest`.
- `backend/app/db/neo4j.py`: read to identify `get_alert()` and `get_security_context()` graph fields.
- `backend/app/domains/soc/config.py`: read to identify `ALERT_TYPE_CATEGORY_MAP` and `resolve_alert_category()`.
- `scripts/soc_c9b_live_age_smoke.py`: read to identify the smoke POST body.

## Q1 — Seed Script Alert Node Properties
`scripts/soc_c9b_seed_alerts.py` defines credential-access seed values through `CATEGORY_ALERT_TYPES`. The credential-access entry maps to lowercase `anomalous_login` at `scripts/soc_c9b_seed_alerts.py:14-15`. `AlertSpec` contains `category` and `alert_type` fields at `scripts/soc_c9b_seed_alerts.py:84-90`, and `build_alert_spec()` derives `alert_type=CATEGORY_ALERT_TYPES[category]` at `scripts/soc_c9b_seed_alerts.py:118-127`.

Alert node properties set by the seed script:

- `alert_id`: `spec.alert_id`, `scripts/soc_c9b_seed_alerts.py:286`.
- `id`: `spec.alert_id`, `scripts/soc_c9b_seed_alerts.py:287`.
- `category`: `spec.category`, `scripts/soc_c9b_seed_alerts.py:288`.
- `severity`: `spec.severity`, `scripts/soc_c9b_seed_alerts.py:289`.
- `alert_type`: `spec.alert_type`, `scripts/soc_c9b_seed_alerts.py:290`.
- `status`: `"pending"`, `scripts/soc_c9b_seed_alerts.py:291`.
- `origin`: `"c9b_seed"`, `scripts/soc_c9b_seed_alerts.py:292`.
- `source`: `"c9b_seed"`, `scripts/soc_c9b_seed_alerts.py:293`.
- `c9b_proof`: `True`, `scripts/soc_c9b_seed_alerts.py:294`.
- `timestamp_epoch`: `spec.timestamp_epoch`, `scripts/soc_c9b_seed_alerts.py:295`.
- `source_location`: `spec.source_location`, `scripts/soc_c9b_seed_alerts.py:296`.
- `user_id`: `spec.user_id`, `scripts/soc_c9b_seed_alerts.py:297`.
- `asset_id`: `spec.asset_id`, `scripts/soc_c9b_seed_alerts.py:298`.
- `attack_pattern_id`: `""`, `scripts/soc_c9b_seed_alerts.py:299`.
- `mfa_completed`: `spec.mfa_completed`, `scripts/soc_c9b_seed_alerts.py:300`.
- `device_fingerprint_match`: `spec.device_fingerprint_match`, `scripts/soc_c9b_seed_alerts.py:301`.
- `vpn_provider`: `"c9b_seed"`, `scripts/soc_c9b_seed_alerts.py:302`.

Specific answers:
- Does it set `alert_type`? YES, `scripts/soc_c9b_seed_alerts.py:290`.
- Does it set `situation_type`? NO evidence found in the seed Alert node properties at `scripts/soc_c9b_seed_alerts.py:286-302`.
- Does it set `category`? YES, `scripts/soc_c9b_seed_alerts.py:288`.
- What exact property name is used? `alert_type` is the route-read category input.
- What exact example value/casing is used for credential_access alerts? `anomalous_login`, lowercase, from `scripts/soc_c9b_seed_alerts.py:14-15`.

## Q2 — Analyze Route Alert Data Source
The route is declared as `@router.post("/alert/analyze")` in `backend/app/routers/triage.py:146`; `backend/app/main.py:122` mounts `triage.router` with prefix `/api`, making the full path `/api/alert/analyze`.

The request model is `ProcessAlertRequest`, with `alert_id`, optional `deployment_version`, and optional `simulate_failure` at `backend/app/models/schemas.py:33-37`. The handler reads `alert_id = request.alert_id` at `backend/app/routers/triage.py:173`.

The route then loads graph data:

- `alert_data = await neo4j_client.get_alert(alert_id)`, `backend/app/routers/triage.py:178`.
- Missing alert raises 404 at `backend/app/routers/triage.py:180-181`.
- `context = await neo4j_client.get_security_context(alert_id)`, `backend/app/routers/triage.py:186`.
- Missing context raises 404 at `backend/app/routers/triage.py:188-189`.

`get_alert()` matches `Alert {alert_id: $alert_id}` and returns the graph Alert at `backend/app/db/neo4j.py:400-404`. `get_security_context()` starts from `MATCH (alert:Alert {alert_id: $alert_id})` and requires Asset/User matches at `backend/app/db/neo4j.py:77-80`.

Classification: both. The POST body supplies `alert_id`; the route reads Alert/context data from the graph by that `alert_id`.

## Q3 — Analyze Route Category Field
The handler reads graph-derived `alert_type` from context:

- `alert_type = context.get("alert_type") or "unknown"`, `backend/app/routers/triage.py:194`.
- `alert_category = resolve_alert_category(alert_type)`, `backend/app/routers/triage.py:197`.

`get_security_context()` populates that field from the Alert node:

- `"alert_type": alert.get("alert_type")`, `backend/app/db/neo4j.py:136`.

The resolver then performs a mapping lookup:

- `normalized = (alert_type or "").strip()`, `backend/app/domains/soc/config.py:320`.
- `category = ALERT_TYPE_CATEGORY_MAP.get(normalized)`, `backend/app/domains/soc/config.py:321`.

Classification: graph Alert `alert_type` via `resolve_alert_category()` and `ALERT_TYPE_CATEGORY_MAP`. The handler does not use graph Alert `situation_type` or `category` for category resolution in this path.

## Q4 — Seed Field vs Route Field Contract
The field contract matches.

- Seed writes `alert_type` to Alert nodes at `scripts/soc_c9b_seed_alerts.py:290`.
- Graph context returns `alert.get("alert_type")` as `context["alert_type"]` at `backend/app/db/neo4j.py:136`.
- Analyze reads `context.get("alert_type")` at `backend/app/routers/triage.py:194`.
- Analyze resolves category by passing that value to `resolve_alert_category()` at `backend/app/routers/triage.py:197`.

The seed script matters because the smoke script does not post `alert_type`, `situation_type`, or `category`; it posts only `alert_id`:

```python
score = client.post("/api/alert/analyze", json={"alert_id": alert_id})
```

Evidence: `scripts/soc_c9b_live_age_smoke.py:288`.

## Q5 — resolve_alert_category Logic
`resolve_alert_category()` is defined at `backend/app/domains/soc/config.py:308-331`. It uses the module-level `ALERT_TYPE_CATEGORY_MAP`, not a `get_alert_category_mapping()` method and not a classifier.

Mapping and normalization evidence:

- `ALERT_TYPE_CATEGORY_MAP` begins at `backend/app/domains/soc/config.py:266`.
- Credential-access keys include lowercase `"anomalous_login"` at `backend/app/domains/soc/config.py:268`, `"brute_force"` at line 270, `"credential_stuffing"` at line 271, and `"credential_access"` at line 272.
- The resolver docstring says it uses `ALERT_TYPE_CATEGORY_MAP`, `backend/app/domains/soc/config.py:309-315`.
- It strips whitespace only: `normalized = (alert_type or "").strip()`, `backend/app/domains/soc/config.py:320`.
- It requires exact-case keys: `category = ALERT_TYPE_CATEGORY_MAP.get(normalized)`, `backend/app/domains/soc/config.py:321`.
- It returns `UNCLASSIFIED_CATEGORY` when unmapped, `backend/app/domains/soc/config.py:322-331`.

Answers:
- Does it use `get_alert_category_mapping`? NO evidence found; the active code uses `ALERT_TYPE_CATEGORY_MAP`.
- Does it normalize case? NO; it strips whitespace only.
- Does it require exact-case keys? YES.
- Does it support uppercase aliases? NO evidence found in `ALERT_TYPE_CATEGORY_MAP`; uppercase `CREDENTIAL_STUFFING` is not present.

## Q6 — CREDENTIAL_STUFFING Trace
If an Alert is seeded in AGE with `alert_type="CREDENTIAL_STUFFING"` and the smoke script posts `alert_id` referencing that alert, analyze will not resolve `category="credential_access"` in the current source. It will resolve to `unclassified` and the handler will return HTTP 422.

Trace:

1. Request body: the smoke script posts `{"alert_id": alert_id}` to `/api/alert/analyze`, `scripts/soc_c9b_live_age_smoke.py:288`.
2. Graph load or body parse: the handler reads `request.alert_id` at `backend/app/routers/triage.py:173`, loads the Alert at line 178, and loads context at line 186.
3. Category field read: `get_security_context()` places graph `alert.get("alert_type")` into `context["alert_type"]` at `backend/app/db/neo4j.py:136`; the handler reads it at `backend/app/routers/triage.py:194`.
4. Normalization/mapping/classifier: `resolve_alert_category()` strips only whitespace at `backend/app/domains/soc/config.py:320` and does exact lookup at line 321. There is no classifier and no lowercase conversion.
5. Final category: the mapping includes lowercase `"credential_stuffing"` at `backend/app/domains/soc/config.py:271`, but not uppercase `CREDENTIAL_STUFFING`; unmapped values return `unclassified` at `backend/app/domains/soc/config.py:322-331`; the route rejects `unclassified` with HTTP 422 at `backend/app/routers/triage.py:198-211`.

This is a hypothetical normalization risk for uppercase inputs, not a proven blocker for the current C9B seed/smoke path. The current seed uses lowercase `anomalous_login` for credential-access alerts at `scripts/soc_c9b_seed_alerts.py:14-15`, and that value maps to `credential_access` at `backend/app/domains/soc/config.py:268`.

## Q7 — Required Analyze Context
Required context and behavior:

- Scorer readiness: `analyze_alert()` checks scorer availability before processing; missing scorer raises 503 at `backend/app/routers/triage.py:157-170`.
- Alert node: the handler calls `get_alert(alert_id)` at `backend/app/routers/triage.py:178`; missing alert raises 404 at `backend/app/routers/triage.py:180-181`.
- Asset node and `DETECTED_ON` edge: `get_security_context()` requires `MATCH (alert)-[:DETECTED_ON]->(asset:Asset)` at `backend/app/db/neo4j.py:78`; missing required context causes route 404 at `backend/app/routers/triage.py:188-189`.
- User node and `INVOLVES` edge: `get_security_context()` requires `MATCH (alert)-[:INVOLVES]->(user:User)` at `backend/app/db/neo4j.py:79`; missing required context causes route 404 at `backend/app/routers/triage.py:188-189`.
- Optional related graph context: attack pattern, playbook, travel, SLA, and behavior-pattern matches are optional at `backend/app/db/neo4j.py:81-85`; missing optional context defaults or remains absent in returned fields at `backend/app/db/neo4j.py:134-155`.
- Factor/scoring context: after category resolution, the handler computes factors with `compute_factor_vector(alert_data, computers, neo4j_client)` at `backend/app/routers/triage.py:219-221`. Failures there are outside the field contract but can affect full analyze success.

The C9B seed script creates the required `INVOLVES` and `DETECTED_ON` edges at `scripts/soc_c9b_seed_alerts.py:311-330`.

## Q8 — Analyze Request Body Format
The route receives `ProcessAlertRequest`, imported in `backend/app/routers/triage.py:33` and used in the handler signature at `backend/app/routers/triage.py:147`.

Pydantic model:

```python
class ProcessAlertRequest(BaseModel):
    """Request to process an alert through the agent"""
    alert_id: str
    deployment_version: Optional[str] = "v3.1"
    simulate_failure: bool = False
```

Evidence: `backend/app/models/schemas.py:33-37`.

Exact request body shape:

```json
{
  "alert_id": "string",
  "deployment_version": "v3.1",
  "simulate_failure": false
}
```

Only `alert_id` is required.

## Contract Classification
- Field contract: MATCH.
- Value contract: NORMALIZATION_RISK.
- Runtime blocker: NO.
- Optional robustness: YES.
- Blocking fixer needed: NO.
- Rationale: The current seed writes Alert `alert_type`, the route reads graph Alert `alert_type`, and the seeded credential-access value `anomalous_login` is present in the resolver map. The resolver is exact-case, so uppercase `CREDENTIAL_STUFFING` would fail, but that is not the current seed/smoke value.
- If blocking fixer needed, smallest future fixer scope: Not applicable.
- If optional robustness only, recommended optional improvement: Normalize `alert_type` case in `resolve_alert_category()` or add uppercase aliases for externally sourced alert types.

## Diagnostic Limitations
- No code was modified.
- No seed scripts were run.
- No smoke scripts were run.
- No tests were run.
- No app server was run.
- Analysis is source-level only.
