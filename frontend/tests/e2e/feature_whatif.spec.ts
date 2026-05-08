// Feature: What-If projections — API contract tests.

import { test, expect } from '@playwright/test';

const BACKEND_PORT = process.env.BACKEND_PORT || '8001';
const BACKEND = `http://localhost:${BACKEND_PORT}`;

function expectArray(value: unknown, name: string) {
  expect(Array.isArray(value), `${name} must be an array`).toBe(true);
}

const customScenario = {
  name: 'playwright_custom',
  description: 'Short deterministic projection for E2E contract coverage.',
  alpha: 0.25,
  V: 200.0,
  q_initial: 0.8,
  q_target: 0.8,
  q_ramp_days: 0,
  horizon_days: 3,
  disruption_day: null,
  disruption_delta: 0.0,
  eta: 0.05,
  n_half: 14.0,
  t_max_days: 21.0,
  iks_initial: 50.0,
  iks_gain_green: 0.8,
  iks_gain_amber: 0.3,
  iks_gain_red: -0.2,
};

test('whatif_presets_available', async ({ page }) => {
  test.setTimeout(30_000);

  const response = await page.request.get(`${BACKEND}/api/whatif/presets`);
  expect(response.status()).toBe(200);
  const data = await response.json();

  expect(typeof data.count).toBe('number');
  expect(data.count).toBeGreaterThanOrEqual(3);
  expect(typeof data.presets).toBe('object');
  expect(Object.keys(data.presets)).toContain('healthy_deployment');
});

test('whatif_preset_healthy_returns_green', async ({ page }) => {
  test.setTimeout(30_000);

  const response = await page.request.get(`${BACKEND}/api/whatif/presets/healthy_deployment`);
  expect(response.status()).toBe(200);
  const data = await response.json();

  expectArray(data.daily_trajectory, 'daily_trajectory');
  expect(data.daily_trajectory.length).toBeGreaterThan(0);
  expect(data.summary.final_status).toBe('GREEN');
  expect(typeof data.summary.days_green).toBe('number');
  expect(typeof data.iks_estimate).toBe('number');
});

test('whatif_project_custom_scenario', async ({ page }) => {
  test.setTimeout(30_000);

  const response = await page.request.post(`${BACKEND}/api/whatif/project`, {
    data: customScenario,
  });
  expect(response.status()).toBe(200);
  const data = await response.json();

  expect(data.scenario.name).toBe('playwright_custom');
  expectArray(data.daily_trajectory, 'daily_trajectory');
  expect(data.daily_trajectory.length).toBe(3);
  expect(typeof data.summary.final_status).toBe('string');
  expectArray(data.warnings, 'warnings');
});

test('whatif_projection_has_conservation', async ({ page }) => {
  test.setTimeout(30_000);

  const response = await page.request.post(`${BACKEND}/api/whatif/project`, {
    data: customScenario,
  });
  expect(response.status()).toBe(200);
  const data = await response.json();

  expect(typeof data.conservation_law).toBe('object');
  expect(typeof data.conservation_law.theta_min).toBe('number');
  expect(typeof data.conservation_law.formula).toBe('string');
  const first = data.daily_trajectory[0];
  expect(typeof first.day).toBe('number');
  expect(typeof first.q).toBe('number');
  expect(typeof first.signal).toBe('number');
  expect(typeof first.status).toBe('string');
  expect(typeof first.passed).toBe('boolean');
});
