// Feature: ServiceNow mock incident workflow — API contract tests.

import { test, expect } from '@playwright/test';

const BACKEND_PORT = process.env.BACKEND_PORT || '8001';
const BACKEND = `http://localhost:${BACKEND_PORT}`;

function uniqueId(prefix: string, workerIndex: number) {
  return `${prefix}-${Date.now()}-${workerIndex}-${Math.random().toString(36).slice(2, 8)}`;
}

function incidentPayload(decisionId: string) {
  return {
    decision_id: decisionId,
    alert_id: `ALERT-${decisionId}`,
    alert_type: 'Suspicious Login',
    category: 'Security',
    confidence: 0.91,
    nl_explanation: 'Created by Playwright API contract test.',
    analyst_id: 'playwright',
  };
}

async function createIncident(page: import('@playwright/test').Page, decisionId: string) {
  const response = await page.request.post(`${BACKEND}/api/servicenow/create-incident`, {
    data: incidentPayload(decisionId),
  });
  expect(response.status()).toBe(200);
  return response.json();
}

test('servicenow_create_incident', async ({ page }, testInfo) => {
  test.setTimeout(30_000);

  const decisionId = uniqueId('PW-SN-CREATE', testInfo.workerIndex);
  const data = await createIncident(page, decisionId);

  expect(data.decision_id).toBe(decisionId);
  expect(data.incident_number).toMatch(/^INC\d+$/);
  expect(data.status).toBe('New');
  expect(data.urgency).toBe(1);
  expect(typeof data.external_url).toBe('string');
});

test('servicenow_list_incidents', async ({ page }, testInfo) => {
  test.setTimeout(30_000);

  const decisionId = uniqueId('PW-SN-LIST', testInfo.workerIndex);
  await createIncident(page, decisionId);

  const response = await page.request.get(`${BACKEND}/api/servicenow/incidents`);
  expect(response.status()).toBe(200);
  const data = await response.json();

  expect(Array.isArray(data)).toBe(true);
  expect(data.some((incident: any) => incident.decision_id === decisionId)).toBe(true);
});

test('servicenow_get_incident_by_decision', async ({ page }, testInfo) => {
  test.setTimeout(30_000);

  const decisionId = uniqueId('PW-SN-GET', testInfo.workerIndex);
  const created = await createIncident(page, decisionId);

  const response = await page.request.get(`${BACKEND}/api/servicenow/incident/${encodeURIComponent(decisionId)}`);
  expect(response.status()).toBe(200);
  const data = await response.json();

  expect(data.decision_id).toBe(decisionId);
  expect(data.incident_number).toBe(created.incident_number);
  expect(data.alert_id).toBe(created.alert_id);
});

test('servicenow_update_status', async ({ page }, testInfo) => {
  test.setTimeout(30_000);

  const decisionId = uniqueId('PW-SN-UPDATE', testInfo.workerIndex);
  await createIncident(page, decisionId);

  const response = await page.request.post(`${BACKEND}/api/servicenow/update-status`, {
    data: {
      decision_id: decisionId,
      status: 'Resolved',
    },
  });
  expect(response.status()).toBe(200);
  const data = await response.json();

  expect(data.decision_id).toBe(decisionId);
  expect(data.status).toBe('Resolved');
});
