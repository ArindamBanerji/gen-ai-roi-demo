import { expect, test, type APIRequestContext } from '@playwright/test'

const S2P_API_URL = process.env.S2P_API_URL
const ALLOW_LIVE = process.env.ALLOW_LIVE_S2P_RECEIPT_WRITES === '1'
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
  return `PW-RCP-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

const baseScorePayload = {
  event_id: 'S2P-INV-0001',
  category: 'price_variance',
  amount: 22426.73,
  supplier_id: 'SUP-001',
  match_status: 0.698,
  amount_variance_ratio: 0.142,
  duplicate_score: 0.065,
  supplier_exception_history: 0.164,
  payment_terms_impact: 0.859,
  commodity_index_correlation: 0.194,
  tax_regulatory_compliance: 0.586,
}

async function scoreInvoice(request: APIRequestContext, eventId: string) {
  const response = await request.post(`${s2pApi}/api/s2p/score`, {
    data: { ...baseScorePayload, event_id: eventId },
  })
  expect(response.status()).toBe(200)
  return response.json()
}

async function learnDecision(
  request: APIRequestContext,
  decisionId: string,
  actualAction: string,
  invoiceId: string,
  outcome = 'confirmed',
) {
  const data: Record<string, unknown> = {
    decision_id: decisionId,
    actual_action: actualAction,
    outcome,
    context: {
      invoice_number: invoiceId,
      supplier_name: 'Playwright Receipt Supplier',
      po_number: `PO-${invoiceId}`,
    },
  }
  if (outcome === 'override') {
    data.reason_code = 'wrong_action'
  }
  const response = await request.post(`${s2pApi}/api/learn`, { data })
  expect(response.status()).toBe(200)
  return response.json()
}

async function receiptForInvoice(request: APIRequestContext, invoiceId: string) {
  const response = await request.get(`${s2pApi}/api/s2p/evidence/receipts/${invoiceId}`)
  expect(response.status()).toBe(200)
  const body = await response.json()
  expect(Array.isArray(body.receipts)).toBeTruthy()
  expect(body.receipts.length).toBeGreaterThan(0)
  return body.receipts[body.receipts.length - 1]
}

test.describe('S2P receipt audit fields', () => {
  test.skip(!S2P_API_URL, 'receipt write tests require explicit isolated S2P_API_URL')
  test.skip(isLivePersistentTarget(S2P_API_URL) && !ALLOW_LIVE, 'receipt write tests require isolated S2P_API_URL; set ALLOW_LIVE_S2P_RECEIPT_WRITES=1 only for intentional live writes')

  test('correct outcome receipt includes PD audit fields', async ({ request }) => {
    const invoiceId = uniqueInvoiceId()
    const score = await scoreInvoice(request, invoiceId)

    await learnDecision(request, score.decision_id, score.action, invoiceId)

    const receipt = await receiptForInvoice(request, invoiceId)
    expect(receipt.amount_recovered).toBeGreaterThanOrEqual(0)
    expect(typeof receipt.amount_recovered).toBe('number')
    expect(receipt.supplier_name).toBe('Playwright Receipt Supplier')
    expect(receipt.invoice_number).toBe(invoiceId)
    expect(receipt.po_number).toBe(`PO-${invoiceId}`)
  })

  test('incorrect outcome receipt has zero amount recovered', async ({ request }) => {
    const invoiceId = uniqueInvoiceId()
    const score = await scoreInvoice(request, invoiceId)
    const wrongAction = ['auto_approve', 'hold_for_review', 'escalate_to_buyer', 'flag_leakage', 'reject_invoice']
      .find((action) => action !== score.action)
    expect(wrongAction).toBeTruthy()

    await learnDecision(request, score.decision_id, wrongAction as string, invoiceId, 'override')

    const receipt = await receiptForInvoice(request, invoiceId)
    expect(receipt.is_correct).toBe(false)
    expect(receipt.amount_recovered).toBe(0)
    expect(receipt.supplier_name).toBe('Playwright Receipt Supplier')
    expect(receipt.invoice_number).toBe(invoiceId)
    expect(receipt.po_number).toBe(`PO-${invoiceId}`)
  })

  test('evidence compliance endpoint remains available', async ({ request }) => {
    const response = await request.get(`${s2pApi}/api/s2p/evidence/compliance`)

    expect(response.status()).toBeLessThan(500)
  })
})
