/**
 * soc-profile.spec.ts — /api/soc/profile tensor contract.
 *
 * Focused API checks for the SOC scorer profile exposed to Runtime Evolution.
 * These tests guard the P77 adapter migration: profile JSON must preserve the
 * legacy tensor shape and score metadata expected by the frontend.
 *
 * Run: npx playwright test tests/e2e/soc-profile.spec.ts --reporter=list
 */

import { test, expect } from '@playwright/test';
import { BACKEND } from './helpers';

async function getProfile(request: import('@playwright/test').APIRequestContext): Promise<any> {
  const response = await request.get(`${BACKEND}/api/soc/profile`);
  expect(response.status()).toBe(200);
  return response.json();
}

test.describe('/api/soc/profile contract', () => {
  test('profile shows 6 categories', async ({ request }) => {
    const profile = await getProfile(request);
    expect(Array.isArray(profile.categories)).toBe(true);
    expect(profile.categories.length).toBe(6);
  });

  test('profile shows 4 actions', async ({ request }) => {
    const profile = await getProfile(request);
    expect(Array.isArray(profile.actions)).toBe(true);
    expect(profile.actions.length).toBe(4);
    expect(profile.actions).toEqual(['escalate', 'investigate', 'suppress', 'monitor']);
  });

  test('profile centroids shape is 6x4x6', async ({ request }) => {
    const profile = await getProfile(request);
    expect(Array.isArray(profile.centroids)).toBe(true);
    expect(profile.centroids.length).toBe(6);

    for (const categoryCentroids of profile.centroids) {
      expect(Array.isArray(categoryCentroids)).toBe(true);
      expect(categoryCentroids.length).toBe(4);
      for (const factorVector of categoryCentroids) {
        expect(Array.isArray(factorVector)).toBe(true);
        expect(factorVector.length).toBe(6);
      }
    }
  });

  test('profile IKS score bounded 0-100', async ({ request }) => {
    const profile = await getProfile(request);
    const iks = profile.iks;
    const score = typeof iks === 'number' ? iks : iks?.current ?? iks?.score ?? 0;
    expect(typeof score).toBe('number');
    expect(Number.isFinite(score)).toBe(true);
    expect(score).toBeGreaterThanOrEqual(0);
    expect(score).toBeLessThanOrEqual(100);
  });

  test('profile decision count non-negative', async ({ request }) => {
    const profile = await getProfile(request);
    expect(typeof profile.decision_count).toBe('number');
    expect(profile.decision_count).toBeGreaterThanOrEqual(0);
  });
});
