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
  await expect(page.getByText(/Exception Queue/i).first()).toBeVisible({ timeout: 15_000 })
}

async function expectVisibleText(page: Page, pattern: RegExp) {
  await expect(page.getByText(pattern).first()).toBeVisible({ timeout: 10_000 })
}

function s2pMain(page: Page) {
  return page.locator('main').filter({ hasText: 'S2P Preview' }).first()
}

test('s2p preview tab loads with engine version', async ({ page }) => {
  await goToS2PPreview(page)

  await expectVisibleText(page, /Powered by Graph Attention Engine v0\.7\.23/i)
  await expectVisibleText(page, /The engine is domain-agnostic\. The intelligence is firm-specific\./i)
})

test('s2p preview queue shows invoices, confidence, actions, and auto approve rate', async ({ page }) => {
  await goToS2PPreview(page)

  const queue = s2pMain(page).locator('table').first()
  await expect(queue).toBeVisible()
  await expect(queue.getByText(/INV-|S2P-/i).first()).toBeVisible()
  await expect(queue.getByText(/Auto Approve|Hold For Review|Escalate To Buyer|Flag Leakage|Refer To Specialist/i).first()).toBeVisible()
  await expect(queue.getByText(/\d+(\.\d+)?%/).first()).toBeVisible()
  await expectVisibleText(page, /auto approve/i)
})

test('s2p preview queue shows S2P categories', async ({ page }) => {
  await goToS2PPreview(page)

  await expectVisibleText(page, /Price Variance|Quantity Mismatch|Duplicate Risk|Contract Gap|Format Compliance/i)
})

test('s2p preview conservation shows green projected status and penalty ratio', async ({ page }) => {
  await goToS2PPreview(page)

  const conservation = s2pMain(page).locator('div').filter({ hasText: /^Conservation/ }).first()
  await expect(conservation).toBeVisible()
  await expect(conservation.getByText(/GREEN/i).first()).toBeVisible()
  await expect(conservation.getByText(/illustration|projected/i).first()).toBeVisible()
  await expect(conservation.getByText(/5:1/i).first()).toBeVisible()
  await expect(conservation.getByText(/Verified decisions/i).first()).toBeVisible()
})

test('s2p preview compounding curve shows projected milestones', async ({ page }) => {
  await goToS2PPreview(page)

  const curve = s2pMain(page).locator('div').filter({ hasText: 'Compounding Curve' }).first()
  await expect(curve).toBeVisible()
  await expect(curve.locator('svg').first()).toBeVisible()
  await expect(curve.getByText(/projected/i).first()).toBeVisible()
  await expect(curve.getByText(/72%|78%|84%/).first()).toBeVisible()
})

test('s2p preview supplier profile shows Chen-Lin, exception rate, and OTIF', async ({ page }) => {
  await goToS2PPreview(page)

  const supplierProfile = s2pMain(page).locator('div').filter({ hasText: 'Supplier Profile' }).first()
  await expect(supplierProfile).toBeVisible()
  await expect(supplierProfile.getByText(/Chen-Lin/i).first()).toBeVisible()
  await expect(supplierProfile.getByText(/Exception rate/i).first()).toBeVisible()
  await expect(supplierProfile.getByText(/OTIF score/i).first()).toBeVisible()
})

test('soc to s2p to soc round trip keeps both tabs working', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: /SOC Analytics/i }).first().click()
  await expect(page.getByText(/SOC Analytics|Governed security metrics|MTTR|auto-close/i).first()).toBeVisible({ timeout: 10_000 })

  await goToS2PPreview(page)
  await expectVisibleText(page, /Exception Queue/i)
  await expectVisibleText(page, /Conservation/i)

  await page.getByRole('button', { name: /SOC Analytics/i }).first().click()
  await expect(page.getByText(/SOC Analytics|Governed security metrics|MTTR|auto-close/i).first()).toBeVisible({ timeout: 10_000 })
})

test('s2p preview shows multiple actions and numeric confidence', async ({ page }) => {
  await goToS2PPreview(page)

  const mainText = await s2pMain(page).innerText()
  const actionMatches = mainText.match(/Auto Approve|Hold For Review|Escalate To Buyer|Flag Leakage|Refer To Specialist/g) || []
  expect(new Set(actionMatches).size).toBeGreaterThanOrEqual(2)
  expect(mainText).toMatch(/\b\d{1,3}(\.\d+)?%\b/)
})

test('s2p preview conservation and queue are populated together', async ({ page }) => {
  await goToS2PPreview(page)

  await expect(s2pMain(page).locator('table tbody tr').first()).toBeVisible()
  await expectVisibleText(page, /\d+ total/i)
  await expectVisibleText(page, /Accuracy/i)
  await expectVisibleText(page, /Verified decisions/i)
})

test('s2p preview all four panels are populated before the closing narrative', async ({ page }) => {
  await goToS2PPreview(page)

  const main = s2pMain(page)
  await expect(main.getByText(/Exception Queue/i).first()).toBeVisible()
  await expect(main.getByText(/^Conservation$/i).first()).toBeVisible()
  await expect(main.getByText(/Compounding Curve/i).first()).toBeVisible()
  await expect(main.getByText(/Supplier Profile/i).first()).toBeVisible()

  const bodyText = await main.innerText()
  expect(bodyText.indexOf('Exception Queue')).toBeLessThan(bodyText.indexOf('The engine is domain-agnostic'))
  expect(bodyText.indexOf('Supplier Profile')).toBeLessThan(bodyText.indexOf('The engine is domain-agnostic'))
})

test('s2p preview links Chen-Lin profile with loaded preview content', async ({ page }) => {
  await goToS2PPreview(page)

  const mainText = await s2pMain(page).innerText()
  expect(mainText).toMatch(/Chen-Lin/i)
  expect(mainText).toMatch(/Exception Queue/)
  expect(mainText).toMatch(/Supplier Profile/)
})
