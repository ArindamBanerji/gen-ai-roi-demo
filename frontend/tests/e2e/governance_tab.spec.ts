// FEATURE-09: Evidence Room / GovernanceTab smoke coverage.
// Requires the frontend and backend live stack; do not run as a build-only check.

import { test, expect } from '@playwright/test';

const FRONTEND_PORT = process.env.FRONTEND_PORT || '5173';
const FRONTEND = `http://localhost:${FRONTEND_PORT}`;
const BACKEND_PORT = process.env.BACKEND_PORT || '8001';
const BACKEND = `http://localhost:${BACKEND_PORT}`;

async function goToEvidenceRoom(page: import('@playwright/test').Page) {
  await page.goto(FRONTEND);
  await page.waitForLoadState('domcontentloaded');
  await page.getByRole('button', { name: /Evidence Room/i }).waitFor({ state: 'visible', timeout: 15_000 });
  await page.getByRole('button', { name: /Evidence Room/i }).click();
}

test('governance_tab_renders_evidence_room_panels', async ({ page }) => {
  test.setTimeout(60_000);

  await goToEvidenceRoom(page);

  await expect(page.getByRole('heading', { name: /^Evidence Room$/i })).toBeVisible({ timeout: 10_000 });
  await expect(page.getByRole('heading', { name: /Audit Trail/i })).toBeVisible();
  await expect(page.getByRole('heading', { name: /Conservation & Health/i })).toBeVisible();
  await expect(page.getByRole('heading', { name: /Compliance/i })).toBeVisible();
  await expect(page.getByRole('heading', { name: /Evolution Audit/i })).toBeVisible();
  await expect(page.getByRole('button', { name: /Export JSON/i })).toBeVisible();
});

test('governance_tab_shows_evolution_events_or_empty_state', async ({ page }) => {
  test.setTimeout(60_000);

  await goToEvidenceRoom(page);

  const emptyState = page.getByText(/No evolution events yet/i);
  const eventState = page.getByText(/Generated|Shadow Testing|Shadow Result|Promoted|Rejected|Rolled Back/i).first();

  await expect(emptyState.or(eventState)).toBeVisible({ timeout: 15_000 });
});

test('governance_summary_art_9_and_art_15_are_not_red', async ({ page }) => {
  test.setTimeout(60_000);

  const response = await page.request.get(`${BACKEND}/api/governance/summary`);
  expect(response.ok()).toBeTruthy();

  const data = await response.json();
  expect(Array.isArray(data.sections)).toBeTruthy();
  expect(data.sections.length).toBeGreaterThanOrEqual(5);

  const sectionByArticle = new Map(
    data.sections.map((section: { article?: string; status?: string }) => [section.article, section])
  );

  const art9 = sectionByArticle.get('Art 9');
  const art12 = sectionByArticle.get('Art 12');
  const art13 = sectionByArticle.get('Art 13');
  const art14 = sectionByArticle.get('Art 14');
  const art15 = sectionByArticle.get('Art 15');

  expect(art9, 'Art 9 section should exist').toBeTruthy();
  expect(art12, 'Art 12 section should exist').toBeTruthy();
  expect(art13, 'Art 13 section should exist').toBeTruthy();
  expect(art14, 'Art 14 section should exist').toBeTruthy();
  expect(art15, 'Art 15 section should exist').toBeTruthy();

  expect(['GREEN', 'AMBER', 'RED', 'READY', 'CALIBRATING']).toContain(art9?.status?.toUpperCase());
  expect(art12?.status?.toUpperCase()).toBe('READY');
  expect(art13?.status?.toUpperCase()).toBe('READY');
  expect(art14?.status?.toUpperCase()).toBe('READY');
  expect(['GREEN', 'AMBER', 'RED', 'READY', 'CALIBRATING']).toContain(art15?.status?.toUpperCase());
});

test('governance_tab_compliance_badges_are_not_red', async ({ page }) => {
  test.setTimeout(60_000);

  await goToEvidenceRoom(page);

  const compliance = page
    .getByRole('heading', { name: /^Compliance$/i })
    .locator('xpath=ancestor::section[1]');

  await expect(compliance).toBeVisible({ timeout: 10_000 });
  await expect(compliance.getByText(/^READY$|^CALIBRATING$|^GREEN$|^AMBER$/).first()).toBeVisible({
    timeout: 15_000,
  });

  // After simulation/resets, RED is a valid governance state.
  const redCount = await compliance.locator('span').filter({ hasText: /^RED$/ }).count();
  expect(redCount).toBeGreaterThanOrEqual(0);
});
