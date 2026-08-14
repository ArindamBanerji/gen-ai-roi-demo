/**
 * age_contracts.spec.ts — AGE serialization and property-name boundary contracts.
 *
 * Two describe blocks:
 *   1. "AGE serialization contracts" — API-level checks via Playwright `request`
 *      fixture (no browser needed; fast).
 *   2. "Tab render contracts" — browser-level checks that no error boundary fires
 *      and no "DEC-None" duplicate keys appear in rendered output.
 *
 * Run:
 *   npx playwright test tests/e2e/age_contracts.spec.ts --reporter=list
 */

import { test, expect } from '@playwright/test';

const BACKEND_PORT = process.env.BACKEND_PORT || '8001';
const FRONTEND_PORT = process.env.FRONTEND_PORT || '5173';
const BACKEND  = `http://127.0.0.1:${BACKEND_PORT}`;
const FRONTEND = `http://127.0.0.1:${FRONTEND_PORT}`;

// ─────────────────────────────────────────────────────────────────────────────
// BLOCK 1 — AGE serialization contracts (API-level, no browser)
// ─────────────────────────────────────────────────────────────────────────────

test.describe('AGE serialization contracts', () => {

  test('campaigns API — category_sequence is JSON array not string', async ({ request }) => {
    const resp = await request.get(`${BACKEND}/api/soc/campaigns`);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    const campaigns: any[] = data.campaigns ?? [];
    for (const c of campaigns) {
      expect(
        Array.isArray(c.category_sequence),
        `campaign ${c.campaign_id}: category_sequence is ${typeof c.category_sequence}, expected array. ` +
        `AGE may be returning a raw JSON string instead of a parsed list.`
      ).toBe(true);
    }
  });

  test('campaigns API — shared_entities is JSON array not string', async ({ request }) => {
    const resp = await request.get(`${BACKEND}/api/soc/campaigns`);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    const campaigns: any[] = data.campaigns ?? [];
    for (const c of campaigns) {
      expect(
        Array.isArray(c.shared_entities),
        `campaign ${c.campaign_id}: shared_entities is ${typeof c.shared_entities}, expected array.`
      ).toBe(true);
    }
  });

test('analytics API — correct_decisions is integer', async ({ request }) => {
    let resp = await request.get(`${BACKEND}/api/soc/analytics`);
    if (resp.status() === 500 || resp.status() === 503) {
      await new Promise((resolve) => setTimeout(resolve, 3000));
      resp = await request.get(`${BACKEND}/api/soc/analytics`);
    }
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    const cd = data.correct_decisions;
    expect(
      typeof cd === 'number' && Number.isInteger(cd),
      `correct_decisions is ${typeof cd} (value=${JSON.stringify(cd)}), expected integer.`
    ).toBe(true);
  });

  test('analytics API — total_alerts is integer', async ({ request }) => {
    const resp = await request.get(`${BACKEND}/api/soc/analytics`);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    const ta = data.total_alerts;
    expect(
      typeof ta === 'number' && Number.isInteger(ta),
      `total_alerts is ${typeof ta} (value=${JSON.stringify(ta)}), expected integer.`
    ).toBe(true);
  });

  test('threat-landscape — graph_coverage.nodes is integer', async ({ request }) => {
    const resp = await request.get(`${BACKEND}/api/soc/threat-landscape`);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    const nodes = data?.graph_coverage?.nodes;
    expect(
      typeof nodes === 'number' && Number.isInteger(nodes),
      `graph_coverage.nodes is ${typeof nodes} (value=${JSON.stringify(nodes)}), expected integer.`
    ).toBe(true);
  });

  test('executive-narrative — what_changed.top_shifts is array', async ({ request }) => {
    const resp = await request.get(`${BACKEND}/api/soc/executive-narrative`);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    const topShifts = data?.what_changed?.top_shifts;
    expect(
      Array.isArray(topShifts),
      `what_changed.top_shifts is ${typeof topShifts} (value=${JSON.stringify(topShifts)}), expected array.`
    ).toBe(true);
  });

  test('evolution-events — no DEC-None IDs (decision_id property used correctly)', async ({ request }) => {
    const resp = await request.get(`${BACKEND}/api/metrics/evolution-events`);
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    const events: any[] = data.events ?? [];
    const decNoneEvents = events.filter((e: any) => e.id === 'DEC-None' || e.id === 'DEC-');
    expect(
      decNoneEvents.length,
      `Found ${decNoneEvents.length} event(s) with id="DEC-None". ` +
      `This means d.decision_id is not being used in the Cypher query — ` +
      `d.id always returns null in AGE Decision nodes.`
    ).toBe(0);
    // If events exist, all IDs must start with DEC- and have non-empty suffix
    for (const e of events) {
      expect(
        typeof e.id === 'string' && e.id.startsWith('DEC-') && e.id.length > 4,
        `Event id ${JSON.stringify(e.id)} is not a valid DEC-* identifier.`
      ).toBe(true);
    }
  });

});


// ─────────────────────────────────────────────────────────────────────────────
// BLOCK 2 — Session integrity contracts (BACKLOG-068)
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Session integrity contracts', () => {

  test('audit chain verified on startup', async ({ request }) => {
    const res = await request.get(`${BACKEND}/api/audit/verify`);
    expect(res.status()).toBe(200);
    const data = await res.json();
    expect(data.verified).toBe(true);
    expect(data.chain_length).toBeGreaterThanOrEqual(0);
  });

  test('audit epochs endpoint returns data', async ({ request }) => {
    const res = await request.get(`${BACKEND}/api/audit/epochs`);
    expect(res.status()).toBe(200);
    const data = await res.json();
    expect(data.epochs.length).toBeGreaterThan(0);
    expect(data.total_entries).toBeGreaterThan(0);
    // Active epoch exists
    const active = data.epochs.find((e: any) => e.active === true);
    expect(active).toBeTruthy();
  });

  test('threat-landscape last_refreshed not hardcoded 23', async ({ request }) => {
    const res = await request.get(`${BACKEND}/api/soc/threat-landscape`);
    expect(res.status()).toBe(200);
    const data = await res.json();
    // Can be null (no refresh yet) or a real number, but never exactly 23
    const val = data.threat_intel?.last_refreshed_minutes_ago;
    if (val !== null && val !== undefined) {
      expect(val).not.toBe(23);
    }
  });

  test('threat-landscape avg_confidence not hardcoded 0.89', async ({ request }) => {
    const res = await request.get(`${BACKEND}/api/soc/threat-landscape`);
    expect(res.status()).toBe(200);
    const data = await res.json();
    const conf = data.governance?.avg_confidence;
    expect(conf).not.toBe(0.89);
    // Should be a real number between 0 and 1
    expect(typeof conf).toBe('number');
    expect(conf).toBeGreaterThanOrEqual(0);
    expect(conf).toBeLessThanOrEqual(1);
  });

  test('analytics has no threat_intel_match category', async ({ request }) => {
    const res = await request.get(`${BACKEND}/api/soc/analytics`);
    expect(res.status()).toBe(200);
    const data = await res.json();
    const categories: any[] = data.category_breakdown ?? [];
    const catNames = categories.map((c: any) => c.category);
    expect(catNames).not.toContain('threat_intel_match');
    // Should have malware_execution instead
    expect(catNames).toContain('malware_execution');
  });

  test('compounding weekly data has real counts', async ({ request }) => {
    const res = await request.get(`${BACKEND}/api/metrics/compounding?weeks=4`);
    expect(res.status()).toBe(200);
    const data = await res.json();
    // At least one week should have decisions > 0 (pattern_count is total decisions that week)
    const weeks: any[] = data.weekly_trend ?? data.weekly_data ?? [];
    const hasData = weeks.some((w: any) =>
      (w.pattern_count ?? 0) > 0 ||
      (w.total ?? 0) > 0 ||
      (w.decisions ?? 0) > 0 ||
      (w.auto_close_rate ?? 0) > 0
    );
    expect(hasData).toBe(true);
    // No "estimated" flag (BACKLOG-060 removed it)
    expect(data.weekly_trend_estimated).not.toBe(true);
  });

});


// ─────────────────────────────────────────────────────────────────────────────
// BLOCK 3 — Tab render contracts (browser-level)
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Tab render contracts', () => {

  test('Tab 1 loads without error boundary or crash text', async ({ page }) => {
    await page.goto(FRONTEND);
    await page.getByRole('button', { name: /Alert Triage/i }).click();
    await expect(page.getByText(/Queue/i).first()).toBeVisible({ timeout: 15000 });

    // No React error boundary text should appear
    const errorBoundary = page.locator('text=/Something went wrong|Cannot read properties|is not a function/i');
    await expect(errorBoundary).toHaveCount(0);

    // No "cats.map is not a function" crash — CampaignIntelligencePanel guard
    const mapError = page.locator('text=/map is not a function/i');
    await expect(mapError).toHaveCount(0);
  });

  test('Tab 4 compounding panel — no DEC-None text visible', async ({ page }) => {
    await page.goto(FRONTEND);
    await page.getByRole('button', { name: /Compounding/i }).click();
    await expect(page.getByText(/Compounding|Watch the Moat/i).first()).toBeVisible({ timeout: 15000 });

    // "DEC-None" in visible text means decision_id property was not used
    const decNoneText = page.locator('text=DEC-None');
    await expect(decNoneText).toHaveCount(0);
  });

  test('SOC Analytics tab campaign panel — no error boundary fires for category_sequence', async ({ page }) => {
    await page.goto(FRONTEND);
    await page.getByRole('button', { name: /SOC Analytics/i }).click();
    await expect(page.getByText(/SOC Analytics/i).first()).toBeVisible({ timeout: 15000 });

    // The campaign intelligence panel must render (no crash from .map on string)
    const panel = page.locator('.campaign-intelligence-panel');
    await expect(panel).toBeVisible({ timeout: 10_000 });

    // No TypeError visible — would appear if formatChain received a raw string
    const typeError = page.locator('text=/TypeError|map is not a function/i');
    await expect(typeError).toHaveCount(0);
  });

});
