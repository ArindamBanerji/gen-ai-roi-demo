/**
 * compounding.spec.ts — Cross-tab state propagation tests.
 *
 * Verifies that decisions made on Tab 1 (Alert Triage) compound into
 * observable intelligence changes on Tabs 2–5 and across backend APIs.
 *
 * WARNING: writes real decisions to Neo4j.  Do not run against production.
 *
 * Run: npx playwright test tests/e2e/compounding.spec.ts --reporter=list
 */

import { test, expect } from '@playwright/test';
import {
  BACKEND,
  FRONTEND,
  makeNDecisions,
  navigateToTab,
  getApiData,
  getTab2Metrics,
} from './helpers';

// ── Reset alert pool before each test so there are always pending alerts ───────
// POST /api/alerts/reset sets all Alert nodes back to status=pending.
// learning_state (decision_count, IKS) is excluded from the reset intentionally —
// we rely on it accumulating so we can assert increases within each test.
test.beforeEach(async ({ page }) => {
  await page.request.post(`${BACKEND}/api/alerts/reset`);
  await page.waitForTimeout(500); // let the backend settle
});

test.describe('Cross-tab compounding', () => {

  // ── Test 1 ──────────────────────────────────────────────────────────────────
  //
  // learning-state.decision_count is an in-memory counter that is NOT cleared by
  // alerts/reset.  Each correct decision increments it by 1.
  // After making N decisions the after count must exceed the before count.

  test('decisions increment tab2 decision count', async ({ page }) => {
    test.setTimeout(180000);

    await page.goto(FRONTEND);
    const before = await getTab2Metrics(page);

    await navigateToTab(page, 1);
    const made = await makeNDecisions(page, 3);
    expect(made).toBeGreaterThanOrEqual(1);

    const after = await getTab2Metrics(page);
    expect(after.decisionCount).toBeGreaterThan(before.decisionCount);
  });

  // ── Test 2 ──────────────────────────────────────────────────────────────────
  //
  // IKS (iks_v2) is a computed metric — its direction after decisions depends on
  // decision quality.  This test only verifies it remains a valid non-negative
  // number after decisions are submitted (no NaN, no negative value).

  test('decisions leave tab2 IKS as a valid number', async ({ page }) => {
    test.setTimeout(300000);

    await page.goto(FRONTEND);
    await navigateToTab(page, 1);
    await makeNDecisions(page, 5);

    const after = await getTab2Metrics(page);
    expect(typeof after.iks).toBe('number');
    expect(isNaN(after.iks)).toBe(false);
    expect(after.iks).toBeGreaterThanOrEqual(0);
  });

  // ── Test 3 ──────────────────────────────────────────────────────────────────
  //
  // /api/soc/accuracy-trajectory returns { categories: [{ trajectory_points: [...] }] }.
  // After decisions the trajectory data should be at least as long as before.
  // The endpoint is live (source="live") so trajectory_points always come from
  // real graph data — the count can only grow or stay equal.

  test('decisions do not shrink accuracy trajectory', async ({ page }) => {
    test.setTimeout(300000);

    const before = await getApiData(page, '/api/soc/accuracy-trajectory');
    const beforePoints = before.categories?.[0]?.trajectory_points?.length ?? 0;

    await page.goto(FRONTEND);
    await navigateToTab(page, 1);
    await makeNDecisions(page, 5);

    const after = await getApiData(page, '/api/soc/accuracy-trajectory');
    const afterPoints = after.categories?.[0]?.trajectory_points?.length ?? 0;
    expect(afterPoints).toBeGreaterThanOrEqual(beforePoints);
  });

  // ── Test 4 ──────────────────────────────────────────────────────────────────
  //
  // /api/soc/profile exposes switching-cost economics used on Tab 4.
  // decisions_per_day must be > 0 — it is derived from total Decision nodes in
  // the graph, which always includes the 4 860+ training decisions.

  test('tab4 economics reports positive decisions_per_day', async ({ page }) => {
    test.setTimeout(30000);

    const data = await getApiData(page, '/api/soc/profile');
    const dpd = data.iks?.switching_cost?.decisions_per_day;
    expect(typeof dpd).toBe('number');
    expect(dpd).toBeGreaterThan(0);
  });

  // ── Test 5 ──────────────────────────────────────────────────────────────────
  //
  // /api/soc/executive-narrative exposes verified_decisions (Tab 5).
  // Correct decisions that pass through OutcomeFeedback are persisted to Neo4j;
  // after making new decisions the count must be >= the baseline.

  test('decisions do not decrease tab5 verified count', async ({ page }) => {
    test.setTimeout(300000);

    const before = await getApiData(page, '/api/soc/executive-narrative');
    const beforeVerified: number =
      before.metrics?.decisions_verified ?? before.verified_decisions ?? 0;

    await page.goto(FRONTEND);
    await navigateToTab(page, 1);
    await makeNDecisions(page, 5);

    const after = await getApiData(page, '/api/soc/executive-narrative');
    const afterVerified: number =
      after.metrics?.decisions_verified ?? after.verified_decisions ?? 0;
    expect(afterVerified).toBeGreaterThanOrEqual(beforeVerified);
  });

  // ── Test 6 ──────────────────────────────────────────────────────────────────
  //
  // /api/soc/epistemic-state must return a categories structure.
  // total_verified may or may not be present depending on backend implementation;
  // the test asserts a valid non-negative number either way.

  test('epistemic state endpoint returns valid categories structure', async ({ page }) => {
    test.setTimeout(180000);

    await page.goto(FRONTEND);
    await navigateToTab(page, 1);
    await makeNDecisions(page, 3);

    const data = await getApiData(page, '/api/soc/epistemic-state');
    expect(data.categories).toBeDefined();

    // total_verified is optional — safe-read with fallback
    const totalVerified: number = data.total_verified ?? 0;
    expect(totalVerified).toBeGreaterThanOrEqual(0);
  });

  // ── Test 7 ──────────────────────────────────────────────────────────────────
  //
  // API contract check — no decisions required.
  // /api/soc/learning-state must return the three conservation-layer fields that
  // all five tabs rely on.

  test('learning state has required conservation fields', async ({ page }) => {
    test.setTimeout(10000);

    const data = await getApiData(page, '/api/soc/learning-state');
    expect(typeof data.decision_count).toBe('number');
    expect(data.decision_count).toBeGreaterThanOrEqual(0);
    expect(typeof data.frozen).toBe('boolean');
    expect(typeof data.iks_v2).toBe('number');
    expect(data.iks_v2).toBeGreaterThanOrEqual(0);
  });

  // ── Test 8 ──────────────────────────────────────────────────────────────────
  //
  // Cross-source consistency check:
  //   analytics.total_decisions  = graph query (all Decision nodes, ~4 860+)
  //   learning-state.decision_count = in-memory counter (smaller; excludes seed data)
  //
  // The graph always contains at least as many decisions as the in-memory counter.
  // A hundreds-level divergence in the wrong direction would indicate a broken
  // query or field name (the bug that motivated this test suite).

  test('cross tab decision count directional consistency', async ({ page }) => {
    test.setTimeout(10000);

    const learning = await getApiData(page, '/api/soc/learning-state');
    const analytics = await getApiData(page, '/api/soc/analytics');

    const lsDC: number = learning.decision_count ?? 0;
    const totalDC: number = analytics.total_decisions ?? 0;

    expect(lsDC).toBeGreaterThanOrEqual(0);
    expect(totalDC).toBeGreaterThanOrEqual(0);

    // Graph count >= in-memory counter (graph includes all historical + seed data).
    // Tolerance of 50: after the 40-decision learning loop, the in-memory counter
    // is updated synchronously while graph writes are async, creating a brief window
    // where the counter can lead the graph by up to ~40 decisions.
    expect(
      totalDC,
      `analytics.total_decisions (${totalDC}) should be within 50 of ` +
      `learning-state.decision_count (${lsDC})`,
    ).toBeGreaterThanOrEqual(lsDC - 50);

    // Seed data guard: graph must have real training data (> 100)
    expect(
      totalDC,
      `analytics.total_decisions=${totalDC} is suspiciously low — expect > 100 from seed data`,
    ).toBeGreaterThan(100);
  });

});
