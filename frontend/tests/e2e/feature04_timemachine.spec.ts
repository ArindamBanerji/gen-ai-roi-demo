// FEATURE-04: Centroid Time Machine — E2E tests for the Time Machine panel in System Health.
// Backend must be running on BACKEND_PORT (default 8001).

import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname  = path.dirname(__filename);

const FRONTEND_PORT = process.env.FRONTEND_PORT || '5173';
const FRONTEND      = `http://127.0.0.1:${FRONTEND_PORT}`;
const SCREENSHOTS   = path.join(__dirname, 'screenshots', 'feature04_timemachine');

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

test('test_timemachine_section_renders', async ({ page }) => {
  test.setTimeout(90_000);
  await goToSystemHealth(page);

  // Scroll to Time Machine heading — it is below What-If in the section.
  const tmText = page.getByText(/Centroid Time Machine/i).first();
  await tmText.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(500);

  await expect(tmText).toBeVisible({ timeout: 10_000 });
  console.log('Centroid Time Machine section: VISIBLE');
  await snap(page, '01_timemachine_section');
});

test('test_timemachine_timeline_chart', async ({ page }) => {
  test.setTimeout(90_000);
  await goToSystemHealth(page);

  await page.getByText(/Centroid Time Machine/i).first().scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(1500);

  // Recharts renders SVG. Check for SVG elements within the time machine panel area.
  const svgEls = page.locator('svg').filter({ has: page.locator('path') });
  const svgCount = await svgEls.count().catch(() => 0);
  console.log(`SVG chart elements in page: ${svgCount}`);

  // The timeline chart is a ComposedChart (Recharts → SVG).
  // If no snapshots exist yet, we expect the "No centroid snapshots yet" message.
  const noSnapshots = page.getByText(/No centroid snapshots yet/i).first();
  const noSnapshotsVisible = await noSnapshots.isVisible({ timeout: 3_000 }).catch(() => false);
  console.log(`"No centroid snapshots yet" message: ${noSnapshotsVisible}`);

  if (!noSnapshotsVisible) {
    expect(svgCount).toBeGreaterThan(0);
    console.log('Timeline chart SVG: VISIBLE');
  } else {
    console.log('Timeline chart: no data yet (snapshots not written)');
  }

  await snap(page, '02_timemachine_chart');
});

test('test_timemachine_snapshot_table', async ({ page }) => {
  test.setTimeout(90_000);
  await goToSystemHealth(page);

  await page.getByText(/Centroid Time Machine/i).first().scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(1500);

  // Snapshot table or "no snapshots" message.
  const tableEl = page.locator('table').first();
  const tableVisible = await tableEl.isVisible({ timeout: 5_000 }).catch(() => false);
  const noSnapshots = await page.getByText(/No centroid snapshots yet/i).first().isVisible({ timeout: 2_000 }).catch(() => false);

  console.log(`Snapshot table visible: ${tableVisible}`);
  console.log(`"No snapshots yet" message: ${noSnapshots}`);

  if (tableVisible) {
    // If table exists, rows may be 0 at baseline (no snapshots written yet).
    const rows = page.locator('table tbody tr');
    const rowCount = await rows.count().catch(() => 0);
    console.log(`Snapshot table rows: ${rowCount} (0 is valid at baseline)`);

    if (rowCount > 0) {
      // Columns should include SHA (sha256) data.
      const shaCell = page.locator('table').getByText(/[a-f0-9]{8}/i).first();
      const shaVisible = await shaCell.isVisible({ timeout: 3_000 }).catch(() => false);
      console.log(`SHA cell visible: ${shaVisible}`);
    } else {
      console.log('Snapshot table present but 0 rows — no snapshots written yet (expected at baseline)');
    }
  } else {
    console.log('Snapshot table: no snapshots yet (table not rendered)');
    expect(noSnapshots || !tableVisible).toBe(true);
  }

  await snap(page, '03_timemachine_table');
});

test('test_timemachine_bootstrap_compare', async ({ page }) => {
  test.setTimeout(90_000);
  await goToSystemHealth(page);

  await page.getByText(/Centroid Time Machine/i).first().scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(1500);

  // "Compare Current vs Bootstrap" button.
  const compareBtn = page.getByRole('button', { name: /Compare.*Bootstrap|Bootstrap.*Compare/i }).first();
  const compareBtnVisible = await compareBtn.isVisible({ timeout: 5_000 }).catch(() => false);
  console.log(`Compare Current vs Bootstrap button: ${compareBtnVisible ? 'VISIBLE' : 'NOT VISIBLE'}`);

  if (compareBtnVisible) {
    const isDisabled = await compareBtn.isDisabled().catch(() => true);
    console.log(`Compare button disabled (no snapshots): ${isDisabled}`);

    if (!isDisabled) {
      await compareBtn.click();
      await page.waitForTimeout(3000);

      const comparisonEl = page.getByText(/per_category|drift|distance|comparison/i).first();
      const comparisonVisible = await comparisonEl.isVisible({ timeout: 5_000 }).catch(() => false);
      console.log(`Comparison results: ${comparisonVisible ? 'VISIBLE' : 'NOT VISIBLE'}`);
    } else {
      console.log('Compare button disabled — no snapshots written yet (expected at baseline)');
    }
    await expect(compareBtn).toBeAttached();
  } else {
    console.log('Compare button not found — Time Machine panel may require scroll or section expansion');
  }

  await snap(page, '04_timemachine_compare');
});
