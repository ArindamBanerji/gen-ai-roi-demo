import { expect, type Page, test } from '@playwright/test'

async function goToS2PPreview(page: Page) {
  await page.goto('/')

  const roleTab = page.getByRole('tab', { name: /S2P|Preview|Procurement/i }).first()
  if (await roleTab.isVisible().catch(() => false)) {
    await roleTab.click()
  } else {
    await page.getByRole('button', { name: /S2P Preview|S2P|Procurement/i }).first().click()
  }

  await expect(page.getByRole('heading', { name: /^S2P Preview$/i })).toBeVisible({ timeout: 15_000 })
}

async function mockS2PPreviewData(page: Page) {
  await page.route('**/api/s2p/**', async (route) => {
    const url = route.request().url()
    let body: Record<string, unknown>

    if (url.includes('/api/s2p/preview/queue')) {
      body = {
        engine_version: 'v0.7.23',
        total: 1,
        auto_approve_rate: 0.72,
        confidence_avg: 0.91,
        exceptions: [{ invoice_id: 'INV-1', supplier: 'Aster', amount: 1200, category: 'price_variance', scored_action: 'hold_for_review', confidence: 0.91 }],
      }
    } else if (url.includes('/api/s2p/preview/conservation')) {
      body = { engine_version: 'v0.7.23', source: 'illustration', status: 'GREEN', auto_approve_rate: 0.72, accuracy: 0.91, verified_decisions: 15, penalty_ratio: 5 }
    } else if (url.includes('/api/s2p/preview/suppliers')) {
      body = { total: 1, suppliers: [{ supplier_id: 'SUP-1', name: 'Aster', category: 'electronics', exception_rate: 0.12, otif_score: 0.94, avg_invoice_amount: 3000 }] }
    } else if (url.includes('/api/s2p/suppliers/SUP-1/profile')) {
      body = { supplier_id: 'SUP-1', name: 'Aster', intelligence: { behavioral_metrics: { learned: {}, context: {} } } }
    } else if (url.includes('/api/s2p/financial-impact')) {
      body = { net_savings: 25000, total_amount: 100000, by_category: { price_variance: 25000 } }
    } else if (url.includes('/api/s2p/suppliers/payment-strategy')) {
      body = { portfolio_dpo_improvement: 4.5, cash_flow_benefit: 18000, supplier_count: 4 }
    } else if (url.includes('/api/s2p/suppliers/payment-portfolio')) {
      body = { discount_capture_rate: 0.32, total_annual_benefit: 18000, supplier_count: 4 }
    } else if (url.includes('/api/s2p/simulation/scenarios')) {
      body = { total: 2, scenarios: [{ worst_case_impact: 42000, alternatives: [{ supplier_id: 'ALT-1' }] }] }
    } else if (url.includes('/api/s2p/simulation/impact-summary')) {
      body = { worst_case_impact: 42000 }
    } else if (url.includes('/api/s2p/compliance/report')) {
      body = { suppliers_screened: 12, flags_raised: 2, audit_hash: 'abcdef1234567890', uflpa_status: 'green', csddd_status: 'review', scope3_status: 'low' }
    } else if (url.includes('/api/s2p/insight/process-signals')) {
      body = { current_stage: 'learn', bottleneck_activity: 'invoice_review' }
    } else if (url.includes('/api/s2p/insight/cross-graph')) {
      body = { cycle_state: 'learn', bottleneck_activity: 'invoice_review', provenance: 'context' }
    } else if (url.includes('/api/s2p/novelty/status')) {
      body = { alert_active: false, conservation_review: false, novelty_rate: 0.04, novelty_count: 3, distance_threshold: 1.4 }
    } else if (url.includes('/api/s2p/suppliers/trends')) {
      body = { source: 'fixture', total: 1, trends: [{ supplier_id: 'SUP-1', supplier_name: 'Aster', trend: 'declining', archetype: 'late_delivery' }] }
    } else if (url.includes('/api/s2p/suppliers/early-warnings')) {
      body = { active_warnings: [{ supplier_id: 'SUP-1', supplier_name: 'Aster', warning_type: 'late_delivery', summary: 'Late delivery pattern' }] }
    } else {
      body = {}
    }

    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) })
  })
}

test('S2P Preview shows at least one provenance badge', async ({ page }) => {
  await mockS2PPreviewData(page)
  await goToS2PPreview(page)

  await expect(page.getByText(/learned|context|proven|sample/i).first()).toBeVisible({ timeout: 15_000 })
})

test('TrendCorrelation panel shows sample badge for fixture data', async ({ page }) => {
  await mockS2PPreviewData(page)
  await goToS2PPreview(page)

  const trendPanel = page.locator('section[aria-label="Trend Correlation"]').first()
  await expect(trendPanel).toBeVisible({ timeout: 15_000 })
  await expect(trendPanel.getByText(/sample/i).first()).toBeVisible()
})

test('not connected state does not render provenance badges', async ({ page }) => {
  await page.route('**/api/s2p/**', (route) => route.abort())
  await goToS2PPreview(page)

  await expect(page.getByText(/S2P service not connected/i)).toBeVisible({ timeout: 15_000 })
  await expect(page.getByText(/learned|context|proven|sample/i)).toHaveCount(0)
})
