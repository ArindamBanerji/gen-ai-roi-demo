import { test, expect } from '@playwright/test'

async function goToS2P(page: import('@playwright/test').Page) {
  await page.goto('/')
  await page.getByText('S2P Preview').click()
  await page.waitForTimeout(2000)
}

test('s2p_tab_button_visible', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('S2P Preview')).toBeVisible({ timeout: 10_000 })
})

test('s2p_tab_renders_without_crash', async ({ page }) => {
  await goToS2P(page)

  const title = await page.title()
  expect(title.length).toBeGreaterThan(0)

  const containerVisible = await page.locator('.bg-soc-card, .bg-slate-900, .bg-slate-800').first().isVisible({ timeout: 5_000 }).catch(() => false)
  const previewVisible = await page.getByText(/S2P Preview|Exception Queue|S2P service not connected/i).first().isVisible({ timeout: 5_000 }).catch(() => false)
  expect(containerVisible || previewVisible).toBe(true)
})

test('preview_queue_returns_valid_data', async ({ page }) => {
  const res = await page.request.get('/api/s2p/preview/queue')
  expect(res.ok()).toBeTruthy()

  const data = await res.json()
  expect(data.invoices).toBeDefined()
  expect(Array.isArray(data.invoices)).toBeTruthy()

  if (Array.isArray(data.invoices) && data.invoices.length > 0) {
    const inv = data.invoices[0]
    expect(inv.factor_vector).toBeDefined()
    expect(Array.isArray(inv.factor_vector)).toBeTruthy()
    if (Array.isArray(inv.factor_vector)) {
      expect(inv.factor_vector.length).toBe(8)
    }
    expect(inv.recommended_action).toBeDefined()
    if (typeof inv.confidence === 'number') {
      expect(inv.confidence).toBeGreaterThanOrEqual(0)
      expect(inv.confidence).toBeLessThanOrEqual(1)
    }
  }
})

test('preview_conservation_returns_status', async ({ page }) => {
  const res = await page.request.get('/api/s2p/preview/conservation')
  expect(res.ok()).toBeTruthy()

  const data = await res.json()
  expect(['GREEN', 'AMBER', 'RED']).toContain(data.status)
  expect(typeof data.auto_approve_pct).toBe('number')
  expect(typeof data.verified_decisions).toBe('number')
})

test('preview_compounding_returns_trajectory', async ({ page }) => {
  const res = await page.request.get('/api/s2p/preview/compounding')
  expect(res.ok()).toBeTruthy()

  const data = await res.json()
  expect(Array.isArray(data.trajectory)).toBeTruthy()
  if (!Array.isArray(data.trajectory)) return
  expect(data.trajectory.length).toBeGreaterThan(0)

  const first = data.trajectory[0]?.accuracy
  const last = data.trajectory[data.trajectory.length - 1]?.accuracy
  if (typeof first === 'number' && typeof last === 'number') {
    expect(last).toBeGreaterThanOrEqual(first)
  }
})

test('preview_suppliers_returns_chen_lin', async ({ page }) => {
  const res = await page.request.get('/api/s2p/preview/suppliers?limit=10')
  expect(res.ok()).toBeTruthy()

  const data = await res.json()
  expect(Array.isArray(data.suppliers)).toBeTruthy()
  if (!Array.isArray(data.suppliers)) return
  expect(data.suppliers.length).toBe(10)

  const names = data.suppliers.map((supplier: { supplier_name?: string }) => supplier.supplier_name)
  const chenLin = data.suppliers.find((supplier: { supplier_name?: string }) => supplier.supplier_name?.includes('Chen-Lin'))
  expect(names.some((name: string | undefined) => name?.includes('Chen-Lin'))).toBeTruthy()
  if (chenLin) {
    expect(chenLin.otif?.q1_q2).toBe(0.88)
    expect(chenLin.otif?.q3).toBe(0.88)
  }
})

test('preview_config_returns_v2_shape', async ({ page }) => {
  const res = await page.request.get('/api/s2p/preview/config')
  expect(res.ok()).toBeTruthy()

  const data = await res.json()
  expect(String(data.tensor_shape ?? '')).toContain('5, 5, 8')
  expect(Array.isArray(data.factors)).toBeTruthy()
  if (Array.isArray(data.factors)) expect(data.factors.length).toBe(8)
  expect(Array.isArray(data.categories)).toBeTruthy()
  if (Array.isArray(data.categories)) expect(data.categories.length).toBe(5)
  expect(Array.isArray(data.actions)).toBeTruthy()
  if (Array.isArray(data.actions)) expect(data.actions.length).toBe(5)
})

test('s2p_tab_shows_invoice_queue_or_error', async ({ page }) => {
  await goToS2P(page)

  const queueVisible = await page.getByText(/Exception Queue/i).first().isVisible({ timeout: 5_000 }).catch(() => false)
  const errorVisible = await page.getByText(/S2P service not connected/i).first().isVisible({ timeout: 5_000 }).catch(() => false)
  expect(queueVisible || errorVisible).toBe(true)
})

test('s2p_tab_no_soc_categories', async ({ page }) => {
  await goToS2P(page)

  for (const cat of ['credential_access', 'lateral_movement', 'data_exfiltration', 'insider_threat']) {
    const visible = await page.getByText(cat, { exact: true }).isVisible().catch(() => false)
    expect(visible).toBe(false)
  }
})

test('s2p_tab_no_soc_actions', async ({ page }) => {
  await goToS2P(page)

  for (const action of ['investigate', 'suppress']) {
    const visible = await page.getByText(action, { exact: true }).isVisible().catch(() => false)
    expect(visible).toBe(false)
  }
})

test('s2p_tab_handles_backend_down_gracefully', async ({ page }) => {
  await goToS2P(page)

  const title = await page.title()
  expect(title.length).toBeGreaterThan(0)
  const errorBoundaryVisible = await page.getByText(/something went wrong/i).isVisible().catch(() => false)
  expect(errorBoundaryVisible).toBe(false)
})
