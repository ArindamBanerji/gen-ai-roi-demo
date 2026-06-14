import { expect, test, type APIRequestContext } from '@playwright/test'

const S2P_API_BASE_URL = process.env.S2P_API_BASE_URL ?? 'http://127.0.0.1:8002'

async function getTemplate(request: APIRequestContext, params: Record<string, string>) {
  const query = new URLSearchParams(params)
  const response = await request.get(`${S2P_API_BASE_URL}/api/s2p/evidence/template?${query}`)
  return { response, body: await response.json() }
}

test('s2p evidence template includes trust explanation', async ({ request }) => {
  const { response, body } = await getTemplate(request, { category: 'price_variance' })

  expect(response.status()).toBe(200)
  expect(body.trust_explanation).toBeTruthy()
  expect(Array.isArray(body.trust_explanation.factors)).toBe(true)
  expect(typeof body.trust_explanation.summary).toBe('string')
})

test('pre-transition trust explanation is honest', async ({ request }) => {
  const { response, body } = await getTemplate(request, { category: 'price_variance' })

  expect(response.status()).toBe(200)
  const trust = body.trust_explanation
  if (trust.trust_available === false) {
    expect(trust.learning_message).toContain('learning factor reliability')
    const serialized = JSON.stringify(trust)
    expect(serialized).not.toContain('trusted factor')
    expect(serialized).not.toContain('noisy factor')
  }
})

test('omitted invoice evidence template remains safe with trust explanation', async ({ request }) => {
  const { response, body } = await getTemplate(request, { category: 'price_variance' })

  expect(response.status()).toBe(200)
  expect(body.invoice_id).toBe('unknown')
  expect(body.invoice_found).toBe(false)
  expect(body.rendered).toBeTruthy()
  expect(body.trust_explanation).toBeTruthy()
})

test('nonexistent invoice evidence template remains safe with trust explanation', async ({ request }) => {
  const { response, body } = await getTemplate(request, {
    category: 'price_variance',
    invoice_id: 'INV-DOES-NOT-EXIST',
  })

  expect(response.status()).toBe(200)
  expect(body.invoice_id).toBe('INV-DOES-NOT-EXIST')
  expect(body.invoice_found).toBe(false)
  expect(body.rendered).toBeTruthy()
  expect(body.trust_explanation).toBeTruthy()
})

test('unknown category evidence behavior remains non-500 with trust explanation', async ({ request }) => {
  const { response, body } = await getTemplate(request, {
    category: 'unknown_category',
    invoice_id: 'S2P-INV-0001',
  })

  expect(response.status()).not.toBeGreaterThanOrEqual(500)
  expect(body.category).toBe('unknown_category')
  expect(body.rendered).toBeTruthy()
  expect(body.trust_explanation).toBeTruthy()
})
