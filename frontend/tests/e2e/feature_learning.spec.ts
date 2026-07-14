// Feature: Learning telemetry — API contract tests.

import { test, expect } from '@playwright/test';

const BACKEND_PORT = process.env.BACKEND_PORT || '8001';
const BACKEND = `http://127.0.0.1:${BACKEND_PORT}`;

function expectArray(value: unknown, name: string) {
  expect(Array.isArray(value), `${name} must be an array`).toBe(true);
}

test('learning_state_loads', async ({ page }) => {
  test.setTimeout(30_000);

  const response = await page.request.get(`${BACKEND}/api/soc/learning-state`);
  expect(response.status()).toBe(200);
  const data = await response.json();

  expect(typeof data.frozen).toBe('boolean');
  expect(typeof data.decision_count).toBe('number');
  expect(typeof data.verified_decisions).toBe('number');
  expect(typeof data.iks_v2).toBe('number');
  expect(typeof data.iks_components).toBe('object');
  expect(typeof data.bootstrap_category_weights).toBe('object');
});

test('centroid_evolution_returns_data', async ({ page }) => {
  test.setTimeout(30_000);

  const response = await page.request.get(`${BACKEND}/api/soc/centroid-evolution?n=50`);
  expect(response.status()).toBe(200);
  const data = await response.json();

  expectArray(data, 'centroid evolution');
  if (data.length > 0) {
    const first = data[0];
    expect(typeof first.decision_number).toBe('number');
    expect(typeof first.centroid_delta_norm).toBe('number');
    expect(typeof first.category).toBe('string');
    expect(typeof first.action).toBe('string');
    expect(typeof first.drift_type).toBe('string');
  }
});

test('confidence_trajectory_has_history', async ({ page }) => {
  test.setTimeout(30_000);

  const response = await page.request.get(`${BACKEND}/api/gae/confidence-trajectory`);
  expect(response.status()).toBe(200);
  const data = await response.json();

  expect(typeof data.trajectories).toBe('object');
  expect('message' in data).toBe(true);
  for (const entries of Object.values(data.trajectories)) {
    expectArray(entries, 'trajectory entries');
    if ((entries as unknown[]).length > 0) {
      const first = (entries as any[])[0];
      expect(typeof first.decision_number).toBe('number');
      expect(typeof first.confidence).toBe('number');
      expect(typeof first.action).toBe('string');
    }
  }
});

test('learning_balance_sheet_has_categories', async ({ page }) => {
  test.setTimeout(30_000);

  const response = await page.request.get(`${BACKEND}/api/soc/learning-balance-sheet`);
  expect(response.status()).toBe(200);
  const data = await response.json();

  expectArray(data.categories, 'categories');
  expect(data.categories.length).toBeGreaterThan(0);
  const first = data.categories[0];
  expect(typeof first.category).toBe('string');
  expect(typeof first.epistemic_band).toBe('string');
  expect(typeof first.verified_count).toBe('number');
  expect(typeof first.status).toBe('string');
  expect(typeof data.summary).toBe('object');
  expect(typeof data.health_status).toBe('string');
});
