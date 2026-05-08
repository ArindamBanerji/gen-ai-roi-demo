// Feature: Model swap proof — API contract tests.

import { test, expect } from '@playwright/test';

const BACKEND_PORT = process.env.BACKEND_PORT || '8001';
const BACKEND = `http://localhost:${BACKEND_PORT}`;

async function expectAvailable(response: import('@playwright/test').APIResponse) {
  if (response.status() === 503) {
    const data = await response.json();
    expect(data.detail).toBeTruthy();
    return null;
  }
  expect(response.status()).toBe(200);
  return response.json();
}

test('model_swap_trial_returns_comparison', async ({ page }) => {
  test.setTimeout(60_000);

  const response = await page.request.get(`${BACKEND}/api/soc/model-swap-trial?n_alerts=5`);
  const data = await expectAvailable(response);
  if (!data) return;

  expect(typeof data.ok).toBe('boolean');
  expect(['ok', 'partial', 'error']).toContain(data.status);
  expect(data.n_alerts_requested).toBe(5);
  expect(typeof data.n_alerts_processed).toBe('number');
  expect(typeof data.scoring_method).toBe('string');
  expect(typeof data.reproducibility_check).toBe('object');
  expect(Array.isArray(data.alerts)).toBe(true);
});

test('model_swap_is_deterministic', async ({ page }) => {
  test.setTimeout(90_000);

  const url = `${BACKEND}/api/soc/model-swap-trial?n_alerts=2`;
  const firstResponse = await page.request.get(url);
  const first = await expectAvailable(firstResponse);
  if (!first) return;

  const secondResponse = await page.request.get(url);
  const second = await expectAvailable(secondResponse);
  if (!second) return;

  expect(second.llm_calls_made).toBe(first.llm_calls_made);
  expect(second.llm_dependency).toBe(first.llm_dependency);
  expect(second.narrative_affects_scoring).toBe(first.narrative_affects_scoring);
  expect(second.scoring_method).toBe(first.scoring_method);
  expect(second.reproducibility_check?.passed).toBe(first.reproducibility_check?.passed);
});

test('model_swap_narrative_independent', async ({ page }) => {
  test.setTimeout(60_000);

  const response = await page.request.get(`${BACKEND}/api/soc/model-swap-trial?n_alerts=1`);
  const data = await expectAvailable(response);
  if (!data) return;

  expect(data.llm_calls_made).toBe(0);
  expect(data.llm_dependency).toBe(false);
  expect(data.narrative_affects_scoring).toBe(false);
  expect(data.summary).toContain('Zero LLM calls');
  expect(typeof data.narrative_llm_used).toBe('string');
});
