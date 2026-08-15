/**
 * conservation.spec.ts — Conservation law E2E tests.
 *
 * Verifies that the three conservation invariants hold end-to-end:
 *   1. learning_state fields are always present and valid.
 *   2. Conservation narrative (Evidence Ledger, EU AI Act) renders on Tab 5.
 *   3. The frozen/active badge on Tab 2 matches the API's frozen field.
 *   4. Epistemic state bands are always one of the four defined values.
 *   5. Accuracy trajectory always has 6 live categories.
 *
 * No real decisions are made in tests 1, 3, 4, 5 — they are pure API/DOM
 * contract checks.  Test 2 navigates to Tab 5 but does not make decisions.
 *
 * Run: npx playwright test tests/e2e/conservation.spec.ts --reporter=list
 */

import { test, expect } from '@playwright/test';
import {
  BACKEND,
  FRONTEND,
  navigateToTab,
  getApiData,
} from './helpers';

// ── Reset before each test for consistent alert-pool state ───────────────────
test.beforeEach(async ({ page }) => {
  await page.request.post(`${BACKEND}/api/alerts/reset`);
  await page.waitForTimeout(500);
});

test.describe('Conservation law E2E', () => {

  // ── Test 1 ──────────────────────────────────────────────────────────────────
  //
  // Pure API contract: /api/soc/learning-state must always return the three
  // conservation-layer fields that every tab depends on.
  // Mirrors compounding.spec.ts test 7 — repeated here as a standalone gate.

  test('learning state has conservation fields', async ({ page }) => {
    test.setTimeout(10000);

    const data = await getApiData(page, '/api/soc/learning-state');

    expect(typeof data.decision_count).toBe('number');
    expect(data.decision_count).toBeGreaterThanOrEqual(0);

    expect(typeof data.frozen).toBe('boolean');

    expect(typeof data.iks_v2).toBe('number');
    expect(data.iks_v2).toBeGreaterThanOrEqual(0);
    expect(Number.isFinite(data.iks_v2)).toBe(true);
  });

  test('learning health exposes the live conservation provider', async ({ page }) => {
    test.setTimeout(10000);
    const health = await getApiData(page, '/api/soc/learning-health');
    expect(health.status).toMatch(/GREEN|AMBER|RED|CALIBRATING|UNKNOWN/);
    expect(health.provider_source).toBeTruthy();
    expect(health.provider_source).not.toBe('literal');
    expect(typeof health.overallSafe).toBe('boolean');
    expect(health.overallSafe).toBe(health.status === 'GREEN');
  });

  // ── Test 2 ──────────────────────────────────────────────────────────────────
  //
  // Conservation narrative visible in Tab 5 DOM.
  // BACKLOG-017 fix: conservation_narrative is rendered under the
  // "Conservation & Audit Status" label in ExecutiveNarrativeTab.tsx.
  //
  // Asserts:
  //   • "Evidence Ledger" appears in the Tab 5 body text.
  //   • "Conservation" appears in the Tab 5 body text.
  //   • The executive-narrative API returns a non-empty headline.

  test('conservation narrative in tab5 DOM', async ({ page }) => {
    test.setTimeout(30000);

    await page.goto(FRONTEND);
    await navigateToTab(page, 5);

    // Wait for the narrative sections to load
    await page.getByRole('heading', { name: /What Changed/i }).waitFor({
      state: 'visible',
      timeout: 15000,
    });

    const bodyText = await page.locator('body').textContent() ?? '';
    expect(bodyText).toContain('Evidence Ledger');
    expect(bodyText).toContain('Conservation');

    // API contract: headline must be non-empty
    const apiData = await getApiData(page, '/api/soc/executive-narrative');
    expect(typeof apiData.headline).toBe('string');
    expect(apiData.headline.trim().length).toBeGreaterThan(0);
  });

  // ── Test 3 ──────────────────────────────────────────────────────────────────
  //
  // Frozen badge on Tab 2 matches learning_state.frozen from the API.
  //
  // When data.frozen === true  → a "frozen" badge must be visible on Tab 2.
  // When data.frozen === false → an "active" or "learning" badge must be visible.
  //
  // Uses the selector pattern from checklist.spec.ts
  // "override learning status: frozen badge OR active badge visible".

  test('frozen badge matches API state', async ({ page }) => {
    test.setTimeout(20000);

    // Read the authoritative frozen state from the API
    const data = await getApiData(page, '/api/soc/learning-state');
    const isFrozen: boolean = data.frozen;
    expect(typeof isFrozen).toBe('boolean');

    // Navigate to Tab 2 where the badge is rendered
    await page.goto(FRONTEND);
    await navigateToTab(page, 2);
    await page.getByText(/Institutional Knowledge Score/i).waitFor({
      state: 'visible',
      timeout: 15000,
    });

    // The badge text must match the API state
    const badgePattern = isFrozen ? /frozen/i : /active|learning/i;
    const badge = page.getByText(badgePattern).first();
    await expect(badge).toBeVisible({ timeout: 10000 });
  });

  // ── Test 4 ──────────────────────────────────────────────────────────────────
  //
  // /api/soc/epistemic-state returns per-category counts and knowledge bands.
  //
  // Band thresholds (from soc.py source):
  //   novice      < 50 verified decisions
  //   learning    50–199
  //   calibrating 200–499
  //   expert      500+
  //
  // Every category returned must have:
  //   • count: a non-negative integer
  //   • band: one of the four defined band strings

  test('epistemic state bands are valid', async ({ page }) => {
    test.setTimeout(10000);

    const data = await getApiData(page, '/api/soc/epistemic-state');

    expect(data.categories).toBeDefined();
    expect(typeof data.total_verified).toBe('number');
    expect(data.total_verified).toBeGreaterThanOrEqual(0);

    const validBands = ['novice', 'learning', 'calibrating', 'expert'];

    for (const [cat, info] of Object.entries(data.categories ?? {})) {
      const catInfo = info as { count: number; band: string };

      expect(
        typeof catInfo.count,
        `Category "${cat}" count is not a number`,
      ).toBe('number');
      expect(
        catInfo.count,
        `Category "${cat}" count is negative`,
      ).toBeGreaterThanOrEqual(0);

      expect(
        validBands,
        `Category "${cat}" band "${catInfo.band}" is not a valid band`,
      ).toContain(catInfo.band);
    }
  });

  // ── Test 5 ──────────────────────────────────────────────────────────────────
  //
  // /api/soc/accuracy-trajectory must always return 6 live categories.
  // source = "live" means the data comes from real graph queries, not
  // a fallback stub.  This is the same check as checklist.spec.ts Phase B,
  // repeated here as a conservation-law gate.

  test('accuracy trajectory has 6 live categories', async ({ page }) => {
    test.setTimeout(10000);

    const data = await getApiData(page, '/api/soc/accuracy-trajectory');

    expect(data.categories).toBeDefined();
    expect(
      data.categories.length,
      `Expected 6 accuracy-trajectory categories, got ${data.categories.length}`,
    ).toBe(6);

    expect(
      data.source,
      `Expected source="live" but got "${data.source}" — trajectory is using a fallback stub`,
    ).toBe('live');

    // Each category must have at least one trajectory data point
    for (const cat of data.categories) {
      expect(
        Array.isArray(cat.trajectory_points),
        `Category "${cat.category ?? cat.name}" missing trajectory_points array`,
      ).toBe(true);
      expect(cat.trajectory_points.length).toBeGreaterThan(0);
    }
  });

});
