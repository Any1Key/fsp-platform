import { test, expect } from "@playwright/test";

test("FSP evidence brand entrypoint is visible and responsive", async ({ page }) => {
  await page.goto("/");

  await expect(page.locator('img[alt="ФСП"]')).toBeVisible();
  await expect(page.locator('main[data-brand="fsp-talent"]')).toBeVisible();
  await expect(page.getByRole("link", { name: "Как работает FSP Talent" })).toBeVisible();
  await expect(page.getByText(/FSP evidence becomes a bounded verified signal/i)).toBeVisible();

  const brand = await page.evaluate(() => ({
    primary: getComputedStyle(document.documentElement).getPropertyValue("--brand-primary").trim(),
    accent: getComputedStyle(document.documentElement).getPropertyValue("--brand-accent").trim(),
    ink: getComputedStyle(document.documentElement).getPropertyValue("--brand-ink").trim(),
    font: getComputedStyle(document.body).fontFamily,
    overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
  }));
  expect(brand.primary).toBe("#402fff");
  expect(brand.accent).toBe("#ec1d35");
  expect(brand.ink).toBe("#1b1c21");
  expect(brand.font).toContain("JetBrains Mono");
  expect(brand.overflow).toBe(false);

  const logo = page.locator('img[alt="ФСП"]');
  await expect(logo).toHaveAttribute("src", /logo_white1/);

  const brandLink = page.getByRole("link", { name: "Как работает FSP Talent" });
  const linkBox = await brandLink.boundingBox();
  expect(linkBox).not.toBeNull();
  expect(linkBox!.x + linkBox!.width).toBeLessThanOrEqual(page.viewportSize()!.width);
  const responsiveBounds = await page.evaluate(() => {
    const viewportWidth = document.documentElement.clientWidth;
    const selectors = [
      'a.primary',
      '.proofCard',
      '.authPanel',
      '.principles',
    ];
    return selectors.flatMap((selector) =>
      Array.from(document.querySelectorAll<HTMLElement>(selector)).map((element) => {
        const rect = element.getBoundingClientRect();
        return {
          selector,
          left: rect.left,
          right: rect.right,
          width: rect.width,
          visible: rect.width > 0 && rect.height > 0,
          inside: rect.left >= -1 && rect.right <= viewportWidth + 1,
        };
      }),
    );
  });
  for (const element of responsiveBounds.filter((item) => item.visible)) {
    expect(element.inside, `${element.selector} escaped the viewport`).toBe(true);
    expect(element.width).toBeGreaterThan(0);
  }
  if (page.viewportSize()!.width <= 1100) {
    await expect(page.locator(".hero")).toHaveCSS("grid-template-columns", /^(\d+(\.\d+)?px)$/);
  }
  await brandLink.focus();
  await expect(brandLink).toBeFocused();
  const focus = await brandLink.evaluate((element) => {
    const style = getComputedStyle(element);
    return { outlineStyle: style.outlineStyle, outlineWidth: style.outlineWidth };
  });
  expect(focus.outlineStyle).toBe("solid");
  expect(focus.outlineWidth).toBe("3px");

  await page.emulateMedia({ reducedMotion: "reduce" });
  const motion = await page.evaluate(() => ({
    scroll: getComputedStyle(document.documentElement).scrollBehavior,
    transition: getComputedStyle(document.querySelector(".actions a")!).transitionDuration,
  }));
  expect(motion.scroll).toBe("auto");
  expect(parseFloat(motion.transition)).toBeLessThanOrEqual(0.01);
});
