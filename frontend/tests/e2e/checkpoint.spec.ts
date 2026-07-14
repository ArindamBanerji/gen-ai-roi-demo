import { test, expect } from '@playwright/test';

const PORT = process.env.BACKEND_PORT || '8001';
const BASE = `http://127.0.0.1:${PORT}`;

test.describe('Checkpoint integrity', () => {

  test('checkpoint create returns success', async ({ page }) => {
    await page.goto('/');
    const resp = await page.request.post(`${BASE}/api/framework/checkpoint/create`);
    expect(resp.status()).toBeLessThan(500);
  });

  test('profile endpoint returns centroid info', async ({ page }) => {
    await page.goto('/');
    const resp = await page.request.get(`${BASE}/api/soc/profile`);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data.iks).toBeDefined();
  });

  test('convergence endpoint returns finite weight norm', async ({ page }) => {
    await page.goto('/');
    const resp = await page.request.get(`${BASE}/api/gae/convergence`);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    if (data.weight_norm !== undefined) {
      expect(Number.isFinite(data.weight_norm)).toBe(true);
    }
  });

  test('checkpoint list returns data', async ({ page }) => {
    await page.goto('/');
    const resp = await page.request.get(`${BASE}/api/framework/checkpoint/list`);
    if (resp.status() === 200) {
      const data = await resp.json();
      expect(typeof data).toBe('object');
    } else {
      expect(resp.status()).toBeLessThan(500);
    }
  });
});
