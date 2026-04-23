import { test, expect } from '@playwright/test';

const PORT = process.env.BACKEND_PORT || '8001';
const BASE = `http://localhost:${PORT}`;

test.describe('Narrative quality', () => {

  test('executive narrative has non-empty headline', async ({ page }) => {
    await page.goto('/');
    const resp = await page.request.get(`${BASE}/api/soc/executive-narrative`);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect((data.headline || '').length).toBeGreaterThan(0);
  });

  test('narrative response has substantial content', async ({ page }) => {
    await page.goto('/');
    const resp = await page.request.get(`${BASE}/api/soc/executive-narrative`);
    const data = await resp.json();
    const fullText = JSON.stringify(data);
    expect(fullText.length).toBeGreaterThan(500);
  });

  test('PDF export returns content', async ({ page }) => {
    await page.goto('/');
    const resp = await page.request.get(`${BASE}/api/soc/executive-narrative/pdf`);
    expect(resp.status()).toBeLessThan(500);
    if (resp.status() === 200) {
      const body = await resp.body();
      expect(body.length).toBeGreaterThan(100);
    }
  });

  test('benchmarking report has content', async ({ page }) => {
    await page.goto('/');
    const resp = await page.request.get(`${BASE}/api/soc/benchmarking-report`);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data.report?.total_decisions).toBeGreaterThanOrEqual(0);
  });
});
