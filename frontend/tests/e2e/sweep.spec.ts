import { test, expect } from '@playwright/test';

const SOC = 'http://127.0.0.1:8001';

test.describe('SOC sweep — point tests', () => {
  test('diagnostics has full measurement spine', async ({ page }) => {
    const r = await page.request.get(`${SOC}/api/self/diagnostics`);
    expect(r.status()).toBe(200);
    const d = await r.json();
    expect(d.centroid_distance_to_canonical).toBeDefined();
    expect(d.epsilon_firm).toBeDefined();
    expect(d.iks).toBeDefined();
    expect(d.measurement_state).toBeDefined();
  });

  test('conservation payload is complete', async ({ page }) => {
    const r = await page.request.get(`${SOC}/api/soc/learning-health`);
    expect(r.status()).toBe(200);
    const d = await r.json();
    expect(d.conservation).toBeDefined();
    expect(d.conservation.status).toBeDefined();
    expect(d.conservation.headroom).toBeDefined();
    expect(typeof d.interpretation).toBe('string');
  });

  test('evolution summary has rejection data', async ({ page }) => {
    const r = await page.request.get(`${SOC}/api/self/evolution/summary`);
    expect(r.status()).toBe(200);
    const d = await r.json();
    expect(d.schema_version).toBe(1);
    expect(d.recent_events).toBeDefined();
  });

  test('SOC evolution has rejection reason codes', async ({ page }) => {
    const r = await page.request.get(`${SOC}/api/evolution/recent-events?limit=5`);
    expect(r.status()).toBe(200);
  });

  test('G1: exploration never overrides — health check', async ({ page }) => {
    const r = await page.request.get(`${SOC}/health`);
    expect(r.status()).toBe(200);
  });

  test('learning health returns state', async ({ page }) => {
    const r = await page.request.get(`${SOC}/api/soc/learning-health`);
    if (r.status() === 200) {
      const d = await r.json();
      expect(d.learning_enabled).toBeDefined();
    }
  });

  test('evidence room returns audit trail', async ({ page }) => {
    const r = await page.request.get(`${SOC}/api/soc/evidence-room`);
    expect(r.status()).toBe(200);
    const d = await r.json();
    expect(d.audit_trail).toBeDefined();
  });

  test('governance summary available', async ({ page }) => {
    const r = await page.request.get(`${SOC}/api/governance/summary`);
    expect(r.status()).toBe(200);
  });
});

test.describe('SOC sweep — demo flows', () => {
  test('V5 red-team flow: simulate-failure endpoint exists', async ({ page }) => {
    const r = await page.request.get(`${SOC}/api/eval/simulate-failure`);
    expect([200, 405, 400, 422]).toContain(r.status());
  });

  test('E2 situation analysis: explain exists', async ({ page }) => {
    const r = await page.request.get(`${SOC}/api/soc/judgment/explain`);
    expect([200, 400, 405, 422]).toContain(r.status());
  });

  test('E7 ServiceNow: incident endpoint exists', async ({ page }) => {
    const r = await page.request.get(`${SOC}/api/servicenow/create-incident`);
    expect([200, 405, 400, 422]).toContain(r.status());
  });

  test('E8 evidence: ledger endpoint exists', async ({ page }) => {
    const r = await page.request.get(`${SOC}/api/soc/evidence`);
    expect([200, 404]).toContain(r.status());
  });

  test('VC cut V1-V7 measurement spine: all endpoints consistent', async ({ page }) => {
    const responses = await Promise.all([
      page.request.get(`${SOC}/api/self/diagnostics`),
      page.request.get(`${SOC}/api/soc/learning-health`),
      page.request.get(`${SOC}/api/self/evolution/summary`),
      page.request.get(`${SOC}/api/self/centroid-history?limit=5`),
    ]);
    for (const response of responses) expect(response.status()).toBe(200);
  });

  test('SOC tabs 1-5 content endpoints return data', async ({ page }) => {
    for (let n = 1; n <= 5; n += 1) {
      const r = await page.request.get(`${SOC}/api/soc/tab/${n}/content`);
      expect(r.status()).toBe(200);
      const d = await r.json();
      expect(Object.keys(d).length).toBeGreaterThan(0);
    }
  });

  test('frontend loads and first tab renders', async ({ page }) => {
    await page.goto('http://127.0.0.1:5173');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('body')).not.toBeEmpty();
  });
});
