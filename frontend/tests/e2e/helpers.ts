/**
 * helpers.ts — Shared E2E utilities for cross-tab compounding tests.
 *
 * Port convention mirrors all other spec files: read BACKEND_PORT / FRONTEND_PORT
 * from the environment (populated by playwright.config.ts via root .env).
 * Never hardcode port numbers here.
 */

import { Page } from '@playwright/test';

const FRONTEND_PORT = process.env.FRONTEND_PORT || '5173';
const BACKEND_PORT  = process.env.BACKEND_PORT  || '8001';

export const FRONTEND = `http://localhost:${FRONTEND_PORT}`;
export const BACKEND  = `http://localhost:${BACKEND_PORT}`;

// Alert card selector — matches both SIM-* and ALERT-* IDs.
const ALERT_CARD_RE = /ALERT-|SIM-/i;

// Tab 1-5 button name patterns (button text from the nav bar).
const TAB_NAMES: Record<number, RegExp> = {
  1: /Alert Triage/i,
  2: /Runtime Evolution/i,
  3: /SOC Analytics/i,
  4: /Compounding|Decision Economics/i,
  5: /Executive Narrative/i,
};

/**
 * Click the numbered tab button and wait for the nav button to become active.
 * Uses getByRole so it survives minor label rewording.
 */
export async function navigateToTab(page: Page, tabNumber: number): Promise<void> {
  const name = TAB_NAMES[tabNumber];
  if (!name) throw new Error(`Unknown tab number: ${tabNumber}`);
  await page.getByRole('button', { name }).click();
}

/**
 * Execute one complete triage decision (correct outcome):
 *   1. Full page reload — resets React closedLoop state.
 *   2. Navigate to Tab 1.
 *   3. Click first pending alert.
 *   4. Wait for the analysis panel ("Why This Decision?").
 *   5. Click the execute / apply recommendation button.
 *   6. Wait for OUTCOME FEEDBACK panel.
 *   7. Click "Confirmed Correct" and wait for the POST /api/alert/outcome response.
 *
 * Uses waitForResponse (not waitForTimeout) for the outcome submit so the call
 * returns as soon as the server acknowledges the write — not on an arbitrary timer.
 */
export async function makeDecision(page: Page): Promise<void> {
  await page.goto(FRONTEND);
  await navigateToTab(page, 1);

  const alertCard = page.locator('button').filter({ hasText: ALERT_CARD_RE }).first();
  await alertCard.waitFor({ state: 'visible', timeout: 20000 });
  await alertCard.click();

  // Wait for the LLM analysis round-trip.
  await page.getByText(/Why This Decision\?/).waitFor({ state: 'visible', timeout: 30000 });

  const executeBtn = page.getByRole('button', {
    name: /Apply Recommendation|Apply Policy Resolution/i,
  });
  await executeBtn.waitFor({ state: 'visible', timeout: 15000 });
  await executeBtn.scrollIntoViewIfNeeded();
  await executeBtn.click();

  // OutcomeFeedback panel — appears when closedLoop state is set.
  await page.getByText(/OUTCOME FEEDBACK/i).waitFor({ state: 'visible', timeout: 10000 });

  // Submit outcome and capture the server acknowledgement.
  await Promise.all([
    page.waitForResponse(
      resp => resp.url().includes('/api/alert/outcome') && resp.status() < 500,
      { timeout: 15000 },
    ),
    page.getByRole('button', { name: /Confirmed Correct/i }).click(),
  ]);
}

/**
 * Make up to n decisions, returning the count actually completed.
 * Stops early if no more alert cards are available or any step times out.
 */
export async function makeNDecisions(page: Page, n: number): Promise<number> {
  let made = 0;
  for (let i = 0; i < n; i++) {
    try {
      await makeDecision(page);
      made++;
    } catch {
      break; // no more alerts or timeout
    }
  }
  return made;
}

/**
 * GET a backend API endpoint and return the parsed JSON body.
 * Uses page.request so it shares the browser's network context and cookies.
 */
export async function getApiData(page: Page, endpoint: string): Promise<any> {
  const response = await page.request.get(`${BACKEND}${endpoint}`);
  return response.json();
}

/**
 * Read Tab 2 metrics from /api/soc/learning-state.
 * Returns iks (iks_v2) and decisionCount as safe numbers.
 */
export async function getTab2Metrics(page: Page): Promise<{
  iks: number;
  decisionCount: number;
}> {
  const data = await getApiData(page, '/api/soc/learning-state');
  return {
    iks: data.iks_v2 ?? 0,
    decisionCount: data.decision_count ?? 0,
  };
}
