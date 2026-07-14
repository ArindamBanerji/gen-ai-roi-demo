import { expect, test } from "@playwright/test";

const FRONTEND = process.env.SOC_FRONTEND ?? "http://127.0.0.1:5173";
const BACKEND = process.env.SOC_BACKEND ?? "http://127.0.0.1:8001";

test.beforeEach(async ({ request }) => {
  const health = await request.get(`${BACKEND}/health`, { timeout: 5_000 }).catch(() => null);
  test.skip(!health?.ok(), "SOC backend not running");
});

test("rejection panel visible on runtime evolution", async ({ page }) => {
  await page.goto(FRONTEND);
  await page.getByRole("button", { name: /Runtime Evolution/i }).click();
  await expect(page.getByRole("heading", { name: "Agent Evolution Summary", exact: true })).toBeVisible({
    timeout: 20_000,
  });
});
