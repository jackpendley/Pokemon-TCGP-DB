import { expect, test, type Page } from "@playwright/test";

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

  /**
   * Swipes are dispatched as pointer events rather than driven with page.mouse:
   * on a touch-enabled context (iPhone 14 → hasTouch) the mouse API hangs, and
   * the handlers under test read nothing but clientX/clientY off the event.
   */
  async function swipe(
    page: Page,
    from: { x: number; y: number },
    to: { x: number; y: number },
  ) {
    const flip = page.locator(".flip-inner");
    await flip.dispatchEvent("pointerdown", { clientX: from.x, clientY: from.y });
    await flip.dispatchEvent("pointerup", { clientX: to.x, clientY: to.y });
  }

  async function openFirstCard(page: Page) {
    await page.goto("/cards");
    const tile = page.locator("div.grid button").first();
    await tile.waitFor();
    await tile.click();
    return (await page.locator(".flip-inner").boundingBox())!;
  }

  test("a sideways swipe flips the card", async ({ page }) => {
    // The gesture, not just the button: sideways used to page through the grid.
    const box = await openFirstCard(page);
    const flip = page.locator(".flip-inner");
    await expect(flip).toHaveAttribute("data-flipped", "false");
    const y = box.y + box.height / 2;
    await swipe(page, { x: box.x + box.width * 0.8, y }, { x: box.x + box.width * 0.2, y });
    await expect(flip).toHaveAttribute("data-flipped", "true");
  });

  test("a downward swipe reveals the related-cards tabs", async ({ page }) => {
    const box = await openFirstCard(page);
    const x = box.x + box.width / 2;
    await swipe(page, { x, y: box.y + 20 }, { x, y: box.y + 220 });

    // Tabs are a phone-visible surface now; they used to be desktop-only.
    await expect(page.getByRole("tablist")).toBeVisible();
    await page.getByLabel("Hide related cards").click();
    await expect(page.getByRole("tablist")).toBeHidden();
  });

  test("the Related button reaches the tabs without a gesture", async ({ page }) => {
    await openFirstCard(page);
    await page.getByLabel("Show related cards").click();
    await expect(page.getByRole("tablist")).toBeVisible();
  });
});
