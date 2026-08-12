import { test, expect } from '@playwright/test'

async function navigateToS2PPreview(page: import('@playwright/test').Page) {
  await page.goto('/')
  await page.getByText('S2P Preview').click()
  await expect(page.getByText(/S2P Preview|Exception Queue|S2P Preview backend is not available/i).first()).toBeVisible({ timeout: 10_000 })
}

test('supplier lead-time renders contractual and actual Q4 values', async ({ page }) => {
  await navigateToS2PPreview(page)

  const supplierSection = page.locator('div').filter({ hasText: 'Supplier Profile' }).first()
  await expect(supplierSection).toBeVisible({ timeout: 10_000 })
  await expect(supplierSection.getByText('Lead time').first()).toBeVisible({ timeout: 10_000 })
  const sectionText = await supplierSection.innerText()
  expect(sectionText).not.toMatch(/undefined|NaN/i)
  expect(sectionText).toMatch(/\d+\s+contractual days/)
  expect(sectionText).toMatch(/\d+\s+actual Q4 days/)
  expect(sectionText).toMatch(/\d+\s+contractual days\s*·\s*\d+\s+actual Q4 days/)
})

test.skip('domain applicability panel is visible in Tab 6', async ({ page }) => {
  await navigateToS2PPreview(page)

  await expect(page.getByText('Domain Applicability')).toBeVisible({ timeout: 10_000 })
  await expect(page.getByText('Nine domains, one engine.')).toBeVisible()
  await expect(page.getByText('2 live')).toBeVisible()
  await expect(page.getByText('3 specified')).toBeVisible()
  await expect(page.getByText('4 designed')).toBeVisible()

  const bodyText = await page.locator('body').innerText()
  expect(bodyText).toContain('SOC')
  expect(bodyText).toContain('S2P')
  expect(bodyText).toMatch(/Trading|Purchasing|DataOps/)
})

test('Tab 6 visible UI does not mention hardcoded port 8002', async ({ page }) => {
  await navigateToS2PPreview(page)

  const visibleText = await page.locator('body').innerText()
  expect(visibleText).not.toContain('8002')
  expect(visibleText).not.toMatch(/port\s+8002/i)
})

test.skip('domain applicability remains visible when S2P backend is unavailable', async ({ page }) => {
  // Requires SOC backend up and S2P backend down; run manually or unskip in a controlled stack.
  await navigateToS2PPreview(page)

  await expect(page.getByText('S2P Preview backend is not available')).toBeVisible()
  const visibleText = await page.locator('body').innerText()
  expect(visibleText).not.toContain('8002')
  expect(visibleText).not.toMatch(/port\s+8002/i)
  await expect(page.getByText('Domain Applicability')).toBeVisible()
})
