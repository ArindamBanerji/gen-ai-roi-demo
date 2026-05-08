# FEATURE-07: Cross-Graph Discovery — Design Preview

This document is a design preview only. It is grounded in the current code and seed data, not aspirational docs. Source evidence follows the repo grounding rule in `CLAUDE.md:5-16`.

## 0. Roadmap Decisions

- Production Clock 4, not a demo mock. This feature persists through R-07 v1.2.
- Tab 3 placement: a Discovery banner appears above the alert queue in Alert Triage.
- Four algorithms ship in the v1.0 design:
  - Shared Entity
  - Pattern Convergence
  - Temporal Velocity
  - Cross-Factor Anomaly
- API namespace: `GET /api/discoveries?domain=soc`.
- Discovery data model must include `domain` and `source_domains`.
- v1.0 cache: in-memory cache with a short TTL and explicit refresh support.
- v1.1 persistence: AGE-backed Discovery nodes/edges after v1.0 stabilizes.
- Seed data must contain discoverable patterns organically.
- Performance target: full refresh under 5 seconds on the current graph.

## 1. Graph Structure

`backend/app/graph_schema.py` is the single source for the seeded SOC graph contract. The contract defines node labels and required fields at `graph_schema.py:76-151`, seed creation at `graph_schema.py:516-761`, and AGE-safe serialization at `graph_schema.py:46-69`.

### 1.1 Node Labels

| Label | Required Fields | min_count | Seed Count | Notes |
|---|---|---:|---:|---|
| Alert | `alert_id`, `category`, `severity`, `status`, `origin`, `timestamp_epoch`, `user_id`, `asset_id`, `alert_type`, `source_location`, `attack_pattern_id` | 570 | 570 | Required fields from `graph_schema.py:78-84`; seed creates 540 training alerts and 30 demo alerts at `graph_schema.py:584-621`. |
| Decision | `decision_id`, `category`, `action`, `factor_vector`, `confidence`, `outcome`, `timestamp_epoch` | 4860 | 4860 | Required fields from `graph_schema.py:85-101`; seed creates decisions and `DECIDED_ON` atomically at `graph_schema.py:731-751`. |
| User | `user_id`, `name`, `origin`, `department`, `risk_level` | 20 | 20 | Required fields from `graph_schema.py:103-107`; seed creates Users at `graph_schema.py:516-527`. |
| Asset | `asset_id`, `hostname`, `criticality`, `origin`, `asset_type` | 15 | 15 | Required fields from `graph_schema.py:108-113`; seed creates Assets at `graph_schema.py:534-543`. |
| Campaign | `campaign_id`, `category_sequence`, `name`, `origin`, `severity`, `last_seen`, `first_seen`, `alert_count` | 3 | 4 | Required fields from `graph_schema.py:114-124`; seed creates Campaigns at `graph_schema.py:568-582`. |
| ThreatIndicator | `indicator`, `indicator_type`, `severity`, `origin`, `source` | 5 | 5 | Required fields from `graph_schema.py:125-136`; seed creates ThreatIndicators at `graph_schema.py:557-566`. |
| AttackPattern | `pattern_id`, `name`, `mitre_id`, `origin`, `tactic`, `category` | 6 | 6 | Required fields from `graph_schema.py:137-141`; seed creates AttackPatterns at `graph_schema.py:545-555`. |
| TravelRecord | absent from `GRAPH_CONTRACT` | 0 | 0 | `TravelMatchFactor` expects `(User)-[:HAS_TRAVEL]->(TravelRecord)` at `factors.py:153-180`, but the v5 graph contract and seed do not create this label. |
| Device | absent from `GRAPH_CONTRACT` | 0 | 0 | The seed file has no top-level `devices` records in the read-only analysis. |

### 1.2 Relationship Types and Directions

| Relationship | Direction | Count | Notes |
|---|---|---:|---|
| `DECIDED_ON` | `(Decision)-[:DECIDED_ON]->(Alert)` | 4860 | Contract direction at `graph_schema.py:144`; atomic seed create at `graph_schema.py:737-751`. |
| `INVOLVES` | `(Alert)-[:INVOLVES]->(User)` | 570 | Contract direction at `graph_schema.py:145`; seed create at `graph_schema.py:639-645`. |
| `DETECTED_ON` | `(Alert)-[:DETECTED_ON]->(Asset)` | 570 | Contract direction at `graph_schema.py:146`; seed create at `graph_schema.py:653-659`. |
| `MEMBER_OF` | `(Alert)-[:MEMBER_OF]->(Campaign)` | 23 | Contract direction at `graph_schema.py:147`; seed create at `graph_schema.py:697-707`. |
| `CLASSIFIED_AS` | `(Alert)-[:CLASSIFIED_AS]->(AttackPattern)` | 570 | Contract direction at `graph_schema.py:148`; seed create at `graph_schema.py:667-673`. |
| `HAS_INDICATOR` | `(Alert)-[:HAS_INDICATOR]->(ThreatIndicator)` | 81 | Contract direction at `graph_schema.py:149`; seed create at `graph_schema.py:682-688`. |
| `TRIGGERED_EVOLUTION` | `(Decision)-[:TRIGGERED_EVOLUTION]->(EvolutionEvent)` | runtime, min 0 | Contract direction at `graph_schema.py:150`; W2 read path at `factors.py:488-506`. |

### 1.3 Critical Traversal Paths

- Alert ↔ Decision: stored direction is `(d:Decision)-[:DECIDED_ON]->(a:Alert)`. Reverse traversal is allowed in MATCH patterns, but there is no stored `Alert -> Decision` relationship. Evidence: `graph_schema.py:144`, `graph_schema.py:737-751`.
- Alert ↔ User: stored direction is `(a:Alert)-[:INVOLVES]->(u:User)`. Evidence: `graph_schema.py:145`, `graph_schema.py:639-645`.
- Alert ↔ Asset: stored direction is `(a:Alert)-[:DETECTED_ON]->(asset:Asset)`. Evidence: `graph_schema.py:146`, `graph_schema.py:653-659`.
- User ↔ TravelRecord: absent from the current graph contract and seed. `TravelMatchFactor` contains a future/legacy query shape `(u:User {id: ...})-[:HAS_TRAVEL]->(t:TravelRecord)`, but `User` seed fields use `user_id`, not `id`. Evidence: `factors.py:153-180`, `graph_schema.py:103-107`.
- Alert ↔ ThreatIndicator: stored direction is `(a:Alert)-[:HAS_INDICATOR]->(ti:ThreatIndicator)`. Evidence: `graph_schema.py:149`, `graph_schema.py:682-688`.
- Alert ↔ Campaign: stored direction is `(a:Alert)-[:MEMBER_OF]->(c:Campaign)`. Evidence: `graph_schema.py:147`, `graph_schema.py:697-707`.
- Alert ↔ AttackPattern: stored direction is `(a:Alert)-[:CLASSIFIED_AS]->(ap:AttackPattern)`. Evidence: `graph_schema.py:148`, `graph_schema.py:667-673`.

## 2. Seed Data Pattern Verification

Read-only seed analysis used `backend/support/setup/zero_day_decisions_v5.json` plus `SOC_PROFILE_CENTROIDS` from `backend/app/domains/soc/config.py`. The seed counts were: 20 Users, 15 Assets, 540 training Alerts, 30 demo Alerts, 4860 Decisions, 4 Campaigns, 5 ThreatIndicators, 6 AttackPatterns, 0 TravelRecords, and 0 Devices.

### Pattern 1 — Shared Entity Discovery

- EXISTS: YES
- Evidence: `USR-014` is involved in 19 alerts across `cloud_infrastructure`, `insider_threat`, and `lateral_movement` within a 30-day window from epoch `1741046400000` to `1743638400000`. Example seed evidence includes `SYN-CI-D005-001` with `user_id: USR-014`, `asset_id: AST-004`, and `timestamp_epoch: 1741392000000` at `zero_day_decisions_v5.json:947-958`.
- Specific satisfying nodes: `USR-014`; example alerts include `SYN-LM-D001-001`, `SYN-IT-D004-001`, `SYN-CI-D005-001`, `SYN-LM-D006-001`, `SYN-IT-D009-001`, `SYN-CI-D010-001`.
- Specific seed data change if NO: not needed.

### Pattern 2 — Threat Intel Intersection

- EXISTS: YES
- Evidence: The highest-volume shared user `USR-014` has no threat indicators in the sampled Pattern 1 set, but another Pattern 1 user, `USR-017`, has 13 alerts across `credential_access` and `data_exfiltration` within 30 days and has threat indicators on those alerts. Example: `SYN-DE-D004-001` has `user_id: USR-017` and indicators `45.33.32.156` and `malware-traffic-analysis.net` at `zero_day_decisions_v5.json:818-832`; `45.33.32.156` is a seeded ThreatIndicator at `zero_day_decisions_v5.json:362`.
- Specific satisfying nodes: `USR-017`, `SYN-DE-D004-001`, `45.33.32.156`, `malware-traffic-analysis.net`.
- Specific seed data change if NO: not needed.

### Pattern 3 — Pattern Convergence

- EXISTS: YES
- Evidence: Multiple categories share action `investigate` with confidence above 0.70. Examples: `SYN-DEC-a5d98b1f` is `credential_access`, action `investigate`, confidence `0.73` at `zero_day_decisions_v5.json:8712-8725`; `SYN-DEC-fa7e0843` is `lateral_movement`, action `investigate`, confidence `0.95` at `zero_day_decisions_v5.json:8922-8934`; `SYN-DEC-b44b216e` is `data_exfiltration`, action `investigate`, confidence `0.9` at `zero_day_decisions_v5.json:9132-9144`.
- Specific satisfying nodes: `SYN-DEC-a5d98b1f`, `SYN-DEC-fa7e0843`, `SYN-DEC-b44b216e`.
- Specific seed data change if NO: not needed.

### Pattern 4 — Temporal Velocity

- EXISTS: YES
- Evidence: `USR-014` has recent_count `4`, baseline_count `1`, normalized 7-day baseline `0.2333`, and ratio `17.14`. `AST-004` also satisfies the same ratio. Example supporting seed lines include `SYN-ME-D004-001` on `AST-004` at `zero_day_decisions_v5.json:835-844`, `SYN-CI-D005-001` on `USR-014`/`AST-004` at `zero_day_decisions_v5.json:947-958`, and `SYN-LM-D007-001` on `AST-004` at `zero_day_decisions_v5.json:1061-1072`.
- Specific satisfying nodes: `USR-014`, `AST-004`.
- Specific seed data change if NO: not needed.

### Pattern 5 — Cross-Factor Anomaly

- EXISTS: YES
- Evidence: Using `SOC_PROFILE_CENTROIDS` from `config.py:122-199`, read-only L2 analysis found 4063 decisions whose factor vector is closer to another category centroid than the assigned category. Example: `SYN-DEC-7187c42e` is assigned `malware_execution`, but its factor vector is closer to `insider_threat` by distance gap `0.2483`; the decision and factor vector are at `zero_day_decisions_v5.json:60351-60363`.
- Specific satisfying nodes: `SYN-DEC-7187c42e` and many others.
- Specific seed data change if NO: not needed.

## 3. AGE-Compatible Cypher Queries

All query blocks below follow these AGE rules: no `datetime()`, no `duration()`, no named `$param`, no `MERGE`, no `ON CREATE SET` or `ON MATCH SET`, no `CASE WHEN`, no `toFloat()`, no `labels(n) IN [...]`, no array properties, strings serialized with `_S()`, computed epoch integers inlined, `cnt` used instead of alias `count`, and JSON strings parsed in Python. These rules are grounded in `CLAUDE.md:102-130` and existing AGE-safe patterns such as inline epoch counting in `learning_health.py:261-274`.

### 3.1 Algorithm 1 — Shared Entity Discovery

Design: find Users and Assets involved in 3+ alerts across 2+ categories after `cutoff_epoch`, then enrich matching shared-entity discoveries with ThreatIndicator intersections.

Python inputs:

- `cutoff_epoch`
- `min_alerts = 3`
- `min_categories = 2`
- optional `limit`, default `50`

User query:

```cypher
MATCH (a:Alert)-[:INVOLVES]->(u:User)
WHERE a.timestamp_epoch >= 1741046400000
RETURN u.user_id AS entity_id,
       u.name AS entity_name,
       collect(a.alert_id) AS alert_ids_json,
       collect(a.category) AS categories_json,
       min(a.timestamp_epoch) AS first_seen_epoch,
       max(a.timestamp_epoch) AS last_seen_epoch,
       count(a) AS cnt
ORDER BY cnt DESC
LIMIT 50
```

Asset query:

```cypher
MATCH (a:Alert)-[:DETECTED_ON]->(asset:Asset)
WHERE a.timestamp_epoch >= 1741046400000
RETURN asset.asset_id AS entity_id,
       asset.hostname AS entity_name,
       collect(a.alert_id) AS alert_ids_json,
       collect(a.category) AS categories_json,
       min(a.timestamp_epoch) AS first_seen_epoch,
       max(a.timestamp_epoch) AS last_seen_epoch,
       count(a) AS cnt
ORDER BY cnt DESC
LIMIT 50
```

Threat-intel intersection lookup:

```cypher
MATCH (a:Alert)-[:INVOLVES]->(u:User)
MATCH (a)-[:HAS_INDICATOR]->(ti:ThreatIndicator)
WHERE u.user_id = 'USR-017'
  AND a.timestamp_epoch >= 1741046400000
RETURN ti.indicator AS indicator,
       ti.indicator_type AS indicator_type,
       ti.severity AS indicator_severity,
       collect(a.alert_id) AS alert_ids_json,
       count(a) AS cnt
ORDER BY cnt DESC
LIMIT 20
```

Python post-processing:

1. Parse AGE-normalized collection fields or JSON strings into Python lists.
2. Enforce `cnt >= min_alerts`.
3. Deduplicate categories and require `len(categories) >= min_categories`.
4. Optionally re-window results in Python for exact 30-day windows.
5. Compute confidence from alert count, category count, and threat-intel intersection.
6. Emit one discovery per qualifying entity.

Output discovery fields:

- `discovery_id`
- `domain`
- `source_domains`
- `algorithm`
- `entities`
- `alert_ids`
- `categories`
- `confidence`
- `severity`
- `evidence`

### 3.2 Algorithm 2 — Pattern Convergence

Hybrid approach: Cypher fetches recent high-confidence decisions; Python/numpy does grouping and vector distance work. This avoids an O(n²) Cypher cross-join.

Fetch query:

```cypher
MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)
WHERE d.timestamp_epoch >= 1741046400000
  AND d.confidence > 0.70
RETURN d.decision_id AS decision_id,
       a.alert_id AS alert_id,
       d.category AS category,
       d.action AS action,
       d.confidence AS confidence,
       d.factor_vector AS factor_vector,
       d.timestamp_epoch AS timestamp_epoch
ORDER BY d.timestamp_epoch DESC
LIMIT 1000
```

Factor vector JSON parsing rule:

- `graph_schema._S()` serializes Python lists as JSON strings for AGE at `graph_schema.py:64-67`.
- Seed decisions write `factor_vector` using `_S(d["factor_vector"])` at `graph_schema.py:741-744`.
- Therefore, parse `factor_vector` in Python after AGE returns rows.

Python grouping and ranking:

1. Group rows by `action`.
2. Keep groups containing at least two categories.
3. Parse `factor_vector` into `np.ndarray` of length 6.
4. Compute pairwise L2 distances within each action group in Python.
5. Rank convergence by low factor distance, high confidence, and category diversity.
6. Return top N convergence discoveries.

### 3.3 Algorithm 3 — Temporal Velocity

Two-query design: run one recent-window query and one baseline-window query per supported entity type, then merge in Python. This avoids `CASE WHEN`.

User recent query:

```cypher
MATCH (a:Alert)-[:INVOLVES]->(u:User)
WHERE a.timestamp_epoch >= 1743033600000
RETURN u.user_id AS entity_id,
       collect(a.alert_id) AS alert_ids_json,
       count(a) AS cnt
ORDER BY cnt DESC
LIMIT 100
```

User baseline query:

```cypher
MATCH (a:Alert)-[:INVOLVES]->(u:User)
WHERE a.timestamp_epoch >= 1740441600000
  AND a.timestamp_epoch < 1743033600000
RETURN u.user_id AS entity_id,
       count(a) AS cnt
ORDER BY cnt DESC
LIMIT 100
```

Asset recent query:

```cypher
MATCH (a:Alert)-[:DETECTED_ON]->(asset:Asset)
WHERE a.timestamp_epoch >= 1743033600000
RETURN asset.asset_id AS entity_id,
       collect(a.alert_id) AS alert_ids_json,
       count(a) AS cnt
ORDER BY cnt DESC
LIMIT 100
```

Asset baseline query:

```cypher
MATCH (a:Alert)-[:DETECTED_ON]->(asset:Asset)
WHERE a.timestamp_epoch >= 1740441600000
  AND a.timestamp_epoch < 1743033600000
RETURN asset.asset_id AS entity_id,
       count(a) AS cnt
ORDER BY cnt DESC
LIMIT 100
```

Python merge:

- `min_ratio = 2.5`
- `baseline_normalized = baseline_cnt * 7 / 30`
- `ratio = recent_cnt / baseline_normalized`
- require `recent_cnt >= 2`, `baseline_cnt > 0`, and `ratio >= min_ratio`
- no `CASE WHEN` in Cypher

### 3.4 Algorithm 4 — Cross-Factor Anomaly

Python-only analysis after reusing the recent decision fetch from Algorithm 2.

Inputs:

- recent decisions from Algorithm 2
- `SOC_PROFILE_CENTROIDS` from `config.py:122-199`
- category order from `SOC_CATEGORIES` at `config.py:63-70`

Compute steps:

1. Parse each `factor_vector` into a length-6 numeric vector.
2. Compare against all centroid cells in `SOC_PROFILE_CENTROIDS` or a category representative vector derived from the tensor.
3. Identify misroutes where nearest category differs from assigned category.
4. Identify novel/far-from-all-centroids alerts where minimum distance exceeds a configured threshold.
5. Rank by distance gap and confidence.

Output discovery fields:

- `discovery_id`
- `domain`
- `source_domains`
- `algorithm`
- `entities`
- `decision_ids`
- `alert_ids`
- `categories`
- `assigned_category`
- `nearest_category`
- `distance_gap`
- `confidence`
- `severity`
- `evidence`

### 3.5 AGE Anti-Pattern Audit

| Algorithm | datetime | $param | MERGE | CASE WHEN | array property | toFloat | labels() | Status |
|---|---|---|---|---|---|---|---|---|
| Shared Entity | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| Pattern Convergence | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| Temporal Velocity | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| Cross-Factor Anomaly | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS; Python-only after fetch |

## 4. Performance Estimates

Current graph size is small: 570 Alerts, 4860 Decisions, 20 Users, 15 Assets, 4 Campaigns, 5 ThreatIndicators, and 6 AttackPatterns. Relationship density is also bounded: 4860 `DECIDED_ON`, 570 `INVOLVES`, 570 `DETECTED_ON`, 570 `CLASSIFIED_AS`, 81 `HAS_INDICATOR`, and 23 `MEMBER_OF`.

| Algorithm | Query | Rows Scanned | Result Size | Estimate | Risk | Mitigation |
|---|---|---:|---:|---|---|---|
| Shared Entity | User aggregate | ~570 Alert/User edges | <= 20 rows | < 500 ms | LOW | Apply timestamp cutoff and `LIMIT 50`. |
| Shared Entity | Asset aggregate | ~570 Alert/Asset edges | <= 15 rows | < 500 ms | LOW | Apply timestamp cutoff and `LIMIT 50`. |
| Shared Entity | Threat intel lookup | ~81 indicator edges plus entity filter | <= 20 rows | < 500 ms | LOW | Run only for qualifying entities. |
| Pattern Convergence | Recent high-confidence decisions fetch | <= 4860 Decision rows | <= 1000 rows | 500 ms to 1.5 s | MEDIUM | Time cutoff, `LIMIT 1000`, Python grouping by action. |
| Pattern Convergence | Python pairwise | <= 1000 rows grouped by action | top N | 500 ms to 2 s | MEDIUM | Cap group size per action; sample newest rows first. |
| Temporal Velocity | User recent/baseline | ~570 Alert/User edges per query | <= 20 rows | < 500 ms each | LOW | Two simple queries, no CASE. |
| Temporal Velocity | Asset recent/baseline | ~570 Alert/Asset edges per query | <= 15 rows | < 500 ms each | LOW | Two simple queries, no CASE. |
| Cross-Factor Anomaly | Reuse recent decisions fetch | no extra Cypher beyond Algorithm 2 | <= 1000 rows | 300 ms to 1 s Python | LOW-MEDIUM | Vectorize numpy distance calculation. |

Full refresh should meet the <5 second target on the current graph if Algorithm 2 fetches are capped and Algorithm 3 uses two-query aggregates. The main bottleneck is Python pairwise convergence if all 4860 decisions are compared without grouping or limits.

## 5. AlertTriageTab Integration

Current structure:

- `AlertTriageTab` owns local alert queue, selected alert, analysis, closed-loop, threat intel, decision factor, enrichment, filter, and sort state at `AlertTriageTab.tsx:284-315`.
- Alert queue loads on mount via `loadAlertQueue()` at `AlertTriageTab.tsx:317-319`.
- Threat intel also refreshes on mount at `AlertTriageTab.tsx:387-390`.
- `loadAlertQueue()` uses the frontend API helper `getAlerts()` and handles invalid or failed responses at `AlertTriageTab.tsx:402-441`.
- The main layout begins with a header at `AlertTriageTab.tsx:563-579` and then a three-column grid at `AlertTriageTab.tsx:581`.
- The Alert Queue Sidebar starts at `AlertTriageTab.tsx:582-599`; queue list rendering starts at `AlertTriageTab.tsx:625-663`.
- The component does not receive graph client props; it uses API helpers imported at `AlertTriageTab.tsx:18`.

Exact insertion point:

- Insert `DiscoveryBanner` above the alert queue and inside the Tab 3 view.
- Preferred placement: after the header block ending at `AlertTriageTab.tsx:579` and before the grid that starts at `AlertTriageTab.tsx:581`. This keeps the banner above the queue and avoids squeezing the existing sidebar.

Required state variables:

- `discoveries`
- `discoveriesLoading`
- `discoveriesError`
- `discoveriesLastRefresh`

API fetch pattern:

- Add a small `getDiscoveries(domain = "soc")` API helper in a later implementation prompt.
- Fetch `GET /api/discoveries?domain=soc`.
- Use `ensureArray()` before rendering discovery arrays, consistent with the frontend boundary rule in `CLAUDE.md:228-229`.

Refresh pattern:

- Fetch on Tab 3 mount.
- Provide a refresh button in the banner.
- Keep refresh independent from alert queue reset.
- Optional v1.0 router can expose `refresh=true` query param later, but the roadmap namespace only requires `GET /api/discoveries?domain=soc`.

Empty/error/loading states:

- Loading: compact banner skeleton or "Finding cross-graph patterns...".
- Empty: "No cross-graph discoveries in the current window."
- Error: non-blocking warning state; do not break alert triage.

App tab behavior:

- Tab 3 is `id: "triage"`, label `"Alert Triage"`, component `AlertTriageTab`, at `App.tsx:65-72`.
- App renders only the active tab component through `ActiveComponent`, `App.tsx:112`, `App.tsx:177-183`.
- Refresh-on-tab-enter implication: because inactive tabs are unmounted, `AlertTriageTab` mount effects run when the user enters Tab 3.

Proposed frontend component inventory:

- `frontend/src/components/discovery/DiscoveryBanner.tsx`
- `frontend/src/components/discovery/DiscoveryCard.tsx`
- `frontend/src/hooks/useDiscoveries.ts` or a local hook in the banner

## 6. Router Registration

Existing router pattern:

- Most routers are imported from `app.routers` at `main.py:72-73`.
- Most routers are included with `prefix="/api"` at `main.py:77-93`.
- ServiceNow is an exception with a router-local prefix and no app prefix at `main.py:74`, `main.py:94`.

Discovery router status:

- No discovery router exists in the current `backend/app/routers` listing.

Proposed files:

- `backend/app/routers/discoveries_router.py`
- `backend/app/services/cross_graph_discovery.py`

Proposed endpoint:

- `GET /api/discoveries?domain=soc`

Proposed mount:

- Import `discoveries_router` in `main.py`.
- Include with `app.include_router(discoveries_router.router, prefix="/api", tags=["Cross-Graph Discovery"])`.
- Router defines `@router.get("/discoveries")`.

Response schema:

```json
{
  "domain": "soc",
  "source_domains": ["soc"],
  "generated_at_epoch": 1741046400000,
  "cache": {
    "hit": true,
    "ttl_seconds": 60
  },
  "discoveries": [
    {
      "discovery_id": "soc-shared-entity-USR-014-1741046400000",
      "domain": "soc",
      "source_domains": ["soc"],
      "algorithm": "shared_entity",
      "entities": [{"type": "User", "id": "USR-014"}],
      "alert_ids": ["SYN-LM-D001-001", "SYN-IT-D004-001"],
      "decision_ids": [],
      "categories": ["lateral_movement", "insider_threat"],
      "confidence": 0.82,
      "severity": "medium",
      "evidence": ["User appears in 3+ alerts across 2+ categories in 30 days"]
    }
  ]
}
```

v1.0 cache behavior:

- Process-local in-memory cache keyed by `domain`.
- TTL default: 60 seconds.
- Cache value includes generated timestamp and discovery list.
- If graph query fails but a cache value exists, router may return stale data with `cache.stale = true`.

v1.1 AGE persistence plan:

- Add `Discovery` nodes with scalar properties only.
- Store list fields (`source_domains`, `alert_ids`, `decision_ids`, `categories`, `entities`, `evidence`) as JSON strings via `_S()`.
- Add relationships only after direction/schema is decided, for example `(disc:Discovery)-[:DISCOVERED_FROM]->(a:Alert)` and `(disc)-[:REFERENCES_DECISION]->(d:Decision)`.
- Avoid `MERGE`; use MATCH-then-CREATE like campaign persistence does at `campaigns.py:608-657`.

## 7. Implementation Sequence

1. Service models/data classes: define discovery result structures and response model.
2. Discovery service with in-memory cache: implement TTL cache and orchestration.
3. AGE-compatible query helpers: add query functions for shared entity, threat-intel intersection, temporal velocity, and recent decision fetch.
4. Router: add `GET /api/discoveries?domain=soc`.
5. Backend unit tests: query helper tests with fake graph client, service tests for cache and algorithm outputs.
6. DiscoveryBanner frontend: compact banner with loading/error/empty states.
7. AlertTriageTab integration: insert banner above the queue.
8. E2E tests: API contract test and Tab 3 banner smoke test.
9. v1.1 AGE persistence: add Discovery persistence schema and tests.

Effort estimates:

| Component | Estimate |
|---|---:|
| Service models and response schema | 0.25 day |
| Discovery service and cache | 0.5 day |
| AGE query helpers and Python post-processing | 0.75 day |
| Router and backend tests | 0.5 day |
| Frontend banner and AlertTriageTab integration | 0.5 day |
| E2E tests and polish | 0.5 day |
| Total v1.0 | ~3 days |
| v1.1 AGE persistence | +1 to 1.5 days |

Three days is realistic for v1.0 because the graph is small, the algorithms are read-only, and the UI entry point is a compact banner. It does not include v1.1 persistence.

## 8. Exact File Inventory

| File | New/Modified | Approx Lines | Purpose |
|---|---|---:|---|
| `backend/app/services/cross_graph_discovery.py` | New | 350-500 | Discovery models, cache, AGE query orchestration, Python algorithms. |
| `backend/app/routers/discoveries_router.py` | New | 80-140 | `GET /api/discoveries?domain=soc` router and response models. |
| `backend/app/main.py` | Modified | 2-4 | Import and include discovery router. |
| `backend/tests/test_cross_graph_discovery.py` | New | 250-400 | Service and algorithm unit tests with fake graph responses. |
| `backend/tests/test_discoveries_router.py` | New | 100-180 | FastAPI route contract/cache tests. |
| `frontend/src/components/discovery/DiscoveryBanner.tsx` | New | 180-260 | Banner above alert queue. |
| `frontend/src/components/discovery/DiscoveryCard.tsx` | New | 100-180 | Optional repeated card display inside banner. |
| `frontend/src/components/tabs/AlertTriageTab.tsx` | Modified | 10-30 | Import and render banner above queue. |
| `frontend/tests/e2e/feature_discovery.spec.ts` | New | 80-140 | API and Tab 3 banner smoke coverage. |
| `backend/FEATURE07_DESIGN.md` | New | this document | Design preview and evidence record. |

## 9. Open Risks and Required Decisions

- Missing seed patterns: none for the five required discovery proofs. TravelRecord and Device are absent, so they must not be used in v1.0.
- AGE query uncertainty: `collect(...)` behavior should be validated against AGEClient normalization. If collection values return agtype/strings inconsistently, parse at the service boundary and keep API lists as `list[...]`.
- Performance risks: Algorithm 2 pairwise comparisons can grow quickly. Keep query limits and group by action before pairwise distance.
- UI density risk in AlertTriageTab: the existing tab already has header, queue, threat intel, enrichment, campaign, graph, and situation panels. Banner should be compact and collapsible.
- v1.1 persistence schema decision: choose between only JSON fields on `Discovery` nodes or additional relationships to Alert/Decision/entity nodes.
- Multi-domain expansion readiness: v1.0 response includes `domain` and `source_domains`, but only `soc` is supported until a second domain has verified graph contract paths.
