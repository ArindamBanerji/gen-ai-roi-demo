// FEATURE-02: Governance Evidence — E2E tests for the governance panel on Executive Narrative tab.
// Backend must be running on BACKEND_PORT (default 8001).

import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname  = path.dirname(__filename);

const FRONTEND_PORT = process.env.FRONTEND_PORT || '5173';
const FRONTEND      = `http://127.0.0.1:${FRONTEND_PORT}`;
const SCREENSHOTS   = path.join(__dirname, 'screenshots', 'feature02_governance');

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

async function goToExecutiveNarrative(page: import('@playwright/test').Page) {
  await page.goto(FRONTEND);
  await page.waitForLoadState('domcontentloaded');
  await page.getByRole('button', { name: /Executive Narrative/i }).waitFor({ state: 'visible', timeout: 15_000 });
  await page.getByRole('button', { name: /Executive Narrative/i }).click();
  await page.waitForTimeout(2000);
}

test('test_governance_section_renders', async ({ page }) => {
  test.setTimeout(60_000);
  await goToExecutiveNarrative(page);

  // Governance & Compliance collapsible button is always present.
  const govButton = page.getByRole('button', { name: /Governance.*Compliance|Compliance.*Governance/i }).first();
  await expect(govButton).toBeVisible({ timeout: 10_000 });
  console.log('Governance & Compliance section: VISIBLE');

  // Legal disclaimer amber banner is always shown (outside the expanded conditional).
  const disclaimer = page.getByText(/Evidence supporting human oversight/i).first();
  const disclaimerVisible = await disclaimer.isVisible({ timeout: 5_000 }).catch(() => false);
  console.log(`Legal disclaimer banner visible: ${disclaimerVisible}`);

  await snap(page, '01_governance_section');
  await expect(govButton).toBeVisible();
});

test('test_governance_article_count', async ({ page }) => {
  test.setTimeout(90_000);
  await goToExecutiveNarrative(page);

  // Click to expand the governance section so article cards load.
  const govButton = page.getByRole('button', { name: /Governance.*Compliance|Compliance.*Governance/i }).first();
  await govButton.click();

  // Each article card renders a div directly containing the article identifier
  // ("Art 9", "Art 12", etc.) — the label div inside button.text-green-300.
  // Anchor with ^ and $ to match only that div's own textContent, not its parent
  // button whose concatenated textContent also includes title and status text.
  const articleLabels = page.locator('div').filter({ hasText: /^Art\s+\d+$/ });
  await articleLabels.first().waitFor({ state: 'visible', timeout: 30_000 });
  const count = await articleLabels.count();
  console.log(`Article section cards found: ${count}`);

  await snap(page, '02_governance_articles');

  // At least 5 EU AI Act article sections must render after expand.
  expect(count).toBeGreaterThanOrEqual(5);
});

test('test_governance_export_buttons', async ({ page }) => {
  test.setTimeout(90_000);
  await goToExecutiveNarrative(page);

  // Expand governance section so download buttons are rendered.
  const govButton = page.getByRole('button', { name: /Governance.*Compliance|Compliance.*Governance/i }).first();
  await govButton.click();
  await page.waitForTimeout(1500);

  // JSON download button.
  const jsonBtn = page.getByRole('button', { name: /Download JSON/i }).first();
  await expect(jsonBtn).toBeVisible({ timeout: 10_000 });
  console.log('Download JSON button: VISIBLE');

  // CSV download button.
  const csvBtn = page.getByRole('button', { name: /Download CSV/i }).first();
  await expect(csvBtn).toBeVisible({ timeout: 5_000 });
  console.log('Download CSV button: VISIBLE');

  await snap(page, '03_governance_export');
});

test('test_governance_legal_disclaimer', async ({ page }) => {
  test.setTimeout(60_000);
  await goToExecutiveNarrative(page);

  // Legal disclaimer text must contain "evidence supporting" (case-insensitive).
  const disclaimer = page.getByText(/Evidence supporting human oversight/i).first();
  await expect(disclaimer).toBeVisible({ timeout: 10_000 });
  console.log('Legal disclaimer text: VISIBLE');

  // Must NOT contain "certified" or "compliant" (banned words in the GOVERNANCE_DISCLAIMER constant).
  const certifiedEl = page.getByText(/certified/i).first();
  // Use "is compliant" to avoid matching legitimate "EU AI Act Art. 13 compliant" text.
  const compliantEl = page.getByText(/\bis compliant\b/i).first();

  const certifiedVisible = await certifiedEl.isVisible({ timeout: 2_000 }).catch(() => false);
  const compliantVisible  = await compliantEl.isVisible({ timeout: 2_000 }).catch(() => false);

  console.log(`"certified" text visible (must be false): ${certifiedVisible}`);
  console.log(`"compliant" text visible (must be false): ${compliantVisible}`);

  expect(certifiedVisible).toBe(false);
  expect(compliantVisible).toBe(false);

  await snap(page, '04_governance_disclaimer');
});
