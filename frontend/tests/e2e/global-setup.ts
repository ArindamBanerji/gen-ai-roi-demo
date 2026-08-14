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
    warmups: ['http://127.0.0.1:8001/api/soc/analytics'],
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

async function fetchWithDeadline(url: string, timeoutMs: number): Promise<Response> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    return await fetch(url, { signal: controller.signal })
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
      return
    } catch (error) {
      if (attempt === 9) {
        throw new Error(`${backend.name} backend not ready after 30s: ${String(error)}`)
      }
      await new Promise((resolve) => setTimeout(resolve, 3000))
    }
  }
}

export default async function globalSetup(_config: FullConfig): Promise<void> {
  for (const backend of backends) {
    await waitForBackend(backend)
  }
}
