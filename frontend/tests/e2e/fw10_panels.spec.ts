import { test, expect } from '@playwright/test'

test('tab4_three_channel_panel_visible', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: /Compounding/i }).waitFor({ state: 'visible', timeout: 15_000 })
  await page.getByRole('button', { name: /Compounding/i }).click()
  await page.waitForTimeout(2000)

  await expect(page.getByText('Three-Channel Error Budget')).toBeVisible()
  await expect(page.getByText('Channel 1 (Scorer)')).toBeVisible()
  await expect(page.getByText('Channel 2 (Graph)')).toBeVisible()
  await expect(page.getByText('Channel 3 (Labels)')).toBeVisible()
  await expect(page.getByText(/Estimated improvement/)).toBeVisible()
  await expect(page.getByText(/simulation calibration/i)).toBeVisible()
})

test('tab4_three_channel_labels_pending', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: /Compounding/i }).waitFor({ state: 'visible', timeout: 15_000 })
  await page.getByRole('button', { name: /Compounding/i }).click()
  await page.waitForTimeout(2000)

  await expect(page.getByText('PENDING', { exact: true })).toBeVisible()
})

test('tab3_learning_state_hidden_continuous', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: /Alert Triage/i }).waitFor({ state: 'visible', timeout: 15_000 })
  await page.getByRole('button', { name: /Alert Triage/i }).click()
  await page.waitForTimeout(2000)

  const alertCard = page.locator('button').filter({ hasText: /ALERT-|SIM-/ }).first()
  await alertCard.click()
  await page.waitForTimeout(1500)

  await expect(page.getByText(' Learning State')).toHaveCount(0)
})
