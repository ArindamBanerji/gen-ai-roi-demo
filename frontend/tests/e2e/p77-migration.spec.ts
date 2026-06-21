/**
 * p77-migration.spec.ts — SOC scorer migration E2E gates.
 *
 * Verifies that the ProfileScorer -> CompoundingScorer adapter migration is
 * invisible to users: tabs still render, score/outcome APIs retain their JSON
 * shape, conservation/trust endpoints remain reachable, and tab navigation does
 * not emit browser console errors.
 *
 * Run: npx playwright test tests/e2e/p77-migration.spec.ts --reporter=list
 */

import { test, expect, type APIResponse, type Page } from '@playwright/test';
import { BACKEND, FRONTEND, navigateToTab, resetDemoAlerts } from './helpers';

const VALID_ACTIONS = ['escalate', 'investigate', 'suppress', 'monitor', 'refer_to_analyst'];

const TABS = [
  {
    label: 'SOC Analytics',
    tabNumber: 3,
    bodyPattern: /SOC Analytics|Threat Landscape|Detection Engineering|Graph Explorer/i,
  },
  {
    label: 'Runtime Evolution',
    tabNumber: 2,
    bodyPattern: /Runtime Evolution|Institutional Knowledge Score|Learning State|System Health/i,
  },
  {
    label: 'Alert Triage',
    tabNumber: 1,
    bodyPattern: /Alert Triage|Alert Queue|Active decisions|Recommendation/i,
  },
  {
    label: 'Compounding',
    roleName: /Compounding|Decision Economics/i,
    bodyPattern: /Compounding|Decision Economics|Simulation|ROI/i,
  },
  {
    label: 'Executive Narrative',
    tabNumber: 5,
    bodyPattern: /Executive Narrative|What Changed|What Was Discovered|Evidence Ledger/i,
  },
  {
    label: 'Evidence Room',
    roleName: /Evidence Room/i,
    bodyPattern: /Evidence Room|Audit Trail|Conservation & Health|Compliance/i,
  },
] as const;

test.beforeEach(async ({ page }) => {
  await resetDemoAlerts(page);
  await page.waitForTimeout(500);
});

async function gotoTab(page: Page, tab: (typeof TABS)[number]) {
  await page.goto(FRONTEND);
  if ('tabNumber' in tab) {
    await navigateToTab(page, tab.tabNumber);
  } else {
    await page.getByRole('button', { name: tab.roleName }).click();
  }
}

async function expectTabVisible(page: Page, tab: (typeof TABS)[number]) {
  await expect(page.locator('body')).toContainText(tab.bodyPattern, { timeout: 20_000 });
  await expect(page.locator('body')).toBeVisible();
}

async function getJson(page: Page, endpoint: string): Promise<any> {
  const response = await page.request.get(`${BACKEND}${endpoint}`);
  expect(response.status(), `${endpoint} returned ${response.status()}`).toBeLessThan(500);
  expect(response.ok(), `${endpoint} must return 2xx`).toBeTruthy();
  return response.json();
}

async function postJson(page: Page, endpoint: string, payload: Record<string, unknown>): Promise<any> {
  const response = await page.request.post(`${BACKEND}${endpoint}`, { data: payload });
  expect(response.status(), `${endpoint} returned ${response.status()}`).toBeLessThan(500);
  expect(response.ok(), `${endpoint} must return 2xx`).toBeTruthy();
  return response.json();
}

async function firstSuccessfulGet(page: Page, endpoints: string[]): Promise<{ endpoint: string; response: APIResponse } | null> {
  for (const endpoint of endpoints) {
    const response = await page.request.get(`${BACKEND}${endpoint}`);
    if (response.status() === 404) {
      continue;
    }
    expect(response.status(), `${endpoint} returned ${response.status()}`).toBeLessThan(500);
    expect(response.ok(), `${endpoint} must return 2xx when present`).toBeTruthy();
    return { endpoint, response };
  }
  return null;
}

async function getFirstAlertId(page: Page): Promise<string> {
  const queue = await getJson(page, '/api/alerts/queue');
  const alerts = Array.isArray(queue.alerts) ? queue.alerts : [];
  expect(alerts.length, 'reset alert queue should expose pending demo alerts').toBeGreaterThan(0);
  const alertId = alerts[0]?.id ?? alerts[0]?.alert_id;
  expect(typeof alertId).toBe('string');
  return alertId;
}

test.describe('P77 migration UI continuity', () => {
  test('SOC Analytics tab loads after migration', async ({ page }) => {
    await gotoTab(page, TABS[0]);
    await expectTabVisible(page, TABS[0]);
  });

  test('Runtime Evolution tab loads after migration', async ({ page }) => {
    await gotoTab(page, TABS[1]);
    await expectTabVisible(page, TABS[1]);
    await expect(page.locator('body')).toContainText(/Agent|Evolution|Learning|IKS/i);
  });

  test('Alert Triage tab loads after migration', async ({ page }) => {
    await gotoTab(page, TABS[2]);
    await expectTabVisible(page, TABS[2]);
    await expect(page.locator('button').filter({ hasText: /ALERT-|SIM-/i }).first()).toBeVisible({ timeout: 20_000 });
  });

  test('Compounding tab loads after migration', async ({ page }) => {
    await gotoTab(page, TABS[3]);
    await expectTabVisible(page, TABS[3]);
  });

  test('Executive Narrative tab loads after migration', async ({ page }) => {
    await gotoTab(page, TABS[4]);
    await expectTabVisible(page, TABS[4]);
  });

  test('Evidence Room tab loads after migration', async ({ page }) => {
    await gotoTab(page, TABS[5]);
    await expectTabVisible(page, TABS[5]);
  });

  test('no console errors on tab navigation', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (message) => {
      if (message.type() === 'error') {
        errors.push(message.text());
      }
    });

    for (const tab of TABS) {
      await gotoTab(page, tab);
      await expectTabVisible(page, tab);
    }

    const unexpected = errors.filter((message) => !/favicon|ResizeObserver|Failed to load|Failed to fetch/i.test(message));
    expect(unexpected).toEqual([]);
  });

  test('all tabs reachable via click', async ({ page }) => {
    await page.goto(FRONTEND);
    for (const tab of TABS) {
      if ('tabNumber' in tab) {
        await navigateToTab(page, tab.tabNumber);
      } else {
        await page.getByRole('button', { name: tab.roleName }).click();
      }
      await expectTabVisible(page, tab);
    }
  });
});

test.describe('P77 migration API shape', () => {
  test('analyze endpoint returns valid response', async ({ page }) => {
    const alertId = await getFirstAlertId(page);
    const data = await postJson(page, '/api/alert/analyze', { alert_id: alertId });

    const recommendedAction = data.recommended_action ?? data.recommendation?.action;
    const confidence = data.confidence ?? data.recommendation?.confidence;
    const factorVector = data.factor_vector ?? data.gae_scoring?.factor_vector;
    const category = data.category ?? data.alert?.category ?? data.situation_analysis?.situation_type;

    expect(VALID_ACTIONS).toContain(recommendedAction);
    expect(typeof confidence).toBe('number');
    expect(confidence).toBeGreaterThanOrEqual(0);
    expect(confidence).toBeLessThanOrEqual(1);
    expect(Array.isArray(factorVector)).toBe(true);
    expect(factorVector.length).toBe(6);
    expect(typeof category).toBe('string');
    expect(category.length).toBeGreaterThan(0);
  });

  test('outcome recording accepts an adapter-scored decision', async ({ page }) => {
    const alertId = await getFirstAlertId(page);
    const analysis = await postJson(page, '/api/alert/analyze', { alert_id: alertId });
    const decisionId = analysis.recommendation?.decision_id ?? analysis.gae_scoring?.decision_id;
    const action = analysis.recommendation?.action ?? 'investigate';

    expect(typeof decisionId).toBe('string');
    const outcome = await postJson(page, '/api/alert/outcome', {
      alert_id: alertId,
      decision_id: decisionId,
      outcome: 'correct',
      analyst_action: action,
    });

    expect(outcome).toBeTruthy();
    expect(Array.isArray(outcome.graph_updates ?? [])).toBe(true);
  });

  test('profile endpoint returns scorer data', async ({ page }) => {
    const data = await getJson(page, '/api/soc/profile');
    expect(Array.isArray(data.actions)).toBe(true);
    expect(Array.isArray(data.categories)).toBe(true);
    expect(Array.isArray(data.centroids)).toBe(true);
    expect(Array.isArray(data.counts)).toBe(true);
    expect(data.categories.length).toBe(6);
    expect(data.actions.length).toBe(4);
  });

  test('conservation status endpoint returns data', async ({ page }) => {
    const found = await firstSuccessfulGet(page, [
      '/api/conservation/status',
      '/api/soc/learning-health',
      '/api/soc/learning-state',
    ]);
    expect(found, 'expected a conservation or learning-state endpoint').not.toBeNull();

    const data = await found!.response.json();
    const status = data.status ?? data.conservation?.status ?? (data.frozen ? 'FROZEN' : 'ACTIVE');
    expect(typeof status).toBe('string');

    const components = data.components ?? data.conservation ?? {};
    if ('alpha' in components) expect(typeof components.alpha).toBe('number');
    if ('q' in components) expect(typeof components.q).toBe('number');
  });

  test('health endpoint returns healthy', async ({ page }) => {
    const response = await page.request.get(`${BACKEND}/health`);
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data.status).toMatch(/healthy|operational/i);
  });

  test('fingerprint endpoint returns factor data', async ({ page }) => {
    const found = await firstSuccessfulGet(page, [
      '/api/fingerprint',
      '/api/soc/factor-analysis/summary',
      '/api/soc/factor-analysis',
    ]);
    test.skip(found === null, 'No fingerprint/factor-analysis endpoint is present in this build.');

    const data = await found!.response.json();
    const text = JSON.stringify(data);
    expect(text).toMatch(/factor|privileged|asset|threat|pattern|device/i);
  });

  test('trajectory endpoint returns data', async ({ page }) => {
    const found = await firstSuccessfulGet(page, [
      '/api/trajectory',
      '/api/soc/accuracy-trajectory',
      '/api/metrics/confidence-trajectory',
    ]);
    test.skip(found === null, 'No trajectory endpoint is present in this build.');

    const data = await found!.response.json();
    expect(JSON.stringify(data)).toMatch(/trajectory|categories|points|source/i);
  });

  test('accuracy endpoint returns category data', async ({ page }) => {
    const found = await firstSuccessfulGet(page, [
      '/api/self/accuracy-by-category',
      '/api/soc/accuracy-trajectory',
    ]);
    test.skip(found === null, 'No accuracy-by-category endpoint is present in this build.');

    const data = await found!.response.json();
    const categories = data.categories ?? data.accuracy_by_category ?? data;
    expect(Array.isArray(categories) || typeof categories === 'object').toBe(true);
  });
});
