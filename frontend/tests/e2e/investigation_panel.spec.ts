import { expect, test, type Page, type Route } from '@playwright/test'

const FRONTEND_PORT = process.env.FRONTEND_PORT || '5173'
const FRONTEND = `http://127.0.0.1:${FRONTEND_PORT}`


const alert = {
  id: 'ALERT-VLD-1',
  alert_type: 'anomalous_login',
  severity: 'high',
  asset_hostname: 'dc-01',
  user_name: 'alice',
  timestamp: '2026-09-08T19:00:00Z',
  status: 'new',
  source_location: 'Seattle',
}

const analysis = {
  alert: { ...alert, category: 'credential_access' },
  analysis: {
    root_cause: 'Suspicious login pattern',
    severity_assessment: 'High severity',
  },
  context: {
    nodes_count: 4,
    subgraphs_traversed: ['auth', 'host'],
    patterns_matched: 2,
    key_facts: [{ source: 'iam', fact: 'Privilege change followed login' }],
  },
  recommendation: {
    action: 'investigate',
    confidence: 0.74,
    routing_zone: 'agent_zone',
    reasoning: 'Credential behavior needs analyst review.',
    decision_id: 'DEC-VLD-1',
  },
  graph_data: {
    nodes: [{ id: 'ALERT-VLD-1', label: 'Alert', type: 'Alert', properties: {} }],
    relationships: [],
  },
  situation_analysis: {
    situation_type: 'credential_access',
    situation_confidence: 0.74,
    factors_detected: ['privileged_identity_context'],
    options_evaluated: [
      { action: 'investigate', score: 0.74, factors: ['privileged_identity_context'], estimated_resolution_time: '20m', estimated_analyst_cost: 50, risk_if_wrong: 'medium' },
    ],
    selected_option: 'investigate',
    selection_reasoning: 'Auth trail needs review.',
    decision_economics: { time_saved: '20m', cost_avoided: '$50', monthly_projection: '$2k' },
    mitre_technique: 'T1078',
    mitre_tactic: 'Credential Access',
  },
  gae_scoring: {
    factor_vector: [0.8, 0.4, 0.2, 0.6, 0.7, 0.3],
    factor_names: ['privileged_identity_context', 'asset_criticality', 'threat_intel_enrichment', 'pattern_history', 'time_anomaly', 'device_trust'],
    action_probabilities: { escalate: 0.2, investigate: 0.74, suppress: 0.01, monitor: 0.05 },
    decision_method: 'centroid_l2',
  },
  narrative: 'This recommendation is calibrated from verified SOC decisions.',
}

function traceStep(step: number, pattern: string, evidenceKeys: string[], haltReason: string | null = null) {
  return {
    step,
    pattern,
    alert_category: 'credential_access',
    v_before: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
    v_after: [0.2, 0.3, 0.3, 0.5, 0.6, 0.6],
    cat_distances_before: { credential_access: 0.32, lateral_movement: 0.51, malware_execution: 0.73 },
    cat_distances_after: { credential_access: 0.28, lateral_movement: 0.41, malware_execution: 0.69 },
    evidence_keys: evidenceKeys,
    candidate_reads: ['credential_access', 'lateral_movement'],
    selected_edge: step === 0 ? 'INVOLVES' : 'CONNECTED_TO',
    propensity: 0.67,
    cost: 2.0,
    timestamp: `2026-09-08T19:0${step}:00Z`,
    policy_version: 'vld-router-v1',
    residual: step === 0 ? 0.12 : 0.03,
    halt_reason: haltReason,
  }
}

function investigationPayload(overrides: Record<string, unknown> = {}) {
  const vld = {
    action: 'escalate',
    confidence: 0.91,
    category: 'credential_access',
    investigated_category: 'credential_access',
    routing_agreed: true,
    trace: [
      traceStep(0, 'credential_access', ['auth_trail_depth', 'privilege_escalation']),
      traceStep(1, 'lateral_movement', ['connected_assets', 'campaign_threat_indicator'], 'residual_converged'),
    ],
    v_final: [0.3, 0.4, 0.3, 0.5, 0.7, 0.6],
    steps: 2,
    single_pass_action: 'investigate',
    single_pass_confidence: 0.74,
    agreement: false,
    fixture_source: null,
    conservation_emit_gate: 'not_evaluated_read_only',
    halt_reason: 'residual_converged',
    policy: 'vld',
    ...overrides,
  }
  return {
    status: 'ok',
    mode: 'vld_read_only_shadow',
    alert_id: alert.id,
    single_pass: { action: vld.single_pass_action, confidence: vld.single_pass_confidence, category: 'credential_access' },
    vld,
    investigation_trace: vld.trace,
    conservation_emit_gate: vld.conservation_emit_gate,
  }
}

async function mockTriageApis(page: Page, investigateHandler?: (route: Route) => Promise<void>) {
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url())
    const path = url.pathname
    const respond = (body: unknown, status = 200) => route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify(body),
    })

    if (path === '/api/alerts/queue') {
      return respond({ alerts: [alert] })
    }
    if (path === '/api/alert/analyze') {
      return respond(analysis)
    }
    if (path === '/api/soc/investigate') {
      if (investigateHandler) return investigateHandler(route)
      return respond(investigationPayload())
    }

    if (path === '/api/deployments') {
      return respond({ deployments: [] })
    }
    if (path === '/api/rl/reward-summary') {
      return respond({ total_decisions: 0, correct: 0, incorrect: 0, asymmetric_ratio: 20, cumulative_r_t: 0, loop3_status: 'insufficient_data', governs: [] })
    }
    if (path === '/api/soc/profile') {
      return respond({ categories: [], actions: [], centroids: [], counts: [], decision_count: 0, iks: { current: null, delta_7d: null, interpretation: 'unavailable', decision_count: 0, estimated: true, trend: [] } })
    }
    if (path === '/api/soc/graph-stats') {
      return respond({ nodes_traversed: 0, relationships_analyzed: 0, historical_decisions: 0, source: 'unavailable' })
    }
    if (path === '/api/soc/centroid-evolution') {
      return respond([])
    }
    if (path === '/api/soc/learning-state') {
      return respond({ decision_count: 10, verified_decisions: 10, iks_v2: 10 })
    }
    if (path === '/api/soc/centroid-heatmap') {
      return respond({ status: 'cold_start', factors: [], noise_fingerprint: {} })
    }
    if (path === '/api/soc/enrichment-status') {
      return respond({ sources: [], enrichment_health: 'unavailable', health_reason: 'test', total_enrichment_nodes: 0 })
    }
    if (path === '/api/soc/centroid-support') {
      return respond({ overall_health: 'unknown', warning_count: 0, interpretation: 'test' })
    }
    if (path === '/api/soc/accuracy-trajectory') {
      return respond({ categories: [] })
    }
    if (path === '/api/soc/learning/control-room') {
      return respond({ status: 'ok', controls: [], interventions: [], recommendations: [] })
    }
    if (path === '/api/soc/learning/frozen-comparison') {
      return respond({ status: 'ok', categories: [], frozen: null, current: null })
    }
    if (path === '/api/soc/authority') {
      return respond({ status: 'ok', rungs: [], categories: [], interventions: [] })
    }
    if (path === '/api/soc/interventions/history') {
      return respond({ interventions: [] })
    }
    if (path === '/api/diagnostics/day-zero') {
      return respond({ status: 'ok', checks: [] })
    }
    if (path === '/api/soc/learning-health') {
      return respond({ status: 'GREEN', conservation: { status: 'GREEN' } })
    }
    if (path === '/api/soc/iks-trend') {
      return respond({ trend: [] })
    }
    if (path === '/api/soc/shadow/report') {
      return respond({ decisions: [], summary: {} })
    }
    if (path === '/api/soc/checkpoint/list') {
      return respond({ checkpoints: [] })
    }

    if (path === '/api/graph/threat-intel/refresh') {
      return respond({ source: 'local', indicators_ingested: 1, timestamp: '2026-09-08T19:00:00Z', enrichment_summary: [] })
    }
    if (path.startsWith('/api/graph/enrichment/by-alert/')) {
      return respond({ alert_id: alert.id, has_enrichment: false, indicators: [], sources: {}, source_count: 0, consensus_severity: 'low' })
    }
    if (path === '/api/soc/explain/what-if') {
      return respond({ explanation: 'No boundary move needed', current_action: 'investigate', nearest_alternative: { action: 'escalate', distance: 0.2, factors_to_change: [] }, per_factor: [] })
    }
    if (path === '/api/alert/policy-check') {
      return respond({ has_conflict: false, conflicts: [], policies_applied: [], resolution: null })
    }
    if (path.startsWith('/api/triage/decision-factors/')) {
      return respond({ alert_id: alert.id, factors: [], recommended_action: 'investigate', confidence: 0.74, decision_method: 'centroid_l2', weights_note: 'test' })
    }
    if (path.startsWith('/api/soc/judgment/explain/')) {
      return respond({ alert_id: alert.id, category: 'credential_access', action: 'investigate', confidence: 0.74, confidence_tier: 'medium', dominant_factors: [], factor_contributions: {}, rationale: 'test', action_scores: {}, auto_approvable: false })
    }
    if (path === '/api/soc/explain/no-precedent') {
      return respond({ is_novel: false, min_distance: 0.1, threshold: 0.5, known_evidence: [], missing_evidence: [], similar_count: 3, nearest_action: 'investigate' })
    }

    return respond({ status: 'ok', items: [], alerts: [], decisions: [], events: [], categories: [], checkpoints: [] })
  })
}

async function openTriageWithAnalysis(page: Page) {
  await page.goto(FRONTEND)
  await page.getByRole('button', { name: /Alert Triage/i }).click()
  await page.getByRole('button', { name: /ALERT-VLD-1/i }).click()
  await expect(page.getByText(/Why This Decision/i)).toBeVisible({ timeout: 10000 })
}

test('InvestigationPanel renders idle state below triage scoring context', async ({ page }) => {
  await mockTriageApis(page)
  await openTriageWithAnalysis(page)
  await expect(page.getByTestId('investigation-panel')).toBeVisible()
  await expect(page.getByRole('button', { name: /Run Investigation/i })).toBeVisible()
})

test('InvestigationPanel shows loading state when API is called', async ({ page }) => {
  await mockTriageApis(page, async route => {
    await new Promise(resolve => setTimeout(resolve, 300))
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(investigationPayload()) })
  })
  await openTriageWithAnalysis(page)
  await page.getByRole('button', { name: /Run Investigation/i }).click()
  await expect(page.getByRole('button', { name: /Investigating/i })).toBeVisible()
})

test('InvestigationPanel renders a multi-step trace and VLD decision change', async ({ page }) => {
  await mockTriageApis(page)
  await openTriageWithAnalysis(page)
  await page.getByRole('button', { name: /Run Investigation/i }).click()
  await expect(page.getByText(/Step 0: Routed to credential access/i)).toBeVisible()
  await expect(page.getByText(/Step 1: Routed to lateral movement/i)).toBeVisible()
  await expect(page.getByText(/auth trail depth/i)).toBeVisible()
  await expect(page.getByText(/campaign threat indicator/i)).toBeVisible()
  await expect(page.getByText(/VLD changed the decision/i)).toBeVisible()
})

test('InvestigationPanel shows routing agreement badge', async ({ page }) => {
  await mockTriageApis(page, route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(investigationPayload({ routing_agreed: true })) }))
  await openTriageWithAnalysis(page)
  await page.getByRole('button', { name: /Run Investigation/i }).click()
  await expect(page.getByText(/Routing agreed: yes/i)).toBeVisible()
})

test('InvestigationPanel shows routing disagreement badge', async ({ page }) => {
  await mockTriageApis(page, route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(investigationPayload({ routing_agreed: false, investigated_category: 'lateral_movement' })) }))
  await openTriageWithAnalysis(page)
  await page.getByRole('button', { name: /Run Investigation/i }).click()
  await expect(page.getByText(/Routing agreed: no/i)).toBeVisible()
})

test('InvestigationPanel handles API error gracefully', async ({ page }) => {
  await mockTriageApis(page, route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'Scorer not ready' }) }))
  await openTriageWithAnalysis(page)
  await page.getByRole('button', { name: /Run Investigation/i }).click()
  await expect(page.getByRole('alert')).toContainText(/Investigation error/i)
})

test('InvestigationPanel shows agreement when single-pass matches VLD', async ({ page }) => {
  await mockTriageApis(page, route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(investigationPayload({ action: 'investigate', single_pass_action: 'investigate', agreement: true })) }))
  await openTriageWithAnalysis(page)
  await page.getByRole('button', { name: /Run Investigation/i }).click()
  await expect(page.getByText(/single-pass matched VLD/i)).toBeVisible()
})


