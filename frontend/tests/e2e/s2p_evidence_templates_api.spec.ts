import { expect, test } from '@playwright/test'

const S2P_API_BASE_URL = process.env.S2P_API_BASE_URL ?? 'http://127.0.0.1:8002'

const categories = [
  'price_variance',
  'quantity_mismatch',
  'duplicate_risk',
  'contract_gap',
  'format_compliance',
]

test('s2p evidence template route works for price variance', async ({ request }) => {
  const response = await request.get(`${S2P_API_BASE_URL}/api/s2p/evidence/template`, {
    params: {
      category: 'price_variance',
      invoice_id: 'S2P-INV-0001',
    },
  })

  expect(response.status()).toBe(200)
  const body = await response.json()
  expect(body.category).toBe('price_variance')
  expect(body.rendered).toEqual(expect.any(String))
  expect(body.evidence.text).toBe(body.rendered)
})

test('s2p evidence templates render all canonical categories', async ({ request }) => {
  for (const category of categories) {
    const response = await request.get(`${S2P_API_BASE_URL}/api/s2p/evidence/template`, {
      params: {
        category,
        invoice_id: 'S2P-INV-0001',
      },
    })

    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(body.category).toBe(category)
    expect(body.rendered).toEqual(expect.any(String))
    expect(body.rendered.length).toBeGreaterThan(0)
  }
})

test('s2p evidence template unknown category does not return 500', async ({ request }) => {
  const response = await request.get(`${S2P_API_BASE_URL}/api/s2p/evidence/template`, {
    params: {
      category: 'unknown_category',
      invoice_id: 'S2P-INV-0001',
    },
  })

  expect([200, 400, 404]).toContain(response.status())
  expect(response.status()).not.toBe(500)
  const body = await response.json()
  expect(JSON.stringify(body)).toMatch(/unknown_category|category|review/i)
})

test('s2p evidence template missing invoice returns safe response', async ({ request }) => {
  const response = await request.get(`${S2P_API_BASE_URL}/api/s2p/evidence/template`, {
    params: {
      category: 'price_variance',
      invoice_id: 'INV-DOES-NOT-EXIST',
    },
  })

  expect(response.status()).toBe(200)
  const body = await response.json()
  expect(body.invoice_id).toBe('INV-DOES-NOT-EXIST')
  expect(body.invoice_found).toBe(false)
  expect(body.rendered).toEqual(expect.any(String))
  expect(body.situation_context.warnings.length).toBeGreaterThan(0)
})

test('s2p evidence template omitted invoice id returns safe response', async ({ request }) => {
  const response = await request.get(`${S2P_API_BASE_URL}/api/s2p/evidence/template`, {
    params: {
      category: 'price_variance',
    },
  })

  expect(response.status()).toBe(200)
  expect(response.status()).not.toBe(422)
  const body = await response.json()
  expect(body.invoice_id).toBe('unknown')
  expect(body.invoice_found).toBe(false)
  expect(body.rendered).toEqual(expect.any(String))
  expect(body.evidence.missing_fields).toContain('invoice_id')
  expect(body.situation_context.warnings.length).toBeGreaterThan(0)
})
