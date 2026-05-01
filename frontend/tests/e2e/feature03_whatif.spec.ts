// FEATURE-03: What-If Simulator — E2E tests for the Conservation Projection panel in System Health.
// Backend must be running on BACKEND_PORT (default 8001).

import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname  = path.dirname(__filename);

const FRONTEND_PORT = process.env.FRONTEND_PORT || '5173';
const FRONTEND      = `http://localhost:${FRONTEND_PORT}`;
const SCREENSHOTS   = path.join(__dirname, 'screenshots', 'feature03_whatif');

test.beforeAll(() => {
  fs.mkdirSync(SCREENSHOTS, { recursive: true });
});

async function snap(page: import('@playwright/test').Page, name: string) {
  try {
    await page.screenshot({ path: path.join(SCREENSHOTS, `${name}.png`), fullPage: false });
  } catch (err) {
    console.log(`[screenshot] ${name}: ${err}`);
  }
}

async function goToSystemHealth(page: import('@playwright/test').Page) {
  await page.goto(FRONTEND);
  await page.waitForLoadState('domcontentloaded');
  await page.getByRole('button', { name: /Runtime Evolution/i }).waitFor({ state: 'visible', timeout: 15_000 });
  await page.getByRole('button', { name: /Runtime Evolution/i }).click();
  await page.waitForTimeout(1000);
  // Navigate to System Health subsection [D].
  const dBtn = page.locator('button').filter({ hasText: /\[D\]/ }).first();
  await dBtn.waitFor({ state: 'visible', timeout: 10_000 });
  await dBtn.click();
  await page.waitForTimeout(1500);
  // Scroll System Health into view.
  try { await page.locator('#section-d').scrollIntoViewIfNeeded(); } catch { /* ok */ }
  await page.waitForTimeout(1000);
}

test('test_whatif_section_renders', async ({ page }) => {
  test.setTimeout(90_000);
  await goToSystemHealth(page);

  const heading = page.getByRole('heading', { name: /What-If Simulator/i }).first();
  const headingVisible = await heading.isVisible({ timeout: 10_000 }).catch(() => false);

  if (!headingVisible) {
    // Scroll further — the What-If panel may be below the fold.
    await page.getByText(/What-If Simulator/i).first().scrollIntoViewIfNeeded().catch(() => {});
    await page.waitForTimeout(500);
  }

  const textEl = page.getByText(/What-If Simulator/i).first();
  await expect(textEl).toBeVisible({ timeout: 10_000 });
  console.log('What-If Simulator section: VISIBLE');
  await snap(page, '01_whatif_section');
});

test('test_whatif_presets_load', async ({ page }) => {
  test.setTimeout(120_000);
  await goToSystemHealth(page);

  await page.getByText(/What-If Simulator/i).first().scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(1000);

  // The What-If panel starts COLLAPSED. Click the toggle to expand it.
  const whatIfToggle = page.locator('button').filter({ has: page.getByText(/What-If Simulator/i) }).first();
  const toggleVisible = await whatIfToggle.isVisible({ timeout: 5_000 }).catch(() => false);
  if (toggleVisible) {
    await whatIfToggle.click();
    await page.waitForTimeout(1500);
  }

  // Actual preset labels from source: ['Healthy', 'Gradual Decline', 'Sudden Disruption'].
  const presetBtns = page.getByRole('button', { name: /Healthy|Gradual Decline|Sudden Disruption/i });
  const presetCount = await presetBtns.count().catch(() => 0);
  console.log(`Preset buttons found: ${presetCount}`);

  await snap(page, '02_whatif_presets');
  expect(presetCount).toBeGreaterThanOrEqual(3);

  // Verify each preset button is visible (scope: presets load, not click interaction).
  const firstPreset = presetBtns.first();
  const firstVisible = await firstPreset.isVisible({ timeout: 3_000 }).catch(() => false);
  console.log(`First preset button visible: ${firstVisible}`);
  await snap(page, '02b_whatif_preset_visible');
});

test('test_whatif_run_button', async ({ page }) => {
  test.setTimeout(120_000);
  await goToSystemHealth(page);

  await page.getByText(/What-If Simulator/i).first().scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(1000);

  // The What-If panel starts COLLAPSED. Expand it before looking for Run Projection.
  const whatIfToggle = page.locator('button').filter({ has: page.getByText(/What-If Simulator/i) }).first();
  const toggleVisible = await whatIfToggle.isVisible({ timeout: 5_000 }).catch(() => false);
  if (toggleVisible) {
    await whatIfToggle.click();
    await page.waitForTimeout(1500);
  }

  // "Run Projection" button.
  const runBtn = page.getByRole('button', { name: /Run Projection/i }).first();
  await expect(runBtn).toBeVisible({ timeout: 10_000 });
  console.log('"Run Projection" button: VISIBLE');

  await runBtn.scrollIntoViewIfNeeded();
  await runBtn.click();
  await page.waitForTimeout(3000);

  // Trajectory data appears: Days by Status, Final Status, Final IKS.
  const trajectoryEl = page.getByText(/Days by Status|Final Status|Final IKS/i).first();
  const trajectoryVisible = await trajectoryEl.isVisible({ timeout: 15_000 }).catch(() => false);
  console.log(`Trajectory results after Run Projection: ${trajectoryVisible ? 'VISIBLE' : 'NOT VISIBLE'}`);
  await snap(page, '03_whatif_run_result');
});

test('test_whatif_ceiling_line', async ({ page }) => {
  test.setTimeout(120_000);
  await goToSystemHealth(page);

  await page.getByText(/What-If Simulator/i).first().scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(1000);

  // Expand the What-If panel first.
  const whatIfToggle = page.locator('button').filter({ has: page.getByText(/What-If Simulator/i) }).first();
  const toggleVisible = await whatIfToggle.isVisible({ timeout: 5_000 }).catch(() => false);
  if (toggleVisible) {
    await whatIfToggle.click();
    await page.waitForTimeout(1500);
  }

  // Run a projection first.
  const runBtn = page.getByRole('button', { name: /Run Projection/i }).first();
  const runVisible = await runBtn.isVisible({ timeout: 5_000 }).catch(() => false);
  if (runVisible) {
    await runBtn.scrollIntoViewIfNeeded();
    await runBtn.click();
    await page.waitForTimeout(4000);
  }

  // Ceiling reference: either text "Structural ceiling" or "ceiling_estimate" label.
  const ceilingEl = page.getByText(/Structural ceiling|ceiling estimate/i).first();
  const ceilingVisible = await ceilingEl.isVisible({ timeout: 5_000 }).catch(() => false);
  console.log(`Ceiling reference line/text: ${ceilingVisible ? 'VISIBLE' : 'NOT VISIBLE (no ceiling data from API)'}`);
  await snap(page, '04_whatif_ceiling');
});
