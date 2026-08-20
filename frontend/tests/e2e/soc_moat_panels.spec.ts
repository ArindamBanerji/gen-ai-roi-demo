import { expect, test } from '@playwright/test'

const FRONTEND = process.env.SOC_FRONTEND ?? 'http://127.0.0.1:5173'
const BACKEND = process.env.SOC_BACKEND ?? 'http://127.0.0.1:8001'

test.beforeEach(async ({ request }) => {
  const health = await request.get(`${BACKEND}/health`, { timeout: 5_000 }).catch(() => null)
  test.skip(!health?.ok(), 'SOC backend not running')
})

test('learning control room renders five-face proof surface', async ({ page }) => {
  await page.goto(FRONTEND)
  await page.getByRole('button', { name: /Runtime Evolution/i }).click()
  const panel = page.getByTestId('learning-control-room-panel')
  await expect(panel).toBeVisible({ timeout: 20_000 })
  await expect(panel.getByText('Centroid movement', { exact: true })).toBeVisible()
  await expect(panel.getByText('Conservation state', { exact: true })).toBeVisible()
})

test('learning control room shows evidence and safety state', async ({ page }) => {
  await page.goto(FRONTEND)
  await page.getByRole('button', { name: /Runtime Evolution/i }).click()
  const panel = page.getByTestId('learning-control-room-panel')
  await expect(panel).toBeVisible({ timeout: 20_000 })
  await expect(panel.getByText(/live measurements|unavailable/i).first()).toBeVisible()
  await expect(panel.getByText(/shadow|conservation|rollback/i).first()).toBeVisible()
})

test('earned autonomy ladder renders per-category rungs', async ({ page }) => {
  await page.goto(FRONTEND)
  await page.getByRole('button', { name: 'Compounding', exact: true }).click()
  const panel = page.getByTestId('autonomy-ladder-panel')
  await expect(panel).toBeVisible({ timeout: 20_000 })
  await expect(panel.getByText('Earned autonomy', { exact: true })).toBeVisible()
})

test('earned autonomy ladder exposes circuit-break state when present', async ({ page }) => {
  await page.goto(FRONTEND)
  await page.getByRole('button', { name: 'Compounding', exact: true }).click()
  const panel = page.getByTestId('autonomy-ladder-panel')
  await expect(panel).toBeVisible({ timeout: 20_000 })
  await expect(panel.getByText(/circuit-broken|No authority records/i).first()).toBeVisible()
})

test('no-precedent sidebar renders beside triage detail', async ({ page }) => {
  await page.goto(FRONTEND)
  await page.getByRole('button', { name: /Alert Triage/i }).click()
  await expect(page.getByTestId('no-precedent-sidebar')).toBeVisible({ timeout: 20_000 })
})

test('no-precedent surface keeps an honest unprecedented empty state', async ({ page }) => {
  await page.goto(FRONTEND)
  await page.getByRole('button', { name: /Alert Triage/i }).click()
  const panel = page.getByTestId('no-precedent-sidebar')
  await expect(panel).toBeVisible({ timeout: 20_000 })
  await expect(panel.getByText(/NONE — unprecedented here\.|Precedent search unavailable/i)).toBeVisible()
})

test('what-if inspector renders factor sensitivity', async ({ page }) => {
  await page.goto(FRONTEND)
  await page.getByRole('button', { name: /Alert Triage/i }).click()
  const panel = page.getByTestId('what-if-inspector')
  await expect(panel).toBeVisible({ timeout: 20_000 })
  await expect(panel.getByText('What would change the decision?', { exact: true })).toBeVisible()
})

test('coverage panel renders fixed safety bar metrics', async ({ page }) => {
  await page.goto(FRONTEND)
  await page.getByRole('button', { name: 'Compounding', exact: true }).click()
  const panel = page.getByTestId('coverage-safety-bar-panel')
  await expect(panel).toBeVisible({ timeout: 20_000 })
  await expect(panel.getByText('Safe auto-approve coverage', { exact: true })).toBeVisible()
  await expect(panel.getByText('Recovery half-life', { exact: true })).toBeVisible()
})

test('day-zero readiness renders honest fresh-tenant view', async ({ page }) => {
  await page.goto(FRONTEND)
  await page.getByRole('button', { name: /Analytics/i }).click()
  const panel = page.getByTestId('day-zero-readiness-panel')
  await expect(panel).toBeVisible({ timeout: 20_000 })
  await expect(panel.getByText('Day-zero readiness', { exact: true })).toBeVisible()
  await expect(panel.getByText('no fabricated ROI', { exact: true })).toBeVisible()
})

test('triage to evolution to compounding keeps all moat panels addressable', async ({ page }) => {
  await page.goto(FRONTEND)
  await page.getByRole('button', { name: /Alert Triage/i }).click()
  await expect(page.getByTestId('what-if-inspector')).toBeVisible({ timeout: 20_000 })
  await page.getByRole('button', { name: /Runtime Evolution/i }).click()
  await expect(page.getByTestId('learning-control-room-panel')).toBeVisible({ timeout: 20_000 })
  await page.getByRole('button', { name: 'Compounding', exact: true }).click()
  await expect(page.getByTestId('autonomy-ladder-panel')).toBeVisible({ timeout: 20_000 })
  await expect(page.getByTestId('coverage-safety-bar-panel')).toBeVisible({ timeout: 20_000 })
})
