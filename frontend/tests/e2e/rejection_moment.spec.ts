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

test("promotion and rejection table renders on compounding", async ({ page }) => {
  await page.goto(FRONTEND);
  await page.getByRole("button", { name: "Compounding", exact: true }).click();
  await expect(page.getByTestId("promotion-rejection-table")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("What survived the gate?", { exact: true })).toBeVisible();
});

test("promotion table exposes failure reasons", async ({ page }) => {
  await page.goto(FRONTEND);
  await page.getByRole("button", { name: "Compounding", exact: true }).click();
  const panel = page.getByTestId("promotion-rejection-table");
  await expect(panel).toBeVisible({ timeout: 20_000 });
  await expect(panel.getByText("Failure category", { exact: true })).toBeVisible();
});

test("continuity panel renders on executive narrative", async ({ page }) => {
  await page.goto(FRONTEND);
  await page.getByRole("button", { name: "Executive Narrative", exact: true }).click();
  await expect(page.getByTestId("continuity-panel")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("$ of judgment retained", { exact: true })).toBeVisible();
});

test("continuity panel shows retained judgment metric", async ({ page }) => {
  await page.goto(FRONTEND);
  await page.getByRole("button", { name: "Executive Narrative", exact: true }).click();
  const panel = page.getByTestId("continuity-panel");
  await expect(panel).toBeVisible({ timeout: 20_000 });
  await expect(panel.getByText("Judgment retained", { exact: true })).toBeVisible();
});

test("rejection moment shows failure categories", async ({ page }) => {
  await page.goto(FRONTEND);
  await page.getByRole("button", { name: /Runtime Evolution/i }).click();
  const panel = page.getByTestId("soc-rejection-moment");
  await expect(panel).toBeVisible({ timeout: 20_000 });
  await expect(panel.getByText("SOC rejection moment", { exact: true })).toBeVisible();
  await expect(panel.getByText("Correctness floor", { exact: true })).toBeVisible();
});

test("navigating between compounding and executive preserves the new panels", async ({ page }) => {
  await page.goto(FRONTEND);
  await page.getByRole("button", { name: "Compounding", exact: true }).click();
  await expect(page.getByTestId("promotion-rejection-table")).toBeVisible({ timeout: 20_000 });
  await page.getByRole("button", { name: "Executive Narrative", exact: true }).click();
  await expect(page.getByTestId("continuity-panel")).toBeVisible({ timeout: 20_000 });
});
