import { test, expect } from "@playwright/test";

test("bootstrap landing renders without horizontal overflow", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Проверенные навыки/i })).toBeVisible();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth
  );
  expect(overflow).toBe(false);
});

test("backend health is reachable", async ({ request }) => {
  const base = process.env.BACKEND_BASE_URL || "http://backend:8000";
  const response = await request.get(`${base}/health`);
  expect(response.ok()).toBeTruthy();
});
