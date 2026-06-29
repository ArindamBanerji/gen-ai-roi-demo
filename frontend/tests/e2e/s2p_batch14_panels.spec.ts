import { expect, type Page, test } from '@playwright/test'

const BACKEND = 'http://127.0.0.1:8002'

async function goToS2PPreview(page: Page) {
  await page.goto('/')

  const roleTab = page.getByRole('tab', { name: /S2P|Preview|Procurement/i }).first()
  if (await roleTab.isVisible().catch(() => false)) {
    await roleTab.click()
  } else {
    await page.getByRole('button', { name: /S2P Preview|S2P|Procurement/i }).first().click()
  }

  await expect(page.getByRole('heading', { name: /^S2P Preview$/i })).toBeVisible({ timeout: 15_000 })
  await expect(page.getByText(/Exception Queue/i).first()).toBeVisible({ timeout: 15_000 })
}

function panel(page: Page, name: RegExp) {
  return page.locator('section').filter({ hasText: name }).first()
}

test.describe('S2P Batch 14 panels', () => {
  test.beforeEach(async ({ request }) => {
    const response = await request.get(`${BACKEND}/api/s2p/novelty/status`)
    test.skip(!response.ok(), 'S2P backend unavailable')
  })

  test('test_disruption_panel_visible', async ({ page }) => {
    await goToS2PPreview(page)
    const target = panel(page, /Disruption simulation/i)
    await expect(target).toBeVisible({ timeout: 15_000 })
    await expect(target.getByText(/Active scenarios|Loading disruption|S2P backend unavailable/i).first()).toBeVisible()
    await expect(target.getByText(/\d+/).first()).toBeVisible()
  })

  test('test_financial_impact_panel_visible', async ({ page }) => {
    await goToS2PPreview(page)
    const target = panel(page, /Financial impact/i)
    await expect(target).toBeVisible({ timeout: 15_000 })
    await expect(target.getByText(/Net savings|Loading financial|S2P backend unavailable/i).first()).toBeVisible()
  })

  test('test_working_capital_panel_visible', async ({ page }) => {
    await goToS2PPreview(page)
    const target = panel(page, /Working capital/i)
    await expect(target).toBeVisible({ timeout: 15_000 })
    await expect(target.getByText(/DPO impact|Payment timing strategy/i)).toBeVisible()
    await expect(target.getByText(/Optimized payment timing|Unavailable|\d+(\.\d+)?%/i).first()).toBeVisible()
  })

  test('test_compliance_panel_visible', async ({ page }) => {
    await goToS2PPreview(page)
    const target = panel(page, /Compliance screening/i)
    await expect(target).toBeVisible({ timeout: 15_000 })
    await expect(target.getByText(/Suppliers screened|Loading compliance|S2P backend unavailable/i).first()).toBeVisible()
  })

  test('test_process_fusion_panel_visible', async ({ page }) => {
    await goToS2PPreview(page)
    const target = panel(page, /Process fusion/i)
    await expect(target).toBeVisible({ timeout: 15_000 })
    await expect(target.getByText(/Current stage|Loading process|S2P backend unavailable/i).first()).toBeVisible()
  })

  test('test_novelty_panel_visible', async ({ page }) => {
    await goToS2PPreview(page)
    const target = panel(page, /Novelty detection/i)
    await expect(target).toBeVisible({ timeout: 15_000 })
    await expect(target.getByText(/Novelty rate|Loading novelty|S2P backend unavailable/i).first()).toBeVisible()
  })

  test('test_trend_panel_visible', async ({ page }) => {
    await goToS2PPreview(page)
    const target = panel(page, /Trend correlation/i)
    await expect(target).toBeVisible({ timeout: 15_000 })
    await expect(target.getByText(/Early warnings/i)).toBeVisible()
    await expect(target.getByText(/\d+/).first()).toBeVisible()
  })
})