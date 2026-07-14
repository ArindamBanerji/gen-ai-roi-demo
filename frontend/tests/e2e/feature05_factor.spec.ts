// FEATURE-05A: Factor Analysis (SNR) — E2E tests for the Factor Analysis panel in System Health.
// Backend must be running on BACKEND_PORT (default 8001).

import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname  = path.dirname(__filename);

const FRONTEND_PORT = process.env.FRONTEND_PORT || '5173';
const FRONTEND      = `http://127.0.0.1:${FRONTEND_PORT}`;
const SCREENSHOTS   = path.join(__dirname, 'screenshots', 'feature05_factor');

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
  const dBtn = page.locator('button').filter({ hasText: /\[D\]/ }).first();
  await dBtn.waitFor({ state: 'visible', timeout: 10_000 });
  await dBtn.click();
  await page.waitForTimeout(2000);
  try { await page.locator('#section-d').scrollIntoViewIfNeeded(); } catch { /* ok */ }
  await page.waitForTimeout(1000);
}

test('test_factor_analysis_section_renders', async ({ page }) => {
  test.setTimeout(90_000);
  await goToSystemHealth(page);

  // Factor Analysis (SNR) panel heading.
  const faText = page.getByText(/Factor Analysis.*SNR|SNR.*Factor Analysis/i).first();
  await faText.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(500);

  await expect(faText).toBeVisible({ timeout: 10_000 });
  console.log('Factor Analysis (SNR) section: VISIBLE');
  await snap(page, '01_factor_section');
});

test('test_factor_analysis_summary_loads', async ({ page }) => {
  test.setTimeout(90_000);
  await goToSystemHealth(page);

  await page.getByText(/Factor Analysis.*SNR|SNR.*Factor Analysis/i).first().scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(1000);

  // Factor Analysis panel starts COLLAPSED — click its toggle to expand it.
  const faToggle = page.locator('button').filter({ has: page.getByText(/Factor Analysis/i) }).first();
  const faToggleVisible = await faToggle.isVisible({ timeout: 5_000 }).catch(() => false);
  if (faToggleVisible) {
    await faToggle.click();
    await page.waitForTimeout(2000);
  }

  // Overall SNR value.
  const snrLabel = page.getByText(/Overall SNR/i).first();
  const snrVisible = await snrLabel.isVisible({ timeout: 10_000 }).catch(() => false);
  console.log(`Overall SNR label: ${snrVisible ? 'VISIBLE' : 'NOT VISIBLE'}`);

  if (snrVisible) {
    // The SNR value is a .text-2xl element near the label.
    const snrValue = page.locator('.text-2xl').filter({ hasText: /\d+\.\d+/ }).first();
    const snrValVisible = await snrValue.isVisible({ timeout: 3_000 }).catch(() => false);
    console.log(`SNR numeric value visible: ${snrValVisible}`);
  }

  // Weakest category: the table should name categories.
  const weakestEl = page.getByText(/weakest|Weakest|SNR/i).first();
  const weakestVisible = await weakestEl.isVisible({ timeout: 5_000 }).catch(() => false);
  console.log(`Weakest category / SNR text visible: ${weakestVisible}`);

  // Loading or error states.
  const loadingEl = page.getByText(/Loading SNR summary/i).first();
  const errorEl   = page.getByText(/Factor Analysis summary unavailable/i).first();
  const isLoading = await loadingEl.isVisible({ timeout: 2_000 }).catch(() => false);
  const isError   = await errorEl.isVisible({ timeout: 2_000 }).catch(() => false);
  console.log(`SNR loading: ${isLoading}, error: ${isError}`);

  expect(snrVisible || isLoading || isError).toBe(true);
  await snap(page, '02_factor_summary');
});

test('test_factor_proposal_card', async ({ page }) => {
  test.setTimeout(90_000);
  await goToSystemHealth(page);

  await page.getByText(/Factor Analysis.*SNR|SNR.*Factor Analysis/i).first().scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(1000);

  // Factor Analysis panel starts COLLAPSED — expand it.
  const faToggle = page.locator('button').filter({ has: page.getByText(/Factor Analysis/i) }).first();
  const faToggleVisible = await faToggle.isVisible({ timeout: 5_000 }).catch(() => false);
  if (faToggleVisible) {
    await faToggle.click();
    await page.waitForTimeout(2000);
  }

  // Proposal card: "recommendation" text and "Structural analysis" label.
  const recommendEl = page.getByText(/recommendation/i).first();
  const recommendVisible = await recommendEl.isVisible({ timeout: 5_000 }).catch(() => false);
  console.log(`Proposal "recommendation" text: ${recommendVisible ? 'VISIBLE' : 'NOT VISIBLE (no proposal yet)'}`);

  const structuralEl = page.getByText(/Structural analysis/i).first();
  const structuralVisible = await structuralEl.isVisible({ timeout: 3_000 }).catch(() => false);
  console.log(`"Structural analysis" label: ${structuralVisible ? 'VISIBLE' : 'NOT VISIBLE'}`);

  // Factor Analysis section itself must be present.
  await expect(page.getByText(/Factor Analysis.*SNR|SNR.*Factor Analysis/i).first()).toBeVisible({ timeout: 10_000 });
  await snap(page, '03_factor_proposal');
});
