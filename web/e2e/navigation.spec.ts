import { expect, test } from "@playwright/test";

import { HAS_PIPELINE_DATA } from "./fixtures";

test.describe("desktop navigation", () => {
  test.skip(({ isMobile }) => !!isMobile, "sidebar is hidden below md");
  // Navigation asserts on hydrated, data-backed pages.
  test.skip(!HAS_PIPELINE_DATA, "needs pipeline artifacts");

  test("sidebar links navigate", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Cards", exact: true }).click();
    await expect(page).toHaveURL(/\/cards$/);
    await expect(page.getByRole("heading", { name: "Cards", level: 1 })).toBeVisible();
  });

  test("the sidebar collapses and the choice survives a reload", async ({ page }) => {
    await page.goto("/");
    const rail = page.locator("aside.sidebar-rail");
    const expanded = (await rail.boundingBox())!.width;

    await page.getByLabel("Collapse sidebar").click();
    await expect
      .poll(async () => (await rail.boundingBox())!.width)
      .toBeLessThan(expanded);

    // Persisted before paint, so the rail must already be narrow on reload.
    await page.reload();
    expect((await rail.boundingBox())!.width).toBeLessThan(expanded);

    await page.getByLabel("Expand sidebar").click();
    await expect
      .poll(async () => (await rail.boundingBox())!.width)
      .toBe(expanded);
  });
});

test.describe("mobile", () => {
  test.skip(({ isMobile }) => !isMobile, "covers the phone-only UI");
  test.skip(!HAS_PIPELINE_DATA, "needs pipeline artifacts");

  test("the drawer opens, navigates and closes on Escape", async ({ page }) => {
    await page.goto("/");
    // The Suspense fallback (MobileNavFallback) carries the same aria-label as
    // the streamed <MobileNav>, so both are briefly present. Wait for the
    // boundary to resolve rather than racing it.
    const trigger = page.getByLabel("Open navigation");
    await expect(trigger).toHaveCount(1);
    await trigger.click();
    const drawer = page.getByRole("dialog");
    await expect(drawer).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(drawer).toBeHidden();
  });

  test("a card opens full screen and flips to its details", async ({ page }) => {
    await page.goto("/cards");
    const tile = page.locator("div.grid button").first();
    await tile.waitFor();
    await tile.click();

    const dialog = page.locator('[data-slot="dialog-content"]');
    await expect(dialog).toBeVisible();

    // Full-bleed: the viewer fills the viewport rather than sitting in a card.
    // Tolerance covers the scrollbar gutter; the regression this guards against
    // is the old fixed 320px column, which is far outside it.
    const box = (await dialog.boundingBox())!;
    const viewport = page.viewportSize()!;
    expect(box.width).toBeGreaterThan(viewport.width * 0.95);

    const flip = page.locator(".flip-inner");
    await expect(flip).toHaveAttribute("data-flipped", "false");
    // Exact: the card itself is labelled "Show details for <name>", so a
    // substring match would be ambiguous with the gesture button.
    await page.getByLabel("Show details", { exact: true }).click();
    await expect(flip).toHaveAttribute("data-flipped", "true");
    await expect(page.locator(".flip-face-back")).toContainText(/rarity/i);
  });
});
