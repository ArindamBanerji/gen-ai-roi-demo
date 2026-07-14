import { expect, test } from '@playwright/test'

const S2P_API_BASE_URL = process.env.S2P_API_BASE_URL ?? 'http://127.0.0.1:8002'

test.describe('S2P supplier enrichment API', () => {
  test.describe.configure({ timeout: 90_000 })

  test('summary is safe before enrichment', async ({ request }) => {
    const response = await request.get(`${S2P_API_BASE_URL}/api/s2p/enrichment/summary`)

    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(Array.isArray(body.suppliers)).toBeTruthy()
    expect(body.total_suppliers).toBe(body.suppliers.length)
  })

  test('dry-run returns provenance-aware report and does not require persisted state', async ({ request }) => {
    const response = await request.post(`${S2P_API_BASE_URL}/api/s2p/enrichment/run`, {
      params: { dry_run: 'true', min_decisions: '1' },
    })

    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(body.report.dry_run).toBe(true)
    expect(Array.isArray(body.receipts)).toBeTruthy()
    expect(Array.isArray(body.suppliers)).toBeTruthy()
    const supplier = body.suppliers[0]
    if (supplier) {
      const metrics = supplier.metrics
      expect(metrics).toBeTruthy()
      for (const metric of Object.values(metrics) as Array<Record<string, unknown>>) {
        expect(metric).toHaveProperty('source')
        expect(metric).toHaveProperty('provenance_tier')
        expect(metric).toHaveProperty('measured')
        expect(metric).toHaveProperty('verified')
      }
    }
  })

  test('run endpoint returns receipts and no fixture metric is labeled measured or verified', async ({ request }) => {
    const response = await request.post(`${S2P_API_BASE_URL}/api/s2p/enrichment/run`, {
      params: { dry_run: 'true' },
    })

    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(Array.isArray(body.receipts)).toBeTruthy()
    for (const supplier of body.suppliers ?? []) {
      for (const metric of Object.values(supplier.metrics ?? {}) as Array<Record<string, unknown>>) {
        if (metric.source === 'fixture') {
          expect(metric.measured).toBe(false)
          expect(metric.verified).toBe(false)
          expect(metric.provenance_tier).toBe('context')
        }
      }
    }
  })

  test('supplier endpoint is safe for unknown supplier', async ({ request }) => {
    const response = await request.get(`${S2P_API_BASE_URL}/api/s2p/enrichment/supplier/UNKNOWN_SUPPLIER`)

    expect(response.status()).toBe(404)
  })

  test('alerts endpoint is safe and only exposes verified measured alert metrics when present', async ({ request }) => {
    const response = await request.get(`${S2P_API_BASE_URL}/api/s2p/enrichment/alerts`, {
      params: { threshold: '0.1' },
    })

    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(Array.isArray(body.alerts)).toBeTruthy()
    for (const alert of body.alerts) {
      if (alert.exception_rate) {
        expect(alert.exception_rate.verified).toBe(true)
        expect(alert.exception_rate.measured).toBe(true)
      }
    }
  })

  test('persisted enrichment can be read back with provenance when run in setup', async ({ request }) => {
    const run = await request.post(`${S2P_API_BASE_URL}/api/s2p/enrichment/run`, {
      params: { dry_run: 'false', min_decisions: '1' },
    })
    expect(run.status()).toBe(200)
    const runBody = await run.json()
    const supplierId = runBody.suppliers?.[0]?.supplier_id
    test.skip(!supplierId, 'No supplier enrichment available in this backend state')

    const response = await request.get(`${S2P_API_BASE_URL}/api/s2p/enrichment/supplier/${supplierId}`)

    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(body.supplier_id).toBe(supplierId)
    expect(body.metrics).toBeTruthy()
    for (const metric of Object.values(body.metrics) as Array<Record<string, unknown>>) {
      expect(metric).toHaveProperty('source')
      expect(metric).toHaveProperty('provenance_tier')
    }
  })
})
