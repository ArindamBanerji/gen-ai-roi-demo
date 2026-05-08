// Feature: Evidence Room and governance report — API contract tests.

import { test, expect } from '@playwright/test';

const BACKEND_PORT = process.env.BACKEND_PORT || '8001';
const BACKEND = `http://localhost:${BACKEND_PORT}`;

const CONSERVATION_STATUSES = ['GREEN', 'AMBER', 'RED', 'CALIBRATING', 'UNKNOWN', 'UNAVAILABLE'];

test('evidence_room_summary_has_all_sections', async ({ page }) => {
  test.setTimeout(30_000);

  const response = await page.request.get(`${BACKEND}/api/soc/evidence-room`);
  expect(response.status()).toBe(200);
  const data = await response.json();

  expect(typeof data.generated_at).toBe('string');
  expect(typeof data.audit_trail).toBe('object');
  expect(typeof data.conservation).toBe('object');
  expect(typeof data.override_analysis).toBe('object');
  expect(typeof data.hash_chain).toBe('object');
});

test('evidence_room_conservation_status_valid', async ({ page }) => {
  test.setTimeout(30_000);

  const response = await page.request.get(`${BACKEND}/api/soc/evidence-room`);
  expect(response.status()).toBe(200);
  const data = await response.json();

  expect(CONSERVATION_STATUSES).toContain(data.conservation.status);
  expect(typeof data.conservation.product).toBe('number');
  expect(typeof data.conservation.threshold).toBe('number');
  expect(typeof data.conservation.verified_decisions).toBe('number');
  expect(typeof data.conservation.frozen).toBe('boolean');
});

test('evidence_room_export_has_metadata', async ({ page }) => {
  test.setTimeout(30_000);

  const response = await page.request.get(`${BACKEND}/api/soc/evidence-room/export`);
  expect(response.status()).toBe(200);
  expect(response.headers()['content-type'] || '').toContain('application/json');
  const data = await response.json();

  expect(typeof data.generated_at).toBe('string');
  expect(typeof data.export_metadata).toBe('object');
  expect(data.export_metadata.format_version).toBe('1.0');
  expect(data.export_metadata.product).toBe('SOC Copilot');
  expect(typeof data.hash_chain).toBe('object');
});

test('governance_report_structure', async ({ page }) => {
  test.setTimeout(60_000);

  const response = await page.request.get(`${BACKEND}/api/governance/report`);
  expect(response.status()).toBe(200);
  const data = await response.json();

  expect(typeof data.title).toBe('string');
  expect(typeof data.report_id).toBe('string');
  expect(typeof data.generated_at).toBe('string');
  expect(typeof data.legal_disclaimer).toBe('string');
  expect(Array.isArray(data.sections)).toBe(true);
  expect(data.sections.length).toBeGreaterThanOrEqual(5);
  const first = data.sections[0];
  expect(typeof first.article).toBe('string');
  expect(typeof first.title).toBe('string');
  expect(typeof first.status).toBe('string');
  expect(typeof first.evidence).toBe('object');
  expect(typeof first.evidence_count).toBe('number');
});
