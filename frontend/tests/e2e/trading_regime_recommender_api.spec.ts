import { expect, test } from '@playwright/test'

const TRADING_API_BASE_URL = process.env.TRADING_API_BASE_URL ?? 'http://127.0.0.1:8010'

async function getRegimeDetail(request: import('@playwright/test').APIRequestContext, query = '') {
  let response = await request.get(`${TRADING_API_BASE_URL}/api/trading/regime/detail${query}`)
  if (response.status() === 500 || response.status() === 503) {
    await new Promise((resolve) => setTimeout(resolve, 3000))
    response = await request.get(`${TRADING_API_BASE_URL}/api/trading/regime/detail${query}`)
  }
  return response
}

test.describe('Trading regime recommender API', () => {
  test('regime detail returns P49 fields without replacing existing shape', async ({ request }) => {
    const response = await getRegimeDetail(request)

    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(body).toHaveProperty('regime')
    expect(body).toHaveProperty('recommendations')
    expect(body).toHaveProperty('regime_transitions')
    expect(body).toHaveProperty('regime_edge_summary')
    expect(body).toHaveProperty('sizing_recommendation')
    expect(body).toHaveProperty('transition_alert')
    expect(body).toHaveProperty('regime_factor_weights')
  })

  test('insufficient data state is honest when history is sparse', async ({ request }) => {
    const response = await getRegimeDetail(request)

    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(['available', 'insufficient_data', 'unavailable']).toContain(body.regime_edge_summary?.status)
    expect(body.regime_edge_summary).toHaveProperty('sample_size_current')
    expect(body.regime_edge_summary).toHaveProperty('sample_size_comparison')
  })

  test('per-regime DK unavailable state is explicit when unavailable', async ({ request }) => {
    const response = await getRegimeDetail(request)

    expect(response.status()).toBe(200)
    const body = await response.json()
    if (body.regime_factor_weights?.status !== 'available') {
      expect(['learning', 'unavailable']).toContain(body.regime_factor_weights?.status)
      expect(JSON.stringify(body.regime_factor_weights).toLowerCase()).toContain('not available')
    }
  })

  test('transition alert shape exists and can accept previous regime query', async ({ request }) => {
    const response = await getRegimeDetail(request, '?previous_regime=trending')

    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(typeof body.transition_alert?.active).toBe('boolean')
    expect(body.transition_alert).toHaveProperty('previous_regime')
    expect(body.transition_alert).toHaveProperty('current_regime')
    expect(body.transition_alert).toHaveProperty('reason')
  })

  test('response does not claim guaranteed future profit', async ({ request }) => {
    const response = await getRegimeDetail(request)

    expect(response.status()).toBe(200)
    const text = JSON.stringify(await response.json()).toLowerCase()
    expect(text).not.toContain('guaranteed profit')
    expect(text).not.toContain('guaranteed future')
  })
})
