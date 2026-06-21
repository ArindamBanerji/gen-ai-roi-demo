/**
 * API client for SOC Copilot Demo
 * Handles all backend communication
 */

const API_BASE = '/api'

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const fullUrl = `${API_BASE}${url}`
  console.log(`[API] Fetching: ${fullUrl}`)

  const response = await fetch(fullUrl, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  console.log(`[API] Response status: ${response.status} ${response.statusText}`)

  if (response.status === 401) {
    window.location.href = '/saml/login'
    throw new Error('Unauthorized')
  }

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`)
  }

  const data = await response.json()
  console.log(`[API] Response data:`, data)
  return data
}

async function getErrorMessage(response: Response): Promise<string> {
  try {
    const data = await response.json() as { detail?: unknown }
    const detail = data?.detail
    if (typeof detail === 'string') return detail
    if (detail && typeof detail === 'object') return JSON.stringify(detail)
  } catch {
    // Fall back to status text when JSON parsing fails.
  }
  return response.statusText || `HTTP ${response.status}`
}

function triggerBrowserDownload(blob: Blob, filename: string) {
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(objectUrl)
}

function triggerDirectDownload(url: string) {
  const link = document.createElement('a')
  link.href = `${API_BASE}${url}`
  link.download = ''
  document.body.appendChild(link)
  link.click()
  link.remove()
}

// ============================================================================
// Tab 1: SOC Analytics
// ============================================================================

export async function queryMetric(question: string) {
  return fetchJSON('/soc/query', {
    method: 'POST',
    body: JSON.stringify({ question }),
  })
}

export async function getThreatLandscape() {
  return fetchJSON('/soc/threat-landscape')
}

export async function getAttackTacticBreakdown() {
  return fetchJSON('/soc/attack-tactic-breakdown')
}

// ============================================================================
// Tab 2: Runtime Evolution
// ============================================================================

export async function getDeployments() {
  return fetchJSON('/deployments')
}

export async function processAlert(alertId: string, simulateFailure: boolean = false) {
  return fetchJSON('/alert/process', {
    method: 'POST',
    body: JSON.stringify({
      alert_id: alertId,
      simulate_failure: simulateFailure,
    }),
  })
}

export async function processAlertBlocked(alertId: string) {
  return fetchJSON('/alert/process-blocked', {
    method: 'POST',
    body: JSON.stringify({
      alert_id: alertId,
    }),
  })
}

export async function simulateFailedGate() {
  return fetchJSON('/eval/simulate-failure', { method: 'POST' })
}

export async function getRewardSummary() {
  return fetchJSON('/rl/reward-summary')
}

// VIS-2: ProfileScorer state including IKS
export async function getProfileState() {
  return fetchJSON('/soc/profile')
}

// VIS-2: Centroid evolution per decision (may return 404 if endpoint not built yet)
export async function getCentroidEvolution(n: number = 200) {
  return fetchJSON(`/soc/centroid-evolution?n=${n}`)
}

export const fetchCentroidExport = () =>
  fetchJSON('/soc/centroid-export')

// ============================================================================
// Tab 3: Alert Triage
// ============================================================================

export async function getAlerts() {
  console.log('[API] Calling GET /api/alerts/queue')
  const response = await fetchJSON('/alerts/queue')
  console.log('[API] GET /api/alerts/queue response:', response)
  return response
}

export async function analyzeAlert(alertId: string) {
  return fetchJSON('/alert/analyze', {
    method: 'POST',
    body: JSON.stringify({ alert_id: alertId }),
  })
}

export async function executeAction(alertId: string) {
  return fetchJSON('/action/execute', {
    method: 'POST',
    body: JSON.stringify({ alert_id: alertId }),
  })
}

export async function resetAlerts() {
  console.log('[API] Calling POST /api/alerts/reset')
  const response = await fetchJSON('/alerts/reset', { method: 'POST' })
  console.log('[API] POST /api/alerts/reset response:', response)
  return response
}

export async function getDecisionFactors(alertId: string) {
  return fetchJSON(`/triage/decision-factors/${alertId}`)
}

export const fetchJudgmentExplain = (alertId: string) =>
  fetchJSON(`/soc/judgment/explain/${alertId}`)

export const fetchDiscoveries = (domain = 'soc') =>
  fetchJSON(`/discoveries?domain=${encodeURIComponent(domain)}`)

export const refreshDiscoveries = (domain = 'soc') =>
  fetchJSON(`/discoveries/refresh?domain=${encodeURIComponent(domain)}`, { method: 'POST' })

export const fetchDiscoverySummary = (domain = 'soc') =>
  fetchJSON(`/discoveries/summary?domain=${encodeURIComponent(domain)}`)

// ============================================================================
// Simulation (SIM-2)
// ============================================================================

export async function startSimulation(n_decisions: number, speed_ms: number) {
  return fetchJSON('/simulation/start', {
    method: 'POST',
    body: JSON.stringify({ n_decisions, speed_ms }),
  })
}

export async function getSimulationProgress(simId: string) {
  return fetchJSON(`/simulation/progress/${simId}`)
}

export async function getSimulationResult(simId: string) {
  return fetchJSON(`/simulation/result/${simId}`)
}

export async function getSimulationExperimentLog(simId: string) {
  return fetchJSON(`/simulation/experiment-log/${simId}`)
}

// ============================================================================
// Tab 4: Compounding Metrics
// ============================================================================

export async function getCompoundingMetrics(weeks: number = 4) {
  return fetchJSON(`/metrics/compounding?weeks=${weeks}`)
}

export type CohortStatusState = 'INSTRUMENT_VALIDATED' | 'ACCUMULATING' | 'MEASURED'

export interface CohortStatusResponse {
  state: CohortStatusState
  instrument: {
    validated?: boolean
    provenance?: string
    source_artifact?: string
    experiments?: Array<{
      name?: string
      injected_lift?: number
      recovered_lift?: number
      pass?: boolean
    }>
  }
  real: {
    treatment_n?: number
    control_n?: number
    threshold_k?: number
    lift?: number | null
    provenance?: string
    status?: string
  }
  structure?: {
    present?: boolean
    treatment_n?: number
    control_n?: number
    split_balanced?: boolean | null
    join_ok?: boolean | null
    provenance?: string
  }
}

export async function getCohortStatus() {
  return fetchJSON<CohortStatusResponse>('/campaign/cohort-status')
}

export async function uploadEvalCSV(file: File) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE}/eval/upload`, {
    method: 'POST',
    body: formData,
  })

  if (response.status === 401) {
    window.location.href = '/saml/login'
    throw new Error('Unauthorized')
  }

  if (!response.ok) {
    throw new Error(await getErrorMessage(response))
  }

  return response.json()
}

export async function fetchEvalTemplates() {
  return fetchJSON('/eval/templates')
}

export const fetchAutoApproveStats = () =>
  fetchJSON('/soc/auto-approve-stats')

export const fetchLearningBalanceSheet = () =>
  fetchJSON('/soc/learning-balance-sheet')

export async function getEvolutionEvents(limit: number = 10) {
  return fetchJSON(`/metrics/evolution-events?limit=${limit}`)
}

export async function resetDemoData() {
  return fetchJSON('/demo/reset', { method: 'POST' })
}

export async function resetAllDemoData() {
  console.log('[API] Calling POST /api/demo/reset-all')
  const response = await fetchJSON('/demo/reset-all', { method: 'POST' })
  console.log('[API] POST /api/demo/reset-all response:', response)
  return response
}

export async function reseedDemoData() {
  console.log('[API] Calling POST /api/demo/reseed')
  const response = await fetchJSON('/demo/reseed', { method: 'POST' })
  console.log('[API] POST /api/demo/reseed response:', response)
  return response
}

// F4c: Compounding Proof data feeds
export async function getWeightHistory(alertType?: string) {
  const query = alertType ? `?alert_type=${encodeURIComponent(alertType)}` : ''
  return fetchJSON(`/evolution/weight-history${query}`)
}

export async function getConfidenceTrajectory() {
  return fetchJSON('/metrics/confidence-trajectory')
}

// F6b: Asymmetric trust tracking
export async function getTrustScores() {
  return fetchJSON('/evolution/trust-scores')
}

// ============================================================================
// GAE Learning State (3b/3c)
// ============================================================================

export async function getGAEWeights() {
  return fetchJSON('/gae/weights')
}

export async function getGAEHistory(limit: number = 50) {
  return fetchJSON(`/gae/history?limit=${limit}`)
}

export async function getGAEConvergence() {
  return fetchJSON('/gae/convergence')
}

export async function getGAEConfidenceTrajectory() {
  return fetchJSON('/gae/confidence-trajectory')
}

export async function getGAETrustCurve() {
  return fetchJSON('/gae/trust-curve')
}

export async function getGAEBeforeAfter() {
  return fetchJSON('/gae/before-after')
}

export async function getGAEWeightEvolution() {
  return fetchJSON('/gae/weight-evolution')
}

// ============================================================================
// ROI Calculator (v2.5)
// ============================================================================

export async function getROIDefaults() {
  return fetchJSON('/roi/defaults')
}

export async function calculateROI(inputs: {
  alerts_per_day: number
  analysts: number
  avg_salary: number
  current_mttr_minutes: number
  current_auto_close_pct: number
  avg_escalation_cost: number
}) {
  return fetchJSON('/roi/calculate', {
    method: 'POST',
    body: JSON.stringify(inputs),
  })
}

// ============================================================================
// Outcome Feedback Loop (v2.5)
// ============================================================================

export async function getOutcomeStatus(alertId: string) {
  return fetchJSON(`/alert/outcome/status?alert_id=${alertId}`)
}

export async function reportOutcome(alertId: string, decisionId: string, outcome: 'correct' | 'incorrect') {
  return fetchJSON('/alert/outcome', {
    method: 'POST',
    body: JSON.stringify({
      alert_id: alertId,
      decision_id: decisionId,
      outcome,
    }),
  })
}

// ============================================================================
// Policy Conflict Resolution (v2.5)
// ============================================================================

export async function checkPolicyConflict(alertId: string) {
  return fetchJSON(`/alert/policy-check?alert_id=${alertId}`)
}

// ============================================================================
// Graph Intelligence (v3.0)
// ============================================================================

// Module-level in-flight tracker: React.StrictMode double-invokes useEffect(fn,[])
// in development. If a refresh is already in flight, callers share the same promise
// so exactly one HTTP POST is sent. Resets to null after completion so manual
// button refreshes always work.
let _threatIntelInFlight: Promise<unknown> | null = null

export async function refreshThreatIntel() {
  if (_threatIntelInFlight) return _threatIntelInFlight
  console.log('[API] Calling POST /api/graph/threat-intel/refresh')
  _threatIntelInFlight = fetchJSON('/graph/threat-intel/refresh', { method: 'POST' })
    .finally(() => { _threatIntelInFlight = null })
  const response = await _threatIntelInFlight
  console.log('[API] POST /api/graph/threat-intel/refresh response:', response)
  return response
}

export async function getEnrichmentSummary() {
  return fetchJSON('/graph/enrichment/summary')
}

export async function getAlertEnrichment(alertId: string) {
  return fetchJSON(`/graph/enrichment/by-alert/${alertId}`)
}

// ============================================================================
// Audit Trail (v3.0)
// ============================================================================

export async function getAuditDecisions() {
  return fetchJSON('/audit/decisions?format=json')
}

export async function verifyAuditChain() {
  return fetchJSON('/audit/verify')
}

export async function getAccuracyTrajectory() {
  return fetchJSON('/soc/accuracy-trajectory')
}

// ============================================================================
// WIRE-03: Learning Health / Conservation Law (Tab 2 System Health)
// ============================================================================

export async function fetchLearningHealth() {
  return fetchJSON('/soc/learning-health')
}

// ============================================================================
// WIRE-04: IKS Trend / Trajectory (Tab 2 System Health)
// ============================================================================

export async function fetchIksTrend() {
  return fetchJSON('/soc/iks-trend')
}

export async function fetchFactorAnalysis() {
  return fetchJSON('/soc/factor-analysis')
}

export async function fetchFactorAnalysisSummary() {
  return fetchJSON('/soc/factor-analysis/summary')
}

export const fetchModelSwapTrial = (n?: number) =>
  fetchJSON(`/soc/model-swap-trial${n ? `?n_alerts=${n}` : ''}`)

// ============================================================================
// FEATURE-03: What-If Simulator
// ============================================================================

export async function runWhatIfProjection(scenario: Record<string, unknown>) {
  return fetchJSON('/whatif/project', {
    method: 'POST',
    body: JSON.stringify(scenario),
  })
}

export async function fetchWhatIfPresets() {
  return fetchJSON('/whatif/presets')
}

// ============================================================================
// FEATURE-04: Centroid Time Machine
// ============================================================================

export async function fetchTimeMachineSnapshots() {
  return fetchJSON('/time-machine/snapshots')
}

export async function fetchTimeMachineSnapshot(id: string) {
  return fetchJSON(`/time-machine/snapshots/${id}`)
}

export async function fetchTimeMachineCompare(idA: string, idB: string) {
  return fetchJSON(`/time-machine/compare?a=${idA}&b=${idB}`)
}

export async function fetchTimeMachineCompareBootstrap(snapshotId: string) {
  return fetchJSON(`/time-machine/compare-bootstrap?snapshot_id=${snapshotId}`)
}

export async function fetchTimeMachineTimeline() {
  return fetchJSON('/time-machine/timeline')
}

// ============================================================================
// WIRE-01: Governance & Compliance (Tab 5)
// ============================================================================

export async function fetchCompliance() {
  return fetchJSON('/soc/compliance')
}

export async function fetchTransparency() {
  return fetchJSON('/soc/transparency')
}

export async function fetchGovernanceReport() {
  return fetchJSON('/governance/report')
}

export async function fetchGovernanceSummary() {
  return fetchJSON('/governance/summary')
}

export async function downloadGovernanceReportJson() {
  const report = await fetchGovernanceReport()
  const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
  triggerBrowserDownload(blob, 'governance_report.json')
  return report
}

export function downloadGovernanceReportCsv() {
  triggerDirectDownload('/governance/report/csv')
}

// ============================================================================
// WIRE-02: Analyst Benchmarking (Tab 1)
// ============================================================================

export async function fetchAnalystBenchmarking() {
  return fetchJSON('/soc/analyst-benchmarking')
}

export async function fetchF9Report() {
  return fetchJSON('/soc/f9-report')
}

// ============================================================================
// WIRE-05: Shadow Mode
// ============================================================================

export const toggleShadowMode = (enabled: boolean) =>
  fetchJSON('/soc/shadow/toggle', { method: 'POST', body: JSON.stringify({ enabled }) })

export const recordShadowAction = (body: Record<string, unknown>) =>
  fetchJSON('/soc/shadow/analyst-action', {
    method: 'POST',
    body: JSON.stringify(body),
  })

export const fetchShadowReport = () =>
  fetchJSON('/soc/shadow/report')

// ============================================================================
// WIRE-06: Checkpoint Controls
// ============================================================================

export const createCheckpoint = (reason = 'manual') =>
  fetchJSON('/soc/checkpoint/create', { method: 'POST', body: JSON.stringify({ reason }) })

export const fetchCheckpoints = () =>
  fetchJSON('/soc/checkpoint/list')

export const rollbackCheckpoint = (checkpointId: string) =>
  fetchJSON('/soc/checkpoint/rollback', {
    method: 'POST',
    body: JSON.stringify({ checkpoint_id: checkpointId }),
  })

// ============================================================================
// WIRE-08: Graph Explorer
// ============================================================================

export const fetchGraphSummary = () =>
  fetchJSON('/soc/graph/summary')

export const fetchTopNodes = () =>
  fetchJSON('/soc/graph/top-nodes')

export const fetchNodeNeighbors = (nodeId: string) =>
  fetchJSON(`/soc/graph/node/${nodeId}/neighbors`)

export const fetchPrebuiltQueries = () =>
  fetchJSON('/soc/graph/prebuilt-queries')

export const runPrebuiltQuery = (queryName: string) =>
  fetchJSON(`/soc/graph/prebuilt/${queryName}`, { method: 'POST' })

export const runGraphQuery = (cypher: string) =>
  fetchJSON('/soc/graph/query', {
    method: 'POST',
    body: JSON.stringify({ cypher }),
  })
