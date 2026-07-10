import { test, expect, type Page } from '@playwright/test'
import { BACKEND, FRONTEND, navigateToTab } from './helpers'

async function backendUp(page: Page) {
  try {
    const response = await page.request.get(`${BACKEND}/api/soc/campaign-timeline`, { timeout: 5000 })
    return response.ok()
  } catch {
    return false
  }
}

async function gotoRuntimeEvolution(page: Page) {
  await page.goto(FRONTEND)
  await navigateToTab(page, 2)
  await expect(page.getByRole('heading', { name: 'Campaign Timeline', exact: true })).toBeVisible({ timeout: 20000 })
}

test.describe('SOC campaign timeline', () => {
  test('Campaign Timeline heading visible on Runtime Evolution tab', async ({ page }) => {
    await gotoRuntimeEvolution(page)
  })

  test('campaign entry renders when data exists', async ({ page }) => {
    const up = await backendUp(page)
    await gotoRuntimeEvolution(page)
    if (!up) {
      await expect(page.getByText(/Campaign timeline unavailable|No campaigns detected/i)).toBeVisible()
      return
    }

    const response = await page.request.get(`${BACKEND}/api/soc/campaign-timeline`)
    const data = await response.json()
    if (!Array.isArray(data) || data.length === 0) {
      await expect(page.getByText(/No campaigns detected/i)).toBeVisible()
      return
    }
    await expect(page.getByText(data[0].campaign_id).first()).toBeVisible()
  })

  test('campaign state badge visible', async ({ page }) => {
    const up = await backendUp(page)
    await gotoRuntimeEvolution(page)
    if (!up) {
      await expect(page.getByText(/Campaign timeline unavailable|No campaigns detected/i)).toBeVisible()
      return
    }
    const response = await page.request.get(`${BACKEND}/api/soc/campaign-timeline`)
    const data = await response.json()
    if (!Array.isArray(data) || data.length === 0) {
      await expect(page.getByText(/No campaigns detected/i)).toBeVisible()
      return
    }
    await expect(page.getByText(/Active|Continuing|Resolved/i).first()).toBeVisible()
  })

  test('summary counts visible', async ({ page }) => {
    const up = await backendUp(page)
    await gotoRuntimeEvolution(page)
    if (!up) {
      await expect(page.getByText(/Campaign timeline unavailable|No campaigns detected/i)).toBeVisible()
      return
    }
    const response = await page.request.get(`${BACKEND}/api/soc/campaign-timeline`)
    const data = await response.json()
    if (!Array.isArray(data) || data.length === 0) {
      await expect(page.getByText(/No campaigns detected/i)).toBeVisible()
      return
    }
    await expect(page.getByText(/Active: \d+/i)).toBeVisible()
    await expect(page.getByText(/Continuing: \d+/i)).toBeVisible()
    await expect(page.getByText(/Resolved: \d+/i)).toBeVisible()
  })

  test('provenance badge visible when timeline data exists', async ({ page }) => {
    const up = await backendUp(page)
    await gotoRuntimeEvolution(page)
    if (!up) {
      await expect(page.getByText(/Campaign timeline unavailable|No campaigns detected/i)).toBeVisible()
      return
    }
    const response = await page.request.get(`${BACKEND}/api/soc/campaign-timeline`)
    const data = await response.json()
    if (!Array.isArray(data) || data.length === 0) {
      await expect(page.getByText(/No campaigns detected/i)).toBeVisible()
      return
    }
    const panel = page.getByTestId('campaign-timeline-panel')
    await expect(panel.getByText(/learned|context|proven|sample/i).first()).toBeVisible()
  })

  test('heading renders when no campaigns are returned', async ({ page }) => {
    await page.route('**/api/soc/campaign-timeline', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: '[]',
      })
    })
    await gotoRuntimeEvolution(page)
    await expect(page.getByText(/No campaigns detected/i)).toBeVisible()
  })
})
