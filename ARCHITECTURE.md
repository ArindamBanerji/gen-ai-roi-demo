# SOC Copilot — Architecture

**Last verified:** April 12, 2026
**Source:** Direct codebase investigation (grep + route dump + endpoint health check)

---

## 1. Port Configuration (✅ RESOLVED)

Backend runs on port 8001. Frontend on 5173. All port references read from root `.env`:

```
BACKEND_PORT=8001
FRONTEND_PORT=5173
```

- `vite.config.ts` proxy reads `BACKEND_PORT` from `.env` → forwards `/api` to backend
- Playwright config reads `BACKEND_PORT` from `.env` → all API tests use correct port
- No hardcoded ports remain in test files or config

**History:** Prior to April 10, the Vite proxy targeted port 8000 and Playwright tests hardcoded port 8000. This caused ~58 E2E failures. Fixed by reading all ports from `.env`.

---

## 2. Tab Structure

### Tab definitions (from App.tsx lines 47-87)

| Index | id | Label (button text) | Component | Default? |
|-------|-----|---------------------|-----------|----------|
| 0 | `soc` | SOC Analytics | SOCAnalyticsTab | No |
| 1 | `evolution` | Runtime Evolution | RuntimeEvolutionTab | **YES** (line 91) |
| 2 | `triage` | Alert Triage | AlertTriageTab | No |
| 3 | `compounding` | Compounding | CompoundingTab | No |
| 4 | `executive` | Executive Narrative | ExecutiveNarrativeTab | No |

### Tab navigation in tests

Tabs are plain `<button>` elements (App.tsx line 133), NOT `role="tab"`. They render `{tab.label}` as text (line 147).

**Correct selector pattern:**
```typescript
// Navigate to Alert Triage:
await page.getByText('Alert Triage').click();
// Navigate to Runtime Evolution:
await page.getByText('Runtime Evolution').click();
// Navigate to Compounding:
await page.getByText('Compounding').click();
// Navigate to Executive Narrative:
await page.getByText('Executive Narrative').click();
```

**Note:** `page.getByRole('tab', { name: ... })` will NOT work — these buttons have no `role="tab"` attribute. Tests using `getByRole('tab')` must be rewritten to use `getByText()` matching the label.

### Default tab is "Runtime Evolution" (Tab index 1)

Line 91: `const [activeTab, setActiveTab] = useState<TabId>('evolution')`

This means: IKS score, category dropdown, and other Tab 2 content IS visible on page load without clicking anything.

---

## 3. Alert Card DOM (AlertTriageTab.tsx)

### Card element (lines 574-598)

```tsx
<button
  key={alert.id}
  onClick={() => handleAlertSelect(alert)}
  className={`w-full px-4 py-3 text-left hover:bg-soc-bg transition-colors ${
    selectedAlert?.id === alert.id ? 'bg-soc-bg border-l-2 border-soc-primary' : ''
  }`}
>
  <span className="font-mono text-sm font-semibold">
    {alert.id}                          ← alert ID text
  </span>
  <span className={`px-2 py-0.5 rounded text-xs font-semibold border ${getSeverityColor(alert.severity)}`}>
    {alert.severity.toUpperCase()}      ← "HIGH", "MEDIUM", etc.
  </span>
  <div className="text-xs text-gray-400">
    {alert.alert_type.replace(/_/g, ' ')}
  </div>
  <div className="text-xs text-gray-500 mt-1">
    {alert.user_name} • {alert.asset_hostname}
  </div>
</button>
```

**Facts:**
- Element IS a `<button>` ✓
- Text contains `alert.id` — alert IDs include both `ALERT-78xx` (seed data) and `SIM-XX-00x` (simulation alerts)
- `getAlerts()` calls `fetchJSON('/alerts/queue')` → hits `/api/alerts/queue`
- All API data arrays are wrapped in `ensureArray()` from `src/lib/guards.ts` (WS-3, April 12)

**Test selector:** `page.locator('button').filter({ hasText: /ALERT-|SIM-/i }).first()`

---

## 4. IKS Score DOM (RuntimeEvolutionTab.tsx)

### IKS block (lines 1598-1623)

Located in section `d` ("System Health") of RuntimeEvolutionTab.

```tsx
<div className="text-3xl font-bold font-mono text-soc-secondary">
  {iksCurrentDisplay.toFixed(1)}        ← the number
</div>
<div className="text-xs text-gray-500">/ 100</div>   ← the label
```

**Test selectors:**
- `.text-3xl` with numeric content → CORRECT, matches line 1609
- `/ 100` text → CORRECT, matches line 1610
- IKS value comes from `profileStateFull?.iks?.current` (profile endpoint) OR `learningStateData?.iks_v2` (learning-state endpoint)

### IKS is in subsection 'd', not visible by default

RuntimeEvolutionTab has internal subsections: `a` (Macro), `b` (Situational), `c` (Adaptation), `d` (System Health). Default is `a` (line 327: `useState<...>('a')`).

**IKS block is only visible when subsection 'd' is active.** Tests looking for `.text-3xl` IKS on page load will fail because subsection `a` is shown, not `d`.

To reach IKS, tests must click the "System Health" subsection button first.

### Category dropdown (lines 1178-1184)

```tsx
<select
  value={categoryFilter}
  onChange={e => setCategoryFilter(e.target.value)}
  className="text-xs bg-gray-800 border border-gray-700 rounded px-2 py-1 text-gray-300"
>
```

This `<select>` is inside the Accuracy Trajectory section, which is in subsection `b` ("Situational"). Tests looking for `select` on page load will fail — subsection `a` is default.

---

## 5. Frontend URL Map

### fetchJSON base URL

`fetchJSON()` prepends `/api` to paths (based on usage pattern: `fetchJSON('/soc/profile')` → fetches `/api/soc/profile`). The Vite proxy intercepts `/api` and forwards to the backend.

### Direct fetch calls (bypass fetchJSON)

Some components use raw `fetch('/api/...')` directly. These also go through Vite proxy.

### Complete URL map

| Frontend call | Resolved URL | Backend route | Status |
|---|---|---|---|
| `fetchJSON('/alerts/queue')` | `/api/alerts/queue` | `GET /api/alerts/queue` | ✅ |
| `fetchJSON('/alert/analyze', POST)` | `/api/alert/analyze` | `POST /api/alert/analyze` | ✅ |
| `fetchJSON('/action/execute', POST)` | `/api/action/execute` | `POST /api/action/execute` | ✅ |
| `fetchJSON('/alerts/reset', POST)` | `/api/alerts/reset` | `POST /api/alerts/reset` | ✅ |
| `fetchJSON('/triage/decision-factors/${id}')` | `/api/triage/decision-factors/${id}` | `GET /api/triage/decision-factors/{alert_id}` | ✅ |
| `fetchJSON('/soc/profile')` | `/api/soc/profile` | `GET /api/soc/profile` | ✅ |
| `fetchJSON('/soc/centroid-evolution?n=N')` | `/api/soc/centroid-evolution` | `GET /api/soc/centroid-evolution` | ✅ |
| `fetchJSON('/soc/query', POST)` | `/api/soc/query` | `POST /api/soc/query` | ✅ |
| `fetchJSON('/soc/threat-landscape')` | `/api/soc/threat-landscape` | `GET /api/soc/threat-landscape` | ✅ |
| `fetchJSON('/soc/attack-tactic-breakdown')` | `/api/soc/attack-tactic-breakdown` | `GET /api/soc/attack-tactic-breakdown` | ✅ |
| `fetchJSON('/deployments')` | `/api/deployments` | `GET /api/deployments` | ✅ |
| `fetchJSON('/rl/reward-summary')` | `/api/rl/reward-summary` | `GET /api/rl/reward-summary` | ✅ |
| `fetchJSON('/alert/process', POST)` | `/api/alert/process` | `POST /api/alert/process` | ✅ |
| `fetchJSON('/alert/process-blocked', POST)` | `/api/alert/process-blocked` | `POST /api/alert/process-blocked` | ✅ |
| `fetchJSON('/eval/simulate-failure', POST)` | `/api/eval/simulate-failure` | `POST /api/eval/simulate-failure` | ✅ |
| `fetchJSON('/alert/outcome', POST)` | `/api/alert/outcome` | `POST /api/alert/outcome` | ✅ |
| `fetchJSON('/alert/outcome/status?alert_id=X')` | `/api/alert/outcome/status` | `GET /api/alert/outcome/status` | ✅ |
| `fetchJSON('/alert/policy-check?alert_id=X')` | `/api/alert/policy-check` | `GET /api/alert/policy-check` | ✅ |
| `fetchJSON('/graph/threat-intel/refresh', POST)` | `/api/graph/threat-intel/refresh` | `POST /api/graph/threat-intel/refresh` | ✅ |
| `fetchJSON('/graph/enrichment/summary')` | `/api/graph/enrichment/summary` | `GET /api/graph/enrichment/summary` | ✅ |
| `fetchJSON('/graph/enrichment/by-alert/${id}')` | `/api/graph/enrichment/by-alert/{id}` | `GET /api/graph/enrichment/by-alert/{alert_id}` | ✅ |
| `fetchJSON('/roi/defaults')` | `/api/roi/defaults` | `GET /api/roi/defaults` | ✅ |
| `fetchJSON('/roi/calculate', POST)` | `/api/roi/calculate` | `POST /api/roi/calculate` | ✅ |
| `fetchJSON('/metrics/decision-economics')` | `/api/metrics/decision-economics` | `GET /api/metrics/decision-economics` | ✅ |
| `fetchJSON('/metrics/compounding?weeks=N')` | `/api/metrics/compounding` | `GET /api/metrics/compounding` | ✅ |
| `fetchJSON('/metrics/evolution-events?limit=N')` | `/api/metrics/evolution-events` | `GET /api/metrics/evolution-events` | ✅ |
| `fetchJSON('/metrics/confidence-trajectory')` | `/api/metrics/confidence-trajectory` | `GET /api/metrics/confidence-trajectory` | ✅ |
| `fetchJSON('/evolution/weight-history')` | `/api/evolution/weight-history` | `GET /api/evolution/weight-history` | ✅ |
| `fetchJSON('/evolution/trust-scores')` | `/api/evolution/trust-scores` | `GET /api/evolution/trust-scores` | ✅ |
| `fetchJSON('/gae/weights')` | `/api/gae/weights` | `GET /api/gae/weights` | ✅ |
| `fetchJSON('/gae/history?limit=N')` | `/api/gae/history` | `GET /api/gae/history` | ✅ |
| `fetchJSON('/gae/convergence')` | `/api/gae/convergence` | `GET /api/gae/convergence` | ✅ |
| `fetchJSON('/gae/confidence-trajectory')` | `/api/gae/confidence-trajectory` | `GET /api/gae/confidence-trajectory` | ✅ |
| `fetchJSON('/gae/trust-curve')` | `/api/gae/trust-curve` | `GET /api/gae/trust-curve` | ✅ |
| `fetchJSON('/gae/before-after')` | `/api/gae/before-after` | `GET /api/gae/before-after` | ✅ |
| `fetchJSON('/gae/weight-evolution')` | `/api/gae/weight-evolution` | `GET /api/gae/weight-evolution` | ✅ |
| `fetchJSON('/demo/reset', POST)` | `/api/demo/reset` | `POST /api/demo/reset` | ✅ |
| `fetchJSON('/demo/reset-all', POST)` | `/api/demo/reset-all` | `POST /api/demo/reset-all` | ✅ |
| `fetchJSON('/demo/reseed', POST)` | `/api/demo/reseed` | `POST /api/demo/reseed` | ✅ |
| `fetchJSON('/audit/decisions?format=json')` | `/api/audit/decisions` | `GET /api/audit/decisions` | ✅ |
| `fetchJSON('/audit/verify')` | `/api/audit/verify` | `GET /api/audit/verify` | ✅ |
| `fetchJSON('/simulation/start', POST)` | `/api/simulation/start` | `POST /api/simulation/start` | ✅ |
| `fetchJSON('/simulation/progress/${id}')` | `/api/simulation/progress/{id}` | `GET /api/simulation/progress/{simulation_id}` | ✅ |
| `fetchJSON('/simulation/result/${id}')` | `/api/simulation/result/{id}` | `GET /api/simulation/result/{simulation_id}` | ✅ |
| `fetchJSON('/simulation/experiment-log/${id}')` | `/api/simulation/experiment-log/{id}` | `GET /api/simulation/experiment-log/{simulation_id}` | ✅ |
| `fetch('/api/soc/graph-stats')` | `/api/soc/graph-stats` | `GET /api/soc/graph-stats` | ✅ |
| `fetch('/api/soc/centroid-evolution?n=200')` | `/api/soc/centroid-evolution` | `GET /api/soc/centroid-evolution` | ✅ |
| `fetch('/api/soc/learning-state')` | `/api/soc/learning-state` | `GET /api/soc/learning-state` | ✅ |
| `fetch('/api/soc/centroid-heatmap')` | `/api/soc/centroid-heatmap` | `GET /api/soc/centroid-heatmap` | ✅ |
| `fetch('/api/soc/enrichment-status')` | `/api/soc/enrichment-status` | `GET /api/soc/enrichment-status` | ✅ |
| `fetch('/api/soc/centroid-support')` | `/api/soc/centroid-support` | `GET /api/soc/centroid-support` | ✅ |
| `fetch('/api/soc/operational-metrics')` | `/api/soc/operational-metrics` | `GET /api/soc/operational-metrics` | ✅ |
| `fetch('/api/soc/board-export')` | `/api/soc/board-export` | `GET /api/soc/board-export` | ✅ |
| `fetch('/api/soc/economics')` | `/api/soc/economics` | `GET /api/soc/economics` | ✅ |
| `fetch('/api/soc/detection-engineering')` | `/api/soc/detection-engineering` | `GET /api/soc/detection-engineering` | ✅ |
| `fetch('/api/soc/accuracy-trajectory')` | `/api/soc/accuracy-trajectory` | `GET /api/soc/accuracy-trajectory` | ✅ |

**Result: Zero URL mismatches.** Every frontend URL maps to a valid backend route.

---

## 6. Endpoint Health (direct to backend, port 8001)

| Status | Endpoint | Notes |
|--------|----------|-------|
| 200 | `/api/soc/learning-state` | ✅ |
| 200 | `/api/soc/profile` | ✅ |
| 200 | `/api/soc/analytics` | ✅ |
| 200 | `/api/soc/accuracy-trajectory` | ✅ |
| 200 | `/api/soc/threat-landscape` | ✅ |
| 200 | `/api/soc/campaigns` | ✅ |
| 200 | `/api/soc/attack-tactic-breakdown` | ✅ |
| 200 | `/api/soc/detection-engineering` | ✅ |
| 200 | `/api/soc/executive-narrative` | ✅ |
| 200 | `/api/soc/enrichment-advisor` | ✅ |
| 200 | `/api/soc/analyst-benchmarking` | ✅ |
| 200 | `/api/soc/benchmarking-report` | ✅ |
| 200 | `/api/soc/three-claims` | ✅ |
| 200 | `/api/soc/compliance` | ✅ |
| 200 | `/api/soc/transparency` | ✅ |
| 200 | `/api/soc/centroid-evolution` | ✅ |
| 200 | `/api/soc/graph-stats` | ✅ |
| 200 | `/api/deployments` | ✅ |
| 200 | `/api/rl/reward-summary` | ✅ |
| 200 | `/health` | ✅ (no `/api` prefix) |

All 10 Pydantic response_model endpoints return valid typed responses (WS-2, April 12).

---

## 7. Data Flow

```
AGE (PostgreSQL+AGE, WSL2:5433)
  → AGEClient._normalize_value (ci-platform — type boundary)
  → neo4j.py switcher (SOC backend — GRAPH_BACKEND=age)
  → routers (290 call sites)
  → Pydantic response_model (type boundary — 10 endpoints)
  → Vite proxy (:5173 → :8001)
  → React components + ensureArray/ensureNumber/safeKey (type boundary)
  → 5 tabs (Alert Triage, Runtime Evolution, SOC Analytics, Compounding, Executive Narrative)
```

Three type validation boundaries (WS-1/2/3, April 12):
1. **AGEClient._normalize_value** — agtype → clean Python (lists, None, numbers)
2. **Pydantic response_model** — Python dict → validated response (list fields enforced)
3. **guards.ts** — API data → safe React rendering (ensureArray, ensureNumber, safeKey)

---

## 8. Tensor Configuration

### SOC (confirmed April 12)
- Categories: 6 (credential_access, lateral_movement, data_exfiltration, malware_execution, insider_threat, cloud_infrastructure)
- Actions: 4 (escalate, investigate, suppress, monitor) — `refer_to_analyst` is routing only, NOT a scorer action
- Factors: 6 (travel_match, asset_criticality, threat_intel_enrichment, pattern_history, time_anomaly, device_trust)
- Tensor: (6, 4, 6) = 144 cells
- W-matrix: (4, 6) — matches scorer actions × factors
- Single source of truth: `SOC_SCORING_ACTIONS`, `SOC_ROUTING_ACTIONS`, `SOC_N_ACT` in `config.py`

### S2P (⚠️ BACKLOG-051)
- Actual tensor: (6, 4, 6) — matches SOC dimensions
- Spec tensor: (5, 5, 8) per MAP/math_synopsis
- Decision needed: intentional MVP simplification or bug?

---

## 9. Startup Sequence

```powershell
# Terminal 1: WSL2 AGE (leave open)
wsl -d Ubuntu-24.04 -e bash -c "sudo service postgresql start && echo 'AGE ready on 5433' && tail -f /var/log/postgresql/postgresql-17-main.log"

# Terminal 2: Backend
cd $env:CLAUDE_SOC\backend
uvicorn app.main:app --port 8001 --reload
# Wait for: [STARTUP] Backend=AGE | Client=AGEClient | Nodes=13236 | Status=VERIFIED
# correct_decisions auto-hydrates from AGE (no manual bootstrap needed)

# Terminal 3: Frontend
cd $env:CLAUDE_SOC\frontend
npm run dev

# After Playwright runs that call /api/alerts/reset:
python backend/support/setup/bootstrap_learning_loop.py --live
```

---

## 10. Conventions

### Backend
- Runs on port 8001 (from `BACKEND_PORT` in root `.env`)
- SOC endpoints under `/api/soc/`
- Triage endpoints under `/api/triage/`, `/api/alerts/`, `/api/alert/`
- GAE endpoints under `/api/gae/`
- Metrics under `/api/metrics/`
- Health at `/health` (no `/api` prefix)
- All graph queries via AGEClient (GRAPH_BACKEND=age). Neo4j removed.
- 10 priority endpoints have Pydantic `response_model` decorators

### Frontend
- `fetchJSON(path)` prepends `/api` to path, throws on non-200
- Some components use raw `fetch('/api/...')` directly (RuntimeEvolutionTab, CompoundingTab, SOCAnalyticsTab)
- Vite proxy intercepts `/api` → forwards to backend
- Default tab: Runtime Evolution (index 1, id 'evolution')
- RuntimeEvolutionTab has 4 internal subsections: a (Macro), b (Situational), c (Adaptation), d (System Health)
- IKS score is in subsection d. Category dropdown is in subsection b.
- All `.map()` calls on API data wrapped in `ensureArray()` from `src/lib/guards.ts`
- React list keys use `safeKey(id, index)` — no bare `key={item.id}`

### Tests
- `openFirstAlert()` clicks `button` with text matching `/ALERT-|SIM-/i`
- API contract tests call backend directly using `BACKEND_PORT` from `.env`
- Tab navigation uses `getByText()` matching the label (NOT `getByRole('tab')`)
- Playwright E2E: 130/131 passing (1 skipped: S2P score test)
- Backend pytest: 600/601 (1 skipped: BACKLOG-031b IKS test)
- Contract validation: `python scripts/validate_contracts.py --port 8001` → 70/70
