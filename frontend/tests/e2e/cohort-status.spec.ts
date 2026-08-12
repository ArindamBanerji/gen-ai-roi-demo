import { test, expect, type Page } from '@playwright/test';
import { BACKEND, FRONTEND } from './helpers';

async function gotoCompounding(page: Page) {
  await page.goto(FRONTEND);
  await page.getByRole('button', { name: /Compounding|Decision Economics/i }).click();
  // The live SOC stack can contend with concurrent AGE reads while the panel mounts.
  await expect(page.getByTestId('cohort-status-panel')).toBeVisible({ timeout: 30_000 });
}

test.describe('SOC cohort status panel', () => {
  test('SOC cohort status panel renders', async ({ page }) => {
    await gotoCompounding(page);
    await expect(page.getByTestId('cohort-status-title')).toContainText('Campaign Measurement Status');
  });

  test('SOC cohort status shows state badge', async ({ page }) => {
    await gotoCompounding(page);
    await expect(page.getByTestId('cohort-status-state-badge')).toContainText(
      /INSTRUMENT_VALIDATED|ACCUMULATING|MEASURED/,
    );
  });

  test('SOC instrument section always visible', async ({ page }) => {
    await gotoCompounding(page);
    await expect(page.getByTestId('cohort-status-instrument')).toBeVisible();
    await expect(page.getByTestId('cohort-status-instrument-tier')).toContainText('T-O');
  });

  test('SOC real section visible', async ({ page }) => {
    await gotoCompounding(page);
    await expect(page.getByTestId('cohort-status-real')).toBeVisible();
    await expect(page.getByTestId('cohort-status-real-tier')).toContainText('T-R');
    await expect(page.getByTestId('cohort-status-progress')).toBeVisible();
  });

  test('SOC cohort-status endpoint returns valid shape', async ({ page }) => {
    const response = await page.request.get(`${BACKEND}/api/campaign/cohort-status`);
    expect(response.ok(), `cohort-status returned ${response.status()}`).toBeTruthy();
    const data = await response.json();

    expect(['INSTRUMENT_VALIDATED', 'ACCUMULATING', 'MEASURED']).toContain(data.state);
    expect(data.instrument).toBeTruthy();
    expect(data.real).toBeTruthy();
    expect(typeof data.real.treatment_n).toBe('number');
    expect(typeof data.real.control_n).toBe('number');
  });

  test('SOC no synthetic lift displayed', async ({ page }) => {
    await gotoCompounding(page);
    await expect(page.getByTestId('cohort-status-panel')).not.toContainText(/synthetic lift/i);
  });

  test('SOC no INSUFFICIENT_DATA message', async ({ page }) => {
    await gotoCompounding(page);
    await expect(page.getByTestId('cohort-status-panel')).not.toContainText('INSUFFICIENT_DATA');
  });

  test('SOC no console errors on cohort panel', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (message) => {
      if (message.type() === 'error') {
        errors.push(message.text());
      }
    });

    await gotoCompounding(page);

    const unexpected = errors.filter((message) => !/favicon|ResizeObserver|Failed to load|Failed to fetch|same key|unique.*key/i.test(message));
    expect(unexpected).toEqual([]);
  });
});
