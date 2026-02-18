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

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`)
  }

  const data = await response.json()
  console.log(`[API] Response data:`, data)
  return data
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

// ============================================================================
// Tab 4: Compounding Metrics
// ============================================================================

export async function getCompoundingMetrics(weeks: number = 4) {
  return fetchJSON(`/metrics/compounding?weeks=${weeks}`)
}

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
