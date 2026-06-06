import { expect, test, type APIRequestContext } from '@playwright/test'

const S2P_API_URL = process.env.S2P_API_URL
const ALLOW_LIVE = process.env.ALLOW_LIVE_S2P_EVIDENCE_WRITES === '1'
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
  return `PW-EVID-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

async function conservationStatus(request: APIRequestContext) {
  const response = await request.get(`${s2pApi}/api/conservation/status`)
  expect(response.status()).toBe(200)
  return response.json()
}

async function waitForRecordedOutcome(
  request: APIRequestContext,
  before: { verified_count: number; total_decisions: number },
) {
  const deadline = Date.now() + 5000
  let current = await conservationStatus(request)
  while (
    Date.now() < deadline &&
    (current.verified_count !== before.verified_count + 1 ||
      current.total_decisions !== before.total_decisions + 1)
  ) {
    await new Promise((resolve) => setTimeout(resolve, 250))
    current = await conservationStatus(request)
  }
  return current
}

async function scoreInvoice(request: APIRequestContext, eventId: string) {
  const response = await request.post(`${s2pApi}/api/s2p/score`, {
    data: {
      event_id: eventId,
      category: 'price_variance',
      amount: 5000,
      supplier_id: 'SUP-PW-EVID',
      match_status: 0.92,
      amount_variance_ratio: 0.08,
      duplicate_score: 0.04,
      supplier_exception_history: 0.05,
      payment_terms_impact: 0.48,
      commodity_index_correlation: 0.76,
      tax_regulatory_compliance: 0.9,
    },
  })
  expect(response.status()).toBe(200)
  return response.json()
}

test.describe('S2P evidence receipt pre-outcome wiring', () => {
  test.skip(!S2P_API_URL, 'evidence receipt write tests require explicit isolated S2P_API_URL')
  test.skip(
    isLivePersistentTarget(S2P_API_URL) && !ALLOW_LIVE,
    'evidence receipt write tests require isolated S2P_API_URL; set ALLOW_LIVE_S2P_EVIDENCE_WRITES=1 only for intentional live writes',
  )

  test('verified outcome increments conservation once', async ({ request }) => {
    const invoiceId = uniqueInvoiceId()
    const before = await conservationStatus(request)
    const score = await scoreInvoice(request, invoiceId)

    const learn = await request.post(`${s2pApi}/api/learn`, {
      data: {
        decision_id: score.decision_id,
        actual_action: score.action,
        outcome: 'confirmed',
        context: {
          invoice_number: invoiceId,
          supplier_name: 'Playwright Evidence Supplier',
          po_number: `PO-${invoiceId}`,
        },
      },
    })
    expect(learn.status()).toBe(200)
    const learnBody = await learn.json()

    if (learnBody.status === 'paused') {
      expect(learnBody.reason).toBe('conservation_red')
      const after = await conservationStatus(request)
      expect(after.verified_count).toBe(before.verified_count)
      expect(after.total_decisions).toBe(before.total_decisions)
    } else {
      const after = await waitForRecordedOutcome(request, before)
      expect(after.verified_count).toBe(before.verified_count + 1)
      expect(after.total_decisions).toBe(before.total_decisions + 1)
    }
  })
})
