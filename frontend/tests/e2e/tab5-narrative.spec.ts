import { test, expect } from '@playwright/test';
import { FRONTEND, collectConsoleErrors, expectNoConsoleErrors, navigateToTab } from './helpers';

test.describe('Tab 5 executive narrative sections', () => {
  test('renders the three executive narrative sections', async ({ page }) => {
    await page.goto(FRONTEND);
    await navigateToTab(page, 5);

    await expect(page.getByText('System Health').first()).toBeVisible();
    await expect(page.getByText('What the System Has Learned').first()).toBeVisible();
    await expect(page.getByText('Recommendations').first()).toBeVisible();
  });

  test('shows conservation and system health language', async ({ page }) => {
    await page.goto(FRONTEND);
    await navigateToTab(page, 5);

    await expect(page.getByText(/System Health|rolling accuracy|conservation|protective mode/i).first()).toBeVisible();
    await expect(page.getByText(/Verified|Correct|Threshold/i).first()).toBeVisible();
  });

  test('shows IKS and institutional knowledge language', async ({ page }) => {
    await page.goto(FRONTEND);
    await navigateToTab(page, 5);

    await expect(page.getByText(/IKS|institutional knowledge|Decisions processed/i).first()).toBeVisible();
  });

  test('shows recommendation language', async ({ page }) => {
    await page.goto(FRONTEND);
    await navigateToTab(page, 5);

    await expect(page.getByText(/Recommendations|category-specific|performing within expected ranges|action required/i).first()).toBeVisible();
  });

  test('sections survive reload without real console errors', async ({ page }) => {
    const consoleErrors = collectConsoleErrors(page);

    await page.goto(FRONTEND);
    await navigateToTab(page, 5);
    await expect(page.getByText('System Health').first()).toBeVisible();

    await page.reload();
    await navigateToTab(page, 5);
    await expect(page.getByText('System Health').first()).toBeVisible();
    await expect(page.getByText('What the System Has Learned').first()).toBeVisible();
    await expect(page.getByText('Recommendations').first()).toBeVisible();

    expectNoConsoleErrors(consoleErrors);
  });
});
