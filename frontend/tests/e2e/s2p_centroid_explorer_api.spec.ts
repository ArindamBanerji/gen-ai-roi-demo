import { expect, test } from '@playwright/test'

const S2P_API_BASE_URL = process.env.S2P_API_BASE_URL ?? 'http://127.0.0.1:8002'

test.describe('S2P centroid explorer API', () => {
  test('all centroids returns cells and S2P shape', async ({ request }) => {
    const response = await request.get(`${S2P_API_BASE_URL}/api/s2p/centroid/all`)

    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(body.shape).toEqual({ categories: 5, actions: 5, factors: 7 })
    expect(body.read_only).toBe(true)
    expect(Array.isArray(body.cells)).toBe(true)
    expect(body.cells).toHaveLength(25)
    expect(body.cells[0]).toHaveProperty('centroid_vector')
  })

  test('single centroid returns one named centroid vector', async ({ request }) => {
    const response = await request.get(`${S2P_API_BASE_URL}/api/s2p/centroid/price_variance/auto_approve`)

    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(body.category).toBe('price_variance')
    expect(body.action).toBe('auto_approve')
    expect(body.read_only).toBe(true)
    expect(body.centroid_vector).toHaveLength(7)
    expect(body.source).toBe('scorer_centroid')
  })

  test('drift returns honest supported or empty unsupported shape', async ({ request }) => {
    const response = await request.get(`${S2P_API_BASE_URL}/api/s2p/centroid/drift/price_variance/auto_approve`)

    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(typeof body.supported).toBe('boolean')
    expect(Array.isArray(body.points)).toBe(true)
    if (body.points.length === 0) {
      expect(['centroid_history_unavailable', 'no centroid checkpoint history for category/action', '']).toContain(
        body.reason,
      )
    }
  })

  test('unknown category or action returns safe error', async ({ request }) => {
    const badCategory = await request.get(`${S2P_API_BASE_URL}/api/s2p/centroid/not_a_category/auto_approve`)
    const badAction = await request.get(`${S2P_API_BASE_URL}/api/s2p/centroid/price_variance/not_an_action`)

    expect([404, 422]).toContain(badCategory.status())
    expect([404, 422]).toContain(badAction.status())
  })

  test('explain missing decision returns 404', async ({ request }) => {
    const response = await request.get(`${S2P_API_BASE_URL}/api/s2p/centroid/explain/NO-SUCH-P41-DECISION`)

    expect(response.status()).toBe(404)
  })

  test('scored decision can be explained when score endpoint is available', async ({ request }) => {
    const score = await request.post(`${S2P_API_BASE_URL}/api/s2p/score`, {
      data: {
        event_id: `P41-E2E-${Date.now()}`,
        category: 'price_variance',
        amount: 1000,
        supplier_id: 'SUP-001',
      },
    })

    test.skip(score.status() !== 200, 'score endpoint unavailable; explain success covered by backend tests')
    const decisionId = (await score.json()).decision_id
    const response = await request.get(`${S2P_API_BASE_URL}/api/s2p/centroid/explain/${decisionId}`)

    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(body.decision_id).toBe(decisionId)
    expect(body.recommended_action).toBeTruthy()
    expect(body.closest_action).toBeTruthy()
    expect(body.read_only).toBe(true)
    expect(body).toHaveProperty('centroid_distances')
    expect(Array.isArray(body.factor_contributions)).toBe(true)
    expect(body.factor_contributions).toHaveLength(7)
    expect(JSON.stringify(body).toLowerCase()).not.toContain('learning_applied')
    expect(JSON.stringify(body).toLowerCase()).not.toContain('outcome_written')
  })
})

