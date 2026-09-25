# Demo Surface Validation — Nine Story Beats

**Validation:** 2026-09-17  
**Backend tested:** `http://127.0.0.1:8001` (requested port 8000 was down)  
**UI:** NOT TESTED — Python Playwright unavailable  
**Tier:** live demo/API surface; values below are runtime responses.

## Summary

API: 7 pass, 1 fail, 1 missing. UI: API-only.

| Check # | Name | Priority | API | UI | Actual values / response keys | Status |
|---:|---|---:|---|---|---|---|
| 1 | Policy-conflict override | 1 | PASS | NOT TESTED | /api/alert/policy-check: ['alert_id', 'conflicting_policies', 'has_conflict', 'policies_applied', 'resolution']; /api/alert/policy-history: ['conflicts', 'total_count'] | NEEDS PLANTING |
| 2 | Tamper-evident evidence ledger | 1 | PASS | NOT TESTED | /api/audit/decisions: ['decisions', 'total']; /api/audit/verify: ['archived_epochs', 'chain_length', 'epoch', 'first_record', 'last_record', 'verified']; /api/soc/evidence-room: ['audit_trail', 'conservation', 'generated_at', 'hash_chain', 'override_analysis']; /api/audit/decisions?format=csv: str | LIVE |
| 3 | Cross-graph / multi-source query | 1 | PASS | NOT TESTED | /api/discoveries: ['as_of_epoch_ms', 'cache', 'discoveries', 'domain', 'errors', 'generated_at', 'source_domains', 'total']; /api/soc/graph/prebuilt-queries: ['count', 'queries'] | NEEDS PLANTING |
| 4 | Gate health band | 1 | PASS | NOT TESTED | /api/soc/learning-health: ['auto_pause_active', 'baseline', 'baseline_std', 'complacency_advisory', 'components', 'conservation', 'health_source', 'interpretation', 'learning_enabled', 'overallSafe', 'pre_activation', 'provider_observed_at', 'provider_source', 'red_days', 'signal', 'status', 'status_reason', 'theta_min'] | NEEDS PLANTING |
| 5 | Centroid rollback | 1 | PASS | NOT TESTED | /api/soc/checkpoint/list: ['checkpoints'] | NEEDS PLANTING |
| 6 | Switching cost / moat | 1 | 404 (endpoint missing) | NOT TESTED | /api/metrics/switching-cost: ['detail'] | NEEDS PLANTING |
| 7 | Compounding curve | 1 | PASS | NOT TESTED | /api/metrics/compounding: ['business_impact', 'evolution_events', 'headline', 'historical_fallback', 'period', 'weekly_trend']; /api/soc/learning-state: ['bootstrap_category_weights', 'categories_active', 'checkpoint_id', 'decision_count', 'frozen', 'iks_components', 'iks_interpretation', 'iks_v2', 'last_verified_at', 'total_decisions', 'verified_decisions']; /api/soc/iks-trend: ['current', 'trend'] | LIVE |
| 8 | Frozen-twin | 1 | PARTIAL | NOT TESTED | /api/learning/frozen-twin: ['detail'] | NEEDS PLANTING |
| 9 | RSI rejection moment | 1 | PASS | NOT TESTED | /api/evolution/recent-events: ['count', 'events', 'limit'] | LIVE |

## Details

### 1. Policy-conflict override

- API: **PASS**
- Endpoint correction: None; both paths exist and policy-check was called with a queued alert identifier.
- Empty state: Policy history is non-empty; policy-check needs a valid alert/request input for a rendered decision.
- Planting needed: **True**
- Notes: Endpoint exists; queued alert `ALERT-LM-101` returned no conflict, so a conflict fixture is still needed.

- `/api/alert/policy-check` → HTTP 200; keys `['alert_id', 'conflicting_policies', 'has_conflict', 'policies_applied', 'resolution']`; non-empty `True`
- `/api/alert/policy-history` → HTTP 200; keys `['conflicts', 'total_count']`; non-empty `True`

### 2. Tamper-evident evidence ledger

- API: **PASS**
- Endpoint correction: None.
- Empty state: Audit decisions, verification, evidence room, and CSV export all return non-empty responses.
- Planting needed: **False**
- Notes: Ledger data is live and suitable for recording.

- `/api/audit/decisions` → HTTP 200; keys `['decisions', 'total']`; non-empty `True`
- `/api/audit/verify` → HTTP 200; keys `['archived_epochs', 'chain_length', 'epoch', 'first_record', 'last_record', 'verified']`; non-empty `True`
- `/api/soc/evidence-room` → HTTP 200; keys `['audit_trail', 'conservation', 'generated_at', 'hash_chain', 'override_analysis']`; non-empty `True`
- `/api/audit/decisions?format=csv` → HTTP 200; keys `str`; non-empty `True`

### 3. Cross-graph / multi-source query

- API: **PASS**
- Endpoint correction: Requested /api/soc/graph/prebuilt corrected to /api/soc/graph/prebuilt-queries (GET catalog; execution is POST /api/soc/graph/prebuilt/{query_name}).
- Empty state: The prebuilt-query catalog is non-empty, but the discoveries list is empty.
- Planting needed: **True**
- Notes: The requested singular /prebuilt path is not a live GET route; OpenAPI confirms the corrected catalog path. Discovery data needs planting.

- `/api/discoveries` → HTTP 200; keys `['as_of_epoch_ms', 'cache', 'discoveries', 'domain', 'errors', 'generated_at', 'source_domains', 'total']`; non-empty `True`
- `/api/soc/graph/prebuilt-queries` → HTTP 200; keys `['count', 'queries']`; non-empty `True`

### 4. Gate health band

- API: **PASS**
- Endpoint correction: None.
- Empty state: Learning-health response is non-empty and contains the current gate/health values.
- Planting needed: **True**
- Notes: Live gate-health story.

- `/api/soc/learning-health` → HTTP 200; keys `['auto_pause_active', 'baseline', 'baseline_std', 'complacency_advisory', 'components', 'conservation', 'health_source', 'interpretation', 'learning_enabled', 'overallSafe', 'pre_activation', 'provider_observed_at', 'provider_source', 'red_days', 'signal', 'status', 'status_reason', 'theta_min']`; non-empty `True`

### 5. Centroid rollback

- API: **PASS**
- Endpoint correction: Requested /api/soc/checkpoints corrected to /api/soc/checkpoint/list.
- Empty state: Checkpoint list response is non-empty; rollback itself is a POST mutation and was not executed.
- Planting needed: **True**
- Notes: Rollback inventory is live; no destructive/mutating endpoint was called.

- `/api/soc/checkpoint/list` → HTTP 200; keys `['checkpoints']`; non-empty `True`

### 6. Switching cost / moat

- API: **404 (endpoint missing)**
- Endpoint correction: No correction found in OpenAPI; no live switching-cost route is registered.
- Empty state: The requested panel cannot receive data from this route.
- Planting needed: **True**
- Notes: Needs a route/data source before recording this beat.

- `/api/metrics/switching-cost` → HTTP 404; keys `['detail']`; non-empty `True`

### 7. Compounding curve

- API: **PASS**
- Endpoint correction: Requested /api/soc/learning-state is live; no correction required.
- Empty state: All three compounding/learning responses are non-empty.
- Planting needed: **False**
- Notes: Live values are available for v4 narration.

- `/api/metrics/compounding` → HTTP 200; keys `['business_impact', 'evolution_events', 'headline', 'historical_fallback', 'period', 'weekly_trend']`; non-empty `True`
- `/api/soc/learning-state` → HTTP 200; keys `['bootstrap_category_weights', 'categories_active', 'checkpoint_id', 'decision_count', 'frozen', 'iks_components', 'iks_interpretation', 'iks_v2', 'last_verified_at', 'total_decisions', 'verified_decisions']`; non-empty `True`
- `/api/soc/iks-trend` → HTTP 200; keys `['current', 'trend']`; non-empty `True`

### 8. Frozen-twin

- API: **PARTIAL**
- Endpoint correction: Requested /api/metrics/frozen-twin corrected to /api/learning/frozen-twin.
- Empty state: Corrected frozen-twin endpoint returns a non-empty response.
- Planting needed: **True**
- Notes: The route exists, but the live service reports that Frozen Twin has not been initialized; this is setup/data missing, not a missing route.

- `/api/learning/frozen-twin` → HTTP 404; keys `['detail']`; non-empty `True`

### 9. RSI rejection moment

- API: **PASS**
- Endpoint correction: None.
- Empty state: Recent evolution events return non-empty data.
- Planting needed: **False**
- Notes: Live evolution event stream.

- `/api/evolution/recent-events` → HTTP 200; keys `['count', 'events', 'limit']`; non-empty `True`

## Recording guidance

Safe to record as-is: Tamper-evident evidence ledger, Compounding curve, RSI rejection moment.
Needs planting or input-specific setup: Policy-conflict override, Cross-graph / multi-source query, Gate health band, Centroid rollback, Switching cost / moat, Frozen-twin.
Needs code/route fix: Switching cost / moat.

The specified `localhost:8000` service was not running. The five-copilot launcher exposed the live SOC API on port 8001; all endpoint corrections are recorded above.
