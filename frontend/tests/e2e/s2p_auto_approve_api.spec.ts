import { expect, test } from '@playwright/test'

const S2P_API_BASE_URL = process.env.S2P_API_BASE_URL ?? 'http://127.0.0.1:8002'

test.describe('S2P auto-approve shadow API', () => {
  test.describe.configure({ mode: 'serial', timeout: 90_000 })

  test('status returns config and default disabled mode', async ({ request }) => {
    await request.post(`${S2P_API_BASE_URL}/api/s2p/auto-approve/disable`)
    const response = await request.get(`${S2P_API_BASE_URL}/api/s2p/auto-approve/status`)

    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(body.config).toBeTruthy()
    expect(body.enabled).toBe(false)
    expect(body.mode).toBe('disabled')
    expect(body).toHaveProperty('derived_category_readiness')
  })

  test('evaluate returns shadow advisory response without verified outcome claims', async ({ request }) => {
    await request.post(`${S2P_API_BASE_URL}/api/s2p/auto-approve/disable`)
    const response = await request.post(`${S2P_API_BASE_URL}/api/s2p/auto-approve/evaluate`, {
      data: {
        category: 'price_variance',
        confidence: 0.99,
        recommended_action: 'auto_approve',
        decision_id: 'S2P-SHADOW-E2E',
      },
    })

    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(body.shadow_only).toBe(true)
    expect(body.learning_applied).toBe(false)
    expect(body.outcome_written).toBe(false)
    expect(body.verified).toBe(false)
    expect(body.event.learning_applied).toBe(false)
    expect(body.event.outcome_written).toBe(false)
    expect(body.event.verified).toBe(false)
  })

  test('enable accepts shadow mode only', async ({ request }) => {
    const response = await request.post(`${S2P_API_BASE_URL}/api/s2p/auto-approve/enable`, {
      data: { mode: 'shadow' },
    })

    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(body.mode).toBe('shadow')
    expect(body.execution_authority).toBe(false)
  })

  test('enable rejects execution mode', async ({ request }) => {
    const response = await request.post(`${S2P_API_BASE_URL}/api/s2p/auto-approve/enable`, {
      data: { mode: 'execute_pending_verification' },
    })

    expect(response.status()).toBe(400)
  })

  test('audit returns shadow evaluation log shape', async ({ request }) => {
    const response = await request.get(`${S2P_API_BASE_URL}/api/s2p/auto-approve/audit`)

    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(Array.isArray(body.shadow_evaluation_log)).toBeTruthy()
    expect(body.durable_audit).toBe(false)
    expect(body.learning_applied).toBe(false)
    expect(body.outcome_written).toBe(false)
  })

  test('existing auto-approve stats route remains available', async ({ request }) => {
    const response = await request.get(`${S2P_API_BASE_URL}/api/s2p/auto-approve/stats`)

    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(body.source).toBe('in_memory_demo_stats')
  })

  test('existing expansion-proof route remains available without route collision', async ({ request }) => {
    const response = await request.get(`${S2P_API_BASE_URL}/api/s2p/auto-approve/expansion-proof`, {
      params: { category: 'price_variance' },
    })

    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(body).toHaveProperty('safe_to_expand')
  })
})
