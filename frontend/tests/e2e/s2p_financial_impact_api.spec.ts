import { test, expect } from '@playwright/test'

const API_BASE = process.env.S2P_API_BASE_URL ?? 'http://127.0.0.1:8002'

test.describe('S2P financial impact API', () => {
  test('summary exposes P28-backed fields', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/s2p/financial-impact`)
    expect(response.ok()).toBeTruthy()

    const data = await response.json()
    expect(data).toHaveProperty('total_decisions')
    expect(data).toHaveProperty('verified_decisions')
    expect(data).toHaveProperty('total_amount')
    expect(data).toHaveProperty('total_at_risk')
    expect(data).toHaveProperty('total_recovered')
    expect(data).toHaveProperty('net_savings')
    expect(data).toHaveProperty('recovery_rate')
    expect(data).toHaveProperty('missing_receipts')
    expect(data).toHaveProperty('by_supplier')
    expect(data).toHaveProperty('by_category')
    expect(data).not.toHaveProperty('source', 'fixture')
  })

  test('trend exposes weekly points', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/s2p/financial-impact/trend`)
    expect(response.ok()).toBeTruthy()

    const data = await response.json()
    expect(data.window_weeks).toBe(12)
    expect(Array.isArray(data.points)).toBeTruthy()
    expect(data).toHaveProperty('totals')
  })

  test('valid category exposes category summary', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/s2p/financial-impact/price_variance`)
    expect(response.ok()).toBeTruthy()

    const data = await response.json()
    expect(data.category).toBe('price_variance')
    expect(data.allowed_categories).toContain('price_variance')
    expect(data).toHaveProperty('total_recovered')
  })

  test('invalid category returns allowed categories', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/s2p/financial-impact/not_a_category`)
    expect([400, 404]).toContain(response.status())

    const data = await response.json()
    const allowedCategories = data.detail?.allowed_categories ?? data.allowed_categories
    expect(allowedCategories).toContain('price_variance')
  })
})
