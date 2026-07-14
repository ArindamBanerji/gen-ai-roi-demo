// EU AI Act compliance rendering coverage for the Evidence Room tab.
// Requires the frontend and backend live stack; do not run as a build-only check.

import { test, expect } from '@playwright/test';

const FRONTEND_PORT = process.env.FRONTEND_PORT || '5173';
const FRONTEND = `http://127.0.0.1:${FRONTEND_PORT}`;

async function goToEvidenceRoom(page: import('@playwright/test').Page) {
  await page.goto(FRONTEND);
  await page.waitForLoadState('domcontentloaded');
  await page.getByRole('button', { name: /Evidence Room/i }).waitFor({ state: 'visible', timeout: 15_000 });
  await page.getByRole('button', { name: /Evidence Room/i }).click();
}

function isExpectedConsoleNoise(text: string): boolean {
  return /favicon|404|ResizeObserver/i.test(text);
}

test('governance compliance shows EU AI Act article cards', async ({ page }) => {
  test.setTimeout(60_000);

  await goToEvidenceRoom(page);

  const compliance = page
    .getByRole('heading', { name: /^Compliance$/i })
    .locator('xpath=ancestor::section[1]');

  await expect(compliance).toBeVisible({ timeout: 10_000 });
  await expect(compliance.getByText(/EU AI Act/i)).toBeVisible({ timeout: 15_000 });
  await expect(compliance.getByText(/Article 9 \/ Risk Management/i)).toBeVisible();
  await expect(compliance.getByText(/Article 15 \/ Accuracy & Robustness/i)).toBeVisible();
  await expect(compliance.getByText(/COMPLIANT|INVESTIGATION/).first()).toBeVisible();
});

test('governance compliance renders without real console errors', async ({ page }) => {
  test.setTimeout(60_000);
  const errors: string[] = [];

  page.on('console', (message) => {
    if (message.type() !== 'error') return;
    const text = message.text();
    if (!isExpectedConsoleNoise(text)) errors.push(text);
  });
  page.on('pageerror', (error) => {
    errors.push(error.message);
  });

  await goToEvidenceRoom(page);
  const compliance = page
    .getByRole('heading', { name: /^Compliance$/i })
    .locator('xpath=ancestor::section[1]');

  await expect(compliance.getByText(/EU AI Act/i)).toBeVisible({ timeout: 15_000 });
  expect(errors).toEqual([]);
});
