import { expect, test, type APIRequestContext } from '@playwright/test'
import { FRONTEND, BACKEND, collectConsoleErrors, expectNoConsoleErrors, navigateToTab, resetDemoAlerts } from './helpers'

interface FactorContribution {
  name: string
  index: number
  contribution_pct: number
  signal_strength: string
  rank: number
}

interface FactorContributionResponse {
  factors: FactorContribution[]
  method: string
  top_factor: string | null
  weakest_factor: string | null
}

async function fetchFactorContribution(request: APIRequestContext): Promise<FactorContributionResponse> {
  const response = await request.get(`${BACKEND}/api/soc/factor-contribution`)
  expect(response.status()).toBe(200)
  return response.json()
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function factorNamePattern(name: string) {
  return new RegExp(escapeRegExp(name.replace(/_/g, ' ')), 'i')
}

function contributionTotal(factors: FactorContribution[]) {
  return factors.reduce((total, factor) => total + factor.contribution_pct, 0)
}

test('factor_contribution_api_returns_six_factors_summing_to_100', async ({ request }) => {
  const data = await fetchFactorContribution(request)

  expect(Array.isArray(data.factors)).toBe(true)
  expect(data.factors).toHaveLength(6)
  expect(contributionTotal(data.factors)).toBeGreaterThanOrEqual(99)
  expect(contributionTotal(data.factors)).toBeLessThanOrEqual(101)
  expect(data.method).toMatch(/^(dk_weights|uniform)$/)
  if (data.method === 'dk_weights') {
    expect(data.top_factor).toBeTruthy()
  }
})

test('factor_contribution_panel_visible_on_alert_triage', async ({ page }) => {
  await resetDemoAlerts(page)
  const apiData = await fetchFactorContribution(page.request)

  await page.goto(FRONTEND)
  await navigateToTab(page, 1)

  const alertCard = page.locator('button').filter({ hasText: /ALERT-|SIM-/i }).first()
  await alertCard.waitFor({ state: 'visible', timeout: 20_000 })
  await alertCard.click()

  await page.getByText(/Why This Decision\?/).waitFor({ state: 'visible', timeout: 30_000 })

  const panel = page.getByTestId('factor-contribution-panel')
  await expect(panel).toBeVisible({ timeout: 15_000 })
  await expect(panel).toContainText(`Factor Contributions (${apiData.method})`)
  if (apiData.top_factor) {
    await expect(panel).toContainText(factorNamePattern(apiData.top_factor))
  }

  for (const factor of apiData.factors) {
    await expect(page.getByTestId(`factor-bar-${factor.index}`)).toBeVisible()
  }
})

test('factor_contribution_panel_has_no_console_errors', async ({ page }) => {
  const errors = collectConsoleErrors(page)

  await resetDemoAlerts(page)
  await page.goto(FRONTEND)
  await navigateToTab(page, 1)

  const alertCard = page.locator('button').filter({ hasText: /ALERT-|SIM-/i }).first()
  await alertCard.waitFor({ state: 'visible', timeout: 20_000 })
  await alertCard.click()

  await expect(page.getByTestId('factor-contribution-panel')).toBeVisible({ timeout: 45_000 })
  expectNoConsoleErrors(errors)
})
