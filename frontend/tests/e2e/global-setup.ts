import type { FullConfig } from '@playwright/test'

type Backend = {
  name: string
  health: string
  warmups: string[]
}

const backends: Backend[] = [
  {
    name: 'SOC',
    health: 'http://127.0.0.1:8001/health',
    warmups: [
      'http://127.0.0.1:8001/api/soc/analytics',
      // Reconstruct the in-memory audit projection before cross-tab tests
      // inspect evidence-room timestamps during the full suite.
      'http://127.0.0.1:8001/api/audit/decisions',
    ],
  },
  {
    name: 'Trading',
    health: 'http://127.0.0.1:8010/health',
    warmups: ['http://127.0.0.1:8010/api/trading/regime/detail'],
  },
  {
    name: 'S2P',
    health: 'http://127.0.0.1:8002/health',
    warmups: [
      'http://127.0.0.1:8002/api/s2p/governance/compliance-screening',
      'http://127.0.0.1:8002/api/s2p/preview/suppliers',
    ],
  },
]

async function fetchWithDeadline(url: string, timeoutMs: number, init?: RequestInit): Promise<Response> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    return await fetch(url, { ...init, signal: controller.signal })
  } finally {
    clearTimeout(timer)
  }
}

async function waitForBackend(backend: Backend): Promise<void> {
  for (let attempt = 0; attempt < 10; attempt++) {
    try {
      const health = await fetchWithDeadline(backend.health, 5000)
      if (!health.ok) throw new Error(`health ${health.status}`)
      for (const warmupUrl of backend.warmups) {
        const warmup = await fetchWithDeadline(warmupUrl, 10000)
        if (!warmup.ok) throw new Error(`${warmupUrl} returned ${warmup.status}`)
      }
      if (backend.name === 'SOC') {
        await seedAuditTrail()
      }
      return
    } catch (error) {
      if (attempt === 9) {
        throw new Error(`${backend.name} backend not ready after 30s: ${String(error)}`)
      }
      await new Promise((resolve) => setTimeout(resolve, 3000))
    }
  }
}

async function seedAuditTrail(): Promise<void> {
  const queueResponse = await fetchWithDeadline('http://127.0.0.1:8001/api/alerts/queue', 10000)
  if (!queueResponse.ok) throw new Error(`/api/alerts/queue returned ${queueResponse.status}`)
  const queue = await queueResponse.json() as {
    alerts?: Array<{ id?: string; alert_id?: string; alert_type?: string }>
  }
  const canonicalCategories = new Set([
    'credential_access', 'malware_execution', 'lateral_movement',
    'data_exfiltration', 'insider_threat', 'cloud_infrastructure',
  ])
  const seedAlert = queue.alerts?.find(alert => canonicalCategories.has(alert.alert_type ?? ''))
    ?? queue.alerts?.[0]
  const alertId = seedAlert?.id ?? seedAlert?.alert_id
  if (!alertId) throw new Error('SOC alert queue returned no seedable alert')

  const analysisResponse = await fetchWithDeadline('http://127.0.0.1:8001/api/alert/analyze', 30000, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ alert_id: alertId }),
  })
  if (!analysisResponse.ok) throw new Error(`/api/alert/analyze returned ${analysisResponse.status}`)
  const analysis = await analysisResponse.json() as {
    recommendation?: { decision_id?: string; action?: string }
    gae_scoring?: { decision_id?: string; action?: string }
  }
  const decisionId = analysis.recommendation?.decision_id ?? analysis.gae_scoring?.decision_id
  const action = analysis.recommendation?.action ?? analysis.gae_scoring?.action ?? 'investigate'
  if (!decisionId) throw new Error('SOC analyze response returned no decision_id')

  const outcomeResponse = await fetchWithDeadline('http://127.0.0.1:8001/api/alert/outcome', 30000, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      alert_id: alertId,
      decision_id: decisionId,
      outcome: 'correct',
      analyst_action: action,
    }),
  })
  if (!outcomeResponse.ok) throw new Error(`/api/alert/outcome returned ${outcomeResponse.status}`)
}

export default async function globalSetup(_config: FullConfig): Promise<void> {
  for (const backend of backends) {
    await waitForBackend(backend)
  }
}
