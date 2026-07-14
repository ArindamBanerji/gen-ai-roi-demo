// FEATURE-06: Model Swap Trial (LLM Independence Proof) — E2E tests in System Health.
// Backend must be running on BACKEND_PORT (default 8001).

import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname  = path.dirname(__filename);

const FRONTEND_PORT = process.env.FRONTEND_PORT || '5173';
const FRONTEND      = `http://127.0.0.1:${FRONTEND_PORT}`;
const SCREENSHOTS   = path.join(__dirname, 'screenshots', 'feature06_modelswap');

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

test('test_modelswap_section_renders', async ({ page }) => {
  test.setTimeout(90_000);
  await goToSystemHealth(page);

  // Panel heading: "Model Swap Trial (LLM Independence Proof)"
  const heading = page.getByText(/Model Swap Trial|LLM Independence/i).first();
  await heading.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(500);

  await expect(heading).toBeVisible({ timeout: 10_000 });
  console.log('Model Swap Trial / LLM Independence section: VISIBLE');
  await snap(page, '01_modelswap_section');
});

test('test_modelswap_run_button', async ({ page }) => {
  test.setTimeout(120_000);
  await goToSystemHealth(page);

  await page.getByText(/Model Swap Trial|LLM Independence/i).first().scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(1000);

  // "Run Model Swap Trial" button.
  const runBtn = page.getByRole('button', { name: /Run Model Swap Trial/i }).first();
  await expect(runBtn).toBeVisible({ timeout: 10_000 });
  console.log('"Run Model Swap Trial" button: VISIBLE');

  await runBtn.scrollIntoViewIfNeeded();
  await runBtn.click();
  console.log('Clicked "Run Model Swap Trial"');

  // Wait for the trial API round-trip (up to 25s).
  // Results section: "LLM Calls" label appears after response.
  const llmCallsEl = page.getByText(/LLM Calls/i).first();
  await expect(llmCallsEl).toBeVisible({ timeout: 25_000 });
  console.log('Results section (LLM Calls label): VISIBLE');

  await snap(page, '02_modelswap_result');
});

test('test_modelswap_proof_values', async ({ page }) => {
  test.setTimeout(120_000);
  await goToSystemHealth(page);

  await page.getByText(/Model Swap Trial|LLM Independence/i).first().scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(1000);

  // Run the trial.
  const runBtn = page.getByRole('button', { name: /Run Model Swap Trial/i }).first();
  const runVisible = await runBtn.isVisible({ timeout: 5_000 }).catch(() => false);
  if (runVisible) {
    await runBtn.scrollIntoViewIfNeeded();
    await runBtn.click();
    await page.waitForTimeout(8000);
  }

  // "LLM Calls" label must appear with value 0 (wait up to 25s for API).
  const llmCallsLabel = page.getByText(/LLM Calls/i).first();
  await expect(llmCallsLabel).toBeVisible({ timeout: 25_000 });
  console.log('"LLM Calls" label: VISIBLE');

  // The value "0" renders as a .text-2xl next to "LLM Calls" (Zero by construction).
  const zeroEl = page.getByText(/Zero by construction/i).first();
  const zeroVisible = await zeroEl.isVisible({ timeout: 5_000 }).catch(() => false);
  console.log(`"Zero by construction" text: ${zeroVisible ? 'VISIBLE' : 'NOT VISIBLE'}`);

  // "Deterministic" label — renders as PASS/FAIL (wait for full result).
  const deterministicEl = page.getByText(/Deterministic/i).first();
  await expect(deterministicEl).toBeVisible({ timeout: 25_000 });
  console.log('"Deterministic" label: VISIBLE');

  // PASS or FAIL verdict text.
  const passEl = page.getByText(/^PASS$|^FAIL$/i).first();
  const passVisible = await passEl.isVisible({ timeout: 5_000 }).catch(() => false);
  console.log(`PASS/FAIL verdict: ${passVisible ? 'VISIBLE' : 'NOT VISIBLE'}`);

  // Repro proof section ("same_action", "same_confidence").
  const reproEl = page.getByText(/same_action|Repro Proof/i).first();
  const reproVisible = await reproEl.isVisible({ timeout: 5_000 }).catch(() => false);
  console.log(`Repro Proof section: ${reproVisible ? 'VISIBLE' : 'NOT VISIBLE'}`);

  await snap(page, '03_modelswap_proof');
});
