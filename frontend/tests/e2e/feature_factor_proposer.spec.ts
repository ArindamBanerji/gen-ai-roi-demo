// Feature: Factor proposer and enrichment advisor — API contract tests.

import { test, expect } from '@playwright/test';

const BACKEND_PORT = process.env.BACKEND_PORT || '8001';
const BACKEND = `http://localhost:${BACKEND_PORT}`;

function expectArray(value: unknown, name: string) {
  expect(Array.isArray(value), `${name} must be an array`).toBe(true);
}

async function expectAvailableOrColdStart(response: import('@playwright/test').APIResponse) {
  if (response.status() === 503) {
    const data = await response.json();
    expect(data.detail?.status).toBe('cold_start');
    return null;
  }
  expect(response.status()).toBe(200);
  return response.json();
}

test('factor_analysis_returns_six_categories', async ({ page }) => {
  test.setTimeout(30_000);

  const response = await page.request.get(`${BACKEND}/api/soc/factor-analysis`);
  const data = await expectAvailableOrColdStart(response);
  if (!data) return;

  expect(typeof data.current).toBe('object');
  expectArray(data.current.categories, 'current.categories');
  expect(data.current.categories.length).toBe(6);
  const first = data.current.categories[0];
  expect(typeof first.category).toBe('string');
  expect(typeof first.snr_effective).toBe('number');
  expect(typeof first.ceiling_estimate).toBe('number');
  expect(typeof first.status).toBe('string');
});

test('factor_analysis_summary_has_proposals', async ({ page }) => {
  test.setTimeout(30_000);

  const response = await page.request.get(`${BACKEND}/api/soc/factor-analysis/summary`);
  const data = await expectAvailableOrColdStart(response);
  if (!data) return;

  expect(typeof data.overall_snr).toBe('number');
  expect(typeof data.overall_ceiling).toBe('number');
  expect(typeof data.weakest_category).toBe('string');
  expect(typeof data.recommendation).toBe('string');
  expect('bootstrap_improved' in data).toBe(true);
});

test('enrichment_advisor_ranked', async ({ page }) => {
  test.setTimeout(30_000);

  const response = await page.request.get(`${BACKEND}/api/soc/enrichment-advisor`);
  expect(response.status()).toBe(200);
  const data = await response.json();

  expectArray(data.ranked_factors, 'ranked_factors');
  expect(data.ranked_factors.length).toBe(6);
  expect(typeof data.top_opportunity).toBe('object');
  expect(data.top_opportunity.enrichment_priority).toBe(1);
  expect(typeof data.top_opportunity.factor_name).toBe('string');
  expect(typeof data.top_opportunity.expected_permanent_gap_pp).toBe('number');
  expect(typeof data.ioc_coverage).toBe('number');
  expect(typeof data.ioc_coverage_band).toBe('string');
});
