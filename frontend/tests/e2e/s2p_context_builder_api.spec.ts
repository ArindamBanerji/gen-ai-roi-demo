import { expect, test, type APIRequestContext } from '@playwright/test'

const S2P_API_BASE_URL = process.env.S2P_API_BASE_URL ?? 'http://127.0.0.1:8002'

async function getTemplate(request: APIRequestContext, params: Record<string, string>) {
  const query = new URLSearchParams(params)
  const response = await request.get(`${S2P_API_BASE_URL}/api/s2p/evidence/template?${query}`)
  return { response, body: await response.json() }
}

test('known invoice template returns sourced situation context nodes', async ({ request }) => {
  const { response, body } = await getTemplate(request, {
    category: 'contract_gap',
    invoice_id: 'S2P-INV-0001',
  })

  expect(response.status()).toBe(200)
  expect(Array.isArray(body.situation_context.nodes)).toBe(true)
  expect(body.situation_context.nodes.length).toBeGreaterThan(0)
  expect(body.situation_context.nodes.some((node: { source?: string }) => node.source === 'fixture')).toBe(true)
  for (const node of body.situation_context.nodes as Array<{ properties?: Record<string, unknown> }>) {
    expect(node.properties?.provenance_label).toBeTruthy()
    expect(node.properties?.provenance_tier).toBeTruthy()
    expect(typeof node.properties?.measured).toBe('boolean')
  }
})

test('fixture supplier context is labeled as integration pending', async ({ request }) => {
  const { response, body } = await getTemplate(request, {
    category: 'contract_gap',
    invoice_id: 'S2P-INV-0001',
  })

  expect(response.status()).toBe(200)
  const supplier = body.situation_context.nodes.find((node: { type?: string }) => node.type === 'supplier')
  expect(supplier).toBeTruthy()
  expect(supplier.source).toBe('fixture')
  expect(supplier.properties.provenance_label).toContain('integration pending')
  expect(supplier.properties.provenance_tier).toBe('context')
  expect(supplier.properties.integration_status).toBe('pending')
  expect(supplier.properties.measured).toBe(false)
})

test('known invoice includes supplier or PO context when fixture has it', async ({ request }) => {
  const { response, body } = await getTemplate(request, {
    category: 'contract_gap',
    invoice_id: 'S2P-INV-0001',
  })

  expect(response.status()).toBe(200)
  const nodeTypes = body.situation_context.nodes.map((node: { type?: string }) => node.type)
  expect(nodeTypes.some((type: string | undefined) => type !== undefined && ['supplier', 'purchase_order'].includes(type))).toBe(true)
})

test('trust explanation remains present with context builder output', async ({ request }) => {
  const { response, body } = await getTemplate(request, {
    category: 'contract_gap',
    invoice_id: 'S2P-INV-0001',
  })

  expect(response.status()).toBe(200)
  expect(body.trust_explanation).toBeTruthy()
  expect(Array.isArray(body.trust_weighted_factors)).toBe(true)
  expect(body.trust_explanation.provenance.provenance_label).toBeTruthy()
  expect(body.trust_explanation.provenance.source).toBe('context')
  expect(body.trust_explanation.dk_weight_provenance).toBeTruthy()
  for (const factor of body.trust_weighted_factors as Array<Record<string, unknown>>) {
    expect(factor.provenance_label).toBeTruthy()
    expect(factor.provenance_tier).toBeTruthy()
    expect(factor.factor_value_provenance).toBeTruthy()
    expect(factor.dk_weight_provenance).toBeTruthy()
  }
})

test('similarity criterion is visible even when live history is unavailable', async ({ request }) => {
  const { response, body } = await getTemplate(request, {
    category: 'contract_gap',
    invoice_id: 'S2P-INV-0001',
  })

  expect(response.status()).toBe(200)
  expect(body.situation_context.metadata.similarity_label).toBe('same supplier + same category')
  expect(body.situation_context.metadata.similarity_criteria.order_by).toBe('created_at DESC')
  const similar = body.situation_context.nodes.filter((node: { type?: string }) => node.type === 'similar_decision')
  for (const node of similar as Array<{ source?: string, properties?: Record<string, unknown> }>) {
    expect(node.source).toBe('graph_store')
    expect(node.properties?.similarity_label).toBe('same supplier + same category')
    expect(node.properties?.similarity_criteria).toBeTruthy()
    const verified = node.properties?.verified === true || node.properties?.outcome_verified === true
    const label = String(node.properties?.provenance_label ?? '')
    if (verified) {
      expect(node.properties?.provenance_tier).toBe('learned')
    } else {
      expect(node.properties?.provenance_tier).toBe('context')
      expect(label).not.toContain('verified decisions')
    }
  }
})

test('omitted invoice remains safe with warnings', async ({ request }) => {
  const { response, body } = await getTemplate(request, { category: 'price_variance' })

  expect(response.status()).toBe(200)
  expect(body.invoice_found).toBe(false)
  expect(Array.isArray(body.situation_context.warnings)).toBe(true)
  expect(body.situation_context.warnings.length).toBeGreaterThan(0)
})

test('nonexistent invoice remains safe', async ({ request }) => {
  const { response, body } = await getTemplate(request, {
    category: 'price_variance',
    invoice_id: 'INV-DOES-NOT-EXIST',
  })

  expect(response.status()).toBe(200)
  expect(body.invoice_found).toBe(false)
  expect(body.rendered).toBeTruthy()
})

test('unknown category remains non-500', async ({ request }) => {
  const { response, body } = await getTemplate(request, {
    category: 'unknown_category',
    invoice_id: 'S2P-INV-0001',
  })

  expect(response.status()).not.toBeGreaterThanOrEqual(500)
  expect(body.category).toBe('unknown_category')
})
