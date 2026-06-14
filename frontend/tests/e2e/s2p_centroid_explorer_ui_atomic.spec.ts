import { expect, type Page, test } from '@playwright/test'

const S2P_UI_BASE_URL = process.env.S2P_UI_BASE_URL ?? 'http://127.0.0.1:5177'

const invoice = {
  invoice_id: 'P41-UI-INV-001',
  supplier_id: 'SUP-001',
  supplier_name: 'Acme Components',
  amount: 1250,
  category: 'price_variance',
  confidence: 0.91,
}

const explanation = {
  decision_id: 'P41-UI-DECISION-001',
  category: 'price_variance',
  recommended_action: 'hold_for_review',
  closest_action: 'auto_approve',
  closest_matches_recommendation: false,
  factor_names: [
    'match_status',
    'amount_variance_ratio',
    'duplicate_score',
    'supplier_exception_history',
    'payment_terms_impact',
    'commodity_index_correlation',
    'tax_regulatory_compliance',
  ],
  factor_contributions: [
    {
      factor_name: 'amount_variance_ratio',
      factor_index: 1,
      factor_value: 0.82,
      centroid_value: 0.28,
      distance: 0.54,
      dk_weight: null,
      dk_status: 'learning',
      weighted_distance: 0.077,
      direction: 'above_centroid',
    },
    {
      factor_name: 'match_status',
      factor_index: 0,
      factor_value: 0.12,
      centroid_value: 0.42,
      distance: 0.3,
      dk_weight: null,
      dk_status: 'learning',
      weighted_distance: 0.043,
      direction: 'below_centroid',
    },
  ],
  centroid_distances: {
    auto_approve: 0.91,
    hold_for_review: 1.16,
    flag_leakage: 1.34,
  },
  summary:
    'The learned centroid comparison is closest to auto_approve, while the scorer recommended hold_for_review. Treat this as explanatory context, not a replacement for the scorer decision.',
  dk_status: 'learning',
  p39_evidence: {
    exception_rate: {
      value: 0.12,
      source: 'fixture',
      provenance_tier: 'context',
      provenance_label: 'integration pending',
      measured: false,
      verified: false,
    },
  },
  read_only: true,
}

async function openTab(page: Page, name: string) {
  const byRole = page.getByRole('button', { name })
  if ((await byRole.count()) > 0) {
    await byRole.first().click()
    return
  }
  await page.getByText(name, { exact: true }).first().click()
}

async function mockBaseTriage(page: Page) {
  await page.route('**/api/s2p/preview/queue', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ exceptions: [invoice], total: 1, auto_approve_rate: 0, confidence_avg: 0.91 }),
    }),
  )
  await page.route('**/api/conservation/status', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'GREEN', passed: true }),
    }),
  )
  await page.route('**/api/s2p/evidence/template**', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ invoice_id: invoice.invoice_id, category: invoice.category, template: '', rendered: '', variables: {} }),
    }),
  )
  await page.route('**/api/s2p/score', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        event_id: invoice.invoice_id,
        category: invoice.category,
        recommended_action: explanation.recommended_action,
        action_index: 1,
        confidence: 0.93,
        decision_id: explanation.decision_id,
        factor_vector: [0.12, 0.82, 0.1, 0.25, 0.2, 0.16, 0.4],
        factor_names: explanation.factor_names,
      }),
    }),
  )
}

async function scoreMockedDecision(page: Page) {
  await page.goto(S2P_UI_BASE_URL)
  await openTab(page, 'Exception Triage')
  await page.getByRole('button', { name: 'Score' }).click()
  await expect(page.getByText(`Decision ${explanation.decision_id}`)).toBeVisible()
}

function centroidExplorer(page: Page) {
  return page.locator('article').filter({ hasText: 'Decision proximity explanation' }).first()
}

test.describe('S2P centroid explorer UI atomic contracts', () => {
  test('centroid explorer empty state is reachable from Insight', async ({ page }) => {
    await mockBaseTriage(page)
    await page.goto(S2P_UI_BASE_URL)
    await openTab(page, 'Insight')

    await expect(page.getByText('Select or score a decision to view centroid explanation.')).toBeVisible()
  })

  test('read-only explanation copy is visible and non-causal', async ({ page }) => {
    await mockBaseTriage(page)
    await page.route('**/api/s2p/centroid/explain/**', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(explanation) }),
    )
    await page.route('**/api/s2p/centroid/drift/**', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ category: 'price_variance', action: 'auto_approve', supported: false, reason: 'centroid_history_unavailable', points: [] }),
      }),
    )

    await scoreMockedDecision(page)
    const explorer = centroidExplorer(page)

    await expect(explorer.getByText(/Read-only centroid comparison/i)).toBeVisible()
    await expect(explorer.getByText('read-only', { exact: true })).toBeVisible()
    await expect(explorer.getByText(/explanatory context, not causal proof/i)).toBeVisible()
    await expect(explorer.getByText(/not a replacement for the scorer recommendation/i)).toBeVisible()
    await expect(page.getByText(/the scorer chose/i)).toHaveCount(0)
  })

  test('closest-action mismatch warning is visible', async ({ page }) => {
    await mockBaseTriage(page)
    await page.route('**/api/s2p/centroid/explain/**', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(explanation) }),
    )
    await page.route('**/api/s2p/centroid/drift/**', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ category: 'price_variance', action: 'auto_approve', supported: false, reason: 'centroid_history_unavailable', points: [] }),
      }),
    )

    await scoreMockedDecision(page)

    await expect(
      page.getByText('Centroid proximity is explanatory context and does not replace the scorer recommendation.'),
    ).toBeVisible()
  })

  test('FactorRadar renders contributions and missing DK as learning', async ({ page }) => {
    await mockBaseTriage(page)
    await page.route('**/api/s2p/centroid/explain/**', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(explanation) }),
    )
    await page.route('**/api/s2p/centroid/drift/**', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ category: 'price_variance', action: 'auto_approve', supported: false, reason: 'centroid_history_unavailable', points: [] }),
      }),
    )

    await scoreMockedDecision(page)

    await expect(page.getByText('Factor proximity')).toBeVisible()
    await expect(page.getByText(/Decision 82% · centroid 28% · distance/i)).toBeVisible()
    await expect(page.getByText('above centroid')).toBeVisible()
    await expect(page.getByText('DK learning')).toBeVisible()
    await expect(page.getByText('Trust weights unavailable; using uniform display ordering.').first()).toBeVisible()
    await expect(page.getByText(/learned trust/i)).toHaveCount(0)
  })

  test('drift unsupported state reaches unavailable final state', async ({ page }) => {
    await mockBaseTriage(page)
    await page.route('**/api/s2p/centroid/explain/**', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(explanation) }),
    )
    await page.route('**/api/s2p/centroid/drift/**', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ category: 'price_variance', action: 'auto_approve', supported: false, reason: 'centroid_history_unavailable', points: [] }),
      }),
    )

    await scoreMockedDecision(page)

    await expect(page.getByText(/Centroid history unavailable/i)).toBeVisible()
    await expect(page.getByText('Checking centroid history...')).toHaveCount(0)
  })

  test('P39 evidence is displayed as provenance context only', async ({ page }) => {
    await mockBaseTriage(page)
    await page.route('**/api/s2p/centroid/explain/**', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(explanation) }),
    )
    await page.route('**/api/s2p/centroid/drift/**', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ category: 'price_variance', action: 'auto_approve', supported: false, reason: 'centroid_history_unavailable', points: [] }),
      }),
    )

    await scoreMockedDecision(page)

    await expect(page.getByText('P39 supplier evidence')).toBeVisible()
    await expect(page.getByText(/integration pending · measured no · verified no/i)).toBeVisible()
    await expect(page.getByText('Supplier enrichment is displayed as provenance context only and is not used in centroid distances.')).toBeVisible()
    await expect(page.getByText(/learned proof/i)).toHaveCount(0)
  })
})
