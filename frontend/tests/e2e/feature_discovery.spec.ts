import { test, expect } from '@playwright/test';

const BACKEND_PORT = process.env.BACKEND_PORT || '8001';
const FRONTEND_PORT = process.env.FRONTEND_PORT || '5173';
const BACKEND = `http://localhost:${BACKEND_PORT}`;
const FRONTEND = `http://localhost:${FRONTEND_PORT}`;

function expectArray(value: unknown, name: string) {
  expect(Array.isArray(value), `${name} must be an array`).toBe(true);
}

function expectCache(value: unknown) {
  expect(value && typeof value === 'object', 'cache must be an object').toBeTruthy();
}

test('discoveries_endpoint_returns_200', async ({ page }) => {
  test.setTimeout(15_000);

  const response = await page.request.get(`${BACKEND}/api/discoveries?domain=soc`);
  expect(response.status()).toBe(200);

  const data = await response.json();
  expect(data.domain).toBe('soc');
  expectArray(data.source_domains, 'source_domains');
  expectArray(data.discoveries, 'discoveries');
  expect(typeof data.total).toBe('number');
  expectArray(data.errors, 'errors');
  expectCache(data.cache);
});

test('discoveries_summary_returns_counts', async ({ page }) => {
  test.setTimeout(15_000);

  const response = await page.request.get(`${BACKEND}/api/discoveries/summary?domain=soc`);
  expect(response.status()).toBe(200);

  const data = await response.json();
  expect(data.domain).toBe('soc');
  expect(typeof data.total).toBe('number');
  expect(typeof data.high_count).toBe('number');
  expect(typeof data.medium_count).toBe('number');
  expect(typeof data.low_count).toBe('number');
  expectArray(data.top_discoveries, 'top_discoveries');
  expectArray(data.errors, 'errors');
  expectCache(data.cache);
});

test('discoveries_refresh_returns_200', async ({ page }) => {
  test.setTimeout(15_000);

  const response = await page.request.post(`${BACKEND}/api/discoveries/refresh?domain=soc`);
  expect(response.status()).toBe(200);

  const data = await response.json();
  expect(data.domain).toBe('soc');
  expectArray(data.discoveries, 'discoveries');
  expect(typeof data.total).toBe('number');
  expectCache(data.cache);
});

test('discoveries_unsupported_domain_returns_400', async ({ page }) => {
  test.setTimeout(5_000);

  const response = await page.request.get(`${BACKEND}/api/discoveries?domain=invalid`);
  expect(response.status()).toBe(400);
});

test('discoveries_refresh_returns_valid_shape_when_empty', async ({ page }) => {
  test.setTimeout(15_000);

  const response = await page.request.post(`${BACKEND}/api/discoveries/refresh?domain=soc`);
  expect(response.status()).toBe(200);

  const data = await response.json();
  expect(typeof data.total).toBe('number');
  expect(data.total).toBeGreaterThanOrEqual(0);
  expectArray(data.discoveries, 'discoveries');
  expect(data.discoveries.length).toBe(data.total);
  expectArray(data.errors, 'errors');
  expectCache(data.cache);
});

test('discovery_items_have_required_fields', async ({ page }) => {
  test.setTimeout(15_000);

  const response = await page.request.get(`${BACKEND}/api/discoveries?domain=soc`);
  expect(response.status()).toBe(200);

  const data = await response.json();
  expectArray(data.discoveries, 'discoveries');

  if (data.discoveries.length === 0) return;

  const discovery = data.discoveries[0];
  expect(typeof discovery.discovery_id).toBe('string');
  expect(typeof discovery.type).toBe('string');
  expect(['high', 'medium', 'low']).toContain(discovery.severity);
  expect(typeof discovery.title).toBe('string');
  expect(typeof discovery.score).toBe('number');
  expect(discovery.score).toBeGreaterThanOrEqual(0);
  expect(discovery.score).toBeLessThanOrEqual(1);
  expectArray(discovery.source_domains, 'discovery.source_domains');
  expectArray(discovery.involved_entity_ids, 'discovery.involved_entity_ids');
  expectArray(discovery.involved_alert_ids, 'discovery.involved_alert_ids');
  expectArray(discovery.involved_decision_ids, 'discovery.involved_decision_ids');
  expectArray(discovery.threat_indicator_ids, 'discovery.threat_indicator_ids');
});

test('discoveries_sorted_by_score_descending', async ({ page }) => {
  test.setTimeout(15_000);

  const response = await page.request.get(`${BACKEND}/api/discoveries?domain=soc`);
  expect(response.status()).toBe(200);

  const data = await response.json();
  expectArray(data.discoveries, 'discoveries');

  for (let i = 1; i < data.discoveries.length; i += 1) {
    expect(data.discoveries[i - 1].score).toBeGreaterThanOrEqual(data.discoveries[i].score);
  }
});

test('discovery_banner_visible_in_tab3', async ({ page }) => {
  test.setTimeout(45_000);

  await page.goto(FRONTEND);
  await page.getByRole('button', { name: /Alert Triage/i }).click();

  const banner = page.getByTestId('discovery-banner');
  await expect(banner).toBeVisible();
  await expect(banner).toContainText(/Cross-Graph|Discover|Finding|No cross-graph/i);
});
