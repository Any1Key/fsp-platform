import { test, expect } from "@playwright/test";

test("FSP evidence brand entrypoint is visible and responsive", async ({ page }) => {
  await page.goto("/");

  await expect(page.locator('img[alt="ФСП"]')).toBeVisible();
  await expect(page.getByText(/FSP evidence becomes a bounded verified signal/i)).toBeVisible();

  const brand = await page.evaluate(() => ({
    primary: getComputedStyle(document.documentElement).getPropertyValue("--brand-primary").trim(),
    accent: getComputedStyle(document.documentElement).getPropertyValue("--brand-accent").trim(),
    overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
  }));
  expect(brand.primary).toBe("#402fff");
  expect(brand.accent).toBe("#ec1d35");
  expect(brand.overflow).toBe(false);
});
