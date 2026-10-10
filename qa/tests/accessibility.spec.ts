import { test, expect } from "@playwright/test";

type Rgb = [number, number, number];

function parseRgb(value: string): Rgb | null {
  const channels = value.match(/rgba?\((\d+(?:\.\d+)?),\s*(\d+(?:\.\d+)?),\s*(\d+(?:\.\d+)?)/);
  return channels ? [Number(channels[1]), Number(channels[2]), Number(channels[3])] : null;
}

function luminance([red, green, blue]: Rgb): number {
  const channel = (value: number) => {
    const normalized = value / 255;
    return normalized <= 0.03928 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(red) + 0.7152 * channel(green) + 0.0722 * channel(blue);
}

function contrastRatio(foreground: Rgb, background: Rgb): number {
  const lighter = Math.max(luminance(foreground), luminance(background));
  const darker = Math.min(luminance(foreground), luminance(background));
  return (lighter + 0.05) / (darker + 0.05);
}

test("public entrypoint supports keyboard navigation and AA contrast", async ({ page }) => {
  await page.goto("/");

  const skipLink = page.getByRole("link", { name: "Перейти к содержимому" });
  await page.keyboard.press("Tab");
  await expect(skipLink).toBeFocused();
  await expect(skipLink).toBeVisible();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main-content")).toBeFocused();

  const primaryLink = page.getByRole("link", { name: "Как работает FSP Talent" });
  await primaryLink.focus();
  const focusStyle = await primaryLink.evaluate((element) => {
    const style = getComputedStyle(element);
    return { outline: style.outlineColor, outlineWidth: style.outlineWidth, shadow: style.boxShadow };
  });
  expect(focusStyle.outline).toBe("rgb(255, 255, 255)");
  expect(focusStyle.outlineWidth).toBe("3px");
  expect(focusStyle.shadow).toContain("rgb(64, 47, 255)");

  const contrastResults = await page.evaluate(() => {
    const selectors = [
      ".eyebrow",
      ".lead",
      ".actions a.primary",
      ".actions a.secondary",
      ".cardLabel",
      ".metric span",
      ".metric strong",
      ".chips span",
      ".fspLine",
      ".principles p",
    ];
    const findBackground = (element: HTMLElement): string => {
      let current: HTMLElement | null = element;
      while (current) {
        const background = getComputedStyle(current).backgroundColor;
        if (!background.startsWith("rgba(0, 0, 0, 0)")) return background;
        current = current.parentElement;
      }
      return getComputedStyle(document.body).backgroundColor;
    };
    return selectors.map((selector) => {
      const element = document.querySelector<HTMLElement>(selector);
      if (!element) throw new Error(`Missing contrast target: ${selector}`);
      return {
        selector,
        color: getComputedStyle(element).color,
        background: findBackground(element),
      };
    });
  });

  for (const result of contrastResults) {
    const foreground = parseRgb(result.color);
    const background = parseRgb(result.background);
    expect(foreground, `${result.selector} foreground should be rgb`).not.toBeNull();
    expect(background, `${result.selector} background should be rgb`).not.toBeNull();
    expect(
      contrastRatio(foreground!, background!),
      `${result.selector} contrast ${result.color} on ${result.background}`,
    ).toBeGreaterThanOrEqual(4.5);
  }
});
