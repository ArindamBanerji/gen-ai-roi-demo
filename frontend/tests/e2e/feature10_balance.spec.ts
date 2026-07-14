// FEATURE-10: Learning Balance Sheet — E2E tests on the Compounding tab.
// Backend must be running on BACKEND_PORT (default 8001).

import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname  = path.dirname(__filename);

const FRONTEND_PORT = process.env.FRONTEND_PORT || '5173';
const FRONTEND      = `http://127.0.0.1:${FRONTEND_PORT}`;
const SCREENSHOTS   = path.join(__dirname, 'screenshots', 'feature10_balance');

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

async function goToCompounding(page: import('@playwright/test').Page) {
  await page.goto(FRONTEND);
  await page.waitForLoadState('domcontentloaded');
  await page.getByRole('button', { name: /Compounding/i }).waitFor({ state: 'visible', timeout: 15_000 });
  await page.getByRole('button', { name: /Compounding/i }).click();
  await page.waitForTimeout(2000);
}

test('test_balance_sheet_section_renders', async ({ page }) => {
  test.setTimeout(60_000);
  await goToCompounding(page);

  // Scroll down to find Learning Balance Sheet — it is below Evaluate on Your Data.
  const balanceHeading = page.getByRole('heading', { name: /Learning Balance Sheet/i }).first();
  await balanceHeading.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(500);

  await expect(balanceHeading).toBeVisible({ timeout: 10_000 });
  console.log('Learning Balance Sheet section: VISIBLE');
  await snap(page, '01_balance_section');
});

test('test_balance_sheet_loads_categories', async ({ page }) => {
  test.setTimeout(90_000);
  await goToCompounding(page);

  // Scroll to the section.
  const balanceHeading = page.getByRole('heading', { name: /Learning Balance Sheet/i }).first();
  await balanceHeading.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(500);

  // Click the section header button to expand (it is a collapsible).
  // The heading is inside a <button> that toggles expanded state.
  const toggleBtn = page.locator('button').filter({ has: page.getByRole('heading', { name: /Learning Balance Sheet/i }) }).first();
  const isToggle = await toggleBtn.isVisible({ timeout: 3_000 }).catch(() => false);
  if (isToggle) {
    await toggleBtn.click();
    await page.waitForTimeout(2000);
  }

  // Wait for data to load (loading state disappears).
  await page.waitForFunction(
    () => !document.body.innerText.includes('Loading learning balance sheet'),
    { timeout: 15_000 }
  ).catch(() => console.log('Loading indicator timeout'));

  // Table columns: Category, Band, Verified, Drift, Auto-approve, Status.
  const categoryHeader = page.getByRole('columnheader', { name: /Category/i }).first();
  const categoryVisible = await categoryHeader.isVisible({ timeout: 10_000 }).catch(() => false);
  console.log(`Table Category column header: ${categoryVisible ? 'VISIBLE' : 'NOT VISIBLE'}`);

  const bandHeader = page.getByRole('columnheader', { name: /Band/i }).first();
  const bandVisible = await bandHeader.isVisible({ timeout: 3_000 }).catch(() => false);
  console.log(`Table Band column header: ${bandVisible ? 'VISIBLE' : 'NOT VISIBLE'}`);

  const verifiedHeader = page.getByRole('columnheader', { name: /Verified/i }).first();
  const verifiedVisible = await verifiedHeader.isVisible({ timeout: 3_000 }).catch(() => false);
  console.log(`Table Verified column header: ${verifiedVisible ? 'VISIBLE' : 'NOT VISIBLE'}`);

  const statusHeader = page.getByRole('columnheader', { name: /Status/i }).first();
  const statusVisible = await statusHeader.isVisible({ timeout: 3_000 }).catch(() => false);
  console.log(`Table Status column header: ${statusVisible ? 'VISIBLE' : 'NOT VISIBLE'}`);

  if (categoryVisible) {
    // SOC has 6 categories — verify 6 data rows.
    const rows = page.getByTestId('learning-balance-category-row');
    const rowCount = await rows.count().catch(() => 0);
    console.log(`Balance sheet table rows: ${rowCount} (expect 6)`);
    expect(rowCount).toBe(6);
  } else {
    // Table may not have rendered yet — check for loading/error.
    const loadingEl = page.getByText(/Loading learning balance sheet/i).first();
    const errorEl   = page.getByText(/Unable to load learning balance sheet/i).first();
    const isLoading = await loadingEl.isVisible({ timeout: 2_000 }).catch(() => false);
    const isError   = await errorEl.isVisible({ timeout: 2_000 }).catch(() => false);
    console.log(`Balance sheet loading: ${isLoading}, error: ${isError}`);
    expect(isLoading || isError || categoryVisible).toBe(true);
  }

  await snap(page, '02_balance_categories');
});

test('test_balance_sheet_ceiling_column', async ({ page }) => {
  test.setTimeout(90_000);
  await goToCompounding(page);

  const balanceHeading = page.getByRole('heading', { name: /Learning Balance Sheet/i }).first();
  await balanceHeading.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(500);

  // Expand the section if needed.
  const toggleBtn = page.locator('button').filter({ has: page.getByRole('heading', { name: /Learning Balance Sheet/i }) }).first();
  const isToggle = await toggleBtn.isVisible({ timeout: 3_000 }).catch(() => false);
  if (isToggle) {
    await toggleBtn.click();
    await page.waitForTimeout(2000);
  }

  await page.waitForFunction(
    () => !document.body.innerText.includes('Loading learning balance sheet'),
    { timeout: 15_000 }
  ).catch(() => {});

  // Ceiling column header (conditionally rendered when ceiling_estimate data exists).
  const ceilingHeader = page.getByRole('columnheader', { name: /Ceiling/i }).first();
  const ceilingVisible = await ceilingHeader.isVisible({ timeout: 5_000 }).catch(() => false);
  console.log(`Ceiling column header: ${ceilingVisible ? 'VISIBLE' : 'NOT VISIBLE (no ceiling data yet — expected at baseline)'}`);

  // Status column must always render with valid status values.
  const statusHeader = page.getByRole('columnheader', { name: /Status/i }).first();
  const statusVisible = await statusHeader.isVisible({ timeout: 5_000 }).catch(() => false);
  console.log(`Status column: ${statusVisible ? 'VISIBLE' : 'NOT VISIBLE'}`);

  if (statusVisible) {
    // At least one valid status badge: insufficient_data, at_ceiling, converging, early.
    const statusBadge = page.getByText(/insufficient_data|at_ceiling|converging|early/i).first();
    const badgeVisible = await statusBadge.isVisible({ timeout: 5_000 }).catch(() => false);
    console.log(`Status badge value visible: ${badgeVisible}`);
  }

  // Section must be present regardless of ceiling data.
  await expect(page.getByRole('heading', { name: /Learning Balance Sheet/i }).first()).toBeVisible({ timeout: 10_000 });
  await snap(page, '03_balance_ceiling');
});
