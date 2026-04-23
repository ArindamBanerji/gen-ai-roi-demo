import { test, expect } from '@playwright/test';

const PORT = process.env.BACKEND_PORT || '8001';
const BASE = `http://localhost:${PORT}`;

test.describe('Campaign and threat intel', () => {

  test('campaigns endpoint returns valid data', async ({ page }) => {
    await page.goto('/');
    const resp = await page.request.get(`${BASE}/api/soc/campaigns`);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data.total).toBeGreaterThanOrEqual(0);
  });

  test('threat landscape has real node count', async ({ page }) => {
    await page.goto('/');
    const resp = await page.request.get(`${BASE}/api/soc/threat-landscape`);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data.graph_coverage?.nodes).toBeGreaterThan(100);
  });

  test('attack tactic breakdown is non-empty', async ({ page }) => {
    await page.goto('/');
    const resp = await page.request.get(`${BASE}/api/soc/attack-tactic-breakdown`);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    const breakdown = data.breakdown || data;
    const len = Array.isArray(breakdown) ? breakdown.length : Object.keys(breakdown).length;
    expect(len).toBeGreaterThan(0);
  });

  test('detection engineering has 6 categories', async ({ page }) => {
    await page.goto('/');
    const resp = await page.request.get(`${BASE}/api/soc/detection-engineering`);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data.category_scores).toBeDefined();
    const keys = Object.keys(data.category_scores || {});
    expect(keys.length).toBe(6);
  });
});
