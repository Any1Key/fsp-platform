import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const syntheticProfile = {
  category: "Backend · Middle",
  score: "87",
  skills: ["Python", "FastAPI", "PostgreSQL"],
  evidence: "FSP evidence becomes a bounded verified signal",
};

const screenshotOutput = process.env.SCREENSHOT_OUTPUT || "/workspace/screenshots";

function writeScreenshotManifest(testInfo: { project: { name: string }; title: string }, surfaces: string[]) {
  const manifestPath = path.join(screenshotOutput, "screenshot-manifest.json");
  const existing = fs.existsSync(manifestPath)
    ? (JSON.parse(fs.readFileSync(manifestPath, "utf8")) as {
        suite: string;
        generatedBy: string;
        fixture: string;
        privacy: string;
        projects: Array<{ project: string; title: string; surfaces: string[] }>;
      })
    : {
        suite: "fsp-public-synthetic-evidence",
        generatedBy: "qa/tests/screenshots.spec.ts",
        fixture: "public-landing-synthetic-profile-v1",
        privacy: "Unauthenticated public surface; no real PII, chat, resumes, tokens, or minor documents.",
        projects: [],
      };
  existing.projects = existing.projects.filter((project) => project.project !== testInfo.project.name);
  existing.projects.push({
    project: testInfo.project.name,
    title: testInfo.title,
    surfaces,
  });
  const manifest = {
    suite: "fsp-public-synthetic-evidence",
    generatedBy: "qa/tests/screenshots.spec.ts",
    fixture: "public-landing-synthetic-profile-v1",
    privacy: "Unauthenticated public surface; no real PII, chat, resumes, tokens, or minor documents.",
    projects: existing.projects,
  };
  fs.writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
}

test("capture responsive synthetic public evidence", async ({ page }, testInfo) => {
  // The frontend's public runtime URL is localhost-oriented for a real browser. QA runs in a
  // Compose container, so route only the browser request to the internal synthetic/demo service.
  for (const publicHost of ["localhost", "127.0.0.1"]) {
    await page.route(`http://${publicHost}:8081/**`, async (route) => {
      const target = new URL(route.request().url());
      target.hostname = "keycloak";
      target.port = "8080";
      await route.continue({ url: target.toString() });
    });
  }
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Проверенные навыки/i })).toBeVisible();
  await expect(page.locator(".proofCard")).toContainText(syntheticProfile.category);
  await expect(page.locator(".proofCard .metric")).toContainText("Assessment");
  await expect(page.locator(".proofCard .metric strong")).toHaveText(syntheticProfile.score);
  for (const skill of syntheticProfile.skills) {
    await expect(page.locator(".proofCard")).toContainText(skill);
  }
  await expect(page.locator(".proofCard")).toContainText(syntheticProfile.evidence);
  await expect(page.locator(".authPanel")).toBeVisible();
  await page.waitForFunction(
    () => !document.querySelector(".authPanel .uiStateLoading"),
    undefined,
    { timeout: 10_000 },
  );
  await page.evaluate(() => document.fonts.ready);

  fs.mkdirSync(screenshotOutput, { recursive: true });
  const prefix = path.join(screenshotOutput, `fsp-${testInfo.project.name}`);

  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: `${prefix}-hero.png`,
    fullPage: false,
  });

  await page.locator("#proof").scrollIntoViewIfNeeded();
  await page.screenshot({
    path: `${prefix}-evidence.png`,
    fullPage: false,
  });

  await page.screenshot({
    path: `${prefix}-full-page.png`,
    fullPage: true
  });

  writeScreenshotManifest(testInfo, ["hero", "evidence", "full-page"]);
});
