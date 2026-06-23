import { expect, type Page, test } from '@playwright/test'
import { existsSync } from 'fs'
import { extname, join } from 'path'

const MOCK_APP_URL = 'http://r18b-s2p.local/'
const DIST_DIR = join(process.cwd(), 'dist')

const supplier = {
  supplier_id: 'SUP-001',
  supplier_name: 'Chen-Lin Electronics',
  name: 'Chen-Lin Electronics',
  category: 'electronics',
  exception_rate: 0.11,
  otif_score: 0.72,
  avg_invoice_amount: 12400,
  recent_trend: 'deteriorating',
}

const profile = {
  ...supplier,
  risk_level: 'red',
  intelligence: {
    depth: {
      headline_tier: 'emerging',
      metrics_past_threshold: 0,
      metrics_total: 4,
      label: '0 of 4 metrics past threshold',
      per_metric: {
        exception_rate: { tier: 'emerging', count: 12 },
        accuracy: { tier: 'emerging', count: 12 },
      },
      trajectory: {
        thresholds: {
          reliable: { remaining_decisions: 38, estimated_weeks: 8 },
        },
      },
    },
    risk: {
      tier: 'insufficient_data',
      basis: 'insufficient_data',
      source_count: 12,
      reason: 'verified sample below risk threshold',
      warnings: ['verified_sample_below_risk_threshold'],
    },
    caught: {
      count: 0,
      flagged_invoice_value: 0,
      currency: 'USD',
      source: 'verified_outcomes',
      label: 'No verified caught discrepancies yet',
    },
    behavioral_metrics: {
      learned: {
        exception_rate: {
          value: 0.11,
          source: 'verified_outcomes',
          provenance_tier: 'learned',
          measured: true,
          verified: true,
          source_count: 12,
          provenance_label: 'learned from verified outcomes',
        },
      },
      context: {
        otif: {
          value: 0.72,
          source: 'fixture',
          provenance_tier: 'context',
          measured: false,
          verified: false,
          provenance_label: 'connect ERP to verify',
        },
        avg_lead_time_days: {
          value: 21,
          source: 'invoice_context',
          provenance_tier: 'context',
          measured: false,
          verified: false,
          provenance_label: 'connect logistics to verify',
        },
      },
      unavailable: ['erp_verified_lead_time'],
    },
    economic_exposure: {
      amount: 148800,
      currency: 'USD',
      computation: '12 verified decisions x 11% exception exposure x $12,400 average invoice amount',
      source_breakdown: {
        decision_count: { value: 12, source: 'verified_outcomes' },
        exception_rate: { value: 0.11, source: 'verified_outcomes' },
        avg_invoice_amount: { value: 12400, source: 'fixture' },
      },
      caveat: 'Exception exposure only. This is not confirmed savings.',
    },
    new_manager_summary:
      'Chen-Lin Electronics: intelligence depth is emerging (0 of 4 metrics past threshold). Caught discrepancies: 0. Risk: insufficient_data (insufficient_data).',
    warnings: ['supplier intelligence is still emerging'],
  },
}

function intelligencePanel(page: Page) {
  return page.getByRole('region', { name: 'Supplier Intelligence Profile' })
}

function panelCard(panel: ReturnType<typeof intelligencePanel>, heading: string | RegExp) {
  return panel.locator('div').filter({ hasText: heading }).first()
}

async function openS2PPreview(page: Page) {
  await page.goto(MOCK_APP_URL)

  const previewHeading = page.getByRole('heading', { name: 'S2P Preview' })
  if (await previewHeading.isVisible().catch(() => false)) {
    return
  }

  const previewTab = page.getByRole('button', { name: /^S2P Preview$/ })
  await expect(previewTab, 'S2P Preview tab button should be visible before opening the supplier intelligence panel').toBeVisible()
  await previewTab.click()
  await expect(previewHeading, 'S2P Preview tab content should render after selecting the tab').toBeVisible()
}

async function mockS2PPreview(page: Page, supplierProfile: Record<string, unknown> | null = profile) {
  await page.route('**/*', (route) => {
    const { pathname } = new URL(route.request().url())
    if (!pathname.startsWith('/api/')) {
      const filePath = pathname === '/' ? join(DIST_DIR, 'index.html') : join(DIST_DIR, pathname)
      if (!existsSync(filePath)) {
        route.fulfill({ status: 404, contentType: 'text/plain', body: `Missing mocked frontend asset: ${pathname}` })
        return
      }
      const extension = extname(filePath)
      const contentType =
        extension === '.html' ? 'text/html' :
          extension === '.js' ? 'text/javascript' :
            extension === '.css' ? 'text/css' :
              extension === '.svg' ? 'image/svg+xml' :
                'application/octet-stream'
      route.fulfill({ status: 200, contentType, path: filePath })
      return
    }

    let body: unknown = {}
    let status = 200

    if (pathname === '/api/s2p/preview/queue') {
      body = {
        engine_version: 'test',
        exceptions: [],
        total: 0,
        auto_approve_rate: 0.31,
        confidence_avg: 0.88,
      }
    } else if (pathname === '/api/s2p/preview/conservation') {
      body = {
        engine_version: 'test',
        status: 'GREEN',
        source: 'mock',
        auto_approve_rate: 0.31,
        accuracy: 0.91,
        verified_decisions: 42,
        penalty_ratio: 5,
      }
    } else if (pathname === '/api/s2p/preview/suppliers') {
      body = {
        engine_version: 'test',
        suppliers: [supplier],
        total: 1,
      }
    } else if (pathname === '/api/s2p/suppliers/SUP-001/profile') {
      if (!supplierProfile) {
        status = 404
        body = { detail: 'not found' }
      } else {
        body = supplierProfile
      }
    }

    route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
  })
}

test.describe('S2P supplier intelligence UI', () => {
  test('renders intelligence depth and provenance split', async ({ page }) => {
    await mockS2PPreview(page)
    await openS2PPreview(page)

    const panel = intelligencePanel(page)
    const learnedCard = panelCard(panel, 'Learned / Verified Metrics')
    const contextCard = panelCard(panel, 'Context / Fixture Metrics')

    await expect(panel.getByRole('heading', { name: 'Intelligence Depth' })).toBeVisible()
    await expect(panel.getByText('0 of 4 metrics past threshold', { exact: true })).toBeVisible()
    await expect(panel.getByText('Emerging · 12 verified decisions')).toHaveCount(2)
    await expect(panel.getByText('Learned / Verified Metrics')).toBeVisible()
    await expect(learnedCard.getByText('learned', { exact: true })).toHaveCount(2)
    await expect(learnedCard.getByText('verified_outcomes · learned', { exact: true })).toBeVisible()
    await expect(panel.getByText('Context / Fixture Metrics')).toBeVisible()
    await expect(contextCard.getByText('integration pending', { exact: true })).toBeVisible()
    await expect(contextCard.getByText(/connect ERP to verify/i)).toBeVisible()
  })

  test('uses intelligence risk as canonical instead of legacy risk_level', async ({ page }) => {
    await mockS2PPreview(page)
    await openS2PPreview(page)

    const riskCard = panelCard(intelligencePanel(page), 'Risk with Basis')
    await expect(riskCard.getByText('Insufficient Data', { exact: true })).toHaveCount(2)
    await expect(riskCard.getByText(/Legacy context risk level: red/i)).toBeVisible()
    await expect(riskCard.getByText(/Supplier intelligence risk above is canonical/i)).toBeVisible()
    await expect(riskCard.getByText(/^Red$/)).toHaveCount(0)
  })

  test('renders caught and exposure caveat without savings or ROI claims', async ({ page }) => {
    await mockS2PPreview(page)
    await openS2PPreview(page)

    const panel = intelligencePanel(page)
    const caughtCard = panelCard(panel, 'What the System Caught')
    const exposureCard = panelCard(panel, 'Economic Exposure')

    await expect(caughtCard.getByText('0', { exact: true })).toBeVisible()
    await expect(caughtCard.getByText(/No verified caught discrepancies yet/i)).toBeVisible()
    await expect(exposureCard.getByText('$148,800')).toBeVisible()
    await expect(exposureCard.getByText(/not confirmed savings/i)).toBeVisible()
    await expect(panel.getByText(/ROI/i)).toHaveCount(0)
    await expect(panel.getByText(/recovered/i)).toHaveCount(0)
  })

  test('handles missing intelligence block gracefully', async ({ page }) => {
    await mockS2PPreview(page, { ...supplier, risk_level: 'red' })
    await openS2PPreview(page)

    const fallback = page.locator('div').filter({ hasText: 'Supplier intelligence is not available yet' }).first()
    await expect(fallback.getByText(/Supplier intelligence is not available yet/i)).toBeVisible()
    await expect(fallback.getByText(/integration pending/i)).toBeVisible()
  })
})
