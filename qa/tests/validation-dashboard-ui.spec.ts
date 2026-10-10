import { test, expect } from "@playwright/test";

const enabled = process.env.VALIDATION_DASHBOARD_E2E_ENABLED === "true";

test.describe("Validation Dashboard", () => {
  test.skip(
    !enabled,
    "Set VALIDATION_DASHBOARD_E2E_ENABLED=true and provide an authenticated employer storage state",
  );

  test("shows aggregate evidence without mobile overflow", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "mobile-390", "The full interaction runs once on the mobile acceptance viewport");

    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Доказательная база подбора" })).toBeVisible();
    await expect(page.getByText("Confusion matrix")).toBeVisible();
    await expect(page.getByText("Grade-collapse check passed")).toBeVisible();

    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    );
    expect(overflow).toBe(false);
  });
});

