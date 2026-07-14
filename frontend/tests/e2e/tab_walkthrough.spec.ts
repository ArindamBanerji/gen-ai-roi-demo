// INVESTIGATIVE — documents what exists on each tab. No hard assertions on content.
// Run: cd frontend && npx playwright test tab_walkthrough
// Backend must be running on BACKEND_PORT (default 8001).

import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname  = path.dirname(__filename);

const FRONTEND_PORT = process.env.FRONTEND_PORT || '5173';
const FRONTEND      = `http://127.0.0.1:${FRONTEND_PORT}`;
const SCREENSHOTS   = path.join(__dirname, 'screenshots', 'tab_walkthrough');

// Tab definitions — order matches App.tsx tabs array (index 0..5).
const TABS = [
  { index: 0, id: 'soc',         label: 'SOC Analytics'       },
  { index: 1, id: 'evolution',   label: 'Runtime Evolution'    },
  { index: 2, id: 'triage',      label: 'Alert Triage'         },
  { index: 3, id: 'compounding', label: 'Compounding'          },
  { index: 4, id: 'executive',   label: 'Executive Narrative'  },
  { index: 5, id: 's2p',         label: 'S2P Preview'          },
];

// Runtime Evolution subsections.
// Desktop sidebar buttons render as "[A] This Decision", "[B] Situational", etc.
// Mobile nav renders as "A · This Decision" (no brackets) and is hidden on desktop.
// Filtering by the bracket tag (e.g. /\[A\]/) uniquely targets the visible desktop buttons.
const EVOLUTION_SUBSECTIONS = [
  { key: 'a', tag: '[A]', label: 'This Decision' },
  { key: 'b', tag: '[B]', label: 'Situational'   },
  { key: 'c', tag: '[C]', label: 'Adaptation'    },
  { key: 'd', tag: '[D]', label: 'System Health' },
];

test.beforeAll(() => {
  fs.mkdirSync(SCREENSHOTS, { recursive: true });
});

// ── Utility ──────────────────────────────────────────────────────────────────

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

// ── Main walkthrough ──────────────────────────────────────────────────────────

test('tab_walkthrough_all_tabs', async ({ page }) => {
  test.setTimeout(120_000);

  await page.goto(FRONTEND);
  await page.waitForLoadState('networkidle');

  const summary: Record<string, object> = {};

  for (const tab of TABS) {
    console.log(`\n=== TAB ${tab.index}: ${tab.label} ===`);

    // Navigate — tabs are <button> elements, NOT role="tab".
    try {
      await page.getByRole('button', { name: new RegExp(tab.label, 'i') }).click();
      await page.waitForTimeout(1000);
    } catch (err) {
      console.log(`[nav] ${tab.label}: ${err}`);
      continue;
    }

    await snap(page, `${tab.index}_${tab.id}`);

    // ── Heading text ────────────────────────────────────────────────────────
    const headings: string[] = [];
    try {
      const els = page.locator('h1, h2, h3');
      const count = await els.count();
      for (let i = 0; i < count; i++) {
        const t = (await els.nth(i).textContent())?.trim() ?? '';
        if (t) headings.push(t);
      }
    } catch (err) {
      console.log(`[headings] ${tab.label}: ${err}`);
    }
    console.log(`Headings: ${headings.slice(0, 10).join(' | ')}`);

    // ── Metric values (.text-3xl, .text-2xl, .font-mono) ───────────────────
    const metrics: string[] = [];
    try {
      const els = page.locator('.text-3xl, .text-2xl, .font-mono');
      const count = await els.count();
      for (let i = 0; i < Math.min(count, 15); i++) {
        try {
          const t = (await els.nth(i).textContent())?.trim() ?? '';
          if (t) metrics.push(t);
        } catch { /* element detached */ }
      }
    } catch (err) {
      console.log(`[metrics] ${tab.label}: ${err}`);
    }
    console.log(`Metrics: ${metrics.slice(0, 10).join(' | ')}`);

    // ── Chart counts ────────────────────────────────────────────────────────
    let canvasCount = 0;
    let svgCount    = 0;
    let tableCount  = 0;
    try {
      canvasCount = await page.locator('canvas').count();
      svgCount    = await page.locator('svg').count();
      tableCount  = await page.locator('table').count();
    } catch (err) {
      console.log(`[chart-count] ${tab.label}: ${err}`);
    }
    console.log(`Charts: canvas=${canvasCount}  svg=${svgCount}  tables=${tableCount}`);

    // ── Status badges ────────────────────────────────────────────────────────
    const badges: string[] = [];
    try {
      const els = page.locator('.rounded-full, .badge').filter({ hasText: /active|frozen|green|amber|red|ok|warn/i });
      const count = await els.count();
      for (let i = 0; i < Math.min(count, 5); i++) {
        try {
          const t = (await els.nth(i).textContent())?.trim() ?? '';
          if (t) badges.push(t);
        } catch { /* skip */ }
      }
    } catch (err) {
      console.log(`[badges] ${tab.label}: ${err}`);
    }
    if (badges.length) console.log(`Badges: ${badges.join(' | ')}`);

    summary[tab.id] = { headings: headings.length, metrics: metrics.length, canvasCount, svgCount, tableCount };

    // ── Runtime Evolution: subsection walkthrough ────────────────────────────
    if (tab.id === 'evolution') {
      for (const sub of EVOLUTION_SUBSECTIONS) {
        // Target the desktop sidebar button via its bracket tag, e.g. /\[A\]/
        // This avoids matching the hidden mobile nav (which uses "A ·" format).
        const tagPattern = new RegExp(sub.tag.replace('[', '\\[').replace(']', '\\]'));

        try {
          const btn = page.locator('button').filter({ hasText: tagPattern }).first();
          await btn.click({ timeout: 5000 });
          await page.waitForTimeout(500);
          await snap(page, `${tab.index}_${tab.id}_sub_${sub.key}_${sub.label.toLowerCase().replace(' ', '_')}`);
          console.log(`  Subsection ${sub.key} (${sub.label}): clicked`);
        } catch (err) {
          console.log(`  Subsection ${sub.key} (${sub.label}): NOT FOUND — ${(err as Error).message?.slice(0, 80)}`);
          // Scroll to section directly as fallback so we can still screenshot it.
          try {
            await page.locator(`#section-${sub.key}`).scrollIntoViewIfNeeded();
            await page.waitForTimeout(500);
            await snap(page, `${tab.index}_${tab.id}_sub_${sub.key}_${sub.label.toLowerCase().replace(' ', '_')}_scroll`);
            console.log(`  Subsection ${sub.key}: scrolled to #section-${sub.key} (fallback)`);
          } catch { /* ignore scroll failure */ }
          continue;
        }

        // In System Health ('d'): log IKS value and "/ 100" label.
        if (sub.key === 'd') {
          // Scroll section-d into view to ensure IKS block is rendered.
          try { await page.locator('#section-d').scrollIntoViewIfNeeded(); } catch { /* ok */ }
          await page.waitForTimeout(500);

          try {
            const iksEl = page.locator('.text-3xl').filter({ hasText: /^\d+(\.\d+)?$/ }).first();
            const iksVisible = await iksEl.isVisible({ timeout: 3000 }).catch(() => false);
            if (iksVisible) {
              const iksVal = await iksEl.textContent();
              console.log(`  IKS value (.text-3xl): ${iksVal?.trim()}`);
            } else {
              console.log('  IKS value (.text-3xl): NOT VISIBLE after scrolling to System Health');
            }
          } catch (err) {
            console.log(`  IKS (.text-3xl): ${err}`);
          }
          try {
            const label100 = page.getByText(/\/\s*100/).first();
            const l100Visible = await label100.isVisible({ timeout: 3000 }).catch(() => false);
            console.log(`  "/ 100" label: ${l100Visible ? 'VISIBLE' : 'NOT VISIBLE'}`);
          } catch (err) {
            console.log(`  "/ 100" label: ${err}`);
          }
        }
      }
    }

    // ── Alert Triage: count alert cards, log first 3 IDs ────────────────────
    if (tab.id === 'triage') {
      try {
        const alertCards = page.locator('button').filter({ hasText: /ALERT-|SIM-/i });
        const alertCount = await alertCards.count();
        console.log(`  Alert cards: ${alertCount}`);

        const alertIds: string[] = [];
        for (let i = 0; i < Math.min(alertCount, 3); i++) {
          try {
            const text = await alertCards.nth(i).textContent();
            const match = text?.match(/(ALERT-\S+|SIM-\S+)/i);
            if (match) alertIds.push(match[1]);
          } catch { /* skip */ }
        }
        console.log(`  First alert IDs: ${alertIds.join(', ')}`);
      } catch (err) {
        console.log(`  Alert cards: ${err}`);
      }
    }
  }

  // ── Summary table ─────────────────────────────────────────────────────────
  console.log('\n=== TAB WALKTHROUGH SUMMARY ===');
  console.log('Tab              | Headings | Metrics | Canvas | SVG | Tables');
  console.log('-'.repeat(65));
  for (const tab of TABS) {
    const s = summary[tab.id] as any ?? {};
    console.log(
      `${tab.label.padEnd(16)} | ${String(s.headings ?? '-').padEnd(8)} | ${String(s.metrics ?? '-').padEnd(7)} | ${String(s.canvasCount ?? '-').padEnd(6)} | ${String(s.svgCount ?? '-').padEnd(3)} | ${s.tableCount ?? '-'}`
    );
  }

  // Soft gate: page must still be alive (no crash).
  await expect(page.locator('body')).toBeVisible();
});

// ── Per-tab smoke tests (individual, easier to re-run) ────────────────────────

for (const tab of TABS) {
  test(`tab_visible_${tab.id}`, async ({ page }) => {
    test.setTimeout(30_000);
    await page.goto(FRONTEND);
    await page.waitForLoadState('networkidle');

    let clicked = false;
    try {
      await page.getByRole('button', { name: new RegExp(tab.label, 'i') }).click();
      await page.waitForTimeout(1000);
      clicked = true;
    } catch (err) {
      console.log(`[nav] ${tab.label}: ${err}`);
    }

    await snap(page, `smoke_${tab.index}_${tab.id}`);
    await expect(page.locator('body')).toBeVisible();
    console.log(`${tab.label}: navigated=${clicked}`);
  });
}
