import { test, expect } from "@playwright/test";

const enabled = process.env.TALENT_RADAR_E2E_ENABLED === "true";

test.describe("Employer Talent Radar polish", () => {
  test.skip(
    !enabled,
    "Set TALENT_RADAR_E2E_ENABLED=true and provide TALENT_RADAR_STORAGE_STATE for an authenticated employer session",
  );

  test("explains evidence, keeps invitation action reachable, and stays usable on mobile", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "mobile-390", "The full interaction runs once on the mobile acceptance viewport");

    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Talent Radar" })).toBeVisible();
    await expect(page.getByText("CATEGORY SUPPLY")).toBeVisible();
    await expect(page.getByRole("button", { name: "View proof" }).first()).toBeVisible();
    await expect(page.getByRole("button", { name: /Пригласить/ }).first()).toBeVisible();

    await page.getByRole("button", { name: "View proof" }).first().click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(page.getByText("Score breakdown")).toBeVisible();
    await expect(page.getByText("Evidence gaps")).toBeVisible();
    await page.getByRole("button", { name: "Закрыть объяснение" }).click();
    await expect(page.getByRole("dialog")).toHaveCount(0);

    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    );
    expect(overflow).toBe(false);
  });
});
