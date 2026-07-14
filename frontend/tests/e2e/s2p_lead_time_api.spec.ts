import { expect, test } from '@playwright/test'

const S2P_API_BASE_URL = process.env.S2P_API_BASE_URL ?? 'http://127.0.0.1:8002'

test.describe('S2P lead time intelligence API', () => {
  test.describe.configure({ timeout: 90_000 })

  test('summary returns lead-time groups', async ({ request }) => {
    const response = await request.get(`${S2P_API_BASE_URL}/api/s2p/lead-time/summary`)

    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(Array.isArray(body.stats)).toBeTruthy()
    expect(body.total_groups).toEqual(expect.any(Number))
    expect(body.total_samples).toEqual(expect.any(Number))
    expect(body.tolerance_days).toEqual(expect.any(Number))
  })

  test('alerts returns an array and accepts tolerance', async ({ request }) => {
    const response = await request.get(`${S2P_API_BASE_URL}/api/s2p/lead-time/alerts`, {
      params: { tolerance_days: '5' },
    })

    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(Array.isArray(body.alerts)).toBeTruthy()
    expect(body.total_alerts).toBe(body.alerts.length)
    expect(body.tolerance_days).toBe(5)
  })

  test('suppliers returns supplier summaries', async ({ request }) => {
    const response = await request.get(`${S2P_API_BASE_URL}/api/s2p/lead-time/suppliers`)

    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(Array.isArray(body.suppliers)).toBeTruthy()
    expect(body.total_suppliers).toBe(body.suppliers.length)
  })

  test('known supplier returns detail', async ({ request }) => {
    const suppliersResponse = await request.get(`${S2P_API_BASE_URL}/api/s2p/lead-time/suppliers`)
    expect(suppliersResponse.status()).toBe(200)
    const suppliersBody = await suppliersResponse.json()
    const knownSupplier = suppliersBody.suppliers[0]?.supplier_id ?? 'SUP-001'

    const response = await request.get(`${S2P_API_BASE_URL}/api/s2p/lead-time/suppliers/${knownSupplier}`)

    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(body.supplier_id).toBe(knownSupplier)
    expect(Array.isArray(body.stats)).toBeTruthy()
  })

  test('unknown supplier returns not found', async ({ request }) => {
    const response = await request.get(`${S2P_API_BASE_URL}/api/s2p/lead-time/suppliers/UNKNOWN_SUPPLIER`)

    expect(response.status()).toBe(404)
  })

  test('static routes are not captured as supplier ids', async ({ request }) => {
    const summary = await request.get(`${S2P_API_BASE_URL}/api/s2p/lead-time/summary`)
    const alerts = await request.get(`${S2P_API_BASE_URL}/api/s2p/lead-time/alerts`)

    expect(summary.status()).toBe(200)
    expect(alerts.status()).toBe(200)
    expect(await summary.json()).toHaveProperty('stats')
    expect(await alerts.json()).toHaveProperty('alerts')
  })
})
