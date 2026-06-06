import { expect, test, type APIRequestContext } from '@playwright/test'

const S2P_API_URL = process.env.S2P_API_URL
const ALLOW_LIVE = process.env.ALLOW_LIVE_S2P_CONTRIB_WRITES === '1'
const s2pApi = S2P_API_URL || 'http://127.0.0.1:0'

function isLivePersistentTarget(url: string | undefined) {
  if (!url) return false
  try {
    const parsed = new URL(url)
    return ['localhost', '127.0.0.1'].includes(parsed.hostname) && parsed.port === '8002'
  } catch {
    return false
  }
}

function uniqueInvoiceId() {
  return `PW-CONTRIB-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

async function scoreInvoice(request: APIRequestContext, invoiceId: string) {
  const response = await request.post(`${s2pApi}/api/s2p/score`, {
    data: {
      event_id: invoiceId,
      category: 'price_variance',
      amount: 22426.73,
      supplier_id: 'SUP-PW-CONTRIB',
      match_status: 0.7,
      amount_variance_ratio: 0.5,
      duplicate_score: 0.2,
      supplier_exception_history: 0.6,
      payment_terms_impact: 0.3,
      commodity_index_correlation: 0.8,
      tax_regulatory_compliance: 0.9,
    },
  })
  expect(response.status()).toBe(200)
  return response.json()
}

test.describe('S2P factor contribution API smoke', () => {
  test.skip(!S2P_API_URL, 'contribution smoke requires explicit isolated S2P_API_URL')
  test.skip(
    isLivePersistentTarget(S2P_API_URL) && !ALLOW_LIVE,
    'contribution smoke writes a score; use isolated S2P_API_URL or set ALLOW_LIVE_S2P_CONTRIB_WRITES=1 intentionally',
  )

  test('scored invoice exposes seven numeric contribution rows', async ({ request }) => {
    const invoiceId = uniqueInvoiceId()
    await scoreInvoice(request, invoiceId)

    const response = await request.get(
      `${s2pApi}/api/s2p/explorer/contribution?invoice_id=${encodeURIComponent(invoiceId)}`,
    )
    expect(response.status()).toBe(200)
    const body = await response.json()

    expect(body.invoice_id).toBe(invoiceId)
    expect(Array.isArray(body.contributions)).toBe(true)
    expect(body.contributions).toHaveLength(7)
    for (const entry of body.contributions) {
      expect(typeof entry.factor).toBe('string')
      expect(typeof entry.value).toBe('number')
      expect(entry.value).toBeGreaterThanOrEqual(0)
      expect(entry.value).toBeLessThanOrEqual(1)
      expect(entry.distance_to_actions).toBeTruthy()
      expect(typeof entry.distance_to_actions).toBe('object')
    }
  })
})
