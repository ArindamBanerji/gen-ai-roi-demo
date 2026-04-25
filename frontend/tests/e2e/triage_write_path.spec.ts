// INVESTIGATIVE — documents the triage write path end-to-end.
// Run: cd frontend && npx playwright test triage_write_path
// Backend must be running. All /api/* calls route through the Vite proxy.

import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname  = path.dirname(__filename);

const FRONTEND_PORT = process.env.FRONTEND_PORT || '5173';
const BACKEND_PORT  = process.env.BACKEND_PORT  || '8001';
const FRONTEND      = `http://localhost:${FRONTEND_PORT}`;
const BACKEND       = `http://localhost:${BACKEND_PORT}`;
const SCREENSHOTS   = path.join(__dirname, 'screenshots', 'triage_flow');

test.beforeAll(() => {
  fs.mkdirSync(SCREENSHOTS, { recursive: true });
});

async function snap(page: import('@playwright/test').Page, name: string) {
  try {
    await page.screenshot({
      path: path.join(SCREENSHOTS, `${name}.png`),
      fullPage: false,
    });
  } catch (err) {
    console.log(`[screenshot] ${name}: ${err}`);
  }
}

// Safely fetch JSON via the Vite proxy (baseURL = frontend).
async function fetchJson(page: import('@playwright/test').Page, endpoint: string): Promise<any> {
  try {
    const res = await page.request.get(endpoint);
    if (!res.ok()) {
      console.log(`[api] ${endpoint}: HTTP ${res.status()}`);
      return null;
    }
    return res.json();
  } catch (err) {
    console.log(`[api] ${endpoint}: ${err}`);
    return null;
  }
}

// ── Baseline capture helper ───────────────────────────────────────────────────

async function captureBaseline(page: import('@playwright/test').Page, label: string) {
  const learning   = await fetchJson(page, '/api/soc/learning-state');
  const graphStats = await fetchJson(page, '/api/soc/graph-stats');
  const tab2       = await fetchJson(page, '/api/soc/tab/2/content');

  const snapshot = {
    label,
    decision_count: learning?.decision_count   ?? null,
    iks_score:      learning?.iks_v2           ?? null,
    graph_nodes:    graphStats?.nodes_traversed ?? graphStats?.historical_decisions ?? null,
    tab2_iks:       tab2?.content?.iks_score   ?? null,
  };
  console.log(`[baseline:${label}]`, JSON.stringify(snapshot));
  return snapshot;
}

// ── Full triage write-path test ───────────────────────────────────────────────

test('triage_write_path_end_to_end', async ({ page }) => {
  test.setTimeout(120_000);

  // ── STEP 1: Baseline capture ───────────────────────────────────────────────
  console.log('\n=== STEP 1: BASELINE CAPTURE ===');
  await page.goto(FRONTEND);
  await page.waitForLoadState('networkidle');
  const before = await captureBaseline(page, 'before');
  await snap(page, '00_before_triage');

  // ── STEP 2: Navigate to Alert Triage ──────────────────────────────────────
  console.log('\n=== STEP 2: NAVIGATE TO ALERT TRIAGE ===');
  try {
    await page.getByRole('button', { name: /Alert Triage/i }).click();
    await page.waitForTimeout(1500);
  } catch (err) {
    console.log(`[nav] Alert Triage: ${err}`);
  }
  await snap(page, '01_alert_queue');

  // Count alert cards.
  let alertCount = 0;
  try {
    const cards = page.locator('button').filter({ hasText: /ALERT-|SIM-/i });
    alertCount = await cards.count();
  } catch (err) {
    console.log(`[alert-count]: ${err}`);
  }
  console.log(`Alert cards visible: ${alertCount}`);

  // ── STEP 3: Select first alert ────────────────────────────────────────────
  console.log('\n=== STEP 3: SELECT FIRST ALERT ===');
  let alertId = '(unknown)';
  try {
    const firstCard = page.locator('button').filter({ hasText: /ALERT-|SIM-/i }).first();
    await firstCard.waitFor({ state: 'visible', timeout: 15_000 });
    const cardText = await firstCard.textContent();
    const match = cardText?.match(/(ALERT-\S+|SIM-\S+)/i);
    if (match) alertId = match[1];
    console.log(`Clicking alert: ${alertId}`);
    await firstCard.click();
    await page.waitForTimeout(1000);
  } catch (err) {
    console.log(`[select-alert]: ${err}`);
  }
  await snap(page, '02_alert_selected');
  console.log(`Selected alert ID: ${alertId}`);

  // ── STEP 4: Examine scoring panel ─────────────────────────────────────────
  console.log('\n=== STEP 4: EXAMINE SCORING PANEL ===');

  // Wait for analysis round-trip.
  let analysisVisible = false;
  try {
    await page.getByText(/Why This Decision\?/).waitFor({ state: 'visible', timeout: 30_000 });
    analysisVisible = true;
    console.log('"Why This Decision?" panel: VISIBLE');
  } catch (err) {
    console.log(`"Why This Decision?" panel: NOT VISIBLE — ${err}`);
  }

  // Factor names.
  const factors: string[] = [];
  try {
    const factorEls = page.locator('.font-medium, .font-semibold').filter({
      hasText: /travel|asset|threat|pattern|time|device|intel|trust|transfer|destination/i,
    });
    const count = await factorEls.count();
    for (let i = 0; i < Math.min(count, 10); i++) {
      try {
        const t = (await factorEls.nth(i).textContent())?.trim() ?? '';
        if (t) factors.push(t);
      } catch { /* detached */ }
    }
  } catch (err) {
    console.log(`[factors]: ${err}`);
  }
  console.log(`Factors found: ${factors.join(' | ')}`);

  // Recommendation section.
  try {
    const recVisible = await page.getByRole('heading', { name: /Recommendation/i }).isVisible({ timeout: 5000 }).catch(() => false);
    console.log(`Recommendation section: ${recVisible ? 'VISIBLE' : 'NOT VISIBLE'}`);
  } catch { /* skip */ }

  // Confidence display.
  try {
    const confEl = page.getByText(/Confidence:\s*\d+/).first();
    const confVisible = await confEl.isVisible({ timeout: 3000 }).catch(() => false);
    if (confVisible) {
      const confText = await confEl.textContent();
      console.log(`Confidence: ${confText?.trim()}`);
    }
  } catch { /* skip */ }

  // DiagonalKernel mention — text may be in API response rather than DOM.
  try {
    const kernelCount = await page.getByText(/diagonal/i).count().catch(() => 0);
    const kernelVisible = kernelCount > 0 || (await page.getByText(/kernel/i).count().catch(() => 0)) > 0;
    console.log(`DiagonalKernel/kernel text visible in DOM: ${kernelVisible}`);
  } catch { /* skip */ }

  // Decision method.
  try {
    const dmVisible = await page.getByText(/Decision method:/i).first().isVisible({ timeout: 3000 }).catch(() => false);
    console.log(`Decision method line: ${dmVisible ? 'VISIBLE' : 'NOT VISIBLE'}`);
  } catch { /* skip */ }

  await snap(page, '03_factor_breakdown');

  // Wait for factor analysis to complete loading.
  try {
    await expect(page.getByText(/Factor analysis loading/i)).not.toBeVisible({ timeout: 12_000 });
  } catch { /* may not exist */ }

  // ── STEP 5: Submit verdict ────────────────────────────────────────────────
  console.log('\n=== STEP 5: SUBMIT VERDICT ===');
  let actionTaken = 'none';

  // Strategy A: "Apply Recommendation" / "Apply Policy Resolution" (existing pattern).
  let appliedViaRecommendation = false;
  try {
    const applyBtn = page.getByRole('button', { name: /Apply Recommendation|Apply Policy Resolution/i });
    const applyVisible = await applyBtn.isVisible({ timeout: 5000 }).catch(() => false);
    if (applyVisible) {
      await applyBtn.scrollIntoViewIfNeeded();
      await applyBtn.click();
      appliedViaRecommendation = true;
      actionTaken = 'apply_recommendation';
      console.log('Clicked: Apply Recommendation / Apply Policy Resolution');
    }
  } catch (err) {
    console.log(`[apply-recommendation]: ${err}`);
  }

  // Strategy B: direct action buttons (escalate / investigate / suppress / monitor).
  if (!appliedViaRecommendation) {
    const directActions = ['investigate', 'escalate', 'monitor', 'suppress', 'close'];
    for (const action of directActions) {
      try {
        const btn = page.getByText(new RegExp(action, 'i')).filter({ hasText: new RegExp(`^${action}$`, 'i') }).first();
        const visible = await btn.isVisible({ timeout: 2000 }).catch(() => false);
        if (visible) {
          await btn.scrollIntoViewIfNeeded();
          await btn.click();
          actionTaken = action;
          console.log(`Clicked direct action: ${action}`);
          break;
        }
      } catch { /* try next */ }
    }
    if (actionTaken === 'none') {
      console.log('NO ACTION BUTTONS FOUND (neither Apply Recommendation nor direct actions)');
    }
  }

  await page.waitForTimeout(2000);

  // Strategy C: if Apply Recommendation was clicked, complete the outcome step.
  if (appliedViaRecommendation) {
    try {
      await page.getByText(/OUTCOME FEEDBACK/i).waitFor({ state: 'visible', timeout: 10_000 });
      console.log('"OUTCOME FEEDBACK" panel: VISIBLE');
      await Promise.all([
        page.waitForResponse(
          resp => resp.url().includes('/api/alert/outcome') && resp.status() < 500,
          { timeout: 15_000 },
        ),
        page.getByRole('button', { name: /Confirmed Correct/i }).click(),
      ]);
      actionTaken = 'confirmed_correct';
      console.log('Outcome submitted: Confirmed Correct');
    } catch (err) {
      console.log(`[outcome-feedback]: ${err}`);
    }
  }

  await page.waitForTimeout(2000);
  await snap(page, '04_after_verdict');

  // ── STEP 6: Post-triage capture ───────────────────────────────────────────
  console.log('\n=== STEP 6: POST-TRIAGE CAPTURE ===');
  const after = await captureBaseline(page, 'after');
  await snap(page, '05_after_triage');

  // ── STEP 7: Compare before/after ─────────────────────────────────────────
  console.log('\n=== TRIAGE WRITE PATH RESULTS ===');
  console.log(`Alert: ${alertId}`);
  console.log(`Action taken: ${actionTaken}`);
  console.log(`Decision count: ${before.decision_count} → ${after.decision_count} (delta: ${
    after.decision_count != null && before.decision_count != null
      ? after.decision_count - before.decision_count
      : 'N/A'
  })`);
  console.log(`Graph nodes: ${before.graph_nodes} → ${after.graph_nodes}`);
  console.log(`IKS: ${before.iks_score} → ${after.iks_score}`);
  console.log('=================================');

  // ── STEP 8: Audit chain check ─────────────────────────────────────────────
  console.log('\n=== STEP 8: AUDIT CHAIN CHECK ===');
  try {
    const audit = await fetchJson(page, '/api/audit/decisions?format=json');
    if (audit) {
      const entries: any[] = Array.isArray(audit) ? audit : audit.entries ?? audit.decisions ?? [];
      const latest = entries[entries.length - 1];
      if (latest) {
        console.log('Most recent audit entry:', {
          decision_id:  latest.decision_id  ?? latest.id       ?? null,
          action:       latest.action       ?? latest.outcome  ?? null,
          hash:         latest.entry_hash   ?? latest.hash     ?? null,
          chain_index:  latest.chain_index                     ?? null,
        });
      } else {
        console.log('Audit entries: none returned');
      }
    } else {
      console.log('/api/audit/decisions: endpoint not available (404 or error)');
    }
  } catch (err) {
    console.log(`[audit]: ${err}`);
  }

  // Navigate to the area that would show evidence ledger on Tab 5.
  try {
    await page.getByRole('button', { name: /Executive Narrative/i }).click();
    await page.waitForTimeout(1500);
    const ledgerVisible = await page.getByText(/Evidence Ledger/i).first().isVisible({ timeout: 5000 }).catch(() => false);
    console.log(`Evidence Ledger text visible on Tab 5: ${ledgerVisible}`);
    await snap(page, '06_audit_chain');
  } catch (err) {
    console.log(`[audit-nav]: ${err}`);
  }

  // Soft gate: page must still be alive.
  await expect(page.locator('body')).toBeVisible();
});

// ── Lightweight API probe (runs independently of the UI flow) ─────────────────

test('triage_write_path_api_probe', async ({ page }) => {
  test.setTimeout(30_000);

  await page.goto(FRONTEND);
  await page.waitForLoadState('networkidle');

  const endpoints = [
    '/api/soc/learning-state',
    '/api/soc/graph-stats',
    '/api/soc/tab/2/content',
    '/api/soc/tab/3/content',
    '/api/soc/analytics',
  ];

  console.log('\n=== API PROBE ===');
  for (const ep of endpoints) {
    try {
      const res = await page.request.get(ep);
      const body = await res.json().catch(() => null);
      console.log(`${ep}: HTTP ${res.status()} — keys: ${body ? Object.keys(body).slice(0, 6).join(', ') : 'parse error'}`);
    } catch (err) {
      console.log(`${ep}: ${err}`);
    }
  }

  // Audit endpoint probe.
  const auditEndpoints = [
    '/api/audit/decisions',
    '/api/audit/decisions?format=json',
    '/api/audit/chain',
    '/api/soc/audit',
  ];
  console.log('\n=== AUDIT ENDPOINT PROBE ===');
  for (const ep of auditEndpoints) {
    try {
      const res = await page.request.get(ep);
      console.log(`${ep}: HTTP ${res.status()}`);
    } catch (err) {
      console.log(`${ep}: ${err}`);
    }
  }

  await expect(page.locator('body')).toBeVisible();
});
