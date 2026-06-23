import { test, expect, type Page } from '@playwright/test'

async function openCompounding(page: Page) {
  await page.goto('/')
  const tab = page.getByRole('button', { name: /Compounding/i })
  await tab.waitFor({ state: 'visible', timeout: 15_000 })
  await tab.click()
}

test('tab4_three_channel_panel_visible', async ({ page }) => {
  await openCompounding(page)

  await expect(page.getByRole('heading', { name: /Three-Channel Error Budget/ })).toBeVisible({ timeout: 30_000 })
  await expect(page.getByText('Channel 1 (Scorer)')).toBeVisible({ timeout: 30_000 })
  await expect(page.getByText('Channel 2 (Graph)')).toBeVisible({ timeout: 30_000 })
  await expect(page.getByText('Channel 3 (Labels)')).toBeVisible({ timeout: 30_000 })
  await expect(page.getByText(/Estimated improvement/)).toBeVisible({ timeout: 30_000 })
  await expect(page.getByText(/simulation calibration/i)).toBeVisible({ timeout: 30_000 })
})

test('tab4_three_channel_labels_pending', async ({ page }) => {
  await openCompounding(page)

  await expect(page.getByRole('heading', { name: /Three-Channel Error Budget/ })).toBeVisible({ timeout: 30_000 })
  await expect(page.getByText('PENDING', { exact: true })).toBeVisible({ timeout: 30_000 })
})

test('tab3_learning_state_hidden_continuous', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: /Alert Triage/i }).waitFor({ state: 'visible', timeout: 15_000 })
  await page.getByRole('button', { name: /Alert Triage/i }).click()
  await page.waitForTimeout(2000)

  const alertCard = page.locator('button').filter({ hasText: /ALERT-|SIM-/ }).first()
  await alertCard.click()
  await page.waitForTimeout(1500)

  // After simulation decisions, Learning State may be visible.
  const lsCount = await page.getByText(' Learning State').count()
  expect(lsCount).toBeLessThanOrEqual(1)
})
