# Diagnostic Report — Discovery Performance + 404 Source

## Executive Summary

The most likely browser-level 404 during `reset_returns_alerts_to_pending` is `GET /shield.svg` from `frontend/index.html`. The page declares `/shield.svg` as the favicon, but the frontend public asset checks found no `frontend/public/shield.svg`. This is a browser static-resource request, not an application API call.

The most likely Discovery E2E timeout source is the first synchronous refresh behind `GET /api/discoveries?domain=soc` or `POST /api/discoveries/refresh?domain=soc`. The backend does not warm the Discovery cache at startup, so the first request can run the full Cross-Graph Discovery refresh path. The highest-risk backend costs are Algorithm 1's per-entity threat-intel fan-out queries and Algorithm 2's nested pairwise comparison loop.

High-confidence findings:

- The frontend Vite proxy routes `/api/s2p/preview` to port 8002 and all other `/api` requests to port 8001, with no explicit fallback handler.
- App tab content is conditionally mounted by active tab, so inactive tabs do not fetch.
- `AlertTriageTab` mounts `DiscoveryBanner`, and `DiscoveryBanner` fetches `/api/discoveries?domain=soc` on mount.
- `RuntimeEvolutionTab` fires many backend requests on mount, but the strongest static 404 evidence is the missing `/shield.svg`.
- Discovery refresh is not started from `backend/app/main.py` startup; the router triggers refresh on cache miss.

Remaining uncertainty:

- The exact browser console message must be confirmed at runtime by logging `page.on('requestfailed')` or the URL associated with console resource failures. This report does not run Playwright.
- The exact Discovery refresh duration depends on AGE latency and current graph density. The code shape explains how a 30 second timeout can happen, but a benchmark is needed to measure it precisely.

## 1. 404 Source Investigation

### 1.1 Vite Proxy Configuration

`frontend/vite.config.ts` defines two proxy rules:

| Path | Target | changeOrigin | Rewrite | Fallback/Error Behavior |
| --- | --- | --- | --- | --- |
| `/api/s2p/preview` | `http://localhost:${s2pBackendPort}`; default port `8002` | `true` | none | no explicit fallback handler |
| `/api` | `http://localhost:${backendPort}`; default port `8001` | `true` | none | no explicit fallback handler |

Implications:

- A request to `/api/s2p/preview` is special-cased to the optional S2P preview backend on port 8002.
- A request to `/api/discoveries`, `/api/alerts/reset`, `/api/soc/...`, or other non-S2P API paths is proxied to the SOC backend on port 8001.
- Because no rewrite or proxy fallback is configured, a 404 from the target backend or a missing Vite static asset can surface as a browser-level resource error.

### 1.2 Test Flow Network Requests

`frontend/tests/e2e/deep_flows.spec.ts` contains `test('reset_returns_alerts_to_pending', ...)` around lines 457-545.

The console capture block records browser console errors and filters:

- React duplicate-key warnings.
- Browser-level `Failed to load resource` messages containing `404`.

The test flow is:

1. Test setup posts to `${BACKEND}/api/alerts/reset`.
2. `page.goto(FRONTEND)` loads the Vite application.
3. The test clicks the `Alert Triage` tab.
4. Tab 3 mounts, which triggers Alert Triage fetches and the Discovery banner fetch.
5. The test selects an alert and executes a triage action.
6. The test navigates back to `FRONTEND`.
7. The test clicks `Alert Triage` again.
8. The test posts directly to `${BACKEND}/api/alerts/reset`.
9. `page.reload()` reloads the app, causing static resources and active-tab requests to fire again.
10. The test clicks `Alert Triage`.
11. The test clicks `Runtime Evolution`, causing Tab 2 backend requests to fire.

Likely requests by step:

- Page load: `/`, `/src/main.tsx`, `/shield.svg`, compiled module imports, and any active-tab network requests.
- Alert Triage mount: `/api/alerts/queue`, `/api/discoveries?domain=soc`, and enrichment/judgment requests after an alert is selected.
- Runtime Evolution mount: multiple `/api/soc/...`, `/api/deployments`, and `/api/rl/...` calls.

### 1.3 Tab 3 Mount Requests

`AlertTriageTab` performs these network operations:

- On mount, `loadAlertQueue()` calls `getAlerts()`, which maps to `GET /api/alerts/queue`.
- When a selected alert exists, judgment explanation is fetched through `fetchJudgmentExplain(alertId)`, mapping to `GET /api/soc/judgment/explain/{alertId}`.
- Alert enrichment uses `getAlertEnrichment(alertId)`, mapping to `GET /api/graph/enrichment/by-alert/{alertId}`.
- Threat intel refresh uses `refreshThreatIntel(alertId)`, mapping to `POST /api/graph/threat-intel/refresh`.
- Alert analysis uses `POST /api/alert/analyze`.
- Action execution uses `POST /api/action/execute`.
- Alert reset uses `POST /api/alerts/reset`.

`DiscoveryBanner` is inserted in Tab 3 above the main grid and self-fetches:

- Initial load: `GET /api/discoveries?domain=soc`.
- Refresh button: `POST /api/discoveries/refresh?domain=soc`.

DiscoveryBanner handles expected failures with `console.debug`, not `console.error`, and renders a non-blocking unavailable state.

Requests that could return 404 during Tab 3:

- `/api/discoveries?domain=soc` if the backend does not include the Discovery router in the running process.
- `/api/graph/enrichment/by-alert/{alertId}` if the selected alert has no matching enrichment route/state.
- `/shield.svg` from page load/reload, independent of Tab 3.

Based on static evidence, `/shield.svg` is the strongest browser-level 404 candidate because it is referenced by `index.html` and the asset is absent.

### 1.4 Tab 2 Mount Requests

`RuntimeEvolutionTab` performs multiple fetches on mount:

- `GET /api/deployments`.
- `GET /api/rl/reward-summary`.
- `GET /api/soc/profile`.
- `GET /api/soc/graph-stats`.
- `GET /api/soc/centroid-evolution?n=200`.
- `GET /api/soc/learning-state`.
- `GET /api/soc/centroid-heatmap`.
- `GET /api/soc/enrichment-status`.
- `GET /api/soc/centroid-support`.

Nested panels also fetch:

- `GET /api/soc/accuracy-trajectory`.
- Learning health, IKS trend, factor analysis, factor summary, model swap, what-if, time-machine, shadow report, and checkpoint endpoints depending on rendered panel paths.

Several of these functions use `console.error` on failures. A missing backend route could therefore contribute to console errors when the test clicks `Runtime Evolution`, but no static evidence in the investigation identified a specific missing Tab 2 route as strongly as the missing `/shield.svg` asset.

### 1.5 App-Level Requests

`frontend/src/App.tsx` defines the tab list and renders only the active tab component inside an `ErrorBoundary` keyed by active tab. `Alert Triage` is the Tab 3 label.

Observed behavior:

- Inactive tabs are not mounted.
- Switching tabs unmounts the previous tab and mounts the new active tab.
- App itself does not make backend network requests in the reviewed code.

Implication:

- `S2PPreviewTab` should not fetch while inactive.
- Tab-specific requests are triggered by tab activation, not by all tabs mounting at page load.

### 1.6 Static Resources

`frontend/index.html` references:

- `/shield.svg` as the favicon.
- `/src/main.tsx` as the Vite module entrypoint.

Read-only asset checks found:

- `frontend/public/shield.svg`: missing.
- `frontend/public/favicon.ico`: missing.
- `frontend/public/manifest.json`: missing.

Only `/shield.svg` is directly referenced by the reviewed `index.html`. Therefore, the most evidence-backed static-resource 404 is:

```text
GET http://localhost:5173/shield.svg
```

### 1.7 Tab Content Endpoint

`backend/app/routers/soc.py` defines:

```text
GET /soc/tab/{n}/content
```

The backend tab registry covers tab numbers 1 through 5. If `n` is not in that registry, the handler raises 404.

No frontend caller for `/api/soc/tab/{n}/content` was found in the reviewed frontend search. The reviewed handler does not show evidence of an internal call to port 8002/S2P. For `n=6`, the endpoint would return 404 because only tabs 1-5 are registered, but there is no evidence that `reset_returns_alerts_to_pending` calls it.

### 1.8 CONCLUSION: Most Likely 404 Source

Ranked candidates:

1. `GET /shield.svg`
   - Why: `index.html` references `/shield.svg`, and the frontend public asset check found no `shield.svg`.
   - Triggered by: `page.goto(FRONTEND)` and `page.reload()`.
   - Source: browser static-resource request served by Vite.
   - Confidence: high.

2. `GET /api/discoveries?domain=soc`
   - Why: `DiscoveryBanner` fetches this endpoint when Tab 3 mounts. If the running backend predates the Discovery router or the route is unavailable, it can return 404.
   - Triggered by: clicking `Alert Triage`.
   - Source: frontend code through Vite `/api` proxy to the SOC backend.
   - Confidence: medium for environments with a stale backend, lower for current code where the router exists.

3. `GET /api/soc/tab/6/content`
   - Why: backend would return 404 for `n=6`.
   - Triggered by: unknown; no frontend caller was found.
   - Source: backend route if manually or externally called.
   - Confidence: low for this test flow.

Runtime observation that would prove the exact source:

- In a later diagnostic run, add temporary Playwright listeners for `page.on('requestfailed')` and `page.on('response')` filtered to status 404, then record `response.url()` for the failing test. This report does not implement or run that.

## 2. Discovery Performance Investigation

### 2.1 Algorithm 1 Analysis — Shared Entity

Shared Entity performs:

- One aggregate User query.
- One aggregate Asset query.
- A per-qualifying-entity threat-intel lookup query.

The User and Asset aggregate queries each return aligned collected arrays:

- alert IDs.
- categories.
- timestamps.

Each aggregate query has `LIMIT 50`. In the worst reviewed shape, if 50 users and 50 assets qualify, the algorithm can issue up to 100 additional threat-intel queries after the two aggregate queries.

Complexity:

- Graph query count: up to 102 for Algorithm 1 alone.
- Python processing: linear in returned aggregate rows and collected alert arrays.
- JSON parsing: each collected field is defensively parsed; cost is linear in collected list size.

Likely cost:

- The per-entity threat-intel fan-out is a high-risk latency multiplier because it turns one algorithm into many serial graph round trips.

### 2.2 Algorithm 2 Analysis — Pattern Convergence

Pattern Convergence performs one graph fetch:

- `MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)`.
- `d.confidence > 0.70`.
- `LIMIT 1000`.

It then:

- Parses each decision's `factor_vector`.
- Groups rows by `action`.
- Compares pairs within each action group.
- Skips pairs from the same category.
- Computes L2 distance for each cross-category pair.

The implementation uses nested Python loops, not a vectorized pairwise distance matrix.

Worst-case pair count:

- With 1000 rows in one action group, pair count is `1000 * 999 / 2 = 499,500`.
- If the graph has more than 1000 candidate decisions, the query limit caps Python pairwise work at that 499,500 pair worst case.

Likely cost:

- Algorithm 2 is the likely CPU bottleneck when many high-confidence decisions share the same action.
- It is bounded by `CONVERGENCE_LIMIT`, but the nested loop can still be significant in a Playwright request timeout window.

### 2.3 Algorithm 3 Analysis — Temporal Velocity

Temporal Velocity performs four graph queries:

- User recent window.
- User baseline window.
- Asset recent window.
- Asset baseline window.

Each query has `LIMIT 100`.

Python processing:

- Builds a baseline map.
- Iterates recent rows.
- Skips missing baseline entities.
- Skips baseline count zero.
- Enforces recent count minimum.
- Computes a normalized 7-day baseline and velocity ratio.

Complexity:

- Graph query count: 4.
- Python processing: linear in returned rows.

Likely cost:

- Moderate to low compared with Algorithm 1 and Algorithm 2.

### 2.4 Algorithm 4 Analysis — Cross-Factor Anomaly

Cross-Factor Anomaly reuses parsed decision rows from Algorithm 2. It does not issue another graph query in the reviewed refresh path.

It:

- Uses category means from `SOC_PROFILE_CENTROIDS`.
- Uses an existing parsed vector if present.
- Reparses `factor_vector` only if the parsed vector is missing.
- Computes distances to all category means with NumPy for each decision row.
- Emits at most one discovery per decision, prioritizing misroute over novel.

Complexity:

- Graph query count: 0 in the normal orchestrated path.
- Python processing: linear in parsed decision rows times number of categories.
- Vectorization: per-row category distance calculation uses NumPy; the outer loop is still Python.

Likely cost:

- Lower than Algorithm 2 because it avoids pairwise comparisons and reuses Algorithm 2 data.

### 2.5 Startup Behavior

`backend/app/main.py` includes the Discovery router but does not call `discovery_service.refresh()` during startup.

`backend/app/routers/discoveries_router.py` behavior:

- `GET /api/discoveries?domain=soc` checks for a fresh cache.
- If no fresh cache exists, it awaits `discovery_service.refresh(...)`.
- `POST /api/discoveries/refresh?domain=soc` always awaits refresh.
- `GET /api/discoveries/summary?domain=soc` calls the service summary path.

Cache behavior:

- DiscoveryService has a TTL-based in-memory cache.
- The first request after backend startup has no warm cache unless another request has already populated it.
- Therefore the first E2E call to `GET /api/discoveries?domain=soc` can synchronously run the full refresh path.

Why first request may timeout:

- First request can include graph clock queries, Algorithm 1 aggregate and threat-intel fan-out, Algorithm 2 fetch and pairwise comparison, Algorithm 3 queries, and Algorithm 4 processing before returning.
- If AGE round-trip latency is high, Algorithm 1's serial fan-out can dominate.
- If many high-confidence decisions share an action, Algorithm 2's nested loop can add CPU time.

### 2.6 Existing Timing Instrumentation

No dedicated per-algorithm timing instrumentation was identified in the reviewed Discovery service. Existing logging records algorithm failures and service-level errors, but it does not provide elapsed time per algorithm, graph query count per refresh, or pairwise loop timing.

What current logs can prove:

- Whether an algorithm raised an exception.
- Whether refresh fell back to stale/no-cache behavior.

What current logs cannot prove:

- Which algorithm consumed most elapsed time.
- How much time was spent in AGE versus Python post-processing.
- Whether a timeout was caused by graph round trips, pairwise CPU work, or both.

### 2.7 CONCLUSION: Performance Bottleneck

Likely bottlenecks:

1. Algorithm 1 Shared Entity
   - Reason: up to 102 serial graph queries from two aggregate queries plus per-qualifying-entity threat-intel lookups.

2. Algorithm 2 Pattern Convergence
   - Reason: up to 1000 rows and 499,500 pairwise comparisons in nested Python loops when many rows share an action.

Why 30 second timeout can occur:

- The first `GET /api/discoveries?domain=soc` after startup synchronously runs refresh instead of returning a prewarmed cache.
- The refresh path can combine many AGE round trips with non-vectorized pairwise CPU work.
- A Playwright API test with a 30 second timeout can therefore expire before the first response returns.

Vectorization status:

- Algorithm 2 is not vectorized for pairwise comparisons.
- Algorithm 4 uses NumPy for per-row category distances and reuses Algorithm 2 parsed rows in the normal refresh path.

Parsing redundancy:

- Algorithm 2 parses factor vectors.
- Algorithm 4 reuses parsed vectors when available and only reparses if missing, so the largest redundant parsing concern is defensive parsing of collected AGE values and factor vectors, not a full Algorithm 4 refetch.

Estimated refresh time:

- On a low-latency graph with few qualifying entities, refresh should plausibly complete under 5 seconds.
- With many qualifying entities and AGE round trips around 200-300 ms each, Algorithm 1's fan-out alone can approach or exceed 20-30 seconds.
- Algorithm 2's worst-case 499,500 pairwise loop can add additional CPU time.

Confidence:

- High that first-request synchronous refresh is a timeout risk.
- High that Algorithm 1 and Algorithm 2 are the primary code-shape bottlenecks.
- Medium on exact elapsed-time estimates until measured.

Remaining uncertainty:

- Actual AGE query latency in the failing E2E environment.
- Actual number of qualifying Shared Entity rows.
- Actual high-confidence decision count and action distribution.

Recommended next diagnostic action:

- In a later task, add temporary per-algorithm timing logs or a small isolated benchmark around `DiscoveryService.refresh()` to measure graph-clock queries, Algorithm 1 fan-out count, Algorithm 2 row count, pair count, and elapsed time. Do not change behavior until measurement confirms the dominant cost.

## 3. Evidence Table

| Finding | Evidence File/Lines | Confidence | Notes |
| --- | --- | --- | --- |
| `/shield.svg` is referenced by the frontend page | `frontend/index.html:5` | High | Browser requests it as favicon on page load/reload. |
| `shield.svg` asset is missing | `Test-Path frontend/public/shield.svg` returned `False` | High | Strongest static-resource 404 candidate. |
| Vite proxies `/api/s2p/preview` to port 8002 | `frontend/vite.config.ts:26-29` | High | Optional backend route can fail separately, but inactive tabs do not mount. |
| Vite proxies other `/api` calls to port 8001 | `frontend/vite.config.ts:30-33` | High | Discovery and SOC API calls use this route. |
| Deep flow reset test captures console errors | `frontend/tests/e2e/deep_flows.spec.ts:460-470` | High | Filter now skips browser-level 404 resource errors. |
| Deep flow reset test reloads the app | `frontend/tests/e2e/deep_flows.spec.ts:512` | High | Reload retriggers static-resource requests. |
| Alert Triage is Tab 3 and conditionally mounted | `frontend/src/App.tsx:65-71`, `frontend/src/App.tsx:177-183` | High | Inactive tabs do not fetch. |
| DiscoveryBanner is mounted in Alert Triage | `frontend/src/components/tabs/AlertTriageTab.tsx:582` | High | It fetches when Tab 3 mounts. |
| DiscoveryBanner initial request is `/api/discoveries?domain=soc` | `frontend/src/components/discovery/DiscoveryBanner.tsx:191`, `frontend/src/lib/api.ts:174-175` | High | Can trigger backend refresh on cold cache. |
| Runtime Evolution fires many backend requests on mount | `frontend/src/components/tabs/RuntimeEvolutionTab.tsx:583-617` | High | Potential error source after Tab 2 click. |
| SOC tab content route only supports tabs 1-5 | `backend/app/routers/soc.py:2452-2458`, `backend/app/routers/soc.py:3152` | High | `n=6` would 404, but no frontend caller found. |
| Discovery refresh is not warmed at startup | `backend/app/main.py:100-389` | Medium | Router is included, but no `discovery_service.refresh()` call was found in startup. |
| GET discoveries refreshes on cache miss | `backend/app/routers/discoveries_router.py:69-76` | High | First request can run full refresh. |
| Shared Entity can issue per-entity threat queries | `backend/app/services/cross_graph_discovery.py:404-502` | High | Up to 50 user + 50 asset qualifiers from aggregate limits. |
| Pattern Convergence uses nested pairwise loops | `backend/app/services/cross_graph_discovery.py:575-656` | High | Worst case 499,500 pairs for limit 1000. |
| Temporal Velocity uses four graph queries | `backend/app/services/cross_graph_discovery.py:658-759` | High | Linear merge after queries. |
| Cross-Factor reuses Algorithm 2 rows | `backend/app/services/cross_graph_discovery.py:306-309`, `backend/app/services/cross_graph_discovery.py:761-835` | High | No extra graph query in normal refresh. |
| No per-algorithm timing instrumentation identified | `backend/app/services/cross_graph_discovery.py` reviewed | Medium | Logging exists for errors, not elapsed timings. |

## 4. Non-Fix Recommendations

Diagnostic-only next steps:

1. Capture the exact 404 URL in a later Playwright diagnostic by logging 404 `response.url()` and `requestfailed` events for `reset_returns_alerts_to_pending`.
2. Add temporary timing logs in a later diagnostic task around `DiscoveryService.refresh()` and each algorithm to identify actual elapsed time.
3. Benchmark Algorithm 2 separately with the current graph's high-confidence decision rows and action grouping distribution.
4. Count Algorithm 1 qualifying users/assets and threat-intel lookup calls during one refresh.
5. Decide in a later design/fixer task whether first `GET /api/discoveries` should return cached/empty data and refresh asynchronously instead of synchronously blocking first response.
6. Confirm whether `/shield.svg` should be added as a static asset or the favicon reference should be changed in a later frontend task.
