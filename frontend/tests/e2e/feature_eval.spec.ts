// Feature: Evaluate on Your Data — API contract tests.

import { test, expect } from '@playwright/test';

const BACKEND_PORT = process.env.BACKEND_PORT || '8001';
const BACKEND = `http://127.0.0.1:${BACKEND_PORT}`;

function expectArray(value: unknown, name: string) {
  expect(Array.isArray(value), `${name} must be an array`).toBe(true);
}

async function readBody(response: import('@playwright/test').APIResponse) {
  const text = await response.text();
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

test('eval_templates_available', async ({ page }) => {
  test.setTimeout(30_000);

  const response = await page.request.get(`${BACKEND}/api/eval/templates`);
  expect(response.status()).toBe(200);
  const data = await response.json();

  expectArray(data.formats, 'formats');
  expect(data.formats.length).toBeGreaterThan(0);
  expectArray(data.required_columns, 'required_columns');
  expect(data.required_columns).toContain('category');
  expect(data.required_columns).toContain('ground_truth_action');
  expect(typeof data.example_count).toBe('number');
});

test('eval_template_csv_download', async ({ page }) => {
  test.setTimeout(30_000);

  const response = await page.request.get(`${BACKEND}/api/eval/templates/generic.csv`);
  expect(response.status()).toBe(200);
  const text = await response.text();

  expect(response.headers()['content-type'] || '').toContain('text/csv');
  expect(text).toContain('category');
  expect(text).toContain('ground_truth_action');
  expect(text).toContain('privileged_identity_context');
});

test('eval_upload_rejects_invalid', async ({ page }) => {
  test.setTimeout(30_000);

  const response = await page.request.post(`${BACKEND}/api/eval/upload`, {
    multipart: {
      file: {
        name: 'invalid.csv',
        mimeType: 'text/csv',
        buffer: Buffer.from('category,ground_truth_action\ncredential_access,escalate\n'),
      },
    },
  });

  expect([400, 422]).toContain(response.status());
  const body = await readBody(response);
  expect(body).toBeTruthy();
});

test('eval_upload_valid_returns_results', async ({ page }) => {
  test.setTimeout(60_000);

  const csv = [
    'row_id,category,ground_truth_action,privileged_identity_context,asset_criticality,threat_intel_enrichment,pattern_history,time_anomaly,device_trust',
    'pw-1,credential_access,escalate,0.95,0.90,0.85,0.75,0.80,0.10',
    'pw-2,malware_execution,investigate,0.20,0.75,0.65,0.70,0.45,0.35',
    'pw-3,cloud_infrastructure,monitor,0.15,0.55,0.25,0.30,0.35,0.80',
  ].join('\n');

  const response = await page.request.post(`${BACKEND}/api/eval/upload`, {
    multipart: {
      file: {
        name: 'valid.csv',
        mimeType: 'text/csv',
        buffer: Buffer.from(csv),
      },
    },
  });

  expect(response.status()).toBe(200);
  const data = await response.json();
  expect(typeof data.accuracy).toBe('number');
  expect(data.evaluated_rows).toBe(3);
  expect(data.invalid_rows).toBe(0);
  expectArray(data.per_decision_log, 'per_decision_log');
  expectArray(data.per_category_results, 'per_category_results');
  expect(typeof data.majority_baseline).toBe('object');
});
