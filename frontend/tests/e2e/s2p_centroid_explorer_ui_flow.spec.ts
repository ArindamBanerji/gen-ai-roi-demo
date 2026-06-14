import { expect, type Locator, type Page, test } from '@playwright/test'

const S2P_UI_BASE_URL = process.env.S2P_UI_BASE_URL ?? 'http://127.0.0.1:5177'

async function openTab(page: Page, name: string) {
  const byRole = page.getByRole('button', { name })
  if ((await byRole.count()) > 0) {
    await byRole.first().click()
    return
  }
  await page.getByText(name, { exact: true }).first().click()
}

async function openTriage(page: Page) {
  await page.goto(S2P_UI_BASE_URL)
  await openTab(page, 'Exception Triage')
  await expect(page.getByRole('heading', { name: 'Exception Triage' })).toBeVisible()
}

async function scoreCurrentInvoice(page: Page): Promise<{ decisionId: string; explorer: Locator }> {
  await page.getByRole('button', { name: 'Score' }).click()
  const decisionLine = page.getByText(/^Decision\s+\S+/).first()
  await expect(decisionLine).toBeVisible()
  const text = (await decisionLine.textContent()) ?? ''
  const decisionId = text.replace(/^Decision\s+/, '').trim()
  expect(decisionId.length).toBeGreaterThan(0)

  const explorer = page.locator('article').filter({ hasText: 'Decision proximity explanation' }).first()
  await expect(explorer).toBeVisible()
  return { decisionId, explorer }
}

test.describe('S2P centroid explorer UI flow', () => {
  test('score-to-centroid-explorer flow renders explanation sections without learning claims', async ({ page }) => {
    await openTriage(page)
    const { decisionId, explorer } = await scoreCurrentInvoice(page)

    await expect(explorer.getByText(decisionId)).toBeVisible()
    await expect(explorer.getByText('Recommended', { exact: true })).toBeVisible()
    await expect(explorer.getByText('Closest centroid', { exact: true })).toBeVisible()
    await expect(explorer.getByText('Factor proximity')).toBeVisible()
    await expect(explorer.getByText('Action distance table')).toBeVisible()
    await expect(explorer.getByText('P39 supplier evidence')).toBeVisible()
    await expect(explorer.getByText('Centroid drift')).toBeVisible()
    await expect(
      explorer.getByText(/Centroid history unavailable|Timestamp|Checking centroid history/i),
    ).toBeVisible()
    await expect(explorer.getByText('Checking centroid history...')).toHaveCount(0, { timeout: 10000 })
    const explorerText = ((await explorer.textContent()) ?? '').toLowerCase()
    expect(explorerText).not.toContain('learning_applied')
    expect(explorerText).not.toContain('outcome_written')
    expect(explorerText).not.toContain('learning applied true')
    expect(explorerText).not.toContain('outcome written true')
  })

  test('second scored decision refreshes centroid explorer instead of keeping stale decision id', async ({ page }) => {
    await openTriage(page)
    const first = await scoreCurrentInvoice(page)

    const invoiceButtons = page.locator('article').filter({ hasText: 'Invoice Selector' }).getByRole('button')
    test.skip((await invoiceButtons.count()) < 2, 'Need at least two preview invoices for a distinct decision transition')

    await invoiceButtons.nth(1).click()
    await expect(page.getByText(first.decisionId)).toHaveCount(0)

    const second = await scoreCurrentInvoice(page)
    expect(second.decisionId).not.toBe(first.decisionId)
    await expect(second.explorer.getByText(second.decisionId)).toBeVisible()
    await expect(second.explorer.getByText(first.decisionId)).toHaveCount(0)
  })
})
