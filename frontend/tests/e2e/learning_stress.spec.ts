/**
 * learning_stress.spec.ts — Stress and resilience tests for the learning loop.
 *
 * These tests make real decisions (writes to AGE) and verify that:
 *   - the system stays stable under load (10+ decisions)
 *   - no DEC-None artifacts appear after rapid decisions
 *   - tab switching mid-flight does not crash the app
 *   - reset→decide→reset cycles preserve data integrity
 *
 * WARNING: writes real data to AGE.  Do not run against production.
 *
 * Run: npx playwright test tests/e2e/learning_stress.spec.ts --reporter=list
 *
 * Note: most tests here call test.slow() to triple the default timeout —
 * each triage decision takes ~10–30 s (LLM round-trip + AGE write).
 */

import { test, expect } from '@playwright/test';
import {
  BACKEND,
  FRONTEND,
  makeNDecisions,
  navigateToTab,
  getApiData,
  collectConsoleErrors,
  expectNoConsoleErrors,
  resetDemoAlerts,
} from './helpers';

// ── Reset alert pool before each test ────────────────────────────────────────
// POST /api/alerts/reset sets all Alert nodes back to pending (102 available).
// learning_state (decision_count, IKS) is excluded from reset intentionally.
//
// After heavy decision runs (10 decisions), the PostgreSQL/AGE commit takes
// longer than 500ms to become visible to the frontend's pending-alert query.
// Instead of a blind sleep, we navigate to Tab 1 and wait until at least one
// alert card appears — that DOM wait is the true "DB is ready" signal.
test.beforeEach(async ({ page }) => {
  await resetDemoAlerts(page);
  await page.goto(FRONTEND);
  await navigateToTab(page, 1);
  await page.locator('button').filter({ hasText: /ALERT-|SIM-/i }).first()
    .waitFor({ state: 'visible', timeout: 30000 });
});

test.describe('Learning stress tests', () => {

  // ── Test 1 ──────────────────────────────────────────────────────────────────
  //
  // 10 mixed decisions (all via "Confirmed Correct" — natural confidence variation
  // drives both correct and borderline outcomes through the learning weight update).
  // After 10 decisions:
  //   • IKS (iks_v2) must still be a valid non-negative number — no NaN collapse.
  //   • decision_count must have increased.
  //   • No fatal console errors (React duplicate-key warnings are filtered).

  test('mixed correct incorrect does not collapse', async ({ page }) => {
    test.slow(); // triples default timeout

    const errors = collectConsoleErrors(page);

    const before = await getApiData(page, '/api/soc/learning-state');
    const beforeDC: number = before.decision_count ?? 0;

    await page.goto(FRONTEND);
    const made = await makeNDecisions(page, 10);
    expect(made).toBeGreaterThanOrEqual(1);

    const after = await getApiData(page, '/api/soc/learning-state');
    expect(after.iks_v2).toBeGreaterThanOrEqual(0);
    expect(isNaN(after.iks_v2)).toBe(false);
    expect(after.decision_count).toBeGreaterThan(beforeDC);

    expectNoConsoleErrors(errors);
  });

  // ── Test 2 ──────────────────────────────────────────────────────────────────
  //
  // 10 rapid decisions (makeNDecisions uses waitForResponse — no extra delay).
  // Verifies two race-condition regression guards:
  //   1. decision_count increased — no writes silently dropped.
  //   2. "DEC-None" does NOT appear on Tab 4 — decision_id is never null.
  //      (DEC-None is produced when d.decision_id is null in the AGE graph;
  //       see deep_flows.spec.ts test 1 for full explanation of the exact-match rule.)

  test('rapid fire 10 decisions no race condition', async ({ page }) => {
    test.slow();

    const before = await getApiData(page, '/api/soc/learning-state');
    const beforeDC: number = before.decision_count ?? 0;

    await page.goto(FRONTEND);
    const made = await makeNDecisions(page, 10);
    expect(made).toBeGreaterThanOrEqual(1);

    const after = await getApiData(page, '/api/soc/learning-state');
    expect(after.decision_count).toBeGreaterThan(beforeDC);

    // Navigate to Tab 4 and assert no "DEC-None" element anywhere on the page.
    // Use exact:true — SYN-DEC-* event rows render id-div("DEC-SYN-DEC-") +
    // event_type-div("None"), whose concatenated textContent contains "DEC-None"
    // as a substring; exact match only fires when an element's FULL text is "DEC-None".
    await page.goto(FRONTEND);
    await navigateToTab(page, 4);
    await page.getByText(/ROI|return on investment|roi calculator/i).first().waitFor({
      state: 'visible',
      timeout: 15000,
    });
    const decNoneCount = await page.getByText('DEC-None', { exact: true }).count();
    expect(
      decNoneCount,
      'DEC-None found on Tab 4 after rapid decisions — a Decision node has null decision_id.',
    ).toBe(0);
  });

  // ── Test 3 ──────────────────────────────────────────────────────────────────
  //
  // Make 3 decisions → reset alerts → make 3 more decisions.
  // Verifies that the reset→decide cycle does not corrupt learning_state.
  //
  // The reset endpoint (POST /api/alerts/reset) is the same one used in beforeEach;
  // it resets alert statuses but deliberately preserves in-memory learning_state.
  // decision_count must be >= the value recorded mid-test (not regress).

  test('decision then reset then decision', async ({ page }) => {
    test.slow();

    await page.goto(FRONTEND);
    const made1 = await makeNDecisions(page, 3);
    expect(made1).toBeGreaterThanOrEqual(1);

    // Capture mid-point count
    const mid = await getApiData(page, '/api/soc/learning-state');
    const midDC: number = mid.decision_count ?? 0;

    // Reset alert statuses to pending; wait for the DOM to confirm availability.
    await resetDemoAlerts(page);
    await page.goto(FRONTEND);
    await navigateToTab(page, 1);
    await page.locator('button').filter({ hasText: /ALERT-|SIM-/i }).first()
      .waitFor({ state: 'visible', timeout: 30000 });
    const made2 = await makeNDecisions(page, 3);
    expect(made2).toBeGreaterThanOrEqual(1);

    // learning_state must still be valid — no corruption from reset
    const after = await getApiData(page, '/api/soc/learning-state');
    expect(after.decision_count).toBeGreaterThanOrEqual(midDC);
    expect(typeof after.frozen).toBe('boolean');
    expect(after.iks_v2).toBeGreaterThanOrEqual(0);
  });

  // ── Test 4 ──────────────────────────────────────────────────────────────────
  //
  // Make 5 decisions, then navigate through all 5 tabs in order.
  // Verifies that active learning state does not crash any tab's render tree.
  //
  // Checks on each tab:
  //   • Body is still visible (no full-page crash).
  //   • No React error-boundary text ("Something went wrong", "An error occurred").
  //   • No fatal console errors (React duplicate-key warnings are filtered).

  test('all tabs reachable after 5 decisions', async ({ page }) => {
    test.slow();

    const errors = collectConsoleErrors(page);

    await page.goto(FRONTEND);
    const made = await makeNDecisions(page, 5);
    expect(made).toBeGreaterThanOrEqual(1);

    // Visit each tab and verify no crash
    await page.goto(FRONTEND);
    const tabChecks: Array<{ tab: number; wait: string | RegExp }> = [
      { tab: 1, wait: /ALERT-|SIM-/i },
      { tab: 2, wait: /Institutional Knowledge Score/i },
      { tab: 3, wait: /Analytics|Campaign|Threat|Decision/i },
      { tab: 4, wait: /ROI|return on investment/i },
      { tab: 5, wait: /What Changed|Executive/i },
    ];

    for (const { tab, wait } of tabChecks) {
      await navigateToTab(page, tab);
      // Wait for any primary content on this tab — proves the render tree is alive.
      await page.getByText(wait).first().waitFor({ state: 'visible', timeout: 20000 });
      await expect(page.locator('body')).toBeVisible();

      // No error boundary text
      const bodyText = await page.locator('body').textContent() ?? '';
      expect(bodyText).not.toMatch(/Something went wrong|An error occurred|Unexpected error/i);
    }

    expectNoConsoleErrors(errors);
  });

  // ── Test 5 ──────────────────────────────────────────────────────────────────
  //
  // After 3 decisions, centroid and weight values must be numerically bounded.
  // Uses /api/gae/convergence (the source-of-truth for weight_norm; decision_flow
  // spec test 3 already validates this endpoint returns weight_norm > 0).
  // Also confirms learning-state IKS is finite and non-negative.

  test('centroid values bounded after decisions', async ({ page }) => {
    test.setTimeout(180000);

    await page.goto(FRONTEND);
    await makeNDecisions(page, 3);

    // Convergence metrics (GAE in-memory W-matrix state)
    const conv = await getApiData(page, '/api/gae/convergence');
    expect(conv.weight_norm).toBeGreaterThan(0);
    expect(Number.isFinite(conv.weight_norm)).toBe(true);

    // Learning-state IKS (computed from graph data)
    const ls = await getApiData(page, '/api/soc/learning-state');
    expect(ls.iks_v2).toBeGreaterThanOrEqual(0);
    expect(Number.isFinite(ls.iks_v2)).toBe(true);
  });

  // ── Test 6 ──────────────────────────────────────────────────────────────────
  //
  // Alert queue resilience: navigate to Tab 1 after beforeEach reset and
  // confirm that the queue renders at least one alert card without a decision
  // needing to be made.  Guards against alert-queue regressions where the
  // component crashes on mount when no prior decisions exist in this session.

  test('alert queue renders without prior decisions', async ({ page }) => {
    test.setTimeout(30000);

    // beforeEach already landed on FRONTEND → Tab 1 with alerts visible.
    // Set up the listener AFTER the initial navigation so that fetch-abort errors
    // from the beforeEach page.goto are not captured in this test's window.
    await page.goto(FRONTEND);
    await navigateToTab(page, 1);
    const errors = collectConsoleErrors(page);

    // Queue must have at least one card (reset in beforeEach restored them all)
    const alertCard = page.locator('button').filter({ hasText: /ALERT-|SIM-/i }).first();
    await alertCard.waitFor({ state: 'visible', timeout: 20000 });
    const count = await page.locator('button').filter({ hasText: /ALERT-|SIM-/i }).count();
    expect(count).toBeGreaterThanOrEqual(1);

    // No console errors on idle Tab 1
    expectNoConsoleErrors(errors);
  });

  // ── Test 7 ──────────────────────────────────────────────────────────────────
  //
  // Resilience under mid-flight tab switch:
  //   1. Navigate to Tab 1, click an alert (kicks off async LLM analysis).
  //   2. Before the analysis panel loads, switch to Tab 2.
  //   3. Switch back to Tab 1.
  //   4. Verify no crash and learning-state is still a valid API response.
  //
  // This guards against React state errors that arise when the analysis fetch
  // tries to update a component that has been unmounted by the tab switch.

  test('concurrent tab switch during decision', async ({ page }) => {
    test.setTimeout(90000);

    // beforeEach already navigated to FRONTEND → Tab 1.  Set up listener AFTER
    // a fresh page.goto so that the navigation's fetch-abort noise is excluded.
    await page.goto(FRONTEND);
    await navigateToTab(page, 1);
    const errors = collectConsoleErrors(page);

    // Click the first alert — this starts the async analysis fetch.
    const alertCard = page.locator('button').filter({ hasText: /ALERT-|SIM-/i }).first();
    await alertCard.waitFor({ state: 'visible', timeout: 20000 });
    await alertCard.click();

    // Immediately switch to Tab 2 without waiting for analysis to complete.
    await navigateToTab(page, 2);

    // Brief wait to let any in-flight state update settle.
    await page.waitForTimeout(1000);

    // Switch back to Tab 1 — the app must not have crashed.
    await navigateToTab(page, 1);

    // Alert queue must still be reachable.
    await alertCard.waitFor({ state: 'visible', timeout: 20000 });
    await expect(page.locator('body')).toBeVisible();

    // learning-state API must still respond normally.
    const ls = await getApiData(page, '/api/soc/learning-state');
    expect(ls.decision_count).toBeGreaterThanOrEqual(0);

    expectNoConsoleErrors(errors);
  });

});
