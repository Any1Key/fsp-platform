import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

test("capture landing", async ({ page }, testInfo) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Проверенные навыки/i })).toBeVisible();
  const dir = process.env.SCREENSHOT_OUTPUT || "/workspace/screenshots";
  fs.mkdirSync(dir, { recursive: true });
  await page.screenshot({
    path: path.join(dir, `landing-${testInfo.project.name}.png`),
    fullPage: true
  });
});
